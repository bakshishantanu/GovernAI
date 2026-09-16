from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RequirementStatus:
    key: str
    type: str
    label: str
    description: str
    fields: list[dict]
    satisfied: bool


async def resolve_requirements(
    org_id: UUID,
    skill_ids: list[str],
    skill_repo,
    connection_repo,
    document_repo,
) -> list[RequirementStatus]:
    """The deduplicated setup checklist for an agent built from `skill_ids`.

    Two skills that both declare a "documents" requirement collapse into one
    entry -- the UI renders one upload box, not two (first declaration wins
    for label/description, which only matters if two skills phrase the same
    key differently; none do today). Satisfaction is checked per requirement
    type: `file_upload` looks at whether the org has ever uploaded a READY
    document (a document is org-wide, not agent-scoped, so any ready
    document satisfies it -- there is deliberately no per-agent document
    binding yet); anything else looks for a matching row in the org's
    connections.
    """
    by_key: dict[str, RequirementStatus] = {}
    connections = {c.requirement_key for c in await connection_repo.list_for_org(org_id)}
    documents = await document_repo.list_documents(org_id)
    has_ready_document = any(d.status == "READY" for d in documents)

    for skill_id in skill_ids:
        skill = await skill_repo.get_skill(skill_id)
        if skill is None:
            continue
        for requirement in skill.requirements:
            if requirement.key in by_key:
                continue
            satisfied = (
                has_ready_document
                if requirement.type == "file_upload"
                else requirement.key in connections
            )
            by_key[requirement.key] = RequirementStatus(
                key=requirement.key,
                type=requirement.type,
                label=requirement.label,
                description=requirement.description,
                fields=list(requirement.fields) if requirement.fields else [],
                satisfied=satisfied,
            )

    return list(by_key.values())
