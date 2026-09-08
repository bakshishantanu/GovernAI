"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { logout } from "@/app/auth/actions";
import { LogOut, User, Bell } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { fetchApi } from "@/lib/api-client";

/**
 * App shell header, on Priya's design system (D-038).
 *
 * The organisation name is real, from GET /auth/settings — the same call
 * the settings page makes — not a hardcoded "Default Org" string. It is
 * intentionally the org's name only; per-user identity lives in the
 * sidebar's SignedInAs card, which already reads /auth/me.
 *
 * The org chip is keyed by orgName but deliberately NOT wrapped in
 * AnimatePresence mode="wait". That mode holds the incoming element back
 * until the outgoing element's exit animation completes — and if the tab
 * is backgrounded, requestAnimationFrame is throttled/paused by the
 * browser, so that exit animation never ticks and the swap never happens.
 * Confirmed live: the chip froze at its `initial` opacity:0 state
 * indefinitely with the real org name already fetched and in React state,
 * purely because the tab was hidden. A plain keyed remount (this version)
 * animates in on its own schedule without gating on anything exiting, so
 * real information is never held hostage by a decorative transition.
 */
export function Header() {
  const [orgName, setOrgName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/auth/settings")
      .then((data) => {
        if (!cancelled) setOrgName(data?.organization?.name ?? null);
      })
      .catch(() => {
        /* header still renders; the chip just stays a loading state */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center justify-between border-b border-[var(--l-line)] bg-[var(--l-cream)]/90 px-6 backdrop-blur-md">
      <motion.span
        key={orgName ?? "loading"}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.25 }}
        className="rounded-full bg-[var(--l-cream-deep)] px-3 py-1.5 text-sm font-medium text-[var(--l-charcoal)]/70"
      >
        {orgName ?? "Loading organisation…"}
      </motion.span>

      <div className="flex items-center gap-1.5">
        <ThemeToggle />

        <button className="rounded-full p-2 text-[var(--l-charcoal)]/60 transition-colors hover:bg-[var(--l-cream-deep)] hover:text-[var(--l-ink)]">
          <Bell className="h-4 w-4" />
        </button>

        <div className="mx-2 h-4 w-px bg-[var(--l-line)]" />

        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--l-cream-deep)] text-[var(--l-charcoal)]/70">
          <User className="h-4 w-4" />
        </div>

        <form action={logout}>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            type="submit"
            className="ml-1 rounded-full p-2 text-[var(--l-charcoal)]/60 transition-colors hover:bg-[var(--l-orange)]/10 hover:text-[var(--l-orange-deep)]"
            title="Log out"
          >
            <LogOut className="h-4 w-4" />
          </motion.button>
        </form>
      </div>
    </header>
  );
}
