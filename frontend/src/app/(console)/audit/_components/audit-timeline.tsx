"use client";

import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck, ShieldX, User, Bot, Cpu } from "lucide-react";
import { isAllowed, timeAgo, type AuditEvent } from "./audit-types";

const ACTOR_ICON: Record<string, typeof User> = {
  user: User,
  agent: Bot,
  system: Cpu,
  USER: User,
  AGENT: Bot,
  SYSTEM: Cpu,
};

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
              const ActorIcon = ACTOR_ICON[e.actor_type] ?? User;
              return (
                <motion.div
                  key={e.id}
                  layout
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25, delay: Math.min(i, 14) * 0.02 }}
                  className="flex items-start gap-3 rounded-xl px-2.5 py-2.5"
                  style={{
                    background: allowed ? "transparent" : "color-mix(in srgb, var(--l-orange-deep) 6%, transparent)",
                  }}
                >
                  {allowed ? (
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-dashed" style={{ borderColor: "var(--l-teal)" }}>
                      <ShieldCheck className="h-3.5 w-3.5" style={{ color: "var(--l-teal)" }} />
                    </span>
                  ) : (
                    <motion.span
                      initial={{ rotate: 0 }}
                      animate={{ rotate: [0, -10, 10, -5, 0] }}
                      transition={{ duration: 0.4 }}
                      className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-dashed"
                      style={{ borderColor: "var(--l-orange-deep)" }}
                    >
                      <ShieldX className="h-3.5 w-3.5" style={{ color: "var(--l-orange-deep)" }} />
                    </motion.span>
                  )}

                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-1.5">
                      <ActorIcon className="h-3 w-3 shrink-0 text-[var(--l-charcoal)]/45" />
                      <span className="font-mono text-[12px] text-[var(--l-ink)]">
                        {e.tool ?? e.action}
                      </span>
                      {e.agent_id && (
                        <Link
                          href={`/agents/${e.agent_id}`}
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

                  <span className="shrink-0 whitespace-nowrap font-mono text-[10.5px] text-[var(--l-charcoal)]/40">
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
