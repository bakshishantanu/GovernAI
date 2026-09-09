"use client";

import { useState, useEffect, useMemo } from "react";
import { fetchApi } from "@/lib/api-client";
import { AgentRequest, AgentRequestStatus } from "@/lib/types";
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
  Search,
  ClipboardList,
  CheckCircle2,
  XCircle,
  Hammer,
  ArrowRight,
  Plus,
  Bot,
  UserCheck
} from "lucide-react";
import Link from "next/link";

export function RequestsList() {
  const { role, isBuilder, isAdmin, isUser } = useAuth();
  const [requests, setRequests] = useState<AgentRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi("/agent-requests/");
      setRequests(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || "Failed to load requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();

    const handleRoleChange = () => {
      fetchRequests();
    };

    window.addEventListener("govern-ai-role-change", handleRoleChange);
    return () => window.removeEventListener("govern-ai-role-change", handleRoleChange);
  }, [role]);

  const handleClaim = async (requestId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setActionLoadingId(requestId);
      await fetchApi(`/agent-requests/${requestId}/claim`, {
        method: "POST",
      });
      await fetchRequests();
    } catch (err: any) {
      alert(`Claim failed: ${err.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleCancel = async (requestId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to cancel this agent request?")) return;
    try {
      setActionLoadingId(requestId);
      await fetchApi(`/agent-requests/${requestId}/cancel`, {
        method: "POST",
      });
      await fetchRequests();
    } catch (err: any) {
      alert(`Cancel failed: ${err.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const getStatusBadge = (status: AgentRequestStatus) => {
    switch (status) {
      case "PENDING":
        return (
          <Badge className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-amber-500/20 pl-3.5 relative">
            <span className="absolute left-1.5 top-1/2 -translate-y-1/2 flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500"></span>
            </span>
            Pending Builder
          </Badge>
        );
      case "CLAIMED":
        return (
          <Badge className="bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border-blue-500/20">
            <Hammer className="w-3 h-3 mr-1" />
            In Development
          </Badge>
        );
      case "FULFILLED":
        return (
          <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Fulfilled
          </Badge>
        );
      case "CANCELLED":
        return (
          <Badge variant="outline" className="text-muted-foreground border-border bg-muted/40">
            <XCircle className="w-3 h-3 mr-1" />
            Cancelled
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const d = new Date(dateString);
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      }).format(d);
    } catch {
      return dateString;
    }
  };

  const filteredRequests = useMemo(() => {
    return requests.filter((req) => {
      const matchesSearch =
        !searchQuery ||
        req.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.description?.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus =
        statusFilter === "ALL" || req.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [requests, searchQuery, statusFilter]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex gap-3">
          <div className="h-10 w-64 bg-muted animate-pulse rounded-md" />
          <div className="h-10 w-32 bg-muted animate-pulse rounded-md" />
        </div>
        <div className="border border-border rounded-xl p-8 space-y-4 bg-background">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted/40 animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-8 text-center space-y-3">
        <ClipboardList className="w-8 h-8 text-red-500 mx-auto" />
        <p className="text-red-500 font-semibold">Failed to load agent requests</p>
        <p className="text-muted-foreground text-sm">{error}</p>
        <Button variant="outline" onClick={fetchRequests} className="mt-2">
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search requests..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-background border-input"
            />
          </div>

          <div className="flex items-center bg-muted/40 p-1 rounded-lg border border-border text-xs">
            {["ALL", "PENDING", "CLAIMED", "FULFILLED"].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md transition-all font-medium ${
                  statusFilter === st
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {st === "ALL" ? "All" : st.charAt(0) + st.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>

        {isUser && (
          <Link href="/request-agent">
            <Button className="bg-blue-600 hover:bg-blue-700 text-white w-full sm:w-auto">
              <Plus className="w-4 h-4 mr-1.5" />
              New Agent Request
            </Button>
          </Link>
        )}
      </div>

      {/* Requests List Table */}
      {filteredRequests.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-12 text-center flex flex-col items-center justify-center bg-muted/10 space-y-3">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
            <ClipboardList className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground">No requests found</h3>
          <p className="text-muted-foreground max-w-md text-sm">
            {requests.length === 0
              ? isUser
                ? "You haven't requested any agents yet. Create your first request to have a builder design an AI agent for your workflow."
                : isBuilder
                ? "The requests queue is currently empty. As users submit agent requests, they will appear here ready to be claimed."
                : "No agent requests recorded in the system yet."
              : `No requests matched your filter "${statusFilter}" and search "${searchQuery}".`}
          </p>
          {isUser && requests.length === 0 && (
            <Link href="/request-agent" className="pt-2">
              <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                <Plus className="w-4 h-4 mr-1.5" />
                Request an Agent Now
              </Button>
            </Link>
          )}
        </div>
      ) : (
        <div className="border border-border rounded-xl overflow-hidden bg-background shadow-xs">
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow className="border-border">
                <TableHead className="w-[300px]">Request Title</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden md:table-cell">Requested Skills</TableHead>
                <TableHead className="hidden lg:table-cell text-right">Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRequests.map((req) => (
                <TableRow
                  key={req.id}
                  className="border-border hover:bg-muted/30 group transition-colors"
                >
                  <TableCell className="font-medium text-foreground">
                    <Link href={`/requests/${req.id}`} className="block">
                      <span className="font-semibold group-hover:text-blue-500 transition-colors">
                        {req.title}
                      </span>
                      <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5 max-w-xs sm:max-w-sm">
                        {req.description}
                      </p>
                    </Link>
                  </TableCell>

                  <TableCell>
                    {getStatusBadge(req.status)}
                  </TableCell>

                  <TableCell className="hidden md:table-cell">
                    <div className="flex flex-wrap gap-1.5 max-w-[240px]">
                      {req.requested_skills && req.requested_skills.length > 0 ? (
                        req.requested_skills.map((skillId: string) => (
                          <Badge key={skillId} variant="secondary" className="text-[11px] font-mono">
                            {skillId}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">General Agent</span>
                      )}
                    </div>
                  </TableCell>

                  <TableCell className="hidden lg:table-cell text-right text-xs text-muted-foreground">
                    {formatDate(req.created_at)}
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {/* Action buttons based on status & role */}
                      {req.status === "PENDING" && (isBuilder || isAdmin) && (
                        <Button
                          size="sm"
                          disabled={actionLoadingId === req.id}
                          onClick={(e) => handleClaim(req.id, e)}
                          className="bg-blue-600 hover:bg-blue-700 text-white h-8 text-xs font-medium"
                        >
                          <UserCheck className="w-3.5 h-3.5 mr-1" />
                          Claim
                        </Button>
                      )}

                      {req.status === "CLAIMED" && (isBuilder || isAdmin) && (
                        <Link href={`/requests/${req.id}`}>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 text-xs border-blue-500/30 text-blue-500 hover:bg-blue-500/10"
                          >
                            <Hammer className="w-3.5 h-3.5 mr-1" />
                            Build Agent
                          </Button>
                        </Link>
                      )}

                      {req.status === "FULFILLED" && req.agent_id && (
                        <Link href={`/agents/${req.agent_id}`}>
                          <Button
                            size="sm"
                            className="bg-emerald-600 hover:bg-emerald-700 text-white h-8 text-xs font-medium"
                          >
                            <Bot className="w-3.5 h-3.5 mr-1" />
                            View Agent
                          </Button>
                        </Link>
                      )}

                      {req.status === "PENDING" && (isUser || isAdmin) && (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={actionLoadingId === req.id}
                          onClick={(e) => handleCancel(req.id, e)}
                          className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-8 text-xs"
                        >
                          Cancel
                        </Button>
                      )}

                      <Link href={`/requests/${req.id}`}>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 text-muted-foreground group-hover:text-foreground"
                          title="View Details"
                        >
                          <ArrowRight className="w-4 h-4" />
                        </Button>
                      </Link>
                    </div>
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
