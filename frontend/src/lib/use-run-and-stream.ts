"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, fetchApi, getAuthHeader } from "./api-client";
import { readSseBody } from "./sse-client";

export type RunState = {
  status: "idle" | "connecting" | "running" | "done" | "failed";
  executionId: string | null;
  result: string | null;
  error: string | null;
};

const IDLE: RunState = { status: "idle", executionId: null, result: null, error: null };

/**
 * Starts one execution and streams it to completion, for a caller that only
 * needs the final answer - not `execution-stream.tsx`'s full tabbed
 * run-detail view (governance log, cost tiles, artifacts). Reuses that
 * component's own proven approach: `POST /executions/` to start the run,
 * then `fetch` + `readSseBody` against `/executions/{id}/stream` for the
 * result (not `EventSource`, which cannot carry the Authorization header
 * this endpoint requires - D-024).
 *
 * One hook instance runs one question at a time; calling `start` again
 * aborts whatever stream is still open first, so a second question asked
 * before the first finishes cannot land its answer out of order.
 *
 * `state` is for a caller that wants to *render* the in-progress status
 * reactively (a spinner, a "connecting…" label). `start`'s own return value
 * is the final `RunState` directly, from local variables rather than a
 * stale-closure read of `state` after awaiting — a caller that only needs
 * the finished answer (e.g. to fold into its own per-question history) can
 * use that instead of syncing two pieces of state together with an effect.
 */
export function useRunAndStream() {
  const [state, setState] = useState<RunState>(IDLE);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (agentId: string, goal: string): Promise<RunState> => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ status: "connecting", executionId: null, result: null, error: null });

    try {
      const execution = (await fetchApi("/executions/", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, goal }),
      })) as { id: string };

      if (controller.signal.aborted) return IDLE;
      setState((s) => ({ ...s, status: "running", executionId: execution.id }));

      const auth = await getAuthHeader();
      const res = await fetch(`${API_BASE}/executions/${execution.id}/stream`, {
        headers: { Authorization: auth },
        signal: controller.signal,
      });
      if (!res.body) throw new Error("The run started, but its result stream never opened.");

      let finalState: RunState = {
        status: "failed",
        executionId: execution.id,
        result: null,
        error: "The run's stream closed before it finished.",
      };

      await readSseBody(
        res.body,
        (parsed) => {
          const { event, data } = parsed as { event: string; data: { status?: string; result?: string; error?: string } };
          if (event === "done") {
            finalState = {
              status: data.status === "COMPLETED" ? "done" : "failed",
              executionId: execution.id,
              result: data.result ?? null,
              error: data.error ?? null,
            };
            setState(finalState);
          }
        },
        controller.signal,
      );

      return finalState;
    } catch (err) {
      if (controller.signal.aborted) return IDLE;
      const failed: RunState = {
        status: "failed",
        executionId: null,
        result: null,
        error: err instanceof Error ? err.message : "Could not run this question.",
      };
      setState(failed);
      return failed;
    }
  }, []);

  useEffect(() => () => abortRef.current?.abort(), []);

  return { state, start };
}
