"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { RequirementStatus, RequirementWidget } from "./connection-widgets";

/** One panel, same for every agent -- what it shows is entirely driven by
 * GET /agents/{id}/requirements, which already dedupes across the agent's
 * skills server-side (see resolve_requirements in the backend). */
export function AgentConnectionsPanel({ agentId }: { agentId: string }) {
  const [requirements, setRequirements] = useState<RequirementStatus[] | null>(null);

  function reload() {
    Promise.allSettled([
      fetchApi(`/agents/${agentId}/requirements`) as Promise<RequirementStatus[]>,
      // Org-wide, not agent-scoped -- carries the masked, non-secret preview
      // values (e.g. Jira base URL/email, never the API token) a satisfied
      // requirement needs to show "connected as ..." instead of just a
      // status badge. /agents/{id}/requirements doesn't return these itself.
      fetchApi(`/connections/`) as Promise<
        { requirement_key: string; preview: Record<string, string> | null }[]
      >,
    ]).then(([reqsResult, connectionsResult]) => {
      const reqs = reqsResult.status === "fulfilled" ? (reqsResult.value ?? []) : [];
      const connections = connectionsResult.status === "fulfilled" ? connectionsResult.value : [];
      const previewByKey = new Map(connections.map((c) => [c.requirement_key, c.preview]));
      setRequirements(reqs.map((r) => ({ ...r, preview: previewByKey.get(r.key) })));
    });
  }

  useEffect(reload, [agentId]);

  return (
    <div className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_4px_0_0_rgba(22,19,14,0.12)]">
      <h2 className="landing-display text-base text-[var(--l-ink)]">Connections</h2>

      <div className="mt-3 space-y-2">
        {requirements === null ? (
          <div className="h-16 animate-pulse rounded-lg bg-[var(--l-line)]/50" />
        ) : requirements.length === 0 ? (
          <p className="py-4 text-center text-[12.5px] text-[var(--l-charcoal)]/50">
            This agent&apos;s skills don&apos;t need any extra setup.
          </p>
        ) : (
          requirements.map((requirement) => (
            <RequirementWidget key={requirement.key} requirement={requirement} onSaved={reload} />
          ))
        )}
      </div>
    </div>
  );
}
