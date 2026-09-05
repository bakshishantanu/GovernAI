import { PagePlaceholder } from "@/components/layout/page-placeholder";

export default function CostsPage() {
  return (
    <PagePlaceholder
      title="Costs"
      subtitle="What the agents actually spent, metered per call"
      description="Real spend from GET /api/v1/costs/ and /costs/summary. Every figure is a SUM over cost_events."
    />
  );
}
