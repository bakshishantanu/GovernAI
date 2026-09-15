"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutTemplate,
  ExternalLink,
  Download,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Smartphone,
  Monitor,
  Check,
  Copy,
  Layers,
  Palette,
  Eye,
  FileCode,
  ShieldCheck,
  ChevronRight,
  ChevronDown,
} from "lucide-react";

export interface FigmaWireframeArtifact {
  wireframe_id?: string;
  screen_name: string;
  layout_type?: "desktop" | "mobile" | "modal" | "dashboard" | string;
  embed_url?: string;
  figma_file_url?: string;
  svg_content?: string;
  palette?: {
    canvas?: string;
    primary?: string;
    accent?: string;
    card_bg?: string;
    border?: string;
    text_muted?: string;
    [key: string]: string | undefined;
  };
  node_tree?: {
    id: string;
    name: string;
    type: string;
    children?: any[];
    [key: string]: any;
  };
  ux_breakdown?: string;
  sections_count?: number;
  components_count?: number;
  source_spec_doc?: string;
}

export function FigmaArtifactViewer({
  artifact,
}: {
  artifact: FigmaWireframeArtifact;
}) {
  const [viewMode, setViewMode] = useState<"canvas" | "embed">("canvas");
  const [zoom, setZoom] = useState(1);
  const [copiedHex, setCopiedHex] = useState<string | null>(null);
  const [iframeLoading, setIframeLoading] = useState(true);
  const [showNodeTree, setShowNodeTree] = useState(true);

  const screenName = artifact.screen_name || "Figma Design Frame";
  const layoutType = (artifact.layout_type || "desktop").toLowerCase();
  const isMobile = layoutType === "mobile";

  // The badge used to hardcode "390×844" for mobile and "1200×800" for
  // everything else, regardless of what was actually generated — neither
  // number matches the real canvas the backend renders for any layout type
  // (backend/app/runtime/figma/adapter.py: mobile 390×780, modal 640×480,
  // desktop/dashboard 1000×640), and modal wireframes were silently
  // mislabeled "Desktop" since this only ever branched on isMobile. Parsing
  // the real `viewBox` out of the SVG the backend actually returned is the
  // one value that can never drift from what's on screen; only fall back to
  // a per-layout guess (matching the backend's own real defaults) for an
  // artifact that hasn't rendered its SVG yet.
  const viewBoxDims = artifact.svg_content?.match(/viewBox="0 0 (\d+) (\d+)"/);
  const [canvasWidth, canvasHeight] = viewBoxDims
    ? [Number(viewBoxDims[1]), Number(viewBoxDims[2])]
    : layoutType === "mobile"
      ? [390, 780]
      : layoutType === "modal"
        ? [640, 480]
        : [1000, 640];
  const layoutLabel = layoutType.charAt(0).toUpperCase() + layoutType.slice(1);

  const palette = {
    canvas: artifact.palette?.canvas || "#FBF7EE",
    primary: artifact.palette?.primary || "#1E1B4B",
    accent: artifact.palette?.accent || "#FF3366",
    card_bg: artifact.palette?.card_bg || "#FFFFFF",
    border: artifact.palette?.border || "#E5E7EB",
  };

  const copyColor = (hex: string) => {
    navigator.clipboard.writeText(hex);
    setCopiedHex(hex);
    setTimeout(() => setCopiedHex(null), 1800);
  };

  const downloadSvg = () => {
    if (!artifact.svg_content) return;
    const blob = new Blob([artifact.svg_content], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${screenName.toLowerCase().replace(/\s+/g, "_")}_wireframe.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const figmaExternalUrl =
    artifact.figma_file_url ||
    (artifact.embed_url
      ? artifact.embed_url.replace("https://www.figma.com/embed?embed_host=share&url=", "")
      : null) ||
    "https://www.figma.com";

  return (
    <div className="space-y-4">
      {/* Studio Header Card */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--l-orange)]/30 bg-[var(--l-orange)]/10 text-[var(--l-orange-deep)] shadow-inner">
            <LayoutTemplate className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="landing-display text-base font-bold text-[var(--l-ink)]">
                {screenName}
              </h3>
              <span className="flex items-center gap-1 rounded-full border border-[var(--l-line)] bg-white/60 px-2 py-0.5 font-mono text-[11px] font-semibold text-[var(--l-charcoal)]/80 shadow-xs dark:bg-black/20">
                {isMobile ? <Smartphone className="h-3 w-3" /> : <Monitor className="h-3 w-3" />}
                {layoutLabel} ({canvasWidth}×{canvasHeight})
              </span>
              <span className="rounded-full bg-[var(--l-teal)]/15 px-2 py-0.5 font-mono text-[10px] font-bold tracking-wide text-[var(--l-teal)] uppercase">
                From Figma
              </span>
            </div>
            <p className="mt-0.5 font-mono text-[11px] text-[var(--l-charcoal)]/60">
              Artifact ID: {artifact.wireframe_id || "wf_figma_live"} • Brand Tokens: GovernAI Design System
            </p>
          </div>
        </div>

        {/* View Mode & Actions Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex rounded-xl border-2 border-[var(--l-line)] bg-white/70 p-0.5 shadow-xs dark:bg-black/20">
            <button
              onClick={() => setViewMode("canvas")}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
                viewMode === "canvas"
                  ? "bg-[var(--l-orange-deep)] text-white shadow-xs"
                  : "text-[var(--l-charcoal)]/70 hover:text-[var(--l-ink)]"
              }`}
            >
              <Eye className="h-3.5 w-3.5" />
              Rendered Frame
            </button>
            <button
              onClick={() => setViewMode("embed")}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
                viewMode === "embed"
                  ? "bg-[var(--l-orange-deep)] text-white shadow-xs"
                  : "text-[var(--l-charcoal)]/70 hover:text-[var(--l-ink)]"
              }`}
            >
              <FileCode className="h-3.5 w-3.5" />
              Live Figma Embed
            </button>
          </div>

          {/* Zoom controls for canvas */}
          {viewMode === "canvas" && (
            <div className="flex items-center rounded-xl border border-[var(--l-line)] bg-white/70 px-1 py-0.5 text-xs font-mono shadow-xs dark:bg-black/20">
              <button
                onClick={() => setZoom((z) => Math.max(0.6, Number((z - 0.15).toFixed(2))))}
                className="p-1 text-[var(--l-charcoal)]/70 hover:text-[var(--l-ink)]"
                title="Zoom Out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <span className="min-w-[42px] px-1 text-center text-[11px] font-semibold text-[var(--l-ink)]">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={() => setZoom((z) => Math.min(1.8, Number((z + 0.15).toFixed(2))))}
                className="p-1 text-[var(--l-charcoal)]/70 hover:text-[var(--l-ink)]"
                title="Zoom In"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setZoom(1)}
                className="ml-0.5 border-l border-[var(--l-line)] p-1 text-[var(--l-charcoal)]/50 hover:text-[var(--l-ink)]"
                title="Reset Zoom"
              >
                <RotateCcw className="h-3 w-3" />
              </button>
            </div>
          )}

          {/* Download SVG asset */}
          {artifact.svg_content && (
            <button
              onClick={downloadSvg}
              className="flex items-center gap-1.5 rounded-xl border border-[var(--l-line)] bg-white/70 px-3 py-1.5 text-xs font-semibold text-[var(--l-charcoal)] shadow-xs transition hover:bg-white hover:text-[var(--l-ink)] dark:bg-black/20 dark:hover:bg-black/40"
              title="Download Rendered SVG"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download</span>
            </button>
          )}

          {/* Open in Figma External Link */}
          {figmaExternalUrl && (
            <a
              href={figmaExternalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-xl border-2 border-[var(--l-navy-deep)] bg-[var(--l-navy-deep)] px-3 py-1.5 text-xs font-bold text-white shadow-xs transition hover:opacity-90"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Open in Figma</span>
            </a>
          )}
        </div>
      </div>

      {/* Main Interactive Stage */}
      <div className="relative overflow-hidden rounded-2xl border-2 border-[var(--l-line)] bg-[#EFECE6] p-6 shadow-inner dark:bg-[#121316]">
        {/* Background Canvas Grid Pattern */}
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage: "radial-gradient(#1E1B4B 1px, transparent 1px)",
            backgroundSize: "20px 20px",
          }}
        />

        {viewMode === "canvas" ? (
          <div className="relative flex min-h-[460px] items-center justify-center overflow-auto p-4">
            <motion.div
              animate={{ scale: zoom }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              style={{ transformOrigin: "center center" }}
              className="relative rounded-2xl shadow-2xl transition-shadow"
            >
              {artifact.svg_content ? (
                <div
                  className="rounded-2xl overflow-hidden border border-black/10 dark:border-white/10"
                  style={{
                    width: isMobile ? 390 : 880,
                    maxWidth: "100%",
                  }}
                  dangerouslySetInnerHTML={{ __html: artifact.svg_content }}
                />
              ) : (
                <div className="flex h-80 w-96 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[var(--l-line)] bg-white/80 p-8 text-center">
                  <LayoutTemplate className="h-10 w-10 text-[var(--l-charcoal)]/30" />
                  <p className="mt-2 text-sm font-semibold text-[var(--l-ink)]">
                    Rendering frame canvas...
                  </p>
                </div>
              )}
            </motion.div>
          </div>
        ) : (
          /* Live Figma Embed Iframe */
          <div className="relative h-[620px] w-full overflow-hidden rounded-xl border border-[var(--l-line)] bg-white shadow-md">
            {artifact.embed_url ? (
              <>
                {iframeLoading && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-[var(--l-cream)]/90 backdrop-blur-xs">
                    <div className="h-7 w-7 animate-spin rounded-full border-3 border-[var(--l-orange-deep)] border-t-transparent" />
                    <p className="mt-3 font-mono text-xs text-[var(--l-charcoal)]/70">
                      Loading interactive Figma embed canvas…
                    </p>
                  </div>
                )}
                <iframe
                  src={artifact.embed_url}
                  title={`Figma Embed: ${screenName}`}
                  className="h-full w-full border-0"
                  allowFullScreen
                  onLoad={() => setIframeLoading(false)}
                />
              </>
            ) : (
              <div className="flex h-full flex-col items-center justify-center p-8 text-center">
                <LayoutTemplate className="h-10 w-10 text-[var(--l-charcoal)]/30" />
                <p className="mt-3 font-semibold text-[var(--l-ink)]">
                  Live Figma Embed is not configured for this preview.
                </p>
                <p className="mt-1 text-xs text-[var(--l-charcoal)]/60">
                  Switch to the "Rendered Frame" tab to view the authentic Figma UI design.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Info Strip: Color Palette Tokens + Figma Node Tree Inspector */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-12">
        {/* Design System Token Swatches */}
        <div className="rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4 shadow-xs md:col-span-5">
          <div className="flex items-center gap-2 mb-3">
            <Palette className="h-4 w-4 text-[var(--l-orange-deep)]" />
            <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-[var(--l-ink)]">
              GovernAI Design Tokens
            </h4>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {[
              { label: "Canvas", hex: palette.canvas, role: "Background" },
              { label: "Primary Navy", hex: palette.primary, role: "Brand & Headers" },
              { label: "Action Accent", hex: palette.accent, role: "CTA Buttons" },
              { label: "Card Surface", hex: palette.card_bg, role: "Containers" },
            ].map((swatch) => (
              <button
                key={swatch.label}
                onClick={() => copyColor(swatch.hex)}
                className="group flex items-center justify-between rounded-xl border border-[var(--l-line)] bg-white/70 p-2 text-left transition hover:border-[var(--l-orange-deep)] dark:bg-black/20"
                title="Click to copy hex color"
              >
                <div className="flex items-center gap-2">
                  <div
                    className="h-5 w-5 rounded-full border border-black/10 shadow-xs"
                    style={{ backgroundColor: swatch.hex }}
                  />
                  <div>
                    <div className="text-[11px] font-semibold text-[var(--l-ink)]">
                      {swatch.label}
                    </div>
                    <div className="font-mono text-[10px] text-[var(--l-charcoal)]/60">
                      {swatch.hex}
                    </div>
                  </div>
                </div>
                <div className="text-[var(--l-charcoal)]/30 group-hover:text-[var(--l-orange-deep)]">
                  {copiedHex === swatch.hex ? (
                    <Check className="h-3.5 w-3.5 text-[var(--l-teal)]" />
                  ) : (
                    <Copy className="h-3 w-3 opacity-60 group-hover:opacity-100" />
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Node Hierarchy & Structural Breakdown */}
        <div className="rounded-2xl border-2 border-[var(--l-line)] bg-[var(--l-cream)] p-4 shadow-xs md:col-span-7">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-[var(--l-orange-deep)]" />
              <h4 className="font-mono text-xs font-bold uppercase tracking-wider text-[var(--l-ink)]">
                Figma Node Architecture
              </h4>
            </div>
            <button
              onClick={() => setShowNodeTree(!showNodeTree)}
              className="flex items-center gap-1 font-mono text-[11px] text-[var(--l-charcoal)]/70 hover:text-[var(--l-ink)]"
            >
              {showNodeTree ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              {showNodeTree ? "Collapse" : "Expand"}
            </button>
          </div>

          <div className="flex flex-wrap gap-2 mb-3">
            <span className="rounded-lg border border-[var(--l-line)] bg-white/60 px-2 py-1 font-mono text-[11px] font-semibold text-[var(--l-charcoal)] dark:bg-black/20">
              Sections: <strong>{artifact.sections_count || (artifact.node_tree?.children?.length ?? 1)}</strong>
            </span>
            <span className="rounded-lg border border-[var(--l-line)] bg-white/60 px-2 py-1 font-mono text-[11px] font-semibold text-[var(--l-charcoal)] dark:bg-black/20">
              Total Components: <strong>{artifact.components_count || 4}</strong>
            </span>
            {artifact.source_spec_doc && (
              <span className="flex items-center gap-1 rounded-lg border border-[var(--l-teal)]/30 bg-[var(--l-teal)]/10 px-2 py-1 font-mono text-[11px] font-semibold text-[var(--l-teal)]">
                <ShieldCheck className="h-3 w-3" />
                Spec Grounding: {artifact.source_spec_doc}
              </span>
            )}
          </div>

          <AnimatePresence>
            {showNodeTree && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="max-h-48 overflow-y-auto rounded-xl border border-[var(--l-line)] bg-white/50 p-2.5 font-mono text-[11px] text-[var(--l-charcoal)] dark:bg-black/30"
              >
                {artifact.node_tree ? (
                  <NodeItem node={artifact.node_tree} depth={0} />
                ) : (
                  <div className="space-y-1">
                    <div className="flex items-center gap-1.5 font-bold text-[var(--l-ink)]">
                      <span className="rounded bg-[var(--l-orange)]/20 px-1 py-0.5 text-[9px] text-[var(--l-orange-deep)]">
                        FRAME
                      </span>
                      {screenName} ({layoutType})
                    </div>
                    <div className="pl-4 text-[var(--l-charcoal)]/70">
                      ├── Section: Order Summary (column layout)
                    </div>
                    <div className="pl-4 text-[var(--l-charcoal)]/70">
                      ├── Section: Express Payment (row layout: Apple Pay, Credit Card)
                    </div>
                    <div className="pl-4 text-[var(--l-charcoal)]/70">
                      ├── Section: Shipping Address (input fields)
                    </div>
                    <div className="pl-4 text-[var(--l-charcoal)]/70">
                      └── Section: Action Footer (Primary CTA: Complete Purchase)
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function NodeItem({ node, depth }: { node: any; depth: number }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  const typeBadgeColors: Record<string, string> = {
    FRAME: "bg-[var(--l-orange)]/20 text-[var(--l-orange-deep)]",
    SECTION: "bg-[var(--l-teal)]/20 text-[var(--l-teal)]",
    COMPONENT: "bg-[var(--l-navy-deep)]/15 text-[var(--l-navy-deep)] dark:text-white dark:bg-white/20",
    BUTTON: "bg-[var(--l-orange-deep)] text-white",
    INPUT: "bg-amber-500/20 text-amber-700 dark:text-amber-300",
    CARD: "bg-blue-500/20 text-blue-700 dark:text-blue-300",
    TEXT: "bg-slate-500/20 text-slate-700 dark:text-slate-300",
  };

  const badgeClass =
    typeBadgeColors[node.type?.toUpperCase()] ||
    "bg-[var(--l-charcoal)]/10 text-[var(--l-charcoal)]";

  return (
    <div className="space-y-1">
      <div
        className="flex items-center gap-1.5 py-0.5 hover:bg-black/5 rounded px-1 transition dark:hover:bg-white/5 cursor-pointer"
        style={{ paddingLeft: `${depth * 14}px` }}
        onClick={() => hasChildren && setOpen(!open)}
      >
        {hasChildren ? (
          open ? (
            <ChevronDown className="h-3 w-3 shrink-0 text-[var(--l-charcoal)]/50" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0 text-[var(--l-charcoal)]/50" />
          )
        ) : (
          <span className="w-3" />
        )}
        <span className={`rounded px-1 py-0.2 text-[9px] font-bold ${badgeClass}`}>
          {node.type || "NODE"}
        </span>
        <span className="font-semibold text-[var(--l-ink)]">{node.name}</span>
        {node.layout && (
          <span className="text-[10px] text-[var(--l-charcoal)]/50">({node.layout})</span>
        )}
      </div>
      {hasChildren && open && (
        <div>
          {node.children.map((child: any, idx: number) => (
            <NodeItem key={child.id || idx} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
