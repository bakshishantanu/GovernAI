"use client";

import { useState, useEffect, useMemo } from "react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  ShieldAlert, 
  ShieldCheck, 
  Clock, 
  Search, 
  ChevronRight,
  Bot,
  Sparkles,
  ClipboardList
} from "lucide-react";
import Link from "next/link";

export function AgentList() {
  const { role, isBuilder, isUser } = useAuth();
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi("/agents/");
      setAgents(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || "Failed to load agents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();

    const handleCreated = () => {
      fetchAgents();
    };

    const handleRoleChange = () => {
      fetchAgents();
    };

    window.addEventListener("agent-created", handleCreated);
    window.addEventListener("govern-ai-role-change", handleRoleChange);
    return () => {
      window.removeEventListener("agent-created", handleCreated);
      window.removeEventListener("govern-ai-role-change", handleRoleChange);
    };
  }, [role]);

  const getStatusBadge = (status: string, lifecycle: string) => {
    if (status === "ACTIVE") {
      return (
        <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 relative pl-4 transition-colors">
          <span className="absolute left-1.5 top-1/2 -translate-y-1/2 flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          Active
        </Badge>
      );
    }
    
    if (status === "SUSPENDED") {
      return (
        <Badge className="bg-red-500/10 text-red-500 border-red-500/20">
          Suspended
        </Badge>
      );
    }

    if (lifecycle === "DRAFT") {
      return (
        <Badge variant="outline" className="text-muted-foreground border-border bg-muted/50">
          <Clock className="w-3 h-3 mr-1" /> Draft
        </Badge>
      );
    }
    
    if (lifecycle === "APPROVED") {
      return (
        <Badge className="bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border-blue-500/20">
          <ShieldCheck className="w-3 h-3 mr-1" /> Approved
        </Badge>
      );
    }

    return <Badge variant="outline">{status}</Badge>;
  };

  const formatDate = (dateString: string) => {
    try {
      const d = new Date(dateString);
      return new Intl.DateTimeFormat("en-US", { 
        month: "short", 
        day: "numeric", 
        year: "numeric" 
      }).format(d);
    } catch {
      return dateString;
    }
  };

  const filteredAgents = useMemo(() => {
    if (!searchQuery) return agents;
    const lowerQuery = searchQuery.toLowerCase();
    return agents.filter(a => 
      a.name?.toLowerCase().includes(lowerQuery) || 
      a.description?.toLowerCase().includes(lowerQuery)
    );
  }, [agents, searchQuery]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input disabled value="" readOnly placeholder="Loading agents..." className="pl-9 bg-muted/20 border-border" />
        </div>
        <div className="border border-border rounded-lg overflow-hidden bg-background">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow className="border-border">
                <TableHead>Agent Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden md:table-cell">Description</TableHead>
                <TableHead className="text-right">Created</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[1, 2, 3].map((i) => (
                <TableRow key={i} className="border-border">
                  <TableCell><div className="h-4 w-32 bg-muted animate-pulse rounded"></div></TableCell>
                  <TableCell><div className="h-5 w-16 bg-muted animate-pulse rounded-full"></div></TableCell>
                  <TableCell className="hidden md:table-cell"><div className="h-4 w-64 bg-muted animate-pulse rounded"></div></TableCell>
                  <TableCell className="text-right"><div className="h-4 w-20 bg-muted animate-pulse rounded ml-auto"></div></TableCell>
                  <TableCell></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 text-center">
        <ShieldAlert className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-500 font-medium">Failed to load agents</p>
        <p className="text-muted-foreground text-sm mt-1">{error}</p>
        <Button variant="outline" onClick={fetchAgents} className="mt-4">
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative w-full max-w-sm group">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground transition-colors group-focus-within:text-foreground" />
        <Input 
          type="text"
          placeholder="Search agents by name... (⌘K)" 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 bg-background border-input focus-visible:ring-ring transition-all duration-200 shadow-xs" 
        />
      </div>

      {filteredAgents.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-12 text-center flex flex-col items-center justify-center bg-muted/10">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
            <Bot className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-1">
            {searchQuery ? "No matching agents" : isUser ? "No assigned agents yet" : isBuilder ? "No agents built yet" : "No agents registered"}
          </h3>
          <p className="text-muted-foreground max-w-sm mb-6 text-sm">
            {agents.length === 0 
              ? isUser
                ? "You haven't been assigned any AI agents yet. Submit an agent request to have a builder configure one for your workflow."
                : isBuilder
                ? "You haven't created any agents yet. Claim an incoming request from the queue or build a self-initiated agent."
                : "You haven't registered any AI agents in GovernAI yet. Create your first agent to begin governance tracking."
              : `No agents match your search for "${searchQuery}".`
            }
          </p>
          {agents.length === 0 && (
            <div>
              {isUser ? (
                <Link href="/request-agent">
                  <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                    <Sparkles className="w-4 h-4 mr-2" />
                    Request an Agent
                  </Button>
                </Link>
              ) : (
                <Link href="/requests">
                  <Button variant="outline">
                    <ClipboardList className="w-4 h-4 mr-2" />
                    View Requests Queue
                  </Button>
                </Link>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden bg-background shadow-xs">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow className="border-border hover:bg-muted/50">
                <TableHead className="text-muted-foreground">Agent Name</TableHead>
                <TableHead className="text-muted-foreground">Status</TableHead>
                <TableHead className="text-muted-foreground hidden md:table-cell">Description</TableHead>
                <TableHead className="text-muted-foreground text-right">Created</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAgents.map((agent) => (
                <TableRow key={agent.id} className="border-border hover:bg-muted/30 group transition-all duration-200 cursor-pointer relative">
                  <TableCell className="font-medium text-foreground">
                    <Link href={`/agents/${agent.id}`} className="absolute inset-0 z-10">
                      <span className="sr-only">View Agent</span>
                    </Link>
                    <div className="flex items-center gap-2">
                      <span className="group-hover:text-blue-500 transition-colors font-semibold">
                        {agent.name}
                      </span>
                      {agent.request_id && (
                        <Badge variant="outline" className="text-[10px] text-blue-500 border-blue-500/20 bg-blue-500/5">
                          From Request
                        </Badge>
                      )}
                    </div>
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
                  <TableCell className="text-right">
                    <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
