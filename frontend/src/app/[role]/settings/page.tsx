"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { fetchApi } from "@/lib/api-client";
import { IdentityCard } from "./_components/identity-card";
import { OrgCard } from "./_components/org-card";
import { BudgetCard } from "./_components/budget-card";
import { QuickLinksCard } from "./_components/quick-links-card";
import { DevTokenWarning } from "./_components/dev-token-warning";
import { ChangePasswordCard } from "./_components/change-password-card";
import type { SettingsResponse } from "./_components/settings-types";

/**
 * Read-only, on purpose — this page tells you where every governing number
 * actually comes from rather than letting you edit it here, since none of
 * it is a per-user preference: it's server configuration and org identity.
 */
export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchApi("/auth/settings")
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Could not load settings."));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <h1 className="landing-display text-3xl text-[var(--l-ink)]">Settings</h1>
        <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
          Who you are, what org you're in, and{" "}
          <strong className="text-[var(--l-ink)]">where every governing number comes from</strong>.
        </p>
      </motion.div>

      {error && (
        <div className="rounded-2xl border-2 border-dashed border-[var(--l-orange-deep)]/40 bg-[var(--l-orange-deep)]/5 p-6 text-center text-sm text-[var(--l-charcoal)]/70">
          {error}
        </div>
      )}

      {!error && data === null && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-2xl bg-[var(--l-line)]/40" />
          ))}
        </div>
      )}

      {data && (
        <>
          {data.dev_token_enabled && <DevTokenWarning />}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <IdentityCard
              userId={data.user.id}
              orgId={data.user.org_id}
              role={data.user.role}
              email={data.user.email}
              fullName={data.user.full_name}
            />
            <OrgCard
              name={data.organization.name}
              agentCount={data.organization.agent_count}
              policyCount={data.organization.policy_count}
              automationCount={data.organization.automation_count}
            />
          </div>

          <BudgetCard capUsd={data.budget_cap_usd} windowHours={data.budget_window_hours} />

          <ChangePasswordCard email={data.user.email} />

          <QuickLinksCard role={data.user.role} />
        </>
      )}
    </div>
  );
}
