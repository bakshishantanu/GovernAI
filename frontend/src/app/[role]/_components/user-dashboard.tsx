"use client";

import { useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Play, Plus } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useLive } from "@/lib/use-live";
import { useRoleBase } from "@/lib/use-role-base";
import { timeAgo } from "@/lib/time-ago";

type Agent = {
  id: string;
  name: string;
  description: string;
  passport?: { lifecycle_state: string };
  skills?: { id: string; name: string }[];
};

type Run = { id: string; agent_id: string; goal: string; status: string; started_at: string };

/**
 * The User's home — merged with what used to be the separate Builder's home
 * (D-052: agent_builder's capabilities folded into user), then simplified
 * further once a user could build an agent directly: the request/claim flow
 * this page used to track (Asked for -> Being built -> Ready, plus a claim
 * card) was removed along with the rest of that feature — a two-step "ask,
 * then someone claims it" ceremony has no purpose once the person asking and
 * the person building are the same person. "New agent" on the agents page
 * is the one direct path now, so this page just shows what's ready to use
 * and what's happened lately.
 */
export function UserDashboard() {
  const base = useRoleBase();
  const load = useCallback(async () => {
    const [agents, runs] = await Promise.all([
      fetchApi("/agents/").catch(() => []),
      fetchApi("/executions/").catch(() => []),
    ]);
    return {
      agents: (Array.isArray(agents) ? agents : []) as Agent[],
      runs: (Array.isArray(runs) ? runs : []) as Run[],
    };
  }, []);

  const { data, updatedAt } = useLive(load);
  const agents = data?.agents ?? [];
  const runs = data?.runs ?? [];
  const loading = data === null;

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="landing-display text-[34px] leading-tight text-[var(--l-ink)]">
            Your agents, end to end
          </h1>
          <p className="mt-1 max-w-[62ch] text-sm text-[var(--l-charcoal)]/60">
            Build an agent from a skill, the compliance check runs, and it
            arrives here ready to use.
          </p>
        </div>
        <Link
          href={`${base}/agents`}
          className="inline-flex h-11 items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 text-sm font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)]"
        >
          <Plus className="h-4 w-4" />
          Build an agent
        </Link>
      </header>

      <section>
        <div className="mb-3 flex items-baseline justify-between gap-4">
          <h2 className="landing-display text-xl text-[var(--l-ink)]">Ready to use</h2>
          {agents.length > 0 && (
            <Link
              href={`${base}/agents`}
              className="text-[12.5px] font-semibold text-[var(--l-charcoal)]/55 transition-colors hover:text-[var(--l-orange-deep)]"
            >
              All of them
            </Link>
          )}
        </div>

        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {[0, 1].map((i) => (
              <div
                key={i}
                className="h-[104px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40"
              />
            ))}
          </div>
        ) : agents.length === 0 ? (
          <p className="rounded-2xl border-2 border-dashed border-[var(--l-line)] bg-[var(--l-cream)] px-6 py-9 text-center text-sm text-[var(--l-charcoal)]/60">
            Nothing yet. Build an agent from a skill and it lands here ready
            to run.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {agents.map((agent, i) => (
              <motion.div
                key={agent.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: Math.min(i, 6) * 0.05 }}
              >
                <Link
                  href={`${base}/agents/${agent.id}`}
                  className="group flex h-full flex-col justify-between rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4 transition-colors hover:border-[var(--l-ink)]"
                >
                  <div>
                    <p className="text-[15px] font-semibold text-[var(--l-ink)]">{agent.name}</p>
                    <p className="mt-0.5 line-clamp-2 text-[13px] leading-snug text-[var(--l-charcoal)]/65">
                      {agent.description}
                    </p>
                  </div>
                  <span className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--l-charcoal)]/50 transition-colors group-hover:text-[var(--l-orange-deep)]">
                    <Play className="h-3.5 w-3.5" />
                    Give it a job
                  </span>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-baseline justify-between gap-4">
          <h2 className="landing-display text-xl text-[var(--l-ink)]">Lately</h2>
          <span className="text-[11.5px] text-[var(--l-charcoal)]/40">
            {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
          </span>
        </div>

        {runs.length === 0 ? (
          <p className="rounded-2xl border-2 border-dashed border-[var(--l-line)] bg-[var(--l-cream)] px-6 py-9 text-center text-sm text-[var(--l-charcoal)]/60">
            No runs yet — this fills in the moment you give an agent something to do.
          </p>
        ) : (
          <ul className="divide-y-2 divide-dashed divide-[var(--l-ink)]/10 overflow-hidden rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)]">
            {runs.slice(0, 5).map((run) => (
              <li key={run.id}>
                <Link
                  href={`${base}/agents/${run.agent_id}/executions/${run.id}`}
                  className="flex items-center justify-between gap-4 px-4 py-3 transition-colors hover:bg-[var(--l-cream-deep)]/50"
                >
                  <span className="min-w-0 flex-1 truncate text-[14px] text-[var(--l-ink)]">
                    {run.goal || "No goal recorded"}
                  </span>
                  <span className="gv-num shrink-0 font-mono text-[11px] text-[var(--l-charcoal)]/45">
                    {timeAgo(run.started_at)}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-[var(--l-charcoal)]/35" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
