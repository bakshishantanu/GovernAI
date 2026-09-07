"use client";

import { motion } from "framer-motion";
import { Receipt } from "lucide-react";

/**
 * Answer one, drawn as an itemised bill.
 *
 * A budget owner reads invoices, not dashboards — so the first answer is
 * presented in the document form they already trust. Every line is one real
 * thing the platform records: an agent, its model, its call count, its spend
 * against its own cap.
 */

const LINES = [
  {
    agent: "Ticket manager",
    id: "A-1042",
    model: "llama-3.3-70b",
    calls: 148,
    spend: 8.4,
    cap: 20,
  },
  {
    agent: "RAG researcher",
    id: "A-1051",
    model: "gemini-2.5-flash",
    calls: 96,
    spend: 14.02,
    cap: 15,
  },
  {
    agent: "SQL analyst",
    id: "A-1063",
    model: "llama-3.3-70b",
    calls: 41,
    spend: 3.18,
    cap: 12,
  },
  {
    agent: "Ticket triage (staging)",
    id: "A-1077",
    model: "gemini-2.5-flash",
    calls: 12,
    spend: 0.42,
    cap: 5,
  },
];

const TOTAL = LINES.reduce((sum, l) => sum + l.spend, 0);
const CAP_TOTAL = LINES.reduce((sum, l) => sum + l.cap, 0);

function money(n: number) {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

export function SpendReceipt() {
  return (
    <section
      id="answer-one"
      className="relative bg-[var(--l-cream-deep)] py-28 md:py-36"
    >
      <div className="max-w-6xl mx-auto px-6 grid lg:grid-cols-[1fr_minmax(0,1.05fr)] gap-14 lg:gap-20 items-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold">
            Answer one
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-5xl leading-[1.05] tracking-tight text-[var(--l-charcoal)]">
            It&apos;s an itemised bill, not an estimate.
          </h2>
          <p className="mt-5 text-[var(--l-charcoal)]/70 leading-relaxed max-w-md">
            Every model call writes a cost row the moment it happens — tokens
            in, tokens out, model, price. Spend is attributed to the agent that
            caused it, so &ldquo;what are we spending on AI&rdquo; stops being a
            finance exercise and becomes a line you can read.
          </p>

          <ul className="mt-8 space-y-3">
            {[
              "Attributed per agent, per execution, per model",
              "Written at the time of the call, not reconciled later",
              "Each agent carries its own cap, not one org-wide guess",
            ].map((point) => (
              <li
                key={point}
                className="flex gap-3 text-sm text-[var(--l-charcoal)]/80"
              >
                <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[var(--l-orange)] shrink-0" />
                {point}
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 32, rotate: 1.2 }}
          whileInView={{ opacity: 1, y: 0, rotate: 1.2 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
          className="relative"
        >
          <div className="receipt-paper rounded-t-2xl shadow-[0_14px_0_0_rgba(22,19,14,0.12)] overflow-hidden">
            {/* header */}
            <div className="px-7 pt-7 pb-5 border-b border-dashed border-[var(--l-line)]">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2.5">
                  <Receipt className="w-4 h-4 text-[var(--l-orange)]" />
                  <span className="landing-display text-lg text-[var(--l-ink)]">
                    Agent spend
                  </span>
                </div>
                <span className="font-mono text-[11px] text-[var(--l-charcoal)]/50 text-right leading-relaxed">
                  ACME CORP
                  <br />
                  today · 24h window
                </span>
              </div>
            </div>

            {/* column heads */}
            <div className="px-7 pt-4 grid grid-cols-[1fr_auto_auto] gap-4 font-mono text-[10px] uppercase tracking-[0.1em] text-[var(--l-charcoal)]/45">
              <span>Agent</span>
              <span className="text-right">Calls</span>
              <span className="text-right w-24">Spend / cap</span>
            </div>

            {/* lines */}
            <div className="px-7 pb-2">
              {LINES.map((line, i) => {
                const pct = Math.min(100, (line.spend / line.cap) * 100);
                const hot = pct >= 90;
                return (
                  <motion.div
                    key={line.id}
                    initial={{ opacity: 0, x: -8 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true, amount: 0.6 }}
                    transition={{ duration: 0.4, delay: 0.15 + i * 0.09 }}
                    className="grid grid-cols-[1fr_auto_auto] gap-4 items-baseline py-3"
                  >
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-[var(--l-ink)] truncate">
                        {line.agent}
                      </span>
                      <span className="block font-mono text-[11px] text-[var(--l-charcoal)]/45 truncate">
                        {line.id} · {line.model}
                      </span>
                    </span>

                    <span className="font-mono text-sm tabular-nums text-[var(--l-charcoal)]/70 text-right">
                      {line.calls}
                    </span>

                    <span className="w-24 text-right">
                      <span
                        className={`font-mono text-sm tabular-nums ${
                          hot
                            ? "text-[var(--l-orange-deep)] font-semibold"
                            : "text-[var(--l-ink)]"
                        }`}
                      >
                        {money(line.spend)}
                      </span>
                      <span className="block font-mono text-[10px] text-[var(--l-charcoal)]/40">
                        of {money(line.cap)}
                      </span>
                      <span className="mt-1.5 block h-1 w-full rounded-full bg-[var(--l-line)] overflow-hidden">
                        <motion.span
                          initial={{ width: 0 }}
                          whileInView={{ width: `${pct}%` }}
                          viewport={{ once: true, amount: 0.6 }}
                          transition={{
                            duration: 0.7,
                            delay: 0.3 + i * 0.09,
                            ease: "easeOut",
                          }}
                          className={`block h-full rounded-full ${
                            hot
                              ? "bg-[var(--l-orange)]"
                              : "bg-[var(--l-teal-soft)]"
                          }`}
                        />
                      </span>
                    </span>
                  </motion.div>
                );
              })}
            </div>

            {/* total */}
            <div className="px-7 py-5 border-t-2 border-[var(--l-ink)]/80 flex items-end justify-between">
              <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-[var(--l-charcoal)]/60">
                Total today
              </span>
              <span className="text-right">
                <span className="landing-display text-3xl text-[var(--l-ink)] tabular-nums">
                  {money(TOTAL)}
                </span>
                <span className="block font-mono text-[11px] text-[var(--l-charcoal)]/45">
                  against {money(CAP_TOTAL)} of caps
                </span>
              </span>
            </div>

            <div
              className="perf"
              style={{ ["--perf-bg" as string]: "var(--l-cream-deep)" }}
            />
          </div>

          <p className="landing-hand mt-6 text-xl text-[var(--l-charcoal)]/70 max-w-xs">
            RAG researcher is at 93% of its cap — it will pause itself before it
            reaches you.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
