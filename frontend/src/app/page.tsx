import { redirect } from "next/navigation";
import { slugForRole } from "@/lib/role-slug";
import { resolveSignedInRole } from "@/lib/server-role";

/**
 * The bare root now only decides which role's real page to send someone to
 * — `/admin` or `/user` — the same resolution `[role]/layout.tsx` uses
 * (`resolveSignedInRole`: the admin email list or an admin `profiles` row),
 * no manual override. This used to be the console's own dashboard route (a
 * route group added no URL segment); now that each role is a real prefix,
 * something has to own "/".
 */
export default async function RootPage() {
  const { role } = await resolveSignedInRole();

  redirect(`/${slugForRole(role ?? "admin")}`);
}
