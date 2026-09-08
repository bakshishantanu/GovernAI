"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ShieldPlus, Loader2 } from "lucide-react";
import { fetchApi } from "@/lib/api-client";

/**
 * Only offers an `sql_blocklist` rule at creation time — the one rule type
 * the engine actually enforces (domain/policies/engine.py). Letting someone
 * build a policy out of rule types that change nothing would be a worse UI
 * lie than not offering them at all.
 */
export function CreatePolicyModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [keywords, setKeywords] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) {
      setName("");
      setDescription("");
      setKeywords("");
      setError("");
    }
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError("");

    const keywordList = keywords
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);

    try {
      await fetchApi("/policies/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          enabled: true,
          rules: keywordList.length
            ? [
                {
                  name: "Blocklist",
                  rule_type: "sql_blocklist",
                  config: { keywords: keywordList },
                  priority: 10,
                  enabled: true,
                },
              ]
            : [],
        }),
      });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create this policy.");
    } finally {
      setBusy(false);
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
            onClick={busy ? undefined : onClose}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="fixed left-1/2 top-1/2 z-50 w-[min(480px,92vw)] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-3xl border-2 border-[var(--l-ink)] bg-[var(--l-cream)] shadow-2xl"
          >
            <form onSubmit={handleSubmit}>
              <div className="flex items-center justify-between border-b-2 border-dashed border-[var(--l-ink)]/15 px-6 py-4">
                <h2 className="landing-display text-xl text-[var(--l-ink)]">Write a new policy</h2>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close"
                  className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-4 px-6 py-5">
                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Name
                  </label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Finance Data Guardrails"
                    required
                    className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Description
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="What is this policy for?"
                    rows={2}
                    className="mt-1.5 w-full resize-none rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    Blocked SQL keywords — optional
                  </label>
                  <input
                    value={keywords}
                    onChange={(e) => setKeywords(e.target.value)}
                    placeholder="e.g. internal_payroll, ssn"
                    className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                  />
                  <p className="mt-1 font-mono text-[10.5px] text-[var(--l-charcoal)]/45">
                    comma-separated — the only rule type the engine actually enforces today
                  </p>
                </div>

                {error && <p className="text-[12.5px] font-medium text-[var(--l-orange-deep)]">{error}</p>}
              </div>

              <div className="flex items-center justify-end gap-2 border-t-2 border-dashed border-[var(--l-ink)]/15 px-6 py-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-full px-4 py-2 text-sm font-semibold text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
                >
                  Cancel
                </button>
                <motion.button
                  type="submit"
                  disabled={!name.trim() || busy}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="flex items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 py-2 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--l-orange-deep)] disabled:opacity-40"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldPlus className="h-4 w-4" />}
                  {busy ? "Writing…" : "Create policy"}
                </motion.button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
