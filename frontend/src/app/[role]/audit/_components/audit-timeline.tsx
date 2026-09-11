"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { ShieldCheck, ShieldX, OctagonX, User, Bot, Cpu } from "lucide-react";
import { isAlarming, isAllowed, isHalt, timeAgo, type AuditEvent } from "./audit-types";
import { useRoleBase } from "@/lib/use-role-base";

const ACTOR_ICON: Record<string, typeof User> = {
  user: User,
  agent: Bot,
  system: Cpu,
  USER: User,
  AGENT: Bot,
  SYSTEM: Cpu,
};

/** How recent a decision has to be to count as "it just happened". */
const JUST_HAPPENED_MS = 15_000;

/**
 * Which decisions landed while you were watching — `useLive` re-fetches the
 * whole list on every stream event, so without this a row that just arrived
 * looks identical to one that was already sitting there, and the feed
 * updating is invisible.
 *
 * Two guards, because "an id I haven't rendered before" is *not* the same
 * question as "something just happened":
 *
 * - Nothing is new on the first load. An initial page of history arriving is
 *   not a decision happening while you watch, and flashing fourteen rows on
 *   mount would claim the opposite.
 * - An unseen id only counts if the event itself is recent. Otherwise
 *   switching the filter (All -> Denied and back) surfaces rows this
 *   component has genuinely never rendered, and every one of them would
 *   flash as though it had just been ruled on.
 *
 * Computed in an effect rather than during render: the seen-set is a side
 * effect, and React's dev-mode double-invoke would otherwise burn real
 * arrivals as already-seen before they were ever shown.
 */
function useNewlyArrived(events: AuditEvent[]): Set<string> {
  const seen = useRef<Set<string> | null>(null);
  const [fresh, setFresh] = useState<Set<string>>(() => new Set());
  const key = events.map((e) => e.id).join("|");

  useEffect(() => {
    if (seen.current === null) {
      seen.current = new Set(events.map((e) => e.id));
      return;
    }
    const now = Date.now();
    const arrived = events
      .filter((e) => !seen.current!.has(e.id) && now - +new Date(e.timestamp) < JUST_HAPPENED_MS)
      .map((e) => e.id);
    events.forEach((e) => seen.current!.add(e.id));
    if (arrived.length === 0) return;

    setFresh(new Set(arrived));
    const timer = setTimeout(() => setFresh(new Set()), 1800);
    return () => clearTimeout(timer);
    // `key` stands in for the id list itself; `events` is a fresh array each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return fresh;
}

/** Every governance decision, stamped ALLOW or DENY as it actually happened — the checkpoint log. */
export function AuditTimeline({
  events,
  agentName,
  loading,
}: {
  events: AuditEvent[];
  agentName: (id: string) => string;
  loading: boolean;
}) {
  const base = useRoleBase();
  const still = useReducedMotion();
  const fresh = useNewlyArrived(events);
  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]">
      <div className="space-y-1">
        {loading ? (
          [0, 1, 2, 3, 4].map((i) => <div key={i} className="h-14 animate-pulse rounded-xl bg-[var(--l-line)]/50" />)
        ) : events.length === 0 ? (
          <p className="py-10 text-center text-[12.5px] text-[var(--l-charcoal)]/50">
            Nothing matches these filters.
          </p>
        ) : (
          <AnimatePresence initial={false} mode="popLayout">
            {events.map((e, i) => {
              const allowed = isAllowed(e);
              const halt = isHalt(e);
              const alarming = isAlarming(e);
              const ActorIcon = ACTOR_ICON[e.actor_type] ?? User;
              const justArrived = fresh.has(e.id);
              return (
                <motion.div
                  key={e.id}
                  layout
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25, delay: Math.min(i, 14) * 0.02 }}
                  className="relative flex items-start gap-3 rounded-xl px-2.5 py-2.5"
                  style={{
                    background: alarming
                      ? "color-mix(in srgb, var(--l-orange-deep) 6%, transparent)"
                      : "transparent",
                  }}
                >
                  {/* Settles rather than blinks: a decision that just happened
                      should catch the eye once, then look like every other row. */}
                  {justArrived && !still && (
                    <motion.span
                      aria-hidden
                      initial={{ opacity: 0.5 }}
                      animate={{ opacity: 0 }}
                      transition={{ duration: 1.6, ease: "easeOut" }}
                      className="pointer-events-none absolute inset-0 rounded-xl"
                      style={{
                        background: alarming ? "var(--l-orange-deep)" : "var(--l-yellow)",
                      }}
                    />
                  )}
                  {halt ? (
                    /* A stop, not a refusal — an octagon rather than the denial
                       shield, so it never reads as "a policy blocked this". */
                    <span
                      className="relative mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-dashed"
                      style={{ borderColor: "var(--l-orange-deep)" }}
                    >
                      <OctagonX className="h-3.5 w-3.5" style={{ color: "var(--l-orange-deep)" }} />
                    </span>
                  ) : allowed ? (
                    <span className="relative mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-dashed" style={{ borderColor: "var(--l-teal)" }}>
                      <ShieldCheck className="h-3.5 w-3.5" style={{ color: "var(--l-teal)" }} />
                    </span>
                  ) : (
                    <motion.span
                      initial={{ rotate: 0 }}
                      animate={{ rotate: [0, -10, 10, -5, 0] }}
                      transition={{ duration: 0.4 }}
                      className="relative mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-dashed"
                      style={{ borderColor: "var(--l-orange-deep)" }}
                    >
                      <ShieldX className="h-3.5 w-3.5" style={{ color: "var(--l-orange-deep)" }} />
                    </motion.span>
                  )}

                  <span className="relative min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-1.5">
                      <ActorIcon className="h-3 w-3 shrink-0 text-[var(--l-charcoal)]/45" />
                      <span className="font-mono text-[12px] text-[var(--l-ink)]">
                        {e.tool ?? e.action}
                      </span>
                      {e.agent_id && (
                        <Link
                          href={`${base}/agents/${e.agent_id}`}
                          className="truncate text-[11.5px] text-[var(--l-charcoal)]/55 underline decoration-dotted hover:text-[var(--l-ink)]"
                        >
                          {agentName(e.agent_id)}
                        </Link>
                      )}
                    </span>
                    {e.reason && (
                      <span className="mt-0.5 block truncate text-[11.5px] text-[var(--l-charcoal)]/60">
                        {e.reason}
                      </span>
                    )}
                  </span>

                  <span className="relative shrink-0 whitespace-nowrap font-mono text-[10.5px] text-[var(--l-charcoal)]/40">
                    {timeAgo(e.timestamp)}
                  </span>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
