export type SkillTool = {
  name: string;
  description: string;
  required_permission: string;
};

export type Skill = {
  id: string;
  name: string;
  display_name: string;
  description: string;
  version: string;
  trust_level: string;
  tools: SkillTool[];
  required_permissions: string[];
};

/** One accent per skill id, cycling for any skill this list doesn't name yet — keeps the fan visually distinct without inventing content. */
export const SKILL_ACCENT: Record<string, { fg: string; bg: string; ring: string }> = {
  ticketing: { fg: "var(--l-teal)", bg: "var(--l-teal)", ring: "var(--l-teal)" },
  document_search: { fg: "var(--l-orange-deep)", bg: "var(--l-orange)", ring: "var(--l-orange)" },
  // bg is `var(--l-yellow-deep)`, not the paler `--l-yellow`: it's also the
  // "Read more" button's background under white text, and the pale yellow
  // doesn't have the contrast for that.
  solr_search: { fg: "var(--l-yellow-deep)", bg: "var(--l-yellow-deep)", ring: "var(--l-yellow)" },
  figma_design: { fg: "var(--l-orange-deep)", bg: "var(--l-orange)", ring: "var(--l-orange)" },
  site_audit: { fg: "var(--l-teal)", bg: "var(--l-teal)", ring: "var(--l-teal)" },
};

export function accentFor(id: string) {
  return SKILL_ACCENT[id] ?? { fg: "var(--l-charcoal)", bg: "var(--l-charcoal)", ring: "var(--l-charcoal)" };
}
