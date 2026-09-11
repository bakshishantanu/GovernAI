"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Inbox, RefreshCw } from "lucide-react";
import { ApiError, fetchApi } from "@/lib/api-client";
import { useLive } from "@/lib/use-live";
import { timeAgo } from "@/lib/time-ago";
import type { TicketDraft, TicketDraftStatus } from "@/lib/types";
import { DraftCard } from "./_components/draft-card";

/**
 * Ticket Draft Review Queue — agents no longer post replies to Jira
 * directly; they compose a reply and park it here. Nothing reaches the
 * customer until a human clicks Approve.
 */

const TABS: { label: string; value: TicketDraftStatus | "" }[] = [
  { label: "Pending", value: "PENDING_REVIEW" },
  { label: "Posted", value: "POSTED" },
  { label: "Rejected", value: "REJECTED" },
];

type Toast = { id: number; kind: "error" | "info"; message: string };
let toastSeq = 0;

export default function TicketDraftsPage() {
  const [filter, setFilter] = useState<TicketDraftStatus | "">("PENDING_REVIEW");
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [loadError, setLoadError] = useState(false);

  const pushToast = useCallback((kind: Toast["kind"], message: string) => {
    const id = ++toastSeq;
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000);
  }, []);

  const load = useCallback(async () => {
    try {
      const data = await fetchApi(`/ticket-drafts/?draft_status=${filter}`);
      setLoadError(false);
      return (Array.isArray(data) ? data : []) as TicketDraft[];
    } catch (e) {
      setLoadError(true);
      throw e;
    }
  }, [filter]);

  const { data: drafts, updatedAt, refresh } = useLive(load);

  // useLive keeps polling the same `load` closure via a ref, so switching
  // tabs needs an explicit refresh — otherwise the list would keep showing
  // the previous filter's rows until the next interval tick.
  useEffect(() => {
    refresh();
  }, [filter, refresh]);

  async function handleApprove(id: string) {
    try {
      await fetchApi(`/ticket-drafts/${id}/approve`, { method: "POST" });
      pushToast("info", "Reply posted.");
      refresh();
    } catch (e) {
      handleActionError(e);
    }
  }

  async function handleReject(id: string, note: string | null) {
    try {
      await fetchApi(`/ticket-drafts/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ note }),
      });
      pushToast("info", "Draft rejected.");
      refresh();
    } catch (e) {
      handleActionError(e);
    }
  }

  function handleActionError(e: unknown) {
    if (e instanceof ApiError) {
      if (e.status === 404) {
        pushToast("error", "Draft no longer available.");
        refresh();
        return;
      }
      if (e.status === 409) {
        pushToast("error", "Someone already reviewed this draft.");
        refresh();
        return;
      }
      if (e.status === 503) {
        pushToast("error", "Ticketing is not connected, cannot post.");
        return;
      }
      pushToast("error", e.message);
      return;
    }
    pushToast("error", "Something went wrong.");
  }

  const loading = drafts === null;
  const count = drafts?.length ?? 0;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-wrap items-end justify-between gap-4"
      >
        <div>
          <div className="flex items-center gap-2 text-[var(--l-orange)]">
            <Inbox className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-[0.14em]">
              Draft replies
            </span>
          </div>
          <h1 className="landing-display mt-2 text-3xl text-[var(--l-ink)]">
            Ticket draft review queue
          </h1>
          <p className="mt-1 max-w-md text-sm text-[var(--l-charcoal)]/60">
            Agents compose replies and park them here. Nothing reaches the customer until you
            approve it.
          </p>
        </div>
        <span className="text-[11.5px] text-[var(--l-charcoal)]/40">
          {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
        </span>
      </motion.div>

      <div className="inline-flex rounded-full border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.label}
            onClick={() => setFilter(tab.value)}
            className="relative rounded-full px-4 py-1.5 text-sm font-medium transition-colors"
            style={{ color: filter === tab.value ? "#ffffff" : "var(--l-charcoal)" }}
          >
            {filter === tab.value && (
              <motion.span
                layoutId="drafts-tab-pill"
                className="absolute inset-0 rounded-full bg-[var(--l-ink)]"
                transition={{ type: "spring", stiffness: 500, damping: 38 }}
              />
            )}
            <span className="relative z-10">{tab.label}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[170px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40"
            />
          ))}
        </div>
      ) : loadError ? (
        <div className="rounded-2xl border-2 border-dashed border-[var(--l-line)] px-6 py-14 text-center">
          <p className="landing-display text-base text-[var(--l-ink)]">Couldn&apos;t load drafts</p>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            The request failed, check your connection and try again.
          </p>
          <button
            onClick={() => refresh()}
            className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-[var(--l-ink)] px-4 py-2 text-xs font-semibold text-[var(--l-cream)]"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      ) : count === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-[var(--l-line)] px-6 py-14 text-center">
          <p className="landing-display text-base text-[var(--l-ink)]">
            {filter === "PENDING_REVIEW" ? "Nothing waiting on review" : "No drafts here"}
          </p>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            {filter === "PENDING_REVIEW"
              ? "A reply shows up here when an agent responds to a ticket."
              : "Nothing has this status yet."}
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          <AnimatePresence mode="popLayout">
            {drafts.map((draft) => (
              <li key={draft.id}>
                <DraftCard
                  draft={draft}
                  onApprove={handleApprove}
                  onReject={handleReject}
                />
              </li>
            ))}
          </AnimatePresence>
        </ul>
      )}

      <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 12, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="pointer-events-auto rounded-xl border-2 px-4 py-2.5 text-sm font-medium shadow-[0_6px_0_0_rgba(22,19,14,0.14)]"
              style={{
                background: t.kind === "error" ? "var(--l-pink-blush)" : "var(--l-teal-soft)",
                borderColor: t.kind === "error" ? "var(--l-orange-deep)" : "var(--l-teal)",
                color: "var(--l-ink)",
              }}
            >
              {t.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
