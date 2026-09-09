"use client";

import { motion } from "framer-motion";
import { Search } from "lucide-react";

const FILTERS = ["All", "Active", "Draft", "Suspended", "Revoked"] as const;
export type RosterFilter = (typeof FILTERS)[number];

export function RosterControls({
  query,
  onQuery,
  filter,
  onFilter,
  counts,
}: {
  query: string;
  onQuery: (v: string) => void;
  filter: RosterFilter;
  onFilter: (f: RosterFilter) => void;
  counts: Record<RosterFilter, number>;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-1.5 rounded-full border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 p-1">
        {FILTERS.map((f) => {
          const isOn = filter === f;
          return (
            <button
              key={f}
              onClick={() => onFilter(f)}
              className="relative rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors"
              style={{ color: isOn ? "#ffffff" : "var(--l-charcoal)" }}
            >
              {isOn && (
                <motion.span
                  layoutId="roster-filter-pill"
                  className="absolute inset-0 rounded-full bg-[var(--l-ink)]"
                  transition={{ type: "spring", stiffness: 500, damping: 36 }}
                />
              )}
              <span className="relative z-10">
                {f}
                {counts[f] > 0 && (
                  <span className="ml-1 font-mono opacity-70">{counts[f]}</span>
                )}
              </span>
            </button>
          );
        })}
      </div>

      <label className="flex h-10 items-center gap-2 rounded-full border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-3.5">
        <Search className="h-3.5 w-3.5 text-[var(--l-charcoal)]/50" />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search the roster"
          className="w-40 bg-transparent text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/40 focus:outline-none"
        />
      </label>
    </div>
  );
}
