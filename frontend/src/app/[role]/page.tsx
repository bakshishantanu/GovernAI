"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useLive } from "@/lib/use-live";
import { timeAgo } from "@/lib/time-ago";
import { UserDashboard } from "./_components/user-dashboard";
import { StatRing } from "./_components/stat-ring";
import { FleetOverviewCard } from "./_components/fleet-overview-card";
import { ActivityTrendChart } from "./_components/activity-trend-chart";
import { ToolBreakdownCard } from "./_components/tool-breakdown-card";
import { CallsBarChart } from "./_components/calls-bar-chart";
import { AgentGrid } from "./_components/agent-grid";
import {
  bucketByHour,
  byTool,
  fleetHealth,
  type AuditEvent,
} from "./_components/dashboard-data";

type Agent = {
  id: string;
  name: string;
  status: string;
  passport: { lifecycle_state: string; compliance_status: string };
  skills: { id: string; name: string }[];
};

type AgentBudget = {
  agent_id: string;
  name: string;
  spend_usd: number;
  cap_usd: number;
  percent_of_cap: number;
  suspended: boolean;
};

type BudgetStatus = { cap_usd: number; total_spend_usd: number; agents: AgentBudget[] };

/**
 * Dashboard, restructured on the reference layout the user shared — stat
 * rings, a hero fleet card, a real activity trend with a peak callout, a
 * tool-usage breakdown, a call-volume bar chart, and a filterable agent
 * grid. Every figure comes from a live endpoint; see dashboard-data.ts for
 * how the real (sparse, uneven) audit history is aggregated honestly rather
 * than smoothed or invented.
 */
function AdminDashboard() {
  const load = useCallback(async () => {
    const [agents, audits, budget] = await Promise.all([
      fetchApi("/agents/").catch(() => []),
      fetchApi("/audits/?limit=200").catch(() => []),
      fetchApi("/costs/budget").catch(() => null),
    ]);
    return {
      agents: (agents ?? []) as Agent[],
      audits: (audits ?? []) as AuditEvent[],
      budget: budget as BudgetStatus | null,
    };
  }, []);

  const { data, updatedAt } = useLive(load);
  const agents = data?.agents ?? null;
  const audits = data?.audits ?? null;
  const budget = data?.budget ?? null;

  const loading = agents === null || audits === null || budget === null;

  const total = agents?.length ?? 0;
  const activeAgents = agents?.filter((a) => a.passport.lifecycle_state === "ACTIVE") ?? [];
  const health = fleetHealth(agents ?? []);
  const buckets = bucketByHour(audits ?? []);
  const tools = byTool(audits ?? []);
  const budgetByAgent = new Map((budget?.agents ?? []).map((a) => [a.agent_id, a]));

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <h1 className="landing-display text-3xl text-[var(--l-ink)]">Dashboard</h1>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            Monitor <strong className="text-[var(--l-ink)]">agents, governance, and spend</strong>{" "}
            in one place.
          </p>
          <p className="mt-0.5 text-[11.5px] text-[var(--l-charcoal)]/40">
            {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
          </p>
        </motion.div>

        <div className="flex flex-wrap gap-3">
          <StatRing
            pct={health.pct}
            value={`${health.pct}%`}
            label="Fleet health"
            color="var(--l-teal)"
            loading={loading}
          />
          <StatRing
            pct={total === 0 ? 0 : (activeAgents.length / total) * 100}
            value={String(total)}
            label="Total agents"
            color="var(--l-orange)"
            loading={loading}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-3">
          <FleetOverviewCard
            total={total}
            active={activeAgents.length}
            health={health}
            loading={loading}
          />
        </div>
        <div className="lg:col-span-6">
          <ActivityTrendChart buckets={buckets} loading={loading} />
        </div>
        <div className="lg:col-span-3">
          <ToolBreakdownCard tools={tools} loading={loading} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <CallsBarChart buckets={buckets} loading={loading} />
        </div>
        <div className="lg:col-span-7">
          <AgentGrid agents={agents ?? []} budgets={budgetByAgent} loading={loading} />
        </div>
      </div>
    </div>
  );
}


/**
 * One route, two homes (D-052: agent_builder merged into user, so the
 * former three-way split is now admin vs. everyone else).
 *
 * Each role's first screen answers a different question — "where is what I
 * asked for / what should I build next" vs. "is anything wrong across the
 * org" — so they are two different pages rather than one page with things
 * hidden. The role only chooses which to render; every figure on each is
 * still scoped by the backend to what that caller may see.
 */
export default function DashboardPage() {
  const { role } = useAuth();
  if (role === "admin") return <AdminDashboard />;
  return <UserDashboard />;
}
