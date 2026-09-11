export type UserRole = "admin" | "agent_builder";

export type AgentRequestStatus = "PENDING" | "CLAIMED" | "FULFILLED" | "CANCELLED";

export interface AgentRequest {
  id: string;
  org_id: string;
  requester_id: string;
  builder_id: string | null;
  agent_id: string | null;
  title: string;
  description: string;
  requested_skills: string[];
  status: AgentRequestStatus;
  created_at: string;
  updated_at: string;
  claimed_at: string | null;
  fulfilled_at: string | null;
}

export interface Skill {
  id: string;
  name: string;
  display_name?: string;
  description: string;
  version?: string;
  trust_level?: string;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  assigned_user_id?: string | null;
  request_id?: string | null;
  status: string;
  created_at: string;
  passport?: {
    lifecycle_state?: string;
    compliance_status?: string;
    compliance_checked_at?: string;
    permissions?: string[];
  };
  skills?: Array<{ id?: string; name?: string } | string>;
}

export type TicketDraftStatus = "PENDING_REVIEW" | "POSTED" | "REJECTED";

// Matches what GET /ticket-drafts/ actually returns (app/api/schemas/ticket_draft.py) —
// agent_name and ticket_url are resolved server-side so this page never has to
// join agents or guess at a Jira base URL client-side.
export interface TicketDraft {
  id: string;
  org_id: string;
  agent_id: string;
  agent_name?: string | null;
  execution_id: string | null;
  ticket_id: string;
  ticket_url?: string | null;
  body: string;
  status: TicketDraftStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

// Matches what GET /executions/{id} actually returns, confirmed against a live
// response — not `prompt`/`created_at`, which this file previously guessed at
// and which the API has never sent. `executions/page.tsx` was formatting
// `exec.created_at`, i.e. formatting undefined, as a direct result.
export interface Execution {
  id: string;
  agent_id: string;
  org_id: string;
  goal: string;
  status: string;
  result?: string | null;
  error?: string | null;
  started_at: string;
  completed_at?: string | null;
  triggered_by_id?: string | null;
  total_cost_usd?: number | null;
  total_tokens?: number | null;
}
