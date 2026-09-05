import { Plus, Workflow } from "lucide-react";
import Link from "next/link";
import { PageHeader, ActionPill } from "@/components/board/page-header";
import { BoardPanel, ViewTabs, LiveMarker } from "@/components/board/board-panel";
import { OverviewStats } from "./components/overview-stats";
import { AuditFeed } from "@/components/audit/audit-feed";

/**
 * Dashboard.
 *
 * The three figures and the activity feed are now read from the API —
 * `OverviewStats` names the routes behind each tile. Nothing on this page is
 * invented any more.
 *
 * Still to come: the live marker below says "polling" because the single
 * console EventSource does not exist yet. When it does, both this page's feed
 * and its tiles subscribe to it instead of fetching once on mount.
 */
export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Governance at a glance"
        subtitle="Every agent, checked at every gate and metered the whole way"
        actions={
          <>
            <ActionPill>
              <Workflow className="h-[15px] w-[15px]" strokeWidth={2.2} />
              Automate
            </ActionPill>
            <ActionPill tone="teal" href="/agents">
              <Plus className="h-4 w-4" strokeWidth={2.8} />
              New agent
            </ActionPill>
          </>
        }
      />

      <ViewTabs views={[{ name: "Overview", icon: "overview" }]} active="Overview" />

      <BoardPanel toolbar={<LiveMarker label="Live · not connected" />}>
        <OverviewStats />

        <section className="mx-4 mb-4 overflow-hidden rounded-lg border-2 border-border bg-gv-row">
          <header className="flex h-[38px] items-center gap-2 border-b-2 border-border bg-gv-head px-4">
            <h3 className="text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label">
              Recent governance activity
            </h3>
            <Link
              href="/audit"
              className="ml-auto text-[11px] font-extrabold text-gv-muted underline underline-offset-2 hover:text-foreground"
            >
              Full audit log
            </Link>
          </header>
          <AuditFeed limit={25} emptyLabel="No governance events yet — run an agent to fill this." />
        </section>
      </BoardPanel>
    </>
  );
}
