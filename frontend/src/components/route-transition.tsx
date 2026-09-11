"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { LoadingScreen } from "@/components/loading-screen";

// Next's loading.tsx only fires when a route segment does real async
// server work — our pages render synchronously, so it never triggers.
// This shows the same screen on every route change (and on first
// mount, covering a hard reload) for a guaranteed minimum duration,
// regardless of how fast the actual navigation is.
const MIN_VISIBLE_MS = 900;

export function RouteTransition() {
  const pathname = usePathname();
  const [visible, setVisible] = useState(true);
  const isFirstRun = useRef(true);
  const prevPathname = useRef(pathname);
  // A ref, deliberately not state and deliberately not cleared by a returned
  // effect cleanup: role resolution can bounce the pathname (e.g. "/" ->
  // "/admin") within the same MIN_VISIBLE_MS window, re-firing this effect
  // while shouldShow is now false. A cleanup function tied to the pathname
  // dependency runs on *every* re-fire regardless of that run's outcome —
  // including React 18 Strict Mode's dev-only double-invoke of a fresh
  // effect — and would cancel the still-pending hide timer moments after it
  // was set, with nothing left to reschedule it once isFirstRun is already
  // consumed. This component lives at the root layout for the app's whole
  // lifetime and never unmounts, so skipping cleanup here is safe.
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const cameFromLogin = prevPathname.current?.startsWith("/login");
    prevPathname.current = pathname;
    const shouldShow = isFirstRun.current || cameFromLogin;
    isFirstRun.current = false;

    if (!shouldShow) return;

    setVisible(true);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => setVisible(false), MIN_VISIBLE_MS);
  }, [pathname]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="route-transition"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35 }}
          className="fixed inset-0 z-[9999]"
        >
          <LoadingScreen />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
