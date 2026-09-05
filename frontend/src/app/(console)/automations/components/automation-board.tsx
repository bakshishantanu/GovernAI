"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { BoardPanel, ViewTabs, ToolbarChip } from "@/components/board/board-panel";
import { motion, staggerContainer, staggerItem, useReducedMotion } from "@/components/motion";
import { CreateAutomationButton } from "./create-automation-button";
import {
  ShieldOff,
  ShieldCheck,
  Bell,
  OctagonX,
  ShieldAlert,
  DollarSign,
  CircleSlash,
} from "lucide-react";

/**
 * Automations — recipe-style rules, and the record of what they did.
 *
 * The run history sits on the same page as the rules on purpose. A rule that
 * can suspend an agent is only trustworthy if you can see what it has
 * actually done, and putting that behind a second click invites shipping
 * rules nobody ever checks.
 *
 * SKIPPED runs are shown, not filtered out. "This rule looked and decided not
 * to act" is evidence that it is working; hiding it would make a quiet rule
 * indistinguishable from a broken one.
 */

export type Automation = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  agent_id: string | null;
  trigger_type: "TOOL_DENIED" | "SPEND_THRESHOLD" | "AGENT_SUSPENDED";
  trigger_config: Record<string, any>;
  action_type: "SUSPEND_AGENT" | "RAISE_ALERT";
  action_config: Record<string, any>;
};

type AutomationRun = {
  id: string;
  automation_id: string;
  agent_id: string | null;
  triggered_at: string;
  outcome: "FIRED" | "SKIPPED" | "FAILED";
  detail: string;
};

const TRIGGERS = {
  TOOL_DENIED: { label: "Tool call denied", Icon: ShieldAlert },
  SPEND_THRESHOLD: { label: "Spend threshold", Icon: DollarSign },
  AGENT_SUSPENDED: { label: "Agent suspended", Icon: OctagonX },
} as const;

const ACTIONS = {
  SUSPEND_AGENT: { label: "Suspend the agent", Icon: OctagonX, tone: "bg-gv-held text-gv-held-fg" },
  RAISE_ALERT: { label: "Raise an alert", Icon: Bell, tone: "bg-gv-review text-gv-review-fg" },
} as const;

const OUTCOMES = {
  FIRED: { label: "Fired", fill: "bg-gv-cleared text-gv-cleared-fg" },
  SKIPPED: { label: "Skipped", fill: "bg-gv-draft text-gv-draft-fg" },
  FAILED: { label: "Failed", fill: "bg-gv-held text-gv-held-fg" },
} as const;

/** Turn the stored config into the sentence the rule actually means. */
export function describeRule(automation: Automation): string {
  const config = automation.trigger_config || {};

  const when =
    automation.trigger_type === "TOOL_DENIED"
      ? `${config.count ?? 1} denied tool call${(config.count ?? 1) === 1 ? "" : "s"} within ${config.window_minutes ?? 60} minutes`
      : automation.trigger_type === "SPEND_THRESHOLD"
        ? `spend reaches ${config.percent_of_cap ?? 80}% of the agent's cap`
        : "an agent is suspended by a person";

  const then =
    automation.action_type === "SUSPEND_AGENT" ? "suspend the agent" : "raise an alert";

  return `When ${when}, ${then}.`;
}

