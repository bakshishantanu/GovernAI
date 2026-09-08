"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

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
        <motion.span
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 0.5 }}
          className="inline-block text-xs uppercase tracking-[0.14em] text-[var(--l-orange-soft)] font-semibold mb-6"
        >
          GovernAI
        </motion.span>

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
