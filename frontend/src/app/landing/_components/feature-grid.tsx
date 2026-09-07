"use client";

import { type ReactNode, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { ShieldCheck } from "lucide-react";

const FEATURES = [
  { title: "Skill marketplace", bg: "var(--l-orange)", fg: "white", pos: "md:top-[0%] md:left-[32%]" },
  { title: "Policy engine", bg: "var(--l-navy-deep)", fg: "white", pos: "md:top-[10%] md:left-[66%]" },
  { title: "Live cost tracking", bg: "var(--l-teal)", fg: "white", pos: "md:top-[38%] md:left-[2%]" },
  { title: "Append-only audit log", bg: "var(--l-orange-soft)", fg: "var(--l-ink)", pos: "md:top-[42%] md:left-[70%]" },
  { title: "One-click kill switch", bg: "var(--l-orange-deep)", fg: "white", pos: "md:top-[70%] md:left-[24%]" },
  { title: "Scoped ownership", bg: "var(--l-teal-soft)", fg: "var(--l-ink)", pos: "md:top-[72%] md:left-[58%]" },
];

function MagneticTag({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 150, damping: 12, mass: 0.4 });
  const springY = useSpring(y, { stiffness: 150, damping: 12, mass: 0.4 });

  const handleMouseMove = (e: ReactMouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    x.set((e.clientX - (rect.left + rect.width / 2)) * 0.35);
    y.set((e.clientY - (rect.top + rect.height / 2)) * 0.35);
  };
  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ x: springX, y: springY, ...style }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function CentralMark() {
  return (
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 hidden md:block">
      <div className="relative w-40 h-40 flex items-center justify-center">
        <div className="landing-slow-spin absolute inset-0 rounded-full border-2 border-dashed border-[var(--l-charcoal)]/25" />
        <div className="w-28 h-28 rounded-full bg-[var(--l-navy-deep)] flex items-center justify-center shadow-lg shadow-black/15">
          <ShieldCheck className="w-10 h-10 text-[var(--l-orange)]" strokeWidth={1.5} />
        </div>
      </div>
    </div>
  );
}

export function FeatureGrid() {
  return (
    <section id="features" className="relative bg-[var(--l-yellow)] py-28 md:py-36 overflow-hidden">
      <div className="landing-blob pointer-events-none absolute -top-48 -right-40 w-[520px] h-[520px] bg-[var(--l-yellow-deep)] opacity-60" />
      <div className="landing-blob pointer-events-none absolute -bottom-40 -left-32 w-[420px] h-[420px] bg-[var(--l-yellow-pale)] opacity-70" />

      <div className="max-w-6xl mx-auto px-6 relative">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl mx-auto relative z-10"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-white font-semibold">
            Everything, built in
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-6xl text-[var(--l-ink)] tracking-tight">
            Governance that ships with the agent, not after it.
          </h2>
        </motion.div>

        <div className="relative mt-16 md:mt-4 md:h-[560px] flex flex-col items-center gap-5 md:block">
          <CentralMark />

          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{
                opacity: 0,
                scale: 0.3,
                rotate: (i % 2 === 0 ? -1 : 1) * (25 + i * 3),
              }}
              whileInView={{ opacity: 1, scale: 1, rotate: (i % 2 === 0 ? -1 : 1) * (2 + (i % 3)) }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ type: "spring", stiffness: 240, damping: 14, delay: i * 0.08 }}
              className={`relative md:absolute ${f.pos}`}
            >
              <MagneticTag className="inline-block cursor-default">
                <div
                  className="rounded-full px-6 py-4 md:px-7 md:py-5 shadow-xl shadow-black/15 whitespace-nowrap"
                  style={{ background: f.bg, color: f.fg }}
                >
                  <h3 className="landing-display text-lg md:text-xl leading-none">
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
