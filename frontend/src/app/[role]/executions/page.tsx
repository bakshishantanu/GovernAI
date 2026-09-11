"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useLive } from "@/lib/use-live";
import { timeAgo } from "@/lib/time-ago";
import { useRoleBase } from "@/lib/use-role-base";

/**
 * Every run, newest first — scoped by the backend to whatever the caller is
 * allowed to see, so this page never asks who it is talking to.
 *
 * Fields are the ones the API actually returns (`goal`, `started_at`), not
 * the ones lib/types.ts guesses at (`prompt`, `created_at`); confirmed
 * against a live response before this was written.
 */

type Execution = {
  id: string;
  agent_id: string;
  goal: string;
  status: string;
  result?: string | null;
  error?: string | null;
  started_at: string;
  completed_at?: string | null;
};

const STATUS: Record<string, { label: string; icon: LucideIcon; fill: string; ink: string }> = {
  COMPLETED: {
    label: "Finished",
    icon: CheckCircle2,
    fill: "var(--l-teal-soft)",
    ink: "var(--l-teal)",
  },
  RUNNING: {
    label: "Running",
    icon: Loader2,
    fill: "var(--l-yellow-pale)",
    ink: "var(--l-yellow-deep)",
  },
  PENDING: {
    label: "Queued",
    icon: Loader2,
    fill: "var(--l-cream-deep)",
    ink: "var(--l-charcoal)",
  },
  FAILED: {
    label: "Failed",
    icon: XCircle,
    fill: "var(--l-pink-blush)",
    ink: "var(--l-orange-deep)",
  },
};

const TITLE: Record<string, string> = {
  admin: "All runs",
  user: "My runs",
};

const BLURB: Record<string, string> = {
  admin: "Every execution in the organisation, newest first.",
  user: "Everything your agents — built or handed to you — have done, newest first.",
};

export default function ExecutionsPage() {
  const { role } = useAuth();
  const base = useRoleBase();

  const load = useCallback(async () => {
    const data = await fetchApi("/executions/").catch(() => []);
    return (Array.isArray(data) ? data : []) as Execution[];
  }, []);

  const { data: runs, updatedAt } = useLive(load);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-wrap items-end justify-between gap-4"
      >
        <div>
          <h1 className="landing-display text-3xl text-[var(--l-ink)]">
            {TITLE[role] ?? "Runs"}
          </h1>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            {BLURB[role] ?? "Executions, newest first."}
          </p>
        </div>
        <span className="text-[11.5px] text-[var(--l-charcoal)]/40">
          {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
        </span>
      </motion.div>

      {runs === null ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[84px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40"
            />
          ))}
        </div>
      ) : runs.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-[var(--l-line)] px-6 py-14 text-center">
          <p className="landing-display text-base text-[var(--l-ink)]">Nothing has run yet</p>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            {role === "agent_builder"
              ? "Once an agent is handed to you, give it a job and it will show up here."
              : "Give an agent a goal and its run will appear here."}
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {runs.map((run, i) => {
            const s = STATUS[run.status?.toUpperCase()] ?? STATUS.PENDING;
            const Icon = s.icon;
            const spinning = run.status?.toUpperCase() === "RUNNING";

            return (
              <motion.li
                key={run.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: Math.min(i, 8) * 0.03 }}
              >
                <Link
                  href={`${base}/agents/${run.agent_id}/executions/${run.id}`}
                  className="group block rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4 transition-colors hover:border-[var(--l-ink)]"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <p className="min-w-0 flex-1 text-[15px] font-semibold leading-snug text-[var(--l-ink)]">
                      {run.goal || "No goal recorded"}
                    </p>
                    <span
                      className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold text-[var(--l-ink)]"
                      style={{ background: s.fill }}
                    >
                      <Icon
                        className={`h-3.5 w-3.5 ${spinning ? "animate-spin" : ""}`}
                        style={{ color: s.ink }}
                      />
                      {s.label}
                    </span>
                  </div>

                  {run.error && (
                    <p className="mt-2 line-clamp-2 text-[12.5px] leading-snug text-[var(--l-orange-deep)]">
                      {run.error}
                    </p>
                  )}

                  <div className="mt-3 flex items-center justify-between border-t-2 border-dashed border-[var(--l-ink)]/10 pt-3">
                    <span className="font-mono text-[11px] text-[var(--l-charcoal)]/45">
                      started {timeAgo(run.started_at)}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-[var(--l-charcoal)]/50 transition-colors group-hover:text-[var(--l-orange-deep)]">
                      See every step
                      <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                  </div>
                </Link>
              </motion.li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
