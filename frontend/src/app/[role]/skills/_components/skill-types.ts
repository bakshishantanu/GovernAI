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
  solr_search: { fg: "var(--l-navy-deep)", bg: "var(--l-navy-deep)", ring: "var(--l-navy-deep)" },
};

export function accentFor(id: string) {
  return SKILL_ACCENT[id] ?? { fg: "var(--l-charcoal)", bg: "var(--l-charcoal)", ring: "var(--l-charcoal)" };
}
