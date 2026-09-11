import { notFound, redirect } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { AuthProvider } from "@/lib/auth-context";
import { roleForSlug, slugForRole } from "@/lib/role-slug";
import { resolveSignedInRole } from "@/lib/server-role";
import "../landing/landing.css";

/**
 * App shell, on Priya's design system (D-038). `RouteTransition` (root
 * layout) already provides the navigation animation — the branded loading
 * screen from PR #30 — so this stays a plain wrapper rather than adding a
 * second, competing transition on `children`.
 *
 * Each role is a real URL prefix (`/admin`, `/user`) rather than one shared
 * page re-rendering by client state — the change this layout exists to make.
 * (A third prefix, `/builder`, existed briefly for the `agent_builder` role;
 * that role merged into `user`.) The role that actually renders is resolved
 * here, on the server, by `resolveSignedInRole` (lib/server-role.ts): the
 * admin email list, or an 'admin' row in `profiles` as reported by the
 * backend — there is no manual override of any kind anymore (the dev
 * role-switcher and its cookie were removed). An admin lands on `/admin`;
 * everyone else lands on `/user`. If the URL disagrees with
 * that, this redirects to the URL that matches — a user cannot land on
 * `/admin` by typing it, they just bounce to `/user`. Still a display
 * concern first and foremost: every endpoint re-derives the role from the
 * token server-side regardless of which prefix the browser sits on.
 */
export default async function RoleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ role: string }>;
}) {
  const { role: roleSlug } = await params;
  const urlRole = roleForSlug(roleSlug);
  if (!urlRole) notFound();

  // Signed out (or the lookup failed): no strong signal either way, so the
  // role is null and the URL is trusted below.
  const { user, role: resolvedRole } = await resolveSignedInRole();

  if (resolvedRole && resolvedRole !== urlRole) {
    redirect(`/${slugForRole(resolvedRole)}`);
  }

  const initialRole = resolvedRole ?? urlRole;

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
