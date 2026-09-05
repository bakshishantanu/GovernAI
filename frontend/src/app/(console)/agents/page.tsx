import { AgentList } from "./components/agent-list"
import { CreateAgentButton } from "./components/create-agent-button"
import { PageHeader } from "@/components/board/page-header"

export const metadata = {
  title: "Agents - GovernAI",
  description: "Manage and monitor your AI agents",
}

export default function AgentsPage() {
  return (
    <>
      <PageHeader
        title="Agents"
        subtitle="Every agent carries a passport, a permission set and a live budget."
        actions={<CreateAgentButton />}
      />

      <AgentList />
    </>
  )
}
