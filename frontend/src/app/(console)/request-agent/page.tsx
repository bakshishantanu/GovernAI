"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { fetchApi } from "@/lib/api-client";
import type { AgentRequest } from "@/lib/types";
import { RequestAgentForm } from "./_components/request-agent-form";
import { MyRequests } from "./_components/my-requests";

/**
 * The User's home. One page, because asking for something and finding out
 * what happened to it are the same errand — splitting them across two routes
 * would mean a User has to remember where their own request went.
 *
 * The backend scopes /agent-requests/ to the caller when the role is `user`,
 * so this never asks for a filter and never receives someone else's work.
 */
export default function RequestAgentPage() {
  const [requests, setRequests] = useState<AgentRequest[] | null>(null);

  const load = useCallback(() => {
    fetchApi("/agent-requests/")
      .then((data) => setRequests(Array.isArray(data) ? data : []))
      .catch(() => setRequests([]));
  }, []);

  useEffect(() => {
    load();
    // The dev role switcher changes who the API thinks we are, so the list
    // has to be re-fetched rather than left showing the previous role's data.
    const onRoleChange = () => load();
    window.addEventListener("govern-ai-role-change", onRoleChange);
    return () => window.removeEventListener("govern-ai-role-change", onRoleChange);
  }, [load]);

  async function cancel(id: string) {
    // Optimistic: the row is gone from the user's point of view the moment
    // they click. A failure re-fetches, which puts it straight back.
    setRequests((prev) =>
      prev ? prev.map((r) => (r.id === id ? { ...r, status: "CANCELLED" } : r)) : prev
    );
    try {
      await fetchApi(`/agent-requests/${id}/cancel`, { method: "POST" });
    } finally {
      load();
    }
  }

  const open = (requests ?? []).filter(
    (r) => r.status === "PENDING" || r.status === "CLAIMED"
  ).length;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="landing-display text-3xl text-[var(--l-ink)]">Ask for an agent</h1>
        <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
          Say what you need done. Someone builds it, the governance checks run,
          and it turns up ready to use — you never have to think about
          permissions or budgets.
        </p>
      </motion.div>

      <RequestAgentForm onSubmitted={load} />

      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="landing-display text-xl text-[var(--l-ink)]">What you have asked for</h2>
          {open > 0 && (
            <span className="text-[12.5px] text-[var(--l-charcoal)]/55">
              {open} still in progress
            </span>
          )}
        </div>
        <MyRequests requests={requests} onCancel={cancel} />
      </section>
    </div>
  );
}
