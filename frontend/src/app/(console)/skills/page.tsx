"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Puzzle } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { SkillCard } from "./_components/skill-card";
import { SkillDetailModal } from "./_components/skill-detail-modal";
import type { Skill } from "./_components/skill-types";

/**
 * Skill marketplace, styled as a fanned card deck — reference:
 * aardvarkbookclub.com's book carousel, adapted rather than copied. Real
 * skills only (currently three, all VERIFIED); the fan and the carousel
 * controls are built to hold more without changing shape when a fourth
 * skill is registered.
 */
export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [selected, setSelected] = useState<Skill | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/skills/")
      .then((data) => {
        if (!cancelled) setSkills(data ?? []);
      })
      .catch(() => {
        if (!cancelled) setSkills([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loading = skills === null;

  function scroll(dir: 1 | -1) {
    // `behavior: "smooth"` was tried first and never moved scrollLeft at
    // all in this project's test environment — confirmed directly (not
    // via the button, calling scrollBy on the track itself), confirmed
    // with scroll-snap disabled (not a snap interaction), confirmed after
    // a real 3s wait (not a throttled-animation timing issue like the
    // ones elsewhere in this project — smooth scroll runs on the
    // compositor, not React's scheduler, so that explanation doesn't fit
    // here anyway). "auto" reliably works. CSS scroll-snap still gives the
    // row its settle-into-place feel without needing the smooth behavior.
    trackRef.current?.scrollBy({ left: dir * 320, behavior: "auto" });
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-center gap-2 text-[var(--l-orange)]">
            <Puzzle className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-[0.14em]">
              Skill marketplace
            </span>
          </div>
          <h1 className="landing-display mt-2 text-3xl text-[var(--l-ink)]">
            Reusable capabilities
          </h1>
          <p className="mt-1 max-w-md text-sm text-[var(--l-charcoal)]/60">
            A skill is a shared library, not an agent — pick one or more when
            you build an agent, and its permissions come along automatically.
          </p>
        </motion.div>

        <div className="flex gap-2">
          <button
            onClick={() => scroll(-1)}
            aria-label="Scroll left"
            className="flex h-11 w-11 items-center justify-center rounded-full border border-[var(--l-line)] bg-[var(--l-cream-deep)] text-[var(--l-charcoal)] transition-colors hover:bg-[var(--l-cream-deep)]/70"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => scroll(1)}
            aria-label="Scroll right"
            className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--l-ink)] text-[var(--l-cream)] transition-transform hover:scale-105"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="mt-10 flex justify-center gap-4">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[380px] w-64 shrink-0 animate-pulse rounded-3xl bg-[var(--l-line)]/50"
            />
          ))}
        </div>
      ) : skills.length === 0 ? (
        <p className="mt-10 text-sm text-[var(--l-charcoal)]/60">
          No skills are registered yet.
        </p>
      ) : (
        <div
          ref={trackRef}
          className="mt-10 flex justify-center gap-0 overflow-x-auto px-2 py-10"
          style={{ scrollSnapType: "x proximity" }}
        >
          {skills.map((skill, i) => (
            <div key={skill.id} className={i === 0 ? "" : "-ml-8"} style={{ scrollSnapAlign: "start" }}>
              <SkillCard skill={skill} index={i} onReadMore={() => setSelected(skill)} />
            </div>
          ))}
        </div>
      )}

      <SkillDetailModal skill={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
