"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { fetchApi } from "@/lib/api-client";
import { AuditControls, type DecisionFilter, type ActorFilter } from "./_components/audit-controls";
import { AuditStats } from "./_components/audit-stats";
import { AuditTimeline } from "./_components/audit-timeline";
import { isAllowed, type AuditEvent } from "./_components/audit-types";

type Agent = { id: string; name: string };

/**
 * The audit log, drawn as a checkpoint record — every tool call the
 * governance gate ever ruled on, stamped ALLOW or DENY exactly as it
 * happened. No page here decides anything; it only shows what already did.
 */
export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [query, setQuery] = useState("");
  const [decision, setDecision] = useState<DecisionFilter>("All");
  const [actor, setActor] = useState<ActorFilter>("All");

  useEffect(() => {
    let cancelled = false;
    fetchApi("/audits/?limit=200")
      .then((d) => !cancelled && setEvents(d ?? []))
      .catch(() => !cancelled && setEvents([]));
    fetchApi("/agents/")
      .then((d) => !cancelled && setAgents(d ?? []))
      .catch(() => !cancelled && setAgents([]));
    return () => {
      cancelled = true;
    };
  }, []);

  const nameOf = useMemo(() => {
    const map = new Map((agents ?? []).map((a) => [a.id, a.name]));
    return (id: string) => map.get(id) ?? `${id.slice(0, 8)}…`;
  }, [agents]);

  const counts = useMemo(() => {
    const c: Record<DecisionFilter, number> = { All: events?.length ?? 0, Allowed: 0, Denied: 0 };
    for (const e of events ?? []) {
      if (isAllowed(e)) c.Allowed++;
      else c.Denied++;
    }
    return c;
  }, [events]);

  const visible = useMemo(() => {
    let list = events ?? [];
    if (decision === "Allowed") list = list.filter(isAllowed);
    if (decision === "Denied") list = list.filter((e) => !isAllowed(e));
    if (actor !== "All") list = list.filter((e) => e.actor_type.toLowerCase() === actor.toLowerCase());
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (e) =>
          (e.tool ?? "").toLowerCase().includes(q) ||
          e.action.toLowerCase().includes(q) ||
          (e.agent_id ? nameOf(e.agent_id).toLowerCase().includes(q) : false)
      );
    }
    return list;
  }, [events, decision, actor, query, nameOf]);

  const distinctAgents = useMemo(
    () => new Set((events ?? []).map((e) => e.agent_id).filter(Boolean)).size,
    [events]
  );

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <h1 className="landing-display text-3xl text-[var(--l-ink)]">Audit log</h1>
        <p className="mt-1 text-sm text-[var(--l-charcoal)]/60">
          Every governance decision, <strong className="text-[var(--l-ink)]">exactly as it was ruled</strong>{" "}
          — nothing here can be edited or replayed differently.
        </p>
      </motion.div>

      <AuditStats
        total={events?.length ?? null}
        allowed={events ? counts.Allowed : null}
        denied={events ? counts.Denied : null}
        agentsInvolved={events ? distinctAgents : null}
      />

      <AuditControls
        query={query}
        onQuery={setQuery}
        decision={decision}
        onDecision={setDecision}
        actor={actor}
        onActor={setActor}
        counts={counts}
      />

      <AuditTimeline events={visible} agentName={nameOf} loading={events === null} />
    </div>
  );
}
