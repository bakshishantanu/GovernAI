"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchApi } from "@/lib/api-client";
import { BoardPanel, ViewTabs, LiveMarker } from "@/components/board/board-panel";
import { ChevronRight } from "lucide-react";

/**
 * Every run in the organisation, newest first, on the board primitive.
 *
 * A run is the only place the governance story is visible end to end, so the
 * row leads with status and links straight into the live viewer. Runs that are
 * still going are the reason this page exists — they are the ones you click.
 */

type Execution = {
  id: string;
  agent_id: string;
  goal: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
};

const TERMINAL = ["COMPLETED", "FAILED", "CANCELLED", "TERMINATED"];

function statusSkin(status: string) {
  if (status === "COMPLETED") return "bg-gv-cleared text-gv-cleared-fg";
  if (status === "FAILED" || status === "CANCELLED" || status === "TERMINATED")
    return "bg-gv-held text-gv-held-fg";
  if (status === "RUNNING") return "bg-gv-watch text-gv-watch-fg";
  return "bg-gv-draft text-gv-draft-fg";
}

function whenOf(iso: string) {
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

const HEAD_CELL =
  "px-3 text-left text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label";

export function RunList() {
  const [runs, setRuns] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/executions/")
      .then((data) => {
        if (!cancelled) setRuns(Array.isArray(data) ? data : []);
      })
      .catch((err: any) => {
        if (!cancelled) setError(err.message || "Could not load runs");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeCount = runs.filter((r) => !TERMINAL.includes(r.status)).length;

  return (
    <>
      <ViewTabs views={[{ name: "Table", icon: "table" }]} active="Table" />

      <BoardPanel
        toolbar={
          <LiveMarker
            label={
              activeCount > 0
                ? `${activeCount} run${activeCount === 1 ? "" : "s"} in flight`
                : "No run in flight"
            }
          />
        }
      >
        {error && (
          <div role="alert" className="px-4 py-6 text-[13px] font-extrabold text-gv-held">
            {error}
          </div>
        )}

        {!error && loading && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">Loading runs…</p>
        )}

        {!error && !loading && runs.length === 0 && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">
            No runs yet. Open an active agent and start one to watch it live.
          </p>
        )}

        {!error && !loading && runs.length > 0 && (
          <table className="w-full border-collapse">
            <thead>
              <tr className="h-[38px] border-b-2 border-border bg-gv-head">
                <th className={`${HEAD_CELL} w-[110px]`}>Status</th>
                <th className={HEAD_CELL}>Goal</th>
                <th className={`${HEAD_CELL} w-[150px]`}>Started</th>
                <th className="w-9" />
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="relative h-12 border-b border-gv-rule/40 hover:bg-gv-row-sel"
                >
                  <td className="px-3">
                    <span
                      className={`inline-flex h-[22px] items-center rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${statusSkin(
                        run.status,
                      )}`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="max-w-0 truncate px-3 text-[13px] font-bold text-foreground">
                    {/* the whole row is one target, without nesting controls */}
                    <Link href={`/runs/${run.id}`} className="after:absolute after:inset-0">
                      {run.goal}
                    </Link>
                  </td>
                  <td className="px-3 font-mono text-[11.5px] text-gv-muted">
                    {whenOf(run.started_at)}
                  </td>
                  <td className="px-2">
                    <ChevronRight
                      className="h-4 w-4 text-gv-muted"
                      strokeWidth={2.4}
                      aria-hidden="true"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </BoardPanel>
    </>
  );
}
