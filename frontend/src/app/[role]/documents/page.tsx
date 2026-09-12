"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { FolderOpen } from "lucide-react";
import { LibraryTab } from "./_components/library-tab";
import { AskTab } from "./_components/ask-tab";

type Tab = "library" | "ask";

const TABS: { id: Tab; label: string }[] = [
  { id: "library", label: "Library" },
  { id: "ask", label: "Ask" },
];

/**
 * Upload documents, watch them get indexed, and ask questions against them
 * with citations — the console side of the RAG pipeline the backend already
 * runs. Two tabs on one page rather than two separate routes: it's one
 * feature area, and the Ask tab needs the Library's own document list
 * anyway (to title-match citations), so keeping them siblings avoids
 * fetching the same list twice across a route boundary.
 */
export default function DocumentsPage() {
  const [tab, setTab] = useState<Tab>("library");

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="flex items-center gap-2 text-[var(--l-orange)]">
          <FolderOpen className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-[0.14em]">Document library</span>
        </div>
        <h1 className="landing-display mt-2 text-3xl text-[var(--l-ink)]">Upload, index, ask</h1>
        <p className="mt-1 max-w-md text-sm text-[var(--l-charcoal)]/60">
          Upload a PDF, Word doc, deck, or scanned photo, let it get indexed, then ask a Document
          Search agent questions about it — every answer cites where it came from.
        </p>
      </motion.div>

      <div className="inline-flex rounded-full border-2 border-[var(--l-line)] bg-[var(--l-cream-deep)]/40 p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="relative rounded-full px-4 py-1.5 text-sm font-medium transition-colors"
            style={{ color: tab === t.id ? "var(--l-cream)" : "var(--l-charcoal)" }}
          >
            {tab === t.id && (
              <motion.span
                layoutId="documents-tab-pill"
                className="absolute inset-0 rounded-full bg-[var(--l-ink)]"
                transition={{ type: "spring", stiffness: 500, damping: 38 }}
              />
            )}
            <span className="relative z-10">{t.label}</span>
          </button>
        ))}
      </div>

      {tab === "library" ? <LibraryTab /> : <AskTab />}
    </div>
  );
}
