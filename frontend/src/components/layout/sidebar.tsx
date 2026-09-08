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
  ClipboardList,
  Sparkles,
  PlayCircle,
} from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

/**
 * App shell sidebar, on Priya's landing design system (D-038), with the
 * navigation itself chosen by role.
 *
 * Each role sees only its own surfaces, so the three experiences read as
 * three different sites while sharing one deployment and one design system.
 * This is presentation only: hiding a link is not access control, and every
 * endpoint re-checks the role server-side.
 */

export function Sidebar() {
  const pathname = usePathname();
  const { role } = useAuth();

  const getNavItems = () => {
    switch (role) {
      case "agent_builder":
        return [
          { name: "Overview", href: "/", icon: LayoutDashboard },
          { name: "Requests Queue", href: "/requests", icon: ClipboardList },
          { name: "Skill Marketplace", href: "/skills", icon: Puzzle },
          { name: "My Builds", href: "/agents", icon: Bot },
          { name: "My Activity", href: "/audit", icon: FileText },
        ];
      case "user":
        return [
          { name: "Overview", href: "/", icon: LayoutDashboard },
          { name: "Request an Agent", href: "/request-agent", icon: Sparkles },
          { name: "My Agents", href: "/agents", icon: Bot },
          { name: "My Runs", href: "/executions", icon: PlayCircle },
        ];
      case "admin":
      default:
        return [
          { name: "Overview", href: "/", icon: LayoutDashboard },
          { name: "All Agents", href: "/agents", icon: Bot },
          { name: "Requests", href: "/requests", icon: ClipboardList },
          { name: "Skills", href: "/skills", icon: Puzzle },
          { name: "Policies", href: "/policies", icon: ShieldCheck },
          { name: "Audit Log", href: "/audit", icon: FileText },
          { name: "Costs", href: "/costs", icon: DollarSign },
          { name: "Settings", href: "/settings", icon: Settings },
        ];
    }
  };

  const navItems = getNavItems();

  return (
    <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-[var(--l-line)] bg-[var(--l-cream)]">
      <Link
        href="/"
        className="landing-display flex h-16 shrink-0 items-center gap-2 px-6 text-base text-[var(--l-ink)]"
      >
        <ShieldCheck className="h-5 w-5 text-[var(--l-orange)]" />
        GovernAI
      </Link>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));

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
 * The role is what governs access, so it leads; the raw user id is shown
 * in mono underneath, truncated, the way an id is always presented here.
 */
/** The database's value is a key, not a label - never print it raw. */
const ROLE_NAME: Record<string, string> = {
  admin: "Admin",
  agent_builder: "Agent builder",
  user: "User",
};

function SignedInAs() {
  const [me, setMe] = useState<{ id: string; role: string } | null>(null);

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

  return (
    <Link
      href="/settings"
      className="flex items-center gap-3 rounded-2xl p-2 transition-colors hover:bg-[var(--l-yellow-pale)]/40"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--l-navy-deep)] text-[11px] font-semibold text-[var(--l-cream)]">
        {me ? me.role.slice(0, 2).toUpperCase() : "··"}
      </span>
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="truncate text-[13px] font-semibold text-[var(--l-ink)]">
          {me ? (ROLE_NAME[me.role] ?? me.role) : "Signed in"}
        </span>
        <span className="truncate font-mono text-[10.5px] text-[var(--l-charcoal)]/50">
          {me ? `${me.id.slice(0, 8)}…` : "loading…"}
        </span>
      </span>
    </Link>
  );
}
