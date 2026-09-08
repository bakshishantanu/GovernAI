"use client";

import { useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Play, Plus } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useLive } from "@/lib/use-live";
import { CountUp } from "@/components/count-up";
import { timeAgo } from "@/lib/time-ago";
import type { AgentRequest } from "@/lib/types";

type Agent = {
  id: string;
  name: string;
  description: string;
  passport?: { lifecycle_state: string };
  skills?: { id: string; name: string }[];
};

type Run = { id: string; agent_id: string; goal: string; status: string; started_at: string };

/**
 * The User's home.
 *
 * Structured as the journey the product actually describes — asked, being
 * built, ready — rather than a row of counters, because that sequence *is*
 * the answer to the only question a User has here: where is the thing I asked
 * for? A counter says "2 pending"; the track says which two, and what happens
 * next.
 *
 * Everything below the track is what they can act on right now.
 */

const STAGES = [
  {
    key: "asked",
    label: "Asked for",
    note: "waiting for a builder",
    fill: "var(--l-yellow-pale)",
    pip: "var(--l-yellow-deep)",
    match: (r: AgentRequest) => r.status === "PENDING",
  },
  {
    key: "building",
    label: "Being built",
    note: "someone is on it",
    fill: "var(--l-pink-pale)",
    pip: "var(--l-orange)",
    match: (r: AgentRequest) => r.status === "CLAIMED",
  },
  {
    key: "ready",
    label: "Ready",
    note: "handed over to you",
    fill: "var(--l-teal-soft)",
    pip: "var(--l-teal)",
    match: (r: AgentRequest) => r.status === "FULFILLED",
  },
] as const;

export function UserDashboard() {
  const load = useCallback(async () => {
    const [requests, agents, runs] = await Promise.all([
      fetchApi("/agent-requests/").catch(() => []),
      fetchApi("/agents/").catch(() => []),
      fetchApi("/executions/").catch(() => []),
    ]);
    return {
      requests: (Array.isArray(requests) ? requests : []) as AgentRequest[],
      agents: (Array.isArray(agents) ? agents : []) as Agent[],
      runs: (Array.isArray(runs) ? runs : []) as Run[],
    };
  }, []);

  const { data, updatedAt } = useLive(load);
  const requests = data?.requests ?? [];
  const agents = data?.agents ?? [];
  const runs = data?.runs ?? [];
  const loading = data === null;

  const live = requests.filter((r) => r.status !== "CANCELLED");

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="landing-display text-[34px] leading-tight text-[var(--l-ink)]">
            Your agents, end to end
          </h1>
          <p className="mt-1 max-w-[62ch] text-sm text-[var(--l-charcoal)]/60">
            Ask for what you need. Someone builds it, the governance checks run,
            and it arrives here ready to use.
          </p>
        </div>
        <Link
          href="/request-agent"
          className="inline-flex h-11 items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 text-sm font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)]"
        >
          <Plus className="h-4 w-4" />
          Ask for an agent
        </Link>
      </header>

      {/* The track. The connecting rule draws itself once on mount — the one
          authored moment on this page, and the thing that makes three columns
          read as a sequence rather than three boxes. */}
      <section aria-label="Where your requests are">
        <div className="relative">
          {/* Starts and stops at the pip centres (27px into the first and last
              columns) so the rule connects the stations instead of running off
              the edge as if the sequence continued. */}
          <div className="pointer-events-none absolute left-[27px] right-[calc(33.333%-27px)] top-[26px] hidden h-[2px] sm:block">
            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
              style={{ transformOrigin: "left", background: "var(--l-line)" }}
              className="h-full w-full"
            />
          </div>

          <ol className="relative grid gap-4 sm:grid-cols-3">
            {STAGES.map((stage, i) => {
              const here = live.filter(stage.match);
              return (
                <motion.li
                  key={stage.key}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    duration: 0.45,
                    delay: 0.25 + i * 0.12,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                >
                  <span
                    className="relative z-10 flex h-[54px] w-[54px] items-center justify-center rounded-full border-2 border-[var(--l-ink)] text-xl font-semibold text-[var(--l-ink)]"
                    style={{ background: stage.fill }}
                  >
                    {loading ? "·" : <CountUp value={here.length} />}
                  </span>

                  <h2 className="mt-3 text-[15px] font-semibold text-[var(--l-ink)]">
                    {stage.label}
                  </h2>
                  <p className="text-[12.5px] text-[var(--l-charcoal)]/55">{stage.note}</p>

                  <ul className="mt-3 space-y-1.5">
                    {here.slice(0, 3).map((r) => (
                      <li
                        key={r.id}
                        className="flex items-start gap-2 text-[13px] leading-snug text-[var(--l-ink)]"
                      >
                        <span
                          aria-hidden
                          className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full"
                          style={{ background: stage.pip }}
                        />
                        <span className="min-w-0 truncate">{r.title}</span>
                      </li>
                    ))}
                    {here.length > 3 && (
                      <li className="pl-3.5 text-[12.5px] text-[var(--l-charcoal)]/50">
                        and {here.length - 3} more
                      </li>
                    )}
                    {!loading && here.length === 0 && (
                      <li className="text-[12.5px] text-[var(--l-charcoal)]/40">Nothing here</li>
                    )}
                  </ul>
                </motion.li>
              );
            })}
          </ol>
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-baseline justify-between gap-4">
          <h2 className="landing-display text-xl text-[var(--l-ink)]">Ready to use</h2>
          {agents.length > 0 && (
            <Link
              href="/agents"
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
            Nothing has been handed over yet. Once a builder finishes something
            you asked for, it lands here ready to run.
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
                  href={`/agents/${agent.id}`}
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
                  href={`/agents/${run.agent_id}/executions/${run.id}`}
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
