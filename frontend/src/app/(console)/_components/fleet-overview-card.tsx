"use client";

import { motion, useReducedMotion } from "framer-motion";

/**
 * The dark-navy hero card. Where the reference dashboard uses a property
 * photo, this uses the Gate mark (D-036's proposed primary logo) animated —
 * the chevron sweeps through the posts on a loop, echoing what the product
 * actually does: something passing a checkpoint. Not a stock illustration.
 */
export function FleetOverviewCard({
  total,
  active,
  health,
  loading,
}: {
  total: number;
  active: number;
  health: { pct: number; label: string };
  loading?: boolean;
}) {
  const still = useReducedMotion();

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-[var(--l-line)] bg-[var(--l-navy-deep)] text-[var(--l-cream)]">
      <div className="flex items-center justify-between px-5 pt-4">
        <span className="landing-display text-lg">Agent fleet</span>
        <span className="text-xs text-[var(--l-cream)]/50">real-time</span>
      </div>

      <div className="flex flex-1 items-center justify-center py-4">
        <svg viewBox="0 0 64 64" className="h-24 w-24" aria-hidden="true">
          <rect x="9" y="12" width="10" height="40" rx="4" fill="var(--l-orange-soft)" />
          <rect x="45" y="12" width="10" height="40" rx="4" fill="var(--l-orange-soft)" />
          <motion.path
            d="M 26 22 L 38 32 L 26 42"
            fill="none"
            stroke="var(--l-orange)"
            strokeWidth="7"
            strokeLinecap="round"
            strokeLinejoin="round"
            animate={
              still
                ? undefined
                : { x: [0, 6, 0], opacity: [0.6, 1, 0.6] }
            }
            transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
          />
        </svg>
      </div>

      <div className="grid grid-cols-2 gap-4 px-5 pb-4">
        <div>
          {loading ? (
            <div className="h-7 w-10 animate-pulse rounded bg-white/10" />
          ) : (
            <div className="landing-display text-2xl">{total}</div>
          )}
          <div className="text-xs text-[var(--l-cream)]/50">Total agents</div>
        </div>
        <div>
          {loading ? (
            <div className="h-7 w-10 animate-pulse rounded bg-white/10" />
          ) : (
            <div className="landing-display text-2xl">{active}</div>
          )}
          <div className="text-xs text-[var(--l-cream)]/50">Active</div>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-white/10 bg-black/20 px-5 py-3">
        <span className="text-xs text-[var(--l-cream)]/60">Fleet health</span>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
            {!loading && (
              <motion.div
                className="h-full rounded-full bg-[var(--l-teal-soft)]"
                initial={{ width: 0 }}
                animate={{ width: `${health.pct}%` }}
                transition={{ duration: 0.7, ease: "easeOut", delay: 0.2 }}
              />
            )}
          </div>
          <span className="text-xs font-medium text-[var(--l-teal-soft)]">
            {loading ? "…" : health.label}
          </span>
        </div>
      </div>
    </div>
  );
}
