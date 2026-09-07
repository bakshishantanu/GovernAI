"use client";

import { useRef } from "react";
import { useScroll, useTransform, useMotionValueEvent } from "framer-motion";

const STATEMENT = "Every agent arrives pre-governed";

export function Marquee() {
  const ref = useRef<HTMLDivElement>(null);
  const textPathRef = useRef<SVGTextPathElement>(null);

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  const offset = useTransform(scrollYProgress, [0, 1], [65, -65]);

  useMotionValueEvent(offset, "change", (v) => {
    textPathRef.current?.setAttribute("startOffset", `${v}%`);
  });

  return (
    <div
      ref={ref}
      className="relative bg-[var(--l-cream-deep)] py-6 md:py-10 overflow-hidden"
    >
      <svg
        viewBox="0 0 1200 260"
        className="w-full h-[150px] md:h-[210px]"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <path id="marquee-curve" d="M -300 210 Q 600 10 1500 210" fill="none" />
        </defs>
        <text
          className="landing-display"
          style={{ fill: "var(--l-charcoal)" }}
          fontSize="118"
        >
          <textPath ref={textPathRef} href="#marquee-curve" startOffset="30%">
            {STATEMENT}
          </textPath>
        </text>
      </svg>
    </div>
  );
}
