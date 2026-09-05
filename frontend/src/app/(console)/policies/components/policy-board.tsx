"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { BoardPanel, ViewTabs, ToolbarChip } from "@/components/board/board-panel";
import { ShieldCheck, ShieldOff } from "lucide-react";

/**
 * Policies and their rules, with the rule switch that FRD-14 is measured on:
 * turn a rule off and the same tool call that was refused a moment ago goes
 * through, with no restart. Rules are database rows, so the engine picks the
 * change up on its next evaluation.
 *
 * Toggling is an admin action — `PATCH /policies/{id}/rules/{id}` sits behind
 * `require_admin`. A member gets a 403 and is told so rather than seeing the
 * switch silently snap back.
 *
 * The switch updates optimistically because a governance control that lags
 * feels broken; a failure puts it back and shows why.
 */

type Rule = {
  id: string;
  policy_id: string;
  name: string;
  rule_type: string;
  config: Record<string, any>;
  priority: number;
  enabled: boolean;
};

type Policy = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  rules?: Rule[] | null;
};

export function PolicyBoard() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const list: Policy[] = await fetchApi("/policies/");
      const policyList = Array.isArray(list) ? list : [];

      // The list route does not embed rules, so each policy's rules are
      // fetched alongside it. There are a handful of policies, not thousands.
      const withRules = await Promise.all(
        policyList.map(async (policy) => {
          try {
            const rules = await fetchApi(`/policies/${policy.id}/rules`);
            return { ...policy, rules: Array.isArray(rules) ? rules : [] };
          } catch {
            return { ...policy, rules: [] };
          }
        }),
      );
      setPolicies(withRules);
    } catch (err: any) {
      setError(err.message || "Could not load policies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleRule = async (policyId: string, rule: Rule) => {
    const next = !rule.enabled;
    setPending(rule.id);
    setToggleError(null);

    setPolicies((current) =>
      current.map((policy) =>
        policy.id !== policyId
          ? policy
          : {
              ...policy,
              rules: policy.rules?.map((r) => (r.id === rule.id ? { ...r, enabled: next } : r)),
            },
      ),
    );

    try {
      await fetchApi(`/policies/${policyId}/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: next }),
      });
    } catch (err: any) {
      // Put it back — the rule did not actually change.
      setPolicies((current) =>
        current.map((policy) =>
          policy.id !== policyId
            ? policy
            : {
                ...policy,
                rules: policy.rules?.map((r) =>
                  r.id === rule.id ? { ...r, enabled: rule.enabled } : r,
                ),
              },
        ),
      );
      setToggleError(err.message || "That rule could not be changed.");
    } finally {
      setPending(null);
    }
  };

  const ruleCount = policies.reduce((sum, policy) => sum + (policy.rules?.length ?? 0), 0);
  const activeRules = policies.reduce(
    (sum, policy) => sum + (policy.rules?.filter((r) => r.enabled).length ?? 0),
    0,
  );

  return (
    <>
      <ViewTabs views={[{ name: "Rules", icon: "compliance" }]} active="Rules" />

      <BoardPanel
        toolbar={
          <>
            <ToolbarChip>{policies.length} policies</ToolbarChip>
            <ToolbarChip active={activeRules > 0}>
              {activeRules} of {ruleCount} rules on
            </ToolbarChip>
          </>
        }
      >
        {error && (
          <div role="alert" className="px-4 py-6 text-[13px] font-extrabold text-gv-held">
            {error}
          </div>
        )}

        {toggleError && (
          <div
            role="alert"
            className="m-4 rounded-lg border-2 border-gv-held bg-gv-held/10 p-3 text-[13px] font-extrabold text-gv-held-fg"
          >
            {toggleError}
          </div>
        )}

        {!error && loading && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">Loading policies…</p>
        )}

        {!error && !loading && policies.length === 0 && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">
            No policies defined. Every tool call is still checked against the agent&apos;s
            passport — policies add rules on top of that.
          </p>
        )}

        <div className="flex flex-col gap-4 p-4">
          {policies.map((policy) => (
            <section
              key={policy.id}
              className="gv-card overflow-hidden rounded-lg border-2 border-border bg-gv-row"
            >
              <header className="flex min-h-12 items-center gap-3 border-b-2 border-border px-4 py-2">
                <div className="min-w-0 flex-1">
                  <h2 className="truncate font-display text-[19px] leading-none text-gv-ink">
                    {policy.name}
                  </h2>
                  <p className="mt-1 text-[12.5px] font-semibold text-gv-body">
                    {policy.description}
                  </p>
                </div>
                <span
                  className={`inline-flex h-[22px] shrink-0 items-center rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${
                    policy.enabled
                      ? "bg-gv-cleared text-gv-cleared-fg"
                      : "bg-gv-draft text-gv-draft-fg"
                  }`}
                >
                  {policy.enabled ? "Enforced" : "Off"}
                </span>
              </header>

              {policy.rules && policy.rules.length > 0 ? (
                <ul className="divide-y divide-gv-rule/40">
                  {[...policy.rules]
                    .sort((a, b) => a.priority - b.priority)
                    .map((rule) => (
                      <li key={rule.id} className="flex items-center gap-3 px-4 py-2.5">
                        <span className="w-[52px] shrink-0 font-mono text-[11px] text-gv-muted">
                          #{rule.priority}
                        </span>

                        <span className="min-w-0 flex-1">
                          <span className="block text-[12.5px] font-extrabold text-foreground">
                            {rule.name}
                          </span>
                          <span className="block font-mono text-[11px] text-gv-muted">
                            {rule.rule_type}
                          </span>
                        </span>

                        <button
                          type="button"
                          onClick={() => pending !== rule.id && toggleRule(policy.id, rule)}
                          disabled={pending === rule.id}
                          aria-pressed={rule.enabled}
                          className={`inline-flex h-8 shrink-0 items-center gap-1.5 rounded-xl border-2 border-border px-3 text-[12px] font-extrabold uppercase tracking-[0.06em] transition-transform active:translate-x-px active:translate-y-px disabled:opacity-60 ${
                            rule.enabled
                              ? "gv-chip bg-gv-cleared text-gv-cleared-fg"
                              : "bg-gv-draft text-gv-draft-fg"
                          }`}
                        >
                          {rule.enabled ? (
                            <ShieldCheck className="h-3.5 w-3.5" strokeWidth={2.6} />
                          ) : (
                            <ShieldOff className="h-3.5 w-3.5" strokeWidth={2.6} />
                          )}
                          {rule.enabled ? "On" : "Off"}
                        </button>
                      </li>
                    ))}
                </ul>
              ) : (
                <p className="px-4 py-4 text-[13px] font-bold text-gv-muted">
                  This policy has no rules yet.
                </p>
              )}
            </section>
          ))}
        </div>
      </BoardPanel>
    </>
  );
}
