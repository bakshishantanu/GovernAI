import { RequestsQueue } from "./_components/requests-queue";

export const metadata = {
  title: "Requests · GovernAI",
  description: "Agent requests, from asked for through to handed over.",
};

export default function RequestsPage() {
  return <RequestsQueue />;
}
