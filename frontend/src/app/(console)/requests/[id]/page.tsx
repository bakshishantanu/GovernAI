import { RequestDetail } from "../_components/request-detail";

export const metadata = {
  title: "Request · GovernAI",
  description: "One agent request, and what can be done about it.",
};

export default async function RequestDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <RequestDetail id={id} />;
}
