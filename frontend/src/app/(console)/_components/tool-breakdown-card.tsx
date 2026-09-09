"use client";

import { motion } from "framer-motion";
import { Wrench } from "lucide-react";
import type { ToolCount } from "./dashboard-data";

/** Real tool-call counts, ranked. Replaces the reference's region map with the equivalent this product actually has: which tools agents are reaching for. */
export function ToolBreakdownCard({
  tools,
  loading,
}: {
  tools: ToolCount[];
  loading?: boolean;
}) {
  const max = Math.max(1, ...tools.map((t) => t.count));

  return (
    <div className="flex h-full flex-col rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream)] p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="h-4 w-4 text-[var(--l-orange)]" />
          <span className="landing-display text-lg text-[var(--l-ink)]">Tools reached for</span>
        </div>
      </div>

      {loading ? (
        <div className="space-y-2.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-8 animate-pulse rounded-lg bg-[var(--l-line)]/60" />
          ))}
        </div>
      ) : tools.length === 0 ? (
        <p className="text-sm text-[var(--l-charcoal)]/60">No tool calls recorded yet.</p>
      ) : (
        <div className="flex-1 space-y-3">
          {tools.slice(0, 5).map((t, i) => (
            <motion.div
              key={t.tool}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.06 }}
            >
              <div className="mb-1 flex items-baseline justify-between text-xs">
                <code className="font-mono text-[var(--l-ink)]">{t.tool}</code>
                <span className="tabular-nums text-[var(--l-charcoal)]/60">
                  {t.count}
                  {t.denied > 0 && (
                    <span className="ml-1 text-[var(--l-orange-deep)]">({t.denied} denied)</span>
                  )}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--l-line)]">
                <motion.div
                  className="h-full rounded-full bg-[var(--l-orange)]"
                  initial={{ width: 0 }}
                  animate={{ width: `${(t.count / max) * 100}%` }}
                  transition={{ duration: 0.5, delay: 0.15 + i * 0.06, ease: "easeOut" }}
                />
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-[var(--l-line)] pt-3 text-xs text-[var(--l-charcoal)]/50">
        <span>{tools.length} distinct tools</span>
        <div className="flex items-center gap-1.5">
          <span>Fewer calls</span>
          <span className="h-1.5 w-14 rounded-full bg-gradient-to-r from-[var(--l-cream-deep)] to-[var(--l-orange)]" />
          <span>More</span>
        </div>
      </div>
    </div>
  );
}
