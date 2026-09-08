"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { AlertCircle, ArrowLeft, ArrowRight, Hammer } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useLive } from "@/lib/use-live";
import { timeAgo } from "@/lib/time-ago";
import type { AgentRequest } from "@/lib/types";
import { REQUEST_STATUS, shortId } from "./request-status";
import { BuildAgentDialog } from "./build-agent-dialog";

/**
 * One request, in full, with whatever you can do about it.
 *
 * The backend returns 404 both when a request does not exist and when it is
 * not yours to see — deliberately, so probing ids reveals nothing. This page
 * repeats that: one "not found", never "exists but not for you".
 */
export function RequestDetail({ id }: { id: string }) {
  const { isBuilder, isAdmin, isUser } = useAuth();
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [buildOpen, setBuildOpen] = useState(false);
  const [missing, setMissing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = (await fetchApi(`/agent-requests/${id}`)) as AgentRequest;
      setMissing(false);
      return data;
    } catch (err) {
      setMissing(true);
      throw err;
    }
  }, [id]);

  const { data: request, refresh } = useLive(load, 20000);

  async function act(action: "claim" | "cancel") {
    setBusy(true);
    setActionError(null);
    try {
      await fetchApi(`/agent-requests/${id}/${action}`, { method: "POST" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      setActionError(
        /already claimed/i.test(message)
          ? "Someone else claimed this first."
          : message || "That did not go through. Nothing was changed."
      );
    } finally {
      setBusy(false);
      refresh();
    }
  }

  if (missing && !request) {
    return (
      <div className="mx-auto max-w-2xl py-20 text-center">
        <p className="landing-display text-2xl text-[var(--l-ink)]">No such request</p>
        <p className="mx-auto mt-2 max-w-[48ch] text-sm text-[var(--l-charcoal)]/60">
          It may have been cancelled, or it may not be yours to see.
        </p>
        <Link
          href="/requests"
          className="mt-6 inline-flex items-center gap-2 rounded-full border-2 border-[var(--l-line)] px-4 py-2 text-[13px] font-semibold text-[var(--l-ink)] transition-colors hover:border-[var(--l-ink)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to requests
        </Link>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="mx-auto max-w-3xl space-y-4" aria-busy="true">
        <div className="h-6 w-40 animate-pulse rounded-full bg-[var(--l-line)]/60" />
        <div className="h-[220px] animate-pulse rounded-3xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40" />
        <div className="h-[120px] animate-pulse rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40" />
      </div>
    );
  }

  const s = REQUEST_STATUS[request.status];
  const StatusIcon = s.icon;
  const canClaim = request.status === "PENDING" && (isBuilder || isAdmin) && !isUser;
  const canBuild = request.status === "CLAIMED" && (isBuilder || isAdmin) && !isUser;
  const canCancel =
    (request.status === "PENDING" || request.status === "CLAIMED") && (isUser || isAdmin);

  const steps = [
    { label: "Asked for", at: request.created_at, done: true },
    {
      label: "Picked up",
      at: request.claimed_at,
      done: Boolean(request.claimed_at),
    },
    {
      label: "Handed over",
      at: request.fulfilled_at,
      done: Boolean(request.fulfilled_at),
    },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link
        href="/requests"
        className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-[var(--l-charcoal)]/55 transition-colors hover:text-[var(--l-orange-deep)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All requests
      </Link>

      <motion.article
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="rounded-3xl border-2 border-[var(--l-ink)] bg-[var(--l-cream)] p-6"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="landing-display max-w-[24ch] text-[28px] leading-tight text-[var(--l-ink)]">
            {request.title}
          </h1>
          <span
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-[12.5px] font-semibold text-[var(--l-ink)]"
            style={{ background: s.fill }}
          >
            <StatusIcon className="h-3.5 w-3.5" style={{ color: s.pip }} />
            {s.label}
          </span>
        </div>

        <p className="mt-1 text-[13px] text-[var(--l-charcoal)]/60">{s.meaning}</p>

        <p className="mt-4 max-w-[70ch] whitespace-pre-line text-[15px] leading-relaxed text-[var(--l-charcoal)]/85">
          {request.description}
        </p>

        <div className="mt-5">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/45">
            Skills they suggested
          </span>
          {request.requested_skills.length === 0 ? (
            <p className="mt-1.5 text-[13px] text-[var(--l-charcoal)]/55">
              None — the builder decides what it needs.
            </p>
          ) : (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {request.requested_skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full bg-[var(--l-cream-deep)] px-2.5 py-1 font-mono text-[11.5px] text-[var(--l-ink)]"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>

        {actionError && (
          <p
            role="status"
            className="mt-5 flex items-start gap-2 rounded-xl border-2 border-[var(--l-orange-deep)] bg-[var(--l-orange-soft)]/25 px-3.5 py-2.5 text-sm text-[var(--l-ink)]"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {actionError}
          </p>
        )}

        {(canClaim || canBuild || canCancel || request.agent_id) && (
          <div className="mt-6 flex flex-wrap items-center gap-3 border-t-2 border-dashed border-[var(--l-ink)]/15 pt-5">
            {canClaim && (
              <motion.button
                type="button"
                onClick={() => act("claim")}
                disabled={busy}
                whileHover={busy ? undefined : { scale: 1.03 }}
                whileTap={busy ? undefined : { scale: 0.97 }}
                className="inline-flex h-11 items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 text-sm font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)] disabled:opacity-50"
              >
                <Hammer className="h-4 w-4" />
                {busy ? "Claiming…" : "I'll build this"}
              </motion.button>
            )}

            {canBuild && (
              <motion.button
                type="button"
                onClick={() => setBuildOpen(true)}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="inline-flex h-11 items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 text-sm font-semibold text-white transition-colors hover:bg-[var(--l-orange-deep)]"
              >
                <Hammer className="h-4 w-4" />
                Build the agent
              </motion.button>
            )}

            {request.agent_id && (
              <Link
                href={`/agents/${request.agent_id}`}
                className="inline-flex h-11 items-center gap-2 rounded-full border-2 border-[var(--l-ink)] px-5 text-sm font-semibold text-[var(--l-ink)] transition-colors hover:bg-[var(--l-cream-deep)]"
              >
                Open the agent
                <ArrowRight className="h-4 w-4" />
              </Link>
            )}

            {canCancel && (
              <button
                type="button"
                onClick={() => act("cancel")}
                disabled={busy}
                className="text-[13px] text-[var(--l-charcoal)]/55 transition-colors hover:text-[var(--l-ink)] hover:underline disabled:opacity-50"
              >
                {busy ? "Working…" : "Cancel this request"}
              </button>
            )}
          </div>
        )}
      </motion.article>

      <section
        aria-label="Progress"
        className="rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-5"
      >
        <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/45">
          Progress
        </h2>
        <ol className="mt-3 space-y-3">
          {steps.map((step, i) => (
            <li key={step.label} className="flex items-start gap-3">
              <span
                aria-hidden
                className="mt-[3px] flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2"
                style={{
                  borderColor: step.done ? "var(--l-teal)" : "var(--l-line)",
                  background: step.done ? "var(--l-teal)" : "transparent",
                }}
              />
              <span className="min-w-0">
                <span
                  className="block text-[14px] font-semibold"
                  style={{
                    color: step.done ? "var(--l-ink)" : "var(--l-charcoal)",
                    opacity: step.done ? 1 : 0.45,
                  }}
                >
                  {step.label}
                </span>
                <span className="gv-num block font-mono text-[11.5px] text-[var(--l-charcoal)]/45">
                  {step.at
                    ? timeAgo(step.at)
                    : request.status === "CANCELLED"
                      ? "did not happen"
                      : i === 1
                        ? "waiting for a builder"
                        : "not yet"}
                </span>
              </span>
            </li>
          ))}
        </ol>

        <p className="gv-num mt-4 border-t-2 border-dashed border-[var(--l-ink)]/10 pt-3 font-mono text-[11px] text-[var(--l-charcoal)]/40">
          {shortId(request.id)}
        </p>
      </section>

      <BuildAgentDialog
        request={request}
        open={buildOpen}
        onClose={() => {
          setBuildOpen(false);
          refresh();
        }}
      />
    </div>
  );
}
