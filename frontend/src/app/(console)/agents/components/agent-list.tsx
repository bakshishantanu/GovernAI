"use client"

import { useState, useEffect, useMemo } from "react"
import { fetchApi } from "@/lib/api-client"
import {
  ViewTabs,
  BoardPanel,
  ToolbarChip,
  LiveMarker,
  type BoardView,
} from "@/components/board/board-panel"
import { Search, ShieldAlert, ChevronRight } from "lucide-react"
import Link from "next/link"

/**
 * The agents board, per design/governai-pro and D-010.
 *
 * A row is 48px with a coloured spine on its left edge, so lifecycle is
 * readable down the column before you read a word of it. The passport column
 * is a filled badge rather than an outline — a passport is a governance fact,
 * not a decoration, and the canvas fills the five states solid.
 *
 * The fetching, the agent-created listener and the search filter are unchanged
 * from the version this replaces; only the presentation is new.
 */

const VIEWS: BoardView[] = [
  { name: "Table", icon: "table" },
  { name: "Compliance", icon: "compliance" },
]

/** lifecycle -> the fill it takes, and the spine colour for its row */
function passportOf(status: string, lifecycle?: string) {
  if (status === "ACTIVE") {
    return { label: "Active", fill: "bg-gv-cleared text-gv-cleared-fg", spine: "bg-gv-cleared" }
  }
  if (status === "SUSPENDED") {
    return { label: "Suspended", fill: "bg-gv-held text-gv-held-fg", spine: "bg-gv-held" }
  }
  if (lifecycle === "APPROVED") {
    return { label: "Approved", fill: "bg-gv-review text-gv-review-fg", spine: "bg-gv-review" }
  }
  if (lifecycle === "DRAFT") {
    return { label: "Draft", fill: "bg-gv-draft text-gv-draft-fg", spine: "bg-gv-rule" }
  }
  return { label: status || "Unknown", fill: "bg-gv-draft text-gv-draft-fg", spine: "bg-gv-rule" }
}

const HEAD_CELL =
  "px-3 py-0 text-left text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label"

