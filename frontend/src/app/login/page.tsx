"use client";

import { useState, useTransition } from "react";
import { login, signup } from "../auth/actions";
import { Shield } from "lucide-react";

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
    <div className="min-h-screen flex flex-col justify-center items-center bg-[#0a0a0a] text-slate-200 p-4 font-sans">
      <div className="w-full max-w-[380px] flex flex-col gap-6">
        
        <div className="flex flex-col items-center mb-2">
          <div className="h-10 w-10 bg-slate-900 border border-slate-800 rounded-md flex items-center justify-center mb-4">
            <Shield className="w-5 h-5 text-slate-100" />
          </div>
          <h1 className="text-xl font-medium text-white">
            {isLogin ? "Sign in to GovernAI" : "Create an account"}
          </h1>
          <p className="text-sm text-slate-400 mt-1.5">
            {isLogin ? "Enter your details to proceed." : "Sign up to start managing agents."}
          </p>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {errorMessage}
          </div>
        )}

        {successMessage && (
          <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-300">Name</label>
              <input
                type="text"
                name="full_name"
                className="w-full bg-[#111] border border-slate-800 rounded-md px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 transition-colors"
                required={!isLogin}
              />
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-300">Email</label>
            <input
              type="email"
              name="email"
              placeholder="name@company.com"
              className="w-full bg-[#111] border border-slate-800 rounded-md px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 transition-colors"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-300">Password</label>
            <input
              type="password"
              name="password"
              className="w-full bg-[#111] border border-slate-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 transition-colors"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isPending}
            className="w-full mt-2 py-2 bg-white hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed text-black font-medium rounded-md text-sm transition-colors"
          >
            {isPending ? "Please wait..." : isLogin ? "Sign in" : "Sign up"}
          </button>
        </form>

        <div className="text-center text-sm">
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setErrorMessage(null);
              setSuccessMessage(null);
            }}
            className="text-slate-400 hover:text-white transition-colors"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
