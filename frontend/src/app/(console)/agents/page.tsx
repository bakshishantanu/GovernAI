"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { fetchApi } from "@/lib/api-client";
import { PassportCard } from "./_components/passport-card";
import { NewAgentTile } from "./_components/new-agent-tile";
import { CreateAgentModal } from "./_components/create-agent-modal";
import { RosterControls, type RosterFilter } from "./_components/roster-controls";
import type { Agent } from "./_components/agent-types";

type AgentBudget = { agent_id: string; spend_usd: number; cap_usd: number; percent_of_cap: number };
type BudgetStatus = { agents: AgentBudget[] };

const STATE_FOR_FILTER: Record<Exclude<RosterFilter, "All">, string> = {
  Active: "ACTIVE",
  Draft: "DRAFT",
  Suspended: "SUSPENDED",
  Revoked: "REVOKED",
};

/**
 * The roster, drawn as a passport office rather than a table: every agent
 * is an identity document (passport-card.tsx), and issuing a new one opens
 * the same two-step flow the backend actually runs — draft, then submit
 * for a real compliance check (create-agent-modal.tsx).
 */
export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<RosterFilter>("All");
  const [modalOpen, setModalOpen] = useState(false);

  function refetch() {
    fetchApi("/agents/")
      .then((data) => setAgents(data ?? []))
      .catch(() => setAgents([]));
    fetchApi("/costs/budget")
      .then((data) => setBudget(data ?? null))
      .catch(() => setBudget(null));
  }

  useEffect(() => {
    refetch();
  }, []);

  const loading = agents === null;
  const budgetByAgent = useMemo(
    () => new Map((budget?.agents ?? []).map((a) => [a.agent_id, a])),
    [budget]
  );

  const counts = useMemo(() => {
    const c: Record<RosterFilter, number> = { All: agents?.length ?? 0, Active: 0, Draft: 0, Suspended: 0, Revoked: 0 };
    for (const a of agents ?? []) {
      const s = a.passport.lifecycle_state;
      if (s === "ACTIVE") c.Active++;
      else if (s === "DRAFT") c.Draft++;
      else if (s === "SUSPENDED") c.Suspended++;
      else if (s === "REVOKED") c.Revoked++;
    }
    return c;
  }, [agents]);

  const visible = useMemo(() => {
    let list = agents ?? [];
    if (filter !== "All") list = list.filter((a) => a.passport.lifecycle_state === STATE_FOR_FILTER[filter]);
    const q = query.trim().toLowerCase();
    if (q) list = list.filter((a) => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q));
    return list;
  }, [agents, filter, query]);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <h1 className="landing-display text-3xl text-[var(--l-ink)]">Agents</h1>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            Every agent carries a <strong className="text-[var(--l-ink)]">passport</strong> — a
            stamped record of what it may do, and who let it.
          </p>
        </motion.div>
        <RosterControls query={query} onQuery={setQuery} filter={filter} onFilter={setFilter} counts={counts} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {filter === "All" && !query.trim() && (
          <NewAgentTile onClick={() => setModalOpen(true)} index={0} />
        )}

        {loading
          ? [0, 1, 2].map((i) => (
              <div key={i} className="min-h-[236px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40" />
            ))
          : visible.map((agent, i) => (
              <PassportCard key={agent.id} agent={agent} budget={budgetByAgent.get(agent.id)} index={i + 1} />
            ))}

        {!loading && visible.length === 0 && (
          <div className="col-span-full py-16 text-center">
            <p className="landing-display text-lg text-[var(--l-ink)]">No passports match</p>
            <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
              Try a different search or filter — or issue a new one.
            </p>
          </div>
        )}
      </div>

      <CreateAgentModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={refetch} />
    </div>
  );
}
