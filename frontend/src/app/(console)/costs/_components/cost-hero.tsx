"use client";

import { useEffect, useState } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { Receipt, Flame, ShieldAlert } from "lucide-react";
import { money } from "./cost-types";

/** Counts up from 0 to `value` once, the way a receipt printer's total ticks over. */
function CountUp({ value, prefix = "" }: { value: number; prefix?: string }) {
  const mv = useMotionValue(0);
  const [display, setDisplay] = useState("0.00");
  const rounded = useTransform(mv, (v) => v);

  useEffect(() => {
    const controls = animate(mv, value, {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v >= 0.01 || v === 0 ? v.toFixed(2) : v.toFixed(4)),
    });
    return controls.stop;
  }, [value, mv]);

  void rounded;
  return (
    <span>
      {prefix}
      {display}
    </span>
  );
}

export function CostHero({
  totalAllTime,
  window24h,
  nearCapCount,
}: {
  totalAllTime: number | null;
  window24h: number | null;
  nearCapCount: number | null;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
      >
        <div className="flex items-center gap-2 text-[var(--l-charcoal)]/50">
          <Receipt className="h-4 w-4" />
          <span className="font-mono text-[10.5px] uppercase tracking-wide">Total spend, all time</span>
        </div>
        <p className="landing-display mt-2 text-3xl text-[var(--l-ink)]">
          {totalAllTime === null ? (
            <span className="inline-block h-8 w-24 animate-pulse rounded bg-[var(--l-line)]" />
          ) : (
            <CountUp value={totalAllTime} prefix="$" />
          )}
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.06 }}
        className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
      >
        <div className="flex items-center gap-2 text-[var(--l-charcoal)]/50">
          <Flame className="h-4 w-4" />
          <span className="font-mono text-[10.5px] uppercase tracking-wide">Current 24h window</span>
        </div>
        <p className="landing-display mt-2 text-3xl text-[var(--l-ink)]">
          {window24h === null ? (
            <span className="inline-block h-8 w-24 animate-pulse rounded bg-[var(--l-line)]" />
          ) : (
            <CountUp value={window24h} prefix="$" />
          )}
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.12 }}
        className="rounded-2xl border-2 p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
        style={{
          borderColor: nearCapCount ? "var(--l-orange-deep)" : "var(--l-ink)",
          background: nearCapCount
            ? "color-mix(in srgb, var(--l-orange-deep) 6%, var(--l-cream))"
            : "var(--l-cream)",
          opacity: 0.9 + 0.1,
        }}
      >
        <div className="flex items-center gap-2 text-[var(--l-charcoal)]/50">
          <ShieldAlert className="h-4 w-4" />
          <span className="font-mono text-[10.5px] uppercase tracking-wide">Near their cap</span>
        </div>
        <p
          className="landing-display mt-2 text-3xl"
          style={{ color: nearCapCount ? "var(--l-orange-deep)" : "var(--l-ink)" }}
        >
          {nearCapCount === null ? (
            <span className="inline-block h-8 w-10 animate-pulse rounded bg-[var(--l-line)]" />
          ) : (
            nearCapCount
          )}
        </p>
      </motion.div>
    </div>
  );
}
