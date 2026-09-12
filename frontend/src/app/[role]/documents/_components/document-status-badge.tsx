"use client";

import { useEffect, useState } from "react";
import { Clock, Loader2, CheckCircle2, XCircle } from "lucide-react";
import type { LibraryDocument } from "@/lib/document-types";

function elapsedLabel(sinceIso: string | null): string {
  if (!sinceIso) return "";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(sinceIso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

/**
 * Ingestion is slow (a long PDF can take minutes, per the backend's own
 * spec) and there is no progress percentage - a spinner with no elapsed time
 * reads as a hang past a few seconds. Ticks its own 1s timer, but only while
 * genuinely in flight, so a READY/FAILED row does no work at all.
 */
export function DocumentStatusBadge({ doc }: { doc: LibraryDocument }) {
  const inFlight = doc.status === "PENDING" || doc.status === "PROCESSING";
  const [, forceTick] = useState(0);

  useEffect(() => {
    if (!inFlight) return;
    const id = setInterval(() => forceTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [inFlight]);

  if (doc.status === "PENDING") {
    return (
      <span className="flex items-center gap-1.5 text-[12.5px] font-medium text-[var(--l-charcoal)]/60">
        <Clock className="h-3.5 w-3.5" />
        Queued
      </span>
    );
  }

  if (doc.status === "PROCESSING") {
    return (
      <span className="flex items-center gap-1.5 text-[12.5px] font-medium text-[var(--l-orange-deep)]">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Reading and indexing… {elapsedLabel(doc.created_at)}
      </span>
    );
  }

  if (doc.status === "FAILED") {
    return (
      <span className="flex items-start gap-1.5 text-[12.5px] font-medium text-[var(--l-orange-deep)]">
        <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>{doc.error || "Ingestion failed."}</span>
      </span>
    );
  }

  // Null, not zero, for a format with no page concept (DOCX) or for a seed
  // document outside the normal ingestion pipeline entirely - saying
  // "0 pages" in either case would read as broken/empty rather than what it
  // actually is. Show whichever counts are real; if neither is, "Indexed"
  // alone is still an honest, complete answer.
  const pagesPart = doc.page_count !== null ? `${doc.page_count} page${doc.page_count === 1 ? "" : "s"}` : null;
  const sectionsPart =
    doc.chunk_count !== null ? `${doc.chunk_count} section${doc.chunk_count === 1 ? "" : "s"} indexed` : null;
  const label = [pagesPart, sectionsPart].filter(Boolean).join(", ") || "Indexed";

  return (
    <span className="flex items-center gap-1.5 text-[12.5px] font-medium text-[var(--l-teal)]">
      <CheckCircle2 className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}
