import { PageHeader } from "@/components/board/page-header";
import { SettingsBoard } from "./components/settings-board";

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="What is configured for this organisation, and what enforces it"
      />
      <SettingsBoard />
    </>
  );
}
