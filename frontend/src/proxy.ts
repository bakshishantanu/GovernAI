import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

// Next.js 16 renamed the `middleware` file convention to `proxy`; behaviour is
// unchanged. The session helper keeps its old module name, lib/supabase/middleware.
export async function proxy(request: NextRequest) {
  // Two-role model: the agent_builder role (and its /builder/* URL prefix)
  // no longer exists — its capabilities merged into user. Old bookmarked or
  // shared /builder links redirect to the equivalent /user page rather than
  // 404ing, preserving the rest of the path (/builder/agents/123 ->
  // /user/agents/123), not just dropping to the bare dashboard.
  const { pathname } = request.nextUrl;
  if (pathname === "/builder" || pathname.startsWith("/builder/")) {
    const url = request.nextUrl.clone();
    url.pathname = "/user" + pathname.slice("/builder".length);
    return NextResponse.redirect(url);
  }

  return await updateSession(request);
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (images, icons)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
