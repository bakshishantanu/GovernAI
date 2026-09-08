"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

export function OwnerCta() {
  return (
    <section className="relative bg-[var(--l-yellow)] py-28 md:py-36 overflow-hidden">
      <div
        aria-hidden
        className="landing-blob absolute -left-32 -bottom-32 h-[28rem] w-[28rem] bg-[var(--l-yellow-deep)] opacity-60"
      />

      <div className="relative max-w-3xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="landing-display text-4xl md:text-6xl leading-[1.03] text-[var(--l-ink)]">
            Find out what your
            <br />
            agents cost today.
          </h2>
          <p className="mt-6 text-lg text-[var(--l-ink)]/75 max-w-xl mx-auto leading-relaxed">
            Point GovernAI at the agents you already run. The board fills in
            with owners, scopes and live spend — before you decide to change a
            single thing about how they work.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/login"
              className="group inline-flex items-center gap-2 rounded-full bg-[var(--l-orange)] px-7 py-3.5 font-semibold text-white shadow-[0_6px_0_0_var(--l-orange-deep)] transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)]"
            >
              See the board
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>

            <Link
              href="/landing"
              className="inline-flex items-center gap-2 rounded-full border-2 border-[var(--l-ink)]/25 px-7 py-3.5 font-semibold text-[var(--l-ink)] transition-colors hover:border-[var(--l-ink)]/60"
            >
              How the rest of it works
            </Link>
          </div>

          <p className="landing-hand mt-10 text-xl text-[var(--l-ink)]/60">
            no agent starts governed by accident
          </p>
        </motion.div>
      </div>
    </section>
  );
}
