import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ConsoleEventsProvider } from "@/components/events/console-events";

export default function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // Full-height, non-scrolling frame: the sidebar and the black bar stay put
    // and the board panel scrolls inside itself, as on the canvas. Pages own
    // their own padding via PageHeader / BoardPanel, so there is none here.
    // One event stream for the whole console lives at this level, so every
    // screen below shares a single connection (D-010).
    <ConsoleEventsProvider>
      <div className="flex h-screen overflow-hidden text-foreground">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header />
          <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {children}
          </main>
        </div>
      </div>
    </ConsoleEventsProvider>
  );
}
