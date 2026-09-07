"use client";

import { useRef, useState, type ElementType } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Ticket,
  Database,
  FileSearch,
  Telescope,
  Terminal,
  CalendarClock,
  MessageSquare,
} from "lucide-react";

type Skill = {
  status: "LIVE" | "IN THE LAB";
  name: string;
  body: string;
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

const SKILLS: Skill[] = [
  {
    status: "LIVE",
    name: "Ticketing",
    body: "Read tickets, search across queues, and post replies, scoped to exactly the permissions the agent's passport grants.",
    tags: ["read_ticket", "search_tickets", "create_ticket_reply"],
    bg: "var(--l-teal)",
    fg: "var(--l-cream)",
    icon: Ticket,
  },
  {
    status: "LIVE",
    name: "SQL Query",
    body: "Read-only queries, validated at the AST level rather than a regex blocklist, so an agent can query real data without ever mutating it.",
    tags: ["Read-only", "AST-validated", "In-scope tables only"],
    bg: "var(--l-navy-deep)",
    fg: "var(--l-cream)",
    icon: Database,
  },
  {
    status: "LIVE",
    name: "Document Search",
    body: "Semantic search over your internal docs, with access-scope filtering enforced before ranking, never after.",
    tags: ["Semantic", "Scope-filtered", "Citation-grounded"],
    bg: "var(--l-orange)",
    fg: "white",
    icon: FileSearch,
  },
  {
    status: "IN THE LAB",
    name: "Research",
    body: "Multi-source web research that comes back as structured findings, not a pile of tabs for a human to sift through.",
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
  const trackRef = useRef<HTMLDivElement>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const updateEdges = () => {
    const el = trackRef.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 4);
  };

  const scrollByCard = (dir: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 320, behavior: "smooth" });
  };

  return (
    <section id="skills" className="relative bg-[var(--l-cream-deep)] py-28 md:py-36 overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex items-end justify-between gap-6 flex-wrap">
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
          className="landing-carousel mt-12 flex gap-5 overflow-x-auto pb-2 snap-x snap-mandatory"
        >
          {SKILLS.map((s, i) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.name}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.5, delay: (i % 4) * 0.08, ease: "easeOut" }}
                whileHover={{ y: -6 }}
                className={`relative shrink-0 w-64 md:w-[19rem] min-h-[460px] overflow-hidden rounded-[28px] p-6 flex flex-col snap-start ${
                  s.dashed ? "border-2 border-dashed border-[var(--l-line)]" : ""
                }`}
                style={{ background: s.dashed ? "transparent" : s.bg, color: s.fg }}
              >
                <Icon
                  className="pointer-events-none absolute -bottom-8 -right-8 w-44 h-44"
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

                <div className="relative mt-auto pt-8">
                  <h3 className="landing-display text-2xl leading-none">{s.name}</h3>
                  <p
                    className="mt-3 text-sm leading-relaxed"
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
                    <div className="mt-5 flex flex-wrap gap-1.5">
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
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
