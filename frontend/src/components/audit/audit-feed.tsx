"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { ShieldAlert, ShieldCheck, Minus } from "lucide-react";

/**
 * The audit log, as one component used in more than one place.
 *
 * FRONTEND.md build order item 3: the organisation-wide feed on Overview and
 * the per-agent history are the same list with a different filter, so this
 * takes `agentId` rather than existing twice.
 *
 * Rows are 38px per the canvas log-row density. The decision is the only
 * filled colour column — it is the governance fact the row exists to report.
 */

export type AuditEvent = {
  id: string;
  timestamp: string;
  actor_type: string;
  agent_id?: string | null;
  execution_id?: string | null;
  action: string;
  resource?: string | null;
  tool?: string | null;
  policy_decision: string;
  result?: string | null;
  reason?: string | null;
  cost_usd?: number | null;
};

/** DENY and DENIED both occur in stored rows; treat them as one thing. */
export function isDenied(event: AuditEvent) {
  return (event.policy_decision || "").toUpperCase().startsWith("DEN");
}

function decisionOf(event: AuditEvent) {
  const raw = (event.policy_decision || "").toUpperCase();
  if (raw.startsWith("DEN")) {
    return { label: "Denied", fill: "bg-gv-held text-gv-held-fg", Icon: ShieldAlert };
  }
  if (raw.startsWith("ALLOW")) {
    return { label: "Allowed", fill: "bg-gv-cleared text-gv-cleared-fg", Icon: ShieldCheck };
  }
  return { label: "n/a", fill: "bg-gv-draft text-gv-draft-fg", Icon: Minus };
}

function timeOf(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--:--:--";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function AuditFeed({
  agentId,
  limit = 50,
  emptyLabel = "No governance events recorded yet.",
}: {
  agentId?: string;
  limit?: number;
  emptyLabel?: string;
}) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchApi(`/audits/?limit=${limit}`);
      const all: AuditEvent[] = Array.isArray(data) ? data : [];
      // The route has no agent filter yet, so narrow here. When
      // `GET /audits/?agent_id=` lands, move this into the query string.
      setEvents(agentId ? all.filter((e) => e.agent_id === agentId) : all);
    } catch (err: any) {
      setError(err.message || "Could not load the audit log");
    } finally {
      setLoading(false);
    }
  }, [agentId, limit]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <FeedNote>Loading the audit log…</FeedNote>;
  }

  if (error) {
    return (
      <div role="alert" className="px-4 py-6 text-[13px] font-extrabold text-gv-held">
        {error}
      </div>
    );
  }

  if (events.length === 0) {
    return <FeedNote>{emptyLabel}</FeedNote>;
  }

  return (
    <ul className="divide-y divide-gv-rule/40">
      {events.map((event) => {
        const decision = decisionOf(event);
        return (
          <li
            key={event.id}
            className="flex h-[38px] items-center gap-3 px-4 hover:bg-gv-row-sel"
          >
            <span className="w-[68px] shrink-0 font-mono text-[11px] text-gv-muted">
              {timeOf(event.timestamp)}
            </span>

            <span
              className={`inline-flex h-[22px] shrink-0 items-center gap-1 rounded border border-border px-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${decision.fill}`}
            >
              <decision.Icon className="h-3 w-3" strokeWidth={2.6} aria-hidden="true" />
              {decision.label}
            </span>

            <span className="min-w-0 flex-1 truncate text-[12.5px] font-bold text-foreground">
              {event.tool ? (
                <>
                  <span className="font-mono text-[12px]">{event.tool}</span>
                  <span className="text-gv-muted"> · {event.action}</span>
                </>
              ) : (
                event.action
              )}
              {event.reason && (
                <span className="text-gv-muted"> — {event.reason}</span>
              )}
            </span>

            <span className="hidden shrink-0 font-mono text-[11px] text-gv-muted sm:block">
              {event.actor_type?.toUpperCase()}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function FeedNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-4 py-6 text-[13px] font-bold text-gv-muted">{children}</p>
  );
}
