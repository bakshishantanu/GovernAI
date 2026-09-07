"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Ticket, Database, FileSearch, Telescope, Check } from "lucide-react";
import { archivoBlack } from "@/lib/landing-fonts";
import "./landing/landing.css";

const SKILLS = [
  { name: "Ticketing", Icon: Ticket, color: "#1f8a83" },
  { name: "SQL Query", Icon: Database, color: "#3b3f4a" },
  { name: "Document Search", Icon: FileSearch, color: "#ff3d8a" },
  { name: "Research", Icon: Telescope, color: "#f0a227" },
];

const STEP_MS = 750;
const HOLD_MS = 1100;

export default function Loading() {
  // 0..SKILLS.length-1 = dropping that skill in; SKILLS.length = "complete" pause
  const [step, setStep] = useState(0);
  const complete = step === SKILLS.length;
  const current = SKILLS[step];

  useEffect(() => {
    const t = setTimeout(
      () => setStep((s) => (s + 1) % (SKILLS.length + 1)),
      complete ? HOLD_MS : STEP_MS
    );
    return () => clearTimeout(t);
  }, [step, complete]);

  return (
    <div
      className={`${archivoBlack.variable} fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-8 bg-[#0b0c10] text-[#fff8ec] overflow-hidden`}
    >
      <div className="landing-noise absolute inset-0 pointer-events-none" />
      <div className="landing-blob pointer-events-none absolute -bottom-40 left-1/2 -translate-x-1/2 w-[420px] h-[420px] bg-[#ff3d8a] opacity-[0.06]" />

      <div className="landing-display text-2xl relative z-10">GovernAI</div>

      <div className="relative z-10 flex flex-col items-center">
        {/* drop zone: the skill currently being added falls in from above */}
        <div className="relative h-16 w-16 flex items-center justify-center">
          <AnimatePresence mode="wait">
            {!complete && (
              <motion.div
                key={step}
                initial={{ y: -70, opacity: 0, scale: 0.6, rotate: -10 }}
                animate={{ y: 0, opacity: 1, scale: 1, rotate: 0 }}
                exit={{ y: 34, opacity: 0, scale: 0.4 }}
                transition={{ type: "spring", stiffness: 260, damping: 16 }}
                className="absolute w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg shadow-black/30"
                style={{ background: current.color }}
              >
                <current.Icon className="w-6 h-6 text-white" strokeWidth={1.75} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* the "cart" — your agent being assembled */}
        <motion.div
          animate={complete ? { scale: [1, 1.05, 1] } : { scale: 1 }}
          transition={{ duration: 0.4 }}
          className="mt-2 w-72 min-h-[68px] rounded-[24px] border-2 border-dashed border-white/20 bg-white/[0.03] px-5 py-4 flex items-center gap-2.5"
        >
          {SKILLS.map((s, i) => (
            <motion.div
              key={s.name}
              animate={
                i < step || complete
                  ? { scale: 1, opacity: 1 }
                  : { scale: 0, opacity: 0 }
              }
              transition={{ type: "spring", stiffness: 320, damping: 18 }}
              className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: s.color }}
            >
              <s.Icon className="w-4 h-4 text-white" strokeWidth={2} />
            </motion.div>
          ))}

          {complete && (
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.15, type: "spring", stiffness: 300, damping: 16 }}
              className="ml-auto w-8 h-8 rounded-full bg-[#1f8a83] flex items-center justify-center shrink-0"
            >
              <Check className="w-4 h-4 text-white" strokeWidth={3} />
            </motion.div>
          )}
        </motion.div>

        <div className="mt-4 text-xs font-mono text-white/45 h-4">
          {complete ? "Agent assembled." : `Adding ${current.name}...`}
        </div>
      </div>
    </div>
  );
}
