"use client";

import { motion } from "framer-motion";
import { Building2, Bot, ShieldCheck, Zap } from "lucide-react";

export function OrgCard({
  name,
  agentCount,
  policyCount,
  automationCount,
}: {
  name: string;
  agentCount: number;
  policyCount: number;
  automationCount: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.06 }}
      className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
    >
      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--l-charcoal)]/45">
        <Building2 className="h-3 w-3" />
        Organization
      </span>
      <h2 className="landing-display mt-1 text-lg text-[var(--l-ink)]">{name}</h2>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <Stat icon={Bot} value={agentCount} label="Agents" />
        <Stat icon={ShieldCheck} value={policyCount} label="Policies" />
        <Stat icon={Zap} value={automationCount} label="Automations" />
      </div>
    </motion.div>
  );
}

function Stat({ icon: Icon, value, label }: { icon: typeof Bot; value: number; label: string }) {
  return (
    <div className="rounded-xl border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-3 py-2.5 text-center">
      <Icon className="mx-auto h-3.5 w-3.5 text-[var(--l-charcoal)]/45" />
      <p className="landing-display mt-1 text-lg text-[var(--l-ink)]">{value}</p>
      <p className="font-mono text-[9.5px] uppercase tracking-wide text-[var(--l-charcoal)]/45">{label}</p>
    </div>
  );
}
