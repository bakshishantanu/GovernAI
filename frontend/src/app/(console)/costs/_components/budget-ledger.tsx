"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { OctagonX } from "lucide-react";
import { money, type AgentBudget } from "./cost-types";

/** Every agent's live 24h cap, the thing that actually stops a runaway bill. */
export function BudgetLedger({ agents, loading }: { agents: AgentBudget[]; loading: boolean }) {
  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]">
      <div className="flex items-baseline justify-between">
        <h2 className="landing-display text-base text-[var(--l-ink)]">24h budget caps</h2>
        <span className="font-mono text-[10.5px] text-[var(--l-charcoal)]/45">
          enforced live, not advisory
        </span>
      </div>

      <div className="mt-3 space-y-3">
        {loading ? (
          [0, 1, 2].map((i) => <div key={i} className="h-12 animate-pulse rounded-xl bg-[var(--l-line)]/50" />)
        ) : agents.length === 0 ? (
          <p className="py-4 text-center text-[12.5px] text-[var(--l-charcoal)]/50">No agents yet.</p>
        ) : (
          agents.map((a, i) => {
            const danger = a.suspended || a.percent_of_cap >= 90;
            return (
              <motion.div
                key={a.agent_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
              >
                <Link href={`/agents/${a.agent_id}`} className="block">
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 truncate text-[12.5px] font-medium text-[var(--l-ink)]">
                      {a.suspended && <OctagonX className="h-3 w-3 shrink-0" style={{ color: "#8a1f1f" }} />}
                      {a.name}
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-[var(--l-charcoal)]/60">
                      {money(a.spend_usd)} / {money(a.cap_usd)}
                    </span>
                  </div>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[var(--l-ink)]/8">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: a.suspended ? "#8a1f1f" : danger ? "var(--l-orange-deep)" : "var(--l-teal)" }}
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, a.percent_of_cap)}%` }}
                      transition={{ duration: 0.6, delay: 0.15 + i * 0.05, ease: "easeOut" }}
                    />
                  </div>
                </Link>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
