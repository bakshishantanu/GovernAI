import { PageHeader } from "@/components/board/page-header";
import { RunList } from "./components/run-list";

export default function RunsPage() {
  return (
    <>
      <PageHeader
        title="Runs"
        subtitle="Every execution, with the decisions and spend it produced"
      />
      <RunList />
    </>
  );
}
