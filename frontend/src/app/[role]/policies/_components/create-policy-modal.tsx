"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ShieldPlus, Loader2 } from "lucide-react";
import { fetchApi } from "@/lib/api-client";

/**
 * Offers only rule types that are both accepted by the API
 * (api/schemas/policy.py's RuleType) and actually enforced by the engine
 * (domain/policies/engine.py): a deny list and a rate limit. Letting someone
 * build a policy out of rule types that change nothing would be a worse UI
 * lie than not offering them at all.
 *
 * `sql_blocklist` used to be the only option here, but the engine applies it
 * to the `sql_query` tool alone, which no longer exists. The Solr keyword
 * blocklist and brand-colour check are enforced but the API does not accept
 * them yet, so they cannot be offered until the shared schema allows them.
 */
type RuleKind = "none" | "deny_list" | "rate_limit";

const RULE_KINDS: { kind: RuleKind; label: string; hint: string }[] = [
  { kind: "none", label: "No rule yet", hint: "create the policy empty and add rules later" },
  { kind: "deny_list", label: "Deny list", hint: "block tools, or any call mentioning certain words" },
  { kind: "rate_limit", label: "Rate limit", hint: "cap how many tool calls an agent makes per minute" },
];

function splitList(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

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
  const [ruleKind, setRuleKind] = useState<RuleKind>("none");
  const [blockedTools, setBlockedTools] = useState("");
  const [blockedWords, setBlockedWords] = useState("");
  const [maxCalls, setMaxCalls] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) {
      setName("");
      setDescription("");
      setRuleKind("none");
      setBlockedTools("");
      setBlockedWords("");
      setMaxCalls("");
      setError("");
    }
  }, [open]);

  /** The rule to send, or an error message saying what is missing. */
  function buildRule(): { rule: object | null } | { problem: string } {
    if (ruleKind === "deny_list") {
      const tools = splitList(blockedTools);
      const words = splitList(blockedWords);
      if (!tools.length && !words.length) {
        return { problem: "A deny list needs at least one tool or one word to block." };
      }
      const config: Record<string, string[]> = {};
      if (tools.length) config.blocked_tools = tools;
      if (words.length) config.blocked_args = words;
      return {
        rule: { name: "Deny list", rule_type: "DENY_LIST", config, priority: 10, enabled: true },
      };
    }
    if (ruleKind === "rate_limit") {
      const max = Number(maxCalls);
      if (!Number.isInteger(max) || max < 1) {
        return { problem: "Enter a whole number of tool calls per minute, 1 or more." };
      }
      return {
        rule: {
          name: "Rate limit",
          rule_type: "RATE_LIMIT",
          config: { max_calls_per_minute: max },
          priority: 10,
          enabled: true,
        },
      };
    }
    return { rule: null };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    const built = buildRule();
    if ("problem" in built) {
      setError(built.problem);
      return;
    }

    setBusy(true);
    setError("");

    try {
      await fetchApi("/policies/", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          enabled: true,
          rules: built.rule ? [built.rule] : [],
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
                  <span className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                    First rule
                  </span>
                  <div role="radiogroup" aria-label="First rule" className="mt-1.5 grid grid-cols-3 gap-1.5">
                    {RULE_KINDS.map((option) => {
                      const selected = ruleKind === option.kind;
                      return (
                        <button
                          key={option.kind}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          onClick={() => {
                            setRuleKind(option.kind);
                            setError("");
                          }}
                          className={`rounded-xl border-2 px-2 py-2 text-[12.5px] font-semibold transition-colors ${
                            selected
                              ? "border-[var(--l-orange)] bg-[var(--l-orange)]/10 text-[var(--l-ink)]"
                              : "border-[var(--l-ink)]/15 text-[var(--l-charcoal)]/70 hover:text-[var(--l-ink)]"
                          }`}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-1 font-mono text-[10.5px] text-[var(--l-charcoal)]/45">
                    {RULE_KINDS.find((option) => option.kind === ruleKind)?.hint}
                  </p>
                </div>

                {ruleKind === "deny_list" && (
                  <div className="space-y-3">
                    <div>
                      <label
                        htmlFor="policy-blocked-tools"
                        className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50"
                      >
                        Tools to block
                      </label>
                      <input
                        id="policy-blocked-tools"
                        value={blockedTools}
                        onChange={(e) => setBlockedTools(e.target.value)}
                        placeholder="e.g. search_tickets, search_solr"
                        className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="policy-blocked-words"
                        className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50"
                      >
                        Words to block in a call
                      </label>
                      <input
                        id="policy-blocked-words"
                        value={blockedWords}
                        onChange={(e) => setBlockedWords(e.target.value)}
                        placeholder="e.g. payroll, ssn"
                        className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                      />
                    </div>
                    <p className="font-mono text-[10.5px] text-[var(--l-charcoal)]/45">
                      comma-separated · both filled: block those tools only when a word appears · words only: block any tool call mentioning them
                    </p>
                  </div>
                )}

                {ruleKind === "rate_limit" && (
                  <div>
                    <label
                      htmlFor="policy-max-calls"
                      className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50"
                    >
                      Max tool calls per minute
                    </label>
                    <input
                      id="policy-max-calls"
                      type="number"
                      min={1}
                      step={1}
                      inputMode="numeric"
                      value={maxCalls}
                      onChange={(e) => setMaxCalls(e.target.value)}
                      placeholder="e.g. 5"
                      className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
                    />
                    <p className="mt-1 font-mono text-[10.5px] text-[var(--l-charcoal)]/45">
                      per agent · denied attempts count too, so a blocked agent can&apos;t hammer through
                    </p>
                  </div>
                )}

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
