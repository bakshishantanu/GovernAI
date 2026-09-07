"use client";

import { motion } from "framer-motion";
import { EyeOff, RefreshCcw, HelpCircle } from "lucide-react";

const POINTS = [
  {
    icon: RefreshCcw,
    title: "Rebuilt, not reused",
    body: "Every team wires up its own ticketing, doc-search, and SQL connectors from scratch — the same integrations, duplicated across the org.",
  },
  {
    icon: EyeOff,
    title: "No consistent identity",
    body: "Agents get unmonitored access to internal data with no shared permission model. Nobody agreed on what an agent is even allowed to touch.",
  },
  {
    icon: HelpCircle,
    title: "Unanswerable questions",
    body: "“How much are we spending on agents?” “Can we pause this one right now?” Leadership asks. Today, nobody can answer.",
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};
const item = {
  hidden: { opacity: 0, y: 28 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: "easeOut" as const },
  },
};

export function Problem() {
  return (
    <section id="problem" className="relative bg-[var(--l-cream)] py-28 md:py-36 overflow-hidden">
      <div className="landing-blob pointer-events-none absolute -bottom-32 -right-32 w-[420px] h-[420px] bg-[var(--l-yellow)] opacity-30" />
      <div className="max-w-6xl mx-auto px-6 relative">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="max-w-2xl"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold">
            The problem
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-6xl text-[var(--l-charcoal)] leading-[1] tracking-tight">
            Enterprises deploying AI agents today have effectively no
            governance layer.
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
          className="mt-16 grid md:grid-cols-3 gap-6"
        >
          {POINTS.map((p) => (
            <motion.div
              key={p.title}
              variants={item}
              className="rounded-2xl border border-[var(--l-line)] bg-white/60 p-7 hover:bg-white transition-colors"
            >
              <p.icon className="w-6 h-6 text-[var(--l-teal)]" />
              <h3 className="mt-5 text-lg font-semibold text-[var(--l-charcoal)]">
                {p.title}
              </h3>
              <p className="mt-2.5 text-sm leading-relaxed text-[var(--l-charcoal)]/65">
                {p.body}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
