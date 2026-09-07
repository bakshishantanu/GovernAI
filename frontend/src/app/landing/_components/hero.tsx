"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { ArrowRight, ShieldCheck, Wallet } from "lucide-react";

export function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });

  const blobY = useTransform(scrollYProgress, [0, 1], [0, 160]);
  const cardY = useTransform(scrollYProgress, [0, 1], [0, 120]);
  const cardRotate = useTransform(scrollYProgress, [0, 1], [-8, -2]);
  const contentOpacity = useTransform(scrollYProgress, [0, 0.75], [1, 0]);
  const contentY = useTransform(scrollYProgress, [0, 1], [0, 60]);

  return (
    <section
      id="hero"
      ref={ref}
      className="relative min-h-[100svh] flex flex-col overflow-hidden bg-[var(--l-yellow)] text-[var(--l-ink)]"
    >
      {/* organic background blobs, Aardvark-style */}
      <motion.div
        style={{ y: blobY }}
        className="landing-blob pointer-events-none absolute -top-24 -left-40 w-[600px] h-[600px] bg-[var(--l-yellow-deep)] opacity-70"
      />
      <motion.div
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, -100]) }}
        className="landing-blob pointer-events-none absolute top-1/4 -right-52 w-[520px] h-[520px] bg-[var(--l-orange)] opacity-25"
      />
      <motion.div
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, 80]) }}
        className="landing-blob pointer-events-none absolute bottom-0 left-1/3 w-[380px] h-[380px] bg-[var(--l-teal)] opacity-20"
      />

      <div className="relative z-10 max-w-6xl mx-auto px-6 pt-32 md:pt-36 pb-16 flex-1 grid md:grid-cols-[1.15fr_0.85fr] gap-10 items-center w-full">
        <motion.div
          style={{ opacity: contentOpacity, y: contentY }}
        >
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="inline-flex items-center gap-2 self-start rounded-full bg-[var(--l-cream)] px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.1em] text-[var(--l-ink)] mb-8 shadow-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--l-orange)] animate-pulse" />
            Deloitte Capstone 2026 · Team Fennec
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="landing-display text-[15vw] sm:text-6xl md:text-[5.2rem] leading-[0.94] tracking-tight"
          >
            Build agents
            <br />
            fast. <span className="text-[var(--l-orange)]">Govern</span>
            <br />
            them faster.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.35 }}
            className="mt-7 max-w-md text-lg text-[var(--l-ink)]/70 leading-relaxed"
          >
            GovernAI assembles internal AI agents from reusable skills — and
            gives every one an identity, a permission scope, and a live
            spending budget the moment it&apos;s born.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.5 }}
            className="mt-9 flex flex-wrap items-center gap-4"
          >
            <a
              href="/login"
              className="group inline-flex items-center gap-2 rounded-full bg-[var(--l-orange)] text-white font-semibold px-6 py-3.5 shadow-[0_8px_0_0_var(--l-orange-deep)] transition-transform hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_4px_0_0_var(--l-orange-deep)]"
            >
              Log-in / Sign-up now
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </a>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-full bg-[var(--l-cream)]/70 backdrop-blur px-6 py-3.5 font-medium text-[var(--l-ink)] hover:bg-[var(--l-cream)] transition-colors"
            >
              See how it works
            </a>
          </motion.div>
        </motion.div>

        {/* tilted passport-card visual, echoing the tilted book covers */}
        <motion.div
          style={{ y: cardY, rotate: cardRotate }}
          initial={{ opacity: 0, x: 30, rotate: -14 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
          className="relative hidden md:block"
        >
          <div className="rounded-[28px] bg-[var(--l-navy-deep)] text-[var(--l-ink,#fff)] p-6 shadow-2xl shadow-black/30 border border-white/10 rotate-[-6deg]">
            <div className="flex items-center justify-between text-[var(--l-cream)]">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-[var(--l-orange-soft)]">
                <ShieldCheck className="w-3.5 h-3.5" />
                Agent Passport
              </div>
              <span className="text-[10px] font-mono text-white/40">#AG-8841</span>
            </div>
            <div className="mt-5 text-xl font-semibold text-[var(--l-cream)]">
              Invoice Triage Bot
            </div>
            <div className="mt-5 flex items-center gap-2.5 rounded-xl bg-white/[0.06] border border-white/10 px-4 py-3">
              <Wallet className="w-4 h-4 text-[var(--l-teal-soft)]" />
              <div className="flex-1">
                <div className="text-[10px] uppercase tracking-wide text-white/40">
                  Live budget
                </div>
                <div className="text-sm font-mono text-[var(--l-cream)]">
                  $18.20 / $25.00
                </div>
              </div>
              <span className="w-2 h-2 rounded-full bg-[var(--l-teal-soft)] animate-pulse" />
            </div>
          </div>

          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.5 }}
            className="landing-hand absolute -bottom-8 -left-10 text-2xl text-[var(--l-ink)] rotate-[-4deg]"
          >
            auto-paused if it overspends →
          </motion.span>
        </motion.div>
      </div>
    </section>
  );
}
