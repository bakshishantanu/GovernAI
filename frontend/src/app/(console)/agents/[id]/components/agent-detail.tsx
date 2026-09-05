"use client"

import { useState, useEffect } from "react"
import { fetchApi } from "@/lib/api-client"
import { PageHeader, ActionPill } from "@/components/board/page-header"
import { BoardPanel } from "@/components/board/board-panel"
import { AuditFeed } from "@/components/audit/audit-feed"
import { RunAgentDialog } from "./run-agent-dialog"
import Link from "next/link"
import type { ReactNode } from "react"
import {
  ArrowLeft,
  PlayCircle,
  ShieldCheck,
  ShieldAlert,
  Activity,
  Settings,
} from "lucide-react"

/**
 * One agent, per design/governai-pro.
 *
 * The passport is the headline here, not a side note: it is the thing that
 * decides whether the agent may run at all, so it gets the first panel and the
 * filled status badge rather than an outline.
 *
 * Fetching, the submit/activate actions and the date formatting are unchanged
 * from the version this replaces; only the presentation is new.
 */

function passportOf(status: string, lifecycle?: string) {
  if (status === "ACTIVE") return { label: "Active", fill: "bg-gv-cleared text-gv-cleared-fg" }
  if (status === "SUSPENDED") return { label: "Suspended", fill: "bg-gv-held text-gv-held-fg" }
  if (lifecycle === "APPROVED") return { label: "Approved", fill: "bg-gv-review text-gv-review-fg" }
  if (lifecycle === "DRAFT") return { label: "Draft", fill: "bg-gv-draft text-gv-draft-fg" }
  return { label: status || "Unknown", fill: "bg-gv-draft text-gv-draft-fg" }
}

const LABEL = "text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label"

/** a panel inside the board — the console's second level of elevation */
function Card({
  title,
  icon,
  action,
  children,
}: {
  title: string
  icon: ReactNode
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="gv-card rounded-lg border-2 border-border bg-gv-row">
      <div className="flex h-12 items-center gap-2 border-b-2 border-border px-4">
        {icon}
        <h2 className="font-display text-[19px] leading-none text-gv-ink">{title}</h2>
        {action && <div className="ml-auto">{action}</div>}
      </div>
      <div className="p-4">{children}</div>
    </section>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className={LABEL}>{label}</span>
      <div className="text-[13.5px] font-bold text-gv-ink">{children}</div>
    </div>
  )
}

