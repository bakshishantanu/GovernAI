"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldX,
  DollarSign,
  Loader2,
  OctagonX,
  CheckCircle2,
  XCircle,
  FileText,
  Wrench,
  ShieldAlert,
  MessageSquare,
  Paperclip,
  Check,
} from "lucide-react";
import { API_BASE, getAuthHeader, fetchApi } from "@/lib/api-client";
import { readSseBody } from "@/lib/sse-client";
import { useRoleBase } from "@/lib/use-role-base";
import type { Execution } from "@/lib/types";
import { money } from "../../../../_components/agent-types";

type LiveStatus = "connecting" | "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED" | "TERMINATED";

type TimelineEvent =
  | { id: string; kind: "allowed" | "denied"; tool: string; reason: string; at: string }
  | { id: string; kind: "cost"; cost_usd: number; tokens: number; model?: string | null; at: string };

/**
 * Every real execution status this run can be in, mapped to which of the
 * three pipeline stages is current. There is no per-run "Compliance Check"
 * stage in this architecture -- an agent's compliance is checked once, at
 * build/approval time, not on every run -- so the honest per-run lifecycle
 * this backend actually has is Request -> Agent Reasoning (every governed
 * tool call and LLM call happens here) -> a terminal stage. Inventing extra
 * named stages (Data Retrieval, Validate Output, ...) this codebase has no
 * timestamps for would mean fabricating durations; this doesn't.
 */
function pipelineStageIndex(status: LiveStatus): 0 | 1 | 2 {
  if (status === "connecting" || status === "PENDING") return 0;
  if (status === "RUNNING") return 1;
  return 2;
}

function terminalLabel(status: LiveStatus): string {
  switch (status) {
    case "COMPLETED":
      return "Completed";
    case "FAILED":
      return "Failed";
    case "CANCELLED":
      return "Cancelled";
    case "TERMINATED":
      return "Terminated";
    default:
      return "Finishing";
  }
}

type Tab = "logs" | "calls" | "governance" | "output" | "artifacts";

const TABS: { id: Tab; label: string; icon: typeof FileText }[] = [
  { id: "logs", label: "Logs", icon: FileText },
  { id: "calls", label: "Tool Calls", icon: Wrench },
  { id: "governance", label: "Governance", icon: ShieldAlert },
  { id: "output", label: "Agent Output", icon: MessageSquare },
  { id: "artifacts", label: "Artifacts", icon: Paperclip },
];

/**
 * The run detail view — a Jenkins-style pipeline over one execution: which
 * stage it's in, every governed tool call and LLM call (live as they happen,
 * and reconstructed from history for a run opened after the fact), the
 * governance decision behind each one, and the run's real cost/tokens.
 *
 * Two data sources feed the same `events` timeline: `GET
 * /executions/{id}/timeline` for everything that already happened (fetched
 * once, on mount — this is what makes a *past* run show its real history
 * instead of nothing, which was the whole reason this component needed to
 * change), and `GET /executions/{id}/stream` for everything that happens
 * from the moment this page is open (unchanged from before — `fetch` +
 * `ReadableStream` rather than `EventSource`, because EventSource cannot
 * carry the Authorization header this endpoint requires, D-024). Events are
 * de-duplicated by id so a run opened mid-flight never shows a tool call
 * twice.
 */
