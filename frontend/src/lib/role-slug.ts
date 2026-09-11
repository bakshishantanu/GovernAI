import { UserRole } from "./types";

/**
 * The two role sections are real URL prefixes (`/admin`, `/user`), not one
 * shared page re-rendering by client state. The URL slug stays `user` even
 * though the underlying role string is `agent_builder` (D-056/D-057) — the
 * slug is routing, not identity, and changing it would break every existing
 * `/user/*` link and bookmark for a naming decision that's internal to the
 * role model. `middleware.ts` redirects any lingering `/builder/*` link to
 * `/user/*` before it ever reaches this mapping.
 */
export const ROLE_SLUGS: Record<UserRole, string> = {
  admin: "admin",
  agent_builder: "user",
};

const SLUG_TO_ROLE: Record<string, UserRole> = {
  admin: "admin",
  user: "agent_builder",
};

export function slugForRole(role: UserRole): string {
  return ROLE_SLUGS[role];
}

/** Returns null for anything that isn't one of the two real slugs. */
export function roleForSlug(slug: string): UserRole | null {
  return SLUG_TO_ROLE[slug] ?? null;
}

/**
 * Which role an email gets — mirrors the backend's `role_rules.py` exactly,
 * so the two agree on where to route someone. This is a *routing*
 * convenience only, never the security boundary: every API call is
 * re-scoped server-side from the real signed-in token regardless of which
 * URL prefix the browser happens to be sitting on.
 */
const ADMIN_EMAILS = (process.env.NEXT_PUBLIC_ADMIN_EMAILS || "admin@governai.com")
  .split(",")
  .map((e) => e.trim().toLowerCase())
  .filter(Boolean);

export function roleForEmail(email: string | null | undefined): UserRole {
  if (!email) return "agent_builder";
  const normalized = email.trim().toLowerCase();
  if (ADMIN_EMAILS.includes(normalized)) return "admin";
  return "agent_builder";
}
