"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { isDenied, type AuditEvent } from "@/components/audit/audit-feed";

/**
 * The three Overview figures, read from the API.
 *
 * These were hardcoded (4 / 12 / $42.50). The canvas rule is "loud chrome,
 * honest data", so each tile now states exactly what it counted:
 *
 *   Active agents  -> GET /agents/        count of status === "ACTIVE"
 *   Denied (7d)    -> GET /audits/        denied decisions inside 7 days
 *   Spend to date  -> GET /costs/summary  total_cost_usd, all time
 *
 * `/costs/summary` has no time window, so the third tile says "to date"
 * rather than "today". Do not relabel it back without a windowed route.
 *
 * The list routes cap at 200 rows, so the denial count is a count over the
 * most recent 200 events. When that cap is reached the tile says so instead
 * of presenting a partial count as a total.
 */

const PAGE = 200;

/**
 * Real per-call spend is fractions of a cent, so a plain toFixed(2) rendered
 * a live total of $0.0015 as "$0.00" — a working meter that looked broken.
 * Same rule as the costs board.
 */
function money(value: number) {
  return value >= 0.01 ? `$${value.toFixed(2)}` : `$${value.toFixed(6)}`;
}

type Tile = {
  label: string;
  value: string;
  meta: string;
};

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; tiles: Tile[] };

export function OverviewStats() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [agents, audits, costs] = await Promise.all([
          fetchApi(`/agents/?limit=${PAGE}`),
          fetchApi(`/audits/?limit=${PAGE}`),
          fetchApi("/costs/summary"),
        ]);
        if (cancelled) return;

        const agentRows: any[] = Array.isArray(agents) ? agents : [];
        const active = agentRows.filter((a) => a.status === "ACTIVE").length;

        const auditRows: AuditEvent[] = Array.isArray(audits) ? audits : [];
        const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
        const denied = auditRows.filter(
          (e) => isDenied(e) && new Date(e.timestamp).getTime() >= weekAgo,
        ).length;

        const total = Number(costs?.total_cost_usd ?? 0);
        const agentsWithSpend = Object.keys(costs?.by_agent ?? {}).length;

        setState({
          kind: "ready",
          tiles: [
            {
              label: "Active agents",
              value: String(active),
              meta: `of ${agentRows.length} registered`,
            },
            {
              label: "Denied this week",
              value: String(denied),
              meta:
                auditRows.length >= PAGE
                  ? `in the last ${PAGE} audit events`
                  : `of ${auditRows.length} governance events`,
            },
            {
              label: "Spend to date",
              value: money(total),
              meta:
                agentsWithSpend === 1
                  ? "across 1 agent"
                  : `across ${agentsWithSpend} agents`,
            },
          ],
        });
      } catch (err: any) {
        if (!cancelled) {
          setState({ kind: "error", message: err.message || "Could not load figures" });
        }
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === "error") {
    return (
      <div
        role="alert"
        className="m-4 rounded-lg border-2 border-gv-held bg-gv-held/10 p-4 text-[13px] font-extrabold text-gv-held-fg"
      >
        {state.message}
      </div>
    );
  }

  const tiles: (Tile | null)[] =
    state.kind === "loading" ? [null, null, null] : state.tiles;

  return (
    <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-3">
      {tiles.map((tile, index) => (
        <div
          key={tile?.label ?? index}
          className="gv-card rounded-lg border-2 border-border bg-gv-row p-4"
        >
          <div className="text-[10px] font-extrabold uppercase tracking-[0.06em] text-gv-muted">
            {tile?.label ?? "\u00a0"}
          </div>
          {/* hero numeral — the other place Bungee is allowed */}
          <div className="mt-2 font-display text-[30px] leading-none text-foreground">
            {tile ? tile.value : <span className="text-gv-rule">—</span>}
          </div>
          <div className="mt-1.5 font-mono text-[11px] text-gv-muted">
            {tile?.meta ?? "loading…"}
          </div>
        </div>
      ))}
    </div>
  );
}
