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
    pos: { top: "34%", right: "4%" },
  },
  {
    title: "Live cost\ntracking",
    bg: "#9982de",
    fg: "#fff",
    rotate: 2.5,
    pos: { top: "48%", left: "12%" },
  },
  {
    title: "Append-only\naudit log",
    bg: "#1ce8ed",
    fg: "#3b308f",
    rotate: 5.8,
    pos: { top: "54%", right: "10%" },
  },
  {
    title: "One-click kill switch",
    bg: "#857521",
    fg: "#fff",
    rotate: -5.3,
    pos: { top: "70%", left: "4%" },
  },
  {
    title: "Scoped ownership",
    bg: "var(--l-teal-soft)",
    fg: "var(--l-ink)",
    rotate: 4,
    pos: { top: "76%", right: "6%" },
  },
];

// Original cash-note glyph (single rounded-rect "bill" plus a $ mark,
// our own linework, not traced from any stock icon), repeated at
// irregular positions, rotations and sizes across one wide tile, with
// several sitting right on the tile's edge so they read as randomly
// scattered bills (some full, some cut off) rather than a uniform grid.
function cashInstance(tx: number, ty: number, rot: number, scale: number) {
  return `%3Cg transform='translate(${tx},${ty}) rotate(${rot}) scale(${scale})'%3E%3Crect x='-17' y='-9' width='34' height='20' rx='3' stroke-width='2.6' opacity='0.4'/%3E%3Ctext x='-5' y='7' font-family='sans-serif' font-size='15' font-weight='700' fill='%23ffffff' stroke='none' opacity='0.4'%3E%24%3C/text%3E%3C/g%3E`;
}

const CASH_INSTANCES: [number, number, number, number][] = [
  [20, 32, -15, 1.5],
  [118, 14, 10, 1.2],
  [208, 72, -20, 1.65],
  [298, 24, 16, 1.25],
  [368, 112, -8, 1.5],
  [458, 54, 20, 1.6],
  [60, 122, 12, 1.15],
  [492, 16, -12, 1.25],
];

const CASH_WATERMARK =
  "data:image/svg+xml," +
  "%3Csvg xmlns='http://www.w3.org/2000/svg' width='500' height='150'%3E" +
  "%3Cg fill='none' stroke='%23ffffff'%3E" +
  CASH_INSTANCES.map(([tx, ty, rot, scale]) => cashInstance(tx, ty, rot, scale)).join("") +
  "%3C/g%3E%3C/svg%3E";

// Two overlapping diagonal ribbons, full-bleed to the browser window on
// both edges (not just the max-w-6xl content column) so each one reads
// as a single continuous band instead of a rectangle clipped mid-shape
// by its container. Rendered as a standalone sibling between FeatureGrid
// and Personas (not nested inside FeatureGrid's own overflow-hidden
// section) with a negative bottom margin, so it can dip down and overlap
// the top of the pink Personas section that follows it.
export function BillingDemoStrip() {
  const watermark: CSSProperties = {
    backgroundImage: `url("${CASH_WATERMARK}")`,
    backgroundRepeat: "repeat",
    backgroundSize: "500px 150px",
  };

  return (
    <div className="relative left-1/2 w-screen -translate-x-1/2 -mb-16 md:-mb-24 z-30 select-none">
      <div className="relative overflow-hidden -rotate-2 bg-[#ff008c] py-4 md:py-6 shadow-lg shadow-black/10">
        <div className="absolute inset-0" style={watermark} aria-hidden />
        <p className="landing-display relative text-center text-xl md:text-3xl text-[#670a2e] tracking-tight px-4">
          Free during your pilot, billing only starts once you go live!
        </p>
      </div>
      <div className="relative overflow-hidden -mt-1 rotate-2 bg-[#1ce8ed] py-4 md:py-6 shadow-lg shadow-black/10">
        <div className="absolute inset-0" style={watermark} aria-hidden />
        <p className="landing-display relative text-center text-xl md:text-3xl text-[#3b308f] tracking-tight px-4">
          Book a live demo and we&apos;ll waive your first invoice!
        </p>
      </div>
    </div>
  );
}

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
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 hidden md:block z-0">
      <div className="relative w-[260px] h-[260px] lg:w-[320px] lg:h-[320px] flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border-[3px] border-[var(--l-charcoal)]/70" />
        <div className="w-40 h-40 rounded-full bg-[var(--l-navy-deep)] flex items-center justify-center shadow-lg shadow-black/15">
          <ShieldCheck className="w-16 h-16 text-[var(--l-orange)]" strokeWidth={1.5} />
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

        <div className="relative mt-16 md:mt-6 md:h-[640px] flex flex-col items-center gap-4 md:block">
          <CentralMark />

          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, scale: 0, rotate: (i % 2 === 0 ? -1 : 1) * (28 + i * 4) }}
              whileInView={{ opacity: 1, scale: 1, rotate: f.rotate }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ type: "spring", stiffness: 240, damping: 14, delay: i * 0.08 }}
              className="relative md:absolute z-10"
              style={{ ...f.pos }}
            >
              <MagneticTag className="inline-block cursor-default">
                <div
                  className="rounded-full px-8 py-5 md:px-11 md:py-7 shadow-xl shadow-black/25 whitespace-pre-line text-center"
                  style={{ background: f.bg, color: f.fg }}
                >
                  <h3 className="landing-display text-2xl md:text-4xl lg:text-5xl leading-[0.85] tracking-tight">
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
