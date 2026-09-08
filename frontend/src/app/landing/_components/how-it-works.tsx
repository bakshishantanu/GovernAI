"use client";

import { useRef, useState } from "react";
import {
  motion,
  useScroll,
  useMotionValueEvent,
  AnimatePresence,
} from "framer-motion";
import {
  Blocks,
  ShieldCheck,
  GaugeCircle,
  ScrollText,
  Check,
  X,
} from "lucide-react";

const STEPS = [
  {
    n: "01",
    icon: Blocks,
    title: "Assemble from skills",
    body: "Builders pick from a curated registry (ticketing, doc search, SQL) instead of writing integrations from zero.",
  },
  {
    n: "02",
    icon: ShieldCheck,
    title: "Governance, generated",
    body: "Identity, permission scope, and a cost budget are issued automatically the moment the agent is created.",
  },
  {
    n: "03",
    icon: GaugeCircle,
    title: "Every call, intercepted",
    body: "The policy gate checks permission scope and budget on every single tool call, in real time, not after the fact.",
  },
  {
    n: "04",
    icon: ScrollText,
    title: "Logged, unconditionally",
    body: "Allowed or blocked, the outcome and its cost land in an append-only audit log the dashboard reads in real time.",
  },
];

export function HowItWorks() {
  const sectionRef = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    const idx = Math.min(STEPS.length - 1, Math.floor(v * STEPS.length));
    setActive(idx);
  });

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="relative bg-[var(--l-cream-deep)]"
      style={{ height: `${STEPS.length * 100}vh` }}
    >
      <div className="sticky top-0 h-screen flex items-center overflow-hidden">
        <div className="max-w-6xl mx-auto px-6 w-full grid md:grid-cols-2 gap-16 items-center">
          <div>
            <span className="text-xs uppercase tracking-[0.14em] text-[var(--l-orange)] font-semibold">
              How it works
            </span>
            <div className="mt-8 space-y-1">
              {STEPS.map((s, i) => (
                <div
                  key={s.n}
                  className="py-4 border-b border-[var(--l-line)] last:border-none"
                >
                  <div className="flex items-baseline gap-4">
                    <span
                      className={`font-mono text-sm transition-colors duration-300 ${
                        i === active
                          ? "text-[var(--l-orange)]"
                          : "text-[var(--l-charcoal)]/30"
                      }`}
                    >
                      {s.n}
                    </span>
                    <h3
                      className={`text-xl md:text-2xl font-semibold transition-all duration-300 ${
                        i === active
                          ? "text-[var(--l-charcoal)]"
                          : "text-[var(--l-charcoal)]/30"
                      }`}
                    >
                      {s.title}
                    </h3>
                  </div>
                  <motion.p
                    initial={false}
                    animate={{
                      height: i === active ? "auto" : 0,
                      opacity: i === active ? 1 : 0,
                    }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden text-sm text-[var(--l-charcoal)]/60 pl-9 leading-relaxed"
                  >
                    <span className="block pt-2 pb-1">{s.body}</span>
                  </motion.p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative h-[420px] flex items-center justify-center">
            <AnimatePresence mode="wait">
              <motion.div
                key={active}
                initial={{ opacity: 0, scale: 0.92, y: 16 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="w-full max-w-sm rounded-3xl bg-[var(--l-navy-deep)] text-[var(--l-cream)] p-8 border border-[var(--l-line-dark)] shadow-2xl shadow-black/10"
              >
                <StepVisual step={active} />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}

function StepVisual({ step }: { step: number }) {
  const Icon = STEPS[step].icon;
  if (step === 0) {
    return (
      <div>
        <Icon className="w-7 h-7 text-[var(--l-orange-soft)]" />
        <div className="mt-6 grid grid-cols-2 gap-2.5">
          {["Ticketing", "Doc search", "SQL query", "+ Skill"].map((s) => (
            <div
              key={s}
              className="rounded-lg border border-[var(--l-line-dark)] bg-white/[0.04] px-3 py-3 text-xs font-mono text-[var(--l-cream)]/70"
            >
              {s}
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (step === 1) {
    return (
      <div>
        <Icon className="w-7 h-7 text-[var(--l-teal-soft)]" />
        <div className="mt-6 space-y-2.5">
          {["Identity issued", "Scope assigned", "Budget cap set"].map((s) => (
            <div key={s} className="flex items-center gap-2.5 text-sm">
              <Check className="w-4 h-4 text-[var(--l-teal-soft)]" />
              <span className="font-mono text-[var(--l-cream)]/80">{s}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (step === 2) {
    return (
      <div>
        <Icon className="w-7 h-7 text-[var(--l-orange-soft)]" />
        <div className="mt-6 space-y-2.5 text-sm font-mono">
          <div className="flex items-center gap-2.5 text-[var(--l-teal-soft)]">
            <Check className="w-4 h-4" /> ticket:read · allowed
          </div>
          <div className="flex items-center gap-2.5 text-[#e07a6b]">
            <X className="w-4 h-4" /> db:write · blocked
          </div>
          <div className="flex items-center gap-2.5 text-[var(--l-teal-soft)]">
            <Check className="w-4 h-4" /> docs:search · allowed
          </div>
        </div>
      </div>
    );
  }
  return (
    <div>
      <Icon className="w-7 h-7 text-[var(--l-orange-soft)]" />
      <div className="mt-6 space-y-2 font-mono text-xs text-[var(--l-cream)]/60">
        <div>12:04:01 · tool_call · allowed · $0.004</div>
        <div>12:04:03 · tool_call · blocked · $0.000</div>
        <div>12:04:07 · tool_call · allowed · $0.011</div>
        <div className="text-[var(--l-orange-soft)]">
          → audit log, append-only, 100% coverage
        </div>
      </div>
    </div>
  );
}
