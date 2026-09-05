import { PageHeader } from "@/components/board/page-header";
import { CostBoard } from "./components/cost-board";

export default function CostsPage() {
  return (
    <>
      <PageHeader
        title="Costs"
        subtitle="What every agent spent, metered call by call"
      />
      <CostBoard />
    </>
  );
}
