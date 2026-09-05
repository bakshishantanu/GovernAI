"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { fetchApi } from "@/lib/api-client";
import { motion, useReducedMotion, DURATION, EASE } from "@/components/motion";
import {
  LayoutDashboard,
  Bot,
  Puzzle,
  ShieldCheck,
  FileText,
  DollarSign,
  Workflow,
  Shield,
  Radio,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Sidebar, per design/governai-pro Main.dc.html.
 *
 * Not a flat list: nav is split into labelled sections, each item is a 42px
 * pill, and items may carry trailing meta (a count, a live dot, a badge).
 * The org budget meter and the user card sit in a footer below it.
 */

type NavItem = {
  name: string;
  href: string;
  icon: LucideIcon;
  count?: string;
  live?: boolean;
  badge?: string;
};

const sections: { label: string; items: NavItem[] }[] = [
  {
    label: "Workspace",
    items: [
      { name: "Dashboard", href: "/", icon: LayoutDashboard },
      { name: "Agents", href: "/agents", icon: Bot },
      { name: "Runs", href: "/runs", icon: Radio, live: true },
      { name: "Skills", href: "/skills", icon: Puzzle },
    ],
  },
  {
    label: "Governance",
    items: [
      { name: "Policies", href: "/policies", icon: ShieldCheck },
      { name: "Audit log", href: "/audit", icon: FileText, live: true },
      { name: "Costs", href: "/costs", icon: DollarSign },
      { name: "Automations", href: "/automations", icon: Workflow, badge: "NEW" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const still = useReducedMotion();

  return (
    <aside className="sticky top-0 flex h-screen w-sidebar shrink-0 flex-col border-r-2 border-border bg-sidebar">
      {/* 60px to line up with the black bar beside it */}
      <div className="flex h-[60px] shrink-0 items-center gap-2.5 border-b-2 border-border px-4">
        <div className="gv-chip flex h-[30px] w-[30px] items-center justify-center rounded-[7px] border-2 border-border bg-gv-yellow">
          <Shield className="h-4 w-4 text-gv-ink" strokeWidth={2.6} />
        </div>
        <span className="font-display text-[19px] leading-none text-foreground">
          GovernAI
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
        {sections.map((section) => (
          <div key={section.label} className="contents">
            <div className="px-2.5 pb-1 pt-3.5 text-[10px] font-extrabold uppercase tracking-[0.06em] text-gv-label">
              {section.label}
            </div>

            {section.items.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/" && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={`relative flex h-navitem items-center gap-2.5 rounded-xl px-3 text-[14px] transition-colors ${
                    isActive
                      ? "font-extrabold text-sidebar-primary-foreground"
                      : "border-2 border-transparent font-bold text-gv-body hover:border-border hover:bg-muted"
                  }`}
                >
                  {/* One pill, shared across nav items: `layoutId` makes Motion
                      slide it from the old item to the new one instead of
                      cross-fading two pills. Under reduced motion it is a
                      plain div, so the active state still reads. */}
                  {isActive &&
                    (still ? (
                      <span className="gv-chip absolute inset-0 rounded-xl border-2 border-border bg-sidebar-primary" />
                    ) : (
                      <motion.span
                        layoutId="nav-active-pill"
                        className="gv-chip absolute inset-0 rounded-xl border-2 border-border bg-sidebar-primary"
                        transition={{ duration: DURATION.base, ease: EASE }}
                      />
                    ))}

                  <item.icon className="relative h-[17px] w-[17px] shrink-0" strokeWidth={2.2} />
                  <span className="relative">{item.name}</span>

                  {item.count && (
                    <span className="relative ml-auto font-mono text-[11px] font-medium">
                      {item.count}
                    </span>
                  )}
                  {item.live && (
                    <span className="relative ml-auto h-2 w-2 rounded-full border border-border bg-gv-teal" />
                  )}
                  {item.badge && (
                    <span className="relative ml-auto inline-flex h-[18px] items-center rounded-xl border border-border bg-gv-lilac px-[7px] text-[9.5px] font-extrabold text-gv-ink">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="flex flex-col gap-2.5 border-t-2 border-border p-3">
        <OrgBudgetMeter />

        <div className="flex items-center gap-2.5 p-0.5">
          <div className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full border-2 border-border bg-gv-lilac text-[11px] font-extrabold text-gv-ink">
            PL
          </div>
          <div className="flex min-w-0 flex-col leading-tight">
            <span className="truncate text-[12.5px] font-extrabold text-foreground">
              Pranav Ladha
            </span>
            <span className="truncate text-[11px] font-semibold text-gv-subtle">
              Admin
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}

type BudgetStatus = {
  cap_usd: number;
  window_hours: number;
  total_spend_usd: number;
  closest: {
    agent_id: string;
    name: string;
    spend_usd: number;
    cap_usd: number;
    percent_of_cap: number;
    suspended: boolean;
  } | null;
};

function money(value: number) {
  return value >= 0.01 ? `$${value.toFixed(2)}` : `$${value.toFixed(4)}`;
}

/**
 * The live budget meter, read from GET /costs/budget.
 *
 * It shows the agent **closest to its own cap**, not an org-wide percentage —
 * there is no org-wide budget in the system. The cap is enforced per agent
 * over a rolling window, so the agent nearest to being auto-suspended is the
 * number that actually means something, and it is the one worth watching
 * during a demo.
 *
 * The bar caps its width at 100% while the label keeps the true figure: an
 * agent can finish the call that crosses its cap before the guard suspends
 * it, so >100% is real and must not be hidden.
 */
function OrgBudgetMeter() {
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [failed, setFailed] = useState(false);
  const still = useReducedMotion();

  useEffect(() => {
    let cancelled = false;
    fetchApi("/costs/budget")
      .then((data) => {
        if (!cancelled) setBudget(data ?? null);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) {
    return (
      <div className="gv-chip rounded-lg border-2 border-border bg-gv-row p-3">
        <span className="text-[11.5px] font-extrabold text-foreground">Budget</span>
        <span className="mt-1.5 block font-mono text-[11px] text-gv-muted">
          unavailable
        </span>
      </div>
    );
  }

  const closest = budget?.closest ?? null;
  const percent = closest ? closest.percent_of_cap : 0;
  const heading = closest ? closest.name : "Budget";

  return (
    <div className="gv-chip rounded-lg border-2 border-border bg-gv-row p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="min-w-0 truncate text-[11.5px] font-extrabold text-foreground">
          {heading}
        </span>
        <span className="shrink-0 font-mono text-[11px] text-foreground">
          {budget ? `${percent.toFixed(0)}%` : "—"}
        </span>
      </div>

      <div className="mt-2 h-[9px] overflow-hidden rounded-xl border border-border bg-gv-track">
        {/* The bar fills to its value once, so the eye is drawn to how far it
            went. It never animates on refetch — a bar that re-fills every poll
            reads as spend happening when nothing has changed. */}
        <motion.div
          className={
            percent >= 100
              ? "h-full bg-gv-held"
              : percent >= 80
                ? "h-full bg-gv-watch"
                : "h-full bg-gv-teal"
          }
          initial={still ? false : { width: 0 }}
          animate={{ width: `${Math.min(percent, 100)}%` }}
          transition={{ duration: DURATION.slow, ease: EASE }}
        />
      </div>

      <span className="mt-1.5 block font-mono text-[11px] text-gv-muted">
        {!budget
          ? "loading…"
          : closest
            ? `${money(closest.spend_usd)} of ${money(closest.cap_usd)} · ${budget.window_hours}h`
            : `no spend in ${budget.window_hours}h`}
      </span>
    </div>
  );
}
