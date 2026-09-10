"use client";

import { useState, useTransition, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { login, signup, signInWithOAuth } from "../auth/actions";
import { ArrowLeft, ArrowRight } from "lucide-react";

function GoogleIcon() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 24 24">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

function LoginForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState<"google" | "github" | null>(null);
  const [isPending, startTransition] = useTransition();

  const searchParams = useSearchParams();

  useEffect(() => {
    const error = searchParams.get("error");
    if (error === "auth_callback_failed") {
      setErrorMessage("Authentication failed or was cancelled. Please try again.");
    } else if (error) {
      setErrorMessage(`Authentication error: ${error}`);
    }
  }, [searchParams]);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const formData = new FormData(e.currentTarget);

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
          e.currentTarget.reset();
        }
      }
    });
  };

  const handleOAuth = (provider: "google" | "github") => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setOauthLoading(provider);

    startTransition(async () => {
      const res = await signInWithOAuth(provider);
      if (res?.error) {
        setErrorMessage(res.error);
        setOauthLoading(null);
      }
    });
  };

  const isAnyLoading = isPending || oauthLoading !== null;

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
                className="w-full bg-[var(--l-cream)] border border-[var(--l-line)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--l-charcoal)] focus:outline-none focus:border-[var(--l-orange)] focus:ring-2 focus:ring-[var(--l-orange)]/20 transition-colors"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isAnyLoading}
              className="group w-full mt-2 inline-flex items-center justify-center gap-2 py-2.5 bg-[var(--l-orange)] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-full text-sm shadow-[0_5px_0_0_var(--l-orange-deep)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)] transition-transform"
            >
              {isPending ? "Please wait..." : isLogin ? "Sign in" : "Sign up"}
              {!isPending && (
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              )}
            </button>
          </form>

          {/* Social OAuth Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--l-line)]" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-3 text-[var(--l-charcoal)]/45 font-medium tracking-wider">
                or continue with
              </span>
            </div>
          </div>

          {/* Social OAuth Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleOAuth("google")}
              disabled={isAnyLoading}
              className="flex items-center justify-center gap-2 py-2.5 px-4 bg-[var(--l-cream)] hover:bg-[#ede9de] border border-[var(--l-line)] rounded-2xl text-xs font-semibold text-[var(--l-charcoal)] transition-all hover:shadow-sm active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {oauthLoading === "google" ? (
                <span className="inline-block w-4 h-4 border-2 border-[var(--l-charcoal)]/30 border-t-[var(--l-charcoal)] rounded-full animate-spin" />
              ) : (
                <GoogleIcon />
              )}
              <span>Google</span>
            </button>

            <button
              type="button"
              onClick={() => handleOAuth("github")}
              disabled={isAnyLoading}
              className="flex items-center justify-center gap-2 py-2.5 px-4 bg-[var(--l-cream)] hover:bg-[#ede9de] border border-[var(--l-line)] rounded-2xl text-xs font-semibold text-[var(--l-charcoal)] transition-all hover:shadow-sm active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {oauthLoading === "github" ? (
                <span className="inline-block w-4 h-4 border-2 border-[var(--l-charcoal)]/30 border-t-[var(--l-charcoal)] rounded-full animate-spin" />
              ) : (
                <GithubIcon />
              )}
              <span>GitHub</span>
            </button>
          </div>

          <div className="text-center text-sm mt-6">
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin);
                setErrorMessage(null);
                setSuccessMessage(null);
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

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
