"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useLive } from "@/lib/use-live";
import { timeAgo } from "@/lib/time-ago";
import { PolicyCard } from "./_components/policy-card";
import { CreatePolicyModal } from "./_components/create-policy-modal";
import type { Policy } from "./_components/policy-types";

/**
 * The rulebook: every policy the governance engine actually reads, each
 * rule a numbered statute with its own live switch (FRD-14 — flip it and
 * the next tool call obeys immediately, no redeploy).
 */
export default function PoliciesPage() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const load = useCallback(async () => {
    const data = await fetchApi("/policies/").catch(() => []);
    return (Array.isArray(data) ? data : []) as Policy[];
  }, []);

  const { data: policies, updatedAt, refresh } = useLive(load);

  useEffect(() => {
    fetchApi("/auth/me")
      .then((me) => setIsAdmin(me?.role === "admin"))
      .catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <h1 className="landing-display text-3xl text-[var(--l-ink)]">Policies</h1>
          <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
            Every rule the governance gate reads before it lets a tool call through:{" "}
            <strong className="text-[var(--l-ink)]">flip a switch and it takes effect immediately</strong>.
          </p>
          <p className="mt-1 text-[11.5px] text-[var(--l-charcoal)]/40">
            {updatedAt ? `updated ${timeAgo(new Date(updatedAt).toISOString())}` : "loading…"}
          </p>
        </motion.div>

        {isAdmin && (
          <motion.button
            onClick={() => setModalOpen(true)}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="flex items-center gap-2 rounded-full bg-[var(--l-orange)] px-4 py-2 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--l-orange-deep)]"
          >
            <Plus className="h-4 w-4" />
            New policy
          </motion.button>
        )}
      </div>

      <div className="space-y-4">
        {policies === null ? (
          [0, 1].map((i) => <div key={i} className="h-40 animate-pulse rounded-2xl bg-[var(--l-line)]/40" />)
        ) : policies.length === 0 ? (
          <div className="rounded-2xl border-2 border-dashed border-[var(--l-ink)]/20 py-16 text-center">
            <p className="landing-display text-lg text-[var(--l-ink)]">No policies written yet</p>
            <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
              Without one, the gate falls back to the passport's own permission check alone.
            </p>
          </div>
        ) : (
          policies.map((p, i) => (
            <PolicyCard key={p.id} policy={p} index={i} isAdmin={isAdmin} onChanged={() => refresh()} />
          ))
        )}
      </div>

      <CreatePolicyModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={refresh} />
    </div>
  );
}
