import { Plus, Workflow } from "lucide-react";
import { PageHeader, ActionPill } from "@/components/board/page-header";
import {
  BoardPanel,
  ViewTabs,
  LiveMarker,
} from "@/components/board/board-panel";

/**
 * Dashboard.
 *
 * WARNING — the figures below are still HARDCODED. The canvas rule is "real
 * data in the cells, never invented", so these must be wired before any demo:
 *   Active agents      -> GET /api/v1/agents/
 *   Denied this week   -> GET /api/v1/audits/   (denied tool calls)
 *   Spend today        -> GET /api/v1/costs/summary
 * Those routes exist but sit on the unmerged p1/complete-api-routes branch.
 * Every tile says "not wired" on screen so nobody mistakes them for real.
 */

const tiles = [
  { label: "Active agents", value: "4", meta: "across 2 environments" },
  { label: "Denied this week", value: "12", meta: "policy gate held" },
  { label: "Spend today", value: "$42.50", meta: "of $54.00 cap" },
];

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
            <ActionPill tone="teal">
              <Plus className="h-4 w-4" strokeWidth={2.8} />
              New agent
            </ActionPill>
          </>
        }
      />

      <ViewTabs
        views={[{ name: "Overview", icon: "overview" }]}
        active="Overview"
      />

      <BoardPanel toolbar={<LiveMarker label="Live · not connected" />}>
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-3">
          {tiles.map((tile) => (
            <div
              key={tile.label}
              className="gv-card rounded-lg border-2 border-border bg-gv-row p-4"
            >
              <div className="text-[10px] font-extrabold uppercase tracking-[0.06em] text-gv-muted">
                {tile.label}
              </div>
              {/* hero numeral — the other place Bungee is allowed */}
              <div className="mt-2 font-display text-[30px] leading-none text-foreground">
                {tile.value}
              </div>
              <div className="mt-1.5 font-mono text-[11px] text-gv-muted">
                {tile.meta}
              </div>
              <div className="mt-2 inline-flex items-center rounded border border-border bg-gv-head px-1.5 py-0.5 font-mono text-[10px] text-gv-muted">
                not wired
              </div>
            </div>
          ))}
        </div>

        <div className="mx-4 mb-4 flex min-h-[280px] items-center justify-center rounded-lg border-2 border-dashed border-gv-rule">
          <p className="text-[13px] font-extrabold tracking-[0.05em] text-gv-muted">
            ACTIVITY FEED — PENDING TASK #11
          </p>
        </div>
      </BoardPanel>
    </>
  );
}
