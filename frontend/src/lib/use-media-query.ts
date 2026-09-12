"use client";

import { useEffect, useState } from "react";

/**
 * Tracks a CSS media query in React state, kept in sync via the
 * `MediaQueryList` change event rather than a resize listener (fires only
 * when the query's truth value actually flips, not on every pixel of a
 * drag-resize).
 *
 * The initial value is read lazily in `useState`'s own initializer (same
 * pattern as `loadCollapsed`/`loadSeen` elsewhere in this app) rather than
 * defaulting to `false` and correcting in an effect - `window` genuinely
 * isn't there during SSR, but by the time this ever renders on the client
 * it is, so there's no reason to render one extra "wrong" frame first.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === "undefined" ? false : window.matchMedia(query).matches
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
