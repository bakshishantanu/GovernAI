import { PagePlaceholder } from "@/components/layout/page-placeholder";

export default function SkillsPage() {
  return (
    <PagePlaceholder
      title="Skill library"
      subtitle="Reusable capabilities an agent can be given"
      description="The skill marketplace. GET /api/v1/skills/ already serves this; skills are immutable after creation (D-018)."
    />
  );
}
