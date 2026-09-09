"use client";

import { useEffect, useRef, useState, type ElementType } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Ticket,
  Database,
  FileSearch,
  Telescope,
  Terminal,
  CalendarClock,
  MessageSquare,
  X,
} from "lucide-react";

type Skill = {
  status: "LIVE" | "IN THE LAB";
  name: string;
  body: string;
  detail: string;
  tags: string[];
  bg: string;
  fg: string;
  icon: ElementType;
  dashed?: boolean;
};

const TAG_CHIPS = [
  { bg: "var(--l-yellow)", fg: "var(--l-ink)" },
  { bg: "var(--l-orange)", fg: "white" },
  { bg: "var(--l-teal)", fg: "white" },
  { bg: "var(--l-cream)", fg: "var(--l-charcoal)" },
];

// resting tilt per card, alternating so the row reads as independently
// placed cards, not a machined grid — same idea as the reference's
// per-item random rotation on its book slider
const ROTATIONS = [-2, 2, -1.5, 1.5, -2, 1, -1];

const SKILLS: Skill[] = [
  {
    status: "LIVE",
    name: "Ticketing",
    body: "Read tickets, search across queues, and post replies, scoped to exactly the permissions the agent's passport grants.",
    detail:
      "Wraps a ticketing backend behind three tools: read_ticket, search_tickets, and create_ticket_reply. Every call passes through the policy gate first, an agent without ticket:write can search and read but never reply. Currently running against a mock adapter by design, so a real backend can be swapped in later without the skill's tools changing at all.",
    tags: ["read_ticket", "search_tickets", "create_ticket_reply"],
    bg: "var(--l-teal)",
    fg: "var(--l-cream)",
    icon: Ticket,
  },
  {
    status: "LIVE",
    name: "SQL Query",
    body: "Read-only queries, validated at the AST level rather than a regex blocklist, so an agent can query real data without ever mutating it.",
    detail:
      "Every query is parsed to an AST with sqlglot, not matched against a regex blocklist, so it's confirmed structurally read-only (no INSERT, UPDATE, DELETE, or DDL) and confirmed in-scope, table by table. Execution also runs over a genuinely read-only database connection underneath, so validation isn't the only thing standing between an agent and a write.",
    tags: ["Read-only", "AST-validated", "In-scope tables only"],
    bg: "var(--l-navy-deep)",
    fg: "var(--l-cream)",
    icon: Database,
  },
  {
    status: "LIVE",
    name: "Document Search",
    body: "Semantic search over your internal docs, with access-scope filtering enforced before ranking, never after.",
    detail:
      "Semantic search over your internal documents. Access-scope filtering happens inside the retrieval query itself, before ranking, so an out-of-scope document is never seen by the scoring step, not filtered out after the fact. Every answer comes back grounded with citations to the chunks it was drawn from.",
    tags: ["Semantic", "Scope-filtered", "Citation-grounded"],
    bg: "var(--l-orange)",
    fg: "white",
    icon: FileSearch,
  },
  {
    status: "IN THE LAB",
    name: "Research",
    body: "Multi-source web research that comes back as structured findings, not a pile of tabs for a human to sift through.",
    detail:
      "Not built yet. The idea: multi-source web research that comes back as structured findings a downstream agent step can actually use, instead of a pile of links for a human to sift through.",
    tags: ["Multi-source", "Structured output"],
    bg: "var(--l-cream)",
    fg: "var(--l-charcoal)",
    icon: Telescope,
    dashed: true,
  },
  {
    status: "IN THE LAB",
    name: "Code Sandbox",
    body: "Run and test snippets in an isolated, time-boxed sandbox, no network, no filesystem, nothing it can reach beyond the run itself.",
    detail:
      "Not built yet. The idea: run and test a snippet in an isolated, time-boxed sandbox, no network, no filesystem, nothing reachable beyond the run itself.",
    tags: ["Isolated", "Time-boxed"],
    bg: "var(--l-cream)",
    fg: "var(--l-charcoal)",
    icon: Terminal,
    dashed: true,
  },
  {
    status: "IN THE LAB",
    name: "Calendar & Scheduling",
    body: "Propose, book, and reschedule meetings inside the owner's own calendar policy, never outside it.",
    detail:
      "Not built yet. The idea: propose, book, and reschedule meetings inside the owner's own calendar policy, never outside it, no double-booking, no access beyond what the owner already shares.",
    tags: ["Owner-scoped", "Policy-aware"],
    bg: "var(--l-cream)",
    fg: "var(--l-charcoal)",
    icon: CalendarClock,
    dashed: true,
  },
  {
    status: "IN THE LAB",
    name: "Slack Messaging",
    body: "Post and read in scoped channels only, no DMs, no reading history outside the agent's own permission set.",
    detail:
      "Not built yet. The idea: post and read in scoped channels only, no DMs, no reading history outside the agent's own permission set, same governance model as every other skill.",
    tags: ["Channel-scoped", "No DMs"],
    bg: "var(--l-cream)",
    fg: "var(--l-charcoal)",
    icon: MessageSquare,
    dashed: true,
  },
];

