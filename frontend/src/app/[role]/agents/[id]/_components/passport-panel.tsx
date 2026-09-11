"use client";

import { motion } from "framer-motion";
import { Bot, FileSearch, Database, Ticket, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { money, type Agent, type Budget } from "../../_components/agent-types";

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  solr_search: Search,
  sql_query: Database,
};

/** The visa pages: what this passport was actually issued to do, and what it's spent doing it. */
export function PassportPanel({ agent, budget }: { agent: Agent; budget?: Budget }) {
  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_4px_0_0_rgba(22,19,14,0.12)]">
      <h2 className="landing-display text-base text-[var(--l-ink)]">Skills bound</h2>
      <div className="mt-3 space-y-2">
        {agent.skills.length === 0 ? (
          <p className="text-[12.5px] text-[var(--l-charcoal)]/50">No skills bound.</p>
        ) : (
          agent.skills.map((s) => {
            const Icon = SKILL_ICON[s.id] ?? Bot;
            return (
              <div key={s.id} className="flex items-center gap-2.5 rounded-xl bg-[var(--l-cream-deep)]/50 px-3 py-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream)]">
                  <Icon className="h-3.5 w-3.5 text-[var(--l-charcoal)]/70" />
                </span>
                <span className="text-[13px] font-medium text-[var(--l-ink)]">{s.name}</span>
              </div>
            );
          })
        )}
      </div>

      <h2 className="landing-display mt-5 text-base text-[var(--l-ink)]">Permissions granted</h2>
      <p className="mt-0.5 font-mono text-[10.5px] text-[var(--l-charcoal)]/45">
        derived from skills, never hand-picked
      </p>
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {agent.passport.permissions.length === 0 ? (
          <p className="text-[12.5px] text-[var(--l-charcoal)]/50">None yet.</p>
        ) : (
          agent.passport.permissions.map((p) => (
            <span
              key={p}
              className="rounded-full border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/60 px-2.5 py-1 font-mono text-[10.5px] text-[var(--l-charcoal)]/75"
            >
              {p}
            </span>
          ))
        )}
      </div>

      {budget && (
        <>
          <h2 className="landing-display mt-5 text-base text-[var(--l-ink)]">24h budget</h2>
          <div className="mt-2 flex items-baseline justify-between font-mono text-[11px] text-[var(--l-charcoal)]/60">
            <span>{money(budget.spend_usd)} spent</span>
            <span>{money(budget.cap_usd)} cap</span>
          </div>
          <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-[var(--l-ink)]/10">
            <motion.div
              className="h-full rounded-full"
              style={{ background: budget.percent_of_cap >= 90 ? "var(--l-orange)" : "var(--l-teal)" }}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, budget.percent_of_cap)}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
        </>
      )}
    </div>
  );
}
