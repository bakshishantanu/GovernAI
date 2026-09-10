"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { subscribeGlobalEvents } from "./global-events";

/**
 * Keeps a screen current without a page refresh.
 *
 * Driven by the org-wide event stream (`GET /events/stream`) when it's
 * connected: a matching backend event triggers an immediate re-fetch, so
 * most updates arrive the moment they happen rather than on the next tick.
 * The interval poll below is kept as the fallback — it's what covers the
 * stream while it's reconnecting, and it's why `updatedAt` is reported at
 * all, so the UI can say "updated N ago" honestly instead of implying a
 * socket that might be down. Three more details that make it behave:
 *
 * - It pauses while the tab is hidden. A backgrounded tab that keeps polling
 *   burns the user's battery and the API's budget to update pixels nobody is
 *   looking at, and browsers throttle the timer unevenly anyway.
 * - It re-fetches immediately when the tab comes back, so returning to the
 *   window never shows a stale figure while waiting for the next tick.
 */
export function useLive<T>(load: () => Promise<T>, intervalMs = 15000) {
  const [data, setData] = useState<T | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  // Held in a ref so the polling effect never restarts when the caller passes
  // a fresh closure, and written in an effect rather than during render, which
  // React does not allow.
  const loadRef = useRef(load);
  useEffect(() => {
    loadRef.current = load;
  }, [load]);

  const refresh = useCallback(async () => {
    try {
      const next = await loadRef.current();
      setData(next);
      setUpdatedAt(Date.now());
    } catch {
      // Leave the last good value on screen. Blanking a dashboard because one
      // poll failed is worse than showing figures a few seconds old.
    }
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (timer) return;
      timer = setInterval(refresh, intervalMs);
    };
    const stop = () => {
      if (!timer) return;
      clearInterval(timer);
      timer = null;
    };

    refresh();
    if (!document.hidden) start();

    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        refresh();
        start();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    const unsubscribeLive = subscribeGlobalEvents(refresh);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
      unsubscribeLive();
    };
  }, [refresh, intervalMs]);

  return { data, updatedAt, refresh };
}
