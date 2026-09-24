export type PolicyRule = {
  id: string;
  policy_id: string;
  name: string;
  rule_type: string;
  config: Record<string, unknown>;
  priority: number;
  enabled: boolean;
};

export type Policy = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  rules: PolicyRule[] | null;
};

/**
 * The rule types the live policy engine (domain/policies/engine.py) actually
 * branches on, lowercased because the engine matches rule types
 * case-insensitively (the API stores `DENY_LIST`, the engine compares
 * `deny_list`). Keep this in step with the engine's rule loop: the console
 * must never call a rule enforced when it changes no outcome, or the reverse.
 *
 * `sql_blocklist` is deliberately absent. The engine only applies it to the
 * `sql_query` tool, which was replaced by the Solr skill, so a row of that
 * type is stored but can no longer block anything.
 */
const ENFORCED_RULE_TYPES = new Set([
  "deny_list",
  "rate_limit",
  "solr_query_blocklist",
  "brand_color_check",
]);

export function isEnforced(ruleType: string) {
  return ENFORCED_RULE_TYPES.has(ruleType.trim().toLowerCase());
}

/** Why a rule that is stored changes no outcome, for the badge's tooltip. */
export function notEnforcedReason(ruleType: string): string {
  switch (ruleType.trim().toLowerCase()) {
    case "sql_blocklist":
      return "Only applies to the SQL query tool, which no longer exists — this rule blocks nothing";
    case "permission_check":
      return "The engine checks the passport's permissions on every call anyway — this rule adds nothing";
    default:
      return "Stored, but the engine doesn't branch on this rule type";
  }
}

function list(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export function ruleSummary(rule: PolicyRule): string {
  const config = rule.config ?? {};
  switch (rule.rule_type.trim().toLowerCase()) {
    case "deny_list": {
      const tools = list(config.blocked_tools);
      const args = list(config.blocked_args);
      if (tools.length && args.length) {
        return `blocks ${tools.join(", ")} when called with: ${args.join(", ")}`;
      }
      if (tools.length) return `blocks tools: ${tools.join(", ")}`;
      if (args.length) return `blocks any tool call mentioning: ${args.join(", ")}`;
      return "no tools or words configured";
    }
    case "rate_limit": {
      const max = config.max_calls_per_minute;
      return max ? `at most ${max} tool calls per minute, per agent` : "no limit configured";
    }
    case "solr_query_blocklist":
    case "sql_blocklist": {
      const keywords = list(config.keywords);
      return keywords.length ? `blocks queries containing: ${keywords.join(", ")}` : "no keywords configured";
    }
    case "brand_color_check": {
      const colours = list(config.allowed_hex_codes);
      return colours.length ? `approved colours: ${colours.join(", ")}` : "no palette configured";
    }
    case "permission_check":
      return "the passport's own permission check";
  }
  if (Object.keys(config).length === 0) return "no configuration";
  return JSON.stringify(config);
}
