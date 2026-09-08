"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { AlertCircle, Bot, Database, FileSearch, Ticket, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import type { AgentRequest } from "@/lib/types";

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  sql_query: Database,
};

type Skill = { id: string; display_name: string; description: string };

/**
 * Build the agent a request asked for.
 *
 * The skills are pre-filled from the request but **editable**, which is the
 * point rather than a convenience: the requester picked from a catalogue they
 * do not fully understand, and the builder is the one who knows what each
 * skill actually grants. Sending their picks through unchanged would make the
 * builder a typist. The dialog says which ones came from the request so a
 * deliberate change stays visible.
 *
 * This only creates the DRAFT. The compliance check and activation happen on
 * the agent's own page, because a failed check has violations to read and act
 * on, and burying that in a dialog that closes would hide the one thing the
 * builder needs to see.
 */
export function BuildAgentDialog({
  request,
  open,
  onClose,
}: {
  request: AgentRequest;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {open && <BuildAgentForm request={request} onClose={onClose} />}
    </AnimatePresence>
  );
}

/**
 * Mounted only while the dialog is open, so every field initialises straight
 * from the request. Seeding them in an effect instead would cost a second
 * render on open and leave a half-finished previous attempt on screen for a
 * frame.
 */
function BuildAgentForm({
  request,
  onClose,
}: {
  request: AgentRequest;
  onClose: () => void;
}) {
  const router = useRouter();
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [name, setName] = useState(() => request.title.slice(0, 80));
  const [description, setDescription] = useState(() => request.description);
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(request.requested_skills)
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchApi("/skills/")
      .then((data) => setSkills(data ?? []))
      .catch(() => setSkills([]));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !saving) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [saving, onClose]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || selected.size === 0) return;
    setSaving(true);
    setError(null);
    try {
      const agent = await fetchApi("/agents/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          skills: [...selected],
          request_id: request.id,
        }),
      });
      onClose();
      router.push(`/agents/${agent.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The agent could not be created.");
      setSaving(false);
    }
  }

  const asked = new Set(request.requested_skills);
  const changed =
    selected.size !== asked.size || [...selected].some((s) => !asked.has(s));

  return (
    <>
      <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={saving ? undefined : onClose}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={`Build the agent for “${request.title}”`}
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="fixed left-1/2 top-1/2 z-50 flex w-[min(560px,92vw)] max-h-[88vh] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-3xl border-2 border-[var(--l-ink)] bg-[var(--l-cream)] shadow-2xl"
          >
            <form onSubmit={submit} className="flex min-h-0 flex-col">
              <div className="flex shrink-0 items-start justify-between gap-4 border-b-2 border-dashed border-[var(--l-ink)]/15 px-6 py-4">
                <div>
                  <h2 className="landing-display text-xl text-[var(--l-ink)]">Build this agent</h2>
                  <p className="mt-0.5 text-[12.5px] text-[var(--l-charcoal)]/60">
                    For “{request.title}”
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close"
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
                <label
                  htmlFor="build-name"
                  className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50"
                >
                  Name
                </label>
                <input
                  id="build-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={80}
                  className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none"
                />

                <label
                  htmlFor="build-description"
                  className="mt-4 block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50"
                >
                  Description
                </label>
                <textarea
                  id="build-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="mt-1.5 w-full resize-none rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm leading-relaxed text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none"
                />

                <div className="mt-5 flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Skills — at least one
                  </span>
                  <span className="text-[11px] text-[var(--l-charcoal)]/45">
                    permissions follow from these, never hand-picked
                  </span>
                </div>

                <div className="mt-2 space-y-2">
                  {skills === null
                    ? [0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="h-[62px] animate-pulse rounded-xl bg-[var(--l-line)]/50"
                        />
                      ))
                    : skills.map((skill) => {
                        const Icon = SKILL_ICON[skill.id] ?? Bot;
                        const isOn = selected.has(skill.id);
                        return (
                          <button
                            type="button"
                            key={skill.id}
                            onClick={() => toggle(skill.id)}
                            aria-pressed={isOn}
                            className="flex w-full items-start gap-3 rounded-xl border-2 p-3 text-left transition-colors"
                            style={{
                              borderColor: isOn ? "var(--l-orange)" : "var(--l-line)",
                              background: isOn ? "var(--l-pink-pale)" : "var(--l-cream-deep)",
                            }}
                          >
                            <Icon className="mt-0.5 h-4 w-4 shrink-0 text-[var(--l-ink)]" />
                            <span className="min-w-0">
                              <span className="flex flex-wrap items-center gap-2">
                                <span className="text-[13.5px] font-semibold text-[var(--l-ink)]">
                                  {skill.display_name}
                                </span>
                                {asked.has(skill.id) && (
                                  <span className="rounded-full bg-[var(--l-cream)] px-2 py-0.5 text-[10.5px] font-semibold text-[var(--l-charcoal)]/65">
                                    they asked for this
                                  </span>
                                )}
                              </span>
                              <span className="mt-0.5 block text-[12px] leading-snug text-[var(--l-charcoal)]/65">
                                {skill.description}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                </div>

                {changed && (
                  <p className="mt-3 text-[12px] text-[var(--l-charcoal)]/60">
                    You have changed the skills from what was requested. That is
                    yours to judge — just make sure it still does what they asked for.
                  </p>
                )}

                {error && (
                  <p className="mt-4 flex items-start gap-2 rounded-xl border-2 border-[var(--l-orange-deep)] bg-[var(--l-orange-soft)]/25 px-3.5 py-2.5 text-sm text-[var(--l-ink)]">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    {error}
                  </p>
                )}
              </div>

              <div className="flex shrink-0 items-center justify-between gap-4 border-t-2 border-dashed border-[var(--l-ink)]/15 px-6 py-4">
                <p className="text-[12px] leading-snug text-[var(--l-charcoal)]/60">
                  Creates the draft. You run the compliance check and activate it
                  on the agent&apos;s own page.
                </p>
                <motion.button
                  type="submit"
                  disabled={saving || !name.trim() || selected.size === 0}
                  whileHover={saving ? undefined : { scale: 1.03 }}
                  whileTap={saving ? undefined : { scale: 0.97 }}
                  className="inline-flex h-11 shrink-0 items-center rounded-full bg-[var(--l-orange)] px-5 text-sm font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {saving ? "Creating…" : "Create the draft"}
                </motion.button>
              </div>
            </form>
          </motion.div>
    </>
  );
}
