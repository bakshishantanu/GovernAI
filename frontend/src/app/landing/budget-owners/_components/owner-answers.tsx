"use client";

import { motion } from "framer-motion";

/**
 * What changes, stated as the sentence a budget owner can now finish.
 *
 * Deliberately framed as before/after rather than a feature grid: this
 * persona does not buy features, they buy the ability to answer a question
 * in a meeting without promising to follow up.
 */

const SHIFTS = [
  {
    before: "We think it's a few hundred a month?",
    after: "$26.02 today, across four agents, itemised.",
    tint: "var(--l-orange)",
  },
  {
    before: "I'd have to ask whoever built it.",
    after: "Every agent has one named owner on the board.",
    tint: "var(--l-teal)",
  },
  {
    before: "We'd find out when the bill arrives.",
    after: "It pauses itself at the cap. Nobody finds out late.",
    tint: "var(--l-yellow-deep)",
  },
  {
    before: "We'd need someone to redeploy it.",
    after: "You suspend it yourself, in one click.",
    tint: "var(--l-orange-soft)",
  },
];

export function OwnerAnswers() {
  return (
    <section className="relative bg-[var(--l-cream)] py-28 md:py-36 overflow-hidden">
      <div
        aria-hidden
        className="landing-blob absolute -right-40 top-10 h-[24rem] w-[24rem] bg-[var(--l-yellow-pale)] opacity-50"
      />

      <div className="relative max-w-5xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="max-w-2xl"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold">
            The difference
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-5xl leading-[1.05] tracking-tight text-[var(--l-charcoal)]">
            Same questions. Different answers.
          </h2>
        </motion.div>

        <div className="mt-14 space-y-4">
          {SHIFTS.map((s, i) => (
            <motion.div
              key={s.before}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.5 }}
              transition={{ duration: 0.5, delay: i * 0.08, ease: "easeOut" }}
              className="grid md:grid-cols-2 gap-3 md:gap-5 items-stretch"
            >
              <div className="rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream-deep)]/60 px-6 py-5">
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--l-charcoal)]/40">
                  Before
                </span>
                <p className="mt-2 text-[var(--l-charcoal)]/55 line-through decoration-[var(--l-charcoal)]/25">
                  {s.before}
                </p>
              </div>

              <div
                className="rounded-2xl px-6 py-5 text-white shadow-[0_6px_0_0_rgba(22,19,14,0.14)]"
                style={{ background: s.tint }}
              >
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-white/70">
                  Now
                </span>
                <p className="mt-2 font-semibold leading-snug">{s.after}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
