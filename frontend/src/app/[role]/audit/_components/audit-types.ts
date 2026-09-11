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

/**
 * An agent being stopped. The kill switch writes this with
 * `policy_decision: "ALLOW"` — correctly, since nothing was refused; an
 * administrator was permitted to halt an agent. So `isAllowed` stays true
 * here, and the Allowed/Denied counts must keep counting it as allowed
 * rather than inflating "denied" with events no policy ever denied.
 */
export function isHalt(e: AuditEvent) {
  return e.action === "agent_suspended";
}

/**
 * Whether a row should *read* as alarming — a refused call, or an agent
 * stopped. Deliberately separate from `isAllowed`: that answers "did a policy
 * refuse this", which drives the filters and the stat counts, while this
 * answers "should this catch the eye", which drives colour only. A kill is
 * permitted and alarming at the same time, and conflating the two questions
 * would either mislabel it as a denial or leave it looking routine.
 */
export function isAlarming(e: AuditEvent) {
  return !isAllowed(e) || isHalt(e);
}

export function timeAgo(iso: string) {
  const s = Math.max(0, Math.floor((Date.now() - +new Date(iso)) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
