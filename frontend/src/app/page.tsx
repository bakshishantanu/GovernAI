import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { UserRole } from "@/lib/types";
import { roleForEmail, slugForRole } from "@/lib/role-slug";

/**
 * The bare root now only decides which role's real page to send someone to
 * — `/admin` or `/user` — the same resolution `[role]/layout.tsx` uses:
 * purely the signed-in account's own email, no manual override. This used
 * to be the console's own dashboard route (a route group added no URL
 * segment); now that each role is a real prefix, something has to own "/".
 */
export default async function RootPage() {
  let role: UserRole = "admin";

  try {
    const supabase = await createClient();
    const { data } = await supabase.auth.getUser();
    if (data.user) {
      role = roleForEmail(data.user.email);
    }
  } catch {
    // Keep the default.
  }

  redirect(`/${slugForRole(role)}`);
}
