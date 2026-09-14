"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowUpCircle,
  Bot,
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  Ticket,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { timeAgo } from "@/lib/time-ago";
import type { TicketDraft } from "@/lib/types";

const BODY_CLAMP_LINES = 6;

/**
 * One drafted reply, awaiting a human decision before it can reach the
 * customer. Approve asks for a confirm step first — this posts a real
 * message to a real ticket, so a stray click must not be enough on its own
 * (see /drafts spec: "single click without confirmation" is not appropriate
 * here). Escalate opens a small dialog for an optional note (the audit
 * trail for why it needed a more senior reviewer) — it also posts to the
 * ticket, a fixed reassuring reply, so the requester is never left wondering
 * whether anyone saw it.
 */
export function DraftCard({
  draft,
  onApprove,
  onEscalate,
}: {
  draft: TicketDraft;
  onApprove: (id: string) => Promise<void>;
  onEscalate: (id: string, note: string | null) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [confirmingApprove, setConfirmingApprove] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "escalate" | null>(null);

  const isPending = draft.status === "PENDING_REVIEW";
  const lineCount = draft.body.split("\n").length;
  const clampable = lineCount > BODY_CLAMP_LINES || draft.body.length > 420;

  async function handleApprove() {
    setBusy("approve");
    try {
      await onApprove(draft.id);
    } finally {
      setBusy(null);
      setConfirmingApprove(false);
    }
  }

  async function handleEscalate() {
    setBusy("escalate");
    try {
      await onEscalate(draft.id, note.trim() || null);
    } finally {
      setBusy(null);
      setEscalating(false);
      setNote("");
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.25 }}
      className="rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--l-cream-deep)]">
            <Ticket className="h-4 w-4 text-[var(--l-orange-deep)]" />
          </span>
          <div className="min-w-0">
            {draft.ticket_url ? (
              <a
                href={draft.ticket_url}
                target="_blank"
                rel="noreferrer"
                className="landing-display text-base text-[var(--l-ink)] hover:underline"
              >
                {draft.ticket_id}
              </a>
            ) : (
              <p className="landing-display text-base text-[var(--l-ink)]">{draft.ticket_id}</p>
            )}
            <p className="flex items-center gap-1 text-[12px] text-[var(--l-charcoal)]/55">
              <Bot className="h-3 w-3" />
              {draft.agent_name ?? "Unknown agent"}
            </p>
          </div>
        </div>
        <span className="font-mono text-[11px] text-[var(--l-charcoal)]/45">
          {timeAgo(draft.created_at)}
        </span>
      </div>

      <div className="mt-3 rounded-xl border border-dashed border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/30 p-3">
        <p
          className={`whitespace-pre-wrap text-[13.5px] leading-relaxed text-[var(--l-charcoal)]/85 ${
            clampable && !expanded ? "line-clamp-6" : ""
          }`}
        >
          {draft.body}
        </p>
        {clampable && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="mt-1.5 flex items-center gap-1 text-[12px] font-semibold text-[var(--l-orange-deep)] hover:underline"
          >
            {expanded ? (
              <>
                Show less <ChevronUp className="h-3 w-3" />
              </>
            ) : (
              <>
                Show more <ChevronDown className="h-3 w-3" />
              </>
            )}
          </button>
        )}
      </div>

      {draft.status === "UNDER_REVIEW" && (
        <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-[var(--l-yellow-pale)]/40 px-2.5 py-2 text-[12px] text-[var(--l-charcoal)]/75">
          <ArrowUpCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--l-orange-deep)]" />
          <span>
            Escalated for higher-authority review. Still open — the requester has been told
            their issue is under review.
            {draft.review_note && (
              <>
                {" "}
                <span className="font-semibold">Note:</span> {draft.review_note}
              </>
            )}
          </span>
        </div>
      )}

      {isPending && (
        <div className="mt-3 border-t-2 border-dashed border-[var(--l-ink)]/10 pt-3">
          {confirmingApprove ? (
            <div className="flex flex-wrap items-center gap-2 rounded-xl bg-[var(--l-yellow-pale)]/40 p-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0 text-[var(--l-orange-deep)]" />
              <p className="min-w-0 flex-1 text-[12.5px] text-[var(--l-charcoal)]/80">
                This will post the reply to {draft.ticket_id}.
              </p>
              <div className="flex shrink-0 gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setConfirmingApprove(false)}
                  disabled={busy !== null}
                >
                  Cancel
                </Button>
                <Button size="sm" onClick={handleApprove} disabled={busy !== null}>
                  {busy === "approve" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Check className="h-3.5 w-3.5" />
                  )}
                  Confirm post
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setEscalating(true)}
                disabled={busy !== null}
              >
                <ArrowUpCircle className="h-3.5 w-3.5" />
                Send to review
              </Button>
              <Button onClick={() => setConfirmingApprove(true)} disabled={busy !== null}>
                <Check className="h-3.5 w-3.5" />
                Approve and post
              </Button>
            </div>
          )}
        </div>
      )}

      <Dialog open={escalating} onOpenChange={setEscalating}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send {draft.ticket_id} to higher-authority review?</DialogTitle>
            <DialogDescription>
              This posts a fixed reply to {draft.ticket_id} letting the requester know their
              issue is under review and will be fixed. The ticket moves to Under review — it
              stays open, not closed, until a more senior reviewer approves the actual fix. An
              optional note explains why it needed escalating.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Why does this need a higher-authority review? (optional)"
            rows={4}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEscalating(false)} disabled={busy !== null}>
              Cancel
            </Button>
            <Button onClick={handleEscalate} disabled={busy !== null}>
              {busy === "escalate" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Send to review
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
