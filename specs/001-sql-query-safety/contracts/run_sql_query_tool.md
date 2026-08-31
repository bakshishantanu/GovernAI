# Contract: `run_sql_query` tool

This is the tool contract exposed to the LLM/orchestrator, in the same shape as every other
`BaseTool` in the platform (Contract 5 — declared `name`, `description`, `parameters` JSON
schema, `execute()`). This is the external interface this feature adds; there is no HTTP
endpoint — tools are invoked in-process by the agent runtime, the same way `TicketingSkill`'s
tools already are.

## Tool metadata

| Field | Value |
|---|---|
| `name` | `run_sql_query` |
| `description` | "Answer a question requiring computation over structured data by running a read-only, scoped SQL query." |

## Input schema (`parameters`)

```json
{
  "type": "object",
  "properties": {
    "question": {
      "type": "string",
      "description": "The natural-language question to answer from structured data."
    },
    "sql": {
      "type": "string",
      "description": "A single read-only SQL SELECT statement answering the question, referencing only permitted tables."
    }
  },
  "required": ["question", "sql"]
}
```

## Output shape — success

```json
{
  "success": true,
  "columns": ["ticket_id", "count"],
  "rows": [{"ticket_id": "TCK-1001", "count": 3}],
  "row_count": 1
}
```

An empty result set is still `"success": true` with `"row_count": 0` and `"rows": []` — never
reported as a failure or a denial (FR-008).

## Output shape — denied (validation failure)

```json
{
  "success": false,
  "error": "denied",
  "reason": "query references table 'internal_payroll' which is outside this agent's permitted scope",
  "statement_type": "SELECT"
}
```

Reasons are always human-readable and specific enough to distinguish a write attempt from an
out-of-scope table from a parse failure — this is what gets written to the audit trail (FR-006).

## Output shape — timeout

```json
{
  "success": false,
  "error": "timeout",
  "reason": "query exceeded the 10s execution limit"
}
```

## Failure modes NOT exposed through this contract

Anything below never reaches the LLM-visible output at all — these are Constitution Principle 7
(Credential Isolation) requirements:
- Database connection strings, credentials, or internal file paths
- Raw database driver exceptions/stack traces (translated into the `denied`/`timeout` shapes
  above instead, per the Edge Cases in spec.md)
