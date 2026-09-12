"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Tracks a CSS media query, via `useSyncExternalStore` rather than a
 * `useState`+effect pair.
 *
 * A lazy `useState(() => window.matchMedia(query).matches)` initializer was
 * tried first and caused a real hydration mismatch: React requires the
 * client's FIRST render (the one hydration diffs against the server's HTML)
 * to match the server exactly, and that first render happens synchronously
 * during hydration itself - by then `window` already exists, so the
 * initializer read the browser's real width immediately while the server
 * (which has no viewport to know) had always rendered `false`. Correcting
 * it via `setState` in a `useEffect` fixed the mismatch but is exactly the
 * pattern `react-hooks/set-state-in-effect` flags, for good reason (a
 * pointless extra render). `useSyncExternalStore`'s `getServerSnapshot` is
 * the API actually designed for "a value this can't know during SSR, but
 * needs correctly on the client without a wasted render" - React accounts
 * for it during hydration natively rather than this being a workaround.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    [query],
  );
  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query]);
  const getServerSnapshot = useCallback(() => false, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
