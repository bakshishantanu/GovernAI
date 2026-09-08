"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Check, Database, FileSearch, Ticket, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { fetchApi } from "@/lib/api-client";

const SKILL_ICON: Record<string, LucideIcon> = {
  ticketing: Ticket,
  document_search: FileSearch,
  sql_query: Database,
};

type Skill = { id: string; display_name: string; description: string };

/**
 * The User's front door: describe the job, pick the skills it probably
 * needs, send it.
 *
 * Deliberately *not* the agent-creation form. A User never builds an agent —
 * this writes an Agent Request, which a Builder picks up. The copy says so
 * plainly rather than implying something is being created here, because the
 * difference (a wait, and someone else's judgement) is the whole point of
 * the workflow.
 *
 * The skill picks are a hint, not a specification: the Builder can change
 * them, since they are the one who knows what each skill actually does. The
 * form says that too, so a User is not surprised later.
 */
export function RequestAgentForm({ onSubmitted }: { onSubmitted: () => void }) {
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sending, setSending] = useState(false);
  const [sentTitle, setSentTitle] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchApi("/skills/")
      .then((data) => setSkills(data ?? []))
      .catch(() => setSkills([]));
  }, []);

  function toggleSkill(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    setSending(true);
    setError(null);
    try {
      await fetchApi("/agent-requests/", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          requested_skills: [...selected],
        }),
      });
      setSentTitle(title.trim());
      setTitle("");
      setDescription("");
      setSelected(new Set());
      onSubmitted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send the request.");
    } finally {
      setSending(false);
    }
  }

  const canSend = title.trim().length > 0 && description.trim().length > 0 && !sending;

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-3xl border-2 border-[var(--l-ink)] bg-[var(--l-cream)] p-6"
    >
      <AnimatePresence>
        {sentTitle && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mb-5 flex items-start gap-3 rounded-2xl border-2 border-[var(--l-teal)] bg-[var(--l-teal-soft)] px-4 py-3"
          >
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--l-ink)]" />
            <div className="text-sm text-[var(--l-ink)]">
              <strong>“{sentTitle}” is with the builders.</strong>
              <span className="block text-[var(--l-charcoal)]/70">
                It will show below as waiting until someone picks it up.
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <label
        htmlFor="request-title"
        className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50"
      >
        What should it do — in a few words
      </label>
      <input
        id="request-title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="e.g. Answer questions about our refund policy"
        maxLength={255}
        className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
      />

      <label
        htmlFor="request-description"
        className="mt-4 block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50"
      >
        The whole story
      </label>
      <textarea
        id="request-description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="What do you need done, how often, and what does a good answer look like? The more you say here, the less guessing the builder has to do."
        rows={4}
        className="mt-1.5 w-full resize-none rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm leading-relaxed text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
      />

      <div className="mt-5 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
          Skills you think it needs — optional
        </span>
        <span className="text-[11px] text-[var(--l-charcoal)]/45">
          a hint, not a decision — the builder may change these
        </span>
      </div>

      <div className="mt-2 grid gap-2 sm:grid-cols-3">
        {skills === null
          ? [0, 1, 2].map((i) => (
              <div key={i} className="h-[86px] animate-pulse rounded-xl bg-[var(--l-line)]/50" />
            ))
          : skills.map((skill) => {
              const Icon = SKILL_ICON[skill.id] ?? Bot;
              const isOn = selected.has(skill.id);
              return (
                <button
                  type="button"
                  key={skill.id}
                  onClick={() => toggleSkill(skill.id)}
                  aria-pressed={isOn}
                  className="flex h-full flex-col gap-1.5 rounded-xl border-2 p-3 text-left transition-colors"
                  style={{
                    borderColor: isOn ? "var(--l-orange)" : "var(--l-line)",
                    // Raw CSS here, not a Tailwind class, so the "/40" opacity
                    // shorthand is not available - it would be dropped silently
                    // and leave the unselected cards with no fill at all.
                    background: isOn ? "var(--l-pink-pale)" : "var(--l-cream-deep)",
                  }}
                >
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4 shrink-0 text-[var(--l-ink)]" />
                    <span className="text-[13px] font-semibold text-[var(--l-ink)]">
                      {skill.display_name}
                    </span>
                  </span>
                  <span className="text-[11.5px] leading-snug text-[var(--l-charcoal)]/65">
                    {skill.description}
                  </span>
                </button>
              );
            })}
      </div>

      {error && (
        <p className="mt-4 rounded-xl border-2 border-[var(--l-orange-deep)] bg-[var(--l-orange-soft)] px-3.5 py-2.5 text-sm text-[var(--l-ink)]">
          {error}
        </p>
      )}

      <div className="mt-6 flex items-center justify-between gap-4 border-t-2 border-dashed border-[var(--l-ink)]/15 pt-5">
        <p className="text-[12px] leading-snug text-[var(--l-charcoal)]/60">
          You are asking for an agent, not building one. A builder assembles it,
          the compliance check runs, and it arrives in <strong>My agents</strong>.
        </p>
        <motion.button
          type="submit"
          disabled={!canSend}
          whileHover={canSend ? { scale: 1.03 } : undefined}
          whileTap={canSend ? { scale: 0.97 } : undefined}
          className="inline-flex h-11 shrink-0 items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 text-sm font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Sparkles className="h-4 w-4" />
          {sending ? "Sending…" : "Send request"}
        </motion.button>
      </div>
    </form>
  );
}
