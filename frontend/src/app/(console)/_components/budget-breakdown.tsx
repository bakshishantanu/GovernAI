"use client";

import { motion } from "framer-motion";

export type AgentBudget = {
  agent_id: string;
  name: string;
  spend_usd: number;
  cap_usd: number;
  percent_of_cap: number;
  suspended: boolean;
};

function money(n: number) {
  if (n === 0) return "$0.00";
  return n >= 0.01 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}

/**
 * Per-agent spend against cap, from GET /costs/budget — the same figures
 * the sidebar's own budget meter draws from, so nothing here can disagree
 * with what the rest of the console already shows. Stands in for the
 * broken GET /costs/summary (500 right now — see DECISIONS.md) rather than
 * waiting on a backend fix to ship real numbers.
 */
export function BudgetBreakdown({
  agents,
  loading,
}: {
  agents: AgentBudget[];
  loading: boolean;
}) {
  return (
    <div className="rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream-deep)]/50">
      <div className="flex items-center justify-between border-b border-[var(--l-line)] px-5 py-4">
        <span className="landing-display text-lg text-[var(--l-ink)]">Spend by agent</span>
        <span className="text-xs text-[var(--l-charcoal)]/50">against each agent&apos;s cap</span>
      </div>

      {loading ? (
        <div className="space-y-3 p-5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-lg bg-[var(--l-line)]/60" />
          ))}
        </div>
      ) : agents.length === 0 ? (
        <p className="p-6 text-sm text-[var(--l-charcoal)]/60">No agents yet.</p>
      ) : (
        <ul className="space-y-4 p-5">
          {agents.map((a, i) => {
            const pct = Math.min(100, a.percent_of_cap);
            const hot = pct >= 90 || a.suspended;
            return (
              <motion.li
                key={a.agent_id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
              >
                <div className="mb-1.5 flex items-baseline justify-between text-sm">
                  <span className="truncate font-medium text-[var(--l-ink)]">{a.name}</span>
                  <span className="shrink-0 font-mono text-xs text-[var(--l-charcoal)]/60">
                    {money(a.spend_usd)} / {money(a.cap_usd)}
                    {a.suspended && (
                      <span className="ml-2 text-[var(--l-orange-deep)]">suspended</span>
                    )}
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--l-line)]">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.5, delay: 0.1 + i * 0.05, ease: "easeOut" }}
                    className="h-full rounded-full"
                    style={{ background: hot ? "var(--l-orange)" : "var(--l-teal)" }}
                  />
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
