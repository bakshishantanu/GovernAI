"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Hourglass, Hammer, PackageCheck, Ban } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AgentRequest, AgentRequestStatus } from "@/lib/types";
import { timeAgo } from "@/lib/time-ago";

/**
 * What happened to the things you asked for.
 *
 * The four statuses are shown as a plain sentence rather than a coloured
 * chip alone, because "CLAIMED" means nothing to someone who has never read
 * the schema — "someone is building it" does. The raw status is still
 * carried in the dot colour so the vocabulary stays learnable.
 */

const STATUS: Record<
  AgentRequestStatus,
  { label: string; blurb: string; icon: LucideIcon; dot: string; fill: string }
> = {
  PENDING: {
    label: "Waiting",
    blurb: "No one has picked this up yet.",
    icon: Hourglass,
    dot: "var(--l-yellow-deep)",
    fill: "var(--l-yellow-pale)",
  },
  CLAIMED: {
    label: "Being built",
    blurb: "A builder is putting it together.",
    icon: Hammer,
    dot: "var(--l-orange)",
    fill: "var(--l-orange-soft)",
  },
  FULFILLED: {
    label: "Ready",
    blurb: "Handed over — it is in My agents.",
    icon: PackageCheck,
    dot: "var(--l-teal)",
    fill: "var(--l-teal-soft)",
  },
  CANCELLED: {
    label: "Cancelled",
    blurb: "This one was withdrawn.",
    icon: Ban,
    dot: "var(--l-charcoal)",
    fill: "var(--l-cream-deep)",
  },
};

export function MyRequests({
  requests,
  onCancel,
}: {
  requests: AgentRequest[] | null;
  onCancel: (id: string) => void;
}) {
  if (requests === null) {
    return (
      <div className="space-y-2">
        {[0, 1].map((i) => (
          <div
            key={i}
            className="h-[92px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40"
          />
        ))}
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-[var(--l-line)] px-6 py-10 text-center">
        <p className="landing-display text-base text-[var(--l-ink)]">Nothing asked for yet</p>
        <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
          Describe a job above and it will appear here while it is built.
        </p>
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {requests.map((req, i) => {
        const s = STATUS[req.status] ?? STATUS.PENDING;
        const Icon = s.icon;
        const canCancel = req.status === "PENDING" || req.status === "CLAIMED";

        return (
          <motion.li
            key={req.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: Math.min(i, 6) * 0.04 }}
            className="rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-[15px] font-semibold text-[var(--l-ink)]">
                  {req.title}
                </p>
                <p className="mt-0.5 line-clamp-2 text-[13px] leading-snug text-[var(--l-charcoal)]/65">
                  {req.description}
                </p>
              </div>

              <span
                className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold text-[var(--l-ink)]"
                style={{ background: s.fill }}
              >
                <Icon className="h-3.5 w-3.5" style={{ color: s.dot }} />
                {s.label}
              </span>
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t-2 border-dashed border-[var(--l-ink)]/10 pt-3">
              <span className="text-[12px] text-[var(--l-charcoal)]/60">
                {s.blurb} <span className="text-[var(--l-charcoal)]/40">· asked {timeAgo(req.created_at)}</span>
              </span>

              <span className="flex items-center gap-3">
                {req.status === "FULFILLED" && req.agent_id && (
                  <Link
                    href={`/agents/${req.agent_id}`}
                    className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--l-orange-deep)] hover:underline"
                  >
                    Open the agent
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                )}
                {canCancel && (
                  <button
                    type="button"
                    onClick={() => onCancel(req.id)}
                    className="text-[12.5px] text-[var(--l-charcoal)]/55 transition-colors hover:text-[var(--l-ink)] hover:underline"
                  >
                    Cancel
                  </button>
                )}
              </span>
            </div>
          </motion.li>
        );
      })}
    </ul>
  );
}
