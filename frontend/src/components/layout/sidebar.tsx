"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Bot,
  Puzzle,
  ShieldCheck,
  FileText,
  DollarSign,
  Settings,
  PlayCircle,
} from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useRoleBase } from "@/lib/use-role-base";

/**
 * App shell sidebar, on Priya's landing design system (D-038), with the
 * navigation itself chosen by role.
 *
 * Two roles (agent_builder merged into user — D-052): admin sees the full
 * console; user sees agents (whether built or assigned), skills, runs,
 * activity, and cost figures for those agents. The request/claim flow
 * (Request an Agent, Requests Queue) was removed once a user could build an
 * agent directly — a two-step "ask, then someone claims it" ceremony had no
 * purpose left once the person asking and the person building are the same
 * person; "New agent" on the agents page is the one direct path now. This
 * is presentation only: hiding a link is not access control, and every
 * endpoint re-checks the role server-side.
 */

export function Sidebar() {
  const pathname = usePathname();
  const { role } = useAuth();
  const base = useRoleBase();

  const getNavItems = () => {
    switch (role) {
      case "agent_builder":
        return [
          { name: "Overview", href: `${base}`, icon: LayoutDashboard },
          { name: "My Agents", href: `${base}/agents`, icon: Bot },
          { name: "Skills", href: `${base}/skills`, icon: Puzzle },
          { name: "My Runs", href: `${base}/executions`, icon: PlayCircle },
          { name: "My Activity", href: `${base}/audit`, icon: FileText },
          { name: "Costs", href: `${base}/costs`, icon: DollarSign },
          { name: "Settings", href: `${base}/settings`, icon: Settings },
        ];
      case "admin":
      default:
        return [
          { name: "Overview", href: `${base}`, icon: LayoutDashboard },
          { name: "All Agents", href: `${base}/agents`, icon: Bot },
          { name: "Skills", href: `${base}/skills`, icon: Puzzle },
          { name: "Policies", href: `${base}/policies`, icon: ShieldCheck },
          { name: "Audit Log", href: `${base}/audit`, icon: FileText },
          { name: "Costs", href: `${base}/costs`, icon: DollarSign },
          { name: "Settings", href: `${base}/settings`, icon: Settings },
        ];
    }
  };

  const navItems = getNavItems();

  return (
    <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-[var(--l-line)] bg-[var(--l-cream)]">
      <Link
        href={base || "/"}
        className="landing-display flex h-16 shrink-0 items-center gap-2 px-6 text-base text-[var(--l-ink)]"
      >
        <ShieldCheck className="h-5 w-5 text-[var(--l-orange)]" />
        GovernAI
      </Link>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== base && pathname.startsWith(item.href));

          return (
            <Link
              key={item.name}
              href={item.href}
              className="relative flex h-10 items-center gap-3 rounded-full px-4 text-sm font-medium transition-colors"
              style={{ color: isActive ? "#ffffff" : "var(--l-charcoal)" }}
            >
              {isActive && (
                <motion.span
                  layoutId="sidebar-active-pill"
                  className="absolute inset-0 rounded-full bg-[var(--l-orange)]"
                  transition={{ type: "spring", stiffness: 500, damping: 38 }}
                />
              )}
              <item.icon className="relative z-10 h-4 w-4 shrink-0" />
              <span className="relative z-10">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--l-line)] p-3">
        <SignedInAs />
      </div>
    </aside>
  );
}

/**
 * Who is actually signed in, from GET /auth/me — never a hardcoded name.
 *
 * Shows the real display name (or email, if no name is set) whenever the
 * token actually carries one — a real Supabase session always does. The dev
 * token has no real identity behind it, so those fields come back null and
 * this falls back to the role name instead of showing nothing/None.
 */
/** The database's value is a key, not a label - never print it raw. */
const ROLE_NAME: Record<string, string> = {
  admin: "Admin",
  agent_builder: "Agent Builder",
};

type Me = { id: string; role: string; email: string | null; full_name: string | null };

function initials(text: string): string {
  const parts = text.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return text.slice(0, 2).toUpperCase();
}

function SignedInAs() {
  const [me, setMe] = useState<Me | null>(null);
  const base = useRoleBase();

  useEffect(() => {
    let cancelled = false;
    fetchApi("/auth/me")
      .then((data) => {
        if (!cancelled) setMe(data ?? null);
      })
      .catch(() => {
        /* sidebar still works signed out; the card just stays unknown */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const displayName = me?.full_name || me?.email || (me ? ROLE_NAME[me.role] : null);
  const subtitle = me?.full_name ? me.email : me ? ROLE_NAME[me.role] : null;

  return (
    <Link
      href={`${base}/settings`}
      className="flex items-center gap-3 rounded-2xl p-2 transition-colors hover:bg-[var(--l-yellow-pale)]/40"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--l-navy-deep)] text-[11px] font-semibold text-[var(--l-cream)]">
        {displayName ? initials(displayName) : "··"}
      </span>
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="truncate text-[13px] font-semibold text-[var(--l-ink)]">
          {displayName ?? "Signed in"}
        </span>
        <span className="truncate font-mono text-[10.5px] text-[var(--l-charcoal)]/50">
          {subtitle ?? (me ? `${me.id.slice(0, 8)}…` : "loading…")}
        </span>
      </span>
    </Link>
  );
}
