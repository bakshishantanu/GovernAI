"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Bot, FileSearch, Database, Ticket } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { PassportStamp } from "./passport-stamp";
import { lifecycleOf, type Agent } from "./agent-types";

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  sql_query: Database,
};

type Budget = { spend_usd: number; cap_usd: number; percent_of_cap: number };

function money(n: number) {
  if (n === 0) return "$0.00";
  return n >= 0.01 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}

/**
 * One agent, drawn as an identity document rather than a table row —
 * GovernAI's real object of record IS a Passport, so the card commits to
 * that literally: an id strip, a photo-less "holder" block, a rotated
 * rubber stamp for lifecycle state (passport-stamp.tsx), skill chips as
 * the visa-page stamps of what it may do, and a live budget strip.
 */
export function PassportCard({
  agent,
  budget,
  index,
}: {
  agent: Agent;
  budget?: Budget;
  index: number;
}) {
  const still = useReducedMotion();
  const lc = lifecycleOf(agent);
  const isLive = agent.passport.lifecycle_state === "ACTIVE";

  return (
    <motion.div
      initial={{ opacity: 0, y: 24, rotate: still ? 0 : index % 2 === 0 ? -1.5 : 1.5 }}
      animate={{ opacity: 1, y: 0, rotate: 0 }}
      transition={{ duration: 0.4, delay: index * 0.07, ease: "easeOut" }}
      whileHover={still ? undefined : { y: -6, rotate: index % 2 === 0 ? -0.6 : 0.6 }}
      className="relative"
    >
      <Link
        href={`/agents/${agent.id}`}
        className="relative block overflow-hidden rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] shadow-[0_6px_0_0_rgba(22,19,14,0.16)] transition-shadow hover:shadow-[0_10px_0_0_rgba(22,19,14,0.2)]"
      >
        <PassportStamp agent={agent} delay={0.15 + index * 0.07} />

        {/* id strip */}
        <div className="flex items-center justify-between border-b-2 border-dashed border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/60 px-4 py-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--l-charcoal)]/50">
            Agent passport
          </span>
          <span className="font-mono text-[10px] text-[var(--l-charcoal)]/40">
            {agent.id.slice(0, 8)}
          </span>
        </div>

        <div className="p-4 pt-3.5">
          <div className="flex items-center gap-1.5">
            {isLive && (
              <span className="relative flex h-1.5 w-1.5 shrink-0">
                {!still && (
                  <motion.span
                    className="absolute inset-0 rounded-full bg-[var(--l-teal)]"
                    animate={{ opacity: [0.7, 0, 0.7], scale: [1, 2.2, 1] }}
                    transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
                  />
                )}
                <span className="relative h-1.5 w-1.5 rounded-full bg-[var(--l-teal)]" />
              </span>
            )}
            <h3 className="landing-display truncate text-[17px] leading-tight text-[var(--l-ink)]">
              {agent.name}
            </h3>
          </div>

          <p className="mt-1.5 line-clamp-2 text-[12px] leading-relaxed text-[var(--l-charcoal)]/65">
            {agent.description || "No description on file."}
          </p>

          {/* the visa page — skills bound */}
          <div className="mt-3 flex flex-wrap gap-1">
            {agent.skills.length === 0 ? (
              <span className="font-mono text-[10.5px] text-[var(--l-charcoal)]/40">
                no skills bound
              </span>
            ) : (
              agent.skills.map((s) => {
                const Icon = SKILL_ICON[s.id] ?? Bot;
                return (
                  <span
                    key={s.id}
                    title={s.name}
                    className="flex h-6 w-6 items-center justify-center rounded-md border border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]"
                  >
                    <Icon className="h-3 w-3 text-[var(--l-charcoal)]/70" />
                  </span>
                );
              })
            )}
          </div>

          {/* budget strip */}
          {budget && (
            <div className="mt-3">
              <div className="flex items-baseline justify-between font-mono text-[10px] text-[var(--l-charcoal)]/55">
                <span>{money(budget.spend_usd)}</span>
                <span>{money(budget.cap_usd)} cap</span>
              </div>
              <div className="mt-1 h-[5px] w-full overflow-hidden rounded-full bg-[var(--l-ink)]/10">
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    background:
                      budget.percent_of_cap >= 90 ? "var(--l-orange)" : "var(--l-teal)",
                  }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, budget.percent_of_cap)}%` }}
                  transition={{ duration: 0.5, delay: 0.3 + index * 0.07, ease: "easeOut" }}
                />
              </div>
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  );
}
