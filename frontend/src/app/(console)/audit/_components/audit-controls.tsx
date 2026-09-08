"use client";

import { motion } from "framer-motion";
import { Search } from "lucide-react";

const DECISIONS = ["All", "Allowed", "Denied"] as const;
export type DecisionFilter = (typeof DECISIONS)[number];

const ACTORS = ["All", "Agent", "User", "System"] as const;
export type ActorFilter = (typeof ACTORS)[number];

export function AuditControls({
  query,
  onQuery,
  decision,
  onDecision,
  actor,
  onActor,
  counts,
}: {
  query: string;
  onQuery: (v: string) => void;
  decision: DecisionFilter;
  onDecision: (f: DecisionFilter) => void;
  actor: ActorFilter;
  onActor: (f: ActorFilter) => void;
  counts: Record<DecisionFilter, number>;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Pills value={decision} onChange={onDecision} options={DECISIONS} layoutId="audit-decision-pill" counts={counts} />
        <Pills value={actor} onChange={onActor} options={ACTORS} layoutId="audit-actor-pill" />
      </div>

      <label className="flex h-10 items-center gap-2 rounded-full border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-3.5">
        <Search className="h-3.5 w-3.5 text-[var(--l-charcoal)]/50" />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search tool, action, agent"
          className="w-48 bg-transparent text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/40 focus:outline-none"
        />
      </label>
    </div>
  );
}

function Pills<T extends string>({
  value,
  onChange,
  options,
  layoutId,
  counts,
}: {
  value: T;
  onChange: (v: T) => void;
  options: readonly T[];
  layoutId: string;
  counts?: Record<string, number>;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-full border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 p-1">
      {options.map((o) => {
        const isOn = value === o;
        return (
          <button
            key={o}
            onClick={() => onChange(o)}
            className="relative rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors"
            style={{ color: isOn ? "#ffffff" : "var(--l-charcoal)" }}
          >
            {isOn && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-full bg-[var(--l-ink)]"
                transition={{ type: "spring", stiffness: 500, damping: 36 }}
              />
            )}
            <span className="relative z-10">
              {o}
              {counts && counts[o] > 0 && <span className="ml-1 font-mono opacity-70">{counts[o]}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
}
