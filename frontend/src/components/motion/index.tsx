"use client";

import { motion, useReducedMotion, type Variants } from "motion/react";
import type { ReactNode } from "react";

/**
 * The console's motion vocabulary, in one place.
 *
 * The canvas is neo-brutalist: hard offset shadows, two border weights, no
 * blur. Motion has to match that or it fights the design — so everything here
 * is **short, small and decisive**. No long fades, no floaty springs, no
 * bounce. Movement is 4-8px and over in about a fifth of a second; the point
 * is to show that something arrived, not to perform.
 *
 * The governing rule is the same as the canvas's: *loud chrome, honest data*.
 * Chrome may animate. A number must never animate in a way that makes it
 * unreadable or that implies activity the backend did not report.
 *
 * Every primitive here collapses to no movement under
 * `prefers-reduced-motion`. That is checked per component with Motion's
 * `useReducedMotion`, not hoped for.
 */

/** Seconds. Anything longer than `slow` is too slow for this design. */
export const DURATION = {
  fast: 0.14,
  base: 0.2,
  slow: 0.28,
} as const;

/** A single decisive curve — out-quart. Nothing eases in; things arrive. */
export const EASE = [0.22, 1, 0.36, 1] as const;

/** Gap between staggered children. Small: a board should not unroll. */
export const STAGGER = 0.035;

/**
 * Fade and rise. The workhorse.
 *
 * `delay` exists for the handful of places that need a beat without a full
 * stagger container.
 */
export function Reveal({
  children,
  delay = 0,
  y = 6,
  className,
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  const still = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={still ? false : { opacity: 0, y }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.base, ease: EASE, delay: still ? 0 : delay }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Stagger container. Pair with `staggerItem` on each child's `variants`.
 *
 * Kept as variants rather than per-child delays so a list of unknown length
 * does not need its indices threaded through the markup.
 */
export const staggerContainer: Variants = {
  hidden: {},
  shown: {
    transition: { staggerChildren: STAGGER },
  },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 6 },
  shown: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.base, ease: EASE },
  },
};

export function Stagger({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const still = useReducedMotion();

  return (
    <motion.div
      className={className}
      variants={staggerContainer}
      initial={still ? false : "hidden"}
      animate="shown"
    >
      {children}
    </motion.div>
  );
}

export { motion, useReducedMotion };
export { AnimatePresence } from "motion/react";
