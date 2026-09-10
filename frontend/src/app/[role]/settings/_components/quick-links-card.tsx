"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Bot,
  ClipboardList,
  DollarSign,
  FileText,
  Puzzle,
  ShieldCheck,
} from "lucide-react";
import { useRoleBase } from "@/lib/use-role-base";
import { ThemeToggle } from "@/components/theme-toggle";

/**
 * "More options" for the settings page — real, working shortcuts into the
 * rest of the console (role-appropriate), plus the one genuine per-viewer
 * preference this app actually has (theme). Everything else on this page is
 * read-only server/org config on purpose (see the page's own docstring);
 * this card is deliberately the one place that's just navigation + a real
 * toggle, not more read-only numbers.
 */
export function QuickLinksCard({ role }: { role: string }) {
  const base = useRoleBase();
  const isAdmin = role === "admin";

  const links = isAdmin
    ? [
        { name: "Policies", href: `${base}/policies`, icon: ShieldCheck },
        { name: "Audit Log", href: `${base}/audit`, icon: FileText },
        { name: "All Agents", href: `${base}/agents`, icon: Bot },
        { name: "Skills", href: `${base}/skills`, icon: Puzzle },
        { name: "Costs", href: `${base}/costs`, icon: DollarSign },
      ]
    : [
        { name: "My Agents", href: `${base}/agents`, icon: Bot },
        { name: "Skills", href: `${base}/skills`, icon: Puzzle },
        { name: "My Activity", href: `${base}/audit`, icon: ClipboardList },
        { name: "Costs", href: `${base}/costs`, icon: DollarSign },
      ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-5 shadow-[0_5px_0_0_rgba(22,19,14,0.14)]"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-[var(--l-charcoal)]/45">
          More options
        </span>
        <div className="flex items-center gap-2 text-[12px] text-[var(--l-charcoal)]/55">
          Appearance
          <ThemeToggle />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {links.map((link) => (
          <Link
            key={link.name}
            href={link.href}
            className="group flex items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm text-[var(--l-ink)] transition-colors hover:bg-[var(--l-cream-deep)]/60"
          >
            <span className="flex items-center gap-2">
              <link.icon className="h-4 w-4 text-[var(--l-charcoal)]/50" />
              {link.name}
            </span>
            <ArrowRight className="h-3.5 w-3.5 text-[var(--l-charcoal)]/30 transition-colors group-hover:text-[var(--l-orange-deep)]" />
          </Link>
        ))}
      </div>
    </motion.div>
  );
}
