/** Matches what GET/POST /documents/{id} actually returns, per the backend's
 * own UI spec (feat/document-upload-rag). `page_count`/`chunk_count` are only
 * meaningful once `status` reaches READY - null before that, not zero, since
 * zero would falsely claim the document was read and found empty. */
export type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED";

export interface LibraryDocument {
  id: string;
  title: string;
  filename: string | null;
  mime_type: string | null;
  status: DocumentStatus;
  error: string | null;
  page_count: number | null;
  chunk_count: number | null;
  access_scope: string[];
  source: string;
  created_at: string | null;
}

/** Still mid-ingestion - the state a document's own row keeps polling in. */
export function isInFlight(doc: LibraryDocument): boolean {
  return doc.status === "PENDING" || doc.status === "PROCESSING";
}
