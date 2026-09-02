from __future__ import annotations
import re
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

    async def evaluate(
        self, 
        agent_id: UUID, 
        tool_name: str, 
        tool_args: dict[str, Any], 
        required_permission: str
    ) -> PolicyDecision:
        try:
            # 1. Fetch Agent and Passport
            agent = await self.agent_repo.get_agent(agent_id)
            if not agent or not agent.passport:
                return PolicyDecision(False, "Agent or compliance passport not found")
                
            # 2. Check Lifecycle state (must be ACTIVE)
            if agent.passport.lifecycle_state != "ACTIVE":
                return PolicyDecision(False, f"Agent is not ACTIVE (current state: {agent.passport.lifecycle_state})")

            # 3. Check Permissions
            permissions = await self.perm_repo.get_permissions_for_passport(agent.passport.id)
            perm_strings = [p.permission for p in permissions]
            
            if required_permission and required_permission not in perm_strings:
                return PolicyDecision(False, f"Missing required permission: '{required_permission}'")

            # 4. DYNAMIC DATABASE POLICIES
            # Fetch all active policies configured by the Org Admin in the database
            policies = await self.policy_repo.get_active_policies_for_org(agent.org_id)
            
            for policy in policies:
                for rule in policy.rules:
                    if not rule.enabled:
                        continue
                        
                    # Evaluate SQL Blocklist Rule
                    if rule.rule_type == "sql_blocklist" and tool_name == "sql_query":
                        blocked_keywords = rule.config.get("keywords", [])
                        query = tool_args.get("query", "")
                        for keyword in blocked_keywords:
                            # Use regex to find exact word matches (case insensitive)
                            if re.search(rf"\b{keyword}\b", query, re.IGNORECASE):
                                return PolicyDecision(False, f"Policy '{policy.name}': Disallowed keyword '{keyword}' detected.")
                    
                    # You can easily add more rule_types here in the future!

            return PolicyDecision(True, "All database policy and permission checks passed")
            
        except Exception as e:
            # Fail-Closed Security: if any error happens, BLOCK execution for safety
            return PolicyDecision(False, f"Governance engine internal error: {str(e)}")
