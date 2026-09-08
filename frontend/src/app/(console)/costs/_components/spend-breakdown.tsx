"use client";

import { motion } from "framer-motion";
import { money } from "./cost-types";

const PALETTE = ["var(--l-orange)", "var(--l-teal)", "var(--l-navy-deep)", "var(--l-charcoal)"];

/** A ranked ledger of spend by one dimension (agent or model) — bars scaled to the top entry. */
export function SpendBreakdown({
  title,
  rows,
  loading,
}: {
  title: string;
  rows: { label: string; value: number }[];
  loading: boolean;
}) {
  const max = Math.max(1e-9, ...rows.map((r) => r.value));

  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]">
      <h2 className="landing-display text-base text-[var(--l-ink)]">{title}</h2>

      <div className="mt-3 space-y-2.5">
        {loading ? (
          [0, 1, 2].map((i) => <div key={i} className="h-9 animate-pulse rounded-lg bg-[var(--l-line)]/50" />)
        ) : rows.length === 0 ? (
          <p className="py-4 text-center text-[12.5px] text-[var(--l-charcoal)]/50">No spend recorded yet.</p>
        ) : (
          rows.map((row, i) => (
            <motion.div
              key={row.label}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
            >
              <div className="flex items-baseline justify-between">
                <span className="truncate text-[12.5px] font-medium text-[var(--l-ink)]">{row.label}</span>
                <span className="shrink-0 font-mono text-[12px] text-[var(--l-charcoal)]/70">
                  {money(row.value)}
                </span>
              </div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[var(--l-ink)]/8">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: PALETTE[i % PALETTE.length] }}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.max(3, (row.value / max) * 100)}%` }}
                  transition={{ duration: 0.6, delay: 0.1 + i * 0.05, ease: "easeOut" }}
                />
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
