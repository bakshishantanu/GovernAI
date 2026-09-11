"use client";

import { API_BASE, getAuthHeader } from "./api-client";
import { readSseBody } from "./sse-client";

/**
 * The org-wide live feed, `GET /events/stream` (the backend's other half of
 * FRD-12). One persistent SSE connection for the whole console, shared by
 * every `useLive` subscriber — not one connection per widget.
 *
 * This is what makes `useLive`'s polling honest rather than the only
 * mechanism: a matching backend event triggers an immediate refresh, and the
 * interval timer stays only as the fallback for a connection that is
 * reconnecting. Reconnects with backoff — this is exactly the "future global
 * feed" the per-execution stream's D-024 comment said would need to opt in
 * explicitly, since a single dropped connection here must not silently stop
 * every screen in the console from updating.
 */

type Listener = () => void;

const listeners = new Set<Listener>();
let startedRoleKey: string | null = null;

function notify() {
  for (const listener of listeners) listener();
}

async function connectOnce(signal: AbortSignal): Promise<void> {
  const auth = await getAuthHeader();
  const res = await fetch(`${API_BASE}/events/stream`, {
    headers: { Authorization: auth },
    signal,
  });
  if (!res.body) throw new Error("no response body");
  await readSseBody(res.body, () => notify(), signal);
}

async function connectLoop(signal: AbortSignal): Promise<void> {
  let attempt = 0;
  while (!signal.aborted) {
    try {
      await connectOnce(signal);
      attempt = 0; // a clean disconnect resets backoff; only failures grow it
    } catch {
      // fall through to the backoff below and try again
    }
    if (signal.aborted) return;
    attempt += 1;
    const delayMs = Math.min(1000 * 2 ** attempt, 15000);
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
}

let controller: AbortController | null = null;

/** (Re)starts the shared connection. Safe to call repeatedly. */
function ensureStarted() {
  // Which dev token a request carries (when there is no real session — see
  // api-client.ts's devToken) now follows the current URL's role prefix
  // rather than a switchable stored value, and the scope this stream is
  // allowed to see is resolved once per connection — keyed on the role
  // segment only (not the full path), so navigating between pages under the
  // same role reuses one connection, and navigating between /admin and
  // /user (which remounts every page under that route segment, re-running
  // this) opens a fresh one instead of pushing the old role's events.
  const roleKey =
    typeof window === "undefined" ? "server" : window.location.pathname.startsWith("/user") ? "user" : "admin";
  if (controller && startedRoleKey === roleKey) return;

  controller?.abort();
  controller = new AbortController();
  startedRoleKey = roleKey;
  connectLoop(controller.signal);
}

/**
 * Subscribes to "something changed" notifications from the global feed.
 * The listener carries no event detail on purpose — callers already know how
 * to refetch their own data; this only tells them *when*.
 */
export function subscribeGlobalEvents(listener: Listener): () => void {
  ensureStarted();
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
