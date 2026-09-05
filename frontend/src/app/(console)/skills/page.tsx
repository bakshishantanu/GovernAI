import { PageHeader } from "@/components/board/page-header";
import { SkillBoard } from "./components/skill-board";

export default function SkillsPage() {
  return (
    <>
      <PageHeader
        title="Skills"
        subtitle="The registry agents are built from, and the permissions each one grants"
      />
      <SkillBoard />
    </>
  );
}
