import assert from "node:assert/strict";
import {
  generateCss,
  generateHtml,
  generateReadme,
  getScreenSlug,
} from "../figma-code-generator";
import type { FigmaWireframeArtifact } from "../figma-artifact-viewer";

const sampleArtifact: FigmaWireframeArtifact = {
  wireframe_id: "wf_test_101",
  screen_name: "Checkout Review",
  layout_type: "desktop",
  palette: {
    canvas: "#FBF7EE",
    primary: "#1E1B4B",
    accent: "#FF3366",
    card_bg: "#FFFFFF",
    border: "#E5E7EB",
    text_muted: "#64748B",
  },
  node_tree: {
    id: "root_1",
    name: "Checkout Frame",
    type: "FRAME",
    children: [
      {
        id: "sec_1",
        name: "Order Summary",
        type: "SECTION",
        layout: "column",
        children: [
          {
            id: "card_1",
            name: "Total Amount Card",
            type: "CARD",
            label: "$124.50",
          },
        ],
      },
      {
        id: "sec_2",
        name: "Payment Details",
        type: "SECTION",
        layout: "row",
        children: [
          {
            id: "inp_1",
            name: "Card Number",
            type: "INPUT",
            placeholder: "4242 •••• •••• 4242",
          },
          {
            id: "btn_1",
            name: "Confirm Order",
            type: "BUTTON",
            variant: "primary",
          },
        ],
      },
    ],
  },
  ux_breakdown: "2-step streamlined enterprise checkout flow",
  sections_count: 2,
  components_count: 3,
  source_spec_doc: "spec-checkout-v2.pdf",
};

console.log("🧪 Starting Figma Code Generator Verification Tests...\n");

// Test 1: Screen Slug
console.log("▶ Test 1: Slug Generation");
const slug = getScreenSlug(sampleArtifact);
assert.equal(slug, "checkout-review");
console.log("  ✓ Slug is correctly normalized to 'checkout-review'");

// Test 2: CSS Compilation with GovernAI Brand Tokens
console.log("\n▶ Test 2: CSS Token Generation");
const desktopCss = generateCss(sampleArtifact);
assert.ok(desktopCss.includes("--wf-canvas: #FBF7EE;"), "Must include canvas token");
assert.ok(desktopCss.includes("--wf-primary: #1E1B4B;"), "Must include primary token");
assert.ok(desktopCss.includes("--wf-accent: #FF3366;"), "Must include accent token");
assert.ok(desktopCss.includes("--wf-card-bg: #FFFFFF;"), "Must include card_bg token");
assert.ok(desktopCss.includes("--wf-border: #E5E7EB;"), "Must include border token");
assert.ok(desktopCss.includes("max-width: 1020px;"), "Desktop layout must be 1020px max-width");
assert.ok(desktopCss.includes(".wf-btn-primary"), "Must define primary button style");
assert.ok(desktopCss.includes(".wf-card"), "Must define card container style");
console.log("  ✓ CSS includes all design tokens, desktop container, and interactive classes");

// Test 3: Layout-specific CSS variations
console.log("\n▶ Test 3: Layout Variations (Mobile & Modal)");
const mobileArtifact: FigmaWireframeArtifact = {
  ...sampleArtifact,
  layout_type: "mobile",
};
const mobileCss = generateCss(mobileArtifact);
assert.ok(mobileCss.includes("max-width: 390px;"), "Mobile must set 390px max-width");
assert.ok(mobileCss.includes("border-radius: 36px;"), "Mobile must set phone rounded corners");

const modalArtifact: FigmaWireframeArtifact = {
  ...sampleArtifact,
  layout_type: "modal",
};
const modalCss = generateCss(modalArtifact);
assert.ok(modalCss.includes("max-width: 640px;"), "Modal must set 640px max-width");
console.log("  ✓ Mobile (390px) and Modal (640px) container sizes correctly applied");

// Test 4: Standalone HTML Compilation
console.log("\n▶ Test 4: Standalone HTML (Zero server dependency)");
const standaloneHtml = generateHtml(sampleArtifact, { standalone: true });
assert.ok(standaloneHtml.startsWith("<!DOCTYPE html>"), "Must have standard doctype");
assert.ok(standaloneHtml.includes("<style>"), "Must embed <style> block for standalone view");
assert.ok(standaloneHtml.includes("--wf-primary: #1E1B4B;"), "Embedded style must contain tokens");
assert.ok(standaloneHtml.includes("Checkout Review"), "Must display screen name in header");
assert.ok(standaloneHtml.includes("<button"), "Must generate <button> elements");
assert.ok(standaloneHtml.includes("Confirm Order"), "Button label must be rendered");
assert.ok(standaloneHtml.includes("<input"), "Must generate <input> element");
assert.ok(standaloneHtml.includes("4242 •••• •••• 4242"), "Input placeholder must be rendered");
assert.ok(standaloneHtml.includes("Order Summary"), "Section title must be rendered");
assert.ok(standaloneHtml.includes("$124.50"), "Card content must be rendered");
console.log("  ✓ Standalone HTML produces self-contained valid markup with embedded styles");

// Test 5: Modular HTML Compilation
console.log("\n▶ Test 5: Modular HTML (Linking to styles.css)");
const modularHtml = generateHtml(sampleArtifact, { standalone: false });
assert.ok(!modularHtml.includes("<style>"), "Modular HTML should not embed raw style block");
assert.ok(modularHtml.includes('<link rel="stylesheet" href="styles.css" />'), "Must link to external styles.css");
assert.ok(modularHtml.includes('class="wf-btn wf-btn-primary"'), "Must include primary button class");
console.log("  ✓ Modular HTML links cleanly to external stylesheet");

// Test 6: README Developer Handoff Generation
console.log("\n▶ Test 6: Developer Handoff Documentation");
const readme = generateReadme(sampleArtifact);
assert.ok(readme.includes("# Checkout Review — Developer Handoff Package"), "Must include title");
assert.ok(readme.includes("Order Summary"), "Must list extracted sections");
assert.ok(readme.includes("#FBF7EE"), "Must document canvas color hex");
assert.ok(readme.includes("#FF3366"), "Must document accent color hex");
console.log("  ✓ README contains token inventory and developer handoff specifications");

// Test 7: Fallback handling when node_tree is empty
console.log("\n▶ Test 7: Graceful Fallbacks (Missing Node Tree or Palette)");
const bareArtifact: FigmaWireframeArtifact = {
  screen_name: "Minimal Wireframe",
};
const fallbackHtml = generateHtml(bareArtifact, { standalone: true });
assert.ok(fallbackHtml.includes("Minimal Wireframe"), "Must fallback gracefully to default structure");
assert.ok(fallbackHtml.includes("Action Footer"), "Must render default sections when AST missing");
console.log("  ✓ Fallback mechanism works smoothly when node tree is missing");

console.log("\n🎉 All 7 Figma Code Generator Tests Passed Successfully!\n");
