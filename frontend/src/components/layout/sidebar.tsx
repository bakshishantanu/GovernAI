"use client";

import { useCallback, useEffect, useState } from "react";
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
  Inbox,
  FolderOpen,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useRoleBase } from "@/lib/use-role-base";
import { useLive } from "@/lib/use-live";
import { useNotifications } from "@/lib/use-notifications";
import { useSidebar } from "@/lib/sidebar-context";
import { useMediaQuery } from "@/lib/use-media-query";

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

const COLLAPSED_KEY = "governai:sidebarCollapsed";

function loadCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function Sidebar() {
  const pathname = usePathname();
  const { role } = useAuth();
  const base = useRoleBase();
  const [collapsed, setCollapsed] = useState(loadCollapsed);
  const { mobileOpen, closeMobile } = useSidebar();
  // The collapse-to-rail preference is desktop-only by design (mobile gets a
  // full-width drawer instead, never a squeezed icon rail) - `collapsed`
  // alone isn't enough to decide rendering, since it can be `true` from a
  // desktop visit while the viewport is currently mobile-sized.
  const isDesktop = useMediaQuery("(min-width: 768px)");
  const effectiveCollapsed = collapsed && isDesktop;

  // Close the mobile drawer whenever the route changes (link click, back
  // button, anything) - it should never stay open across a navigation.
  useEffect(() => {
    closeMobile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
      } catch {
        // Storage unavailable - the toggle still works, it just won't be
        // remembered on the next visit.
      }
      return next;
    });
  }
  // Same source as the header bell (lib/use-notifications.ts) — one shared
  // hook rather than two copies of the same fetch-and-map logic, even
  // though each mounted instance still polls independently.
  const { notifications } = useNotifications();
  const pendingDrafts = notifications.length;
  const hasTicketingAgent = useHasTicketingAgent();

  const getNavItems = () => {
    // "Draft Replies" is only relevant to someone who actually has an agent
    // that can produce a draft — i.e. one built with the ticketing skill.
    // Gated on that (not just on `pendingDrafts > 0`) so it stays visible
    // once you own a ticketing agent even between drafts, but never shows to
    // someone who has never touched ticketing. `/agents/` is already scoped
    // server-side (org-wide for admin, own+assigned for a builder), so the
    // same check works for both roles without re-deriving the scoping rule.
    const draftsItem = hasTicketingAgent
      ? [{ name: "Draft Replies", href: `${base}/drafts`, icon: Inbox, badge: pendingDrafts }]
      : [];

    switch (role) {
      case "agent_builder":
        return [
          { name: "Overview", href: `${base}`, icon: LayoutDashboard },
          { name: "My Agents", href: `${base}/agents`, icon: Bot },
          ...draftsItem,
          { name: "Skills", href: `${base}/skills`, icon: Puzzle },
          { name: "Documents", href: `${base}/documents`, icon: FolderOpen },
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
          ...draftsItem,
          { name: "Skills", href: `${base}/skills`, icon: Puzzle },
          { name: "Documents", href: `${base}/documents`, icon: FolderOpen },
          { name: "Policies", href: `${base}/policies`, icon: ShieldCheck },
          { name: "Audit Log", href: `${base}/audit`, icon: FileText },
          { name: "Costs", href: `${base}/costs`, icon: DollarSign },
          { name: "Settings", href: `${base}/settings`, icon: Settings },
        ];
    }
  };

  const navItems = getNavItems();

  return (
    <>
      {/* Backdrop: mobile-only, shown behind the drawer while it's open.
          Tapping it closes the drawer, same as tapping outside any other
          overlay in this app. `md:hidden` guards against a stale mobileOpen
          surviving a resize up to desktop, where the sidebar is never an
          overlay so there's nothing to dim. */}
      {mobileOpen && (
        <div
          aria-hidden
          onClick={closeMobile}
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-screen w-72 flex-col overflow-hidden border-r border-[var(--l-line)] bg-[var(--l-cream)] transition-transform duration-300 ease-in-out md:sticky md:top-0 md:z-auto md:translate-x-0 md:shrink-0 md:transition-[width] ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } ${effectiveCollapsed ? "md:w-[76px]" : "md:w-64"}`}
      >
        <div
          className={`flex h-16 shrink-0 items-center ${effectiveCollapsed ? "justify-center px-2" : "justify-between px-4"}`}
        >
          <Link
            href={base || "/"}
            className="landing-display flex items-center gap-2 text-base text-[var(--l-ink)]"
          >
            <ShieldCheck className="h-5 w-5 shrink-0 text-[var(--l-orange)]" />
            {!effectiveCollapsed && <span className="whitespace-nowrap">GovernAI</span>}
          </Link>
          {!effectiveCollapsed && (
            <button
              type="button"
              onClick={toggleCollapsed}
              title="Collapse sidebar"
              className="hidden h-7 w-7 shrink-0 items-center justify-center rounded-full text-[var(--l-charcoal)]/50 transition-colors hover:bg-[var(--l-cream-deep)] hover:text-[var(--l-ink)] md:flex"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        {effectiveCollapsed && (
          <button
            type="button"
            onClick={toggleCollapsed}
            title="Expand sidebar"
            className="mx-auto mb-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-full text-[var(--l-charcoal)]/50 transition-colors hover:bg-[var(--l-cream-deep)] hover:text-[var(--l-ink)] md:flex"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        )}

        <nav className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden px-3 py-2">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== base && pathname.startsWith(item.href));
            const badge = "badge" in item ? item.badge : undefined;

            return (
              <Link
                key={item.name}
                href={item.href}
                title={effectiveCollapsed ? item.name : undefined}
                className={`relative flex h-10 items-center rounded-full text-sm font-medium transition-colors ${
                  effectiveCollapsed ? "justify-center px-0" : "gap-3 px-4"
                } ${!isActive ? "hover:bg-[var(--l-cream-deep)] active:scale-[0.98]" : ""}`}
                style={{ color: isActive ? "#ffffff" : "var(--l-charcoal)" }}
              >
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active-pill"
                    className="absolute inset-0 rounded-full bg-[var(--l-orange)]"
                    transition={{ type: "spring", stiffness: 500, damping: 38 }}
                  />
                )}
                <span className="relative z-10 shrink-0">
                  <item.icon className="h-4 w-4" />
                  {effectiveCollapsed && !!badge && (
                    <span
                      className="absolute -right-1 -top-1 h-2 w-2 rounded-full"
                      style={{ background: isActive ? "#ffffff" : "var(--l-orange)" }}
                    />
                  )}
                </span>
                {!effectiveCollapsed && (
                  <span className="relative z-10 flex-1 truncate">{item.name}</span>
                )}
                {!effectiveCollapsed && !!badge && (
                  <span
                    className="relative z-10 flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full px-1.5 text-[11px] font-bold"
                    style={{
                      background: isActive ? "rgba(255,255,255,0.25)" : "var(--l-orange)",
                      color: isActive ? "#ffffff" : "#ffffff",
                    }}
                  >
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-[var(--l-line)] p-3">
          <SignedInAs collapsed={effectiveCollapsed} />
        </div>
      </aside>
    </>
  );
}

/**
 * Whether the signed-in caller has any visible agent built with the
 * `ticketing` skill — the gate for showing "Draft Replies" at all. Changes
 * rarely (only when an agent is built/deleted or its skills edited), so this
 * polls far less often than the pending-count badge. Silently `false` on
 * failure — an API hiccup should hide the link, never crash the sidebar.
 */
function useHasTicketingAgent(): boolean {
  const load = useCallback(async () => {
    const data = await fetchApi("/agents/").catch(() => []);
    const agents = Array.isArray(data) ? data : [];
    return agents.some((a) => (a.skills ?? []).some((s: { id?: string }) => s?.id === "ticketing"));
  }, []);
  const { data } = useLive(load, 120000);
  return data ?? false;
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

function SignedInAs({ collapsed }: { collapsed: boolean }) {
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
      title={collapsed ? (displayName ?? "Signed in") : undefined}
      className={`flex items-center rounded-2xl p-2 transition-colors hover:bg-[var(--l-yellow-pale)]/40 ${collapsed ? "justify-center" : "gap-3"}`}
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--l-navy-deep)] text-[11px] font-semibold text-[var(--l-cream)]">
        {displayName ? initials(displayName) : "··"}
      </span>
      {!collapsed && (
        <span className="flex min-w-0 flex-col leading-tight">
          <span className="truncate text-[13px] font-semibold text-[var(--l-ink)]">
            {displayName ?? "Signed in"}
          </span>
          <span className="truncate font-mono text-[10.5px] text-[var(--l-charcoal)]/50">
            {subtitle ?? (me ? `${me.id.slice(0, 8)}…` : "loading…")}
          </span>
        </span>
      )}
    </Link>
  );
}
