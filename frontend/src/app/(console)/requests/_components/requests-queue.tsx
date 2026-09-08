"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertCircle, ArrowRight, Hammer, RotateCw, Search } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useLive } from "@/lib/use-live";
import { timeAgo } from "@/lib/time-ago";
import type { AgentRequest, AgentRequestStatus } from "@/lib/types";
import { REQUEST_STATUS, STATUS_ORDER, shortId } from "./request-status";

type Filter = "ALL" | AgentRequestStatus;

/**
 * The requests queue.
 *
 * The same route serves all three roles because the backend already decides
 * what each one may see — a User's list is their own requests, a Builder's is
 * the org's. Only the framing changes, so there is one screen to keep correct
 * rather than three.
 *
 * Ordering is oldest-first within Waiting: a queue that surfaces the newest
 * request first is how things sit unclaimed forever.
 */
export function RequestsQueue() {
  const { isBuilder, isAdmin, isUser } = useAuth();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchApi("/agent-requests/");
    return (Array.isArray(data) ? data : []) as AgentRequest[];
  }, []);

  const { data, updatedAt, refresh } = useLive(load);
  const loading = data === null;
  const requests = useMemo(() => data ?? [], [data]);

  const counts = useMemo(() => {
    const c: Record<Filter, number> = {
      ALL: requests.length,
      PENDING: 0,
      CLAIMED: 0,
      FULFILLED: 0,
      CANCELLED: 0,
    };
    for (const r of requests) if (r.status in c) c[r.status] += 1;
    return c;
  }, [requests]);

  const visible = useMemo(() => {
    let list = filter === "ALL" ? [...requests] : requests.filter((r) => r.status === filter);
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.description.toLowerCase().includes(q) ||
          r.requested_skills.some((s) => s.toLowerCase().includes(q))
      );
    }
    // Waiting first, then oldest first inside each group: the thing that has
    // been ignored longest should be the hardest to ignore.
    const rank: Record<string, number> = { PENDING: 0, CLAIMED: 1, FULFILLED: 2, CANCELLED: 3 };
    return list.sort(
      (a, b) =>
        (rank[a.status] ?? 9) - (rank[b.status] ?? 9) ||
        +new Date(a.created_at) - +new Date(b.created_at)
    );
  }, [requests, filter, query]);

  async function act(id: string, action: "claim" | "cancel") {
    setBusyId(id);
    setActionError(null);
    try {
      await fetchApi(`/agent-requests/${id}/${action}`, { method: "POST" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      // 409 is the real, expected outcome of two builders reaching for the
      // same request. Say what happened rather than showing a raw error.
      setActionError(
        /already claimed/i.test(message)
          ? "Someone else claimed that one first — the queue has been refreshed."
          : message || "That did not go through. Nothing was changed."
      );
    } finally {
      setBusyId(null);
      refresh();
    }
  }

  const heading = isUser ? "Your requests" : isAdmin ? "Every request" : "The queue";
  const blurb = isUser
    ? "Everything you have asked for, and where each one has got to."
    : isAdmin
      ? "Every request in the organisation, waiting ones first."
      : "What people have asked for. Claim one to build it — the request is then yours, and activating the agent hands it straight back.";

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="landing-display text-3xl text-[var(--l-ink)]">{heading}</h1>
          <p className="mt-1 max-w-[68ch] text-sm text-[var(--l-charcoal)]/60">{blurb}</p>
        </div>
        <span className="text-[11.5px] text-[var(--l-charcoal)]/40">
          {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
        </span>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap items-center gap-1 rounded-full bg-[var(--l-cream-deep)] p-1">
          {(["ALL", ...STATUS_ORDER] as Filter[]).map((f) => {
            const isOn = filter === f;
            const label = f === "ALL" ? "All" : REQUEST_STATUS[f].label;
            return (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                aria-pressed={isOn}
                className="relative rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors"
                style={{ color: isOn ? "#ffffff" : "var(--l-charcoal)" }}
              >
                {isOn && (
                  <motion.span
                    layoutId="requests-filter-pill"
                    className="absolute inset-0 rounded-full bg-[var(--l-orange)]"
                    transition={{ type: "spring", stiffness: 500, damping: 38 }}
                  />
                )}
                <span className="relative z-10">
                  {label}{" "}
                  <span className="gv-num opacity-60">{counts[f]}</span>
                </span>
              </button>
            );
          })}
        </div>

        <label className="relative min-w-[200px] flex-1">
          <span className="sr-only">Search requests</span>
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--l-charcoal)]/35" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title, detail or skill"
            className="h-10 w-full rounded-full border-2 border-[var(--l-line)] bg-[var(--l-cream)] pl-10 pr-3.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
          />
        </label>
      </div>

      {actionError && (
        <p
          role="status"
          className="flex items-start gap-2 rounded-2xl border-2 border-[var(--l-orange-deep)] bg-[var(--l-orange-soft)]/25 px-4 py-3 text-sm text-[var(--l-ink)]"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {actionError}
        </p>
      )}

      {loading ? (
        <ul className="space-y-2" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <li
              key={i}
              className="h-[132px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40"
            />
          ))}
        </ul>
      ) : visible.length === 0 ? (
        <EmptyState
          filter={filter}
          searching={query.trim().length > 0}
          isUser={isUser}
          onClear={() => {
            setQuery("");
            setFilter("ALL");
          }}
        />
      ) : (
        <ul className="space-y-2">
          {visible.map((req, i) => {
            const s = REQUEST_STATUS[req.status];
            const Icon = s.icon;
            const canClaim = req.status === "PENDING" && (isBuilder || isAdmin) && !isUser;
            const canCancel =
              (req.status === "PENDING" || req.status === "CLAIMED") && (isUser || isAdmin);
            const busy = busyId === req.id;

            return (
              <motion.li
                key={req.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i, 8) * 0.035 }}
                className="rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4 transition-colors hover:border-[var(--l-ink)]"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/requests/${req.id}`}
                      className="text-[16px] font-semibold leading-snug text-[var(--l-ink)] hover:underline"
                    >
                      {req.title}
                    </Link>
                    <p className="mt-1 line-clamp-2 max-w-[80ch] text-[13.5px] leading-snug text-[var(--l-charcoal)]/70">
                      {req.description}
                    </p>
                  </div>
                  <span
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-semibold text-[var(--l-ink)]"
                    style={{ background: s.fill }}
                  >
                    <Icon className="h-3.5 w-3.5" style={{ color: s.pip }} />
                    {s.label}
                  </span>
                </div>

                {req.requested_skills.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {req.requested_skills.map((skill) => (
                      <span
                        key={skill}
                        className="rounded-full bg-[var(--l-cream-deep)] px-2.5 py-0.5 font-mono text-[11px] text-[var(--l-ink)]"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}

                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t-2 border-dashed border-[var(--l-ink)]/10 pt-3">
                  <span className="gv-num font-mono text-[11px] text-[var(--l-charcoal)]/45">
                    {shortId(req.id)} · asked {timeAgo(req.created_at)}
                  </span>

                  <span className="flex flex-wrap items-center gap-3">
                    {canCancel && (
                      <button
                        type="button"
                        onClick={() => act(req.id, "cancel")}
                        disabled={busy}
                        className="text-[12.5px] text-[var(--l-charcoal)]/55 transition-colors hover:text-[var(--l-ink)] hover:underline disabled:opacity-50"
                      >
                        {busy ? "Working…" : "Cancel"}
                      </button>
                    )}
                    {canClaim ? (
                      <motion.button
                        type="button"
                        onClick={() => act(req.id, "claim")}
                        disabled={busy}
                        whileHover={busy ? undefined : { scale: 1.04 }}
                        whileTap={busy ? undefined : { scale: 0.96 }}
                        className="inline-flex h-9 items-center gap-1.5 rounded-full bg-[var(--l-orange)] px-4 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)] disabled:opacity-50"
                      >
                        <Hammer className="h-3.5 w-3.5" />
                        {busy ? "Claiming…" : "I'll build this"}
                      </motion.button>
                    ) : (
                      <Link
                        href={
                          req.status === "FULFILLED" && req.agent_id
                            ? `/agents/${req.agent_id}`
                            : `/requests/${req.id}`
                        }
                        className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--l-charcoal)]/55 transition-colors hover:text-[var(--l-orange-deep)]"
                      >
                        {req.status === "FULFILLED" && req.agent_id ? "Open the agent" : "Details"}
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    )}
                  </span>
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/**
 * Empty is not one state. "Nothing exists yet", "nothing matches this filter"
 * and "nothing matches this search" need different words and different exits.
 */
function EmptyState({
  filter,
  searching,
  isUser,
  onClear,
}: {
  filter: Filter;
  searching: boolean;
  isUser: boolean;
  onClear: () => void;
}) {
  const filtered = filter !== "ALL" || searching;

  return (
    <div className="rounded-2xl border-2 border-dashed border-[var(--l-line)] bg-[var(--l-cream)] px-6 py-14 text-center">
      <p className="landing-display text-lg text-[var(--l-ink)]">
        {filtered
          ? "Nothing matches"
          : isUser
            ? "You have not asked for anything yet"
            : "The queue is clear"}
      </p>
      <p className="mx-auto mt-1 max-w-[52ch] text-sm text-[var(--l-charcoal)]/60">
        {filtered
          ? "No request fits that filter or search."
          : isUser
            ? "Describe a job and a builder will put an agent together for you."
            : "Nothing is waiting. New requests appear here as people send them."}
      </p>

      {filtered ? (
        <button
          type="button"
          onClick={onClear}
          className="mt-4 inline-flex items-center gap-1.5 rounded-full border-2 border-[var(--l-line)] px-4 py-2 text-[13px] font-semibold text-[var(--l-ink)] transition-colors hover:border-[var(--l-ink)]"
        >
          <RotateCw className="h-3.5 w-3.5" />
          Show everything
        </button>
      ) : isUser ? (
        <Link
          href="/request-agent"
          className="mt-4 inline-flex h-10 items-center rounded-full bg-[var(--l-orange)] px-5 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)]"
        >
          Ask for an agent
        </Link>
      ) : null}
    </div>
  );
}
