from typing import Any
from uuid import UUID
from app.domain.agents.repository import AgentRepository
from app.domain.permissions.repository import PermissionRepository
from app.domain.policies.repository import PolicyRepository

class PolicyDecision:
    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason

class PolicyEngine:
    def __init__(
        self,
        agent_repo: AgentRepository,
        perm_repo: PermissionRepository,
        policy_repo: PolicyRepository
    ):
        self.agent_repo = agent_repo
        self.perm_repo = perm_repo
        self.policy_repo = policy_repo

    async def evaluate(self, agent_id: UUID, tool_name: str, tool_args: dict[str, Any], required_permission: str) -> PolicyDecision:
        try:
            agent = await self.agent_repo.get_agent(agent_id)
            if not agent or not agent.passport:
                return PolicyDecision(False, "Agent or passport not found")
                
            if agent.passport.lifecycle_state != "ACTIVE":
                return PolicyDecision(False, f"Agent is not ACTIVE (current state: {agent.passport.lifecycle_state})")

            permissions = await self.perm_repo.get_permissions_for_passport(agent.passport.id)
            perm_strings = [p.permission for p in permissions]
            
            if required_permission not in perm_strings:
                return PolicyDecision(False, f"Missing required permission: {required_permission}")

            # Here we would fetch and evaluate dynamic PolicyRules for the org.
            # Default to ALLOW if all hard checks passed.
            return PolicyDecision(True, "All checks passed")
            
        except Exception as e:
            # FAIL-CLOSED default
            return PolicyDecision(False, f"Governance engine error: {str(e)}")
