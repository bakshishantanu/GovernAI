"use client";

import { motion } from "framer-motion";
import { FolderOpen } from "lucide-react";
import { LibraryTab } from "./_components/library-tab";

/**
 * Upload documents and watch them get indexed — the console side of the RAG
 * pipeline the backend already runs. Once a document is indexed, any agent
 * built with the Document Search skill can search it and cite what it found;
 * asking questions happens through that agent, not on this page.
 */
export default function DocumentsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="flex items-center gap-2 text-[var(--l-orange)]">
          <FolderOpen className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-[0.14em]">Document library</span>
        </div>
        <h1 className="landing-display mt-2 text-3xl text-[var(--l-ink)]">Upload &amp; index</h1>
        <p className="mt-1 max-w-md text-sm text-[var(--l-charcoal)]/60">
          Upload a PDF, Word doc, deck, or scanned photo and let it get indexed — once it's ready,
          any agent built with the Document Search skill can search it and cite exactly where its
          answer came from.
        </p>
      </motion.div>

      <LibraryTab />
    </div>
  );
}
