import { ExecutionStream } from "./_components/execution-stream";

export default async function ExecutionPage({
  params,
}: {
  params: Promise<{ id: string; executionId: string }>;
}) {
  const { id, executionId } = await params;
  return <ExecutionStream agentId={id} executionId={executionId} />;
}
