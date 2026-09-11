"use client";

import { motion } from "framer-motion";
import { Timer } from "lucide-react";
import { money } from "./settings-types";

/** The enforced cap every agent in this org is held to — not advisory, read directly from config. */
export function BudgetCard({ capUsd, windowHours }: { capUsd: number; windowHours: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.12 }}
      className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
    >
      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--l-charcoal)]/45">
        <Timer className="h-3 w-3" />
        Enforced budget cap
      </span>

      <div className="mt-2 flex items-end gap-2">
        <span className="landing-display text-3xl text-[var(--l-ink)]">{money(capUsd)}</span>
        <span className="mb-1 font-mono text-[11px] text-[var(--l-charcoal)]/50">per agent, every {windowHours}h</span>
      </div>

      <p className="mt-3 text-[12px] leading-relaxed text-[var(--l-charcoal)]/60">
        Every agent is auto-suspended the moment its rolling {windowHours}-hour spend crosses this
        cap, read live from the running server's configuration, not a setting this page can change.
      </p>
    </motion.div>
  );
}
