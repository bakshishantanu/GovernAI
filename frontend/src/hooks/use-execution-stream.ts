"use client";

import { useEffect, useRef, useState } from "react";
import { streamSse, type SseEvent } from "@/lib/sse-client";

/**
 * Subscribe to one execution and accumulate what the backend publishes.
 *
 * The frame vocabulary is fixed by `backend/app/api/v1/executions.py`:
 *
 *   status               once, on connect  { execution_id, status, goal }
 *   audit.tool.allowed   per tool call     { id, at, execution_id, tool, reason }
 *   audit.tool.denied    per blocked call  { id, at, execution_id, tool, reason }
 *   cost.llm.incurred    per model call    { id, at, execution_id, cost_usd, tokens }
 *   done                 once, at the end  { status, result, error, completed_at }
 *
 * The stream closes itself after `done`, so there is no reconnect loop here:
 * a closed stream means the run is over, not that the connection dropped.
 */

export type RunEntry = {
  key: string;
  at?: string;
  kind: "allowed" | "denied" | "cost";
  tool?: string;
  reason?: string;
  costUsd?: number;
  tokens?: number;
};

export type RunStream = {
  status: string;
  goal?: string;
  entries: RunEntry[];
  /** Running total of the cost events seen on this stream. */
  spendUsd: number;
  deniedCount: number;
  result?: string | null;
  error?: string | null;
  /** True once the server sent `done` or closed the stream. */
  finished: boolean;
  connectionError: string | null;
};

const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED", "TERMINATED"];

export function useExecutionStream(executionId: string | undefined): RunStream {
  const [state, setState] = useState<RunStream>({
    status: "PENDING",
    entries: [],
    spendUsd: 0,
    deniedCount: 0,
    finished: false,
    connectionError: null,
  });

  // Frames can arrive faster than React commits, so the running key counter
  // lives in a ref rather than in state.
  const seq = useRef(0);

  useEffect(() => {
    if (!executionId) return;

    const controller = new AbortController();
    seq.current = 0;
    setState({
      status: "PENDING",
      entries: [],
      spendUsd: 0,
      deniedCount: 0,
      finished: false,
      connectionError: null,
    });

    const handle = (event: SseEvent) => {
      const data = event.data ?? {};

      setState((prev) => {
        switch (event.type) {
          case "status":
            return { ...prev, status: data.status ?? prev.status, goal: data.goal };

          case "audit.tool.allowed":
          case "audit.tool.denied": {
            const denied = event.type.endsWith("denied");
            const entry: RunEntry = {
              key: data.id ?? `e${seq.current++}`,
              at: data.at,
              kind: denied ? "denied" : "allowed",
              tool: data.tool,
              reason: data.reason,
            };
            return {
              ...prev,
              status: prev.status === "PENDING" ? "RUNNING" : prev.status,
              entries: [...prev.entries, entry],
              deniedCount: prev.deniedCount + (denied ? 1 : 0),
            };
          }

          case "cost.llm.incurred": {
            const cost = Number(data.cost_usd ?? 0);
            const entry: RunEntry = {
              key: data.id ?? `e${seq.current++}`,
              at: data.at,
              kind: "cost",
              costUsd: cost,
              tokens: data.tokens,
            };
            return {
              ...prev,
              status: prev.status === "PENDING" ? "RUNNING" : prev.status,
              entries: [...prev.entries, entry],
              spendUsd: prev.spendUsd + cost,
            };
          }

          case "done":
            return {
              ...prev,
              status: data.status ?? "COMPLETED",
              result: data.result,
              error: data.error,
              finished: true,
            };

          default:
            return prev;
        }
      });
    };

    streamSse(
      `/executions/${executionId}/stream`,
      {
        onEvent: handle,
        onClose: () =>
          setState((prev) => ({
            ...prev,
            finished: true,
            // The stream only closes after `done` or when the run vanished.
            status: TERMINAL.includes(prev.status) ? prev.status : prev.status,
          })),
        onError: (err) =>
          setState((prev) => ({ ...prev, connectionError: err.message, finished: true })),
      },
      controller.signal,
    );

    return () => controller.abort();
  }, [executionId]);

  return state;
}
