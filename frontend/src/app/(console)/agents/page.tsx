import { AgentList } from "./components/agent-list"
import { CreateAgentButton } from "./components/create-agent-button"

export const metadata = {
  title: "Agents - GovernAI",
  description: "Manage and monitor your AI agents",
}

export default function AgentsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-1">Agents</h1>
          <p className="text-muted-foreground">
            Manage your AI agents, view compliance passports, and track governance policies.
          </p>
        </div>
        <CreateAgentButton />
      </div>
      
      <AgentList />
    </div>
  )
}
