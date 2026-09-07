import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import "../landing/landing.css";

/**
 * App shell, on Priya's design system (D-038). `RouteTransition` (root
 * layout) already provides the navigation animation — the branded loading
 * screen from PR #30 — so this stays a plain wrapper rather than adding a
 * second, competing transition on `children`.
 */
export default function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="landing flex min-h-screen text-[var(--l-ink)]">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-8">{children}</main>
      </div>
    </div>
  );
}
