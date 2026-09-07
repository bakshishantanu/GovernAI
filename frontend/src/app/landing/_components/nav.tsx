"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { ShieldCheck } from "lucide-react";

const LINKS = [
  { href: "#problem", label: "Why" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#cost", label: "Cost control" },
  { href: "#features", label: "Features" },
];

export function LandingNav() {
  const [solid, setSolid] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, "change", (latest) => {
    setSolid(latest > 60);
  });

  // Section under the nav starts dark; flip nav text color once we scroll past hero.
  const [onDark, setOnDark] = useState(true);
  useEffect(() => {
    const hero = document.getElementById("hero");
    if (!hero) return;
    const observer = new IntersectionObserver(
      ([entry]) => setOnDark(entry.isIntersecting),
      { rootMargin: "-64px 0px 0px 0px", threshold: 0 }
    );
    observer.observe(hero);
    return () => observer.disconnect();
  }, []);

  const light = onDark && !solid;

  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-300 ${
        solid
          ? "bg-[var(--l-cream)]/90 backdrop-blur-md border-b border-[var(--l-line)]"
          : "bg-transparent border-b border-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <a
          href="#hero"
          className={`flex items-center gap-2 font-semibold tracking-tight transition-colors ${
            light ? "text-[var(--l-ink)]" : "text-[var(--l-charcoal)]"
          }`}
        >
          <ShieldCheck className="w-5 h-5 text-[var(--l-orange)]" />
          GovernAI
        </a>

        <nav className="hidden md:flex items-center gap-8 text-sm">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className={`transition-colors hover:text-[var(--l-orange)] ${
                light ? "text-[var(--l-ink)]/80" : "text-[var(--l-charcoal)]/70"
              }`}
            >
              {l.label}
            </a>
          ))}
        </nav>

        <Link
          href="/login"
          className={`text-sm font-medium px-4 py-2 rounded-full transition-colors ${
            light
              ? "bg-[var(--l-cream)] text-[var(--l-navy-deep)] hover:bg-[var(--l-orange)] hover:text-white"
              : "bg-[var(--l-navy-deep)] text-[var(--l-cream)] hover:bg-[var(--l-orange)]"
          }`}
        >
          Sign in
        </Link>
      </div>
    </motion.header>
  );
}
