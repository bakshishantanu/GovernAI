from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents.repository import DocumentRepository
from app.domain.skills.models import SkillModel, SkillPermission, SkillRequirementModel, ToolModel
from app.domain.skills.repository import SkillRepository
from app.runtime.rag.embeddings import EmbeddingProvider
from app.runtime.rag.pgvector_search import PgVectorDocumentSearchAdapter
from app.skills.base import BaseTool
from app.skills.document_search import DocumentSearchSkill
from app.skills.figma_design import FigmaDesignSkill
from app.skills.site_audit import SiteAuditSkill
from app.skills.solr_search import SolrSearchSkill
from app.skills.ticketing import (
    TicketDraftStore,
    TicketingSkill,
    build_jira_adapter_from_settings,
)


class SkillRegistry:
    def __init__(
        self,
        skill_repo: SkillRepository,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
        draft_store: TicketDraftStore | None = None,
    ):
        self.skill_repo = skill_repo
        self.session = session
        # Real embeddings when a provider is wired in (see api/deps.py); falls
        # back to the TF-IDF adapter otherwise, e.g. in tests, where a real
        # embedding call has no place (see manual_llm_smoke_test.py's rationale).
        document_search_adapter = None
        if embedding_provider is not None:
            document_search_adapter = PgVectorDocumentSearchAdapter(
                repo=DocumentRepository(session), embedding_provider=embedding_provider
            )

        # Real Jira when configured (see .env.example); falls back to
        # TicketingSkill's own in-memory mock otherwise, e.g. in tests.
        jira_adapter = build_jira_adapter_from_settings()

        # In a real app, this scans all classes inheriting from BaseSkill.
        # For now, we manually register the MVP skills (FRD-05).
        self._instances = {
            skill.name: skill
            for skill in (
                TicketingSkill(adapter=jira_adapter, draft_store=draft_store),
                SolrSearchSkill(permitted_collections={"knowledge_base", "compliance_docs"}),
                DocumentSearchSkill(permitted_scopes={"public"}, adapter=document_search_adapter),
                FigmaDesignSkill(),
                SiteAuditSkill(),
            )
        }

    def get_tools(self, skill_ids: list[str]) -> list[BaseTool]:
        """Resolves an agent's bound skill ids into the tool list its LangGraph
        run should expose (FRD-06). A skill_id with no matching registered
        instance is skipped rather than raising -- binding already validates
        the id exists in the DB at agent-creation time (see AgentService),
        so this only happens if a skill was deregistered afterward."""
        tools: list[BaseTool] = []
        for skill_id in skill_ids:
            skill = self._instances.get(skill_id)
            if skill is not None:
                tools.extend(skill.get_tools())
        return tools

    async def bootstrap(self):
        for skill_class in self._instances.values():
            existing = await self.skill_repo.get_skill(skill_class.name)

            if existing is None:
                db_skill = SkillModel(
                    id=skill_class.name,
                    name=skill_class.name,
                    display_name=skill_class.display_name,
                    description=skill_class.description,
                    version=skill_class.version,
                    trust_level=skill_class.trust_level,
                )
                self.session.add(db_skill)

                for permission in skill_class.required_permissions:
                    self.session.add(
                        SkillPermission(id=uuid.uuid4(), skill=db_skill, permission=permission)
                    )

                for tool in skill_class.get_tools():
                    self.session.add(
                        ToolModel(
                            id=uuid.uuid4(),
                            skill=db_skill,
                            name=tool.name,
                            description=tool.description,
                            required_permission=tool.required_permission,
                        )
                    )
                skill_id_for_requirements = db_skill.id
            else:
                # Requirements are re-synced on every boot, unlike
                # permissions/tools above: this is the only piece of a
                # skill's manifest expected to change after a skill already
                # exists in an org's DB, since it ships after some orgs will
                # already have bootstrapped without it.
                for stale_requirement in list(existing.requirements):
                    await self.session.delete(stale_requirement)
                skill_id_for_requirements = existing.id

            for requirement in skill_class.requirements:
                self.session.add(
                    SkillRequirementModel(
                        id=uuid.uuid4(),
                        skill_id=skill_id_for_requirements,
                        key=requirement.key,
                        type=requirement.type,
                        label=requirement.label,
                        description=requirement.description,
                        fields=[
                            {
                                "key": f.key,
                                "label": f.label,
                                "secret": f.secret,
                                "placeholder": f.placeholder,
                            }
                            for f in requirement.fields
                        ]
                        if requirement.fields
                        else None,
                    )
                )
