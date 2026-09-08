import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { AuthProvider } from "@/lib/auth-context";
import { createClient } from "@/lib/supabase/server";
import { cookies } from "next/headers";
import { UserRole } from "@/lib/types";
import "../landing/landing.css";

/**
 * App shell, on Priya's design system (D-038). `RouteTransition` (root
 * layout) already provides the navigation animation — the branded loading
 * screen from PR #30 — so this stays a plain wrapper rather than adding a
 * second, competing transition on `children`.
 *
 * The role is resolved here, on the server, and handed to `AuthProvider` so
 * the first paint already knows which navigation to render — a client-side
 * lookup would flash the wrong sidebar for a frame. It is a display concern
 * only: every endpoint re-derives the role from the token server-side, so
 * nothing here is a security boundary.
 */
export default async function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let initialRole: UserRole = "admin";
  let user = null;

  try {
    const cookieStore = await cookies();
    const cookieRole = cookieStore.get("govern_ai_role")?.value;
    if (cookieRole && ["admin", "agent_builder", "user"].includes(cookieRole)) {
      initialRole = cookieRole as UserRole;
    } else {
      const supabase = await createClient();
      const { data } = await supabase.auth.getUser();
      if (data.user) {
        user = data.user;
        const rawRole = (user.app_metadata?.role || user.user_metadata?.role || "user") as string;
        if (rawRole === "admin" || rawRole === "agent_builder" || rawRole === "user") {
          initialRole = rawRole;
        } else {
          initialRole = "user";
        }
      }
    }
  } catch {
    // Keep defaults
  }

  return (
    <AuthProvider initialRole={initialRole} initialUser={user}>
      <div className="landing relative flex min-h-screen overflow-hidden text-[var(--l-ink)]">
        {/* Ambient colour wash — the console has been cream-only since D-038;
            this borrows the landing/login pages' own layered-blob technique
            (see landing.css's .landing-blob) at low opacity so the whole
            shell reads as the same warm, colourful world instead of a flat
            neutral admin panel. Fixed behind the sidebar/header/main stack
            (all opaque), so it only ever shows through page gutters and gaps
            between cards — never behind actual content. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 z-0">
          <div className="landing-blob landing-blob-animate absolute -top-24 right-[18%] h-[520px] w-[520px] bg-[var(--l-yellow)] opacity-[0.22]" />
          <div className="landing-blob landing-blob-animate absolute top-[45%] -right-40 h-[460px] w-[460px] bg-[var(--l-pink-lilac)] opacity-[0.20]" />
          <div className="landing-blob absolute -bottom-40 left-[30%] h-[440px] w-[440px] bg-[var(--l-teal)] opacity-[0.16]" />
          <div className="landing-noise absolute inset-0" />
        </div>

        <Sidebar />
        {/* min-w-0 overrides the flex default of min-width:auto — without it
            this column cannot shrink below its content's intrinsic width, so
            any wide child (e.g. the Skills fanned-card row) pushes the whole
            page wider instead of scrolling internally. Confirmed live: the
            skills track's own scrollWidth/clientWidth stayed identical at
            every viewport width until this was added. */}
        <div className="relative z-10 flex min-w-0 flex-1 flex-col">
          <Header />
          <main className="min-w-0 flex-1 overflow-auto p-8">{children}</main>
        </div>
      </div>
    </AuthProvider>
  );
}
