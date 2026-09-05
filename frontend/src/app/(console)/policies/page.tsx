import { PageHeader } from "@/components/board/page-header";
import { PolicyBoard } from "./components/policy-board";

export default function PoliciesPage() {
  return (
    <>
      <PageHeader
        title="Policies"
        subtitle="The rules every tool call is measured against, switchable without a restart"
      />
      <PolicyBoard />
    </>
  );
}
