import { PageHeader } from "@/components/board/page-header";
import { BoardPanel } from "@/components/board/board-panel";

/**
 * Shared placeholder for console pages that are not built yet.
 *
 * Uses the real page structure — title block plus board panel — so an unbuilt
 * page still shows the shape it will have, rather than a loose box.
 */
export function PagePlaceholder({
  title,
  subtitle,
  description,
}: {
  title: string;
  subtitle?: string;
  description: string;
}) {
  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />

      <div className="pt-4" />

      <BoardPanel attached={false}>
        <div className="flex h-full flex-col items-center justify-center gap-2 p-10 text-center">
          <span className="text-[13px] font-extrabold tracking-[0.05em] text-gv-muted">
            NOT BUILT YET
          </span>
          <p className="max-w-md text-[13.5px] font-semibold text-gv-body">
            {description}
          </p>
        </div>
      </BoardPanel>
    </>
  );
}