export function ExecutionStream({ agentId, executionId }: { agentId: string; executionId: string }) {
  const base = useRoleBase();
  const [status, setStatus] = useState<LiveStatus>("connecting");
  const [goal, setGoal] = useState("");
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [result, setResult] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [run, setRun] = useState<Execution | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [tab, setTab] = useState<Tab>("logs");
  const abortRef = useRef<AbortController | null>(null);
  const seenIds = useRef<Set<string>>(new Set());

  // History first: everything that already happened, fetched once. Runs
  // before the live stream opens so a finished run's real past isn't
  // momentarily empty, and so live events (below) can de-dupe against it.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [detail, timeline] = await Promise.all([
          fetchApi(`/executions/${executionId}`) as Promise<Execution>,
          fetchApi(`/executions/${executionId}/timeline`) as Promise<{
            governance_events: {
              id: string;
              tool: string | null;
              policy_decision: string;
              reason: string | null;
              timestamp: string;
            }[];
            cost_events: {
              id: string;
              cost_usd: number;
              total_tokens: number | null;
              model: string | null;
              timestamp: string;
            }[];
          }>,
        ]);
        if (cancelled) return;

        setRun(detail);
        setGoal((g) => g || detail.goal);

        const fromHistory: TimelineEvent[] = [
          ...timeline.governance_events
            .filter((e) => e.tool)
            .map((e): TimelineEvent => ({
              id: e.id,
              kind: e.policy_decision === "ALLOW" || e.policy_decision === "ALLOWED" ? "allowed" : "denied",
              tool: e.tool as string,
              reason: e.reason ?? "",
              at: e.timestamp,
            })),
          ...timeline.cost_events.map(
            (e): TimelineEvent => ({
              id: e.id,
              kind: "cost",
              cost_usd: e.cost_usd,
              tokens: e.total_tokens ?? 0,
              model: e.model,
              at: e.timestamp,
            }),
          ),
        ].sort((a, b) => +new Date(a.at) - +new Date(b.at));

        for (const e of fromHistory) seenIds.current.add(e.id);
        setEvents(fromHistory);
      } catch {
        // A run that vanished, or a genuine network failure: the live
        // stream below still has its own independent failure handling, and
        // an empty history is a real, renderable state (see the "No tool
        // calls" / "No logs" empty states), not an error to surface twice.
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [executionId]);

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    let cancelled = false;

    async function connect() {
      const auth = await getAuthHeader();
      const res = await fetch(`${API_BASE}/executions/${executionId}/stream`, {
        headers: { Authorization: auth },
        signal: controller.signal,
      });
      if (!res.body) return;

      await readSseBody(
        res.body,
        (parsed) => {
          const { event, data } = parsed as { event: string; data: any };

          if (event === "status") {
            setGoal((g) => g || data.goal || "");
            setStatus(data.status);
          } else if (event === "audit.tool.allowed" || event === "audit.tool.denied") {
            if (seenIds.current.has(data.id)) return;
            seenIds.current.add(data.id);
            setEvents((prev) => [
              ...prev,
              {
                id: data.id,
                kind: event === "audit.tool.allowed" ? "allowed" : "denied",
                tool: data.tool,
                reason: data.reason ?? "",
                at: data.at,
              },
            ]);
          } else if (event === "cost.llm.incurred") {
            if (seenIds.current.has(data.id)) return;
            seenIds.current.add(data.id);
            setEvents((prev) => [
              ...prev,
              { id: data.id, kind: "cost", cost_usd: data.cost_usd, tokens: data.tokens, at: data.at },
            ]);
          } else if (event === "done") {
            setStatus(data.status);
            setResult(data.result ?? null);
            setRunError(data.error ?? null);
          }
        },
        controller.signal,
      );
    }

    connect().catch(() => {
      if (!cancelled) setStatus((s) => (s === "connecting" ? "FAILED" : s));
    });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [executionId]);

  async function stopRun() {
    setCancelling(true);
    try {
      await fetchApi(`/executions/${executionId}/cancel`, { method: "POST" });
    } catch {
      // the stream's own "done" frame is the source of truth either way
    } finally {
      setCancelling(false);
    }
  }

  const live = status === "PENDING" || status === "RUNNING" || status === "connecting";
  const toolCalls = events.filter((e) => e.kind !== "cost") as Extract<
    TimelineEvent,
    { kind: "allowed" | "denied" }
  >[];
  const llmCalls = events.filter((e) => e.kind === "cost") as Extract<TimelineEvent, { kind: "cost" }>[];
  const denials = toolCalls.filter((e) => e.kind === "denied").length;
  const liveCost = llmCalls.reduce((sum, e) => sum + e.cost_usd, 0);
  const liveTokens = llmCalls.reduce((sum, e) => sum + e.tokens, 0);
  // Prefer the backend's own totals once loaded (the source of truth, and
  // correct even for a run whose live stream was never open for its whole
  // duration); fall back to what's been observed live until then.
  const totalCost = run?.total_cost_usd ?? liveCost;
  const totalTokens = run?.total_tokens ?? liveTokens;

  const duration =
    run?.started_at && (run?.completed_at || !live)
      ? formatDuration(
          +new Date(run.completed_at ?? Date.now()) - +new Date(run.started_at),
        )
      : null;

  const stageIndex = pipelineStageIndex(status);

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link
        href={`${base}/agents/${agentId}`}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to the passport
      </Link>

      <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-6 shadow-[0_6px_0_0_rgba(22,19,14,0.14)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--l-charcoal)]/45">
              Execution · {executionId.slice(0, 8)}
              {run?.triggered_by_id && (
                <> · triggered by {run.triggered_by_id.slice(0, 8)}</>
              )}
            </span>
            <h1 className="landing-display mt-1 text-xl text-[var(--l-ink)]">{goal || "Loading goal…"}</h1>
          </div>
          <StatusBadge status={status} />
        </div>

        <PipelineStrip stageIndex={stageIndex} status={status} denials={denials} />

        {live && (
          <motion.button
            onClick={stopRun}
            disabled={cancelling}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="mt-4 flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_rgba(22,19,14,0.2)] disabled:opacity-50"
            style={{ background: "var(--l-orange-deep)" }}
          >
            <OctagonX className="h-4 w-4" />
            {cancelling ? "Stopping…" : "Kill switch — stop this run"}
          </motion.button>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <StatTile label="Duration" value={duration ?? "—"} />
        <StatTile label="Tool calls" value={String(toolCalls.length)} />
        <StatTile label="LLM calls" value={String(llmCalls.length)} />
        <StatTile label="Governance checks" value={String(toolCalls.length)} />
        <StatTile label="Blocked" value={String(denials)} tone={denials > 0 ? "danger" : undefined} />
        <StatTile label="Tokens" value={String(totalTokens)} />
        <StatTile label="Cost" value={money(totalCost)} />
      </div>

      <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_4px_0_0_rgba(22,19,14,0.12)]">
        <div className="flex flex-wrap gap-1.5 border-b-2 border-dashed border-[var(--l-ink)]/10 pb-3">
          {TABS.map((t) => {
            const TIcon = t.icon;
            const on = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12.5px] font-semibold transition-colors"
                style={{
                  background: on ? "var(--l-ink)" : "transparent",
                  color: on ? "var(--l-cream)" : "var(--l-charcoal)",
                }}
              >
                <TIcon className="h-3.5 w-3.5" />
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="mt-4">
          {!historyLoaded && events.length === 0 ? (
            <div className="space-y-1.5">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-10 animate-pulse rounded-xl bg-[var(--l-line)]/50" />
              ))}
            </div>
          ) : tab === "logs" ? (
            <LogsTab events={events} live={live} />
          ) : tab === "calls" ? (
            <ToolCallsTab calls={toolCalls} live={live} />
          ) : tab === "governance" ? (
            <GovernanceTab calls={toolCalls} live={live} />
          ) : tab === "output" ? (
            <OutputTab status={status} result={result ?? run?.result ?? null} error={runError ?? run?.error ?? null} live={live} />
          ) : (
            <ArtifactsTab />
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Request Received -> Agent Reasoning -> a terminal stage, matching the
 * three real states this backend's executions actually pass through (see
 * `pipelineStageIndex` above for why there is no fourth "Compliance Check"
 * stage). Visual language matches `LifecycleTrack` (the agent passport's own
 * stage strip) on purpose, for consistency across the two places this app
 * shows a "how far along is this" track.
 */
function PipelineStrip({
  stageIndex,
  status,
  denials,
}: {
  stageIndex: 0 | 1 | 2;
  status: LiveStatus;
  denials: number;
}) {
  const failed = status === "FAILED" || status === "CANCELLED" || status === "TERMINATED";
  const stages = [
    { label: "Request Received" },
    { label: "Agent Reasoning" },
    { label: stageIndex === 2 ? terminalLabel(status) : "…" },
  ];

  return (
    <div className="mt-4 flex flex-wrap items-center gap-1">
      {stages.map((s, i) => {
        const done = i < stageIndex || (i === stageIndex && i === 2);
        const isCurrent = i === stageIndex && i < 2;
        const stageFailed = i === 2 && failed && stageIndex === 2;
        return (
          <div key={s.label} className="flex items-center">
            <motion.div
              initial={false}
              animate={{ scale: isCurrent ? 1.04 : 1 }}
              className="flex items-center gap-1.5 rounded-full px-3 py-1.5"
              style={{
                background: stageFailed
                  ? "color-mix(in srgb, var(--l-orange-deep) 14%, var(--l-cream))"
                  : done
                    ? "var(--l-teal)"
                    : isCurrent
                      ? "var(--l-yellow-pale)"
                      : "transparent",
                border: done || isCurrent || stageFailed ? "none" : "2px dashed var(--l-charcoal)",
              }}
            >
              {stageFailed ? (
                <XCircle className="h-3.5 w-3.5" style={{ color: "var(--l-orange-deep)" }} />
              ) : done ? (
                <Check className="h-3.5 w-3.5" style={{ color: "#ffffff" }} />
              ) : isCurrent ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" style={{ color: "var(--l-yellow-deep)" }} />
              ) : null}
              <span
                className="landing-display text-[11px] uppercase tracking-wide"
                style={{
                  color: stageFailed
                    ? "var(--l-orange-deep)"
                    : done
                      ? "#ffffff"
                      : isCurrent
                        ? "var(--l-yellow-deep)"
                        : "var(--l-charcoal)",
                }}
              >
                {s.label}
              </span>
            </motion.div>
            {i < stages.length - 1 && (
              <span
                className="mx-1.5 h-[2px] w-6"
                style={{ background: i < stageIndex ? "var(--l-teal)" : "var(--l-line)" }}
              />
            )}
          </div>
        );
      })}
      {denials > 0 && (
        <span
          className="ml-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10.5px] font-semibold"
          style={{
            background: "color-mix(in srgb, var(--l-orange-deep) 12%, transparent)",
            color: "var(--l-orange-deep)",
          }}
        >
          <ShieldX className="h-3 w-3" />
          governance blocked {denials} action{denials > 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: LiveStatus }) {
  const live = status === "PENDING" || status === "RUNNING" || status === "connecting";
  return (
    <span
      className="flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 font-mono text-[10.5px] font-semibold uppercase tracking-wide"
      style={{
        background: live ? "var(--l-orange)" : status === "COMPLETED" ? "var(--l-teal)" : "#201d1a",
        color: "#ffffff",
      }}
    >
      {live && (
        <motion.span
          className="h-1.5 w-1.5 rounded-full bg-white"
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.2, repeat: Infinity }}
        />
      )}
      {status === "connecting" ? "connecting" : status.toLowerCase()}
    </span>
  );
}

function StatTile({ label, value, tone }: { label: string; value: string; tone?: "danger" }) {
  return (
    <div className="flex-1 min-w-[110px] rounded-xl border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-4 py-2.5">
      <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--l-charcoal)]/45">{label}</p>
      <p
        className="landing-display mt-0.5 text-lg"
        style={{ color: tone === "danger" ? "var(--l-orange-deep)" : "var(--l-ink)" }}
      >
        {value}
      </p>
    </div>
  );
}

