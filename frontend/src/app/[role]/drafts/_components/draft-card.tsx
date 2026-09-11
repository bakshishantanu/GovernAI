"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bot,
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  Ticket,
  X,
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
 * here). Reject opens a small dialog for an optional note, since that note
 * is the audit trail for why a reply was killed.
 */
export function DraftCard({
  draft,
  onApprove,
  onReject,
}: {
  draft: TicketDraft;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string, note: string | null) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [confirmingApprove, setConfirmingApprove] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);

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

  async function handleReject() {
    setBusy("reject");
    try {
      await onReject(draft.id, note.trim() || null);
    } finally {
      setBusy(null);
      setRejecting(false);
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

      {draft.status === "REJECTED" && draft.review_note && (
        <p className="mt-2 text-[12px] text-[var(--l-charcoal)]/60">
          <span className="font-semibold">Reject note:</span> {draft.review_note}
        </p>
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
                onClick={() => setRejecting(true)}
                disabled={busy !== null}
              >
                <X className="h-3.5 w-3.5" />
                Reject
              </Button>
              <Button onClick={() => setConfirmingApprove(true)} disabled={busy !== null}>
                <Check className="h-3.5 w-3.5" />
                Approve and post
              </Button>
            </div>
          )}
        </div>
      )}

      <Dialog open={rejecting} onOpenChange={setRejecting}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject reply to {draft.ticket_id}?</DialogTitle>
            <DialogDescription>
              Nothing is sent to Jira. An optional note is kept as the record of why this reply
              was killed.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Why is this being rejected? (optional)"
            rows={4}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejecting(false)} disabled={busy !== null}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleReject} disabled={busy !== null}>
              {busy === "reject" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Reject draft
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
