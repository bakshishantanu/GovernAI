"use client"

import { useEffect, useState } from "react"
import { fetchApi } from "@/lib/api-client"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Shield, ShieldAlert, ShieldCheck, PlayCircle, Clock } from "lucide-react"
import Link from "next/link"

export function AgentList() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  const getStatusBadge = (status: string, lifecycle: string) => {
    if (status === "ACTIVE") {
      return <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20"><PlayCircle className="w-3 h-3 mr-1" /> Active</Badge>
    }
    
    if (lifecycle === "DRAFT") {
      return <Badge variant="outline" className="text-slate-400 border-slate-700 bg-slate-800/50"><Clock className="w-3 h-3 mr-1" /> Draft</Badge>
    }
    
    if (lifecycle === "APPROVED") {
      return <Badge className="bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border-blue-500/20"><ShieldCheck className="w-3 h-3 mr-1" /> Approved</Badge>
    }

    return <Badge variant="outline">{status}</Badge>
  }

  const formatDate = (dateString: string) => {
    const d = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    }).format(d)
  }

  if (loading) {
    return <div className="text-slate-400 py-12 text-center animate-pulse">Loading agents...</div>
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 text-center">
        <ShieldAlert className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-400 font-medium">Failed to load agents</p>
        <p className="text-slate-400 text-sm mt-1">{error}</p>
        <button onClick={fetchAgents} className="mt-4 text-sm text-blue-400 hover:text-blue-300 underline">Try again</button>
      </div>
    )
  }

  if (agents.length === 0) {
    return (
      <div className="border border-dashed border-slate-800 rounded-xl p-12 text-center flex flex-col items-center justify-center bg-slate-900/30">
        <div className="h-12 w-12 rounded-full bg-slate-800 flex items-center justify-center mb-4">
          <Shield className="h-6 w-6 text-slate-400" />
        </div>
        <h3 className="text-lg font-medium text-slate-200 mb-1">No agents found</h3>
        <p className="text-slate-400 max-w-sm mb-6">
          You haven't registered any AI agents in GovernAI yet. Create your first agent to begin governance tracking.
        </p>
      </div>
    )
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-background">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow className="border-border hover:bg-muted/50">
            <TableHead className="text-muted-foreground">Agent Name</TableHead>
            <TableHead className="text-muted-foreground">Status</TableHead>
            <TableHead className="text-muted-foreground hidden md:table-cell">Description</TableHead>
            <TableHead className="text-muted-foreground text-right">Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {agents.map((agent) => (
            <TableRow key={agent.id} className="border-border hover:bg-muted/50 group transition-colors">
              <TableCell className="font-medium text-foreground">
                <Link href={`/agents/${agent.id}`} className="block hover:text-blue-500 transition-colors">
                  {agent.name}
                </Link>
              </TableCell>
              <TableCell>
                {getStatusBadge(agent.status, agent.passport?.lifecycle_state)}
              </TableCell>
              <TableCell className="text-muted-foreground hidden md:table-cell max-w-[300px] truncate">
                {agent.description}
              </TableCell>
              <TableCell className="text-muted-foreground text-right text-sm">
                {formatDate(agent.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
