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

  const x = useTransform(scrollYProgress, [0, 1], ["28vw", "-70vw"]);

  return (
    <div
      ref={ref}
      className="relative bg-[var(--l-cream-deep)] py-20 md:py-28 overflow-hidden"
    >
      <motion.div
        style={{ x }}
        className="landing-display whitespace-nowrap text-6xl sm:text-8xl md:text-9xl text-[var(--l-charcoal)] -rotate-3 inline-block will-change-transform"
      >
        {STATEMENT}
      </motion.div>
    </div>
  );
}
