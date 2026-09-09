"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { ShieldCheck, ArrowRight, ArrowLeft } from "lucide-react";

/**
 * Page-local nav.
 *
 * The main landing nav links to in-page anchors (#problem, #cost …) that do
 * not exist on this route, so reusing it would leave four dead links in the
 * header. This keeps the same visual language and links back to the sections
 * on the main page by absolute path instead.
 */
export function OwnerNav() {
  const [solid, setSolid] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, "change", (latest) => {
    setSolid(latest > 60);
  });

  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-300 ${
        solid
          ? "bg-[var(--l-cream)]/90 backdrop-blur-md shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-20 flex items-center justify-between">
        <Link
          href="/landing"
          className="landing-display flex items-center gap-2 text-lg text-[var(--l-ink)]"
        >
          <ShieldCheck className="w-5 h-5 text-[var(--l-orange)]" />
          GovernAI
        </Link>

        <Link
          href="/landing"
          className="hidden md:inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-full text-[var(--l-ink)]/75 hover:bg-[var(--l-yellow-pale)] hover:text-[var(--l-ink)] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to overview
        </Link>

        <Link
          href="/login"
          className="group inline-flex items-center gap-2 text-sm font-semibold px-5 py-2.5 rounded-full bg-[var(--l-orange)] text-white shadow-[0_5px_0_0_var(--l-orange-deep)] hover:-translate-y-0.5 active:translate-y-0 active:shadow-[0_2px_0_0_var(--l-orange-deep)] transition-transform"
        >
          Log-in / Sign-up
          <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>
    </motion.header>
  );
}
