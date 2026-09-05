"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api-client";
import { useExecutionStream, type RunEntry } from "@/hooks/use-execution-stream";
import { motion, useReducedMotion, DURATION, EASE, Reveal } from "@/components/motion";
import { PageHeader } from "@/components/board/page-header";
import { BoardPanel, ViewTabs, ToolbarChip, LiveMarker } from "@/components/board/board-panel";
import {
  ArrowLeft,
  ShieldAlert,
  ShieldCheck,
  Coins,
  OctagonX,
  CircleCheck,
  CircleAlert,
} from "lucide-react";

/**
 * The live run viewer — the screen the three demo moments happen on.
 *
 *   1. a tool call BLOCKED   a denied entry appears in the timeline, filled
 *                            red, carrying the policy's own reason
 *   2. budget AUTO-PAUSE     the denial whose reason is the budget cap, after
 *                            which the guard suspends the agent
 *   3. the KILL SWITCH       "Stop this run" posts /executions/{id}/cancel and
 *                            the stream closes on its next heartbeat
 *
 * Until this existed the backend could only be demonstrated from a terminal.
 *
 * Everything below the header is driven by the stream, not by polling. The
 * running spend and denial count are totals over the frames this connection
 * has seen — this run's spend, not the organisation's.
 */

const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED", "TERMINATED"];

function statusSkin(status: string) {
  if (status === "COMPLETED") return "bg-gv-cleared text-gv-cleared-fg";
  if (status === "FAILED") return "bg-gv-held text-gv-held-fg";
  if (status === "CANCELLED" || status === "TERMINATED") return "bg-gv-held text-gv-held-fg";
  if (status === "RUNNING") return "bg-gv-watch text-gv-watch-fg";
  return "bg-gv-draft text-gv-draft-fg";
}

