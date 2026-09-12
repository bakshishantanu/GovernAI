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
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      {/* overflow-x-auto + flex-nowrap rather than flex-wrap: on a narrow
          screen five pills wrapping into a ragged second row reads worse
          than letting the row scroll horizontally, which is the native,
          expected gesture for a segmented control that doesn't fit. */}
      <div className="flex items-center gap-1.5 overflow-x-auto rounded-full border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 p-1">
        {FILTERS.map((f) => {
          const isOn = filter === f;
          return (
            <button
              key={f}
              onClick={() => onFilter(f)}
              className="relative shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors"
              style={{ color: isOn ? "var(--l-cream)" : "var(--l-charcoal)" }}
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

      <label className="flex h-10 w-full items-center gap-2 rounded-full border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-3.5 sm:w-auto">
        <Search className="h-3.5 w-3.5 shrink-0 text-[var(--l-charcoal)]/50" />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search the roster"
          className="w-full bg-transparent text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/40 focus:outline-none sm:w-40"
        />
      </label>
    </div>
  );
}
