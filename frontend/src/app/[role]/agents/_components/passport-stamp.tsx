"use client";

import { motion, useReducedMotion } from "framer-motion";
import { lifecycleOf, type Agent } from "./agent-types";

/**
 * A rubber stamp, not a badge — the visual anchor of the whole card. Real
 * stamps are imprecise: this one is drawn with a slightly irregular dashed
 * ring and sits rotated, overlapping the card's corner, so it reads as
 * pressed onto the passport rather than laid flat as UI chrome.
 */
export function PassportStamp({ agent, delay = 0 }: { agent: Agent; delay?: number }) {
  const still = useReducedMotion();
  const lc = lifecycleOf(agent);

  return (
    <motion.div
      initial={still ? { opacity: 0 } : { opacity: 0, scale: 1.6, rotate: -26 }}
      animate={{ opacity: 1, scale: 1, rotate: -12 }}
      transition={
        still
          ? { duration: 0.2 }
          : { duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }
      }
      className="pointer-events-none absolute -right-3 -top-3 z-10"
    >
      <div
        className="flex h-[68px] w-[68px] items-center justify-center rounded-full border-[2.5px] border-dashed text-center"
        style={{
          borderColor: lc.ink,
          background: `${lc.paper}e6`,
          boxShadow: `0 0 0 3px ${lc.paper}e6`,
        }}
      >
        <span
          className="landing-display text-[9px] leading-[1.05] tracking-tight"
          style={{ color: lc.ink }}
        >
          {lc.stamp}
        </span>
      </div>
    </motion.div>
  );
}
