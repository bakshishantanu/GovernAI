"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, PlayCircle, Skull, RotateCcw, Loader2 } from "lucide-react";
import { ApiError, fetchApi, type ApiViolation } from "@/lib/api-client";
import type { Agent } from "../../_components/agent-types";

const STAGES = ["DRAFT", "APPROVED", "ACTIVE"] as const;

type Action = "submit" | "activate" | "kill" | "reactivate";

/**
 * The passport's own lifecycle, drawn as a stamped route rather than a
 * status pill: three checkpoints an agent must clear in order, with the
 * suspended/revoked states breaking off to the side since they aren't part
 * of the forward path. Whichever action is legal from the current state
 * renders as the one live button — never a whole toolbar of mostly-disabled
 * ones.
 */
export function LifecycleTrack({
  agent,
  isAdmin,
  onChanged,
}: {
  agent: Agent;
  isAdmin: boolean;
  onChanged: (agent: Agent) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [violations, setViolations] = useState<ApiViolation[]>([]);
  const state = agent.passport.lifecycle_state;
  const stageIndex = STAGES.indexOf(state as (typeof STAGES)[number]);
  const broken = state === "SUSPENDED" || state === "REVOKED";

  async function run(action: Action, endpoint: string, method: "PATCH" | "POST") {
    setBusy(true);
    setError("");
    setViolations([]);
    try {
      const updated = await fetchApi(endpoint, { method });
      onChanged(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} this agent.`);
      // A refused submission comes back with every broken rule. Showing only
      // the headline would leave the builder guessing at what to change.
      setViolations(err instanceof ApiError ? err.violations : []);
    } finally {
      setBusy(false);
    }
  }

  const cta =
    state === "DRAFT"
      ? { label: "Submit for review", icon: ShieldCheck, action: () => run("submit", `/agents/${agent.id}/submit`, "PATCH"), adminOnly: false }
      : state === "APPROVED"
      ? { label: "Activate", icon: PlayCircle, action: () => run("activate", `/agents/${agent.id}/activate`, "PATCH"), adminOnly: true }
      : state === "ACTIVE"
      ? { label: "Kill switch", icon: Skull, action: () => run("kill", `/agents/${agent.id}/kill`, "POST"), adminOnly: true, danger: true }
      : state === "SUSPENDED"
      ? { label: "Reactivate", icon: RotateCcw, action: () => run("reactivate", `/agents/${agent.id}/reactivate`, "POST"), adminOnly: true }
      : null;

  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_4px_0_0_rgba(22,19,14,0.12)]">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-1">
          {STAGES.map((s, i) => {
            const done = !broken && i <= stageIndex;
            const isNext = !broken && i === stageIndex + 1;
            return (
              <div key={s} className="flex items-center">
                <motion.div
                  initial={false}
                  animate={{ scale: done ? 1 : 0.9, opacity: done ? 1 : isNext ? 0.6 : 0.3 }}
                  className="flex items-center gap-2 rounded-full px-3 py-1.5"
                  style={{
                    background: done ? "var(--l-teal)" : "transparent",
                    border: done ? "none" : "2px dashed var(--l-charcoal)",
                  }}
                >
                  <span
                    className="landing-display text-[11px] uppercase tracking-wide"
                    style={{ color: done ? "#ffffff" : "var(--l-charcoal)" }}
                  >
                    {s}
                  </span>
                </motion.div>
                {i < STAGES.length - 1 && (
                  <span className="mx-1.5 h-[2px] w-6" style={{ background: done ? "var(--l-teal)" : "var(--l-line)" }} />
                )}
              </div>
            );
          })}
          {broken && (
            <span
              className="landing-display ml-2 rounded-full px-3 py-1.5 text-[11px] uppercase tracking-wide"
              style={{
                background: state === "REVOKED" ? "#8a1f1f" : "var(--l-orange-deep)",
                color: "#ffffff",
              }}
            >
              {state}
            </span>
          )}
        </div>

        {cta && (!cta.adminOnly || isAdmin) && (
          <motion.button
            onClick={cta.action}
            disabled={busy}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_rgba(22,19,14,0.2)] disabled:opacity-50"
            style={{ background: cta.danger ? "var(--l-orange-deep)" : "var(--l-ink)" }}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <cta.icon className="h-4 w-4" />}
            {cta.label}
          </motion.button>
        )}
        {cta && cta.adminOnly && !isAdmin && (
          <span className="font-mono text-[11px] text-[var(--l-charcoal)]/45">
            {cta.label} — admin only
          </span>
        )}
      </div>

      {error && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 text-[12.5px] font-medium text-[var(--l-orange-deep)]"
        >
          {error}
        </motion.p>
      )}

      {violations.length > 0 && (
        <ul className="mt-2 space-y-1.5">
          {violations.map((v) => (
            <li
              key={v.rule + v.message}
              className="rounded-xl border-2 border-[var(--l-orange-deep)]/40 bg-[var(--l-orange-soft)]/25 px-3.5 py-2 text-[12.5px] leading-snug text-[var(--l-ink)]"
            >
              {v.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
