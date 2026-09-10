export type SettingsResponse = {
  user: { id: string; org_id: string; role: string; email: string | null; full_name: string | null };
  organization: {
    id: string;
    name: string;
    agent_count: number;
    policy_count: number;
    automation_count: number;
  };
  budget_cap_usd: number;
  budget_window_hours: number;
  dev_token_enabled: boolean;
};

export function money(n: number) {
  if (n === 0) return "$0.00";
  return n >= 0.01 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}
