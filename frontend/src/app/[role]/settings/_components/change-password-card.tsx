"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, KeyRound, Loader2, X } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { SUPABASE_CONFIGURED } from "@/lib/api-client";
import { PASSWORD_REQUIREMENTS, isPasswordValid } from "@/lib/password-policy";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Change your own sign-in password. The one interactive form on an
 * otherwise read-only page (see the page's own docstring) — this is
 * genuinely a per-account action, not server configuration. Available to
 * every signed-in user regardless of role (admin or builder): the settings
 * page never gates this card on `role`, since it's per-account, not
 * per-permission.
 *
 * Goes straight to Supabase, not through the backend: there is no
 * password-change endpoint on this API, and there never should be one —
 * Supabase already owns credential storage, so re-implementing it here
 * would be a second, drifting copy of the same secret. Re-verifies the
 * current password first via `signInWithPassword` before calling
 * `updateUser`, rather than trusting the session alone: a session cookie
 * left open on a shared machine should not be enough on its own to change
 * the password that protects it.
 *
 * Sits behind a button + dialog rather than an always-open form, so the
 * settings page doesn't lead with three password fields before anyone has
 * asked to change anything.
 */
export function ChangePasswordCard({ email }: { email: string | null }) {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const nextOk = isPasswordValid(next);
  const matches = next.length > 0 && next === confirm;
  const canSubmit = current.length > 0 && nextOk && matches && !busy;

  function resetForm() {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError("");
    setDone(false);
    setBusy(false);
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (!nextOpen) resetForm();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || !email) return;
    setBusy(true);
    setError("");
    setDone(false);
    try {
      const supabase = createClient();

      // Re-authenticate with the current password first. A wrong current
      // password fails here, before anything is changed.
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password: current,
      });
      if (signInError) {
        setError("Current password is incorrect.");
        return;
      }

      const { error: updateError } = await supabase.auth.updateUser({ password: next });
      if (updateError) {
        setError(updateError.message || "Could not update the password.");
        return;
      }

      setDone(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch {
      setError("Could not reach the sign-in service. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.05 }}
      className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
    >
      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--l-charcoal)]/45">
        <KeyRound className="h-3 w-3" />
        Password
      </span>

      {!SUPABASE_CONFIGURED ? (
        <p className="mt-2 text-[12.5px] leading-relaxed text-[var(--l-charcoal)]/60">
          This session has no real Supabase account behind it (dev-token sign-in), so there is no
          password to change here.
        </p>
      ) : (
        <>
          <p className="mt-1.5 text-[12.5px] text-[var(--l-charcoal)]/60">
            Update the password you sign in with.
          </p>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-[var(--l-ink)] px-4 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_rgba(22,19,14,0.2)] transition-transform hover:-translate-y-0.5 active:translate-y-0"
          >
            <KeyRound className="h-3.5 w-3.5" />
            Change password
          </button>
        </>
      )}

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-[420px] bg-[var(--l-cream)] text-[var(--l-ink)]">
          <DialogHeader>
            <DialogTitle className="landing-display text-[var(--l-ink)]">
              Change password
            </DialogTitle>
            <DialogDescription className="text-[var(--l-charcoal)]/60">
              Enter your current password, then choose a new one.
            </DialogDescription>
          </DialogHeader>

          {done ? (
            <div className="space-y-4">
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-1.5 text-[13px] font-medium text-[var(--l-teal)]"
              >
                <Check className="h-4 w-4" />
                Password updated.
              </motion.p>
              <button
                type="button"
                onClick={() => handleOpenChange(false)}
                className="inline-flex items-center gap-1.5 rounded-full bg-[var(--l-ink)] px-4 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_rgba(22,19,14,0.2)]"
              >
                Done
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                  Current password
                </label>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={current}
                  onChange={(e) => setCurrent(e.target.value)}
                  required
                  autoFocus
                  className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2 text-sm text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                  New password
                </label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={next}
                  onChange={(e) => setNext(e.target.value)}
                  required
                  className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2 text-sm text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none"
                />
                <AnimatePresence>
                  {next.length > 0 && (
                    <motion.ul
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 overflow-hidden"
                    >
                      {PASSWORD_REQUIREMENTS.map((req) => {
                        const met = req.test(next);
                        return (
                          <li
                            key={req.id}
                            className="flex items-center gap-1.5 text-[11.5px]"
                            style={{ color: met ? "var(--l-teal)" : "var(--l-charcoal)" }}
                          >
                            {met ? (
                              <Check className="h-3 w-3 shrink-0" />
                            ) : (
                              <X className="h-3 w-3 shrink-0 opacity-40" />
                            )}
                            <span className={met ? "" : "opacity-60"}>{req.label}</span>
                          </li>
                        );
                      })}
                    </motion.ul>
                  )}
                </AnimatePresence>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
                  Confirm new password
                </label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream-deep)]/40 px-3.5 py-2 text-sm text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none"
                />
                {confirm.length > 0 && !matches && (
                  <p className="mt-1 text-[11.5px] text-[var(--l-orange-deep)]">
                    Passwords don&apos;t match.
                  </p>
                )}
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-[12.5px] font-medium text-[var(--l-orange-deep)]"
                >
                  {error}
                </motion.p>
              )}

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => handleOpenChange(false)}
                  disabled={busy}
                  className="rounded-full px-4 py-2 text-sm font-semibold text-[var(--l-charcoal)]/70 transition-colors hover:text-[var(--l-ink)] disabled:opacity-40"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!canSubmit}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[var(--l-ink)] px-4 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_rgba(22,19,14,0.2)] disabled:opacity-40"
                >
                  {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Update password
                </button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
