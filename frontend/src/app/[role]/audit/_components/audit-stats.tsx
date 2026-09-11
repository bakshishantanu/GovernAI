"use client";

export function AuditStats({
  total,
  allowed,
  denied,
  agentsInvolved,
}: {
  total: number | null;
  allowed: number | null;
  denied: number | null;
  agentsInvolved: number | null;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <Tile label="Total events" value={total} />
      <Tile label="Allowed" value={allowed} tone="ok" />
      <Tile label="Denied" value={denied} tone={denied ? "danger" : undefined} />
      <Tile label="Agents involved" value={agentsInvolved} />
    </div>
  );
}

function Tile({ label, value, tone }: { label: string; value: number | null; tone?: "ok" | "danger" }) {
  return (
    <div className="flex-1 rounded-xl border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-4 py-2.5">
      <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--l-charcoal)]/45">{label}</p>
      <p
        className="landing-display mt-0.5 text-lg"
        style={{
          color: tone === "danger" ? "var(--l-orange-deep)" : tone === "ok" ? "var(--l-teal)" : "var(--l-ink)",
        }}
      >
        {value === null ? "—" : value}
      </p>
    </div>
  );
}
