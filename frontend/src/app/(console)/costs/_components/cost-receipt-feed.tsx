"use client";

import { motion } from "framer-motion";
import { money, receiptEdge, type CostEvent } from "./cost-types";

const EDGE = receiptEdge(16);

function timeAgo(iso: string) {
  const s = Math.max(0, Math.floor((Date.now() - +new Date(iso)) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/**
 * Every real LLM-call cost row, printed like an actual receipt — a torn
 * paper edge, a dashed perforation between lines, monospace figures, and a
 * running total that ticks down the tape the way a real till does.
 */
export function CostReceiptFeed({
  events,
  agentName,
  loading,
}: {
  events: CostEvent[];
  agentName: (id: string) => string;
  loading: boolean;
}) {
  const subtotal = events.reduce((sum, e) => sum + e.cost_usd, 0);

  return (
    <div className="relative overflow-hidden rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] shadow-[0_5px_0_0_rgba(22,19,14,0.14)]">
      <div
        aria-hidden
        className="h-3 w-full bg-[var(--l-cream-deep)]"
        style={{ clipPath: EDGE }}
      />

      <div className="px-5 pb-2 pt-3">
        <h2 className="landing-display text-center text-base text-[var(--l-ink)]">Cost receipt</h2>
        <p className="text-center font-mono text-[10px] uppercase tracking-[0.16em] text-[var(--l-charcoal)]/45">
          most recent {events.length} calls
        </p>
      </div>

      <div className="max-h-[360px] space-y-0 overflow-y-auto px-5">
        {loading ? (
          <div className="space-y-2 py-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-[var(--l-line)]/50" />
            ))}
          </div>
        ) : events.length === 0 ? (
          <p className="py-8 text-center text-[12.5px] text-[var(--l-charcoal)]/50">No calls billed yet.</p>
        ) : (
          events.map((e, i) => (
            <motion.div
              key={e.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25, delay: Math.min(i, 12) * 0.02 }}
              className="flex items-center justify-between gap-3 border-b border-dashed border-[var(--l-ink)]/12 py-2 last:border-0"
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate font-mono text-[11.5px] text-[var(--l-ink)]">
                  {e.model ?? "unknown model"}
                </span>
                <span className="block truncate text-[10.5px] text-[var(--l-charcoal)]/50">
                  {agentName(e.agent_id)} · {timeAgo(e.timestamp)}
                </span>
              </span>
              <span className="shrink-0 font-mono text-[12.5px] font-semibold text-[var(--l-ink)]">
                {money(e.cost_usd)}
              </span>
            </motion.div>
          ))
        )}
      </div>

      <div className="flex items-center justify-between border-t-2 border-dashed border-[var(--l-ink)]/20 px-5 py-3">
        <span className="landing-display text-sm text-[var(--l-ink)]">Subtotal</span>
        <span className="font-mono text-sm font-bold text-[var(--l-ink)]">{money(subtotal)}</span>
      </div>

      <div
        aria-hidden
        className="h-3 w-full rotate-180 bg-[var(--l-cream-deep)]"
        style={{ clipPath: EDGE }}
      />
    </div>
  );
}
