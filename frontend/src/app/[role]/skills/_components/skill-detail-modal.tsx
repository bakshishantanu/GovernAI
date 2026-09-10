"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, ShieldCheck, Bot, FileSearch, Database, Ticket } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { accentFor, type Skill } from "./skill-types";

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  sql_query: Database,
};

/**
 * The "Read more" destination — full tool list with each tool's real
 * required permission, not just the skill-level summary the card shows.
 * This is the whole point of a skill/agent split: a builder needs to see
 * exactly what binding this skill grants before choosing it.
 */
export function SkillDetailModal({
  skill,
  onClose,
}: {
  skill: Skill | null;
  onClose: () => void;
}) {
  const Icon = skill ? SKILL_ICON[skill.id] ?? Bot : Bot;
  const accent = skill ? accentFor(skill.id) : accentFor("");

  return (
    <AnimatePresence>
      {skill && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={skill.display_name}
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="fixed left-1/2 top-1/2 z-50 w-[min(560px,92vw)] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-3xl border-2 bg-[var(--l-cream)] shadow-2xl"
            style={{ borderColor: accent.ring, maxHeight: "85vh" }}
          >
            <div className="flex max-h-[85vh] flex-col">
              <div
                className="relative flex shrink-0 items-center gap-3 px-6 py-5"
                style={{ background: `${accent.bg}1a` }}
              >
                <span
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2"
                  style={{ borderColor: accent.ring, background: "var(--l-cream)" }}
                >
                  <Icon className="h-5 w-5" style={{ color: accent.fg }} />
                </span>
                <div className="min-w-0">
                  <h2 className="landing-display truncate text-xl text-[var(--l-ink)]">
                    {skill.display_name}
                  </h2>
                  <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-[var(--l-charcoal)]/60">
                    <ShieldCheck className="h-3 w-3" style={{ color: accent.fg }} />
                    {skill.trust_level} · v{skill.version}
                  </div>
                </div>
                <button
                  onClick={onClose}
                  aria-label="Close"
                  className="ml-auto flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--l-cream)] text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="overflow-y-auto px-6 py-5">
                <p className="text-sm leading-relaxed text-[var(--l-charcoal)]/80">
                  {skill.description}
                </p>

                <div className="mt-5 flex items-center gap-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Grants, if bound to an agent
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {skill.required_permissions.map((p) => (
                    <code
                      key={p}
                      className="rounded-md bg-[var(--l-ink)]/5 px-2 py-1 font-mono text-[11px] text-[var(--l-ink)]"
                    >
                      {p}
                    </code>
                  ))}
                </div>

                <div className="mt-6 space-y-3">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Tools ({skill.tools.length})
                  </span>
                  {skill.tools.map((tool, i) => (
                    <motion.div
                      key={tool.name}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.25, delay: 0.1 + i * 0.06 }}
                      className="rounded-xl border border-[var(--l-line)] bg-[var(--l-cream-deep)]/50 p-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <code className="font-mono text-[13px] font-semibold text-[var(--l-ink)]">
                          {tool.name}
                        </code>
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-[var(--l-charcoal)]/70">
                        {tool.description}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {tool.required_permission.split(",").map((p) => (
                          <code
                            key={p}
                            className="rounded bg-[var(--l-ink)]/5 px-1.5 py-0.5 font-mono text-[10px] text-[var(--l-charcoal)]/70"
                          >
                            {p.trim()}
                          </code>
                        ))}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
