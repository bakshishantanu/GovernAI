"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Hammer, Inbox } from "lucide-react";
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
};

type AgentBudget = { agent_id: string; name: string; spend_usd: number; cap_usd: number };
type Budget = { agents: AgentBudget[]; cap_usd: number; total_spend_usd: number };

/**
 * The Builder's home.
 *
 * A builder's day starts with a question a counter cannot answer: what should
 * I pick up next? So the oldest unclaimed request leads, in full, with the
 * claim action on it — the page's single most useful pixel. Totals are a thin
 * strip underneath, because knowing there are four waiting matters far less
 * than seeing the one that has waited longest.
 */
export function BuilderDashboard() {
  const [claiming, setClaiming] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [requests, agents, budget] = await Promise.all([
      fetchApi("/agent-requests/").catch(() => []),
      fetchApi("/agents/").catch(() => []),
      fetchApi("/costs/budget").catch(() => null),
    ]);
    return {
      requests: (Array.isArray(requests) ? requests : []) as AgentRequest[],
      agents: (Array.isArray(agents) ? agents : []) as Agent[],
      budget: budget as Budget | null,
    };
  }, []);

  const { data, updatedAt, refresh } = useLive(load);
  const loading = data === null;
  const requests = data?.requests ?? [];
  const agents = data?.agents ?? [];
  const budget = data?.budget ?? null;

  const waiting = requests
    .filter((r) => r.status === "PENDING")
    .sort((a, b) => +new Date(a.created_at) - +new Date(b.created_at));
  const mine = requests.filter((r) => r.status === "CLAIMED");
  const delivered = requests.filter((r) => r.status === "FULFILLED");
  const next = waiting[0] ?? null;

  const live = agents.filter((a) => a.passport?.lifecycle_state === "ACTIVE").length;
  const drafts = agents.filter((a) => a.passport?.lifecycle_state === "DRAFT").length;

  async function claim(id: string) {
    setClaiming(id);
    try {
      await fetchApi(`/agent-requests/${id}/claim`, { method: "POST" });
    } finally {
      setClaiming(null);
      refresh();
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-10">
      <header>
        <h1 className="landing-display text-[34px] leading-tight text-[var(--l-ink)]">
          What needs building
        </h1>
        <p className="mt-1 max-w-[62ch] text-sm text-[var(--l-charcoal)]/60">
          People ask for agents here. You assemble them from skills, the
          compliance check runs, and activating one hands it straight back.
        </p>
      </header>

      <section aria-label="Next in the queue">
        {loading ? (
          <div className="h-[188px] animate-pulse rounded-3xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40" />
        ) : next ? (
          <motion.article
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="rounded-3xl border-2 border-[var(--l-ink)] bg-[var(--l-cream)] p-6"
          >
            <div className="flex items-center gap-2 text-[12px] font-semibold text-[var(--l-charcoal)]/55">
              <motion.span
                aria-hidden
                animate={{ opacity: [1, 0.35, 1] }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
                className="h-2 w-2 rounded-full"
                style={{ background: "var(--l-orange)" }}
              />
              Waiting longest · asked {timeAgo(next.created_at)}
            </div>

            <h2 className="mt-3 text-[22px] font-semibold leading-snug text-[var(--l-ink)]">
              {next.title}
            </h2>
            <p className="mt-2 max-w-[70ch] text-[14px] leading-relaxed text-[var(--l-charcoal)]/75">
              {next.description}
            </p>

            {next.requested_skills.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/45">
                  They suggested
                </span>
                {next.requested_skills.map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-[var(--l-cream-deep)] px-2.5 py-1 font-mono text-[11.5px] text-[var(--l-ink)]"
                  >
                    {s}
                  </span>
                ))}
                <span className="text-[11.5px] text-[var(--l-charcoal)]/45">
                  — change them if they do not fit
                </span>
              </div>
            )}

            <div className="mt-6 flex flex-wrap items-center gap-3 border-t-2 border-dashed border-[var(--l-ink)]/15 pt-5">
              <motion.button
                type="button"
                onClick={() => claim(next.id)}
                disabled={claiming === next.id}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="inline-flex h-11 items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 text-sm font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)] disabled:opacity-50"
              >
                <Hammer className="h-4 w-4" />
                {claiming === next.id ? "Claiming…" : "I'll build this"}
              </motion.button>
              <Link
                href="/requests"
                className="text-[13px] font-semibold text-[var(--l-charcoal)]/55 transition-colors hover:text-[var(--l-orange-deep)]"
              >
                See the whole queue
              </Link>
            </div>
          </motion.article>
        ) : (
          <div className="rounded-3xl border-2 border-dashed border-[var(--l-line)] bg-[var(--l-cream)] px-6 py-12 text-center">
            <Inbox className="mx-auto h-6 w-6 text-[var(--l-charcoal)]/30" />
            <p className="landing-display mt-3 text-lg text-[var(--l-ink)]">Queue is clear</p>
            <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
              Nothing is waiting. New requests appear here as people send them.
            </p>
          </div>
        )}
      </section>

      {/* Totals as a strip, not as cards: they are context for the request
          above, not the point of the page. */}
      <section
        aria-label="Queue totals"
        className="flex flex-wrap gap-x-10 gap-y-4 border-y-2 border-dashed border-[var(--l-ink)]/12 py-5"
      >
        {[
          { label: "waiting", value: waiting.length },
          { label: "you are building", value: mine.length },
          { label: "handed over", value: delivered.length },
          { label: "your agents live", value: live },
          { label: "still draft", value: drafts },
        ].map((stat) => (
          <div key={stat.label}>
            <div className="text-[26px] font-semibold leading-none text-[var(--l-ink)]">
              {loading ? "·" : <CountUp value={stat.value} />}
            </div>
            <div className="mt-1 text-[12px] text-[var(--l-charcoal)]/55">{stat.label}</div>
          </div>
        ))}
      </section>

      <section>
        <div className="mb-3 flex items-baseline justify-between gap-4">
          <h2 className="landing-display text-xl text-[var(--l-ink)]">What you have built</h2>
          <span className="text-[11.5px] text-[var(--l-charcoal)]/40">
            {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
          </span>
        </div>

        {loading ? (
          <div className="h-[96px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40" />
        ) : agents.length === 0 ? (
          <p className="rounded-2xl border-2 border-dashed border-[var(--l-line)] bg-[var(--l-cream)] px-6 py-9 text-center text-sm text-[var(--l-charcoal)]/60">
            Nothing yet. Claim a request above and the agent you assemble shows up here.
          </p>
        ) : (
          <ul className="space-y-2">
            {agents.map((agent, i) => {
              const b = budget?.agents.find((x) => x.agent_id === agent.id);
              const pct = b && b.cap_usd > 0 ? Math.min(100, (b.spend_usd / b.cap_usd) * 100) : 0;
              return (
                <motion.li
                  key={agent.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: Math.min(i, 6) * 0.05 }}
                >
                  <Link
                    href={`/agents/${agent.id}`}
                    className="group block rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4 transition-colors hover:border-[var(--l-ink)]"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-[15px] font-semibold text-[var(--l-ink)]">{agent.name}</p>
                      <span className="rounded-full bg-[var(--l-cream-deep)] px-2.5 py-1 text-[11.5px] font-semibold text-[var(--l-ink)]">
                        {agent.passport?.lifecycle_state ?? "—"}
                      </span>
                    </div>

                    {b && (
                      <div className="mt-3">
                        <div className="h-1.5 overflow-hidden rounded-full bg-[var(--l-line)]">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                            className="h-full rounded-full"
                            style={{
                              background: pct > 80 ? "var(--l-orange)" : "var(--l-teal)",
                            }}
                          />
                        </div>
                        <p className="gv-num mt-1.5 font-mono text-[11px] text-[var(--l-charcoal)]/45">
                          ${b.spend_usd < 0.01 ? b.spend_usd.toFixed(4) : b.spend_usd.toFixed(2)} of
                          ${b.cap_usd.toFixed(2)} in the last 24h
                        </p>
                      </div>
                    )}

                    <span className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--l-charcoal)]/50 transition-colors group-hover:text-[var(--l-orange-deep)]">
                      Open its passport
                      <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                  </Link>
                </motion.li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
