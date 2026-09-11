"use client";

import { useParams } from "next/navigation";

/**
 * The current role's URL prefix (`/admin`, `/builder`, `/user`), read off
 * the route itself rather than passed down as a prop — every page under
 * `app/[role]/**` can call this to build a same-role link without needing to
 * know or thread its own prefix. Empty string outside `[role]` (there is
 * nothing to prefix with there).
 */
export function useRoleBase(): string {
  const params = useParams<{ role?: string }>();
  return params?.role ? `/${params.role}` : "";
}
