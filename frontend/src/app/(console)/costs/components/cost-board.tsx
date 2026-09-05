"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { BoardPanel, ViewTabs, LiveMarker } from "@/components/board/board-panel";

/**
 * Spend, from `cost_events` rows and nothing else.
 *
 * `/costs/summary` gives the org total plus a breakdown by agent and by model;
 * `/costs/` gives the individual events. Both are aggregated in SQL — nothing
 * on this page is estimated, and the totals are all-time because the summary
 * route carries no time window.
 *
 * The by-agent breakdown is keyed by agent id, so agent names are resolved
 * against `/agents/` rather than showing a uuid to a human.
 */

type Summary = {
  total_cost_usd: number;
  by_agent: Record<string, number>;
  by_model: Record<string, number>;
};

type CostEvent = {
  id: string;
  agent_id: string;
  execution_id?: string | null;
  event_type: string;
  model?: string | null;
  provider?: string | null;
  total_tokens?: number | null;
  cost_usd: number;
  timestamp: string;
};

const HEAD_CELL =
  "px-3 text-left text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label";

function money(value: number) {
  // Real per-call costs are fractions of a cent; two decimals would show $0.00
  // for every row and make the meter look broken.
  return value >= 0.01 ? `$${value.toFixed(2)}` : `$${value.toFixed(6)}`;
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

export function CostBoard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [events, setEvents] = useState<CostEvent[]>([]);
  const [agentNames, setAgentNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [summaryData, eventData, agentData] = await Promise.all([
          fetchApi("/costs/summary"),
          fetchApi("/costs/?limit=200"),
          fetchApi("/agents/?limit=200"),
        ]);
        if (cancelled) return;

        setSummary(summaryData ?? null);
        setEvents(Array.isArray(eventData) ? eventData : []);

        const names: Record<string, string> = {};
        for (const agent of Array.isArray(agentData) ? agentData : []) {
          names[agent.id] = agent.name;
        }
        setAgentNames(names);
      } catch (err: any) {
        if (!cancelled) setError(err.message || "Could not load spend");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const byAgent = Object.entries(summary?.by_agent ?? {}).sort((a, b) => b[1] - a[1]);
  const byModel = Object.entries(summary?.by_model ?? {}).sort((a, b) => b[1] - a[1]);
  const total = summary?.total_cost_usd ?? 0;

  return (
    <>
      <ViewTabs views={[{ name: "Spend", icon: "overview" }]} active="Spend" />

      <BoardPanel toolbar={<LiveMarker label={`${money(total)} to date`} />}>
        {error && (
          <div role="alert" className="px-4 py-6 text-[13px] font-extrabold text-gv-held">
            {error}
          </div>
        )}

        {!error && loading && (
          <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">Loading spend…</p>
        )}

        {!error && !loading && (
          <>
            <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
              <Breakdown
                title="By agent"
                rows={byAgent.map(([id, cost]) => [agentNames[id] ?? id, cost])}
                total={total}
                empty="No agent has spent anything yet."
              />
              <Breakdown
                title="By model"
                rows={byModel}
                total={total}
                empty="No model calls recorded yet."
              />
            </div>

            <section className="mx-4 mb-4 overflow-hidden rounded-lg border-2 border-border bg-gv-row">
              <header className="flex h-[38px] items-center border-b-2 border-border bg-gv-head px-4">
                <h3 className="text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
                  Recent cost events
                </h3>
              </header>

              {events.length === 0 ? (
                <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">
                  Nothing recorded yet — run an agent to meter it.
                </p>
              ) : (
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="h-[38px] border-b border-gv-rule/40">
                      <th className={`${HEAD_CELL} w-[150px]`}>When</th>
                      <th className={HEAD_CELL}>Agent</th>
                      <th className={`${HEAD_CELL} w-[170px]`}>Model</th>
                      <th className={`${HEAD_CELL} w-[100px]`}>Tokens</th>
                      <th className={`${HEAD_CELL} w-[110px]`}>Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((event) => (
                      <tr key={event.id} className="h-[38px] border-b border-gv-rule/40">
                        <td className="px-3 font-mono text-[11.5px] text-gv-muted">
                          {whenOf(event.timestamp)}
                        </td>
                        <td className="px-3 text-[12.5px] font-bold text-foreground">
                          {agentNames[event.agent_id] ?? (
                            <span className="font-mono text-[11.5px] text-gv-muted">
                              {event.agent_id}
                            </span>
                          )}
                        </td>
                        <td className="px-3 font-mono text-[11.5px] text-gv-muted">
                          {event.model ?? "—"}
                        </td>
                        <td className="px-3 font-mono text-[11.5px] text-gv-muted">
                          {event.total_tokens ?? 0}
                        </td>
                        <td className="px-3 font-mono text-[11.5px] text-foreground">
                          {money(event.cost_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </>
        )}
      </BoardPanel>
    </>
  );
}

/** A share-of-total list. The bar is the value, so it carries no separate label. */
function Breakdown({
  title,
  rows,
  total,
  empty,
}: {
  title: string;
  rows: [string, number][];
  total: number;
  empty: string;
}) {
  return (
    <section className="gv-card overflow-hidden rounded-lg border-2 border-border bg-gv-row">
      <header className="flex h-[38px] items-center border-b-2 border-border bg-gv-head px-4">
        <h3 className="text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
          {title}
        </h3>
      </header>

      {rows.length === 0 ? (
        <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">{empty}</p>
      ) : (
        <ul className="p-3">
          {rows.map(([label, cost]) => {
            const share = total > 0 ? Math.max(2, (cost / total) * 100) : 0;
            return (
              <li key={label} className="py-1.5">
                <div className="flex items-baseline gap-2">
                  <span className="min-w-0 flex-1 truncate text-[12.5px] font-bold text-foreground">
                    {label}
                  </span>
                  <span className="font-mono text-[11.5px] text-gv-muted">{money(cost)}</span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full border border-border bg-gv-track">
                  <div className="h-full bg-gv-teal" style={{ width: `${share}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
