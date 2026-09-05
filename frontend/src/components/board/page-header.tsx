"use client";

import type { ReactNode } from "react";

/**
 * Page title block, per design/governai-pro.
 *
 * Bungee title with a plain-spoken subtitle under it, actions pushed right.
 * Bungee only — this is one of the three places it is allowed, and at 30px it
 * is well clear of its 19px floor.
 */
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-6 px-[22px] pt-5">
      <div className="flex min-w-0 flex-col gap-[5px]">
        <h1 className="font-display text-[30px] leading-none text-foreground">
          {title}
        </h1>
        {subtitle && (
          <p className="text-[13.5px] font-bold text-gv-onyellow">{subtitle}</p>
        )}
      </div>

      {actions && (
        <div className="flex shrink-0 items-center gap-2.5">{actions}</div>
      )}
    </div>
  );
}

/**
 * The pill buttons that sit beside a page title.
 * `tone` maps to a job: teal = the primary create action, paper = secondary.
 */
export function ActionPill({
  children,
  tone = "paper",
  onClick,
  type = "button",
}: {
  children: ReactNode;
  tone?: "teal" | "paper";
  onClick?: () => void;
  type?: "button" | "submit";
}) {
  const tones = {
    teal: "bg-gv-teal gv-card h-10 px-[17px] text-[13.5px]",
    paper: "bg-card gv-chip h-10 px-[15px] text-[13px]",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-xl border-2 border-border font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px ${tones[tone]}`}
    >
      {children}
    </button>
  );
}
