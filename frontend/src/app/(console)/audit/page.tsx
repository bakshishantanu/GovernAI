import { PageHeader } from "@/components/board/page-header";
import { BoardPanel, ViewTabs, LiveMarker } from "@/components/board/board-panel";
import { AuditFeed } from "@/components/audit/audit-feed";

/**
 * The organisation-wide audit log.
 *
 * The same `AuditFeed` renders here unfiltered and on an agent's detail page
 * filtered to that agent — the build order asked for one component, not two.
 */
export default function AuditPage() {
  return (
    <>
      <PageHeader
        title="Audit log"
        subtitle="Every gate an agent passed through, allowed or denied"
      />

      <ViewTabs views={[{ name: "Timeline", icon: "timeline" }]} active="Timeline" />

      <BoardPanel toolbar={<LiveMarker label="Newest first" />}>
        <AuditFeed limit={200} />
      </BoardPanel>
    </>
  );
}
