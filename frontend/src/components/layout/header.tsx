"use client";

import { logout } from "@/app/auth/actions";
import { usePathname } from "next/navigation";
import { LogOut, Search } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

/**
 * The black top bar, per design/governai-pro Main.dc.html.
 *
 * This is the storefront hero's black log strip, reused as console chrome:
 * breadcrumb, a search field, then a live alert chip, the people on the
 * workspace, and the account controls.
 */

const CRUMBS: Record<string, string> = {
  "/": "Dashboard",
  "/agents": "Agents",
  "/skills": "Skills",
  "/policies": "Policies",
  "/audit": "Audit log",
  "/costs": "Costs",
  "/settings": "Settings",
  "/automations": "Automations",
};

function crumbFor(pathname: string) {
  if (CRUMBS[pathname]) return CRUMBS[pathname];
  const base = Object.keys(CRUMBS).find(
    (href) => href !== "/" && pathname.startsWith(href),
  );
  return base ? CRUMBS[base] : "Console";
}

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 flex h-[60px] shrink-0 items-center gap-3.5 bg-gv-bar px-5">
      <div className="flex shrink-0 items-center gap-2 text-[13px] font-bold text-gv-bar-text">
        <span>Acme Corp</span>
        <span aria-hidden>/</span>
        <span className="text-gv-yellow">{crumbFor(pathname)}</span>
      </div>

      <label className="ml-2.5 flex h-9 w-[300px] shrink-0 items-center gap-2 rounded-xl border-2 border-gv-bar-border bg-gv-bar-field px-3.5">
        <Search className="h-[15px] w-[15px] shrink-0 text-gv-subtle" strokeWidth={2.2} />
        <input
          type="search"
          placeholder="Search everything"
          className="min-w-0 flex-1 bg-transparent text-[12.5px] font-semibold text-gv-bar-text placeholder:text-gv-subtle focus:outline-none"
        />
        <kbd className="shrink-0 font-mono text-[10.5px] text-gv-subtle">/</kbd>
      </label>

      <div className="ml-auto flex items-center gap-3">
        {/* TODO: wire to the denied-tool-call event stream. */}
        <div className="hidden h-8 items-center gap-[7px] rounded-xl border-2 border-border bg-gv-pink px-3 lg:flex">
          <span className="h-[7px] w-[7px] rounded-full bg-gv-ink" />
          <span className="text-[12px] font-extrabold text-gv-ink">
            6 denied this hour
          </span>
        </div>

        <div className="hidden md:flex">
          {[
            { initials: "SB", tint: "bg-gv-teal" },
            { initials: "PA", tint: "bg-gv-lilac" },
            { initials: "PL", tint: "bg-gv-pink" },
          ].map((person, i) => (
            <div
              key={person.initials}
              className={`flex h-[30px] w-[30px] items-center justify-center rounded-full border-2 border-gv-paper text-[10.5px] font-extrabold text-gv-ink ${person.tint}`}
              style={{ marginLeft: i === 0 ? 0 : -9 }}
            >
              {person.initials}
            </div>
          ))}
        </div>

        <ThemeToggle />

        <form action={logout}>
          <button
            type="submit"
            title="Log out"
            className="flex h-8 items-center gap-2 rounded-xl border-2 border-border bg-gv-yellow px-3 text-[12.5px] font-extrabold text-gv-ink transition-colors hover:bg-gv-pink"
          >
            <LogOut className="h-[14px] w-[14px]" strokeWidth={2.4} />
            Sign out
          </button>
        </form>
      </div>
    </header>
  );
}
