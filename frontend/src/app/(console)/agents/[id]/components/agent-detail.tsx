"use client"

import { useState, useEffect } from "react"
import { fetchApi } from "@/lib/api-client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { 
  ArrowLeft, 
  PlayCircle, 
  Clock, 
  ShieldCheck, 
  ShieldAlert, 
  Activity, 
  Settings,
  Bot
} from "lucide-react"

export function AgentDetail({ id }: { id: string }) {
  const [agent, setAgent] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

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

  const handleAction = async (action: 'submit' | 'activate') => {
    try {
      setActionLoading(true)
      const updatedAgent = await fetchApi(`/agents/${id}/${action}`, {
        method: "PATCH"
      })
      setAgent(updatedAgent)
    } catch (err: any) {
      alert(`Error: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const getStatusBadge = (status: string, lifecycle: string) => {
    if (status === "ACTIVE") {
      return (
        <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 relative pl-4 transition-colors text-sm py-1">
          <span className="absolute left-1.5 top-1/2 -translate-y-1/2 flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          Active
        </Badge>
      )
    }
    
    if (lifecycle === "DRAFT") {
      return <Badge variant="outline" className="text-muted-foreground border-border bg-muted/50 text-sm py-1"><Clock className="w-3 h-3 mr-1.5" /> Draft</Badge>
    }
    
    if (lifecycle === "APPROVED") {
      return <Badge className="bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border-blue-500/20 text-sm py-1"><ShieldCheck className="w-3 h-3 mr-1.5" /> Approved</Badge>
    }

    return <Badge variant="outline" className="text-sm py-1">{status}</Badge>
  }

  const formatDate = (dateString: string) => {
    const d = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', { 
      month: 'long', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d)
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <div className="h-8 w-8 bg-muted animate-pulse rounded-md" />
          <div className="h-8 w-48 bg-muted animate-pulse rounded-md" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 h-[300px] bg-muted animate-pulse rounded-xl" />
          <div className="h-[300px] bg-muted animate-pulse rounded-xl" />
        </div>
      </div>
    )
  }

  if (error || !agent) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 text-center">
        <ShieldAlert className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-500 font-medium">Failed to load agent details</p>
        <p className="text-muted-foreground text-sm mt-1">{error}</p>
        <Button variant="outline" onClick={fetchAgent} className="mt-4">Try again</Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <Link href="/agents" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors mb-4">
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Agents
          </Link>
          <div className="flex items-center gap-4">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">{agent.name}</h1>
            {getStatusBadge(agent.status, agent.passport?.lifecycle_state)}
          </div>
          <p className="text-muted-foreground mt-2 max-w-2xl">{agent.description}</p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          {agent.passport?.lifecycle_state === 'DRAFT' && (
            <Button 
              onClick={() => handleAction('submit')} 
              disabled={actionLoading}
            >
              <ShieldCheck className="w-4 h-4 mr-2" />
              Submit for Review
            </Button>
          )}
          {agent.passport?.lifecycle_state === 'APPROVED' && agent.status !== 'ACTIVE' && (
            <Button 
              onClick={() => handleAction('activate')}
              disabled={actionLoading}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              <PlayCircle className="w-4 h-4 mr-2" />
              Activate Agent
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
        
        {/* Compliance Passport Card */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-background border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-500" />
                <h2 className="text-lg font-semibold">Compliance Passport</h2>
              </div>
              {agent.passport?.compliance_status && (
                <Badge className={
                  agent.passport.compliance_status === 'PASSED' 
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                    : agent.passport.compliance_status === 'FAILED'
                    ? "bg-red-500/10 text-red-500 border-red-500/20"
                    : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                }>
                  Compliance: {agent.passport.compliance_status}
                </Badge>
              )}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">Lifecycle State</span>
                <p className="text-base font-medium text-foreground">{agent.passport?.lifecycle_state || 'DRAFT'}</p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">Compliance Checked</span>
                <p className="text-sm text-foreground">
                  {agent.passport?.compliance_checked_at ? formatDate(agent.passport.compliance_checked_at) : "Pending initial review"}
                </p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">Agent ID</span>
                <p className="text-sm text-foreground font-mono bg-muted/50 p-2 rounded-md truncate">
                  {agent.id}
                </p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">Created At</span>
                <p className="text-base text-foreground">{formatDate(agent.created_at)}</p>
              </div>
            </div>

            {/* Passport Permissions */}
            <div className="mt-6 pt-6 border-t border-border">
              <span className="text-sm font-medium text-muted-foreground block mb-2">Granted Permissions</span>
              {agent.passport?.permissions && agent.passport.permissions.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {agent.passport.permissions.map((perm: string) => (
                    <Badge key={perm} variant="secondary" className="font-mono text-xs">
                      {perm}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground bg-muted/30 p-2.5 rounded-lg border border-border/50">
                  Standard read-only sandbox permissions (no elevated tool privileges).
                </p>
              )}
            </div>
          </div>

          {/* Audit Logs Placeholder */}
          <div className="bg-background border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-muted-foreground" />
                <h2 className="text-lg font-semibold">Recent Activity</h2>
              </div>
              <Button variant="outline" size="sm" disabled>View All Logs</Button>
            </div>
            <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed border-border rounded-lg bg-muted/10">
              <Activity className="w-8 h-8 text-muted-foreground mb-3 opacity-50" />
              <p className="text-sm text-muted-foreground font-medium">No activity recorded yet.</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-xs">Audit logs will appear here once the agent begins processing tool calls.</p>
            </div>
          </div>
        </div>

        {/* Configuration Sidebar */}
        <div className="space-y-6">
          <div className="bg-background border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-6">
              <Settings className="w-5 h-5 text-muted-foreground" />
              <h2 className="text-lg font-semibold">Configuration</h2>
            </div>
            
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-3">Assigned Skills</h3>
                {agent.skills && agent.skills.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {agent.skills.map((skill: any) => (
                      <Badge key={skill.id || skill} variant="secondary">
                        {skill.name || skill}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded-lg border border-border/50">
                    No skills assigned.
                  </p>
                )}
              </div>

              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-3">Active Policies</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 p-3 bg-muted/30 rounded-lg border border-border/50 text-sm text-muted-foreground">
                    <ShieldAlert className="w-4 h-4 text-warning" />
                    Global PII Redaction
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
