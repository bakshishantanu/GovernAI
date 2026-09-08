"use client";

import { useEffect, useRef } from "react";
import { animate, useReducedMotion } from "framer-motion";

/**
 * A figure that arrives at its value rather than appearing at it.
 *
 * Worth the motion only because these numbers are live and change under the
 * reader — the count draws the eye to the one that moved. It writes to the DOM
 * node directly instead of through state, so a ticking number never re-renders
 * the panel around it.
 *
 * Honest at rest: with reduced motion requested, or when the value has not
 * actually changed, it simply prints the number.
 */
export function CountUp({
  value,
  duration = 0.8,
  className = "",
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef(0);
  const reduced = useReducedMotion();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const from = previous.current;
    previous.current = value;

    if (reduced || from === value) {
      node.textContent = String(value);
      return;
    }

    const controls = animate(from, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        node.textContent = String(Math.round(v));
      },
    });
    return () => controls.stop();
  }, [value, duration, reduced]);

  // Rendered with the final value so the number is correct before hydration
  // and for anything that never runs the effect.
  return (
    <span ref={ref} className={`gv-num ${className}`}>
      {value}
    </span>
  );
}
