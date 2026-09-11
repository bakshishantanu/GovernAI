"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ChevronRight, Loader2, CheckCircle2, XCircle, OctagonX, CircleDashed } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useRoleBase } from "@/lib/use-role-base";

type Execution = {
  id: string;
  agent_id: string;
  goal: string;
  status: string;
  started_at: string;
};

const STATUS_STYLE: Record<string, { icon: typeof CheckCircle2; color: string; live?: boolean }> = {
  COMPLETED: { icon: CheckCircle2, color: "var(--l-teal)" },
  FAILED: { icon: XCircle, color: "var(--l-orange-deep)" },
  CANCELLED: { icon: OctagonX, color: "var(--l-charcoal)" },
  TERMINATED: { icon: OctagonX, color: "#8a1f1f" },
  PENDING: { icon: CircleDashed, color: "var(--l-charcoal)" },
  RUNNING: { icon: Loader2, color: "var(--l-orange)", live: true },
};

/** Every past run for this agent, newest first — the trail its passport has actually walked. */
export function AgentRunsList({ agentId }: { agentId: string }) {
  const base = useRoleBase();
  const [runs, setRuns] = useState<Execution[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/executions/")
      .then((data: Execution[]) => {
        if (cancelled) return;
        const mine = (data ?? [])
          .filter((e) => e.agent_id === agentId)
          .sort((a, b) => +new Date(b.started_at) - +new Date(a.started_at))
          .slice(0, 6);
        setRuns(mine);
      })
      .catch(() => !cancelled && setRuns([]));
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_4px_0_0_rgba(22,19,14,0.12)]">
      <h2 className="landing-display text-base text-[var(--l-ink)]">Recent runs</h2>

      <div className="mt-3 space-y-1.5">
        {runs === null ? (
          [0, 1].map((i) => <div key={i} className="h-12 animate-pulse rounded-xl bg-[var(--l-line)]/50" />)
        ) : runs.length === 0 ? (
          <p className="py-4 text-center text-[12.5px] text-[var(--l-charcoal)]/50">
            No runs yet — give it a goal above.
          </p>
        ) : (
          runs.map((run, i) => {
            const s = STATUS_STYLE[run.status] ?? STATUS_STYLE.PENDING;
            return (
              <motion.div
                key={run.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: i * 0.04 }}
              >
                <Link
                  href={`${base}/agents/${agentId}/executions/${run.id}`}
                  className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-[var(--l-cream-deep)]/60"
                >
                  <s.icon
                    className={`h-4 w-4 shrink-0 ${s.live ? "animate-spin" : ""}`}
                    style={{ color: s.color }}
                  />
                  <span className="min-w-0 flex-1 truncate text-[13px] text-[var(--l-ink)]">{run.goal}</span>
                  <span className="shrink-0 font-mono text-[10px] uppercase text-[var(--l-charcoal)]/45">
                    {run.status}
                  </span>
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[var(--l-charcoal)]/30" />
                </Link>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
