"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { archivoBlack } from "@/lib/landing-fonts";
import "./landing/landing.css";

const STEPS = [
  "Issuing identity...",
  "Scoping permissions...",
  "Checking live budget...",
  "Governance ready.",
];

export default function Loading() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setStep((s) => Math.min(s + 1, STEPS.length - 1));
    }, 650);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      className={`${archivoBlack.variable} fixed inset-0 z-[9999] flex flex-col items-center justify-center gap-8 bg-[#0b0c10] text-[#fff8ec] overflow-hidden`}
    >
      <div className="landing-noise absolute inset-0 pointer-events-none" />

      <div className="relative w-24 h-24 flex items-center justify-center">
        <div className="landing-slow-spin absolute inset-0 rounded-full border-2 border-dashed border-[#ff8ab8]/40" />
        <motion.div
          animate={{ scale: [1, 1.08, 1], opacity: [0.5, 0.9, 0.5] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute inset-2 rounded-full bg-[#ff3d8a]/20 blur-md"
        />
        <div className="relative w-14 h-14 rounded-full bg-[#14151b] border border-white/10 flex items-center justify-center">
          <ShieldCheck className="w-6 h-6 text-[#ff3d8a]" strokeWidth={1.75} />
        </div>
      </div>

      <div className="relative text-center">
        <div className="landing-display text-3xl">GovernAI</div>

        <div className="mt-5 w-56 h-1.5 rounded-full bg-white/10 overflow-hidden mx-auto">
          <motion.div
            className="h-full rounded-full bg-[#ff3d8a]"
            initial={{ width: "0%" }}
            animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>

        <div className="mt-3 text-xs font-mono text-white/45 h-4">
          {STEPS[step]}
        </div>
      </div>
    </div>
  );
}
