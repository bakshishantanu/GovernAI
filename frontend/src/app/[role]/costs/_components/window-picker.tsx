"use client";

import { motion } from "framer-motion";
import type { CostWindow } from "./cost-types";

const OPTIONS: { value: CostWindow; label: string }[] = [
  { value: "24h", label: "24h" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "all", label: "All time" },
];

/**
 * Which window the spend-by-agent/spend-by-model breakdown reads over.
 *
 * Deliberately separate from the hero tiles above it, which always report
 * the two canonical, fixed measures (all-time and the enforced 24h cap
 * window) — this only narrows the breakdown, so the two honest numbers up
 * top never get relabelled into meaning something else.
 */
export function WindowPicker({
  value,
  onChange,
}: {
  value: CostWindow;
  onChange: (window: CostWindow) => void;
}) {
  return (
    <div className="inline-flex items-center gap-1 rounded-full bg-[var(--l-cream-deep)] p-1">
      {OPTIONS.map((opt) => {
        const isOn = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            aria-pressed={isOn}
            className="relative rounded-full px-3 py-1.5 text-[12.5px] font-medium transition-colors"
            style={{ color: isOn ? "#ffffff" : "var(--l-charcoal)" }}
          >
            {isOn && (
              <motion.span
                layoutId="cost-window-pill"
                className="absolute inset-0 rounded-full bg-[var(--l-orange)]"
                transition={{ type: "spring", stiffness: 500, damping: 38 }}
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
