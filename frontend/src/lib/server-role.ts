import type { User } from "@supabase/supabase-js";
import { API_BASE } from "@/lib/api-client";
import { roleForEmail } from "@/lib/role-slug";
import { createClient } from "@/lib/supabase/server";
import { UserRole } from "@/lib/types";

/**
 * Which console a signed-in account belongs in, for server components.
 *
 * Admin comes from two places, mirroring the backend's get_current_user: the
 * ADMIN_EMAILS list, or an 'admin' row in `profiles` (what
 * scripts/promote_to_admin.py sets). The email list is known here directly;
 * the profiles row is not, so for an unlisted email this asks the backend's
 * GET /auth/me, which already reports the role it resolved. Without that, a
 * promoted admin would get admin from the API but be routed to /user.
 *
 * Any failure falls back to the email answer, so a slow or down backend
 * routes someone to /user at worst, never to /admin. Routing only: every API
 * call re-derives the role server-side regardless of the URL.
 */
export async function resolveSignedInRole(): Promise<{
  user: User | null;
  role: UserRole | null;
}> {
  try {
    const supabase = await createClient();
    const { data } = await supabase.auth.getUser();
    if (!data.user) return { user: null, role: null };

    const emailRole = roleForEmail(data.user.email);
    if (emailRole === "admin") return { user: data.user, role: "admin" };

    return { user: data.user, role: (await roleFromBackend(supabase)) ?? emailRole };
  } catch {
    return { user: null, role: null };
  }
}

async function roleFromBackend(
  supabase: Awaited<ReturnType<typeof createClient>>,
): Promise<UserRole | null> {
  try {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) return null;

    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;

    const body = await res.json();
    const role = body?.data?.role;
    return role === "admin" || role === "agent_builder" ? role : null;
  } catch {
    return null;
  }
}
