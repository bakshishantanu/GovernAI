"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

/**
 * One dashboard stat tile. `loading` renders a pulse in place of the value
 * rather than a stale "0" — a 0 that turns out to be "still fetching" reads
 * as a real (wrong) answer, which is worse than visibly not knowing yet.
 */
export function StatTile({
  icon: Icon,
  label,
  value,
  tint,
  loading,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tint: string;
  loading?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream-deep)]/50 p-5"
    >
      <div className="flex items-center gap-2 text-[var(--l-charcoal)]/60">
        <Icon className="h-4 w-4" style={{ color: tint }} />
        <span className="text-sm font-medium">{label}</span>
      </div>
      {loading ? (
        <div className="mt-3 h-8 w-16 animate-pulse rounded-md bg-[var(--l-line)]" />
      ) : (
        <div className="landing-display mt-2 text-3xl text-[var(--l-ink)]">{value}</div>
      )}
    </motion.div>
  );
}
