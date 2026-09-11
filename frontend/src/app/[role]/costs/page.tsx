"use client";

import { useCallback, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { fetchApi } from "@/lib/api-client";
import { useLive } from "@/lib/use-live";
import { timeAgo } from "@/lib/time-ago";
import { CostHero } from "./_components/cost-hero";
import { SpendBreakdown } from "./_components/spend-breakdown";
import { BudgetLedger } from "./_components/budget-ledger";
import { CostReceiptFeed } from "./_components/cost-receipt-feed";
import { WindowPicker } from "./_components/window-picker";
import type { CostEvent, CostSummary, BudgetStatus, CostWindow } from "./_components/cost-types";

type Agent = { id: string; name: string };

const WINDOW_LABEL: Record<CostWindow, string> = {
  "24h": "the last 24 hours",
  "7d": "the last 7 days",
  "30d": "the last 30 days",
  all: "all time",
};

/**
 * Costs, drawn as a ledger rather than a dashboard widget — this is the
 * platform's headline feature (every dollar an agent spends, governed live),
 * so it gets its own register: a receipt-style call feed, ranked spend by
 * agent and by model, and the 24h caps that actually enforce the budget.
 *
 * The hero tiles always report the two canonical, fixed measures (all-time
 * spend and the live enforced 24h window) — a window picker only narrows the
 * breakdown below it, so those two honest numbers never get relabelled into
 * meaning something else.
 */
export default function CostsPage() {
  const [window, setWindow] = useState<CostWindow>("all");

  const load = useCallback(async () => {
    const [allTime, windowed, budget, events, agents] = await Promise.all([
      fetchApi("/costs/summary?window=all").catch(() => null),
      window === "all"
        ? Promise.resolve(null)
        : fetchApi(`/costs/summary?window=${window}`).catch(() => null),
      fetchApi("/costs/budget").catch(() => null),
      fetchApi("/costs/?limit=100").catch(() => []),
      fetchApi("/agents/").catch(() => []),
    ]);
    return {
      allTime: allTime as CostSummary | null,
      windowed: (windowed ?? allTime) as CostSummary | null,
      budget: budget as BudgetStatus | null,
      events: (Array.isArray(events) ? events : []) as CostEvent[],
      agents: (Array.isArray(agents) ? agents : []) as Agent[],
    };
  }, [window]);

  const { data, updatedAt } = useLive(load);
  const allTime = data?.allTime ?? null;
  const windowed = data?.windowed ?? null;
  const budget = data?.budget ?? null;
  const events = data?.events ?? null;
  const agents = data?.agents ?? null;

  const nameOf = useMemo(() => {
    const map = new Map((agents ?? []).map((a) => [a.id, a.name]));
    return (id: string) => map.get(id) ?? `${id.slice(0, 8)}…`;
  }, [agents]);

  const byAgentRows = useMemo(() => {
    if (!windowed) return [];
    return Object.entries(windowed.by_agent)
      .map(([id, value]) => ({ label: nameOf(id), value }))
      .sort((a, b) => b.value - a.value);
  }, [windowed, nameOf]);

  const byModelRows = useMemo(() => {
    if (!windowed) return [];
    return Object.entries(windowed.by_model)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);
  }, [windowed]);

  const nearCapCount = budget ? budget.agents.filter((a) => a.suspended || a.percent_of_cap >= 90).length : null;

  const loading = allTime === null || budget === null;
  const breakdownLoading = windowed === null;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-wrap items-end justify-between gap-4"
      >
        <div>
          <h1 className="landing-display text-3xl text-[var(--l-ink)]">Costs</h1>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            Every dollar an agent has spent, and the <strong className="text-[var(--l-ink)]">live caps</strong>{" "}
            keeping the next one in check.
          </p>
        </div>
        <span className="text-[11.5px] text-[var(--l-charcoal)]/40">
          {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
        </span>
      </motion.div>

      <CostHero
        totalAllTime={allTime?.total_cost_usd ?? null}
        window24h={budget?.total_spend_usd ?? null}
        nearCapCount={nearCapCount}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="landing-display text-lg text-[var(--l-ink)]">Breakdown</h2>
            <WindowPicker value={window} onChange={setWindow} />
          </div>
          <p className="-mt-2 text-[12px] text-[var(--l-charcoal)]/50">
            Spend over {WINDOW_LABEL[window]}.
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SpendBreakdown title="Spend by agent" rows={byAgentRows} loading={breakdownLoading} />
            <SpendBreakdown title="Spend by model" rows={byModelRows} loading={breakdownLoading} />
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
