"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { logout } from "@/app/auth/actions";
import { LogOut, User, Bell, ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth-context";
import { UserRole } from "@/lib/types";
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
  const { role, userName, switchRole } = useAuth();
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

  const getRoleBadge = (r: UserRole) => {
    switch (r) {
      case "admin":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20";
      case "agent_builder":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
      case "user":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
    }
  };

  const getRoleLabel = (r: UserRole) => {
    switch (r) {
      case "admin":
        return "Admin";
      case "agent_builder":
        return "Agent Builder";
      case "user":
        return "User";
    }
  };

  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center justify-between border-b border-[var(--l-line)] bg-[var(--l-cream)]/90 px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <motion.span
          key={orgName ?? "loading"}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25 }}
          className="rounded-full bg-[var(--l-cream-deep)] px-3 py-1.5 text-sm font-medium text-[var(--l-charcoal)]/70"
        >
          {orgName ?? "Loading organisation…"}
        </motion.span>

        {/* Role Simulator / Quick Switcher */}
        <div className="hidden sm:flex items-center bg-[var(--l-cream-deep)] rounded-lg p-0.5 border border-[var(--l-line)] text-xs">
          <span className="text-[11px] font-medium text-[var(--l-charcoal)]/70 px-2 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-[var(--l-charcoal)]/60" />
            Role:
          </span>
          {(["admin", "agent_builder", "user"] as UserRole[]).map((r) => {
            const isActive = role === r;
            return (
              <button
                key={r}
                type="button"
                onClick={() => switchRole(r)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold"
                    : "text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
                }`}
              >
                {getRoleLabel(r)}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <ThemeToggle />

        <button className="rounded-full p-2 text-[var(--l-charcoal)]/60 transition-colors hover:bg-[var(--l-cream-deep)] hover:text-[var(--l-ink)]">
          <Bell className="h-4 w-4" />
        </button>

        <div className="mx-2 h-4 w-px bg-[var(--l-line)]" />

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium text-[var(--l-ink)]">{userName}</span>
            <span className={`text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 border rounded ${getRoleBadge(role)}`}>
              {getRoleLabel(role)}
            </span>
          </div>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--l-cream-deep)] text-[var(--l-charcoal)]/70">
            <User className="h-4 w-4" />
          </div>
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
