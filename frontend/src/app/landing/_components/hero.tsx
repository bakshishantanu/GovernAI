"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { ArrowRight, ChevronDown } from "lucide-react";

export function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });

  const blobY = useTransform(scrollYProgress, [0, 1], [0, 180]);
  const blobScale = useTransform(scrollYProgress, [0, 1], [1, 1.3]);
  const contentOpacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);
  const contentY = useTransform(scrollYProgress, [0, 1], [0, 80]);

  return (
    <section
      id="hero"
      ref={ref}
      className="relative min-h-[100svh] flex flex-col justify-between overflow-hidden bg-[var(--l-navy-deep)] text-[var(--l-ink)]"
    >
      {/* animated background blobs */}
      <motion.div
        style={{ y: blobY, scale: blobScale }}
        className="pointer-events-none absolute -top-40 -right-40 w-[560px] h-[560px] rounded-full blur-[110px] opacity-40"
      >
        <div className="w-full h-full rounded-full bg-[var(--l-orange)]" />
      </motion.div>
      <motion.div
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, -120]) }}
        className="pointer-events-none absolute top-1/3 -left-32 w-[420px] h-[420px] rounded-full blur-[100px] opacity-30"
      >
        <div className="w-full h-full rounded-full bg-[var(--l-teal)]" />
      </motion.div>
      <div className="landing-noise absolute inset-0 pointer-events-none" />

      <motion.div
        style={{ opacity: contentOpacity, y: contentY }}
        className="relative z-10 max-w-6xl mx-auto px-6 pt-40 pb-20 md:pt-48 flex-1 flex flex-col justify-center"
      >
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="inline-flex items-center gap-2 self-start rounded-full border border-[var(--l-line-dark)] px-3 py-1 text-xs uppercase tracking-[0.14em] text-[var(--l-orange-soft)] mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--l-orange)] animate-pulse" />
          Deloitte Capstone 2026 · Team Fennec
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-5xl md:text-7xl font-semibold tracking-tight leading-[1.02] max-w-4xl"
        >
          Build agents fast.
          <br />
          <span className="text-[var(--l-orange)]">Govern</span> them faster.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.35 }}
          className="mt-7 max-w-xl text-lg text-[var(--l-ink)]/70 leading-relaxed"
        >
          GovernAI is the platform that assembles internal AI agents from reusable
          skills — and gives every one of them an identity, a permission scope, and
          a live spending budget the moment it&apos;s born.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
          className="mt-10 flex flex-wrap items-center gap-4"
        >
          <a
            href="#how-it-works"
            className="group inline-flex items-center gap-2 rounded-full bg-[var(--l-orange)] text-[var(--l-navy-deep)] font-medium px-6 py-3 transition-transform hover:scale-[1.03]"
          >
            See how it works
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </a>
          <a
            href="#cost"
            className="inline-flex items-center gap-2 rounded-full border border-[var(--l-line-dark)] px-6 py-3 font-medium text-[var(--l-ink)] hover:border-[var(--l-orange-soft)] hover:text-[var(--l-orange-soft)] transition-colors"
          >
            The cost governance USP
          </a>
        </motion.div>
      </motion.div>

      <motion.div
        animate={{ y: [0, 8, 0] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        className="relative z-10 self-center mb-8 text-[var(--l-ink)]/50"
      >
        <ChevronDown className="w-5 h-5" />
      </motion.div>
    </section>
  );
}
