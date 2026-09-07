"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import { Wallet, TriangleAlert } from "lucide-react";

const CAP = 25;

export function CostGovernance() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const [spend, setSpend] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (!inView) return;
    let raf: number;
    const start = performance.now();
    const duration = 2600;

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const value = t * CAP * 1.08; // slightly overshoot the cap to trigger pause
      setSpend(Math.min(value, CAP * 1.08));
      if (value >= CAP) setPaused(true);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView]);

  const pct = Math.min(100, (spend / CAP) * 100);

  return (
    <section
      id="cost"
      className="relative bg-[var(--l-navy-deep)] text-[var(--l-ink)] py-28 md:py-36 overflow-hidden"
    >
      <div className="landing-noise absolute inset-0 pointer-events-none" />
      <div className="max-w-6xl mx-auto px-6 relative grid md:grid-cols-2 gap-16 items-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange-soft)] font-semibold">
            The headline USP
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-5xl leading-[1.03] tracking-tight">
            Live cost governance. Not a dashboard you check later.
          </h2>
          <p className="mt-5 text-[var(--l-ink)]/60 leading-relaxed max-w-md">
            Every agent gets a real spending budget that auto-pauses it the moment
            it&apos;s exceeded. Most governance platforms treat cost as an
            afterthought — GovernAI makes it the primary, demoable feature.
          </p>
        </motion.div>

        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="rounded-3xl border border-[var(--l-line-dark)] bg-white/[0.03] p-8"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-[var(--l-ink)]/60">
              <Wallet className="w-4 h-4" />
              Invoice Triage Bot — daily budget
            </div>
            {paused && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-1.5 text-xs font-medium text-[#e07a6b] bg-[#e07a6b]/10 border border-[#e07a6b]/30 rounded-full px-2.5 py-1"
              >
                <TriangleAlert className="w-3 h-3" />
                Auto-suspended
              </motion.div>
            )}
          </div>

          <div className="mt-6 flex items-baseline gap-2">
            <span className="text-4xl font-mono font-semibold">
              ${spend.toFixed(2)}
            </span>
            <span className="text-[var(--l-ink)]/40 text-sm">
              / ${CAP.toFixed(2)} cap
            </span>
          </div>

          <div className="mt-4 h-3 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              className={`h-full rounded-full ${
                paused ? "bg-[#e07a6b]" : "bg-[var(--l-teal-soft)]"
              }`}
              style={{ width: `${pct}%` }}
              transition={{ ease: "linear" }}
            />
          </div>

          <div className="mt-6 grid grid-cols-3 gap-3 text-center">
            {[
              { label: "Calls today", value: "148" },
              { label: "Blocked", value: "3" },
              { label: "Status", value: paused ? "Paused" : "Active" },
            ].map((s) => (
              <div
                key={s.label}
                className="rounded-xl bg-white/[0.03] border border-[var(--l-line-dark)] py-3"
              >
                <div className="text-sm font-mono">{s.value}</div>
                <div className="text-[10px] uppercase tracking-wide text-[var(--l-ink)]/40 mt-1">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
