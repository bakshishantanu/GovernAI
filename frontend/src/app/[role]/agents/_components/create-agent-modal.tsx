"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Bot, FileSearch, Ticket, ShieldCheck, ShieldX, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ApiError, fetchApi, type ApiViolation } from "@/lib/api-client";

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  solr_search: Search,
};

type Skill = { id: string; display_name: string; description: string; required_permissions: string[] };

type Stage = "form" | "submitting" | "active" | "approved" | "violation";

/**
 * Draft a new passport and put it to work. Three real backend calls: POST
 * /agents/ creates the DRAFT with derived permissions, PATCH
 * /agents/{id}/submit runs the actual compliance check, and on a pass PATCH
 * /agents/{id}/activate makes it live. A compliance failure is shown as the
 * real violation strings from the backend — the agent still exists, just
 * stuck in DRAFT, and is never activated.
 */
export function CreateAgentModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [stage, setStage] = useState<Stage>("form");
  const [violation, setViolation] = useState("");
  const [violations, setViolations] = useState<ApiViolation[]>([]);
  const [createdName, setCreatedName] = useState("");

  useEffect(() => {
    if (!open) return;
    fetchApi("/skills/")
      // sql_query is retired (replaced by solr_search/"Enterprise Search")
      // — its DB row only survives for an existing agent's binding, it
      // should never be offered as a choice when building a new one.
      .then((data) => setSkills((data ?? []).filter((s: Skill) => s.id !== "sql_query")))
      .catch(() => setSkills([]));
  }, [open]);

  useEffect(() => {
    if (!open) {
      setName("");
      setDescription("");
      setSelected(new Set());
      setStage("form");
      setViolation("");
      setViolations([]);
    }
  }, [open]);

  function toggleSkill(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || selected.size === 0) return;
    setStage("submitting");
    setCreatedName(name.trim());

    try {
      const created = await fetchApi("/agents/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          skills: [...selected],
        }),
      });

      try {
        await fetchApi(`/agents/${created.id}/submit`, { method: "PATCH" });
      } catch (err) {
        setViolation(err instanceof Error ? err.message : "Compliance check failed.");
        setViolations(err instanceof ApiError ? err.violations : []);
        setStage("violation");
        onCreated(); // it still exists, in DRAFT — the roster should show it
        return;
      }

      // Passed compliance: activate straight away, so building an agent ends
      // with a working agent rather than one parked at APPROVED waiting for a
      // click. The owner is allowed to do this (see PATCH /agents/{id}/activate).
      // If activation alone fails, the agent is still approved and the result
      // pane says so, rather than claiming it is live.
      try {
        await fetchApi(`/agents/${created.id}/activate`, { method: "PATCH" });
        setStage("active");
      } catch {
        setStage("approved");
      }
      onCreated();
    } catch (err) {
      setViolation(err instanceof Error ? err.message : "Could not create the agent.");
      setViolations([]);
      setStage("violation");
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={stage === "submitting" ? undefined : onClose}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="fixed left-1/2 top-1/2 z-50 w-[min(520px,92vw)] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-3xl border-2 border-[var(--l-ink)] bg-[var(--l-cream)] shadow-2xl"
            style={{ maxHeight: "88vh" }}
          >
            {stage === "active" ? (
              <ResultPane
                ok
                badge="Compliance passed: Active"
                title={createdName}
                message="Passport issued and the agent is live. Permissions were derived from its skills, nothing more, nothing hand-granted."
                onClose={onClose}
              />
            ) : stage === "approved" ? (
              <ResultPane
                ok
                title={createdName}
                message="Passport approved, but activation did not go through. Open the agent and press Activate."
                onClose={onClose}
              />
            ) : stage === "violation" ? (
              <ResultPane
                ok={false}
                title={createdName}
                message={violation}
                violations={violations}
                onClose={onClose}
              />
            ) : (
              <form onSubmit={handleSubmit} className="flex max-h-[88vh] flex-col">
                <div className="flex shrink-0 items-center justify-between border-b-2 border-dashed border-[var(--l-ink)]/15 px-6 py-4">
                  <h2 className="landing-display text-xl text-[var(--l-ink)]">
                    Draft a new passport
                  </h2>
                  <button
                    type="button"
                    onClick={onClose}
                    aria-label="Close"
                    className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="overflow-y-auto px-6 py-5">
                  <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Name
                  </label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Invoice Triage Bot"
                    required
                    className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                  />

                  <label className="mt-4 block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Description
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What does it do, and for whom?"
                    rows={2}
                    className="mt-1.5 w-full resize-none rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                  />

                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                      Skills (at least one)
                    </span>
                    <span className="font-mono text-[10.5px] text-[var(--l-charcoal)]/40">
                      permissions are derived, never hand-picked
                    </span>
                  </div>

                  <div className="mt-2 space-y-2">
                    {skills === null ? (
                      [0, 1, 2].map((i) => (
                        <div key={i} className="h-14 animate-pulse rounded-xl bg-[var(--l-line)]/50" />
                      ))
                    ) : (
                      skills.map((skill) => {
                        const Icon = SKILL_ICON[skill.id] ?? Bot;
                        const isOn = selected.has(skill.id);
                        return (
                          <button
                            type="button"
                            key={skill.id}
                            onClick={() => toggleSkill(skill.id)}
                            className="flex w-full items-center gap-3 rounded-xl border-2 px-3.5 py-2.5 text-left transition-colors"
                            style={{
                              borderColor: isOn ? "var(--l-orange)" : "var(--l-line)",
                              background: isOn
                                ? "color-mix(in srgb, var(--l-orange) 10%, transparent)"
                                : "var(--l-cream-deep)",
                            }}
                          >
                            <span
                              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-2"
                              style={{ borderColor: isOn ? "var(--l-orange)" : "var(--l-line)" }}
                            >
                              <Icon className="h-3.5 w-3.5 text-[var(--l-charcoal)]/70" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-[13px] font-semibold text-[var(--l-ink)]">
                                {skill.display_name}
                              </span>
                              <span className="block truncate font-mono text-[10.5px] text-[var(--l-charcoal)]/50">
                                {skill.required_permissions.join(", ")}
                              </span>
                            </span>
                            <span
                              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2"
                              style={{
                                borderColor: isOn ? "var(--l-orange)" : "var(--l-charcoal)",
                                background: isOn ? "var(--l-orange)" : "transparent",
                                opacity: isOn ? 1 : 0.35,
                              }}
                            >
                              {isOn && <ShieldCheck className="h-3 w-3 text-white" />}
                            </span>
                          </button>
                        );
                      })
                    )}
                  </div>
                </div>

                <div className="flex shrink-0 items-center justify-end gap-2 border-t-2 border-dashed border-[var(--l-ink)]/15 px-6 py-4">
                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-full px-4 py-2 text-sm font-semibold text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
                  >
                    Cancel
                  </button>
                  <motion.button
                    type="submit"
                    disabled={!name.trim() || selected.size === 0 || stage === "submitting"}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    className="rounded-full bg-[var(--l-orange)] px-5 py-2 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--l-orange-deep)] transition-opacity disabled:opacity-40"
                  >
                    {stage === "submitting" ? "Stamping…" : "Create & submit"}
                  </motion.button>
                </div>
              </form>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function ResultPane({
  ok,
  badge,
  title,
  message,
  violations = [],
  onClose,
}: {
  ok: boolean;
  /** Overrides the default passed/failed label under the title. */
  badge?: string;
  title: string;
  message: string;
  /** Every rule that was broken, not just the first — FRD-02. */
  violations?: ApiViolation[];
  onClose: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-4 px-8 py-10 text-center">
      <motion.div
        initial={{ scale: 1.8, rotate: -20, opacity: 0 }}
        animate={{ scale: 1, rotate: ok ? -10 : -6, opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="flex h-20 w-20 items-center justify-center rounded-full border-[3px] border-dashed"
        style={{ borderColor: ok ? "var(--l-teal)" : "var(--l-orange-deep)" }}
      >
        {ok ? (
          <ShieldCheck className="h-8 w-8" style={{ color: "var(--l-teal)" }} />
        ) : (
          <ShieldX className="h-8 w-8" style={{ color: "var(--l-orange-deep)" }} />
        )}
      </motion.div>
      <div>
        <h3 className="landing-display text-lg text-[var(--l-ink)]">{title}</h3>
        <p
          className="mt-1 text-[10px] font-bold uppercase tracking-[0.14em]"
          style={{ color: ok ? "var(--l-teal)" : "var(--l-orange-deep)" }}
        >
          {badge ?? (ok ? "Compliance passed: Approved" : "Compliance check failed: still Draft")}
        </p>
      </div>
      <p className="max-w-xs text-sm leading-relaxed text-[var(--l-charcoal)]/70">{message}</p>
      {violations.length > 0 && (
        <ul className="w-full space-y-1.5 text-left">
          {violations.map((v) => (
            <li
              key={v.rule + v.message}
              className="rounded-xl border-2 border-[var(--l-orange-deep)]/40 bg-[var(--l-orange-soft)]/25 px-3.5 py-2.5 text-[13px] leading-snug text-[var(--l-ink)]"
            >
              {v.message}
            </li>
          ))}
        </ul>
      )}
      <button
        onClick={onClose}
        className="mt-1 rounded-full border-2 border-[var(--l-ink)] px-5 py-2 text-sm font-semibold text-[var(--l-ink)] transition-colors hover:bg-[var(--l-ink)] hover:text-[var(--l-cream)]"
      >
        {ok ? "See it on the roster" : "Back to roster"}
      </button>
    </div>
  );
}
