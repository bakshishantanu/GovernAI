"use client";

import { motion } from "framer-motion";

const POINTS = [
  {
    title: "Rebuilt, not reused",
    body: "Every team wires up its own ticketing, doc-search, and SQL connectors from scratch, duplicating integrations that already exist elsewhere in the org.",
    bg: "#1f8a83",
    fg: "#fff8ec",
    rotate: -2,
  },
  {
    title: "No consistent identity",
    body: "Agents get unmonitored access to internal data with no shared permission model. Nobody agreed on what an agent is even allowed to touch.",
    bg: "#f9a220",
    fg: "#670a2e",
    rotate: 1.5,
  },
  {
    title: "Unanswerable questions",
    body: "“How much are we spending on agents?” “Can we pause this one right now?” Leadership asks. Today, nobody can answer.",
    bg: "#ff008c",
    fg: "#fff",
    rotate: -1.5,
    callout: "this is the one that keeps leadership up at night",
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
      <div className="landing-blob landing-blob-animate pointer-events-none absolute -bottom-32 -right-32 w-[420px] h-[420px] bg-[var(--l-yellow)] opacity-30" />
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
          {POINTS.map((p, i) => (
            <motion.div
              key={p.title}
              variants={item}
              className="relative"
              style={{ rotate: p.rotate }}
            >
              {p.callout && (
                <span className="landing-hand absolute -top-9 right-2 text-xl text-[var(--l-ink)] rotate-[5deg] z-20 whitespace-nowrap">
                  {p.callout} ↴
                </span>
              )}
              <div
                className="relative overflow-hidden rounded-2xl p-7 shadow-[0_8px_0_0_rgba(22,19,14,0.16)] transition-transform duration-200 hover:-translate-y-1 hover:shadow-[0_10px_0_0_rgba(22,19,14,0.16)]"
                style={{ background: p.bg, color: p.fg }}
              >
                <span
                  aria-hidden
                  className="landing-display absolute -top-10 -right-4 text-[150px] leading-none select-none pointer-events-none opacity-[0.16]"
                  style={{ color: p.fg }}
                >
                  0{i + 1}
                </span>

                <span className="landing-display relative text-2xl">0{i + 1}</span>
                <h3 className="relative mt-4 text-lg font-semibold">{p.title}</h3>
                <p className="relative mt-2.5 text-sm leading-relaxed opacity-80">
                  {p.body}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