export function AgentList() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [view, setView] = useState("Table")

  const fetchAgents = async () => {
    try {
      setLoading(true)
      const data = await fetchApi("/agents/")
      setAgents(Array.isArray(data) ? data : [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAgents()

    const handleCreated = () => {
      fetchAgents()
    }

    window.addEventListener("agent-created", handleCreated)
    return () => window.removeEventListener("agent-created", handleCreated)
  }, [])

  const formatDate = (dateString: string) => {
    const d = new Date(dateString)
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(d)
  }

  const filteredAgents = useMemo(() => {
    if (!searchQuery) return agents
    const lowerQuery = searchQuery.toLowerCase()
    return agents.filter(
      (a) =>
        a.name?.toLowerCase().includes(lowerQuery) ||
        a.description?.toLowerCase().includes(lowerQuery),
    )
  }, [agents, searchQuery])

  const toolbar = (
    <>
      <span className="flex h-8 shrink-0 items-center gap-2 rounded-xl border-2 border-border bg-gv-row px-3">
        <Search className="h-3.5 w-3.5 text-gv-muted" strokeWidth={2.4} />
        <input
          type="text"
          aria-label="Search agents"
          placeholder="Search agents…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-[190px] bg-transparent text-[12.5px] font-bold text-foreground placeholder:font-bold placeholder:text-gv-muted focus:outline-none"
        />
      </span>

      {searchQuery && (
        <ToolbarChip active icon="filter" onRemove={() => setSearchQuery("")}>
          “{searchQuery}”
        </ToolbarChip>
      )}

      <span className="shrink-0 text-[12px] font-extrabold text-gv-muted">
        {filteredAgents.length} of {agents.length}
      </span>

      <LiveMarker label="Not connected" />
    </>
  )

  let body: React.ReactNode

  if (loading) {
    body = (
      <div className="flex flex-col">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="flex h-12 items-center gap-3 border-b-2 border-border px-3"
          >
            <span className="h-3.5 w-40 animate-pulse rounded bg-gv-track" />
            <span className="h-5 w-20 animate-pulse rounded-full bg-gv-track" />
            <span className="ml-auto h-3.5 w-24 animate-pulse rounded bg-gv-track" />
          </div>
        ))}
      </div>
    )
  } else if (error) {
    body = (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-10 text-center">
        <span className="gv-chip mb-1 flex h-10 w-10 items-center justify-center rounded-xl border-2 border-border bg-gv-held">
          <ShieldAlert className="h-5 w-5 text-gv-held-fg" strokeWidth={2.4} />
        </span>
        <span className="text-[13px] font-extrabold tracking-[0.05em] text-gv-ink">
          COULD NOT LOAD AGENTS
        </span>
        <p className="max-w-md text-[13px] font-semibold text-gv-body">{error}</p>
        <button
          type="button"
          onClick={fetchAgents}
          className="gv-chip mt-2 h-9 rounded-xl border-2 border-border bg-card px-4 text-[13px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px"
        >
          Try again
        </button>
      </div>
    )
  } else if (filteredAgents.length === 0) {
    body = (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-10 text-center">
        <span className="text-[13px] font-extrabold tracking-[0.05em] text-gv-muted">
          {agents.length === 0 ? "NO AGENTS YET" : "NOTHING MATCHES"}
        </span>
        <p className="max-w-md text-[13.5px] font-semibold text-gv-body">
          {agents.length === 0
            ? "Create your first agent to give it a passport, a scoped permission set and a live cost budget."
            : `No agent matches “${searchQuery}”.`}
        </p>
      </div>
    )
  } else {
    body = (
      <table className="w-full border-collapse">
        <thead className="sticky top-0 z-10 bg-gv-head">
          <tr className="h-10 border-b-2 border-border">
            {/* the spine column has no label — it is colour, not data */}
            <th className="w-1 p-0" aria-hidden="true" />
            <th scope="col" className={HEAD_CELL}>
              Agent
            </th>
            <th scope="col" className={HEAD_CELL}>
              Passport
            </th>
            <th scope="col" className={`${HEAD_CELL} hidden md:table-cell`}>
              Description
            </th>
            <th scope="col" className={`${HEAD_CELL} text-right`}>
              Created
            </th>
            <th className="w-9 p-0" aria-hidden="true" />
          </tr>
        </thead>

        <tbody>
          {filteredAgents.map((agent) => {
            const passport = passportOf(agent.status, agent.passport?.lifecycle_state)

            return (
              <tr
                key={agent.id}
                className="group relative h-12 border-b-2 border-border last:border-b-0 hover:bg-gv-row-sel"
              >
                <td className={`w-1 p-0 ${passport.spine}`} aria-hidden="true" />

                <td className="max-w-[220px] truncate px-3 text-[13.5px] font-extrabold text-gv-ink">
                  <Link
                    href={`/agents/${agent.id}`}
                    className="after:absolute after:inset-0 after:content-['']"
                  >
                    {agent.name}
                  </Link>
                </td>

                <td className="px-3">
                  <span
                    className={`inline-flex h-[22px] items-center whitespace-nowrap rounded-full border-2 border-border px-2.5 text-[11px] font-extrabold ${passport.fill}`}
                  >
                    {passport.label}
                  </span>
                </td>

                <td className="hidden max-w-[320px] truncate px-3 text-[13px] font-semibold text-gv-body md:table-cell">
                  {agent.description}
                </td>

                <td className="whitespace-nowrap px-3 text-right font-mono text-[12px] font-bold text-gv-muted">
                  {formatDate(agent.created_at)}
                </td>

                <td className="w-9 pr-3 text-right">
                  <ChevronRight
                    className="ml-auto h-4 w-4 text-gv-muted opacity-0 transition-opacity group-hover:opacity-100"
                    strokeWidth={2.6}
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    )
  }

  return (
    <>
      <ViewTabs views={VIEWS} active={view} onSelect={setView} />

      <BoardPanel toolbar={toolbar}>
        {view === "Table" ? (
          body
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-10 text-center">
            <span className="text-[13px] font-extrabold tracking-[0.05em] text-gv-muted">
              NOT BUILT YET
            </span>
            <p className="max-w-md text-[13.5px] font-semibold text-gv-body">
              The compliance view will group agents by passport state and show
              what each one is still missing before it can be activated.
            </p>
          </div>
        )}
      </BoardPanel>
    </>
  )
}
