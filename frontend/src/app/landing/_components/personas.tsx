"use client";

import { motion } from "framer-motion";

const PERSONAS = [
  {
    label: "Persona #1",
    tag: "Platform / security engineers",
    body: "Install GovernAI as the mandatory checkpoint every new agent must pass through before it can act.",
    bg: "var(--l-orange)",
    fg: "white",
    rotate: -6,
  },
  {
    label: "Persona #2",
    tag: "Agent builders",
    body: "Assemble agents from existing skills instead of writing the same integrations from scratch, again.",
    bg: "var(--l-yellow-deep)",
    fg: "var(--l-ink)",
    rotate: 3,
  },
  {
    label: "Persona #3",
    tag: "IT & budget owners",
    body: "One dashboard view of every agent (owner, access, live cost) with the power to pause any of them instantly.",
    bg: "var(--l-teal)",
    fg: "white",
    rotate: -3,
  },
];

export function Personas() {
  return (
    <section className="relative bg-[var(--l-pink-pale)] py-28 md:py-36 overflow-hidden">
      <div className="landing-blob landing-blob-animate pointer-events-none absolute -top-52 -left-32 w-[520px] h-[520px] bg-[var(--l-pink-blush)] opacity-70" />
      <div className="landing-blob landing-blob-animate pointer-events-none absolute -bottom-40 -right-40 w-[480px] h-[480px] bg-[var(--l-pink-lilac)] opacity-40" />
      <div className="landing-blob pointer-events-none absolute top-1/4 right-1/3 w-[260px] h-[260px] bg-white opacity-30" />

      <div className="max-w-6xl mx-auto px-6 relative">
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

        {/* fanned, overlapping cards — matches the reference's step-card
            treatment: elastic pop-in from an exaggerated rotation, then a
            hover that straightens and lifts the card to the front */}
        <div className="mt-16 md:mt-20 flex flex-col md:flex-row md:justify-center items-center md:items-stretch gap-8 md:gap-0">
          {PERSONAS.map((p, i) => (
            <motion.div
              key={p.tag}
              initial={{ opacity: 0, scale: 0, rotate: p.rotate + (i % 2 === 0 ? -30 : 30) }}
              whileInView={{ opacity: 1, scale: 1, rotate: p.rotate }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{
                type: "spring",
                stiffness: 260,
                damping: 12,
                delay: i * 0.09,
              }}
              whileHover={{ rotate: 0, scale: 1.06, zIndex: 20 }}
              className={`relative w-72 sm:w-80 shrink-0 ${
                i > 0 ? "md:-ml-10" : ""
              }`}
              style={{ zIndex: i + 1 }}
            >
              <div
                className="rounded-[28px] px-7 py-8 h-full shadow-xl shadow-black/15"
                style={{ background: p.bg, color: p.fg }}
              >
                <span className="landing-hand text-2xl opacity-80 block">
                  {p.label}
                </span>
                <h3 className="landing-display mt-3 text-2xl leading-tight">
                  {p.tag}
                </h3>
                <p className="mt-3 text-sm leading-relaxed opacity-85">
                  {p.body}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
