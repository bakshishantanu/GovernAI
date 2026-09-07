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

  useEffect(() => {
    if (isFirstRun.current) {
      isFirstRun.current = false;
    } else {
      setVisible(true);
    }

    const t = setTimeout(() => setVisible(false), MIN_VISIBLE_MS);
    return () => clearTimeout(t);
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
