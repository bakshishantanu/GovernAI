import { Ban, Hammer, Hourglass, PackageCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AgentRequestStatus } from "@/lib/types";

/**
 * One vocabulary for request status, shared by the queue and the detail page.
 *
 * `label` is what a person reads; the raw status is never printed. `meaning`
 * says what is actually true right now, because "CLAIMED" tells a requester
 * nothing about whether anyone is working on their request.
 */
export const REQUEST_STATUS: Record<
  AgentRequestStatus,
  { label: string; meaning: string; icon: LucideIcon; fill: string; pip: string }
> = {
  PENDING: {
    label: "Waiting",
    meaning: "No one has picked this up yet.",
    icon: Hourglass,
    fill: "var(--l-yellow-pale)",
    pip: "var(--l-yellow-deep)",
  },
  CLAIMED: {
    label: "Being built",
    meaning: "A builder has taken it on.",
    icon: Hammer,
    fill: "var(--l-pink-pale)",
    pip: "var(--l-orange)",
  },
  FULFILLED: {
    label: "Delivered",
    meaning: "The agent was built and handed over.",
    icon: PackageCheck,
    fill: "var(--l-teal-soft)",
    pip: "var(--l-teal)",
  },
  CANCELLED: {
    label: "Cancelled",
    meaning: "This request was withdrawn.",
    icon: Ban,
    fill: "var(--l-cream-deep)",
    pip: "var(--l-charcoal)",
  },
};

export const STATUS_ORDER: AgentRequestStatus[] = [
  "PENDING",
  "CLAIMED",
  "FULFILLED",
  "CANCELLED",
];

/** A short, stable id for display. Full ids are unreadable and never scanned. */
export function shortId(id: string): string {
  return id.slice(0, 8);
}
