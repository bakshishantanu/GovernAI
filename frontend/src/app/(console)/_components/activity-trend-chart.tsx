"use client";

import { motion, useReducedMotion } from "framer-motion";
import { TrendingUp } from "lucide-react";
import type { HourBucket } from "./dashboard-data";

const W = 600;
const H = 180;
const PAD_L = 8;
const PAD_R = 8;
const PAD_T = 24;
const PAD_B = 24;

function buildPath(buckets: HourBucket[], max: number) {
  if (buckets.length < 2) return { line: "", area: "" };
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;
  const step = innerW / (buckets.length - 1);

  const points = buckets.map((b, i) => {
    const x = PAD_L + i * step;
    const y = PAD_T + innerH - (max === 0 ? 0 : (b.total / max) * innerH);
    return [x, y] as const;
  });

  const line = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area =
    line +
    ` L${points[points.length - 1][0].toFixed(1)},${PAD_T + innerH}` +
    ` L${points[0][0].toFixed(1)},${PAD_T + innerH} Z`;

  return { line, area, points };
}

/**
 * Real tool-call volume, bucketed by hour across the actual observed range
 * (see dashboard-data.ts) — not a smoothed or invented series. The peak
 * callout names the genuine busiest hour, whatever it is.
 */
export function ActivityTrendChart({
  buckets,
  loading,
}: {
  buckets: HourBucket[];
  loading?: boolean;
}) {
  const still = useReducedMotion();
  const max = Math.max(1, ...buckets.map((b) => b.total));
  const { line, area, points } = buildPath(buckets, max);
  const total = buckets.reduce((s, b) => s + b.total, 0);
  const peakIdx = buckets.reduce((mi, b, i) => (b.total > buckets[mi].total ? i : mi), 0);
  const peak = buckets[peakIdx];

  return (
    <div className="rounded-2xl border border-[var(--l-line)] bg-[var(--l-cream)] p-5">
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-[var(--l-teal)]" />
          <span className="landing-display text-lg text-[var(--l-ink)]">Tool-call activity</span>
        </div>
        <span className="text-xs text-[var(--l-charcoal)]/50">by hour, real range</span>
      </div>

      {loading ? (
        <div className="mt-4 h-[180px] animate-pulse rounded-lg bg-[var(--l-line)]/60" />
      ) : buckets.length < 2 ? (
        <p className="mt-6 text-sm text-[var(--l-charcoal)]/60">
          Not enough activity yet to chart a trend — run an agent a few times to see one form.
        </p>
      ) : (
        <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-[1fr_180px]">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Tool calls per hour">
            {/* gridlines at 0 / half / max, with real value labels */}
            {[0, 0.5, 1].map((f) => {
              const y = PAD_T + (H - PAD_T - PAD_B) * (1 - f);
              return (
                <g key={f}>
                  <line
                    x1={PAD_L}
                    x2={W - PAD_R}
                    y1={y}
                    y2={y}
                    stroke="var(--l-line)"
                    strokeWidth="1"
                  />
                  <text x={W - PAD_R} y={y - 4} textAnchor="end" fontSize="9" fill="var(--l-charcoal)" opacity="0.5">
                    {Math.round(max * f)}
                  </text>
                </g>
              );
            })}

            <defs>
              <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--l-teal)" stopOpacity="0.28" />
                <stop offset="100%" stopColor="var(--l-teal)" stopOpacity="0" />
              </linearGradient>
            </defs>

            <motion.path
              d={area}
              fill="url(#trendFill)"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            />
            <motion.path
              d={line}
              fill="none"
              stroke="var(--l-teal)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={still ? undefined : { pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={still ? { duration: 0 } : { duration: 1, ease: "easeOut" }}
            />

            {points && points[peakIdx] && (
              <motion.g
                initial={{ opacity: 0, scale: 0.6 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: 1 }}
              >
                <circle cx={points[peakIdx][0]} cy={points[peakIdx][1]} r="4" fill="var(--l-orange)" stroke="var(--l-cream)" strokeWidth="1.5" />
                <rect
                  x={Math.min(W - 70, Math.max(4, points[peakIdx][0] - 24))}
                  y={Math.max(2, points[peakIdx][1] - 22)}
                  width="52"
                  height="16"
                  rx="8"
                  fill="var(--l-ink)"
                />
                <text
                  x={Math.min(W - 44, Math.max(30, points[peakIdx][0]))}
                  y={Math.max(13, points[peakIdx][1] - 11)}
                  textAnchor="middle"
                  fontSize="9.5"
                  fontWeight="700"
                  fill="var(--l-cream)"
                >
                  {peak.total} calls
                </text>
              </motion.g>
            )}

            {/* first/last x labels only, to avoid clutter with real dense buckets */}
            <text x={PAD_L} y={H - 6} fontSize="9" fill="var(--l-charcoal)" opacity="0.5">
              {buckets[0].label}
            </text>
            <text x={W - PAD_R} y={H - 6} textAnchor="end" fontSize="9" fill="var(--l-charcoal)" opacity="0.5">
              {buckets[buckets.length - 1].label}
            </text>
          </svg>

          <div className="flex flex-col gap-2.5">
            <div className="rounded-xl bg-[var(--l-teal)]/10 p-3">
              <div className="text-[11px] font-medium text-[var(--l-teal)]">Total calls</div>
              <div className="landing-display text-xl text-[var(--l-ink)] tabular-nums">{total}</div>
            </div>
            <div className="rounded-xl bg-[var(--l-cream-deep)] p-3">
              <div className="text-[11px] font-medium text-[var(--l-charcoal)]/60">Busiest hour</div>
              <div className="landing-display text-xl text-[var(--l-ink)] tabular-nums">{peak.total}</div>
              <div className="text-[11px] text-[var(--l-charcoal)]/50">{peak.label}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
