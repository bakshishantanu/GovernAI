import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.domain.agents.models import Agent, AgentPassport, AgentSkill
from app.domain.policies.models import Policy, PolicyRule
from app.domain.skills.models import SkillModel, ToolModel
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

        # 2. Agents
        agent_id = uuid.uuid4()
        agent = Agent(
            id=agent_id,
            org_id=org_id,
            owner_id=admin_id,
            name="Support Escalation Bot",
            description="Reads tickets and queries payroll to resolve customer disputes.",
            status="ACTIVE"
        )
        session.add(agent)

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

        # 3. Documents
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

        # 4. Executions
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

        # 5. Audit & Cost Events
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
        print("Demo seed data successfully generated!")

if __name__ == "__main__":
    asyncio.run(seed_data())