"use client";

import { motion } from "framer-motion";

/** The lever FRD-14 is actually about: flip it and the next tool call obeys immediately. */
export function RuleToggle({
  on,
  onChange,
  disabled,
  size = "md",
}: {
  on: boolean;
  onChange: () => void;
  disabled?: boolean;
  size?: "md" | "lg";
}) {
  const dims = size === "lg" ? { w: 44, h: 24, knob: 18 } : { w: 36, h: 20, knob: 15 };
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      disabled={disabled}
      onClick={onChange}
      className="relative shrink-0 rounded-full transition-colors disabled:opacity-40"
      style={{
        width: dims.w,
        height: dims.h,
        background: on ? "var(--l-teal)" : "color-mix(in srgb, var(--l-ink) 20%, transparent)",
      }}
    >
      <motion.span
        layout
        transition={{ type: "spring", stiffness: 600, damping: 32 }}
        className="absolute top-1/2 block rounded-full bg-white shadow"
        style={{
          width: dims.knob,
          height: dims.knob,
          left: on ? dims.w - dims.knob - 3 : 3,
          y: "-50%",
        }}
      />
    </button>
  );
}
