"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { login, signup } from "../auth/actions";
import { ShieldCheck, ArrowLeft, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

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

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-[var(--l-yellow)] text-[var(--l-ink)] p-4 overflow-hidden">
      <div className="landing-blob pointer-events-none absolute -top-40 -left-40 w-[520px] h-[520px] bg-[var(--l-yellow-deep)] opacity-70" />
      <div className="landing-blob pointer-events-none absolute -bottom-48 -right-40 w-[480px] h-[480px] bg-[var(--l-orange)] opacity-20" />
      <div className="landing-blob pointer-events-none absolute top-1/3 -right-24 w-[300px] h-[300px] bg-[var(--l-teal)] opacity-15" />
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
            <div className="w-11 h-11 rounded-2xl bg-[var(--l-orange)]/10 border border-[var(--l-orange)]/25 flex items-center justify-center mb-4">
              <ShieldCheck className="w-5 h-5 text-[var(--l-orange)]" />
            </div>
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
              disabled={isPending}
              className="group w-full mt-2 inline-flex items-center justify-center gap-2 py-2.5 bg-[var(--l-orange)] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-full text-sm shadow-[0_5px_0_0_var(--l-orange-deep)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)] transition-transform"
            >
              {isPending ? "Please wait..." : isLogin ? "Sign in" : "Sign up"}
              {!isPending && (
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              )}
            </button>
          </form>

          <div className="text-center text-sm mt-5">
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
