"use client";

import { useRef, useState } from "react";
import { Loader2, Upload } from "lucide-react";
import { ApiError } from "@/lib/api-client";

const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

function isImageFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return IMAGE_EXTENSIONS.some((ext) => name.endsWith(ext));
}

/**
 * PDF, Word, PowerPoint and images are all accepted (scans/photos go through
 * OCR). `title` is offered because it is what every citation displays —
 * without it, `_10-K-2025-As-Filed.pdf` becomes the title "10 K 2025 As
 * Filed" instead of something a reader would recognise.
 *
 * Whether a *.pdf* is a scan is only known once the server extracts it, so
 * the OCR timing note can't be conditioned on that client-side - shown
 * generally instead. An image is always OCR'd (there's no other way to read
 * it), so that case gets a stronger, certain warning.
 */
export function UploadDropzone({
  onUpload,
}: {
  onUpload: (file: File, title: string) => Promise<unknown>;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError("");
    try {
      await onUpload(file, title);
      setFile(null);
      setTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      // A refused upload (unsupported type, empty file, over the 25MB limit,
      // document search not configured) comes back as a 400 with `detail` as
      // a plain sentence — shown directly, per the spec.
      setError(err instanceof ApiError ? err.message : "Could not upload this file.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border-2 border-dashed border-[var(--l-ink)]/20 bg-[var(--l-cream-deep)]/30 p-5"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[200px] flex-1">
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
            File
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png,.webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1.5 w-full text-sm text-[var(--l-charcoal)] file:mr-3 file:rounded-full file:border-0 file:bg-[var(--l-ink)] file:px-3.5 file:py-1.5 file:text-[12.5px] file:font-semibold file:text-white"
          />
        </div>
        <div className="min-w-[200px] flex-1">
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-[var(--l-charcoal)]/50">
            Title (optional)
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Apple FY2025 10-K"
            className="mt-1.5 w-full rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream)] px-3.5 py-2 text-sm text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={!file || busy}
          className="inline-flex items-center gap-1.5 rounded-full bg-[var(--l-ink)] px-4 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_rgba(22,19,14,0.2)] disabled:opacity-40"
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
          Upload
        </button>
      </div>

      <p className="mt-2.5 text-[12px] text-[var(--l-charcoal)]/50">
        PDF, Word, PowerPoint, and photos of documents are all supported. Most files index in a few
        seconds; a long or scanned document can take a couple of minutes — scanned pages are read one
        at a time, at roughly 30 seconds each.
      </p>
      {file && isImageFile(file) && (
        <p className="mt-1 text-[12px] font-medium text-[var(--l-orange-deep)]">
          This is a photo — it will be read page by page via OCR, which can take about 30 seconds.
        </p>
      )}

      {error && <p className="mt-2 text-[12.5px] font-medium text-[var(--l-orange-deep)]">{error}</p>}
    </form>
  );
}
