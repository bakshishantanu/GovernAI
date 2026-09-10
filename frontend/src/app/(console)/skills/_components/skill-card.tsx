"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ShieldCheck, Bot, FileSearch, Database, Ticket, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { accentFor, type Skill } from "./skill-types";

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  solr_search: Search,
  sql_query: Database,
};

/** Alternating tilt per position, mirroring a fanned deck of cards. */
const TILT = [-6, 4, -3, 5, -4];

/**
 * One skill, styled as a fanned card — inspired by the reference book-club
 * carousel: a tilted deck that straightens and lifts on hover, a themed
 * accent per item, tag pills at the base, and a "Read more" into the full
 * detail. Cover art is a real skill icon on a tinted panel rather than
 * invented illustration.
 */
export function SkillCard({
  skill,
  index,
  onReadMore,
}: {
  skill: Skill;
  index: number;
  onReadMore: () => void;
}) {
  const still = useReducedMotion();
  const accent = accentFor(skill.id);
  const Icon = SKILL_ICON[skill.id] ?? Bot;
  const tilt = still ? 0 : TILT[index % TILT.length];

  return (
    <motion.div
      initial={{ opacity: 0, y: 40, rotate: 0 }}
      animate={{ opacity: 1, y: 0, rotate: tilt }}
      transition={{ duration: 0.5, delay: index * 0.12, ease: "easeOut" }}
      whileHover={still ? undefined : { rotate: 0, y: -14, scale: 1.04, zIndex: 20 }}
      className="relative w-64 shrink-0 cursor-default"
      style={{ zIndex: 10 - index }}
    >
      <div
        className="flex h-[380px] flex-col overflow-hidden rounded-3xl border-2 bg-[var(--l-cream)] shadow-[0_10px_0_0_rgba(22,19,14,0.14)]"
        style={{ borderColor: accent.ring }}
      >
        {/* "cover" panel — a real icon, tinted, standing in for artwork */}
        <div
          className="relative flex h-40 shrink-0 items-center justify-center"
          style={{ background: `${accent.bg}1a` }}
        >
          <span
            className="absolute left-3 top-3 rounded-full border border-black/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide"
            style={{ background: "var(--l-cream)", color: accent.fg }}
          >
            {skill.trust_level}
          </span>
          <span
            className="flex h-11 w-11 items-center justify-center rounded-full border-2"
            style={{ borderColor: accent.ring, background: "var(--l-cream)" }}
          >
            <ShieldCheck className="h-4 w-4" style={{ color: accent.fg }} />
          </span>
          <Icon className="h-16 w-16" style={{ color: accent.fg, opacity: 0.85 }} strokeWidth={1.5} />
        </div>

        {/* body */}
        <div className="flex flex-1 flex-col p-4">
          <h3 className="landing-display text-lg leading-tight text-[var(--l-ink)]">
            {skill.display_name}
          </h3>
          <p className="mt-1.5 line-clamp-3 text-[12.5px] leading-relaxed text-[var(--l-charcoal)]/70">
            {skill.description}
          </p>

          <div className="mt-2.5 flex flex-wrap gap-1.5">
            <span className="rounded-full bg-[var(--l-cream-deep)] px-2 py-0.5 font-mono text-[10px] text-[var(--l-charcoal)]/60">
              v{skill.version}
            </span>
            <span className="rounded-full bg-[var(--l-cream-deep)] px-2 py-0.5 font-mono text-[10px] text-[var(--l-charcoal)]/60">
              {skill.tools.length} tool{skill.tools.length === 1 ? "" : "s"}
            </span>
          </div>

          <button
            onClick={onReadMore}
            className="mt-auto flex w-fit items-center gap-1.5 self-end rounded-full px-3.5 py-1.5 text-xs font-semibold text-white transition-transform hover:-translate-y-0.5"
            style={{ background: accent.bg }}
          >
            Read more
            <span aria-hidden>→</span>
          </button>
        </div>
      </div>
    </motion.div>
  );
}
