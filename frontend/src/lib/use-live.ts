"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Keeps a screen current without a page refresh.
 *
 * The honest version of "live" until the org-wide event stream exists: it
 * re-fetches on an interval, and reports when it last succeeded so the UI can
 * say so rather than implying a socket. Three details that make it behave:
 *
 * - It pauses while the tab is hidden. A backgrounded tab that keeps polling
 *   burns the user's battery and the API's budget to update pixels nobody is
 *   looking at, and browsers throttle the timer unevenly anyway.
 * - It re-fetches immediately when the tab comes back, so returning to the
 *   window never shows a stale figure while waiting for the next tick.
 * - It re-fetches on the dev role-switch event, because changing role changes
 *   who the API thinks you are, and the previous role's data must not linger.
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
    const onRoleChange = () => refresh();

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("govern-ai-role-change", onRoleChange);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("govern-ai-role-change", onRoleChange);
    };
  }, [refresh, intervalMs]);

  return { data, updatedAt, refresh };
}
