"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck } from "lucide-react";

export function FinalCta() {
  return (
    <section className="relative bg-[var(--l-navy-deep)] text-[var(--l-cream)] overflow-hidden">
      <div className="landing-noise absolute inset-0 pointer-events-none" />
      <motion.div
        aria-hidden
        animate={{ rotate: 360 }}
        transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
        className="pointer-events-none absolute -bottom-56 left-1/2 -translate-x-1/2 w-[720px] h-[720px] rounded-full opacity-[0.12]"
        style={{
          background:
            "conic-gradient(from 0deg, var(--l-orange), var(--l-teal), var(--l-orange))",
        }}
      />

      <div className="relative max-w-3xl mx-auto px-6 py-32 md:py-44 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 0.5 }}
          className="mx-auto mb-8 w-12 h-12 rounded-2xl bg-[var(--l-orange)]/15 border border-[var(--l-orange)]/30 flex items-center justify-center"
        >
          <ShieldCheck className="w-6 h-6 text-[var(--l-orange)]" />
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="landing-display text-5xl md:text-7xl tracking-tight leading-[0.98]"
        >
          Ready to govern
          <br />
          your agents?
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-5 text-[var(--l-cream)]/60 max-w-md mx-auto"
        >
          Sign in to build your first agent, or create an account for your team in
          under a minute.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
        >
          <Link
            href="/login"
            className="group inline-flex items-center gap-2 rounded-full bg-[var(--l-orange)] text-white font-semibold px-7 py-3.5 shadow-[0_6px_0_0_var(--l-orange-deep)] transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)]"
          >
            Sign in to GovernAI
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-full border border-[var(--l-line-dark)] px-7 py-3.5 font-medium hover:border-[var(--l-orange-soft)] hover:text-[var(--l-orange-soft)] transition-colors"
          >
            Create an account
          </Link>
        </motion.div>
      </div>

      <div className="relative border-t border-[var(--l-line-dark)]">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[var(--l-cream)]/40">
          <span>© {new Date().getFullYear()} GovernAI · Team Fennec</span>
          <span>Deloitte Capstone Program 2026 · Manipal University Jaipur</span>
        </div>
      </div>
    </section>
  );
}
