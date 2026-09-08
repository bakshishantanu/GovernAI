"use client";

import { motion } from "framer-motion";
import { Plus } from "lucide-react";

/** Sits first in the grid, same footprint as a passport card, so building an agent reads as "the next blank passport" rather than a separate action bolted on top of the roster. */
export function NewAgentTile({ onClick, index }: { onClick: () => void; index: number }) {
  return (
    <motion.button
      onClick={onClick}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.07, ease: "easeOut" }}
      whileHover={{ y: -6 }}
      className="group flex min-h-[236px] flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[var(--l-ink)]/25 bg-transparent text-[var(--l-charcoal)]/50 transition-colors hover:border-[var(--l-orange)] hover:text-[var(--l-orange-deep)]"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-current transition-transform group-hover:rotate-90 group-hover:scale-110">
        <Plus className="h-5 w-5" />
      </span>
      <span className="landing-display text-sm">New agent</span>
    </motion.button>
  );
}
