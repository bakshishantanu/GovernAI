"use client";

import { motion } from "framer-motion";
import {
  Blocks,
  ShieldCheck,
  ScrollText,
  Power,
  Users,
  Gauge,
} from "lucide-react";

const FEATURES = [
  {
    icon: Blocks,
    title: "Skill marketplace",
    body: "A curated registry of reusable connectors — ticketing, RAG, SQL — each declaring the permissions it needs.",
  },
  {
    icon: ShieldCheck,
    title: "Policy engine",
    body: "Intercepts every tool call live against the agent's scope and global deny rules. No silent access.",
  },
  {
    icon: Gauge,
    title: "Live cost tracking",
    body: "Token counts and model pricing roll up into per-agent, per-execution cost attribution, in real time.",
  },
  {
    icon: ScrollText,
    title: "Append-only audit log",
    body: "Every action — allowed or blocked — is logged unconditionally. 100% coverage, by construction.",
  },
  {
    icon: Power,
    title: "One-click kill switch",
    body: "Suspend any agent instantly from the dashboard, with immediate effect on running executions.",
  },
  {
    icon: Users,
    title: "Scoped ownership",
    body: "Every agent has exactly one owner and an RBAC permission set — no ambiguous access.",
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 24 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

export function FeatureGrid() {
  return (
    <section id="features" className="relative bg-[var(--l-cream)] py-28 md:py-36">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="max-w-xl"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold">
            Everything, built in
          </span>
          <h2 className="mt-4 text-3xl md:text-5xl font-semibold tracking-tight text-[var(--l-charcoal)] leading-tight">
            Governance that ships with the agent, not after it.
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          className="mt-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-5"
        >
          {FEATURES.map((f) => (
            <motion.div
              key={f.title}
              variants={item}
              whileHover={{ y: -4 }}
              className="rounded-2xl border border-[var(--l-line)] bg-white p-6 transition-shadow hover:shadow-lg hover:shadow-black/5"
            >
              <div className="w-10 h-10 rounded-xl bg-[var(--l-teal)]/10 flex items-center justify-center">
                <f.icon className="w-5 h-5 text-[var(--l-teal)]" />
              </div>
              <h3 className="mt-4 font-semibold text-[var(--l-charcoal)]">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--l-charcoal)]/60">
                {f.body}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
