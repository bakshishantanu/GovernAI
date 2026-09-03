# ADR 0008: Agent Passport & RBAC Permission Model

## Context
In traditional applications, Role-Based Access Control (RBAC) applies to human users. In GovernAI, we must apply permissions to autonomous agents. We needed a model that allows humans to grant subset permissions to agents securely.

## Decision
We introduced the concept of an **Agent Passport** (`app/domain/agents/models.py`), which acts as the sovereign identity and permission store for a specific agent instance.

## Rationale
1. **Least Privilege:** An agent does not inherit the permissions of the human who created it. Instead, the human must explicitly stamp the Agent's Passport with specific, granular permissions (e.g., `ticket:read`, `sql:read:internal_payroll`).
2. **Kill Switch Integration:** The Passport contains a `lifecycle_state` (ACTIVE vs SUSPENDED). The overarching Policy Engine immediately checks this state; if the passport is suspended, all permissions are instantly voided, effectively killing the agent mid-flight.
3. **Compliance Triggers:** Future iterations can implement automated Passport renewals or compliance checks, where an agent's permissions automatically expire unless re-approved by a human auditor.

## Consequences
- Agent creation requires a two-step mental model: Instantiate the Agent, then Configure the Passport.
- Tools must map 1-to-1 with the granular permission strings defined in the Passport.
