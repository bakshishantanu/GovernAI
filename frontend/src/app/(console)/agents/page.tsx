"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PassportCard } from "./_components/passport-card";
import { NewAgentTile } from "./_components/new-agent-tile";
import { CreateAgentModal } from "./_components/create-agent-modal";
import { RosterControls, type RosterFilter } from "./_components/roster-controls";
import type { Agent } from "./_components/agent-types";
import type { UserRole } from "@/lib/types";

type AgentBudget = { agent_id: string; spend_usd: number; cap_usd: number; percent_of_cap: number };
type BudgetStatus = { agents: AgentBudget[] };

const STATE_FOR_FILTER: Record<Exclude<RosterFilter, "All">, string> = {
  Active: "ACTIVE",
  Draft: "DRAFT",
  Suspended: "SUSPENDED",
  Revoked: "REVOKED",
};

const TITLE: Record<UserRole, string> = {
  admin: "All agents",
  agent_builder: "My builds",
  user: "My agents",
};

const DESCRIPTION: Record<UserRole, string> = {
  admin:
    "Every agent in the organisation. Each carries a passport — a stamped record of what it may do, and who let it.",
  agent_builder:
    "Agents you have built. Each carries a passport — a stamped record of what it may do, and who let it.",
  user: "Agents built for you and handed over, ready to run.",
};

const EMPTY_TITLE: Record<UserRole, string> = {
  admin: "No passports match",
  agent_builder: "No passports match",
  user: "No agents yet",
};

const EMPTY_BODY: Record<UserRole, string> = {
  admin: "Try a different search or filter — or issue a new one.",
  agent_builder: "Try a different search or filter — or issue a new one.",
  user: "Ask for one and a builder will put it together for you.",
};

/**
 * The roster, drawn as a passport office rather than a table: every agent
 * is an identity document (passport-card.tsx), and issuing a new one opens
 * the same two-step flow the backend actually runs — draft, then submit
 * for a real compliance check (create-agent-modal.tsx).
 */
export default function AgentsPage() {
  const { role, isUser } = useAuth();
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
          <h1 className="landing-display text-3xl text-[var(--l-ink)]">{TITLE[role]}</h1>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">{DESCRIPTION[role]}</p>
        </motion.div>
        <div className="flex items-center gap-3">
          <RosterControls query={query} onQuery={setQuery} filter={filter} onFilter={setFilter} counts={counts} />
          {isUser && (
            <Link
              href="/request-agent"
              className="inline-flex h-10 shrink-0 items-center gap-2 rounded-full bg-[var(--l-orange)] px-4 text-sm font-medium text-white transition-colors hover:bg-[var(--l-orange-deep)]"
            >
              <Sparkles className="h-4 w-4" />
              Request an agent
            </Link>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {!isUser && filter === "All" && !query.trim() && (
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
            <p className="landing-display text-lg text-[var(--l-ink)]">{EMPTY_TITLE[role]}</p>
            <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">{EMPTY_BODY[role]}</p>
          </div>
        )}
      </div>

      {!isUser && (
        <CreateAgentModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={refetch} />
      )}
    </div>
  );
}
