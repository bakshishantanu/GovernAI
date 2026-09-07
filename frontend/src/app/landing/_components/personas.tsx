"use client";

import { type ReactNode, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { ShieldCheck } from "lucide-react";

const PERSONAS = [
  {
    tag: "Platform / security engineers",
    bg: "var(--l-orange)",
    fg: "white",
    rotate: -5,
    pos: "md:top-[2%] md:left-[30%]",
  },
  {
    tag: "Agent builders",
    bg: "var(--l-yellow-deep)",
    fg: "var(--l-ink)",
    rotate: 4,
    pos: "md:top-[54%] md:left-[58%]",
  },
  {
    tag: "IT & budget owners",
    bg: "var(--l-teal)",
    fg: "white",
    rotate: -3,
    pos: "md:top-[58%] md:left-[4%]",
  },
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

export function Personas() {
  return (
    <section className="relative bg-[var(--l-yellow)] py-28 md:py-36 overflow-hidden">
      <div className="landing-blob pointer-events-none absolute -top-52 -left-40 w-[560px] h-[560px] bg-[var(--l-yellow-deep)] opacity-60" />
      <div className="landing-blob pointer-events-none absolute -bottom-40 -right-32 w-[480px] h-[480px] bg-[var(--l-yellow-pale)] opacity-70" />
      <div className="landing-blob pointer-events-none absolute top-1/3 right-1/4 w-[300px] h-[300px] bg-[var(--l-orange)] opacity-10" />

      <div className="max-w-6xl mx-auto px-6 relative">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-2xl mx-auto relative z-10"
        >
          <span className="text-xs uppercase tracking-[0.14em] text-white font-semibold">
            Built for three seats at the table
          </span>
          <h2 className="landing-display mt-4 text-4xl md:text-6xl text-[var(--l-ink)] tracking-tight">
            Who reaches for GovernAI
          </h2>
        </motion.div>

        <div className="relative mt-16 md:mt-4 md:h-[460px] flex flex-col items-center gap-6 md:block">
          <CentralMark />

          {PERSONAS.map((p, i) => (
            <motion.div
              key={p.tag}
              initial={{ opacity: 0, scale: 0.3, rotate: p.rotate + (i % 2 === 0 ? -30 : 30) }}
              whileInView={{ opacity: 1, scale: 1, rotate: p.rotate }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ type: "spring", stiffness: 220, damping: 15, delay: i * 0.15 }}
              className={`relative md:absolute ${p.pos}`}
            >
              <MagneticTag className="inline-block cursor-default">
                <div
                  className="rounded-full px-7 py-5 md:px-8 md:py-6 shadow-xl shadow-black/15 whitespace-nowrap"
                  style={{ background: p.bg, color: p.fg }}
                >
                  <h3 className="landing-display text-xl md:text-2xl leading-none">
                    {p.tag}
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
