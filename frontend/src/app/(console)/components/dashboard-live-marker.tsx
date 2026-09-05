"use client";

import { LiveMarker } from "@/components/board/board-panel";
import { useConsoleEvents } from "@/components/events/console-events";

/**
 * The dashboard's live marker, driven by the console-wide stream.
 *
 * It used to be the fixed string "Not connected", which was at least honest
 * while nothing was connected. Now it reports the actual connection, so the
 * pulsing dot means what it claims.
 */
export function DashboardLiveMarker() {
  const { connected, reconnecting } = useConsoleEvents();

  return (
    <LiveMarker
      live={connected}
      label={
        connected
          ? "Live · connected"
          : reconnecting
            ? `Reconnecting · attempt ${reconnecting.attempt}`
            : "Not connected"
      }
    />
  );
}
