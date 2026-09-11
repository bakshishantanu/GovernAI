/**
 * Pure aggregation helpers for the dashboard. Kept separate from rendering
 * so the "what counts as the peak hour" logic can be read (and trusted) on
 * its own, without wading through JSX.
 *
 * Real data is sparse and uneven — the seed history spans two days with one
 * heavy hour — so buckets are zero-filled across the *actual* observed
 * range rather than dropped, and nothing here manufactures smoothness that
 * isn't in the source events.
 */

export type AuditEvent = {
  id: string;
  timestamp: string;
  agent_id: string | null;
  action: string;
  tool: string | null;
  policy_decision: string | null;
  reason: string | null;
};

export type HourBucket = {
  hourKey: string; // "2026-09-05T19"
  label: string; // "7pm, Sep 5"
  total: number;
  denied: number;
};

/** Zero-filled hourly buckets from the earliest to the latest real event. */
export function bucketByHour(events: AuditEvent[]): HourBucket[] {
  if (events.length === 0) return [];

  const toHourKey = (iso: string) => iso.slice(0, 13);
  const counts = new Map<string, { total: number; denied: number }>();
  for (const e of events) {
    const key = toHourKey(e.timestamp);
    const cur = counts.get(key) ?? { total: 0, denied: 0 };
    cur.total += 1;
    if (e.policy_decision === "DENY") cur.denied += 1;
    counts.set(key, cur);
  }

  const sortedKeys = [...counts.keys()].sort();
  const start = new Date(sortedKeys[0] + ":00:00Z");
  const end = new Date(sortedKeys[sortedKeys.length - 1] + ":00:00Z");

  const buckets: HourBucket[] = [];
  for (let t = new Date(start); t <= end; t = new Date(t.getTime() + 3600_000)) {
    const key = t.toISOString().slice(0, 13);
    const c = counts.get(key) ?? { total: 0, denied: 0 };
    buckets.push({
      hourKey: key,
      label: t.toLocaleTimeString("en-US", { hour: "numeric" }).replace(" ", "") +
        ", " +
        t.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      total: c.total,
      denied: c.denied,
    });
  }
  // Cap defends against an unbounded real history squashing the chart into
  // hairlines, but must never silently drop the actual peak — "most recent
  // 24" did exactly that with this seed data (a 32-event hour sits outside
  // the last 24 hours of a 43-hour range) and quietly turned a real spike
  // into "Total calls 2". Compress by merging adjacent hours into wider
  // buckets instead, so every real event is still counted somewhere.
  const CAP = 48;
  if (buckets.length <= CAP) return buckets;

  const groupSize = Math.ceil(buckets.length / CAP);
  const merged: HourBucket[] = [];
  for (let i = 0; i < buckets.length; i += groupSize) {
    const group = buckets.slice(i, i + groupSize);
    merged.push({
      hourKey: group[0].hourKey,
      label: group.length > 1 ? `${group[0].label}–${group[group.length - 1].label}` : group[0].label,
      total: group.reduce((s, b) => s + b.total, 0),
      denied: group.reduce((s, b) => s + b.denied, 0),
    });
  }
  return merged;
}

export function peakBucket(buckets: HourBucket[]): HourBucket | null {
  if (buckets.length === 0) return null;
  return buckets.reduce((max, b) => (b.total > max.total ? b : max), buckets[0]);
}

export type ToolCount = { tool: string; count: number; denied: number };

export function byTool(events: AuditEvent[]): ToolCount[] {
  const counts = new Map<string, { count: number; denied: number }>();
  for (const e of events) {
    if (!e.tool) continue;
    const cur = counts.get(e.tool) ?? { count: 0, denied: 0 };
    cur.count += 1;
    if (e.policy_decision === "DENY") cur.denied += 1;
    counts.set(e.tool, cur);
  }
  return [...counts.entries()]
    .map(([tool, v]) => ({ tool, ...v }))
    .sort((a, b) => b.count - a.count);
}

export type AgentSummary = {
  passport: { lifecycle_state: string; compliance_status: string };
};

/**
 * Fraction of the fleet in good standing — active (or ready to be) *and*
 * past its compliance check. Deliberately NOT based on the audit ALLOW/DENY
 * ratio: a 100% allow rate could just as easily mean nothing risky was ever
 * attempted as it could mean governance is healthy, so it isn't a safe
 * stand-in for "is this fleet okay". Standing (lifecycle + compliance) is.
 */
export function fleetHealth(agents: AgentSummary[]): {
  pct: number;
  label: "Good" | "Fair" | "Needs review";
} {
  if (agents.length === 0) return { pct: 100, label: "Good" };
  const healthy = agents.filter(
    (a) =>
      ["ACTIVE", "APPROVED"].includes(a.passport.lifecycle_state) &&
      a.passport.compliance_status === "PASSED",
  ).length;
  const pct = Math.round((healthy / agents.length) * 100);
  const label = pct >= 85 ? "Good" : pct >= 60 ? "Fair" : "Needs review";
  return { pct, label };
}
