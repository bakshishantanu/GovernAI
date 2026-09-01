import { AgentDetail } from "./components/agent-detail"

export default function AgentPage({ params }: { params: { id: string } }) {
  return <AgentDetail id={params.id} />
}
