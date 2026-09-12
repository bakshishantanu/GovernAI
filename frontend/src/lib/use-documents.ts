"use client";

import { useCallback, useState } from "react";
import { fetchApi } from "./api-client";
import { useLive } from "./use-live";
import { isInFlight, type LibraryDocument } from "./document-types";

const FAST_POLL_MS = 3000;
const SLOW_POLL_MS = 30000;

/**
 * The org's document library, with upload/delete actions.
 *
 * Polls at `FAST_POLL_MS` whenever any document is still PENDING/PROCESSING
 * (ingestion is slow - a long PDF can take minutes, per the backend's own
 * spec), and backs off to `SLOW_POLL_MS` once nothing is in flight, rather
 * than hammering the list forever at upload speed. `useLive`'s own interval
 * is a real effect dependency, so flipping this number actually restarts the
 * timer at the new cadence.
 */
export function useDocuments() {
  const [pollMs, setPollMs] = useState(FAST_POLL_MS);

  const load = useCallback(async () => {
    const data = await fetchApi("/documents/").catch(() => []);
    const docs = (Array.isArray(data) ? data : []) as LibraryDocument[];
    setPollMs(docs.some(isInFlight) ? FAST_POLL_MS : SLOW_POLL_MS);
    return docs;
  }, []);

  const { data: documents, updatedAt, refresh } = useLive(load, pollMs);

  const uploadDocument = useCallback(
    async (file: File, title?: string) => {
      const body = new FormData();
      body.append("file", file);
      if (title?.trim()) body.append("title", title.trim());
      const created = (await fetchApi("/documents/", {
        method: "POST",
        body,
      })) as LibraryDocument;
      // The new row is PENDING, so the next poll should already be fast -
      // refresh now rather than waiting out whatever the last interval was.
      setPollMs(FAST_POLL_MS);
      await refresh();
      return created;
    },
    [refresh],
  );

  const deleteDocument = useCallback(
    async (id: string) => {
      await fetchApi(`/documents/${id}`, { method: "DELETE" });
      await refresh();
    },
    [refresh],
  );

  return { documents, updatedAt, uploadDocument, deleteDocument, refresh };
}
