"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Check, Loader2, X } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { PASSWORD_REQUIREMENTS, isPasswordValid } from "@/lib/password-policy";

/**
 * Where a password-reset email link lands. `/auth/callback` has already
 * exchanged the emailed code for a real (if short-lived) session by the
 * time this page renders — that recovery session is what makes
 * `supabase.auth.updateUser({ password })` work here, the same call
 * `ChangePasswordCard` uses when you already know your password. There is
 * no separate "verify the code" step because that already happened.
 *
 * Signs the user out after a successful change and sends them back to
 * `/login` to sign in fresh, rather than dropping them straight into the
 * console on a recovery session — changing a password is exactly the
 * moment to make sure the *next* sign-in is a deliberate one.
 */
export default function ResetPasswordPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [hasSession, setHasSession] = useState(false);
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      setHasSession(data.session !== null);
      setChecking(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const nextOk = isPasswordValid(next);
  const matches = next.length > 0 && next === confirm;
  const canSubmit = nextOk && matches && !busy;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setError("");
    try {
      const supabase = createClient();
      const { error: updateError } = await supabase.auth.updateUser({ password: next });
      if (updateError) {
        setError(updateError.message || "Could not update the password.");
        return;
      }
      await supabase.auth.signOut();
      router.push("/login?message=password_reset_success");
    } catch {
      setError("Could not reach the sign-in service. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-[var(--l-yellow)] text-[var(--l-ink)] p-4 overflow-hidden">
      <div className="landing-blob landing-blob-animate pointer-events-none absolute -top-40 -left-40 w-[520px] h-[520px] bg-[var(--l-yellow-deep)] opacity-70" />
      <div className="landing-blob landing-blob-animate pointer-events-none absolute -bottom-48 -right-40 w-[480px] h-[480px] bg-[var(--l-orange)] opacity-20" />
      <div className="landing-blob landing-blob-animate pointer-events-none absolute top-1/3 -right-24 w-[300px] h-[300px] bg-[var(--l-teal)] opacity-15" />
      <div className="landing-noise absolute inset-0 pointer-events-none" />

      <Link
        href="/login"
        className="absolute top-6 left-6 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--l-ink)]/70 hover:text-[var(--l-ink)] transition-colors z-10"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to sign in
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative w-full max-w-[400px]"
      >
        <div className="rounded-[32px] bg-white shadow-2xl shadow-black/10 p-8">
          <div className="flex flex-col items-center mb-7 text-center">
            <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold mb-3">
              GovernAI
            </span>
            <h1 className="landing-display text-2xl text-[var(--l-charcoal)] leading-none">
              Set a new password
            </h1>
            {!checking && hasSession && (
              <p className="text-sm text-[var(--l-charcoal)]/55 mt-2.5">
                Choose a new password for your account.
              </p>
            )}
          </div>

          {checking ? (
            <div className="flex justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-[var(--l-charcoal)]/40" />
            </div>
          ) : !hasSession ? (
            <div className="space-y-4">
              <div className="p-3 rounded-xl bg-[#e07a6b]/10 border border-[#e07a6b]/25 text-[#c14a38] text-sm">
                This reset link is invalid or has expired. Request a new one from the sign-in page.
              </div>
              <Link
                href="/login"
                className="group w-full inline-flex items-center justify-center gap-2 py-2.5 bg-[var(--l-orange)] text-white font-semibold rounded-full text-sm shadow-[0_5px_0_0_var(--l-orange-deep)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)] transition-transform"
              >
                Back to sign in
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--l-charcoal)]/80">
                  New password
                </label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={next}
                  onChange={(e) => setNext(e.target.value)}
                  className="w-full bg-[var(--l-cream)] border border-[var(--l-line)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--l-charcoal)] focus:outline-none focus:border-[var(--l-orange)] focus:ring-2 focus:ring-[var(--l-orange)]/20 transition-colors"
                  required
                  autoFocus
                />
                <AnimatePresence>
                  {next.length > 0 && (
                    <motion.ul
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden space-y-1 pt-1"
                    >
                      {PASSWORD_REQUIREMENTS.map((req) => {
                        const met = req.test(next);
                        return (
                          <li
                            key={req.id}
                            className="flex items-center gap-1.5 text-[12px]"
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

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--l-charcoal)]/80">
                  Confirm new password
                </label>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className="w-full bg-[var(--l-cream)] border border-[var(--l-line)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--l-charcoal)] focus:outline-none focus:border-[var(--l-orange)] focus:ring-2 focus:ring-[var(--l-orange)]/20 transition-colors"
                  required
                />
                {confirm.length > 0 && !matches && (
                  <p className="text-[12.5px] text-[var(--l-orange-deep)]">
                    Passwords don&apos;t match.
                  </p>
                )}
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-[#e07a6b]/10 border border-[#e07a6b]/25 text-[#c14a38] text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={!canSubmit}
                className="group w-full mt-2 inline-flex items-center justify-center gap-2 py-2.5 bg-[var(--l-orange)] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-full text-sm shadow-[0_5px_0_0_var(--l-orange-deep)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)] transition-transform"
              >
                {busy ? "Updating..." : "Update password"}
                {!busy && (
                  <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
                )}
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-[var(--l-ink)]/45">
          Deloitte Capstone 2026 · Team Fennec
        </p>
      </motion.div>
    </div>
  );
}
