"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { login, signup } from "../auth/actions";
import { ArrowLeft, ArrowRight, Check, X } from "lucide-react";
import { PASSWORD_REQUIREMENTS, isPasswordValid } from "@/lib/password-policy";
import { createClient } from "@/lib/supabase/client";

// lucide-react dropped brand icons (Github included) from this major version
// — inlined here rather than pulling in a whole extra icon package for one glyph.
function GithubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.09 3.29 9.4 7.86 10.93.58.1.79-.25.79-.56 0-.27-.01-1.16-.02-2.11-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.75 2.69 1.25 3.34.96.1-.75.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.05 0 0 .96-.31 3.15 1.18a10.9 10.9 0 0 1 2.87-.39c.97.01 1.95.13 2.87.39 2.19-1.49 3.15-1.18 3.15-1.18.62 1.59.23 2.76.11 3.05.73.8 1.18 1.83 1.18 3.08 0 4.41-2.69 5.38-5.25 5.67.41.36.78 1.06.78 2.14 0 1.55-.01 2.79-.01 3.17 0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5z" />
    </svg>
  );
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      <path
        fill="#FFC107"
        d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
      />
      <path
        fill="#FF3D00"
        d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
      />
      <path
        fill="#1976D2"
        d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"
      />
    </svg>
  );
}

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [oauthPending, setOauthPending] = useState<"google" | "github" | null>(null);

  const handleOAuth = async (provider: "google" | "github") => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setOauthPending(provider);

    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        // Lands on the existing PKCE-exchange route, which already redirects
        // into the app on success — same landing spot a password login uses.
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    // A successful call navigates the browser away to the provider's consent
    // screen itself; we only ever reach this line on a real failure (e.g.
    // the provider isn't enabled on the Supabase project yet).
    if (error) {
      setErrorMessage(error.message);
      setOauthPending(null);
    }
  };

  // Only the signup form gates on this — logging in checks a password
  // against what an account already has, it never re-validates its shape.
  const passwordOk = isLogin || isPasswordValid(password);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!isLogin && !passwordOk) {
      setErrorMessage("Password does not meet the requirements below.");
      return;
    }

    // Captured now, not read later: React nulls a pooled SyntheticEvent's
    // fields once the handler that received it returns, and this handler
    // returns immediately (startTransition's callback runs after an await).
    // Reading `e.currentTarget` after that await crashed with "Cannot read
    // properties of null" on a real successful signup — the plain element
    // reference below survives the await instead.
    const form = e.currentTarget;
    const formData = new FormData(form);

    startTransition(async () => {
      if (isLogin) {
        const res = await login(formData);
        if (res?.error) {
          setErrorMessage(res.error);
        }
      } else {
        const res = await signup(formData);
        if (res?.error) {
          setErrorMessage(res.error);
        } else if (res?.success) {
          setSuccessMessage(res.success);
          form.reset();
          setPassword("");
        }
      }
    });
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-[var(--l-yellow)] text-[var(--l-ink)] p-4 overflow-hidden">
      <div className="landing-blob landing-blob-animate pointer-events-none absolute -top-40 -left-40 w-[520px] h-[520px] bg-[var(--l-yellow-deep)] opacity-70" />
      <div className="landing-blob landing-blob-animate pointer-events-none absolute -bottom-48 -right-40 w-[480px] h-[480px] bg-[var(--l-orange)] opacity-20" />
      <div className="landing-blob landing-blob-animate pointer-events-none absolute top-1/3 -right-24 w-[300px] h-[300px] bg-[var(--l-teal)] opacity-15" />
      <div className="landing-noise absolute inset-0 pointer-events-none" />

      <Link
        href="/landing"
        className="absolute top-6 left-6 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--l-ink)]/70 hover:text-[var(--l-ink)] transition-colors z-10"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to GovernAI
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
              {isLogin ? "Sign in to GovernAI" : "Create an account"}
            </h1>
            <p className="text-sm text-[var(--l-charcoal)]/55 mt-2.5">
              {isLogin
                ? "Enter your details to proceed."
                : "Sign up to start managing agents."}
            </p>
          </div>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-xl bg-[#e07a6b]/10 border border-[#e07a6b]/25 text-[#c14a38] text-sm">
              {errorMessage}
            </div>
          )}

          {successMessage && (
            <div className="mb-4 p-3 rounded-xl bg-[var(--l-teal)]/10 border border-[var(--l-teal)]/25 text-[var(--l-teal)] text-sm">
              {successMessage}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--l-charcoal)]/80">
                  Name
                </label>
                <input
                  type="text"
                  name="full_name"
                  className="w-full bg-[var(--l-cream)] border border-[var(--l-line)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--l-charcoal)] placeholder-[var(--l-charcoal)]/35 focus:outline-none focus:border-[var(--l-orange)] focus:ring-2 focus:ring-[var(--l-orange)]/20 transition-colors"
                  required={!isLogin}
                />
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--l-charcoal)]/80">
                Email
              </label>
              <input
                type="email"
                name="email"
                placeholder="name@company.com"
                className="w-full bg-[var(--l-cream)] border border-[var(--l-line)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--l-charcoal)] placeholder-[var(--l-charcoal)]/35 focus:outline-none focus:border-[var(--l-orange)] focus:ring-2 focus:ring-[var(--l-orange)]/20 transition-colors"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--l-charcoal)]/80">
                Password
              </label>
              <input
                type="password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[var(--l-cream)] border border-[var(--l-line)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--l-charcoal)] focus:outline-none focus:border-[var(--l-orange)] focus:ring-2 focus:ring-[var(--l-orange)]/20 transition-colors"
                required
              />

              <AnimatePresence>
                {!isLogin && password.length > 0 && (
                  <motion.ul
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden space-y-1 pt-1"
                  >
                    {PASSWORD_REQUIREMENTS.map((req) => {
                      const met = req.test(password);
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

            <button
              type="submit"
              disabled={isPending || !passwordOk}
              className="group w-full mt-2 inline-flex items-center justify-center gap-2 py-2.5 bg-[var(--l-orange)] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-full text-sm shadow-[0_5px_0_0_var(--l-orange-deep)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)] transition-transform"
            >
              {isPending ? "Please wait..." : isLogin ? "Sign in" : "Sign up"}
              {!isPending && (
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              )}
            </button>
          </form>

          <div className="flex items-center gap-3 mt-5">
            <div className="h-px flex-1 bg-[var(--l-line)]" />
            <span className="text-xs text-[var(--l-charcoal)]/45">or continue with</span>
            <div className="h-px flex-1 bg-[var(--l-line)]" />
          </div>

          <div className="grid grid-cols-2 gap-3 mt-4">
            <button
              type="button"
              onClick={() => handleOAuth("google")}
              disabled={isPending || oauthPending !== null}
              className="inline-flex items-center justify-center gap-2 py-2.5 rounded-xl border border-[var(--l-line)] bg-[var(--l-cream)] text-sm font-medium text-[var(--l-charcoal)] hover:bg-[var(--l-cream-deep)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <GoogleIcon className="w-4 h-4" />
              {oauthPending === "google" ? "Redirecting..." : "Google"}
            </button>
            <button
              type="button"
              onClick={() => handleOAuth("github")}
              disabled={isPending || oauthPending !== null}
              className="inline-flex items-center justify-center gap-2 py-2.5 rounded-xl border border-[var(--l-line)] bg-[var(--l-cream)] text-sm font-medium text-[var(--l-charcoal)] hover:bg-[var(--l-cream-deep)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <GithubIcon className="w-4 h-4" />
              {oauthPending === "github" ? "Redirecting..." : "GitHub"}
            </button>
          </div>

          <div className="text-center text-sm mt-5">
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin);
                setErrorMessage(null);
                setSuccessMessage(null);
                setPassword("");
              }}
              className="text-[var(--l-charcoal)]/55 hover:text-[var(--l-orange)] transition-colors"
            >
              {isLogin
                ? "Don't have an account? Sign up"
                : "Already have an account? Sign in"}
            </button>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-[var(--l-ink)]/45">
          Deloitte Capstone 2026 · Team Fennec
        </p>
      </motion.div>
    </div>
  );
}
