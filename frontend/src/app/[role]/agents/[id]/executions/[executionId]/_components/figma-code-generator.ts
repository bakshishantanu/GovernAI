import JSZip from "jszip";
import type { FigmaWireframeArtifact } from "./figma-artifact-viewer";

/**
 * Normalizes design system tokens with defaults.
 */
function getPaletteTokens(artifact: FigmaWireframeArtifact) {
  const p = artifact.palette || {};
  return {
    canvas: p.canvas || "#FBF7EE",
    primary: p.primary || "#1E1B4B",
    accent: p.accent || "#FF3366",
    cardBg: p.card_bg || "#FFFFFF",
    border: p.border || "#E5E7EB",
    textMuted: p.text_muted || "#64748B",
  };
}

/**
 * Formats a clean file slug from the screen name.
 */
export function getScreenSlug(artifact: FigmaWireframeArtifact): string {
  return (artifact.screen_name || "wireframe")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

/**
 * Compiles a responsive, token-grounded CSS stylesheet for the wireframe.
 */
export function generateCss(artifact: FigmaWireframeArtifact): string {
  const tokens = getPaletteTokens(artifact);
  const layout = (artifact.layout_type || "desktop").toLowerCase();

  return `/* ==========================================================================
   GovernAI Enterprise Design Studio — Wireframe Stylesheet
   Screen: ${artifact.screen_name || "Figma Design"}
   Layout: ${layout}
   Generated: ${new Date().toISOString()}
   ========================================================================== */

:root {
  /* GovernAI Brand Tokens */
  --wf-canvas: ${tokens.canvas};
  --wf-primary: ${tokens.primary};
  --wf-accent: ${tokens.accent};
  --wf-card-bg: ${tokens.cardBg};
  --wf-border: ${tokens.border};
  --wf-text-muted: ${tokens.textMuted};

  /* Typography */
  --wf-font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --wf-font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;

  /* Shadows & Radius */
  --wf-radius-sm: 6px;
  --wf-radius-md: 10px;
  --wf-radius-lg: 16px;
  --wf-radius-pill: 9999px;
  --wf-shadow-card: 0 4px 6px -1px rgba(30, 27, 75, 0.06), 0 2px 4px -2px rgba(30, 27, 75, 0.04);
  --wf-shadow-device: 0 20px 40px -15px rgba(30, 27, 75, 0.15), 0 0 0 1px rgba(30, 27, 75, 0.06);
}

/* Reset & Canvas Base */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--wf-font-family);
  background-color: var(--wf-canvas);
  color: var(--wf-primary);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  padding: 32px 16px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
}

/* Outer Wireframe Shell */
.wf-container {
  width: 100%;
  max-width: ${layout === "mobile" ? "390px" : layout === "modal" ? "640px" : "1020px"};
  background-color: var(--wf-canvas);
  border: 1px solid var(--wf-border);
  border-radius: ${layout === "mobile" ? "36px" : "16px"};
  box-shadow: var(--wf-shadow-device);
  overflow: hidden;
  position: relative;
  transition: all 0.2s ease;
}

/* Device Status / Top Navigation Bar */
.wf-device-bar {
  background-color: var(--wf-primary);
  color: #ffffff;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.wf-window-dots {
  display: flex;
  align-items: center;
  gap: 6px;
}

.wf-window-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.wf-dot-red { background-color: #EF4444; opacity: 0.85; }
.wf-dot-yellow { background-color: #F59E0B; opacity: 0.85; }
.wf-dot-green { background-color: #10B981; opacity: 0.85; }

.wf-screen-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60%;
}

.wf-badge-figma {
  background-color: var(--wf-accent);
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 3px 10px;
  border-radius: var(--wf-radius-pill);
}

/* Main Content Surface */
.wf-content {
  padding: 24px 20px 32px 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Section Containers */
.wf-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wf-section-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--wf-primary);
  opacity: 0.85;
  display: flex;
  align-items: center;
  gap: 8px;
}

.wf-section-title::after {
  content: "";
  flex: 1;
  height: 1px;
  background-color: var(--wf-border);
  opacity: 0.6;
}

/* Layout Directions */
.wf-layout-row {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.wf-layout-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wf-layout-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

/* Interactive Components: Buttons */
.wf-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 18px;
  min-height: 44px;
  border-radius: var(--wf-radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition: transform 0.15s ease, opacity 0.15s ease, background-color 0.15s ease;
  text-decoration: none;
  width: ${layout === "mobile" ? "100%" : "auto"};
}

.wf-btn:hover {
  transform: translateY(-1px);
}

.wf-btn:active {
  transform: translateY(1px);
}

.wf-btn-primary {
  background-color: var(--wf-accent);
  color: #ffffff;
  border-color: var(--wf-accent);
  box-shadow: 0 2px 4px rgba(255, 51, 102, 0.2);
}

.wf-btn-primary:hover {
  background-color: color-mix(in srgb, var(--wf-accent) 90%, #000000);
}

.wf-btn-outline,
.wf-btn-secondary,
.wf-btn-default {
  background-color: var(--wf-card-bg);
  color: var(--wf-primary);
  border-color: var(--wf-border);
}

.wf-btn-outline:hover,
.wf-btn-secondary:hover {
  background-color: color-mix(in srgb, var(--wf-canvas) 70%, var(--wf-card-bg));
  border-color: color-mix(in srgb, var(--wf-border) 80%, #000000);
}

/* Interactive Components: Inputs & Form Controls */
.wf-input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.wf-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--wf-primary);
}

.wf-input {
  width: 100%;
  padding: 10px 14px;
  font-family: inherit;
  font-size: 13px;
  color: var(--wf-primary);
  background-color: var(--wf-card-bg);
  border: 1px solid var(--wf-border);
  border-radius: var(--wf-radius-md);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.wf-input:focus {
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 3px rgba(255, 51, 102, 0.15);
}

.wf-input::placeholder {
  color: var(--wf-text-muted);
}

/* Surface Cards & Data Blocks */
.wf-card {
  background-color: var(--wf-card-bg);
  border: 1px solid var(--wf-border);
  border-radius: var(--wf-radius-md);
  padding: 14px 16px;
  box-shadow: var(--wf-shadow-card);
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.wf-card-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--wf-accent);
  flex-shrink: 0;
}

.wf-card-content {
  flex: 1;
}

.wf-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--wf-primary);
}

.wf-card-subtitle {
  font-size: 11px;
  color: var(--wf-text-muted);
}

/* Brand Footer Strip */
.wf-footer-strip {
  border-top: 1px solid var(--wf-border);
  background-color: color-mix(in srgb, var(--wf-card-bg) 60%, var(--wf-canvas));
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  font-weight: 500;
  color: var(--wf-text-muted);
}

.wf-footer-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.wf-footer-dot-accent {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--wf-accent);
}

.wf-footer-dot-primary {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--wf-primary);
}
`;
}

/**
 * Compiles semantic HTML5 code from the wireframe artifact's node tree.
 */
export function generateHtml(
  artifact: FigmaWireframeArtifact,
  options: { standalone?: boolean } = { standalone: true },
): string {
  const layout = (artifact.layout_type || "desktop").toLowerCase();
  const screenName = artifact.screen_name || "Figma Wireframe";
  const css = options.standalone ? generateCss(artifact) : "";

  // Extract sections from node_tree
  const sections = parseSectionsFromNodeTree(artifact);

  const sectionsHtml = sections
    .map((sec) => {
      const layoutClass =
        sec.layout === "row"
          ? "wf-layout-row"
          : sec.layout === "grid"
          ? "wf-layout-grid"
          : "wf-layout-column";

      const componentsHtml = sec.components
        .map((c) => renderComponentHtml(c))
        .join("\n        ");

      return `      <!-- Section: ${sec.name} -->
      <section class="wf-section">
        <h3 class="wf-section-title">${sec.name}</h3>
        <div class="${layoutClass}">
        ${componentsHtml}
        </div>
      </section>`;
    })
    .join("\n\n");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="generator" content="GovernAI Enterprise Design Studio" />
  <title>${screenName} — Figma Wireframe</title>
  ${
    options.standalone
      ? `<style>\n${css}\n  </style>`
      : `<link rel="stylesheet" href="styles.css" />`
  }
</head>
<body>
  <div class="wf-container">
    <!-- Device Top Navigation Header -->
    <header class="wf-device-bar">
      <div class="wf-window-dots">
        <span class="wf-window-dot wf-dot-red"></span>
        <span class="wf-window-dot wf-dot-yellow"></span>
        <span class="wf-window-dot wf-dot-green"></span>
      </div>
      <span class="wf-screen-title">${screenName}</span>
      <span class="wf-badge-figma">${layout}</span>
    </header>

    <!-- Main Wireframe Body -->
    <main class="wf-content">
${sectionsHtml}
    </main>

    <!-- Brand Footer Strip -->
    <footer class="wf-footer-strip">
      <span>GovernAI Design System &bull; ${layout.toUpperCase()}</span>
      <div class="wf-footer-dots">
        <span class="wf-footer-dot-primary" title="Navy Primary"></span>
        <span class="wf-footer-dot-accent" title="Coral Action"></span>
      </div>
    </footer>
  </div>
</body>
</html>
`;
}

/**
 * Parses section and component representations from the AST node tree.
 */
interface ParsedSection {
  name: string;
  layout: "row" | "column" | "grid";
  components: ParsedComponent[];
}

interface ParsedComponent {
  name: string;
  type: string;
  variant?: string;
  label?: string;
  placeholder?: string;
}

function parseSectionsFromNodeTree(artifact: FigmaWireframeArtifact): ParsedSection[] {
  const sections: ParsedSection[] = [];
  const root = artifact.node_tree;

  if (root && Array.isArray(root.children)) {
    for (const secNode of root.children) {
      const secName = secNode.name || "Section";
      const isHorizontal =
        secNode.layout === "row" ||
        secNode.layoutMode === "HORIZONTAL";
      const isGrid = secNode.layout === "grid";
      const layout: "row" | "column" | "grid" = isGrid
        ? "grid"
        : isHorizontal
        ? "row"
        : "column";

      const components: ParsedComponent[] = [];
      if (Array.isArray(secNode.children)) {
        for (const compNode of secNode.children) {
          const rawType = (
            compNode.componentType ||
            compNode.type ||
            ""
          ).toLowerCase();

          const resolvedType = rawType.includes("button")
            ? "button"
            : rawType.includes("input") ||
              rawType.includes("field") ||
              rawType.includes("text_input")
            ? "input"
            : rawType.includes("card") || rawType.includes("metric")
            ? "card"
            : rawType === "component"
            ? "button"
            : "card";

          components.push({
            name: compNode.name || "Component",
            type: resolvedType,
            variant: compNode.variant || "default",
            label: compNode.label || compNode.name || "",
            placeholder: compNode.placeholder || compNode.label || compNode.name || "",
          });
        }
      }

      sections.push({
        name: secName,
        layout,
        components:
          components.length > 0
            ? components
            : [{ name: "Default Item", type: "card", label: secName }],
      });
    }
  }

  // Fallback defaults if node_tree children are empty
  if (sections.length === 0) {
    sections.push(
      {
        name: "Main Header",
        layout: "row",
        components: [
          { name: "Brand Title", type: "card", label: artifact.screen_name || "Overview" },
          { name: "Action Button", type: "button", variant: "primary", label: "Get Started" },
        ],
      },
      {
        name: "Form Inputs",
        layout: "column",
        components: [
          { name: "Email Address", type: "input", label: "Email Address", placeholder: "Enter your email..." },
        ],
      },
      {
        name: "Action Footer",
        layout: "row",
        components: [
          { name: "Submit CTA", type: "button", variant: "primary", label: "Save & Continue" },
        ],
      },
    );
  }

  return sections;
}

/**
 * Renders HTML for a specific UI component.
 */
function renderComponentHtml(comp: ParsedComponent): string {
  const label = comp.label || comp.name;
  const compType = (comp.type || "card").toLowerCase();

  if (compType === "button") {
    const variantClass =
      comp.variant === "primary"
        ? "wf-btn-primary"
        : comp.variant === "outline"
        ? "wf-btn-outline"
        : "wf-btn-secondary";

    return `<button type="button" class="wf-btn ${variantClass}">${escapeHtml(label)}</button>`;
  }

  if (compType === "input") {
    const placeholder = comp.placeholder || comp.label || comp.name || "Enter value...";
    return `<div class="wf-input-group">
          <label class="wf-label">${escapeHtml(label)}</label>
          <input type="text" class="wf-input" placeholder="${escapeHtml(placeholder)}" />
        </div>`;
  }

  // Card or default
  return `<div class="wf-card">
        <span class="wf-card-indicator"></span>
        <div class="wf-card-content">
          <div class="wf-card-title">${escapeHtml(label)}</div>
          <div class="wf-card-subtitle">${escapeHtml(comp.name)}</div>
        </div>
      </div>`;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Generates a developer handoff README markdown document.
 */
export function generateReadme(artifact: FigmaWireframeArtifact): string {
  const tokens = getPaletteTokens(artifact);
  const layout = artifact.layout_type || "desktop";

  return `# ${artifact.screen_name || "Figma Wireframe"} — Developer Handoff Package

Generated automatically from **GovernAI Enterprise Design Studio** (\`figma_design\`).

---

## 1. Specifications Overview

| Property | Value |
| :--- | :--- |
| **Screen Name** | \`${artifact.screen_name}\` |
| **Form Factor / Layout** | \`${layout}\` |
| **Artifact ID** | \`${artifact.wireframe_id || "wf_figma_export"}\` |
| **Source Specification** | \`${artifact.source_spec_doc || "N/A"}\` |

---

## 2. Design System Tokens (GovernAI Palette)

All styles in \`styles.css\` are grounded in the following CSS custom properties:

\`\`\`css
:root {
  --wf-canvas: ${tokens.canvas};      /* Background Canvas */
  --wf-primary: ${tokens.primary};     /* Deep Navy Primary Text & Headers */
  --wf-accent: ${tokens.accent};      /* Coral Action & Key Button CTA */
  --wf-card-bg: ${tokens.cardBg};     /* White Card Surface */
  --wf-border: ${tokens.border};      /* Subtle Line & Frame Border */
  --wf-text-muted: ${tokens.textMuted};  /* Secondary / Slate Text */
}
\`\`\`

---

## 3. Screen Layout & Component Inventory

${parseSectionsFromNodeTree(artifact)
  .map((s, idx) => {
    const compList = s.components
      .map(
        (c) =>
          `  - \`${c.type}\`: ${c.label || c.name}${
            c.variant && c.variant !== "default" ? ` (${c.variant})` : ""
          }`,
      )
      .join("\n");
    return `- **Section ${idx + 1}: ${s.name}** (\`${s.layout}\` layout)\n${compList}`;
  })
  .join("\n\n")}

