from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.domain.agents.repository import AgentRepository
from app.domain.audit.repository import AuditRepository
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
        policy_repo: PolicyRepository,
        audit_repo: AuditRepository | None = None,
    ):
        self.agent_repo = agent_repo
        self.perm_repo = perm_repo
        self.policy_repo = policy_repo
        # Only RATE_LIMIT needs it, and only to count recent calls. Optional so
        # every existing caller keeps working; a RATE_LIMIT rule without it
        # denies rather than passes - see _check_rate_limit.
        self.audit_repo = audit_repo

    async def evaluate(
        self, agent_id: UUID, tool_name: str, tool_args: dict[str, Any], required_permission: str
    ) -> PolicyDecision:
        try:
            # 1. Fetch Agent and Passport
            agent = await self.agent_repo.get_agent(agent_id)
            if not agent or not agent.passport:
                return PolicyDecision(False, "Agent or compliance passport not found")

            # 2. Check Lifecycle state (must be ACTIVE)
            if agent.passport.lifecycle_state != "ACTIVE":
                return PolicyDecision(
                    False, f"Agent is not ACTIVE (current state: {agent.passport.lifecycle_state})"
                )

            # 3. Check Permissions
            permissions = await self.perm_repo.get_permissions_for_passport(agent.passport.id)
            perm_strings = [p.permission for p in permissions]

            if required_permission and required_permission not in perm_strings:
                return PolicyDecision(
                    False, f"Missing required permission: '{required_permission}'"
                )

            # 4. DYNAMIC DATABASE POLICIES
            # Fetch all active policies configured by the Org Admin in the database
            policies = await self.policy_repo.get_active_policies_for_org(agent.org_id)

            for policy in policies:
                for rule in policy.rules:
                    if not rule.enabled:
                        continue

                    # Rule types are database values written by an admin, so
                    # they are matched case-insensitively: the FRD writes them
                    # in upper case and the seeded demo policy in lower.
                    rule_type = (rule.rule_type or "").strip().lower()

                    if rule_type == "sql_blocklist" and tool_name == "sql_query":
                        denial = self._check_query_blocklist(policy, rule, tool_args)
                    elif rule_type == "solr_query_blocklist" and tool_name in (
                        "search_solr",
                        "facet_solr",
                    ):
                        denial = self._check_query_blocklist(policy, rule, tool_args)
                    elif rule_type == "deny_list":
                        denial = self._check_deny_list(policy, rule, tool_name, tool_args)
                    elif rule_type == "rate_limit":
                        denial = await self._check_rate_limit(policy, rule, agent_id)
                    else:
                        denial = None

                    if denial is not None:
                        return denial

            return PolicyDecision(True, "All database policy and permission checks passed")

        except Exception as e:
            # Fail-Closed Security: if any error happens, BLOCK execution for safety
            return PolicyDecision(False, f"Governance engine internal error: {str(e)}")

    # --- rule types ------------------------------------------------------
    #
    # Each returns a denial or None. Splitting them out keeps evaluate()
    # readable as "which rules exist, in what order", and means a new rule type
    # is one method plus one branch rather than another nested block.

    @staticmethod
    def _check_query_blocklist(policy, rule, tool_args: dict[str, Any]) -> PolicyDecision | None:
        """Deny a query containing a blocked keyword.

        Shared by `sql_blocklist` and `solr_query_blocklist`: both rule types
        ask the identical question of the identical `query` argument, only of
        a different tool, so they run one check rather than two copies that
        could drift apart.
        """
        query = tool_args.get("query", "")
        for keyword in rule.config.get("keywords", []):
            # Word boundaries, case-insensitive: "dropped" is not "DROP".
            if re.search(rf"\b{re.escape(keyword)}\b", query, re.IGNORECASE):
                return PolicyDecision(
                    False,
                    f"Policy '{policy.name}': Disallowed keyword '{keyword}' detected.",
                )
        return None

    @staticmethod
    def _check_deny_list(
        policy, rule, tool_name: str, tool_args: dict[str, Any]
    ) -> PolicyDecision | None:
        """FRD-03: deny specific tool **and argument** combinations.

        `blocked_tools` alone cannot express "this tool, but not against
        payroll", so `blocked_args` narrows it: with both present the call is
        denied only when the tool matches *and* one of the strings appears in
        its arguments. `blocked_args` on its own applies to every tool.
        """
        blocked_tools = rule.config.get("blocked_tools", [])
        blocked_args = rule.config.get("blocked_args", [])

        tool_matches = tool_name in blocked_tools
        if blocked_tools and not tool_matches:
            return None

        if not blocked_args:
            if tool_matches:
                return PolicyDecision(
                    False, f"Policy '{policy.name}': tool '{tool_name}' is on the deny list."
                )
            return None

        haystack = " ".join(str(v) for v in tool_args.values()).lower()
        for needle in blocked_args:
            if str(needle).lower() in haystack:
                return PolicyDecision(
                    False,
                    f"Policy '{policy.name}': '{tool_name}' may not be called with '{needle}'.",
                )
        return None

    async def _check_rate_limit(self, policy, rule, agent_id: UUID) -> PolicyDecision | None:
        """Deny once the agent has made N tool calls in the last minute.

        Counted from the audit log rather than from memory, because the count
        must survive a restart and be the same across processes - an in-memory
        counter would reset the limit every deploy, which is when a runaway
        agent is most likely to be running.

        With no audit repository the limit cannot be counted at all. That is a
        denial, not a pass: an unevaluable limit is not an absent one, and
        fail-closed is the documented stance everywhere else in this engine.
        """
        max_calls = rule.config.get("max_calls_per_minute")
        if not max_calls:
            return None

        if self.audit_repo is None:
            return PolicyDecision(
                False,
                f"Policy '{policy.name}': rate limit cannot be evaluated "
                "(no audit repository available).",
            )

        since = datetime.now(timezone.utc) - timedelta(minutes=1)
        recent = await self.audit_repo.count_tool_calls_since(agent_id=agent_id, since=since)
        if recent >= max_calls:
            return PolicyDecision(
                False,
                f"Policy '{policy.name}': rate limit of {max_calls} tool calls "
                f"per minute reached ({recent} in the last minute).",
            )
        return None
