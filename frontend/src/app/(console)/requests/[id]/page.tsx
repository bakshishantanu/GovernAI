import { RequestDetail } from "./components/request-detail";

export const metadata = {
  title: "Request Details - GovernAI",
  description: "View and manage lifecycle of an AI agent request",
};

export default async function RequestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <RequestDetail id={id} />;
}
