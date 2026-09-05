"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { logout } from "@/app/auth/actions";
import { usePathname } from "next/navigation";
import { LogOut, Search, ShieldAlert } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { fetchApi } from "@/lib/api-client";
import { useConsoleEvents } from "@/components/events/console-events";
import { motion, useReducedMotion, DURATION, EASE } from "@/components/motion";

/**
 * The black top bar, per design/governai-pro Main.dc.html.
 *
 * This is the storefront hero's black log strip, reused as console chrome:
 * breadcrumb, a search field, then a live alert chip, the people on the
 * workspace, and the account controls.
 */

const CRUMBS: Record<string, string> = {
  "/": "Dashboard",
  "/agents": "Agents",
  "/skills": "Skills",
  "/policies": "Policies",
  "/audit": "Audit log",
  "/costs": "Costs",
  "/settings": "Settings",
  "/automations": "Automations",
};

function crumbFor(pathname: string) {
  if (CRUMBS[pathname]) return CRUMBS[pathname];
  const base = Object.keys(CRUMBS).find(
    (href) => href !== "/" && pathname.startsWith(href),
  );
  return base ? CRUMBS[base] : "Console";
}

export function Header() {
  const pathname = usePathname();
  const { deniedLastHour, connected, reconnecting } = useConsoleEvents();
  const [me, setMe] = useState<{ id: string; role: string } | null>(null);
  const still = useReducedMotion();

  useEffect(() => {
    let cancelled = false;
    fetchApi("/auth/me")
      .then((data) => {
        if (!cancelled) setMe(data ?? null);
      })
      .catch(() => {
        /* the header still renders signed out */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="sticky top-0 z-10 flex h-[60px] shrink-0 items-center gap-3.5 bg-gv-bar px-5">
      <div className="flex shrink-0 items-center gap-2 text-[13px] font-bold text-gv-bar-text">
        <span>Acme Corp</span>
        <span aria-hidden>/</span>
        <span className="text-gv-yellow">{crumbFor(pathname)}</span>
      </div>

      <label className="ml-2.5 flex h-9 w-[300px] shrink-0 items-center gap-2 rounded-xl border-2 border-gv-bar-border bg-gv-bar-field px-3.5">
        <Search className="h-[15px] w-[15px] shrink-0 text-gv-subtle" strokeWidth={2.2} />
        <input
          type="search"
          placeholder="Search everything"
          className="min-w-0 flex-1 bg-transparent text-[12.5px] font-semibold text-gv-bar-text placeholder:text-gv-subtle focus:outline-none"
        />
        <kbd className="shrink-0 font-mono text-[10.5px] text-gv-subtle">/</kbd>
      </label>

      <div className="ml-auto flex items-center gap-3">
        {/* Real, from the org-wide event stream: seeded from the audit log
            and kept live. The chip is only shown when there is something to
            report — a permanent "0 denied" is noise, and a hardcoded number
            (which this was) is worse than either. */}
        {deniedLastHour > 0 && (
          <motion.div
            initial={still ? false : { opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: DURATION.base, ease: EASE }}
            className="hidden h-8 items-center gap-[7px] rounded-xl border-2 border-border bg-gv-pink px-3 lg:flex"
          >
            <ShieldAlert className="h-3.5 w-3.5 text-gv-ink" strokeWidth={2.6} />
            <span className="text-[12px] font-extrabold text-gv-ink">
              {deniedLastHour} denied this hour
            </span>
          </motion.div>
        )}

        {/* Connection state for the whole console. It used to be three
            invented colleagues; this is the one thing the header can honestly
            say about who and what is connected. */}
        <span
          className="hidden items-center gap-[7px] text-[11.5px] font-bold text-gv-bar-text md:flex"
          title={
            connected
              ? "Live event stream connected"
              : reconnecting
                ? `Reconnecting (attempt ${reconnecting.attempt})`
                : "Live event stream not connected"
          }
        >
          <span className="relative flex h-2 w-2">
            {connected && !still && (
              <motion.span
                aria-hidden="true"
                className="absolute inset-0 rounded-full bg-gv-teal"
                animate={{ opacity: [0.6, 0, 0.6], scale: [1, 2.1, 1] }}
                transition={{ duration: 1.9, ease: "easeOut", repeat: Infinity }}
              />
            )}
            <span
              className={`relative h-2 w-2 rounded-full ${
                connected ? "bg-gv-teal" : reconnecting ? "bg-gv-yellow" : "bg-gv-subtle"
              }`}
            />
          </span>
          {connected ? "Live" : reconnecting ? "Reconnecting" : "Offline"}
        </span>

        {me && (
          <Link
            href="/settings"
            title={`Signed in as ${me.role}`}
            className="hidden h-[30px] w-[30px] items-center justify-center rounded-full border-2 border-gv-paper bg-gv-lilac text-[10.5px] font-extrabold text-gv-ink md:flex"
          >
            {me.role.slice(0, 2).toUpperCase()}
          </Link>
        )}

        <ThemeToggle />

        <form action={logout}>
          <button
            type="submit"
            title="Log out"
            className="flex h-8 items-center gap-2 rounded-xl border-2 border-border bg-gv-yellow px-3 text-[12.5px] font-extrabold text-gv-ink transition-colors hover:bg-gv-pink"
          >
            <LogOut className="h-[14px] w-[14px]" strokeWidth={2.4} />
            Sign out
          </button>
        </form>
      </div>
    </header>
  );
}
