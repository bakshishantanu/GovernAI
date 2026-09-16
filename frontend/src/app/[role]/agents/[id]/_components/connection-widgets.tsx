"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/api-client";

export type RequirementField = {
  key: string;
  label: string;
  secret: boolean;
  placeholder: string;
};

export type RequirementStatus = {
  key: string;
  type: string;
  label: string;
  description: string;
  fields: RequirementField[];
  satisfied: boolean;
};

/** Renders the right setup widget for one deduplicated requirement. Adding a
 * new requirement `type` later means adding one case here -- the page that
 * mounts this (agent-connections-panel.tsx) never needs to change. */
export function RequirementWidget({
  requirement,
  onSaved,
}: {
  requirement: RequirementStatus;
  onSaved: () => void;
}) {
  switch (requirement.type) {
    case "credentials":
      return <CredentialsWidget requirement={requirement} onSaved={onSaved} />;
    case "file_upload":
      return <FileUploadWidget requirement={requirement} />;
    default:
      return (
        <div className="rounded-lg border border-dashed border-[var(--l-line)] p-3 text-[12.5px] text-[var(--l-charcoal)]/60">
          {requirement.label}: unsupported requirement type &quot;{requirement.type}&quot;.
        </div>
      );
  }
}

function CredentialsWidget({
  requirement,
  onSaved,
}: {
  requirement: RequirementStatus;
  onSaved: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await fetchApi(`/connections/${requirement.key}`, {
        method: "PUT",
        body: JSON.stringify({ type: requirement.type, label: requirement.label, fields: values }),
      });
      onSaved();
    } catch {
      setError("Couldn't save this connection. Check the values and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-2 rounded-xl border border-[var(--l-line)] bg-[var(--l-cream)] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] font-semibold text-[var(--l-ink)]">{requirement.label}</span>
        <StatusBadge satisfied={requirement.satisfied} />
      </div>
      <p className="text-[11.5px] text-[var(--l-charcoal)]/60">{requirement.description}</p>
      {requirement.fields.map((field) => (
        <input
          key={field.key}
          type={field.secret ? "password" : "text"}
          placeholder={field.placeholder || field.label}
          value={values[field.key] ?? ""}
          onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
          className="w-full rounded-lg border border-[var(--l-line)] bg-white px-2.5 py-1.5 text-[12.5px] text-[var(--l-ink)] outline-none focus:border-[var(--l-orange)]"
        />
      ))}
      {error && <p className="text-[11px] text-[var(--l-orange-deep)]">{error}</p>}
      <button
        onClick={handleSave}
        disabled={saving}
        className="rounded-full bg-[var(--l-ink)] px-3 py-1.5 text-[11.5px] font-semibold text-[var(--l-cream)] transition-opacity disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save connection"}
      </button>
    </div>
  );
}

function FileUploadWidget({ requirement }: { requirement: RequirementStatus }) {
  return (
    <div className="space-y-2 rounded-xl border border-[var(--l-line)] bg-[var(--l-cream)] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[13px] font-semibold text-[var(--l-ink)]">{requirement.label}</span>
        <StatusBadge satisfied={requirement.satisfied} />
      </div>
      <p className="text-[11.5px] text-[var(--l-charcoal)]/60">{requirement.description}</p>
      <a href="../../documents" className="text-[11.5px] font-semibold text-[var(--l-ink)] underline">
        Manage documents &rarr;
      </a>
    </div>
  );
}

function StatusBadge({ satisfied }: { satisfied: boolean }) {
  return (
    <span
      className="shrink-0 rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
      style={
        satisfied
          ? { background: "color-mix(in srgb, var(--l-teal) 16%, transparent)", color: "var(--l-teal)" }
          : { background: "color-mix(in srgb, var(--l-yellow-deep) 22%, transparent)", color: "var(--l-yellow-deep)" }
      }
    >
      {satisfied ? "Connected" : "Needs setup"}
    </span>
  );
}
