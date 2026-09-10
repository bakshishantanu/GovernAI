"use client";

import { useState, useEffect } from "react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { Execution } from "@/lib/types";
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
import { PlayCircle, Clock, CheckCircle2, XCircle, AlertCircle, Bot } from "lucide-react";
import Link from "next/link";

export default function ExecutionsPage() {
  const { role, isUser } = useAuth();
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExecutions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi("/executions/");
      setExecutions(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || "Failed to load execution runs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExecutions();
    const handleRoleChange = () => fetchExecutions();
    window.addEventListener("govern-ai-role-change", handleRoleChange);
    return () => window.removeEventListener("govern-ai-role-change", handleRoleChange);
  }, [role]);

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case "COMPLETED":
        return (
          <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Completed
          </Badge>
        );
      case "RUNNING":
        return (
          <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20">
            <Clock className="w-3 h-3 mr-1 animate-spin" />
            Running
          </Badge>
        );
      case "FAILED":
        return (
          <Badge className="bg-red-500/10 text-red-500 border-red-500/20">
            <XCircle className="w-3 h-3 mr-1" />
            Failed
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "-";
    try {
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(new Date(dateString));
    } catch {
      return dateString;
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground mb-1">
          {isUser ? "My Runs" : "Execution Runs"}
        </h1>
        <p className="text-muted-foreground">
          {isUser 
            ? "Track historical runs and live executions of your assigned AI agents."
            : "Review agent task executions, runtime status, and invocation metrics across agents."}
        </p>
      </div>

      {loading ? (
        <div className="border border-border rounded-xl p-8 space-y-3 bg-background">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-muted/40 animate-pulse rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-8 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
          <p className="text-red-500 font-semibold">Failed to load execution runs</p>
          <p className="text-muted-foreground text-sm">{error}</p>
          <Button variant="outline" onClick={fetchExecutions}>Try again</Button>
        </div>
      ) : executions.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-12 text-center flex flex-col items-center justify-center bg-muted/10 space-y-3">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
            <PlayCircle className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground">No executions found</h3>
          <p className="text-muted-foreground max-w-sm text-sm">
            {isUser 
              ? "You haven't run any agents yet. Go to My Agents to trigger a task execution."
              : "No agent executions have been dispatched in this scope."}
          </p>
          <Link href="/agents">
            <Button variant="outline">
              <Bot className="w-4 h-4 mr-2" />
              Go to Agents
            </Button>
          </Link>
        </div>
      ) : (
        <div className="border border-border rounded-xl overflow-hidden bg-background shadow-xs">
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow className="border-border">
                <TableHead>Execution ID</TableHead>
                <TableHead>Agent ID</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Started</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions.map((exec) => (
                <TableRow key={exec.id} className="border-border hover:bg-muted/30">
                  <TableCell className="font-mono text-xs text-foreground font-medium">
                    {exec.id}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    <Link href={`/agents/${exec.agent_id}`} className="hover:text-blue-500 hover:underline">
                      {exec.agent_id}
                    </Link>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(exec.status)}
                  </TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">
                    {formatDate(exec.started_at)}
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
