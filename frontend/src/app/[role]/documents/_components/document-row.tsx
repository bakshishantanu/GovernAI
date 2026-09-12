"use client";

import { useState } from "react";
import { FileText, Loader2, Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { LibraryDocument } from "@/lib/document-types";
import { DocumentStatusBadge } from "./document-status-badge";

/**
 * One document in the library. Delete is irreversible and says so before
 * acting - the same confirm-dialog pattern as deleting a draft agent
 * (lifecycle-track.tsx), since both are "this destroys real state, ask
 * first" actions.
 */
export function DocumentRow({
  doc,
  onDelete,
}: {
  doc: LibraryDocument;
  onDelete: (id: string) => Promise<void>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  async function handleDelete() {
    setDeleting(true);
    setError("");
    try {
      await onDelete(doc.id);
      setConfirming(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this document.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="flex items-start justify-between gap-4 rounded-2xl border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream)] p-4">
      <div className="flex min-w-0 items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--l-cream-deep)]">
          <FileText className="h-4 w-4 text-[var(--l-charcoal)]/60" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[var(--l-ink)]">{doc.title}</p>
          <div className="mt-1">
            <DocumentStatusBadge doc={doc} />
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setConfirming(true)}
        title="Delete document"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[var(--l-charcoal)]/40 transition-colors hover:bg-[var(--l-orange-deep)]/10 hover:text-[var(--l-orange-deep)]"
      >
        <Trash2 className="h-4 w-4" />
      </button>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete &ldquo;{doc.title}&rdquo;?</DialogTitle>
            <DialogDescription>
              This permanently removes the document and every chunk built from it. Any answer that
              cited it will no longer be able to — this cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {error && (
            <p className="text-[12.5px] font-medium text-[var(--l-orange-deep)]">{error}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirming(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Delete document
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
