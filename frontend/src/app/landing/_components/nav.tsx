"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { ShieldCheck, ArrowRight } from "lucide-react";

const LINKS = [
  { href: "#problem", label: "Why" },
  { href: "#skills", label: "Skills" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#cost", label: "Cost control" },
];

export function LandingNav() {
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
        solid ? "bg-[var(--l-cream)]/90 backdrop-blur-md shadow-sm" : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-20 flex items-center justify-between">
        <a
          href="#hero"
          className="landing-display flex items-center gap-2 text-lg text-[var(--l-ink)]"
        >
          <ShieldCheck className="w-5 h-5 text-[var(--l-orange)]" />
          GovernAI
        </a>

        <nav className="hidden md:flex items-center gap-2 rounded-full bg-[var(--l-cream)]/80 backdrop-blur px-2 py-2 shadow-sm">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm font-medium px-4 py-2 rounded-full text-[var(--l-ink)]/75 hover:bg-[var(--l-yellow-pale)] hover:text-[var(--l-ink)] transition-colors"
            >
              {l.label}
            </a>
          ))}
        </nav>

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
