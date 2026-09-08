import { RequestsList } from "./components/requests-list";

export const metadata = {
  title: "Agent Requests - GovernAI",
  description: "Queue and lifecycle management for AI agent requests",
};

export default function RequestsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground mb-1">
          Agent Requests
        </h1>
        <p className="text-muted-foreground">
          Track the lifecycle of custom agent requests from initial intake to builder assignment, compliance testing, and handover.
        </p>
      </div>

      <RequestsList />
    </div>
  );
}
