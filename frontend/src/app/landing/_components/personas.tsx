"use client";

import { motion } from "framer-motion";

const PERSONAS = [
  {
    tag: "Platform / security engineers",
    body: "Install GovernAI as the mandatory checkpoint every new agent must pass through before it can act.",
    bg: "var(--l-orange)",
    fg: "white",
    rotate: -4,
    shift: "md:translate-y-0",
  },
  {
    tag: "Agent builders",
    body: "Assemble agents from existing skills instead of writing the same integrations from scratch, again.",
    bg: "var(--l-yellow-deep)",
    fg: "var(--l-ink)",
    rotate: 3,
    shift: "md:translate-y-12",
  },
  {
    tag: "IT & budget owners",
    body: "One dashboard view of every agent (owner, access, live cost) with the power to pause any of them instantly.",
    bg: "var(--l-teal)",
    fg: "white",
    rotate: -2,
    shift: "md:-translate-y-4",
  },
];

export function Personas() {
  return (
    <section className="relative bg-[var(--l-cream-deep)] py-28 md:py-36 overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl mx-auto"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold">
            Built for three seats at the table
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-6xl text-[var(--l-charcoal)] tracking-tight">
            Who reaches for GovernAI
          </h2>
        </motion.div>

        <div className="mt-20 flex flex-wrap items-start justify-center gap-x-8 gap-y-14 md:gap-y-0">
          {PERSONAS.map((p, i) => (
            <motion.div
              key={p.tag}
              initial={{ opacity: 0, scale: 0.4, rotate: p.rotate + (i % 2 === 0 ? -28 : 28) }}
              whileInView={{ opacity: 1, scale: 1, rotate: p.rotate }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{
                type: "spring",
                stiffness: 220,
                damping: 16,
                delay: i * 0.12,
              }}
              whileHover={{ rotate: 0, scale: 1.04 }}
              className={`w-full max-w-xs shrink-0 ${p.shift}`}
            >
              <div
                className="rounded-[36px] px-7 py-8 shadow-lg shadow-black/10"
                style={{ background: p.bg, color: p.fg }}
              >
                <h3 className="landing-display text-2xl leading-tight">{p.tag}</h3>
                <p className="mt-3 text-sm leading-relaxed opacity-85">{p.body}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
