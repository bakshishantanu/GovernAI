import { BookText } from "lucide-react";
import type { LibraryDocument } from "@/lib/document-types";

/**
 * The model writes "smart" Unicode punctuation - a non-breaking hyphen
 * (U+2011) in "Few‑Shot", a narrow no-break space (U+202F) before a unit -
 * that is invisible to a reader but not to a `===`/`startsWith` comparison
 * against a document title that only ever contains plain ASCII "-" and " ".
 * Found live: a real, correctly-titled citation silently failed to match and
 * rendered as raw bracketed text instead of a chip. Folding both sides to
 * plain ASCII punctuation before comparing (case already handled below)
 * makes the match robust to whichever variant the model happens to use.
 */
function normalizeForMatch(s: string): string {
  return s
    .replace(/[‐-―−]/g, "-")
    .replace(/[  -   ]/g, " ")
    .toLowerCase();
}

/**
 * A citation's locator is format-dependent - "p.32" for a PDF, "slide 7" for
 * a deck, or a full section heading for a Word doc (which can itself contain
 * a comma, e.g. "C. CNN Backbone Configuration, table 1") - so splitting on
 * the first comma would cut a heading in half. Matching the known document
 * title as a literal prefix instead handles every locator shape without
 * needing to parse its contents.
 */
function matchCitation(
  raw: string,
  documents: LibraryDocument[],
): { doc: LibraryDocument; locator: string | null } | null {
  const trimmed = normalizeForMatch(raw.trim());
  for (const doc of documents) {
    const title = normalizeForMatch(doc.title);
    if (trimmed === title) {
      return { doc, locator: null };
    }
    const prefix = `${title}, `;
    if (trimmed.startsWith(prefix)) {
      // Slice the ORIGINAL raw string by the normalized prefix's length:
      // both sides are folded to the same ASCII punctuation set and neither
      // normalization changes string length, so the offset lines up, and the
      // locator keeps its original characters instead of the normalized ones.
      return { doc, locator: raw.trim().slice(prefix.length).trim() || null };
    }
  }
  return null;
}

/**
 * Renders an agent answer with its inline `[Title, locator]`/`[Title]`
 * citations as chips instead of raw brackets. Matched by title against the
 * already-fetched document list (case-insensitive - a model copying a real
 * title verbatim is still not guaranteed to preserve case).
 *
 * A citation is produced by the model copying a string it was given; it is
 * verified server-side, but a model can still write something that matches
 * no document. An unmatched citation renders as plain text, not a broken
 * chip - never throws on a citation this component cannot resolve.
 *
 * The chip's own visible text already names the document and locator, which
 * is the spec's "clicking one should at minimum show which document and
 * page" - satisfied without needing a click handler. A DOCX heading locator
 * can run much longer than "p.32", so the locator segment truncates with an
 * ellipsis rather than growing the chip or wrapping mid-word; the full text
 * is still available as a native tooltip via `title`.
 */
export function CitationText({ text, documents }: { text: string; documents: LibraryDocument[] }) {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  // `matchAll` owns its own iteration state internally rather than mutating
  // a shared regex's `lastIndex` (the earlier `exec`-loop version did, which
  // is unsafe to share across renders/components since a regex literal
  // declared outside the component keeps that state between calls).
  //
  // The model has been observed (live, not per the spec) wrapping a citation
  // in full-width brackets (`【…】`) instead of ASCII `[…]` on some runs -
  // matching both bracket styles rather than only the spec's documented one,
  // so a real citation still renders as a chip instead of silently falling
  // through as unparsed prose.
  for (const match of text.matchAll(/[\[【]([^\]】]+)[\]】]/g)) {
    if (match.index > lastIndex) {
      parts.push(<span key={key++}>{text.slice(lastIndex, match.index)}</span>);
    }

    const matched = matchCitation(match[1], documents);

    if (matched) {
      const { doc, locator } = matched;
      parts.push(
        <span
          key={key++}
          title={locator ? `${doc.title}, ${locator}` : doc.title}
          className="mx-0.5 inline-flex max-w-full items-center gap-1 rounded-full px-2 py-0.5 align-middle text-[11.5px] font-semibold"
          style={{ background: "color-mix(in srgb, var(--l-teal) 14%, transparent)", color: "var(--l-teal)" }}
        >
          <BookText className="h-3 w-3 shrink-0" />
          <span className="shrink-0 whitespace-nowrap">{doc.title}</span>
          {locator !== null && <span className="max-w-[180px] truncate opacity-70">{locator}</span>}
        </span>,
      );
    } else {
      // Unmatched: leave the original bracketed text as plain prose rather
      // than rendering a chip that claims to name a document it cannot find.
      parts.push(<span key={key++}>{match[0]}</span>);
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(<span key={key++}>{text.slice(lastIndex)}</span>);
  }

  return <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--l-charcoal)]/85">{parts}</p>;
}
