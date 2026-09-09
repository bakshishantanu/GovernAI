"use client";

import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";

/** Who is actually signed in, drawn as an ID card rather than a form — this page is read-only. */
export function IdentityCard({ userId, orgId, role }: { userId: string; orgId: string; role: string }) {
  const isAdmin = role === "admin";
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="relative overflow-hidden rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
    >
      <motion.div
        initial={{ opacity: 0, scale: 1.6, rotate: -26 }}
        animate={{ opacity: 1, scale: 1, rotate: -12 }}
        transition={{ duration: 0.45, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute -right-3 -top-3"
      >
        <div
          className="flex h-[62px] w-[62px] items-center justify-center rounded-full border-[2.5px] border-dashed text-center"
          style={{
            borderColor: isAdmin ? "var(--l-orange-deep)" : "var(--l-charcoal)",
            background: "#ffffffe6",
            boxShadow: "0 0 0 3px #ffffffe6",
          }}
        >
          <span
            className="landing-display text-[9px] leading-[1.05] tracking-tight"
            style={{ color: isAdmin ? "var(--l-orange-deep)" : "var(--l-charcoal)" }}
          >
            {role.toUpperCase()}
          </span>
        </div>
      </motion.div>

      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--l-charcoal)]/45">
        <ShieldCheck className="h-3 w-3" />
        Signed in as
      </span>
      <h2 className="landing-display mt-1 text-lg capitalize text-[var(--l-ink)]">{role}</h2>

      <div className="mt-4 space-y-2 border-t-2 border-dashed border-[var(--l-ink)]/12 pt-3">
        <Row label="User id" value={userId} />
        <Row label="Organization id" value={orgId} />
      </div>
    </motion.div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="shrink-0 font-mono text-[10.5px] uppercase tracking-wide text-[var(--l-charcoal)]/45">
        {label}
      </span>
      <span className="truncate font-mono text-[11.5px] text-[var(--l-charcoal)]/70">{value}</span>
    </div>
  );
}
