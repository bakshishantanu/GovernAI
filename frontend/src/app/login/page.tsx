"use client";

import { useState, useTransition } from "react";
import { login, signup } from "../auth/actions";
import { ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

/**
 * Sign in / sign up, per design/governai-pro.
 *
 * The page is the yellow field, and the form is one paper panel sitting on it
 * — the same panel-on-field relationship the console uses, so the product
 * looks like itself before you are even authenticated.
 *
 * Only the styling changed here: the server actions, the login/signup toggle
 * and the pending state are the ones that were already working.
 */

const FIELD =
  "h-11 w-full rounded-xl border-2 border-border bg-gv-row px-3.5 text-[14px] font-bold text-foreground placeholder:font-bold placeholder:text-gv-muted focus:outline-none focus:ring-2 focus:ring-gv-pink focus:ring-offset-2 focus:ring-offset-card";

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
    const form = e.currentTarget;

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
        }
      }
    });
  };

  return (
    <div className="gv-field relative flex min-h-screen flex-col items-center justify-center p-4">
      <div className="absolute right-5 top-5">
        <ThemeToggle />
      </div>

      <div className="flex w-full max-w-[400px] flex-col gap-5">
        {/* wordmark — the one place Bungee appears on this page besides the title */}
        <div className="flex items-center gap-3">
          <span className="gv-card flex h-11 w-11 items-center justify-center rounded-xl border-2 border-border bg-gv-teal">
            <ShieldCheck className="h-[22px] w-[22px] text-gv-ink" strokeWidth={2.4} />
          </span>
          <span className="font-display text-[26px] leading-none text-gv-ink">
            GovernAI
          </span>
        </div>

        <div className="gv-panel rounded-lg border-2 border-border bg-card">
          <div className="border-b-2 border-border px-6 py-5">
            <h1 className="font-display text-[24px] leading-none text-foreground">
              {isLogin ? "Sign in" : "Create account"}
            </h1>
            <p className="mt-2 text-[13px] font-bold text-gv-muted">
              {isLogin
                ? "Every agent you run is governed and costed."
                : "Set up an account to start building governed agents."}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-5">
            {(errorMessage || successMessage) && (
              <div
                role="status"
                aria-live="polite"
                className={`gv-chip rounded-xl border-2 border-border px-3.5 py-2.5 text-[12.5px] font-extrabold ${
                  errorMessage
                    ? "bg-gv-held text-gv-held-fg"
                    : "bg-gv-cleared text-gv-cleared-fg"
                }`}
              >
                {errorMessage ?? successMessage}
              </div>
            )}

            {!isLogin && (
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="full_name"
                  className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-gv-label"
                >
                  Name
                </label>
                <input
                  id="full_name"
                  type="text"
                  name="full_name"
                  autoComplete="name"
                  className={FIELD}
                  required={!isLogin}
                />
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="email"
                className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-gv-label"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                name="email"
                placeholder="name@company.com"
                autoComplete="email"
                className={FIELD}
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="password"
                className="text-[11px] font-extrabold uppercase tracking-[0.08em] text-gv-label"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                name="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
                className={FIELD}
                required
              />
            </div>

            <button
              type="submit"
              disabled={isPending}
              className="gv-card mt-1 inline-flex h-11 w-full items-center justify-center rounded-xl border-2 border-border bg-gv-teal text-[14px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px disabled:opacity-60"
            >
              {isPending ? "Please wait…" : isLogin ? "Sign in" : "Sign up"}
            </button>
          </form>
        </div>

        <button
          type="button"
          onClick={() => {
            setIsLogin(!isLogin);
            setErrorMessage(null);
            setSuccessMessage(null);
          }}
          className="self-center text-[13px] font-bold text-gv-onyellow underline decoration-2 underline-offset-4"
        >
          {isLogin
            ? "Don't have an account? Sign up"
            : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
