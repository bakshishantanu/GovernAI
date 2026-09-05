import { PageHeader } from "@/components/board/page-header";
import { AutomationBoard } from "./components/automation-board";

export default function AutomationsPage() {
  return (
    <>
      <PageHeader
        title="Automations"
        subtitle="Recipe-style rules — when this happens, do that"
      />
      <AutomationBoard />
    </>
  );
}
