"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
                  className={`flex h-navitem items-center gap-2.5 rounded-xl px-3 text-[14px] transition-colors ${
                    isActive
                      ? "gv-chip border-2 border-border bg-sidebar-primary font-extrabold text-sidebar-primary-foreground"
                      : "border-2 border-transparent font-bold text-gv-body hover:border-border hover:bg-muted"
                  }`}
                >
                  <item.icon className="h-[17px] w-[17px] shrink-0" strokeWidth={2.2} />
                  {item.name}

                  {item.count && (
                    <span className="ml-auto font-mono text-[11px] font-medium">
                      {item.count}
                    </span>
                  )}
                  {item.live && (
                    <span className="ml-auto h-2 w-2 rounded-full border border-border bg-gv-teal" />
                  )}
                  {item.badge && (
                    <span className="ml-auto inline-flex h-[18px] items-center rounded-xl border border-border bg-gv-lilac px-[7px] text-[9.5px] font-extrabold text-gv-ink">
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

/**
 * TODO: wire to GET /api/v1/costs/summary against the org cap.
 * Hardcoded until then, and says so rather than pretending.
 */
function OrgBudgetMeter() {
  const percent = 78;

  return (
    <div className="gv-chip rounded-lg border-2 border-border bg-gv-row p-3">
      <div className="flex items-center justify-between">
        <span className="text-[11.5px] font-extrabold text-foreground">
          Org budget today
        </span>
        <span className="font-mono text-[11px] text-foreground">{percent}%</span>
      </div>

      <div className="mt-2 h-[9px] overflow-hidden rounded-xl border border-border bg-gv-track">
        <div
          className="h-full bg-gv-teal"
          style={{ width: `${percent}%` }}
        />
      </div>

      <span className="mt-1.5 block font-mono text-[11px] text-gv-muted">
        placeholder — not wired
      </span>
    </div>
  );
}
