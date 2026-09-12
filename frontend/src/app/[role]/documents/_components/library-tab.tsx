"use client";

import { FileText } from "lucide-react";
import { useDocuments } from "@/lib/use-documents";
import { UploadDropzone } from "./upload-dropzone";
import { DocumentRow } from "./document-row";

export function LibraryTab() {
  const { documents, uploadDocument, deleteDocument } = useDocuments();
  const loading = documents === null;

  return (
    <div className="space-y-5">
      <UploadDropzone onUpload={uploadDocument} />

      {loading ? (
        <div className="space-y-2">
          {[0, 1].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-2xl bg-[var(--l-line)]/40" />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-[var(--l-line)] px-6 py-14 text-center">
          <FileText className="mx-auto h-5 w-5 text-[var(--l-charcoal)]/30" />
          <p className="landing-display mt-2 text-base text-[var(--l-ink)]">No documents yet</p>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            Upload a PDF above to make it searchable by a Document Search agent.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {(documents ?? []).map((doc) => (
            <DocumentRow key={doc.id} doc={doc} onDelete={deleteDocument} />
          ))}
        </div>
      )}
    </div>
  );
}
