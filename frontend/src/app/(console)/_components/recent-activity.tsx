"use client";

import { motion } from "framer-motion";
import { ShieldCheck, ShieldX } from "lucide-react";
import { timeAgo } from "@/lib/time-ago";

export type AuditEvent = {
  id: string;
  timestamp: string;
  agent_id: string | null;
  action: string;
  tool: string | null;
  policy_decision: string | null;
  reason: string | null;
};

/**
 * The dashboard's live feed. Reads straight off GET /audits/ — the same
 * append-only source the /audit screen will page through in full — so a
 * denial shown here and one shown there are never two different truths.
 */
export function RecentActivity({
  events,
  agentNames,
  loading,
}: {
  events: AuditEvent[];
  agentNames: Map<string, string>;
  loading: boolean;
}) {
  return (
    <div className="rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream-deep)]/50">
      <div className="flex items-center justify-between border-b border-[var(--l-line)] px-5 py-4">
        <span className="landing-display text-lg text-[var(--l-ink)]">Recent activity</span>
        <span className="text-xs text-[var(--l-charcoal)]/50">from the audit log</span>
      </div>

      {loading ? (
        <div className="space-y-3 p-5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-12 animate-pulse rounded-lg bg-[var(--l-line)]/60" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <p className="p-6 text-sm text-[var(--l-charcoal)]/60">
          Nothing logged yet — run an agent to see its tool calls appear here.
        </p>
      ) : (
        <ul className="divide-y divide-[var(--l-line)]">
          {events.slice(0, 8).map((e, i) => {
            const denied = e.policy_decision === "DENY";
            const agentName = e.agent_id ? agentNames.get(e.agent_id) : null;
            return (
              <motion.li
                key={e.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.25, delay: i * 0.03 }}
                className="flex items-start gap-3 px-5 py-3"
              >
                {denied ? (
                  <ShieldX className="mt-0.5 h-4 w-4 shrink-0 text-[var(--l-orange-deep)]" />
                ) : (
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[var(--l-teal)]" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-[var(--l-ink)]">
                    <span className="font-medium">{agentName ?? "Unknown agent"}</span>{" "}
                    <span className="text-[var(--l-charcoal)]/70">
                      {denied ? "was denied" : "called"}{" "}
                      <code className="font-mono text-[12px]">{e.tool ?? e.action}</code>
                    </span>
                  </p>
                  {denied && e.reason && (
                    <p className="mt-0.5 truncate text-xs text-[var(--l-orange-deep)]/80">
                      {e.reason}
                    </p>
                  )}
                </div>
                <span className="shrink-0 text-xs text-[var(--l-charcoal)]/45">
                  {timeAgo(e.timestamp)}
                </span>
              </motion.li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
