"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Bot, Ticket, FileSearch, Database } from "lucide-react";
import type { LucideIcon } from "lucide-react";

type Agent = {
  id: string;
  name: string;
  status: string;
  passport: { lifecycle_state: string };
  skills: { id: string; name: string }[];
};

type AgentBudget = { agent_id: string; spend_usd: number; cap_usd: number };

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  solr_search: Search,
  sql_query: Database,
};

const STATUS_STYLE: Record<string, { bg: string; fg: string; label: string }> = {
  ACTIVE: { bg: "var(--l-teal)", fg: "#ffffff", label: "Active" },
  APPROVED: { bg: "var(--l-teal-soft)", fg: "var(--l-ink)", label: "Approved" },
  DRAFT: { bg: "var(--l-cream-deep)", fg: "var(--l-charcoal)", label: "Draft" },
  SUSPENDED: { bg: "var(--l-orange)", fg: "#ffffff", label: "Suspended" },
  REVOKED: { bg: "var(--l-ink)", fg: "var(--l-cream)", label: "Revoked" },
};

function money(n: number) {
  if (n === 0) return "$0.00";
  return n >= 0.01 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}

/**
 * Real agents as cards, filtered by real search and status — the structural
 * equivalent of the reference's listings grid, mapped onto agents instead
 * of properties. Each card's icon reflects its first bound skill so the
 * grid reads at a glance rather than as identical grey tiles.
 */
export function AgentGrid({
  agents,
  budgets,
  loading,
}: {
  agents: Agent[];
  budgets: Map<string, AgentBudget>;
  loading?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const statuses = useMemo(
    () => Array.from(new Set(agents.map((a) => a.passport.lifecycle_state))),
    [agents],
  );

  const filtered = agents.filter((a) => {
    const matchesQuery = a.name.toLowerCase().includes(query.toLowerCase());
    const matchesStatus = statusFilter === "all" || a.passport.lifecycle_state === statusFilter;
    return matchesQuery && matchesStatus;
  });

  return (
    <div className="rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream)] p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <span className="landing-display text-lg text-[var(--l-ink)]">Agents</span>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex h-9 items-center gap-2 rounded-full border border-[var(--l-line)] bg-[var(--l-cream-deep)]/50 px-3">
            <Search className="h-3.5 w-3.5 text-[var(--l-charcoal)]/50" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search agents"
              className="w-32 bg-transparent text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/40 focus:outline-none"
            />
          </label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 rounded-full border border-[var(--l-line)] bg-[var(--l-cream-deep)]/50 px-3 text-sm text-[var(--l-ink)] focus:outline-none"
          >
            <option value="all">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {STATUS_STYLE[s]?.label ?? s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-[var(--l-line)]/60" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--l-charcoal)]/60">
          {agents.length === 0 ? "No agents yet." : "No agents match this search."}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence mode="popLayout">
            {filtered.map((a, i) => {
              const style = STATUS_STYLE[a.passport.lifecycle_state] ?? STATUS_STYLE.DRAFT;
              const Icon = SKILL_ICON[a.skills[0]?.id] ?? Bot;
              const budget = budgets.get(a.id);
              return (
                <motion.div
                  key={a.id}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.04 }}
                  whileHover={{ y: -3 }}
                >
                  <Link
                    href={`/agents/${a.id}`}
                    className="block h-full rounded-xl border border-[var(--l-line)] bg-[var(--l-cream-deep)]/40 p-4 transition-colors hover:bg-[var(--l-cream-deep)]"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--l-orange)]/15">
                        <Icon className="h-4 w-4 text-[var(--l-orange-deep)]" />
                      </div>
                      <span
                        className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                        style={{ background: style.bg, color: style.fg }}
                      >
                        {style.label}
                      </span>
                    </div>
                    <p className="mt-3 truncate text-sm font-semibold text-[var(--l-ink)]">
                      {a.name}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-[var(--l-charcoal)]/55">
                      {a.skills.map((s) => s.name).join(", ") || "No skills bound"}
                    </p>
                    {budget && (
                      <p className="mt-2 font-mono text-[11px] text-[var(--l-charcoal)]/60">
                        {money(budget.spend_usd)} / {money(budget.cap_usd)}
                      </p>
                    )}
                  </Link>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