function BrewingDots({ color }: { color: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: color }}
          animate={{ y: [0, -4, 0] }}
          transition={{
            duration: 0.9,
            repeat: Infinity,
            delay: i * 0.15,
            ease: "easeInOut",
          }}
        />
      ))}
    </span>
  );
}

export function SkillMarketplace() {
  const [openSkill, setOpenSkill] = useState<Skill | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  useEffect(() => {
    document.body.style.overflow = openSkill ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [openSkill]);

  useEffect(() => {
    if (!openSkill) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpenSkill(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openSkill]);

  const updateEdges = () => {
    const el = trackRef.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  };

  const scrollByCard = (dir: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 280, behavior: "smooth" });
  };

  return (
    <section id="skills" className="relative bg-[var(--l-cream-deep)] py-28 md:py-36 overflow-hidden">
      <div className="max-w-6xl mx-auto px-6 flex items-end justify-between gap-6 flex-wrap">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="max-w-xl"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold">
            Assembled, not built from scratch
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-6xl text-[var(--l-charcoal)] leading-[1] tracking-tight">
            Pick your skills.
          </h2>
        </motion.div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => scrollByCard(-1)}
            disabled={atStart}
            aria-label="Scroll skills left"
            className="w-11 h-11 rounded-full bg-white border border-[var(--l-line)] flex items-center justify-center text-[var(--l-charcoal)] disabled:opacity-30 hover:border-[var(--l-orange)] hover:text-[var(--l-orange)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => scrollByCard(1)}
            disabled={atEnd}
            aria-label="Scroll skills right"
            className="w-11 h-11 rounded-full bg-[var(--l-charcoal)] flex items-center justify-center text-white disabled:opacity-30 hover:bg-[var(--l-orange)] transition-colors"
          >
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div
        ref={trackRef}
        onScroll={updateEdges}
        className="landing-hide-scrollbar mt-12 flex gap-5 overflow-x-auto px-6 pt-6 pb-6 snap-x snap-mandatory"
      >
        {SKILLS.map((s, i) => {
          const Icon = s.icon;
          const rotate = ROTATIONS[i % ROTATIONS.length];
          return (
            <motion.button
              type="button"
              key={s.name}
              onClick={() => setOpenSkill(s)}
              initial={{
                opacity: 0,
                scale: 0.5,
                rotate: rotate + (i % 2 === 0 ? -22 : 22),
              }}
              whileInView={{ opacity: 1, scale: 1, rotate }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{
                type: "spring",
                stiffness: 240,
                damping: 15,
                delay: (i % 7) * 0.06,
              }}
              whileHover={{ y: -10, scale: 1.05, rotate: 0 }}
              whileTap={{ scale: 0.98 }}
              className={`group relative shrink-0 w-52 md:w-56 min-h-[350px] overflow-hidden rounded-[24px] p-5 flex flex-col text-left cursor-pointer snap-start shadow-lg shadow-black/10 hover:shadow-2xl hover:shadow-black/20 ${
                s.dashed ? "border-2 border-dashed border-[var(--l-line)]" : ""
              }`}
              style={{ background: s.dashed ? "transparent" : s.bg, color: s.fg }}
            >
              <Icon
                className="pointer-events-none absolute -bottom-6 -right-6 w-32 h-32 transition-transform duration-500 group-hover:scale-110 group-hover:-rotate-6"
                style={{ opacity: s.dashed ? 0.06 : 0.14 }}
                strokeWidth={1}
              />

              <span
                className={`relative self-start text-[10px] font-semibold uppercase tracking-[0.12em] px-2.5 py-1 rounded-full ${
                  s.dashed ? "border border-current opacity-60" : "bg-black/15"
                }`}
              >
                {s.status}
              </span>

              <div className="relative mt-auto pt-6">
                <h3 className="landing-display text-xl leading-none">{s.name}</h3>
                <p
                  className="mt-2.5 text-xs leading-relaxed"
                  style={{ opacity: s.dashed ? 0.65 : 0.8 }}
                >
                  {s.body}
                </p>

                {s.dashed ? (
                  <div className="mt-5 flex items-center gap-2 text-xs uppercase tracking-wide opacity-60">
                    <BrewingDots color={s.fg} />
                    brewing
                  </div>
                ) : (
                  <div className="relative mt-5 h-8">
                    <div className="absolute inset-0 flex flex-wrap items-center gap-1.5 transition-all duration-300 group-hover:opacity-0 group-hover:-translate-y-1">
                      {s.tags.map((t, ti) => {
                        const chip = TAG_CHIPS[ti % TAG_CHIPS.length];
                        return (
                          <span
                            key={t}
                            className="text-[10px] font-mono px-2 py-1 rounded-full"
                            style={{ background: chip.bg, color: chip.fg }}
                          >
                            {t}
                          </span>
                        );
                      })}
                    </div>

                    <span className="absolute inset-0 flex items-center opacity-0 translate-y-1 transition-all duration-300 group-hover:opacity-100 group-hover:translate-y-0">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--l-orange)] text-white text-xs font-semibold pl-3.5 pr-2.5 py-1.5">
                        Read more
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </span>
                    </span>
                  </div>
                )}
              </div>
            </motion.button>
          );
        })}
        <div className="shrink-0 w-2 md:w-6" aria-hidden="true" />
      </div>

      <AnimatePresence>
        {openSkill && (
          <motion.div
            className="fixed inset-0 z-[100] flex items-center justify-center p-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="absolute inset-0 bg-[var(--l-navy-deep)]/60 backdrop-blur-sm"
              onClick={() => setOpenSkill(null)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />

            <motion.div
              role="dialog"
              aria-modal="true"
              initial={{ opacity: 0, scale: 0.9, y: 24 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 12 }}
              transition={{ type: "spring", stiffness: 300, damping: 28 }}
              className="relative w-full max-w-md rounded-[28px] p-8 shadow-2xl"
              style={{
                background: openSkill.dashed ? "var(--l-cream)" : openSkill.bg,
                color: openSkill.dashed ? "var(--l-charcoal)" : openSkill.fg,
              }}
            >
              <button
                type="button"
                onClick={() => setOpenSkill(null)}
                aria-label="Close"
                className="absolute top-5 right-5 w-8 h-8 rounded-full bg-black/10 hover:bg-black/20 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>

              <span
                className={`inline-block text-[10px] font-semibold uppercase tracking-[0.12em] px-2.5 py-1 rounded-full ${
                  openSkill.dashed ? "border border-current opacity-60" : "bg-black/15"
                }`}
              >
                {openSkill.status}
              </span>

              <h3 className="landing-display mt-5 text-3xl leading-none">
                {openSkill.name}
              </h3>

              <p className="mt-4 text-sm leading-relaxed opacity-80">
                {openSkill.detail}
              </p>

              {!openSkill.dashed && (
                <div className="mt-6 flex flex-wrap gap-1.5">
                  {openSkill.tags.map((t, ti) => {
                    const chip = TAG_CHIPS[ti % TAG_CHIPS.length];
                    return (
                      <span
                        key={t}
                        className="text-[10px] font-mono px-2 py-1 rounded-full"
                        style={{ background: chip.bg, color: chip.fg }}
                      >
                        {t}
                      </span>
                    );
                  })}
                </div>
              )}

              {openSkill.dashed && (
                <div className="mt-6 flex items-center gap-2 text-xs uppercase tracking-wide opacity-60">
                  <BrewingDots color="var(--l-charcoal)" />
                  brewing
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