function timeOf(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString([], {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function AutomationBoard() {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const still = useReducedMotion();

  const load = useCallback(async () => {
    try {
      const [rules, history] = await Promise.all([
        fetchApi("/automations/"),
        fetchApi("/automation-runs/?limit=50"),
      ]);
      setAutomations(Array.isArray(rules) ? rules : []);
      setRuns(Array.isArray(history) ? history : []);
    } catch (err: any) {
      setError(err.message || "Could not load automations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (automation: Automation) => {
    const next = !automation.enabled;
    setPending(automation.id);
    setActionError(null);

    setAutomations((current) =>
      current.map((a) => (a.id === automation.id ? { ...a, enabled: next } : a)),
    );

    try {
      await fetchApi(`/automations/${automation.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: next }),
      });
    } catch (err: any) {
      // Put it back — the rule did not actually change.
      setAutomations((current) =>
        current.map((a) =>
          a.id === automation.id ? { ...a, enabled: automation.enabled } : a,
        ),
      );
      setActionError(err.message || "That rule could not be changed.");
    } finally {
      setPending(null);
    }
  };

  const enabledCount = automations.filter((a) => a.enabled).length;
  const firedCount = runs.filter((r) => r.outcome === "FIRED").length;

  return (
    <>
      <ViewTabs views={[{ name: "Rules", icon: "compliance" }]} active="Rules" />

      <BoardPanel
        toolbar={
          <>
            <ToolbarChip>
              {enabledCount} of {automations.length} rules on
            </ToolbarChip>
            <ToolbarChip active={firedCount > 0}>{firedCount} fired</ToolbarChip>
          </>
        }
      >
        {error && (
          <div role="alert" className="px-4 py-6 text-[13px] font-extrabold text-gv-held">
            {error}
          </div>
        )}

        {actionError && (
          <div
            role="alert"
            className="m-4 rounded-lg border-2 border-gv-held bg-gv-held/10 p-3 text-[13px] font-extrabold text-gv-held-fg"
          >
            {actionError}
          </div>
        )}

        {!error && loading && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">Loading automations…</p>
        )}

        {!error && !loading && (
          <>
            <div className="flex items-center gap-3 px-4 pt-4">
              <h2 className="text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
                Rules
              </h2>
              <div className="ml-auto">
                <CreateAutomationButton onCreated={load} />
              </div>
            </div>

            {automations.length === 0 ? (
              <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">
                No automations yet. A rule watches for something the platform already
                records — a denied tool call, spend against a cap, a suspension — and acts on it.
              </p>
            ) : (
              <motion.div
                className="flex flex-col gap-3 p-4"
                variants={staggerContainer}
                initial={still ? false : "hidden"}
                animate="shown"
              >
                {automations.map((automation) => {
                  const trigger = TRIGGERS[automation.trigger_type];
                  const action = ACTIONS[automation.action_type];

                  return (
                    <motion.section
                      key={automation.id}
                      variants={staggerItem}
                      className={`gv-card overflow-hidden rounded-lg border-2 border-border bg-gv-row ${
                        automation.enabled ? "" : "opacity-70"
                      }`}
                    >
                      <header className="flex min-h-12 items-center gap-3 border-b-2 border-border px-4 py-2">
                        <div className="min-w-0 flex-1">
                          <h3 className="truncate font-display text-[19px] leading-none text-gv-ink">
                            {automation.name}
                          </h3>
                          <p className="mt-1.5 text-[12.5px] font-semibold text-gv-body">
                            {describeRule(automation)}
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() => pending !== automation.id && toggle(automation)}
                          disabled={pending === automation.id}
                          aria-pressed={automation.enabled}
                          aria-label={`${automation.enabled ? "Disable" : "Enable"} ${automation.name}`}
                          className={`inline-flex h-8 shrink-0 items-center gap-1.5 rounded-xl border-2 border-border px-3 text-[12px] font-extrabold uppercase tracking-[0.06em] transition-transform active:translate-x-px active:translate-y-px disabled:opacity-60 ${
                            automation.enabled
                              ? "gv-chip bg-gv-cleared text-gv-cleared-fg"
                              : "bg-gv-draft text-gv-draft-fg"
                          }`}
                        >
                          {automation.enabled ? (
                            <ShieldCheck className="h-3.5 w-3.5" strokeWidth={2.6} />
                          ) : (
                            <ShieldOff className="h-3.5 w-3.5" strokeWidth={2.6} />
                          )}
                          {automation.enabled ? "On" : "Off"}
                        </button>
                      </header>

                      <div className="flex flex-wrap items-center gap-2 px-4 py-2.5">
                        <span className="inline-flex h-[22px] items-center gap-1 rounded border border-border bg-gv-head px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] text-gv-label">
                          <trigger.Icon className="h-3 w-3" strokeWidth={2.6} aria-hidden="true" />
                          {trigger.label}
                        </span>
                        <span className="font-mono text-[11px] text-gv-muted">→</span>
                        <span
                          className={`inline-flex h-[22px] items-center gap-1 rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${action.tone}`}
                        >
                          <action.Icon className="h-3 w-3" strokeWidth={2.6} aria-hidden="true" />
                          {action.label}
                        </span>
                        <span className="ml-auto font-mono text-[11px] text-gv-muted">
                          {automation.agent_id ? "one agent" : "every agent"}
                        </span>
                      </div>
                    </motion.section>
                  );
                })}
              </motion.div>
            )}

            <section className="mx-4 mb-4 overflow-hidden rounded-lg border-2 border-border bg-gv-row">
              <header className="flex h-[38px] items-center gap-2 border-b-2 border-border bg-gv-head px-4">
                <h3 className="text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
                  What these rules have done
                </h3>
                <span className="ml-auto font-mono text-[10.5px] text-gv-muted">
                  skipped runs shown too
                </span>
              </header>

              {runs.length === 0 ? (
                <p className="flex items-center gap-2 px-4 py-6 text-[13px] font-bold text-gv-muted">
                  <CircleSlash className="h-4 w-4" strokeWidth={2.2} aria-hidden="true" />
                  Nothing evaluated yet.
                </p>
              ) : (
                <ul className="divide-y divide-gv-rule/40">
                  {runs.map((run) => {
                    const outcome = OUTCOMES[run.outcome] ?? OUTCOMES.SKIPPED;
                    return (
                      <li
                        key={run.id}
                        className="flex min-h-[38px] items-center gap-3 px-4 py-1.5"
                      >
                        <span className="w-[104px] shrink-0 font-mono text-[11px] text-gv-muted">
                          {timeOf(run.triggered_at)}
                        </span>
                        <span
                          className={`inline-flex h-[22px] shrink-0 items-center rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${outcome.fill}`}
                        >
                          {outcome.label}
                        </span>
                        <span className="min-w-0 flex-1 text-[12.5px] font-semibold text-foreground">
                          {run.detail}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </>
        )}
      </BoardPanel>
    </>
  );
}
