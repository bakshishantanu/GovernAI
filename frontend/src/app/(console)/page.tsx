"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bot, ShieldAlert, Wallet } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { StatTile } from "./_components/stat-tile";
import { RecentActivity, type AuditEvent } from "./_components/recent-activity";
import { BudgetBreakdown, type AgentBudget } from "./_components/budget-breakdown";

type Agent = {
  id: string;
  name: string;
  status: string;
  passport: { lifecycle_state: string };
};

type BudgetStatus = {
  cap_usd: number;
  total_spend_usd: number;
  agents: AgentBudget[];
};

function money(n: number) {
  // Sub-cent spend rounds to $0.00 with two decimals, which reads as "free"
  // when it isn't — show four decimals only for genuinely nonzero sub-cent
  // amounts, never for a true zero.
  if (n === 0) return "$0.00";
  return n >= 0.01 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}

/**
 * Dashboard.
 *
 * Three real sources, no invented numbers:
 *  - GET /agents/        -> active-agent count, and names for the feed
 *  - GET /audits/        -> recent activity + the denied-call count
 *  - GET /costs/budget   -> spend total and the per-agent breakdown
 *
 * GET /costs/summary — the endpoint the spec names for a dashboard summary
 * — returns a live 500 right now (see DECISIONS.md). Rather than build
 * against a broken endpoint, the spend figures come from /costs/budget,
 * which already works and already backs the sidebar's own budget meter.
 */
export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [audits, setAudits] = useState<AuditEvent[] | null>(null);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      fetchApi("/agents/"),
      fetchApi("/audits/?limit=50"),
      fetchApi("/costs/budget"),
    ])
      .then(([agentsData, auditsData, budgetData]) => {
        if (cancelled) return;
        setAgents(agentsData ?? []);
        setAudits(auditsData ?? []);
        setBudget(budgetData ?? null);
      })
      .catch(() => {
        if (!cancelled) {
          setAgents([]);
          setAudits([]);
          setBudget(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const loading = agents === null || audits === null || budget === null;
  const activeCount = agents?.filter((a) => a.passport.lifecycle_state === "ACTIVE").length ?? 0;
  const deniedCount = audits?.filter((e) => e.policy_decision === "DENY").length ?? 0;
  const agentNames = new Map((agents ?? []).map((a) => [a.id, a.name]));

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="landing-display text-3xl text-[var(--l-ink)]">Overview</h1>
        <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
          Metrics and recent activity across your organisation.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatTile
          icon={Bot}
          label="Active agents"
          value={String(activeCount)}
          tint="var(--l-teal)"
          loading={loading}
        />
        <StatTile
          icon={ShieldAlert}
          label="Policy blocks"
          value={String(deniedCount)}
          tint="var(--l-orange)"
          loading={loading}
        />
        <StatTile
          icon={Wallet}
          label="Spend"
          value={budget ? `${money(budget.total_spend_usd)} / ${money(budget.cap_usd)}` : "—"}
          tint="var(--l-orange-deep)"
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RecentActivity events={audits ?? []} agentNames={agentNames} loading={loading} />
        <BudgetBreakdown agents={budget?.agents ?? []} loading={loading} />
      </div>
    </div>
  );
}
