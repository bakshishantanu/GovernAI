export type CostEvent = {
  id: string;
  agent_id: string;
  execution_id: string;
  event_type: "LLM_CALL" | "TOOL_CALL";
  model: string | null;
  provider: string | null;
  total_tokens: number | null;
  cost_usd: number;
  timestamp: string;
};

export type CostWindow = "24h" | "7d" | "30d" | "all";

export type CostSummary = {
  total_cost_usd: number;
  by_agent: Record<string, number>;
  by_model: Record<string, number>;
  window: CostWindow;
};

export type AgentBudget = {
  agent_id: string;
  name: string;
  spend_usd: number;
  cap_usd: number;
  percent_of_cap: number;
  suspended: boolean;
};

export type BudgetStatus = {
  cap_usd: number;
  window_hours: number;
  total_spend_usd: number;
  agents: AgentBudget[];
};

export function money(n: number) {
  if (n === 0) return "$0.00";
  return n >= 0.01 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}

/** A torn-receipt-paper edge: alternating triangle teeth as a clip-path polygon. */
export function receiptEdge(teeth = 14): string {
  const points: string[] = [];
  for (let i = 0; i <= teeth; i++) {
    const x = (i / teeth) * 100;
    const y = i % 2 === 0 ? 0 : 100;
    points.push(`${x}% ${y}%`);
  }
  return `polygon(0% 100%, ${points.join(", ")}, 100% 100%)`;
}
