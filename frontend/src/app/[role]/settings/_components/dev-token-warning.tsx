"use client";

import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";

/** A real security-relevant flag, not decoration — surfaced loudly on purpose. */
export function DevTokenWarning() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-start gap-3 rounded-2xl border-2 p-4"
      style={{
        borderColor: "var(--l-orange-deep)",
        background: "color-mix(in srgb, var(--l-orange-deep) 8%, var(--l-cream))",
      }}
    >
      <motion.span
        animate={{ rotate: [0, -6, 6, -3, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, repeatDelay: 2 }}
        className="mt-0.5 shrink-0"
      >
        <AlertTriangle className="h-5 w-5" style={{ color: "var(--l-orange-deep)" }} />
      </motion.span>
      <div>
        <p className="landing-display text-sm text-[var(--l-ink)]">The dev-token auth bypass is on</p>
        <p className="mt-0.5 text-[12.5px] leading-relaxed text-[var(--l-charcoal)]/70">
          Any request with <code className="rounded bg-black/5 px-1 py-0.5 font-mono">Bearer dummy-token</code>{" "}
          is accepted as this org's admin — real Supabase sign-in is not being checked.{" "}
          <code className="rounded bg-black/5 px-1 py-0.5 font-mono">AUTH_ALLOW_DEV_TOKEN</code> should be off
          before this ever reaches a real deployment.
        </p>
      </div>
    </motion.div>
  );
}
