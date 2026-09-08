"use client";

import { motion } from "framer-motion";
import { ArrowDown } from "lucide-react";

/**
 * Hero.
 *
 * The two questions are lifted verbatim from the PRD's problem statement —
 * they are the actual reason this persona exists, so they are the page's
 * opening statement rather than a claim written around them.
 */

const QUESTIONS = [
  {
    n: "01",
    q: "How much are we spending on AI agents?",
    aside: "asked once a quarter, answered with a shrug",
    bg: "var(--l-orange)",
    fg: "#ffffff",
    rotate: -2.5,
  },
  {
    n: "02",
    q: "Can we pause that one? Right now?",
    aside: "asked once, urgently, at the worst moment",
    bg: "var(--l-teal)",
    fg: "#ffffff",
    rotate: 2,
  },
];

export function OwnerHero() {
  return (
    <section className="relative overflow-hidden bg-[var(--l-yellow)] pt-32 pb-24 md:pt-40 md:pb-32">
      {/* organic grounds, same device as the main page */}
      <div
        aria-hidden
        className="landing-blob absolute -top-24 -left-32 h-[26rem] w-[26rem] bg-[var(--l-yellow-deep)] opacity-70"
      />
      <div
        aria-hidden
        className="landing-blob absolute -bottom-40 -right-24 h-[30rem] w-[30rem] bg-[var(--l-yellow-pale)] opacity-60"
        style={{ animationDelay: "-6s" }}
      />

      <div className="relative max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="max-w-3xl"
        >
          <span className="text-xs uppercase tracking-[0.14em] font-semibold text-[var(--l-ink)]/70">
            For IT &amp; budget owners
          </span>

          <h1 className="landing-display mt-5 text-[2.6rem] leading-[1.02] sm:text-6xl md:text-7xl text-[var(--l-ink)]">
            Two questions you
            <br />
            can&apos;t answer today.
          </h1>

          <p className="mt-6 max-w-xl text-lg leading-relaxed text-[var(--l-ink)]/75">
            Your teams are already running AI agents. Somewhere between the
            invoices and the incident channel, nobody owns the answer to either
            of these.
          </p>
        </motion.div>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 max-w-4xl">
          {QUESTIONS.map((item, i) => (
            <motion.div
              key={item.n}
              initial={{ opacity: 0, y: 32, rotate: 0 }}
              animate={{ opacity: 1, y: 0, rotate: item.rotate }}
              transition={{
                duration: 0.55,
                delay: 0.25 + i * 0.12,
                ease: "easeOut",
              }}
              whileHover={{ rotate: 0, y: -6 }}
              className="rounded-3xl p-7 sm:p-8 shadow-[0_10px_0_0_rgba(22,19,14,0.18)]"
              style={{ background: item.bg, color: item.fg }}
            >
              <span className="font-mono text-xs tracking-widest opacity-70">
                Q{item.n}
              </span>
              <p className="landing-display mt-4 text-2xl sm:text-[1.75rem] leading-[1.15]">
                {item.q}
              </p>
              <p className="landing-hand mt-4 text-lg opacity-90">
                {item.aside}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.7 }}
          className="mt-14 flex items-center gap-3 text-[var(--l-ink)]/70"
        >
          <ArrowDown className="w-4 h-4" />
          <span className="text-sm font-medium">
            GovernAI answers both. Here is what each answer looks like.
          </span>
        </motion.div>
      </div>
    </section>
  );
}
