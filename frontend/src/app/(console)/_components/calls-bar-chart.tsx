"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { HourBucket } from "./dashboard-data";

/**
 * The track's fixed pixel height.
 *
 * One confirmed bug: a `%` height on the bar only resolves against an
 * ancestor with an *explicit* height, and the intermediate `<button>` here
 * is `height: auto` — the percentage silently computed to 0px. Verified via
 * `getComputedStyle` (not just a visual check): switching to a pixel value
 * against this constant fixed it — the bar's real layout height reads
 * correctly now.
 *
 * The bar's *growth* is animated as `scaleY` from an unanimated fixed
 * height, not by animating `height` itself — mainly because it's the
 * cheaper, transform-based way to do it, not because height-animation was
 * proven broken. It looked that way mid-investigation: `getBoundingClientRect`
 * read `scaleY(0)` (i.e. visually collapsed) on a tab confirmed
 * `document.visibilityState === "visible"`, several seconds after load —
 * but a screenshot taken right after showed the bars fully grown in. That
 * gap is a caution about this project's test harness, not a finding about
 * Framer Motion: a screenshot forces a real paint, a bare JS
 * `getBoundingClientRect()` call does not, and in a throttled/backgrounded
 * tab the two can disagree. Trust the screenshot over the probe here.
 */
const TRACK_PX = 160;

/**
 * Real per-hour call counts as bars, with a hover tooltip and an
 * All-calls / Denied-only toggle — the structural equivalent of the
 * reference's Sale/Rent toggle, mapped onto data this product actually has.
 */
export function CallsBarChart({
  buckets,
  loading,
}: {
  buckets: HourBucket[];
  loading?: boolean;
}) {
  const [mode, setMode] = useState<"all" | "denied">("all");
  const [hover, setHover] = useState<number | null>(null);

  const values = buckets.map((b) => (mode === "all" ? b.total : b.denied));
  const max = Math.max(1, ...values);

  return (
    <div className="rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream)] p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <span className="landing-display text-lg text-[var(--l-ink)]">Calls per hour</span>
        <div className="flex items-center gap-1 rounded-full border border-[var(--l-line)] p-0.5 text-xs">
          {(["all", "denied"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className="relative rounded-full px-3 py-1 font-medium transition-colors"
              style={{ color: mode === m ? "#ffffff" : "var(--l-charcoal)" }}
            >
              {mode === m && (
                <motion.span
                  layoutId="bar-mode-pill"
                  className="absolute inset-0 rounded-full bg-[var(--l-orange)]"
                  transition={{ type: "spring", stiffness: 500, damping: 36 }}
                />
              )}
              <span className="relative z-10">{m === "all" ? "All calls" : "Denied only"}</span>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-end gap-2" style={{ height: TRACK_PX }}>
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className="flex-1 animate-pulse rounded-t-md bg-[var(--l-line)]/60"
              style={{ height: `${20 + (i % 4) * 15}%` }}
            />
          ))}
        </div>
      ) : buckets.length === 0 ? (
        <p className="text-sm text-[var(--l-charcoal)]/60">No activity recorded yet.</p>
      ) : (
        <div className="relative flex items-end gap-1.5" style={{ height: TRACK_PX }}>
          {buckets.map((b, i) => {
            const v = mode === "all" ? b.total : b.denied;
            const px = Math.max((v / max) * TRACK_PX, v > 0 ? 6 : 2);
            return (
              <div key={b.hourKey} className="relative flex-1">
                <AnimatePresence>
                  {hover === i && (
                    <motion.div
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="pointer-events-none absolute -top-9 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-md bg-[var(--l-ink)] px-2 py-1 text-[11px] font-semibold text-[var(--l-cream)]"
                    >
                      {v} · {b.label}
                    </motion.div>
                  )}
                </AnimatePresence>
                <button
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(i)}
                  onBlur={() => setHover(null)}
                  aria-label={`${v} calls, ${b.label}`}
                  className="block w-full"
                >
                  <motion.div
                    className="w-full origin-bottom rounded-t-md"
                    style={{
                      height: px,
                      background: mode === "denied" ? "var(--l-orange)" : "var(--l-teal)",
                      opacity: hover === null || hover === i ? 1 : 0.45,
                    }}
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: 1 }}
                    transition={{ duration: 0.4, delay: i * 0.02, ease: "easeOut" }}
                  />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
