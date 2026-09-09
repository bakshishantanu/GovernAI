import { RequestAgentForm } from "./components/request-agent-form";

export const metadata = {
  title: "Request an Agent - GovernAI",
  description: "Request a custom AI agent tailored to your organizational workflow",
};

export default function RequestAgentPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground mb-1">
          Request an Agent
        </h1>
        <p className="text-muted-foreground">
          Submit specifications and desired skills. An Agent Builder will assemble, test, and hand over your agent once compliance is verified.
        </p>
      </div>

      <RequestAgentForm />
    </div>
  );
}
