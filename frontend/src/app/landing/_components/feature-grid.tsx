"use client";

import { type ReactNode, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { ShieldCheck } from "lucide-react";

// Positions, rotations and colors pulled directly from the reference's
// own CSS (.benefits__label.is--first..fifth, magenta/orange/
// periwinkle/cyan/olive swatches) — not eyeballed off a screenshot.
const FEATURES: {
  title: string;
  bg: string;
  fg: string;
  rotate: number;
  pos: CSSProperties;
}[] = [
  {
    title: "Skill marketplace",
    bg: "#ff008c",
    fg: "#fff",
    rotate: -5,
    pos: { top: "30%", left: "8%" },
  },
  {
    title: "Policy engine",
    bg: "#f9a220",
    fg: "#670a2e",
    rotate: -1.8,
    pos: { top: "40%", right: "4%" },
  },
  {
    title: "Live cost tracking",
    bg: "#9982de",
    fg: "#fff",
    rotate: 2.5,
    pos: { top: "54%", left: "12%", zIndex: 1 },
  },
  {
    title: "Append-only\naudit log",
    bg: "#1ce8ed",
    fg: "#3b308f",
    rotate: 5.8,
    pos: { top: "58%", right: "10%" },
  },
  {
    title: "One-click kill switch",
    bg: "#857521",
    fg: "#fff",
    rotate: -5.3,
    pos: { top: "72%", left: "4%" },
  },
  {
    title: "Scoped ownership",
    bg: "var(--l-teal-soft)",
    fg: "var(--l-ink)",
    rotate: 4,
    pos: { top: "78%", right: "26%" },
  },
];

function MagneticTag({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 150, damping: 12, mass: 0.4 });
  const springY = useSpring(y, { stiffness: 150, damping: 12, mass: 0.4 });

  const handleMouseMove = (e: ReactMouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    x.set((e.clientX - (rect.left + rect.width / 2)) * 0.3);
    y.set((e.clientY - (rect.top + rect.height / 2)) * 0.3);
  };
  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ x: springX, y: springY }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function CentralMark() {
  return (
    <div className="absolute top-[38%] left-1/2 -translate-x-1/2 -translate-y-1/2 hidden md:block">
      <div className="relative w-72 h-72 lg:w-80 lg:h-80 flex items-center justify-center">
        <div className="landing-slow-spin absolute inset-0 rounded-full border-2 border-dashed border-[var(--l-charcoal)]/20" />
        <div className="w-24 h-24 rounded-full bg-[var(--l-navy-deep)] flex items-center justify-center shadow-lg shadow-black/15">
          <ShieldCheck className="w-9 h-9 text-[var(--l-orange)]" strokeWidth={1.5} />
        </div>
      </div>
    </div>
  );
}

export function FeatureGrid() {
  return (
    <section id="features" className="relative bg-[#faed8f] py-28 md:py-36 overflow-hidden">
      <div className="landing-blob pointer-events-none absolute -top-48 -right-40 w-[520px] h-[520px] bg-[var(--l-yellow-deep)] opacity-40" />
      <div className="landing-blob pointer-events-none absolute -bottom-40 -left-32 w-[420px] h-[420px] bg-[var(--l-yellow-pale)] opacity-60" />

      <div className="max-w-6xl mx-auto px-6 relative">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl mx-auto relative z-10"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-[#670a2e] font-semibold">
            Everything, built in
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-6xl text-[var(--l-ink)] tracking-tight">
            Governance that ships with the agent, not after it.
          </h2>
        </motion.div>

        <div className="relative mt-16 md:mt-6 md:h-[680px] flex flex-col items-center gap-4 md:block">
          <CentralMark />

          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, scale: 0, rotate: (i % 2 === 0 ? -1 : 1) * (28 + i * 4) }}
              whileInView={{ opacity: 1, scale: 1, rotate: f.rotate }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ type: "spring", stiffness: 240, damping: 14, delay: i * 0.08 }}
              className="relative md:absolute"
              style={{ ...f.pos }}
            >
              <MagneticTag className="inline-block cursor-default">
                <div
                  className="rounded-full px-7 py-4 md:px-9 md:py-5 shadow-xl shadow-black/20 whitespace-pre-line text-center"
                  style={{ background: f.bg, color: f.fg }}
                >
                  <h3 className="landing-display text-xl md:text-3xl leading-[0.85] tracking-tight">
                    {f.title}
                  </h3>
                </div>
              </MagneticTag>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