---

## 4. Package Structure

\`\`\`
.
├── index.html        # Semantic HTML5 markup with sections & components
├── styles.css        # Responsive CSS stylesheet with CSS variables
└── README.md         # Developer handoff documentation & tokens
\`\`\`

---

## 5. Quick Start

1. Open \`index.html\` in any web browser (no local web server or build step required).
2. To modify component styling, edit \`styles.css\`.
3. To customize colors across the screen, adjust the \`:root\` variables at the top of \`styles.css\`.
`;
}

/**
 * Browser file download helper.
 */
function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Downloads a self-contained HTML file (HTML + embedded CSS tokens).
 */
export function downloadStandaloneHtml(artifact: FigmaWireframeArtifact) {
  const slug = getScreenSlug(artifact);
  const htmlContent = generateHtml(artifact, { standalone: true });
  const blob = new Blob([htmlContent], { type: "text/html;charset=utf-8" });
  triggerBrowserDownload(blob, `${slug}_standalone.html`);
}

/**
 * Downloads the modular HTML5 file (linking to styles.css).
 */
export function downloadHtmlFile(artifact: FigmaWireframeArtifact) {
  const slug = getScreenSlug(artifact);
  const htmlContent = generateHtml(artifact, { standalone: false });
  const blob = new Blob([htmlContent], { type: "text/html;charset=utf-8" });
  triggerBrowserDownload(blob, `${slug}_index.html`);
}

/**
 * Downloads the modular styles.css stylesheet.
 */
export function downloadCssFile(artifact: FigmaWireframeArtifact) {
  const slug = getScreenSlug(artifact);
  const cssContent = generateCss(artifact);
  const blob = new Blob([cssContent], { type: "text/css;charset=utf-8" });
  triggerBrowserDownload(blob, `${slug}_styles.css`);
}

/**
 * Compiles and downloads the complete ZIP package containing index.html, styles.css, and README.md.
 */
export async function downloadZipBundle(artifact: FigmaWireframeArtifact): Promise<void> {
  const slug = getScreenSlug(artifact);
  const zip = new JSZip();

  const html = generateHtml(artifact, { standalone: false });
  const css = generateCss(artifact);
  const readme = generateReadme(artifact);

  zip.file("index.html", html);
  zip.file("styles.css", css);
  zip.file("README.md", readme);

  const content = await zip.generateAsync({ type: "blob" });
  triggerBrowserDownload(content, `${slug}_wireframe_bundle.zip`);
}