function EmptyTab({ live, waiting, idle }: { live: boolean; waiting: string; idle: string }) {
  return (
    <p className="py-6 text-center text-[12.5px] text-[var(--l-charcoal)]/50">{live ? waiting : idle}</p>
  );
}

function TimelineRow({ event }: { event: TimelineEvent }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="flex items-center gap-3 rounded-xl px-3 py-2.5"
      style={{
        background:
          event.kind === "denied" ? "color-mix(in srgb, var(--l-orange-deep) 8%, transparent)" : "transparent",
      }}
    >
      {event.kind === "allowed" && <ShieldCheck className="h-4 w-4 shrink-0" style={{ color: "var(--l-teal)" }} />}
      {event.kind === "denied" && (
        <motion.span
          initial={{ rotate: 0 }}
          animate={{ rotate: [0, -8, 8, -4, 0] }}
          transition={{ duration: 0.4 }}
        >
          <ShieldX className="h-4 w-4 shrink-0" style={{ color: "var(--l-orange-deep)" }} />
        </motion.span>
      )}
      {event.kind === "cost" && <DollarSign className="h-4 w-4 shrink-0" style={{ color: "var(--l-charcoal)" }} />}

      {event.kind === "cost" ? (
        <span className="flex-1 font-mono text-[12.5px] text-[var(--l-charcoal)]/70">
          {money(event.cost_usd)} · {event.tokens} tokens{event.model ? ` · ${event.model}` : ""}
        </span>
      ) : (
        <span className="min-w-0 flex-1">
          <span className="block font-mono text-[12.5px] text-[var(--l-ink)]">{event.tool}</span>
          {event.reason && (
            <span className="block truncate text-[11px] text-[var(--l-charcoal)]/55">{event.reason}</span>
          )}
        </span>
      )}
      <span className="shrink-0 font-mono text-[10px] text-[var(--l-charcoal)]/35">
        {new Date(event.at).toLocaleTimeString()}
      </span>
    </motion.div>
  );
}

