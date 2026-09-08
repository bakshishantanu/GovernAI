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
 * Read directly off the live policy engine (domain/policies/engine.py): the
 * rule loop only branches on `sql_blocklist`. Every other type is a real,
 * storable, toggleable database row that changes no outcome. The UI says so
 * rather than implying every rule type is equally live.
 */
export function isEnforced(ruleType: string) {
  return ruleType === "sql_blocklist";
}

export function ruleSummary(rule: PolicyRule): string {
  if (rule.rule_type === "sql_blocklist") {
    const keywords = Array.isArray(rule.config?.keywords) ? (rule.config.keywords as string[]) : [];
    return keywords.length ? `blocks: ${keywords.join(", ")}` : "no keywords configured";
  }
  if (rule.rule_type === "PERMISSION_CHECK") return "the passport's own permission check";
  if (Object.keys(rule.config ?? {}).length === 0) return "no configuration";
  return JSON.stringify(rule.config);
}