export function AgentDetail({ id }: { id: string }) {
  const [agent, setAgent] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  // kept separate from `error`: a failed submit/activate must not replace the
  // whole page with the load-failure screen, the way setError would
  const [actionError, setActionError] = useState<string | null>(null)

  const fetchAgent = async () => {
    try {
      setLoading(true)
      const data = await fetchApi(`/agents/${id}`)
      setAgent(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAgent()
  }, [id])

  const handleAction = async (action: "submit" | "activate") => {
    try {
      setActionLoading(true)
      setActionError(null)
      const updatedAgent = await fetchApi(`/agents/${id}/${action}`, {
        method: "PATCH",
      })
      setAgent(updatedAgent)
    } catch (err: any) {
      setActionError(err.message || `Could not ${action} this agent`)
    } finally {
      setActionLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const d = new Date(dateString)
    return new Intl.DateTimeFormat("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d)
  }

  if (loading) {
    return (
      <>
        <PageHeader title="Agent" subtitle="Loading…" />
        <div className="pt-4" />
        <BoardPanel attached={false}>
          <div className="grid gap-4 p-4 lg:grid-cols-3">
            <div className="h-[280px] animate-pulse rounded-lg bg-gv-track lg:col-span-2" />
            <div className="h-[280px] animate-pulse rounded-lg bg-gv-track" />
          </div>
        </BoardPanel>
      </>
    )
  }

  if (error || !agent) {
    return (
      <>
        <PageHeader title="Agent" subtitle="Could not be loaded" />
        <div className="pt-4" />
        <BoardPanel attached={false}>
          <div className="flex h-full flex-col items-center justify-center gap-2 p-10 text-center">
            <span className="gv-chip mb-1 flex h-10 w-10 items-center justify-center rounded-xl border-2 border-border bg-gv-held">
              <ShieldAlert className="h-5 w-5 text-gv-held-fg" strokeWidth={2.4} />
            </span>
            <span className="text-[13px] font-extrabold tracking-[0.05em] text-gv-ink">
              COULD NOT LOAD THIS AGENT
            </span>
            <p className="max-w-md text-[13px] font-semibold text-gv-body">{error}</p>
            <button
              type="button"
              onClick={fetchAgent}
              className="gv-chip mt-2 h-9 rounded-xl border-2 border-border bg-card px-4 text-[13px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px"
            >
              Try again
            </button>
          </div>
        </BoardPanel>
      </>
    )
  }

  const lifecycle = agent.passport?.lifecycle_state
  const passport = passportOf(agent.status, lifecycle)

  return (
    <>
      <PageHeader
        title={agent.name}
        subtitle={agent.description}
        actions={
          <>
            <Link
              href="/agents"
              className="gv-chip inline-flex h-10 items-center gap-2 rounded-xl border-2 border-border bg-card px-[15px] text-[13px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px"
            >
              <ArrowLeft className="h-4 w-4" strokeWidth={2.6} />
              Agents
            </Link>

            {lifecycle === "DRAFT" && (
              <ActionPill tone="teal" onClick={() => !actionLoading && handleAction("submit")}>
                <ShieldCheck className="h-4 w-4" strokeWidth={2.6} />
                {actionLoading ? "Working…" : "Submit for review"}
              </ActionPill>
            )}

            {agent.status === "ACTIVE" && <RunAgentDialog agentId={agent.id} />}

            {lifecycle === "APPROVED" && agent.status !== "ACTIVE" && (
              <ActionPill tone="teal" onClick={() => !actionLoading && handleAction("activate")}>
                <PlayCircle className="h-4 w-4" strokeWidth={2.6} />
                {actionLoading ? "Working…" : "Activate"}
              </ActionPill>
            )}
          </>
        }
      />

      <div className="pt-4" />

      <BoardPanel attached={false}>
        {actionError && (
          <div
            role="status"
            aria-live="polite"
            className="mx-4 mt-4 rounded-xl border-2 border-border bg-gv-held px-3.5 py-2.5 text-[12.5px] font-extrabold text-gv-held-fg"
          >
            {actionError}
          </div>
        )}

        <div className="grid gap-4 p-4 lg:grid-cols-3">
          <div className="flex flex-col gap-4 lg:col-span-2">
            <Card
              title="Compliance passport"
              icon={<ShieldCheck className="h-[18px] w-[18px] text-gv-ink" strokeWidth={2.4} />}
              action={
                <span
                  className={`inline-flex h-[22px] items-center rounded-full border-2 border-border px-2.5 text-[11px] font-extrabold ${passport.fill}`}
                >
                  {passport.label}
                </span>
              }
            >
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Lifecycle state">{lifecycle || "DRAFT"}</Field>
                <Field label="Compliance checked">
                  {agent.passport?.compliance_checked_at
                    ? formatDate(agent.passport.compliance_checked_at)
                    : "Pending initial review"}
                </Field>
                <Field label="Agent ID">
                  <span className="block truncate rounded-lg border-2 border-border bg-gv-track px-2 py-1 font-mono text-[12px]">
                    {agent.id}
                  </span>
                </Field>
                <Field label="Created">{formatDate(agent.created_at)}</Field>
              </div>

              <div className="mt-4 border-t-2 border-border pt-4">
                <span className={`${LABEL} mb-2 block`}>Granted permissions</span>
                {agent.passport?.permissions?.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {agent.passport.permissions.map((perm: string) => (
                      <span
                        key={perm}
                        className="inline-flex h-[22px] items-center rounded-full border-2 border-border bg-gv-lilac px-2.5 font-mono text-[11px] font-bold text-gv-ink"
                      >
                        {perm}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[13px] font-semibold text-gv-body">
                    Read-only sandbox only — no elevated tool privileges.
                  </p>
                )}
              </div>
            </Card>

            <Card
              title="Recent activity"
              icon={<Activity className="h-[18px] w-[18px] text-gv-ink" strokeWidth={2.4} />}
            >
              {/* the same feed as Overview, filtered to this agent */}
              <div className="-mx-4 -mb-4">
                <AuditFeed
                  agentId={agent.id}
                  limit={100}
                  emptyLabel="No governance events for this agent yet."
                />
              </div>
            </Card>
          </div>

          <Card
            title="Configuration"
            icon={<Settings className="h-[18px] w-[18px] text-gv-ink" strokeWidth={2.4} />}
          >
            <div className="flex flex-col gap-4">
              <div>
                <span className={`${LABEL} mb-2 block`}>Assigned skills</span>
                {agent.skills?.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {agent.skills.map((skill: any) => (
                      <span
                        key={skill.id || skill}
                        className="inline-flex h-[22px] items-center rounded-full border-2 border-border bg-gv-teal px-2.5 text-[11px] font-extrabold text-gv-ink"
                      >
                        {skill.name || skill}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[13px] font-semibold text-gv-body">
                    No skills assigned — this agent cannot call any tool.
                  </p>
                )}
              </div>

              <div className="border-t-2 border-border pt-4">
                <span className={`${LABEL} mb-2 block`}>Active policies</span>
                <p className="text-[13px] font-semibold text-gv-body">
                  Per-agent policy display is not wired yet.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </BoardPanel>
    </>
  )
}
