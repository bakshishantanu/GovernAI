"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { fetchApi } from "@/lib/api-client";
import { CostHero } from "./_components/cost-hero";
import { SpendBreakdown } from "./_components/spend-breakdown";
import { BudgetLedger } from "./_components/budget-ledger";
import { CostReceiptFeed } from "./_components/cost-receipt-feed";
import type { CostEvent, CostSummary, BudgetStatus } from "./_components/cost-types";

type Agent = { id: string; name: string };

/**
 * Costs, drawn as a ledger rather than a dashboard widget — this is the
 * platform's headline feature (every dollar an agent spends, governed live),
 * so it gets its own register: a receipt-style call feed, ranked spend by
 * agent and by model, and the 24h caps that actually enforce the budget.
 */
export default function CostsPage() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [events, setEvents] = useState<CostEvent[] | null>(null);
  const [agents, setAgents] = useState<Agent[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/costs/summary")
      .then((d) => !cancelled && setSummary(d))
      .catch(() => !cancelled && setSummary(null));
    fetchApi("/costs/budget")
      .then((d) => !cancelled && setBudget(d))
      .catch(() => !cancelled && setBudget(null));
    fetchApi("/costs/?limit=100")
      .then((d) => !cancelled && setEvents(d ?? []))
      .catch(() => !cancelled && setEvents([]));
    fetchApi("/agents/")
      .then((d) => !cancelled && setAgents(d ?? []))
      .catch(() => !cancelled && setAgents([]));
    return () => {
      cancelled = true;
    };
  }, []);

  const nameOf = useMemo(() => {
    const map = new Map((agents ?? []).map((a) => [a.id, a.name]));
    return (id: string) => map.get(id) ?? `${id.slice(0, 8)}…`;
  }, [agents]);

  const byAgentRows = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_agent)
      .map(([id, value]) => ({ label: nameOf(id), value }))
      .sort((a, b) => b.value - a.value);
  }, [summary, nameOf]);

  const byModelRows = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_model)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
  }, [summary]);

  const nearCapCount = budget ? budget.agents.filter((a) => a.suspended || a.percent_of_cap >= 90).length : null;

  const loading = summary === null || budget === null;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <h1 className="landing-display text-3xl text-[var(--l-ink)]">Costs</h1>
        <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
          Every dollar an agent has spent, and the <strong className="text-[var(--l-ink)]">live caps</strong>{" "}
          keeping the next one in check.
        </p>
      </motion.div>

      <CostHero
        totalAllTime={summary?.total_cost_usd ?? null}
        window24h={budget?.total_spend_usd ?? null}
        nearCapCount={nearCapCount}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SpendBreakdown title="Spend by agent" rows={byAgentRows} loading={loading} />
            <SpendBreakdown title="Spend by model" rows={byModelRows} loading={loading} />
          </div>
          <BudgetLedger agents={budget?.agents ?? []} loading={loading} />
        </div>
        <div>
          <CostReceiptFeed events={events ?? []} agentName={nameOf} loading={events === null} />
        </div>
      </div>
    </div>
  );
}