function timeOf(iso?: string) {
  if (!iso) return "--:--:--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--:--:--";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function RunViewer({ executionId }: { executionId: string }) {
  const run = useExecutionStream(executionId);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [settled, setSettled] = useState<{ status: string; result?: string | null; error?: string | null } | null>(null);
  const [killing, setKilling] = useState(false);
  const [killError, setKillError] = useState<string | null>(null);

  // The stream carries the goal but not the agent, and a run should link back
  // to the agent it belongs to.
  //
  // This also settles a run that was already over before the page opened. The
  // stream sends its `status` frame immediately but only sends `done` — which
  // carries the result and the error — on its next heartbeat, up to ten
  // seconds later. Without this the viewer sat blank for those ten seconds
  // with no result and no error for a run that had long since finished.
  useEffect(() => {
    let cancelled = false;
    fetchApi(`/executions/${executionId}`)
      .then((data) => {
        if (cancelled) return;
        setAgentId(data?.agent_id ?? null);
        if (data?.status && TERMINAL.includes(data.status)) {
          setSettled({ status: data.status, result: data.result, error: data.error });
        }
      })
      .catch(() => {
        /* the stream is the primary source; a missing back-link is not fatal */
      });
    return () => {
      cancelled = true;
    };
  }, [executionId]);

  const live = !run.finished && !settled && !TERMINAL.includes(run.status);
  const reconnecting = run.reconnecting;

  // The stream wins once it has spoken; `settled` only fills the gap before it.
  const status = run.finished ? run.status : (settled?.status ?? run.status);
  const result = run.result ?? settled?.result;
  const error = run.error ?? settled?.error;
  const finished = run.finished || settled !== null;

  const handleKill = async () => {
    if (killing) return;
    setKilling(true);
    setKillError(null);
    try {
      await fetchApi(`/executions/${executionId}/cancel`, { method: "POST" });
      // The stream sees the terminal status on its next heartbeat and closes
      // itself, so nothing is forced here.
    } catch (err: any) {
      setKillError(err.message || "Could not stop the run");
    } finally {
      setKilling(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Run"
        subtitle={run.goal || "Watching this run as it happens"}
        actions={
          <>
            <Link
              href={agentId ? `/agents/${agentId}` : "/runs"}
              className="gv-chip inline-flex h-10 items-center gap-2 rounded-xl border-2 border-border bg-card px-[15px] text-[13px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px"
            >
              <ArrowLeft className="h-4 w-4" strokeWidth={2.6} />
              {agentId ? "Agent" : "Runs"}
            </Link>

            {live && (
              <button
                type="button"
                onClick={handleKill}
                disabled={killing}
                className="gv-card inline-flex h-10 items-center gap-2 rounded-xl border-2 border-border bg-gv-held px-[17px] text-[13.5px] font-extrabold text-gv-held-fg transition-transform active:translate-x-px active:translate-y-px disabled:opacity-60"
              >
                <OctagonX className="h-4 w-4" strokeWidth={2.6} />
                {killing ? "Stopping…" : "Stop this run"}
              </button>
            )}
          </>
        }
      />

      <ViewTabs views={[{ name: "Timeline", icon: "timeline" }]} active="Timeline" />

      <BoardPanel
        toolbar={
          <>
            <span
              className={`inline-flex h-8 shrink-0 items-center rounded-xl border-2 border-border px-3 text-[12px] font-extrabold uppercase tracking-[0.06em] ${statusSkin(
                status,
              )}`}
            >
              {status}
            </span>

            <ToolbarChip icon="filter" active={run.deniedCount > 0}>
              {run.deniedCount} denied
            </ToolbarChip>

            <ToolbarChip>${run.spendUsd.toFixed(4)} this run</ToolbarChip>

            {/* A dropped connection must not look like a finished run — the
                marker says which of the three it is. */}
            <LiveMarker
              live={live && !reconnecting}
              label={
                reconnecting
                  ? `Reconnecting · attempt ${reconnecting.attempt} of ${reconnecting.maxAttempts}`
                  : live
                    ? "Live · streaming"
                    : "Stream closed"
              }
            />
          </>
        }
      >
        {killError && (
          <div
            role="alert"
            className="m-4 rounded-lg border-2 border-gv-held bg-gv-held/10 p-3 text-[13px] font-extrabold text-gv-held-fg"
          >
            {killError}
          </div>
        )}

        {reconnecting && (
          <div
            role="status"
            className="m-4 rounded-lg border-2 border-gv-watch bg-gv-watch/20 p-3 text-[13px] font-extrabold text-gv-watch-fg"
          >
            Lost the live connection. Reconnecting — attempt {reconnecting.attempt} of{" "}
            {reconnecting.maxAttempts}. Events recorded while disconnected are still in the
            audit log.
          </div>
        )}

        {run.connectionError && (
          <div
            role="alert"
            className="m-4 rounded-lg border-2 border-gv-held bg-gv-held/10 p-3 text-[13px] font-extrabold text-gv-held-fg"
          >
            {run.connectionError}
          </div>
        )}

        {/* aria-live so a screen reader hears each decision as it lands */}
        <ul aria-live="polite" className="divide-y divide-gv-rule/40">
          {run.entries.map((entry) => (
            <TimelineRow key={entry.key} entry={entry} />
          ))}
        </ul>

        {run.entries.length === 0 && !run.connectionError && (
          <p className="px-4 py-8 text-[13px] font-bold text-gv-muted">
            {live
              ? "Connected. Waiting for the first tool call…"
              : "This run produced no governance events."}
          </p>
        )}

        {finished && (result || error) && (
          <Reveal className="m-4">
          <section className="overflow-hidden rounded-lg border-2 border-border bg-gv-row">
            <header className="flex h-[38px] items-center gap-2 border-b-2 border-border bg-gv-head px-4">
              {error ? (
                <CircleAlert className="h-4 w-4 text-gv-held" strokeWidth={2.6} />
              ) : (
                <CircleCheck className="h-4 w-4 text-gv-cleared" strokeWidth={2.6} />
              )}
              <h3 className="text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
                {error ? "Run failed" : "Result"}
              </h3>
            </header>
            <p className="whitespace-pre-wrap p-4 text-[13px] font-semibold text-gv-body">
              {error || result}
            </p>
          </section>
          </Reveal>
        )}
      </BoardPanel>
    </>
  );
}

/**
 * One event as it lands.
 *
 * The row slides in from the left, the way a log line arrives — 8px, once,
 * fast. A denial additionally flashes: it is the single most important thing
 * that can happen on this screen, and in a live demo it has to be impossible
 * to miss the moment the gate refuses a call. The flash is a separate overlay
 * that fades to nothing, so the row's resting colour is still plain CSS and
 * nothing depends on an animation having finished.
 */
function TimelineRow({ entry }: { entry: RunEntry }) {
  const still = useReducedMotion();
  const denied = entry.kind === "denied";

  const skin =
    entry.kind === "denied"
      ? { fill: "bg-gv-held text-gv-held-fg", label: "Denied", Icon: ShieldAlert }
      : entry.kind === "allowed"
        ? { fill: "bg-gv-cleared text-gv-cleared-fg", label: "Allowed", Icon: ShieldCheck }
        : { fill: "bg-gv-draft text-gv-draft-fg", label: "Cost", Icon: Coins };

  return (
    <motion.li
      initial={still ? false : { opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: DURATION.base, ease: EASE }}
      className={`relative flex min-h-[38px] items-center gap-3 px-4 py-1 ${
        denied ? "bg-gv-held/10" : ""
      }`}
    >
      {denied && !still && (
        <motion.span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-gv-held"
          initial={{ opacity: 0.32 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        />
      )}

      <span className="relative w-[68px] shrink-0 font-mono text-[11px] text-gv-muted">
        {timeOf(entry.at)}
      </span>

      <span
        className={`relative inline-flex h-[22px] shrink-0 items-center gap-1 rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${skin.fill}`}
      >
        <skin.Icon className="h-3 w-3" strokeWidth={2.6} aria-hidden="true" />
        {skin.label}
      </span>

      <span className="relative min-w-0 flex-1 text-[12.5px] font-bold text-foreground">
        {entry.kind === "cost" ? (
          <span className="font-mono text-[12px] text-gv-muted">
            ${(entry.costUsd ?? 0).toFixed(6)} · {entry.tokens ?? 0} tokens
          </span>
        ) : (
          <>
            <span className="font-mono text-[12px]">{entry.tool}</span>
            {entry.reason && <span className="text-gv-muted"> — {entry.reason}</span>}
          </>
        )}
      </span>
    </motion.li>
  );
}
