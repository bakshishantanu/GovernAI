"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ChevronDown, Loader2, MessageCircleQuestion, Send, Sparkles } from "lucide-react";
import { fetchApi } from "@/lib/api-client";
import { useLive } from "@/lib/use-live";
import { useRunAndStream } from "@/lib/use-run-and-stream";
import { useDocuments } from "@/lib/use-documents";
import { useRoleBase } from "@/lib/use-role-base";
import type { Agent } from "@/lib/types";
import { CreateAgentModal } from "../../agents/_components/create-agent-modal";
import { CitationText } from "./citation-text";

type QA = { id: string; question: string; answer: string | null; error: string | null; pending: boolean };

const LAST_AGENT_KEY = "governai:lastDocumentSearchAgentId";

function readLastAgentId(): string | null {
  try {
    return localStorage.getItem(LAST_AGENT_KEY);
  } catch {
    return null;
  }
}

function writeLastAgentId(id: string) {
  try {
    localStorage.setItem(LAST_AGENT_KEY, id);
  } catch {
    // Best-effort convenience only - nothing depends on this persisting.
  }
}

/**
 * Every ACTIVE agent bound to the `document_search` skill - the spec wants a
 * real picker here, not a silent pick-the-first-one, since an org can have
 * more than one (e.g. scoped to different document sets down the line).
 * Mirrors `sidebar.tsx`'s own `useHasTicketingAgent` check for what counts
 * as "has the skill and is usable".
 */
function useDocumentSearchAgents() {
  const load = useCallback(async () => {
    const data = await fetchApi("/agents/").catch(() => []);
    const agents = (Array.isArray(data) ? data : []) as Agent[];
    return agents.filter(
      (a) =>
        a.passport?.lifecycle_state === "ACTIVE" &&
        (a.skills ?? []).some((s) => (typeof s === "string" ? s : s.id) === "document_search"),
    );
  }, []);
  return useLive(load, 30000);
}

/**
 * Chat over the document library — a thin layer on top of the existing
 * execution machinery, deliberately: there is no dedicated chat endpoint by
 * design (see docs/p2-decision-log.md), since an agent-less run would have
 * no passport and so no permission check, no audit entry, no recorded cost,
 * and be immune to the kill switch. Asking a question here is exactly
 * `run-goal-card.tsx`'s own flow (`POST /executions/`, then stream to
 * completion) with the question as the goal.
 */
export function AskTab() {
  const router = useRouter();
  const base = useRoleBase();
  const { data: agents, updatedAt: agentsCheckedAt, refresh: refreshAgents } = useDocumentSearchAgents();
  const { documents } = useDocuments();
  const { state, start } = useRunAndStream();
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<QA[]>([]);
  const [creatingAgent, setCreatingAgent] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState(readLastAgentId);
  const stillCheckingAgents = agentsCheckedAt === null;
  const agent = agents?.find((a) => a.id === selectedAgentId) ?? agents?.[0] ?? null;

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || !agent || state.status === "connecting" || state.status === "running") return;
    const id = crypto.randomUUID();
    setThread((t) => [...t, { id, question: q, answer: null, error: null, pending: true }]);
    setQuestion("");
    writeLastAgentId(agent.id);

    const finished = await start(agent.id, q);
    setThread((t) =>
      t.map((entry) =>
        entry.id === id
          ? {
              ...entry,
              pending: false,
              answer: finished.result,
              error: finished.status === "failed" ? finished.error ?? "The run did not produce an answer." : null,
            }
          : entry,
      ),
    );
  }

  if (stillCheckingAgents) {
    return <div className="h-40 animate-pulse rounded-2xl bg-[var(--l-line)]/40" />;
  }

  if (!agent) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-[var(--l-line)] px-6 py-14 text-center">
        <MessageCircleQuestion className="mx-auto h-5 w-5 text-[var(--l-charcoal)]/30" />
        <p className="landing-display mt-2 text-base text-[var(--l-ink)]">No Document Search agent yet</p>
        <p className="mx-auto mt-1 max-w-sm text-sm text-[var(--l-charcoal)]/60">
          Asking a question runs a real, governed agent — the same passport, permission checks, and
          cost tracking as everything else here. Build one with the Document Search skill to start.
        </p>
        <button
          type="button"
          onClick={() => setCreatingAgent(true)}
          className="mx-auto mt-4 inline-flex items-center gap-1.5 rounded-full bg-[var(--l-ink)] px-4 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_rgba(22,19,14,0.2)]"
        >
          <Sparkles className="h-3.5 w-3.5" />
          Build a Document Search agent
        </button>
        <CreateAgentModal
          open={creatingAgent}
          onClose={() => setCreatingAgent(false)}
          onCreated={() => {
            setCreatingAgent(false);
            refreshAgents();
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 rounded-2xl border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream-deep)]/40 px-4 py-2.5">
        {agents && agents.length > 1 ? (
          <label className="relative flex min-w-0 flex-1 items-center gap-1.5 text-[12.5px] text-[var(--l-charcoal)]/60">
            Asking as
            <span className="relative inline-flex min-w-0 flex-1">
              <select
                value={agent.id}
                onChange={(e) => {
                  setSelectedAgentId(e.target.value);
                  writeLastAgentId(e.target.value);
                }}
                className="w-full appearance-none truncate rounded-lg border border-[var(--l-ink)]/15 bg-[var(--l-cream)] py-1 pl-2 pr-6 text-[12.5px] font-semibold text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none"
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--l-charcoal)]/40" />
            </span>
          </label>
        ) : (
          <span className="truncate text-[12.5px] text-[var(--l-charcoal)]/60">
            Asking as <strong className="text-[var(--l-ink)]">{agent.name}</strong>
          </span>
        )}
        <button
          type="button"
          onClick={() => router.push(`${base}/agents/${agent.id}`)}
          className="shrink-0 text-[12px] font-semibold text-[var(--l-orange-deep)] hover:underline"
        >
          View passport
        </button>
      </div>

      {thread.length === 0 && (
        <p className="text-sm text-[var(--l-charcoal)]/50">
          Try: &ldquo;How much did the company spend on research and development?&rdquo;
        </p>
      )}

      <div className="space-y-4">
        {thread.map((qa) => (
          <div key={qa.id} className="space-y-2">
            <p className="landing-display text-base text-[var(--l-ink)]">{qa.question}</p>
            {qa.pending ? (
              <div className="flex items-center gap-2 text-[12.5px] text-[var(--l-charcoal)]/50">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {state.status === "connecting" ? "Starting…" : "Reading, searching, and reasoning…"}
              </div>
            ) : qa.error ? (
              <div className="rounded-xl border-2 border-[var(--l-orange-deep)]/40 bg-[var(--l-orange-soft)]/25 px-3.5 py-2.5 text-[13px] text-[var(--l-ink)]">
                {qa.error}
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl border-2 border-[var(--l-ink)]/10 bg-[var(--l-cream)] p-4"
              >
                <CitationText text={qa.answer ?? "No result was recorded."} documents={documents ?? []} />
              </motion.div>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleAsk} className="flex items-center gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your documents…"
          disabled={state.status === "connecting" || state.status === "running"}
          className="flex-1 rounded-full border-2 border-[var(--l-ink)]/15 bg-[var(--l-cream)] px-4 py-2.5 text-sm text-[var(--l-ink)] focus:border-[var(--l-orange)] focus:outline-none disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={!question.trim() || state.status === "connecting" || state.status === "running"}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--l-ink)] text-white disabled:opacity-40"
        >
          {state.status === "connecting" || state.status === "running" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </form>
    </div>
  );
}
