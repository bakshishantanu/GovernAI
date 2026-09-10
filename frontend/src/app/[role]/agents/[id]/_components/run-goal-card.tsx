"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Send, Loader2, Lock } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useRoleBase } from "@/lib/use-role-base";

/**
 * The one form that actually sets an agent to work. Disabled with an
 * explanation rather than hidden when the agent isn't ACTIVE yet, so the
 * lifecycle track above always has somewhere obvious to lead.
 */
export function RunGoalCard({ agentId, active }: { agentId: string; active: boolean }) {
  const router = useRouter();
  const base = useRoleBase();
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const execution = await fetchApi("/executions/", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, goal: goal.trim() }),
      });
      router.push(`${base}/agents/${agentId}/executions/${execution.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the run.");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border-2 border-dashed border-[var(--l-ink)]/25 bg-[var(--l-cream-deep)]/30 p-5">
      <h2 className="landing-display text-base text-[var(--l-ink)]">Run a goal</h2>
      <p className="mt-1 text-[12.5px] text-[var(--l-charcoal)]/60">
        Hand it a real task and watch every tool call as it happens.
      </p>

      {!active ? (
        <div className="mt-4 flex items-center gap-2 rounded-xl bg-[var(--l-ink)]/5 px-3.5 py-3 text-[12.5px] text-[var(--l-charcoal)]/60">
          <Lock className="h-3.5 w-3.5 shrink-0" />
          This passport must be ACTIVE before it can run.
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-4">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Find all open tickets from the last 24 hours and summarize them"
            rows={3}
            required
            className="w-full resize-none rounded-xl border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream)] px-3.5 py-2.5 text-sm text-[var(--l-ink)] placeholder:text-[var(--l-charcoal)]/35 focus:border-[var(--l-orange)] focus:outline-none"
          />
          {error && <p className="mt-2 text-[12.5px] font-medium text-[var(--l-orange-deep)]">{error}</p>}
          <motion.button
            type="submit"
            disabled={!goal.trim() || busy}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="mt-3 flex items-center gap-2 rounded-full bg-[var(--l-orange)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--l-orange-deep)] disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {busy ? "Starting…" : "Run agent"}
          </motion.button>
        </form>
      )}
    </div>
  );
}
