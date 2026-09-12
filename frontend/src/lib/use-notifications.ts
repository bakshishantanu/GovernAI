"use client";

import { useCallback, useState } from "react";
import { fetchApi } from "./api-client";
import { useLive } from "./use-live";
import type { TicketDraft } from "./types";

/**
 * One thing worth a person's attention right now, surfaced in the header
 * bell. `href` is role-relative (no `/admin`/`/user` prefix) — callers
 * prepend their own `useRoleBase()`, same as every other in-console link.
 */
export type Notification = {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  at: string;
  seen: boolean;
};

const SEEN_KEY = "governai:seenNotifications";

function loadSeen(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(SEEN_KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

function saveSeen(ids: Set<string>) {
  try {
    window.localStorage.setItem(SEEN_KEY, JSON.stringify([...ids]));
  } catch {
    // Storage unavailable (private browsing, quota) - the badge count just
    // stops shrinking on click; nothing else in the app depends on this.
  }
}

function fromDraft(d: TicketDraft): Omit<Notification, "seen"> {
  return {
    id: d.id,
    title: `Draft reply ready: ${d.ticket_id}`,
    subtitle: d.agent_name ?? "Unknown agent",
    href: "/drafts",
    at: d.created_at,
  };
}

/**
 * Live "needs your attention" feed for the header bell. Currently one real
 * source — pending ticket drafts, the same `GET /ticket-drafts/` the drafts
 * queue and its sidebar badge already use, already scoped server-side
 * (org-wide for admin, owned/assigned agents for a builder) — so this never
 * needs its own visibility rule. Shaped so a second source (e.g. a newly
 * suspended agent) is one more fetch-and-map away, not a rewrite.
 *
 * A notification permanently leaves the list the moment its underlying
 * draft is approved or rejected (drops out of `PENDING_REVIEW` server-side).
 * Separately, `markSeen` gives a lighter-weight "I've looked at this" signal
 * for the badge count alone — clicking through to a notification shouldn't
 * require actually resolving the draft just to stop the bell nagging about
 * it. Seen ids are kept client-side (localStorage, per browser) and pruned
 * to whatever is still actually pending on every load, so this never grows
 * unbounded or resurrects a count for a draft that's long since resolved.
 */
export function useNotifications() {
  const [seen, setSeen] = useState<Set<string>>(loadSeen);

  const load = useCallback(async () => {
    const data = await fetchApi("/ticket-drafts/?draft_status=PENDING_REVIEW").catch(() => []);
    const drafts = (Array.isArray(data) ? data : []) as TicketDraft[];
    const list = drafts
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .map(fromDraft);

    // Drop seen ids for drafts that are no longer pending (approved,
    // rejected, or otherwise gone) - keeps localStorage from accumulating
    // ids forever and lets a re-raised draft with the same id notify again.
    setSeen((prev) => {
      const stillPending = new Set(list.map((n) => n.id));
      const next = new Set([...prev].filter((id) => stillPending.has(id)));
      if (next.size !== prev.size) saveSeen(next);
      return next;
    });

    return list;
  }, []);

  const { data, refresh } = useLive(load, 30000);
  const notifications: Notification[] = (data ?? []).map((n) => ({ ...n, seen: seen.has(n.id) }));

  const markSeen = useCallback((id: string) => {
    setSeen((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev).add(id);
      saveSeen(next);
      return next;
    });
  }, []);

  const pendingCount = notifications.filter((n) => !n.seen).length;

  return { notifications, pendingCount, markSeen, refresh };
}
