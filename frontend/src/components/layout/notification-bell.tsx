"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Bell, Inbox } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useNotifications } from "@/lib/use-notifications";
import { useRoleBase } from "@/lib/use-role-base";
import { timeAgo } from "@/lib/time-ago";

const MAX_SHOWN = 6;

/**
 * The header bell: a live count of things waiting on you, and a dropdown
 * naming each one — not just a badge that sends you hunting for what
 * changed. See lib/use-notifications.ts for what actually feeds it.
 */
export function NotificationBell() {
  const { notifications, pendingCount, markSeen } = useNotifications();
  const base = useRoleBase();
  const count = notifications.length;

  return (
    <Popover>
      <PopoverTrigger
        render={
          <button
            className="relative rounded-full p-2 text-[var(--l-charcoal)]/60 transition-colors hover:bg-[var(--l-cream-deep)] hover:text-[var(--l-ink)]"
            aria-label={pendingCount > 0 ? `${pendingCount} notifications` : "Notifications"}
          />
        }
      >
        <Bell className="h-4 w-4" />
        {pendingCount > 0 && (
          <motion.span
            key={pendingCount}
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--l-orange)] px-1 text-[10px] font-bold text-white"
          >
            {pendingCount > 9 ? "9+" : pendingCount}
          </motion.span>
        )}
      </PopoverTrigger>

      <PopoverContent>
        <div className="flex items-center justify-between border-b-2 border-dashed border-[var(--l-ink)]/12 px-4 py-3">
          <span className="landing-display text-sm text-[var(--l-ink)]">Notifications</span>
          {pendingCount > 0 && (
            <span className="font-mono text-[10.5px] text-[var(--l-charcoal)]/45">
              {pendingCount} pending
            </span>
          )}
        </div>

        {count === 0 ? (
          <div className="px-4 py-8 text-center">
            <Inbox className="mx-auto h-5 w-5 text-[var(--l-charcoal)]/30" />
            <p className="mt-2 text-[12.5px] text-[var(--l-charcoal)]/50">You&apos;re all caught up.</p>
          </div>
        ) : (
          <ul className="max-h-80 overflow-y-auto py-1">
            {notifications.slice(0, MAX_SHOWN).map((n) => (
              <li key={n.id}>
                <Link
                  href={`${base}${n.href}`}
                  onClick={() => markSeen(n.id)}
                  className="flex items-start gap-2 px-4 py-2.5 transition-colors hover:bg-[var(--l-cream-deep)]"
                >
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ background: n.seen ? "transparent" : "var(--l-orange)" }}
                  />
                  <span className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-semibold text-[var(--l-ink)]">
                      {n.title}
                    </p>
                    <p className="mt-0.5 flex items-center justify-between gap-2 text-[11.5px] text-[var(--l-charcoal)]/55">
                      <span className="truncate">{n.subtitle}</span>
                      <span className="shrink-0 font-mono">{timeAgo(n.at)}</span>
                    </p>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        <Link
          href={`${base}/drafts`}
          className="block border-t-2 border-dashed border-[var(--l-ink)]/12 px-4 py-2.5 text-center text-[12px] font-semibold text-[var(--l-orange-deep)] transition-colors hover:bg-[var(--l-cream-deep)]"
        >
          View all drafts
        </Link>
      </PopoverContent>
    </Popover>
  );
}
