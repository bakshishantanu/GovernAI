"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useRoleBase } from "@/lib/use-role-base";
import { PassportStamp } from "../../_components/passport-stamp";
import { LifecycleTrack } from "./lifecycle-track";
import { PassportPanel } from "./passport-panel";
import { RunGoalCard } from "./run-goal-card";
import { AgentRunsList } from "./agent-runs-list";
import { AgentAuditFeed } from "./agent-audit-feed";
import type { Agent, Budget } from "../../_components/agent-types";

/**
 * One agent's full passport — the lifecycle it must clear, what it was
 * issued to do, what it has spent, what it has actually run, and the one
 * form that puts it to work. Reuses the same stamp visual as the roster
 * card so this reads as "the passport, opened" rather than a new page.
 */
export function AgentDetail({ id }: { id: string }) {
  const base = useRoleBase();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [budget, setBudget] = useState<Budget | undefined>(undefined);
  const [isAdmin, setIsAdmin] = useState(false);
  const [myId, setMyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchApi(`/agents/${id}`)
      .then((data) => !cancelled && setAgent(data))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Could not load this agent."));
    fetchApi("/costs/budget")
      .then((data) => {
        if (cancelled) return;
        const mine = (data?.agents ?? []).find((a: Budget) => a.agent_id === id);
        setBudget(mine);
      })
      .catch(() => {});
    fetchApi("/auth/me")
      .then((me) => {
        if (cancelled) return;
        setIsAdmin(me?.role === "admin");
        setMyId(me?.id ?? null);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border-2 border-dashed border-[var(--l-orange-deep)]/40 bg-[var(--l-orange-deep)]/5 p-8 text-center">
        <ShieldAlert className="mx-auto h-8 w-8" style={{ color: "var(--l-orange-deep)" }} />
        <p className="mt-3 landing-display text-lg text-[var(--l-ink)]">Could not open this passport</p>
        <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">{error}</p>
        <Link href={`${base}/agents`} className="mt-4 inline-block text-sm font-semibold text-[var(--l-ink)] underline">
          Back to the roster
        </Link>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="h-8 w-40 animate-pulse rounded-full bg-[var(--l-line)]/60" />
        <div className="h-32 animate-pulse rounded-2xl bg-[var(--l-line)]/40" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="h-64 animate-pulse rounded-2xl bg-[var(--l-line)]/40 lg:col-span-2" />
          <div className="h-64 animate-pulse rounded-2xl bg-[var(--l-line)]/40" />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <Link
        href={`${base}/agents`}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--l-charcoal)]/60 transition-colors hover:text-[var(--l-ink)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to the roster
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="relative overflow-hidden rounded-2xl border-2 border-[var(--l-ink)]/90 bg-[var(--l-cream)] p-6 shadow-[0_6px_0_0_rgba(22,19,14,0.14)]"
      >
        <PassportStamp agent={agent} delay={0.1} />
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--l-charcoal)]/45">
          Agent passport · {agent.id.slice(0, 8)}
        </span>
        <h1 className="landing-display mt-1 max-w-[80%] text-3xl text-[var(--l-ink)]">{agent.name}</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-[var(--l-charcoal)]/65">
          {agent.description || "No description on file."}
        </p>
      </motion.div>

      <LifecycleTrack
        agent={agent}
        isAdmin={isAdmin}
        isOwner={myId !== null && myId === agent.owner_id}
        onChanged={setAgent}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <RunGoalCard agentId={agent.id} active={agent.passport.lifecycle_state === "ACTIVE"} />
          <AgentRunsList agentId={agent.id} />
        </div>
        <div className="space-y-4">
          <PassportPanel agent={agent} budget={budget} />
          <AgentAuditFeed agentId={agent.id} />
        </div>
      </div>
    </div>
  );
}
