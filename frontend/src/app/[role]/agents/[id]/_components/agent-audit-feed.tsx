"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ShieldX } from "lucide-react";
import { fetchApi } from "@/lib/api-client";

type AuditEvent = {
  id: string;
  timestamp: string;
  agent_id: string | null;
  tool: string | null;
  policy_decision: string;
  reason: string | null;
};

function timeAgo(iso: string) {
  const s = Math.max(0, Math.floor((Date.now() - +new Date(iso)) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/** This agent's slice of the org-wide audit trail — every governance decision it triggered. */
export function AgentAuditFeed({ agentId }: { agentId: string }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/audits/?limit=200")
      .then((data: AuditEvent[]) => {
        if (cancelled) return;
        setEvents((data ?? []).filter((e) => e.agent_id === agentId).slice(0, 8));
      })
      .catch(() => !cancelled && setEvents([]));
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_4px_0_0_rgba(22,19,14,0.12)]">
      <h2 className="landing-display text-base text-[var(--l-ink)]">Governance activity</h2>

      <div className="mt-3 space-y-1">
        {events === null ? (
          [0, 1, 2].map((i) => <div key={i} className="h-9 animate-pulse rounded-lg bg-[var(--l-line)]/50" />)
        ) : events.length === 0 ? (
          <p className="py-4 text-center text-[12.5px] text-[var(--l-charcoal)]/50">
            Nothing logged for this agent yet.
          </p>
        ) : (
          events.map((e, i) => {
            const allowed = e.policy_decision === "ALLOW" || e.policy_decision === "ALLOWED";
            return (
              <motion.div
                key={e.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.25, delay: i * 0.03 }}
                className="flex items-center gap-2.5 rounded-lg px-2 py-1.5"
              >
                {allowed ? (
                  <ShieldCheck className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--l-teal)" }} />
                ) : (
                  <ShieldX className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--l-orange-deep)" }} />
                )}
                <span className="min-w-0 flex-1 truncate font-mono text-[11.5px] text-[var(--l-ink)]">
                  {e.tool ?? "-"}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-[var(--l-charcoal)]/40">
                  {timeAgo(e.timestamp)}
                </span>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
