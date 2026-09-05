"use client";

import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { fetchApi } from "@/lib/api-client";
import { streamSse, type SseEvent } from "@/lib/sse-client";

/**
 * One event stream for the whole console — the last piece of [D-010].
 *
 * Every screen that wants to know something is happening subscribes here
 * rather than opening its own connection. A console with six live screens
 * should hold one socket, not six.
 *
 * Unlike the per-execution stream, this one never ends by itself: an
 * organisation has no "done". So reconnection is switched **on** — this is
 * exactly the case `streamSse`'s `shouldReconnect` was built for, and the
 * reason it defaults to off elsewhere.
 *
 * The denial count is seeded from `/audits/` on mount and then maintained
 * live. Seeding matters: a count that starts at zero and only rises while you
 * watch is not "denied this hour", it is "denied since you opened the tab",
 * and on a governance product that difference is the whole point.
 */

type Listener = (event: SseEvent) => void;

type ConsoleEvents = {
  /** The stream is open and delivering. */
  connected: boolean;
  /** Non-null while dropped and retrying. */
  reconnecting: { attempt: number } | null;
  /** Denied tool calls in the last rolling hour, seeded then kept live. */
  deniedLastHour: number;
  /** Bumps on every forwarded event — a cheap dependency for "refetch now". */
  revision: number;
  /** Raw events, for screens that want them. Returns an unsubscribe. */
  subscribe: (listener: Listener) => () => void;
};

const HOUR_MS = 60 * 60 * 1000;

const ConsoleEventsContext = createContext<ConsoleEvents>({
  connected: false,
  reconnecting: null,
  deniedLastHour: 0,
  revision: 0,
  subscribe: () => () => {},
});

export function useConsoleEvents() {
  return useContext(ConsoleEventsContext);
}

export function ConsoleEventsProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState<{ attempt: number } | null>(null);
  const [deniedLastHour, setDeniedLastHour] = useState(0);
  const [revision, setRevision] = useState(0);

  // Timestamps of denials inside the window, so the count can shrink as they
  // age out rather than only ever growing.
  const denialTimes = useRef<number[]>([]);
  const listeners = useRef(new Set<Listener>());

  const recount = useCallback(() => {
    const cutoff = Date.now() - HOUR_MS;
    denialTimes.current = denialTimes.current.filter((t) => t >= cutoff);
    setDeniedLastHour(denialTimes.current.length);
  }, []);

  const subscribe = useCallback((listener: Listener) => {
    listeners.current.add(listener);
    return () => {
      listeners.current.delete(listener);
    };
  }, []);

  // Seed from the audit log so the figure is a real hour, not a session.
  useEffect(() => {
    let cancelled = false;
    fetchApi("/audits/?limit=200")
      .then((data) => {
        if (cancelled) return;
        const cutoff = Date.now() - HOUR_MS;
        const seeded = (Array.isArray(data) ? data : [])
          .filter((e: any) => (e.policy_decision || "").toUpperCase().startsWith("DEN"))
          .map((e: any) => new Date(e.timestamp).getTime())
          .filter((t: number) => !Number.isNaN(t) && t >= cutoff);
        denialTimes.current = seeded;
        setDeniedLastHour(seeded.length);
      })
      .catch(() => {
        /* the live count still works; it just starts from what it sees */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Age denials out of the window even when nothing is arriving.
  useEffect(() => {
    const timer = setInterval(recount, 60_000);
    return () => clearInterval(timer);
  }, [recount]);

  useEffect(() => {
    const controller = new AbortController();

    streamSse(
      "/events/stream",
      {
        onOpen: () => {
          setConnected(true);
          setReconnecting(null);
        },
        onEvent: (event) => {
          if (event.type === "ready") {
            setConnected(true);
            return;
          }

          if (event.type === "audit.tool.denied") {
            denialTimes.current.push(Date.now());
            recount();
          }

          setRevision((n) => n + 1);
          for (const listener of listeners.current) listener(event);
        },
        onReconnecting: (attempt) => {
          setConnected(false);
          setReconnecting({ attempt });
        },
        onClose: () => setConnected(false),
        onError: () => {
          setConnected(false);
          setReconnecting(null);
        },
      },
      controller.signal,
      // An org-wide feed has no natural end, so a body that ends is always a
      // drop worth retrying.
      { shouldReconnect: () => true, retry: { maxAttempts: 20, maxDelayMs: 15_000 } },
    );

    return () => controller.abort();
  }, [recount]);

  return (
    <ConsoleEventsContext.Provider
      value={{ connected, reconnecting, deniedLastHour, revision, subscribe }}
    >
      {children}
    </ConsoleEventsContext.Provider>
  );
}