/** Every event, in order, as a chronological log feed — the closest this
 * architecture has to structured logs, since there is no separate log table
 * (each line *is* a real governance or cost event, not a synthesized string
 * pretending to be one). */
function LogsTab({ events, live }: { events: TimelineEvent[]; live: boolean }) {
  if (events.length === 0) {
    return <EmptyTab live={live} waiting="Waiting for the first event…" idle="No logs were recorded for this run." />;
  }
  return (
    <div className="space-y-1">
      <AnimatePresence initial={false}>
        {events.map((e) => {
          const time = new Date(e.at).toLocaleTimeString();
          const message =
            e.kind === "cost"
              ? `LLM call completed — ${money(e.cost_usd)}, ${e.tokens} tokens${e.model ? ` (${e.model})` : ""}`
              : e.kind === "allowed"
                ? `${e.tool} — ALLOWED${e.reason ? `: ${e.reason}` : ""}`
                : `${e.tool} — DENIED${e.reason ? `: ${e.reason}` : ""}`;
          return (
            <motion.div
              key={e.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-start gap-3 rounded-lg px-2 py-1 font-mono text-[11.5px]"
            >
              <span className="shrink-0 text-[var(--l-charcoal)]/40">{time}</span>
              <span
                style={{
                  color: e.kind === "denied" ? "var(--l-orange-deep)" : "var(--l-charcoal)",
                }}
              >
                {message}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>
      {live && (
        <div className="flex items-center gap-2 px-2 py-2 text-[12px] text-[var(--l-charcoal)]/45">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          watching…
        </div>
      )}
    </div>
  );
}

function ToolCallsTab({
  calls,
  live,
}: {
  calls: Extract<TimelineEvent, { kind: "allowed" | "denied" }>[];
  live: boolean;
}) {
  if (calls.length === 0) {
    return <EmptyTab live={live} waiting="Waiting for the first tool call…" idle="The agent completed without calling any tools." />;
  }
  return (
    <div className="space-y-1.5">
      <AnimatePresence initial={false}>
        {calls.map((e) => (
          <TimelineRow key={e.id} event={e} />
        ))}
      </AnimatePresence>
    </div>
  );
}

/** Same underlying audit events as Tool Calls, framed as governance
 * decisions rather than call attempts — each event already carries the
 * policy name inside its `reason` (the engine writes "Policy 'X': ...";
 * see backend/app/domain/policies/engine.py), so nothing here is invented. */
function GovernanceTab({
  calls,
  live,
}: {
  calls: Extract<TimelineEvent, { kind: "allowed" | "denied" }>[];
  live: boolean;
}) {
  if (calls.length === 0) {
    return <EmptyTab live={live} waiting="Waiting for the first governance check…" idle="No governance checks were recorded for this run." />;
  }
  return (
    <div className="space-y-2">
      {calls.map((e) => (
        <div
          key={e.id}
          className="rounded-xl border-2 p-3"
          style={{
            borderColor: e.kind === "denied" ? "var(--l-orange-deep)" : "var(--l-teal)",
            background:
              e.kind === "denied"
                ? "color-mix(in srgb, var(--l-orange-deep) 6%, var(--l-cream))"
                : "color-mix(in srgb, var(--l-teal) 6%, var(--l-cream))",
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-[12.5px] font-semibold text-[var(--l-ink)]">{e.tool}</span>
            <span
              className="rounded-full px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide"
              style={{
                background: e.kind === "denied" ? "var(--l-orange-deep)" : "var(--l-teal)",
                color: "#ffffff",
              }}
            >
              {e.kind === "denied" ? "Blocked" : "Allowed"}
            </span>
          </div>
          {e.reason && <p className="mt-1 text-[12px] leading-snug text-[var(--l-charcoal)]/70">{e.reason}</p>}
          <p className="mt-1.5 font-mono text-[10px] text-[var(--l-charcoal)]/40">
            {new Date(e.at).toLocaleString()}
          </p>
        </div>
      ))}
      {live && (
        <div className="flex items-center gap-2 px-2 py-2 text-[12px] text-[var(--l-charcoal)]/45">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          watching…
        </div>
      )}
    </div>
  );
}

function OutputTab({
  status,
  result,
  error,
  live,
}: {
  status: LiveStatus;
  result: string | null;
  error: string | null;
  live: boolean;
}) {
  if (live) {
    return <EmptyTab live waiting="The run is still going — output appears once it finishes." idle="" />;
  }
  return (
    <div
      className="rounded-2xl border-2 p-5"
      style={{
        borderColor: status === "COMPLETED" ? "var(--l-teal)" : "var(--l-orange-deep)",
        background:
          status === "COMPLETED"
            ? "color-mix(in srgb, var(--l-teal) 8%, var(--l-cream))"
            : "color-mix(in srgb, var(--l-orange-deep) 8%, var(--l-cream))",
      }}
    >
      <div className="flex items-center gap-2">
        {status === "COMPLETED" ? (
          <CheckCircle2 className="h-5 w-5" style={{ color: "var(--l-teal)" }} />
        ) : (
          <XCircle className="h-5 w-5" style={{ color: "var(--l-orange-deep)" }} />
        )}
        <h2 className="landing-display text-base text-[var(--l-ink)]">
          {status === "COMPLETED" ? "Run completed" : `Run ${status.toLowerCase()}`}
        </h2>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[var(--l-charcoal)]/75">
        {result || error || "No result was recorded."}
      </p>
    </div>
  );
}

/** Real, honest and always empty right now: none of this platform's current
 * skills (ticketing, sql_query, document_search) produce a file, so there is
 * no artifact data to show — this is not a "coming soon" placeholder, it's
 * the true state, structured so a real artifact can render here later
 * without this tab's shape changing. */
function ArtifactsTab() {
  return (
    <div className="rounded-xl border-2 border-dashed border-[var(--l-line)] px-6 py-10 text-center">
      <Paperclip className="mx-auto h-5 w-5 text-[var(--l-charcoal)]/30" />
      <p className="mt-2 text-[12.5px] text-[var(--l-charcoal)]/50">
        This run produced no files or artifacts.
      </p>
    </div>
  );
}

function formatDuration(ms: number): string {
  if (ms < 0) return "—";
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}
