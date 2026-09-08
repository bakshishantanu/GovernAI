"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Activity, Ban, RotateCcw } from "lucide-react";

/**
 * Answer two, made operable.
 *
 * The claim on this page is "you can stop it right now", so the page lets you
 * do it rather than describing it. Throwing the switch suspends the agent, the
 * live call ticker stops, and the audit line that the real product would write
 * appears underneath — because the honest version of a kill switch is not just
 * that it stops, but that it is recorded.
 */

const LOG_SEED = [
  { t: "12:04:31", body: "tool_call.allowed — read_ticket", tone: "ok" },
  { t: "12:04:33", body: "llm_call — llama-3.3-70b · 1,284 tok · $0.0031", tone: "ok" },
  { t: "12:04:36", body: "tool_call.allowed — search_tickets", tone: "ok" },
] as const;

export function KillSwitchDemo() {
  const [killed, setKilled] = useState(false);
  const [calls, setCalls] = useState(148);
  const stillness = useReducedMotion();
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  // The ticker only runs while the agent is live. Stopping it is the point.
  useEffect(() => {
    if (killed) {
      if (timer.current) clearInterval(timer.current);
      return;
    }
    timer.current = setInterval(() => {
      setCalls((c) => c + 1);
    }, 1400);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [killed]);

  return (
    <section
      id="answer-two"
      className="relative bg-[var(--l-navy-deep)] text-[var(--l-cream)] py-28 md:py-36 overflow-hidden"
    >
      <div className="landing-noise absolute inset-0 pointer-events-none" />

      <div className="relative max-w-6xl mx-auto px-6 grid lg:grid-cols-2 gap-14 lg:gap-20 items-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange-soft)] font-semibold">
            Answer two
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-5xl leading-[1.05] tracking-tight">
            It&apos;s a switch. Throw it.
          </h2>
          <p className="mt-5 text-[var(--l-cream)]/60 leading-relaxed max-w-md">
            Not a ticket to the platform team. Not a deploy. One control, and
            the agent stops before its next tool call — inside a second, whether
            or not it is mid-run.
          </p>
          <p className="mt-4 text-[var(--l-cream)]/60 leading-relaxed max-w-md">
            It stays stopped, too. Nothing restarts an agent automatically; an
            admin has to bring it back, and that is recorded as well.
          </p>

          <p className="landing-hand mt-8 text-xl text-[var(--l-orange-soft)]">
            go on — it&apos;s a demo, nothing breaks
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="rounded-3xl border border-[var(--l-line-dark)] bg-white/[0.03] p-7 sm:p-8"
        >
          {/* agent header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-semibold">Ticket manager</p>
              <p className="font-mono text-[11px] text-[var(--l-cream)]/40 mt-0.5">
                A-1042 · owned by p.ladha
              </p>
            </div>

            <AnimatePresence mode="wait" initial={false}>
              {killed ? (
                <motion.span
                  key="susp"
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85 }}
                  transition={{ duration: 0.25 }}
                  className="inline-flex items-center gap-1.5 rounded-full border border-[#e07a6b]/40 bg-[#e07a6b]/10 px-2.5 py-1 text-xs font-medium text-[#e07a6b]"
                >
                  <Ban className="w-3 h-3" />
                  Suspended
                </motion.span>
              ) : (
                <motion.span
                  key="live"
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85 }}
                  transition={{ duration: 0.25 }}
                  className="inline-flex items-center gap-1.5 rounded-full border border-[var(--l-teal-soft)]/40 bg-[var(--l-teal-soft)]/10 px-2.5 py-1 text-xs font-medium text-[var(--l-teal-soft)]"
                >
                  <span className="relative flex h-1.5 w-1.5">
                    {!stillness && (
                      <span className="absolute inset-0 rounded-full bg-[var(--l-teal-soft)] animate-ping" />
                    )}
                    <span className="relative h-1.5 w-1.5 rounded-full bg-[var(--l-teal-soft)]" />
                  </span>
                  Active
                </motion.span>
              )}
            </AnimatePresence>
          </div>

          {/* the switch */}
          <div className="mt-7 flex items-center gap-5">
            <button
              type="button"
              role="switch"
              aria-checked={!killed}
              aria-label={
                killed ? "Reactivate Ticket manager" : "Suspend Ticket manager"
              }
              onClick={() => setKilled((k) => !k)}
              className={`switch-shell relative h-14 w-[6.5rem] shrink-0 rounded-full transition-colors duration-300 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--l-orange)]/50 ${
                killed ? "bg-[#8f2f24]" : "bg-[var(--l-teal)]"
              }`}
            >
              <motion.span
                layout
                transition={
                  stillness
                    ? { duration: 0 }
                    : { type: "spring", stiffness: 620, damping: 34 }
                }
                className={`switch-knob absolute top-1.5 h-11 w-11 rounded-full bg-[var(--l-cream)] ${
                  killed ? "right-1.5" : "left-1.5"
                }`}
              />
            </button>

            <div className="min-w-0">
              <p className="text-sm font-medium">
                {killed ? "Agent suspended" : "Kill switch"}
              </p>
              <p className="text-xs text-[var(--l-cream)]/50 mt-0.5">
                {killed
                  ? "Every tool call now denies, permissions unchanged."
                  : "One click. Effective before the next tool call."}
              </p>
            </div>
          </div>

          {/* live counters */}
          <div className="mt-7 grid grid-cols-3 gap-3 text-center">
            {[
              { label: "Calls today", value: calls.toString() },
              { label: "Spend", value: "$8.40" },
              { label: "State", value: killed ? "Suspended" : "Active" },
            ].map((s) => (
              <div
                key={s.label}
                className="rounded-xl border border-[var(--l-line-dark)] bg-white/[0.03] py-3"
              >
                <div className="font-mono text-sm tabular-nums">{s.value}</div>
                <div className="mt-1 text-[10px] uppercase tracking-wide text-[var(--l-cream)]/40">
                  {s.label}
                </div>
              </div>
            ))}
          </div>

          {/* the audit trail */}
          <div className="mt-7 rounded-2xl border border-[var(--l-line-dark)] bg-black/25 p-4">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.12em] text-[var(--l-cream)]/40">
              <Activity className="w-3 h-3" />
              Audit log — append only
            </div>

            <div className="mt-3 space-y-1.5 font-mono text-[11px] leading-relaxed">
              {LOG_SEED.map((l) => (
                <p key={l.t} className="text-[var(--l-cream)]/45">
                  <span className="text-[var(--l-cream)]/30">{l.t}</span>{" "}
                  {l.body}
                </p>
              ))}

              <AnimatePresence initial={false}>
                {killed && (
                  <>
                    <motion.p
                      key="kill"
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="text-[#e07a6b]"
                    >
                      <span className="opacity-60">12:04:38</span>{" "}
                      kill_switch.activated — by p.ladha
                    </motion.p>
                    <motion.p
                      key="denied"
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3, delay: 0.35 }}
                      className="text-[#e07a6b]"
                    >
                      <span className="opacity-60">12:04:38</span>{" "}
                      tool_call.denied — create_ticket_reply · agent suspended
                    </motion.p>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>

          {killed && (
            <motion.button
              type="button"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              onClick={() => setKilled(false)}
              className="mt-5 inline-flex items-center gap-2 text-xs font-medium text-[var(--l-cream)]/55 hover:text-[var(--l-cream)] transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reactivate and run it again
            </motion.button>
          )}
        </motion.div>
      </div>
    </section>
  );
}
