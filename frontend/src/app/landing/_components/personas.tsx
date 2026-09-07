"use client";

import { motion } from "framer-motion";

const PERSONAS = [
  {
    tag: "Platform / security engineers",
    body: "Install GovernAI as the mandatory checkpoint every new agent must pass through before it can act.",
  },
  {
    tag: "Agent builders",
    body: "Assemble agents from existing skills instead of writing the same integrations from scratch, again.",
  },
  {
    tag: "IT & budget owners",
    body: "One dashboard view of every agent (owner, access, live cost) with the power to pause any of them instantly.",
  },
];

export function Personas() {
  return (
    <section className="relative bg-[var(--l-cream-deep)] py-28 md:py-36">
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

        <div className="mt-16 grid md:grid-cols-3 gap-6">
          {PERSONAS.map((p, i) => (
            <motion.div
              key={p.tag}
              initial={{ opacity: 0, y: 32 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 0.55, delay: i * 0.1, ease: "easeOut" }}
              className="rounded-2xl bg-[var(--l-navy-deep)] text-[var(--l-cream)] p-7"
            >
              <span className="landing-display text-2xl text-[var(--l-orange-soft)]">
                0{i + 1}
              </span>
              <h3 className="mt-3 font-semibold">{p.tag}</h3>
              <p className="mt-2.5 text-sm leading-relaxed text-[var(--l-cream)]/60">
                {p.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
