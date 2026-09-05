import { PagePlaceholder } from "@/components/layout/page-placeholder";

export default function PoliciesPage() {
  return (
    <PagePlaceholder
      title="Policy rules"
      subtitle="What every agent is allowed to do, and what it is not"
      description="Rule list with on/off toggles. The backend CRUD is complete, but only the sql_blocklist rule type exists so far."
    />
  );
}
