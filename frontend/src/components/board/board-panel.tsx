"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion, DURATION, EASE } from "@/components/motion";
import {
  Table2,
  Columns3,
  ListFilter,
  ShieldCheck,
  LayoutDashboard,
  Search,
  User,
  Filter,
  ArrowUpDown,
  Grid2x2,
  X,
} from "lucide-react";

/**
 * The saved-view tabs and the panel they open onto,
 * per design/governai-pro Main.dc.html.
 *
 * The active tab loses its bottom border and the panel loses its top-left
 * radius, so the two read as one shape — the tab is physically attached to
 * the surface it controls. That join is the whole point; don't round the
 * panel's top-left corner.
 *
 * Icons are named by STRING, not passed as components. These are client
 * components, and a React component cannot be serialised across the server
 * boundary — passing `icon={Table2}` from a server page throws.
 */

const ICONS = {
  table: Table2,
  kanban: Columns3,
  timeline: ListFilter,
  compliance: ShieldCheck,
  overview: LayoutDashboard,
  search: Search,
  person: User,
  filter: Filter,
  sort: ArrowUpDown,
  group: Grid2x2,
} as const;

export type IconName = keyof typeof ICONS;

export type BoardView = {
  name: string;
  icon: IconName;
};

export function ViewTabs({
  views,
  active,
  onSelect,
}: {
  views: BoardView[];
  active: string;
  onSelect?: (name: string) => void;
}) {
  return (
    <div className="flex items-center gap-1.5 px-[22px] pt-4">
      {views.map((view) => {
        const Icon = ICONS[view.icon];
        const isActive = view.name === active;

        return (
          <button
            key={view.name}
            type="button"
            onClick={onSelect ? () => onSelect(view.name) : undefined}
            className={
              isActive
                ? "flex h-9 items-center gap-[7px] rounded-t-xl border-2 border-b-0 border-border bg-card px-3.5 text-[13px] font-extrabold text-gv-ink"
                : "flex h-[34px] items-center gap-[7px] rounded-xl border-2 border-border bg-gv-tab-idle px-[13px] text-[13px] font-bold text-foreground transition-colors hover:bg-card"
            }
          >
            <Icon className="h-[15px] w-[15px]" strokeWidth={2.2} />
            {view.name}
          </button>
        );
      })}
    </div>
  );
}

export function BoardPanel({
  toolbar,
  children,
  attached = true,
}: {
  toolbar?: ReactNode;
  children: ReactNode;
  /** false when the panel stands alone with no tabs above it */
  attached?: boolean;
}) {
  const still = useReducedMotion();

  return (
    <motion.div
      initial={still ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.slow, ease: EASE }}
      className={`gv-panel mx-[22px] mb-[22px] flex min-h-0 flex-1 flex-col overflow-hidden border-2 border-border bg-card ${
        attached ? "rounded-b-lg rounded-tr-lg" : "rounded-lg"
      }`}
    >
      {toolbar && (
        <div className="flex h-[50px] shrink-0 items-center gap-2 overflow-x-auto border-b-2 border-border px-3.5">
          {toolbar}
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </motion.div>
  );
}

/**
 * A toolbar control. `active` is for a filter that is currently applied — the
 * canvas fills it pink and gives it a remove affordance, so an applied filter
 * is never invisible.
 */
export function ToolbarChip({
  children,
  icon,
  active = false,
  onClick,
  onRemove,
}: {
  children: ReactNode;
  icon?: IconName;
  active?: boolean;
  onClick?: () => void;
  onRemove?: () => void;
}) {
  const Icon = icon ? ICONS[icon] : null;

  return (
    <span
      className={`flex h-8 shrink-0 items-center gap-[7px] whitespace-nowrap rounded-xl border-2 border-border px-3 text-[12.5px] ${
        active
          ? "gv-chip bg-gv-pink font-extrabold text-gv-ink"
          : "bg-gv-row font-bold text-foreground"
      }`}
    >
      <button
        type="button"
        onClick={onClick}
        className="flex items-center gap-[7px]"
      >
        {Icon && <Icon className="h-3.5 w-3.5" strokeWidth={2.2} />}
        {children}
      </button>

      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Remove filter"
          className="-mr-1 flex h-4 w-4 items-center justify-center"
        >
          <X className="h-3 w-3" strokeWidth={2.8} />
        </button>
      )}
    </span>
  );
}

/**
 * The "Live · 2s ago" marker at the right of a board toolbar.
 *
 * The dot pulses **only when `live` is true**. A pulsing dot is a claim that
 * something is connected, so a page with no open stream must not make it —
 * every caller that is merely showing a static count passes nothing and gets
 * a still dot.
 */
export function LiveMarker({
  label = "Live",
  live = false,
}: {
  label?: string;
  /** true only when a stream is actually open */
  live?: boolean;
}) {
  const still = useReducedMotion();

  return (
    <span className="ml-auto flex shrink-0 items-center gap-[7px] text-[12px] font-bold text-gv-muted">
      <span className="relative flex h-2 w-2 shrink-0">
        {live && !still && (
          <motion.span
            aria-hidden="true"
            className="absolute inset-0 rounded-full bg-gv-teal"
            animate={{ opacity: [0.65, 0, 0.65], scale: [1, 2.1, 1] }}
            transition={{ duration: 1.9, ease: "easeOut", repeat: Infinity }}
          />
        )}
        <span
          className={`relative h-2 w-2 rounded-full border border-border ${
            live ? "bg-gv-teal" : "bg-gv-rule"
          }`}
        />
      </span>
      {label}
    </span>
  );
}
