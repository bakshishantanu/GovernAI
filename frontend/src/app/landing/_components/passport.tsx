"use client";

import type { ElementType } from "react";
import { motion } from "framer-motion";
import { Fingerprint, KeyRound, Wallet } from "lucide-react";

export function Passport() {
  return (
    <section className="relative bg-[var(--l-cream)] pb-28 md:pb-36">
      <div className="max-w-6xl mx-auto px-6 grid md:grid-cols-2 gap-14 items-center">
        <motion.div
          initial={{ opacity: 0, x: -28 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-teal)] font-semibold">
            Meet the Agent Passport
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-5xl text-[var(--l-charcoal)] leading-[1.02] tracking-tight">
            Governance is generated at creation — not configured afterward.
          </h2>
          <p className="mt-5 text-[var(--l-charcoal)]/65 leading-relaxed max-w-md">
            The instant a builder assembles an agent from skills, GovernAI issues it
            a passport: a unique identity, a scoped permission set, and an
            enforced cost budget. It exists before the agent ever calls a tool.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 32, rotate: -2 }}
          whileInView={{ opacity: 1, y: 0, rotate: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          whileHover={{ rotate: 0.5, y: -4 }}
          className="rounded-3xl bg-[var(--l-navy-deep)] text-[var(--l-ink)] p-8 shadow-2xl shadow-black/10 border border-[var(--l-line-dark)]"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange-soft)]">
              Agent Passport
            </div>
            <div className="text-xs font-mono text-[var(--l-ink)]/40">
              #AG-8841
            </div>
          </div>

          <div className="mt-6 text-2xl font-semibold">Invoice Triage Bot</div>
          <div className="text-sm text-[var(--l-ink)]/50">
            owner: finance-ops@team
          </div>

          <div className="mt-7 space-y-4">
            <Row
              icon={Fingerprint}
              label="Identity"
              value="Issued · UUID + human name"
            />
            <Row
              icon={KeyRound}
              label="Scope"
              value="ticket:read, docs:search, sql:readonly"
            />
            <Row icon={Wallet} label="Budget" value="$25.00 / day · live" ok />
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Row({
  icon: Icon,
  label,
  value,
  ok,
}: {
  icon: ElementType;
  label: string;
  value: string;
  ok?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white/[0.04] border border-[var(--l-line-dark)] px-4 py-3">
      <Icon className="w-4 h-4 text-[var(--l-teal-soft)] shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-[var(--l-ink)]/40">
          {label}
        </div>
        <div className="text-sm font-mono truncate">{value}</div>
      </div>
      {ok && <span className="w-2 h-2 rounded-full bg-[var(--l-teal-soft)] animate-pulse" />}
    </div>
  );
}
