"use client";

import { motion, useReducedMotion } from "framer-motion";

/** Animated circular-progress stat, e.g. "67% Fleet health". */
export function StatRing({
  pct,
  value,
  label,
  color,
  loading,
}: {
  pct: number;
  value: string;
  label: string;
  color: string;
  loading?: boolean;
}) {
  const still = useReducedMotion();
  const r = 22;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, pct));

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream)] px-4 py-3">
      <svg width="52" height="52" viewBox="0 0 52 52" className="shrink-0 -rotate-90">
        <circle cx="26" cy="26" r={r} fill="none" stroke="var(--l-line)" strokeWidth="5" />
        {!loading && (
          <motion.circle
            cx="26"
            cy="26"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={c}
            initial={{ strokeDashoffset: c }}
            animate={{ strokeDashoffset: c - (clamped / 100) * c }}
            transition={still ? { duration: 0 } : { duration: 0.9, ease: "easeOut", delay: 0.15 }}
          />
        )}
      </svg>
      <div>
        {loading ? (
          <div className="h-6 w-12 animate-pulse rounded bg-[var(--l-line)]" />
        ) : (
          <div className="landing-display text-xl text-[var(--l-ink)]">{value}</div>
        )}
        <div className="text-xs text-[var(--l-charcoal)]/60">{label}</div>
      </div>
    </div>
  );
}
