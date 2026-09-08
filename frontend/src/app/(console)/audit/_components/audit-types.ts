export type AuditEvent = {
  id: string;
  timestamp: string;
  actor_type: string;
  actor_id: string;
  agent_id: string | null;
  execution_id: string | null;
  action: string;
  resource: string | null;
  tool: string | null;
  policy_decision: string;
  reason: string | null;
};

export function isAllowed(e: AuditEvent) {
  return e.policy_decision === "ALLOW" || e.policy_decision === "ALLOWED";
}

export function timeAgo(iso: string) {
  const s = Math.max(0, Math.floor((Date.now() - +new Date(iso)) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
