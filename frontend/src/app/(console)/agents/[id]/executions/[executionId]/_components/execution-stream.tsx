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
} from "lucide-react";
import { API_BASE, getAuthHeader, fetchApi } from "@/lib/api-client";
import { money } from "../../../../_components/agent-types";

type LiveStatus = "connecting" | "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED" | "TERMINATED";

type TimelineEvent =
  | { id: string; kind: "allowed" | "denied"; tool: string; reason: string; at: string }
  | { id: string; kind: "cost"; cost_usd: number; tokens: number; at: string };

/** Parses one buffered SSE chunk into complete frames, keeping any partial tail for next time. */
function extractFrames(buffer: string): { frames: string[]; rest: string } {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  return { frames: parts, rest };
}

function parseFrame(frame: string): { event: string; data: unknown } | null {
  if (frame.startsWith(":")) return null; // heartbeat comment
  let event = "message";
  let dataLine = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
  }
  if (!dataLine) return null;
  try {
    return { event, data: JSON.parse(dataLine) };
  } catch {
    return null;
  }
}

/**
 * The live execution view — every tool call, allow/deny and cost as it
 * actually happens, driven by GET /executions/{id}/stream. `fetch` +
 * `ReadableStream` rather than `EventSource`, because EventSource cannot
 * carry the Authorization header this endpoint requires (D-024).
 */
export function ExecutionStream({ agentId, executionId }: { agentId: string; executionId: string }) {
  const [status, setStatus] = useState<LiveStatus>("connecting");
  const [goal, setGoal] = useState("");
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [result, setResult] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

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
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const { frames, rest } = extractFrames(buffer);
        buffer = rest;

        for (const raw of frames) {
          const parsed = parseFrame(raw);
          if (!parsed) continue;
          const { event, data } = parsed as { event: string; data: any };

          if (event === "status") {
            setGoal(data.goal ?? "");
            setStatus(data.status);
          } else if (event === "audit.tool.allowed" || event === "audit.tool.denied") {
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
            setEvents((prev) => [
              ...prev,
              { id: data.id, kind: "cost", cost_usd: data.cost_usd, tokens: data.tokens, at: data.at },
            ]);
          } else if (event === "done") {
            setStatus(data.status);
            setResult(data.result ?? null);
            setRunError(data.error ?? null);
          }
        }
      }
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
  const totalCost = events.reduce((sum, e) => (e.kind === "cost" ? sum + e.cost_usd : sum), 0);
  const denials = events.filter((e) => e.kind === "denied").length;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link
        href={`/agents/${agentId}`}
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
            </span>
            <h1 className="landing-display mt-1 text-xl text-[var(--l-ink)]">{goal || "Loading goal…"}</h1>
          </div>
          <StatusBadge status={status} />
        </div>

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
        <StatTile label="Tool calls" value={String(events.filter((e) => e.kind !== "cost").length)} />
        <StatTile label="Denied" value={String(denials)} tone={denials > 0 ? "danger" : undefined} />
        <StatTile label="Cost so far" value={money(totalCost)} />
      </div>

      <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_4px_0_0_rgba(22,19,14,0.12)]">
        <h2 className="landing-display text-base text-[var(--l-ink)]">Live governance feed</h2>
        <div className="mt-3 space-y-1.5">
          <AnimatePresence initial={false}>
            {events.length === 0 ? (
              <motion.p
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="py-6 text-center text-[12.5px] text-[var(--l-charcoal)]/50"
              >
                {live ? "Waiting for the first tool call…" : "No tool calls were made."}
              </motion.p>
            ) : (
              events.map((e) => <TimelineRow key={e.id} event={e} />)
            )}
          </AnimatePresence>
          {live && (
            <div className="flex items-center gap-2 px-2 py-2 text-[12px] text-[var(--l-charcoal)]/45">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              watching…
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {!live && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
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
            <p className="mt-2 text-sm leading-relaxed text-[var(--l-charcoal)]/75">
              {result || runError || "No result was recorded."}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatusBadge({ status }: { status: LiveStatus }) {
  const live = status === "PENDING" || status === "RUNNING" || status === "connecting";
  return (
    <span
      className="flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 font-mono text-[10.5px] font-semibold uppercase tracking-wide"
      style={{
        background: live ? "var(--l-orange)" : status === "COMPLETED" ? "var(--l-teal)" : "var(--l-charcoal)",
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
    <div className="flex-1 rounded-xl border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-4 py-2.5">
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
          {money(event.cost_usd)} · {event.tokens} tokens
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
