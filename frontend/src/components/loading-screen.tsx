"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Ticket, Search, FileSearch, Telescope, ShoppingCart, Check } from "lucide-react";
import { kecal } from "@/lib/landing-fonts";
import "@/app/landing/landing.css";

const SKILLS = [
  { name: "Ticketing", Icon: Ticket, color: "#1f8a83" },
  { name: "Enterprise Search", Icon: Search, color: "#3b3f4a" },
  { name: "Document Search", Icon: FileSearch, color: "#ff3d8a" },
  { name: "Research", Icon: Telescope, color: "#f0a227" },
];

const STEP_MS = 750;
const HOLD_MS = 1100;

export function LoadingScreen() {
  // 0..SKILLS.length-1 = dropping that skill into the cart; SKILLS.length = "complete" pause
  const [step, setStep] = useState(0);
  const complete = step === SKILLS.length;
  const current = SKILLS[step];
  const count = complete ? SKILLS.length : step;

  useEffect(() => {
    const t = setTimeout(
      () => setStep((s) => (s + 1) % (SKILLS.length + 1)),
      complete ? HOLD_MS : STEP_MS
    );
    return () => clearTimeout(t);
  }, [step, complete]);

  return (
    <div
      className={`${kecal.variable} fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-8 bg-[#0b0c10]/70 backdrop-blur-md text-[#fff8ec] overflow-hidden`}
    >
      <div className="landing-noise absolute inset-0 pointer-events-none" />
      <div className="landing-blob pointer-events-none absolute -bottom-40 left-1/2 -translate-x-1/2 w-[420px] h-[420px] bg-[#ff3d8a] opacity-[0.06]" />

      <div className="landing-display text-2xl relative z-10">GovernAI</div>

      <div className="relative z-10 flex flex-col items-center">
        {/* drop zone: the skill currently being added falls toward the cart */}
        <div className="relative h-16 w-16 flex items-center justify-center">
          <AnimatePresence mode="wait">
            {!complete && (
              <motion.div
                key={step}
                initial={{ y: -70, opacity: 0, scale: 0.6, rotate: -10 }}
                animate={{ y: 0, opacity: 1, scale: 1, rotate: 0 }}
                exit={{ y: 46, opacity: 0, scale: 0.15 }}
                transition={{ type: "spring", stiffness: 260, damping: 16 }}
                className="absolute w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg shadow-black/30"
                style={{ background: current.color }}
              >
                <current.Icon className="w-6 h-6 text-white" strokeWidth={1.75} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* the cart — your agent being assembled, one skill at a time */}
        <motion.div
          key={step}
          initial={{ rotate: 0 }}
          animate={
            complete
              ? { rotate: [0, -8, 8, -4, 0], scale: [1, 1.12, 1] }
              : { rotate: [0, -10, 8, 0], scale: [1, 1.06, 1] }
          }
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="relative mt-2"
        >
          <ShoppingCart
            className="w-20 h-20"
            style={{ color: "#fff8ec" }}
            strokeWidth={1.6}
          />

          <motion.div
            key={count}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 340, damping: 16 }}
            className="absolute -top-2 -right-2.5 min-w-[26px] h-[26px] px-1.5 rounded-full flex items-center justify-center text-xs font-bold"
            style={{ background: "#ff3d8a", color: "white" }}
          >
            {complete ? <Check className="w-3.5 h-3.5" strokeWidth={3} /> : count}
          </motion.div>
        </motion.div>

        <div className="mt-5 text-xs font-mono text-white/45 h-4">
          {complete ? "Agent assembled." : `Adding ${current.name}...`}
        </div>
      </div>
    </div>
  );
}
