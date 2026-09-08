import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.domain.auth.models import Organization, Profile
from app.domain.agents.models import Agent, AgentPassport, AgentSkill
from app.domain.agent_requests.models import AgentRequest
from app.domain.skills.models import SkillModel, ToolModel, SkillPermission
from app.domain.policies.models import Policy, PolicyRule
from app.domain.executions.models import Execution
from app.domain.audit.models import AuditEvent
from app.domain.costs.models import CostEvent
from app.domain.documents.models import Document, DocumentChunk
from app.domain.permissions.models import Permission
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def seed_data():
    async with AsyncSessionLocal() as session:
        org_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        admin_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        builder_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

        # 0. Organization & Profiles (3 roles: admin, agent_builder, user)
        res = await session.execute(select(Organization).where(Organization.id == org_id))
        org = res.scalar_one_or_none()
        if not org:
            org = Organization(id=org_id, name="Default Org")
            session.add(org)

        profiles_data = [
            (admin_id, "admin"),
            (builder_id, "agent_builder"),
            (user_id, "user"),
        ]
        for pid, role in profiles_data:
            p_res = await session.execute(select(Profile).where(Profile.id == pid))
            p = p_res.scalar_one_or_none()
            if not p:
                session.add(Profile(id=pid, org_id=org_id, role=role))
            else:
                p.role = role

        await session.flush()
        
        # 0.5. Skills bootstrap
        skills_to_seed = [
            SkillModel(id="ticketing", name="ticketing", display_name="Ticketing & ITSM", description="Create and resolve tickets", version="1.0", trust_level="verified"),
            SkillModel(id="sql_query", name="sql_query", display_name="SQL Query", description="Query internal databases", version="1.0", trust_level="verified"),
            SkillModel(id="document_search", name="document_search", display_name="Knowledge Search", description="RAG document search", version="1.0", trust_level="verified"),
        ]
        for sk in skills_to_seed:
            existing = await session.get(SkillModel, sk.id)
            if not existing:
                session.add(sk)
        await session.flush()

        # 1. Policies
        policy_id = uuid.uuid4()
        policy = Policy(
            id=policy_id,
            org_id=org_id,
            name="Default Governance Policy",
            description="Enforces baseline security and token controls.",
            enabled=True
        )
        session.add(policy)
        
        policy_rule = PolicyRule(
            id=uuid.uuid4(),
            policy_id=policy_id,
            name="Permissions Enforcer",
            rule_type="PERMISSION_CHECK",
            config={},
            priority=100,
            enabled=True
        )
        session.add(policy_rule)

        # 2. Agent Requests
        # Request 1: PENDING (User requested, awaiting builder claim)
        req_pending_id = uuid.uuid4()
        session.add(AgentRequest(
            id=req_pending_id,
            org_id=org_id,
            requester_id=user_id,
            builder_id=None,
            agent_id=None,
            title="Customer IT Onboarding Agent",
            description="Automates provisioning IT access and issuing initial support tickets.",
            requested_skills=["ticketing"],
            status="PENDING",
            created_at=datetime.now(timezone.utc)
        ))

        # Request 2: CLAIMED (Builder claimed, in development)
        req_claimed_id = uuid.uuid4()
        session.add(AgentRequest(
            id=req_claimed_id,
            org_id=org_id,
            requester_id=user_id,
            builder_id=builder_id,
            agent_id=None,
            title="Sales Analytics & Reporting Bot",
            description="Queries internal sales SQL tables and compiles weekly revenue digests.",
            requested_skills=["sql_query"],
            status="CLAIMED",
            claimed_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        ))

        # 3. Agents & Linked Requests
        req_fulfilled_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        # Step A: Insert fulfilled request with agent_id=None
        req_fulfilled = AgentRequest(
            id=req_fulfilled_id,
            org_id=org_id,
            requester_id=user_id,
            builder_id=builder_id,
            agent_id=None,
            title="Customer Support Escalation Assistant",
            description="Automated triage bot for support escalations and disputes.",
            requested_skills=["ticketing", "sql_query"],
            status="FULFILLED",
            claimed_at=datetime.now(timezone.utc),
            fulfilled_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        session.add(req_fulfilled)
        await session.flush()

        # Step B: Insert agent referencing request_id
        agent = Agent(
            id=agent_id,
            org_id=org_id,
            owner_id=builder_id,
            assigned_user_id=user_id,
            request_id=req_fulfilled_id,
            name="Support Escalation Bot",
            description="Reads tickets and queries payroll to resolve customer disputes.",
            status="ACTIVE"
        )
        session.add(agent)
        await session.flush()

        # Step C: Link agent_id back on request
        req_fulfilled.agent_id = agent_id
        await session.flush()

        passport_id = uuid.uuid4()
        passport = AgentPassport(
            id=passport_id,
            agent_id=agent.id,
            compliance_status="COMPLIANT",
            lifecycle_state="ACTIVE",
            permissions=[]
        )
        session.add(passport)
        
        permissions = [
            Permission(id=uuid.uuid4(), passport_id=passport_id, permission="ticket:read"),
            Permission(id=uuid.uuid4(), passport_id=passport_id, permission="ticket:create"),
            Permission(id=uuid.uuid4(), passport_id=passport_id, permission="sql:read:tickets"),
            Permission(id=uuid.uuid4(), passport_id=passport_id, permission="sql:read:internal_payroll")
        ]
        session.add_all(permissions)

        # AgentSkills (ticketing and sql_query)
        session.add(AgentSkill(agent_id=agent.id, skill_id="ticketing"))
        session.add(AgentSkill(agent_id=agent.id, skill_id="sql_query"))

        # Agent 2: Self-initiated build by builder (no user assignment, in draft)
        agent_draft_id = uuid.uuid4()
        agent_draft = Agent(
            id=agent_draft_id,
            org_id=org_id,
            owner_id=builder_id,
            assigned_user_id=None,
            request_id=None,
            name="Document Search Specialist",
            description="Semantic search over internal knowledge bases and SOP documents.",
            status="DRAFT"
        )
        session.add(agent_draft)

        passport_draft_id = uuid.uuid4()
        session.add(AgentPassport(
            id=passport_draft_id,
            agent_id=agent_draft_id,
            compliance_status="PENDING",
            lifecycle_state="DRAFT",
            permissions=[]
        ))
        session.add(AgentSkill(agent_id=agent_draft_id, skill_id="document_search"))

        # 4. Documents
        doc_id_1 = uuid.uuid4()
        session.add(Document(
            id=doc_id_1,
            org_id=org_id,
            title="Refund Policy 2026",
            source="manual",
            access_scope=["public"]
        ))
        session.add(DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id_1,
            content="All refunds must be processed within 14 days of purchase. No exceptions.",
            embedding=[0.0] * 768,
            chunk_index=0
        ))
        
        doc_id_2 = uuid.uuid4()
        session.add(Document(
            id=doc_id_2,
            org_id=org_id,
            title="VIP Handling Guidelines",
            source="manual",
            access_scope=["internal"]
        ))
        session.add(DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id_2,
            content="VIP customers (tagged in Zendesk) receive automatic 10% concessions.",
            embedding=[0.0] * 768,
            chunk_index=0
        ))

        # 5. Executions
        exec_id = uuid.uuid4()
        execution = Execution(
            id=exec_id,
            agent_id=agent.id,
            org_id=org_id,
            goal="Refund ticket TCK-1002.",
            status="COMPLETED",
            result="Refund initiated."
        )
        session.add(execution)
        await session.flush()

        # 6. Audit & Cost Events
        session.add(AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="agent",
            actor_id=agent.id,
            agent_id=agent.id,
            execution_id=exec_id,
            action="tool_call",
            tool="read_ticket",
            policy_decision="ALLOW",
            reason="All policies passed",
            timestamp=datetime.now(timezone.utc)
        ))
        
        session.add(AuditEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            actor_type="agent",
            actor_id=agent.id,
            agent_id=agent.id,
            execution_id=exec_id,
            action="tool_call",
            tool="delete_database",
            policy_decision="DENY",
            reason="Missing required permission",
            timestamp=datetime.now(timezone.utc)
        ))

        session.add(CostEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            agent_id=agent.id,
            execution_id=exec_id,
            event_type="llm_inference",
            model="gpt-4o",
            prompt_tokens=150,
            completion_tokens=50,
            total_tokens=200,
            cost_usd=0.0015,
            timestamp=datetime.now(timezone.utc)
        ))

        await session.commit()
        print("Demo seed data for Three-Role Model successfully generated!")

if __name__ == "__main__":
    asyncio.run(seed_data())