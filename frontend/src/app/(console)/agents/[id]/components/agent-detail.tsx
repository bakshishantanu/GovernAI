"use client";

import { useState, useEffect } from "react";
import { fetchApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import Link from "next/link";
import { 
  ArrowLeft, 
  PlayCircle, 
  Clock, 
  ShieldCheck, 
  ShieldAlert, 
  Settings,
  AlertOctagon,
  RotateCcw,
  ClipboardList,
  User,
  Terminal
} from "lucide-react";

export function AgentDetail({ id }: { id: string }) {
  const { role, isAdmin, isBuilder } = useAuth();
  const [agent, setAgent] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Execution modal state
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [promptInput, setPromptInput] = useState("Summarize recent compliance events and check for policy anomalies.");
  const [runLoading, setRunLoading] = useState(false);
  const [executionResult, setExecutionResult] = useState<any | null>(null);

  const fetchAgent = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi(`/agents/${id}`);
      setAgent(data);
    } catch (err: any) {
      setError(err.message || "Failed to load agent details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgent();

    const handleRoleChange = () => {
      fetchAgent();
    };
    window.addEventListener("govern-ai-role-change", handleRoleChange);
    return () => window.removeEventListener("govern-ai-role-change", handleRoleChange);
  }, [id, role]);

  const handleAction = async (action: "submit" | "activate") => {
    try {
      setActionLoading(true);
      const updatedAgent = await fetchApi(`/agents/${id}/${action}`, {
        method: "PATCH",
      });
      setAgent(updatedAgent);
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleKillSwitch = async () => {
    if (!confirm("EMERGENCY KILL SWITCH: Are you sure you want to suspend this agent immediately across all org environments?")) {
      return;
    }
    try {
      setActionLoading(true);
      const updatedAgent = await fetchApi(`/agents/${id}/kill`, {
        method: "POST",
      });
      setAgent(updatedAgent);
    } catch (err: any) {
      alert(`Kill switch failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReactivate = async () => {
    try {
      setActionLoading(true);
      const updatedAgent = await fetchApi(`/agents/${id}/reactivate`, {
        method: "POST",
      });
      setAgent(updatedAgent);
    } catch (err: any) {
      alert(`Reactivation failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecuteAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setRunLoading(true);
      setExecutionResult(null);
      const res = await fetchApi("/executions/", {
        method: "POST",
        body: JSON.stringify({
          agent_id: id,
          prompt: promptInput,
        }),
      });
      setExecutionResult(res);
    } catch (err: any) {
      alert(`Execution failed: ${err.message}`);
    } finally {
      setRunLoading(false);
    }
  };

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
      );
    }

    if (status === "SUSPENDED") {
      return (
        <Badge className="bg-red-500/10 text-red-500 border-red-500/20 text-sm py-1">
          <AlertOctagon className="w-3.5 h-3.5 mr-1.5" />
          Suspended by Admin
        </Badge>
      );
    }
    
    if (lifecycle === "DRAFT") {
      return (
        <Badge variant="outline" className="text-muted-foreground border-border bg-muted/50 text-sm py-1">
          <Clock className="w-3 h-3 mr-1.5" /> Draft
        </Badge>
      );
    }
    
    if (lifecycle === "APPROVED") {
      return (
        <Badge className="bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border-blue-500/20 text-sm py-1">
          <ShieldCheck className="w-3 h-3 mr-1.5" /> Approved
        </Badge>
      );
    }

    return <Badge variant="outline" className="text-sm py-1">{status}</Badge>;
  };

  const formatDate = (dateString: string) => {
    try {
      const d = new Date(dateString);
      return new Intl.DateTimeFormat("en-US", { 
        month: "long", 
        day: "numeric", 
        year: "numeric", 
        hour: "2-digit", 
        minute: "2-digit" 
      }).format(d);
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto">
        <div className="flex items-center gap-4">
          <div className="h-8 w-8 bg-muted animate-pulse rounded-md" />
          <div className="h-8 w-48 bg-muted animate-pulse rounded-md" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 h-[300px] bg-muted animate-pulse rounded-xl" />
          <div className="h-[300px] bg-muted animate-pulse rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6 text-center max-w-md mx-auto">
        <ShieldAlert className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-500 font-semibold">Failed to load agent details</p>
        <p className="text-muted-foreground text-sm mt-1">{error}</p>
        <Link href="/agents">
          <Button variant="outline" className="mt-4">Back to Agents</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
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

        {/* Action Buttons Gated by Role & Lifecycle */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Builder / Admin: Submit for compliance review */}
          {(isBuilder || isAdmin) && agent.passport?.lifecycle_state === "DRAFT" && (
            <Button 
              onClick={() => handleAction("submit")} 
              disabled={actionLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <ShieldCheck className="w-4 h-4 mr-2" />
              Submit for Review
            </Button>
          )}

          {/* Builder / Admin: Activate Agent (Triggers automatic handover if request linked) */}
          {(isBuilder || isAdmin) && agent.passport?.lifecycle_state === "APPROVED" && agent.status !== "ACTIVE" && (
            <Button 
              onClick={() => handleAction("activate")}
              disabled={actionLoading}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              <PlayCircle className="w-4 h-4 mr-2" />
              Activate & Handover
            </Button>
          )}

          {/* User / Builder / Admin: Run Agent if Active */}
          {agent.status === "ACTIVE" && (
            <Button
              onClick={() => setRunModalOpen(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Terminal className="w-4 h-4 mr-2" />
              Run Agent
            </Button>
          )}

          {/* Admin only: Kill Switch (Emergency Stop) */}
          {isAdmin && agent.status === "ACTIVE" && (
            <Button
              variant="destructive"
              onClick={handleKillSwitch}
              disabled={actionLoading}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              <AlertOctagon className="w-4 h-4 mr-2" />
              Kill Switch
            </Button>
          )}

          {/* Admin only: Reactivate suspended agent */}
          {isAdmin && agent.status === "SUSPENDED" && (
            <Button
              variant="outline"
              onClick={handleReactivate}
              disabled={actionLoading}
              className="border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Reactivate Agent
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
        
        {/* Compliance Passport Card */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-background border border-border rounded-xl p-6 shadow-xs">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-500" />
                <h2 className="text-lg font-semibold">Compliance Passport</h2>
              </div>
              {agent.passport?.compliance_status && (
                <Badge className={
                  agent.passport.compliance_status === "PASSED" 
                    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                    : agent.passport.compliance_status === "FAILED"
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
                <p className="text-base font-medium text-foreground">{agent.passport?.lifecycle_state || "DRAFT"}</p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">Compliance Checked</span>
                <p className="text-sm text-foreground">
                  {agent.passport?.compliance_checked_at ? formatDate(agent.passport.compliance_checked_at) : "Pending review"}
                </p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">Agent ID</span>
                <p className="text-xs text-foreground font-mono bg-muted/50 p-2 rounded-md truncate">
                  {agent.id}
                </p>
              </div>
              <div className="space-y-1">
                <span className="text-sm font-medium text-muted-foreground">Created At</span>
                <p className="text-sm text-foreground">{formatDate(agent.created_at)}</p>
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
                  Standard sandboxed permissions (no elevated tool privileges).
                </p>
              )}
            </div>
          </div>

          {/* Governance & Ownership Card */}
          <div className="bg-background border border-border rounded-xl p-6 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <User className="w-4 h-4 text-blue-500" />
              Ownership & Handover Status
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="p-3 bg-muted/30 border border-border/60 rounded-lg space-y-1">
                <span className="text-xs text-muted-foreground font-medium">Created By (Builder):</span>
                <p className="font-mono text-xs text-foreground truncate">
                  {agent.owner_id || "System Admin"}
                </p>
              </div>

              <div className="p-3 bg-muted/30 border border-border/60 rounded-lg space-y-1">
                <span className="text-xs text-muted-foreground font-medium">Assigned User (Handover):</span>
                {agent.assigned_user_id ? (
                  <p className="font-mono text-xs text-emerald-600 dark:text-emerald-400 truncate font-semibold">
                    {agent.assigned_user_id}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Self-initiated build (not yet assigned to a user)
                  </p>
                )}
              </div>
            </div>

            {agent.request_id && (
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <ClipboardList className="w-4 h-4 text-blue-500" />
                  <span>Built from Request: <code className="font-mono">{agent.request_id}</code></span>
                </div>
                <Link href={`/requests/${agent.request_id}`} className="text-blue-500 hover:underline font-medium">
                  View Request Details →
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Configuration Sidebar */}
        <div className="space-y-6">
          <div className="bg-background border border-border rounded-xl p-6 shadow-xs">
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
                    <ShieldAlert className="w-4 h-4 text-amber-500" />
                    Global PII Redaction
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Execute Agent Dialog */}
      <Dialog open={runModalOpen} onOpenChange={setRunModalOpen}>
        <DialogContent className="sm:max-w-[540px] bg-background border-border text-foreground">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-blue-500" />
              Run Agent: {agent.name}
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Dispatch an execution query. The execution runtime will enforce compliance checks and tool policies.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleExecuteAgent} className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="run-prompt">Task / Prompt</Label>
              <Textarea
                id="run-prompt"
                value={promptInput}
                onChange={(e) => setPromptInput(e.target.value)}
                required
                className="bg-background border-input min-h-[90px]"
              />
            </div>

            {executionResult && (
              <div className="p-3 bg-muted/50 border border-border rounded-lg text-xs space-y-1">
                <div className="flex items-center justify-between text-emerald-500 font-semibold">
                  <span>Execution Initiated</span>
                  <Badge variant="outline" className="text-[10px]">
                    {executionResult.status || "RUNNING"}
                  </Badge>
                </div>
                <p className="text-muted-foreground font-mono truncate">
                  Execution ID: {executionResult.id}
                </p>
              </div>
            )}

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setRunModalOpen(false)}
              >
                Close
              </Button>
              <Button
                type="submit"
                disabled={runLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {runLoading ? "Executing..." : "Start Execution"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
