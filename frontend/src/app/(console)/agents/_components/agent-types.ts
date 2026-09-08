export type Passport = {
  id: string;
  lifecycle_state: string;
  compliance_status: string;
  permissions: string[];
};

export type Agent = {
  id: string;
  name: string;
  description: string;
  status: string;
  owner_id: string;
  passport: Passport;
  skills: { id: string; name: string }[];
  created_at: string;
};

/**
 * One entry per real lifecycle_state. `stamp` is the word rendered on the
 * rotated passport stamp; `ink`/`paper` are the stamp's own two-colour
 * scheme so it reads as a rubber stamp pressed onto the card, not a badge
 * that happens to be tilted.
 */
export const LIFECYCLE: Record<
  string,
  { stamp: string; ink: string; paper: string; dot?: string }
> = {
  ACTIVE: { stamp: "CLEARED", ink: "var(--l-teal)", paper: "#ffffff", dot: "var(--l-teal)" },
  APPROVED: { stamp: "APPROVED", ink: "var(--l-navy-deep)", paper: "#ffffff" },
  DRAFT: { stamp: "DRAFT", ink: "var(--l-charcoal)", paper: "#ffffff" },
  SUSPENDED: { stamp: "SUSPENDED", ink: "var(--l-orange-deep)", paper: "#ffffff" },
  REVOKED: { stamp: "REVOKED", ink: "#8a1f1f", paper: "#ffffff" },
};

export function lifecycleOf(a: Agent) {
  return LIFECYCLE[a.passport.lifecycle_state] ?? LIFECYCLE.DRAFT;
}

export type Budget = { agent_id: string; spend_usd: number; cap_usd: number; percent_of_cap: number };

export function money(n: number) {
  if (n === 0) return "$0.00";
  return n >= 0.01 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}
