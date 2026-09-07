"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

const STATEMENT = "Every agent arrives pre-governed.";

export function Marquee() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  const x = useTransform(scrollYProgress, [0, 1], ["18vw", "-45vw"]);

  return (
    <div
      ref={ref}
      className="relative bg-[var(--l-cream-deep)] py-16 md:py-24 overflow-hidden"
    >
      <motion.div
        style={{ x }}
        className="landing-marquee-font whitespace-nowrap font-semibold text-4xl sm:text-5xl md:text-6xl text-[var(--l-charcoal)] -rotate-3 inline-block will-change-transform"
      >
        {STATEMENT}
      </motion.div>
    </div>
  );
}
