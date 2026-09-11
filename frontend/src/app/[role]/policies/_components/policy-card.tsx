"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { RuleToggle } from "./rule-toggle";
import { isEnforced, ruleSummary, type Policy, type PolicyRule } from "./policy-types";

/**
 * One policy as an open rulebook page: a title clause, a master switch, and
 * every rule underneath as a numbered statute — priority first, since that's
 * the order the engine actually reads them in.
 */
export function PolicyCard({
  policy,
  index,
  isAdmin,
  onChanged,
}: {
  policy: Policy;
  index: number;
  isAdmin: boolean;
  onChanged: (policy: Policy) => void;
}) {
  const [busyPolicy, setBusyPolicy] = useState(false);
  const [busyRule, setBusyRule] = useState<string | null>(null);
  const rules = [...(policy.rules ?? [])].sort((a, b) => a.priority - b.priority);

  async function togglePolicy() {
    setBusyPolicy(true);
    try {
      const updated = await fetchApi(`/policies/${policy.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !policy.enabled }),
      });
      onChanged(updated);
    } catch {
      // leave the switch where it was — the toggle itself only moves on success
    } finally {
      setBusyPolicy(false);
    }
  }

  async function toggleRule(rule: PolicyRule) {
    setBusyRule(rule.id);
    try {
      const updatedRule = await fetchApi(`/policies/${policy.id}/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !rule.enabled }),
      });
      onChanged({
        ...policy,
        rules: rules.map((r) => (r.id === rule.id ? updatedRule : r)),
      });
    } catch {
      // no-op — the rule stays as it was
    } finally {
      setBusyRule(null);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.06 }}
      className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
      style={{ opacity: policy.enabled ? 1 : 0.55 }}
    >
      <div className="flex items-start justify-between gap-4 border-b-2 border-dashed border-[var(--l-ink)]/15 p-5">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--l-charcoal)]/45">
            Policy {String(index + 1).padStart(2, "0")}
          </span>
          <h2 className="landing-display mt-0.5 text-lg text-[var(--l-ink)]">{policy.name}</h2>
          <p className="mt-1 max-w-md text-[12.5px] text-[var(--l-charcoal)]/60">{policy.description}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {busyPolicy && <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--l-charcoal)]/40" />}
          <RuleToggle on={policy.enabled} onChange={togglePolicy} disabled={!isAdmin || busyPolicy} size="lg" />
        </div>
      </div>

      <div className="divide-y divide-dashed divide-[var(--l-ink)]/12 px-5">
        {rules.length === 0 ? (
          <p className="py-6 text-center text-[12.5px] text-[var(--l-charcoal)]/50">No rules in this policy.</p>
        ) : (
          rules.map((rule) => {
            const enforced = isEnforced(rule.rule_type);
            return (
              <div key={rule.id} className="flex items-center gap-3 py-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-[var(--l-ink)]/15 font-mono text-[10px] text-[var(--l-charcoal)]/60">
                  {rule.priority}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[13px] font-medium text-[var(--l-ink)]">{rule.name}</span>
                    <span className="rounded-full border border-[var(--l-ink)]/12 px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-wide text-[var(--l-charcoal)]/55">
                      {rule.rule_type}
                    </span>
                    <span
                      className="flex items-center gap-1 font-mono text-[9.5px] uppercase tracking-wide"
                      style={{ color: enforced ? "var(--l-teal)" : "var(--l-charcoal)" }}
                      title={enforced ? "The engine enforces this rule type" : "Stored, but the engine doesn't branch on this rule type yet"}
                    >
                      <span
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ background: enforced ? "var(--l-teal)" : "var(--l-charcoal)", opacity: enforced ? 1 : 0.4 }}
                      />
                      {enforced ? "enforced" : "not wired up"}
                    </span>
                  </span>
                  <span className="mt-0.5 block truncate font-mono text-[11px] text-[var(--l-charcoal)]/50">
                    {ruleSummary(rule)}
                  </span>
                </span>
                <div className="flex shrink-0 items-center gap-2">
                  {busyRule === rule.id && <Loader2 className="h-3 w-3 animate-spin text-[var(--l-charcoal)]/40" />}
                  <RuleToggle on={rule.enabled} onChange={() => toggleRule(rule)} disabled={!isAdmin || busyRule === rule.id} />
                </div>
              </div>
            );
          })
        )}
      </div>

      {!isAdmin && (
        <p className="border-t border-dashed border-[var(--l-ink)]/12 px-5 py-2.5 text-center font-mono text-[10.5px] text-[var(--l-charcoal)]/40">
          admin only: you can see the rulebook, not change it
        </p>
      )}
    </motion.div>
  );
}
