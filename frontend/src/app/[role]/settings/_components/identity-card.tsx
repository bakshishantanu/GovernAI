"use client";

import { motion } from "framer-motion";
import { LogOut, ShieldCheck } from "lucide-react";
import { logout } from "@/app/auth/actions";

/** Who is actually signed in, drawn as an ID card rather than a form — this page is read-only. */
export function IdentityCard({
  userId,
  orgId,
  role,
  email,
  fullName,
}: {
  userId: string;
  orgId: string;
  role: string;
  email: string | null;
  fullName: string | null;
}) {
  const isAdmin = role === "admin";
  // "agent_builder" -> "Agent Builder" — the raw DB value is a key, not a
  // label (same rule the sidebar's ROLE_NAME map follows), so multi-word
  // role strings never leak an underscore into the UI.
  const roleLabel = role
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
  // A real Supabase session always carries these; the local dev-token
  // bypass has no real identity behind it, so both come back null — the
  // role name is the honest fallback there, not a fabricated name.
  const displayName = fullName || email || roleLabel;

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
          className="flex h-[62px] w-[62px] items-center justify-center rounded-full border-[2.5px] border-dashed p-1.5 text-center"
          style={{
            borderColor: isAdmin ? "var(--l-orange-deep)" : "var(--l-charcoal)",
            background: "#ffffffe6",
            boxShadow: "0 0 0 3px #ffffffe6",
          }}
        >
          <span
            className="landing-display text-[8px] leading-[1.05] tracking-tight"
            style={{ color: isAdmin ? "var(--l-orange-deep)" : "var(--l-charcoal)" }}
          >
            {roleLabel.toUpperCase()}
          </span>
        </div>
      </motion.div>

      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--l-charcoal)]/45">
        <ShieldCheck className="h-3 w-3" />
        Signed in as
      </span>
      <h2 className="landing-display mt-1 truncate text-lg text-[var(--l-ink)]">{displayName}</h2>
      {fullName && email && (
        <p className="mt-0.5 truncate text-[12.5px] text-[var(--l-charcoal)]/55">{email}</p>
      )}

      <div className="mt-4 space-y-2 border-t-2 border-dashed border-[var(--l-ink)]/12 pt-3">
        <Row label="User id" value={userId} />
        <Row label="Organization id" value={orgId} />
      </div>

      <form action={logout} className="mt-4 border-t-2 border-dashed border-[var(--l-ink)]/12 pt-3">
        <button
          type="submit"
          className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-orange-deep)]"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
      </form>
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
