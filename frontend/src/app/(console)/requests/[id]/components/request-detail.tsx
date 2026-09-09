"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api-client";
import { AgentRequest, AgentRequestStatus } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import {
  ArrowLeft, 
  Hammer, 
  CheckCircle2, 
  XCircle, 
  Bot, 
  ShieldCheck, 
  ShieldAlert
} from "lucide-react";
import Link from "next/link";

export function RequestDetail({ id }: { id: string }) {
  const router = useRouter();
  const { isBuilder, isAdmin, isUser } = useAuth();
  const [request, setRequest] = useState<AgentRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Build Agent Modal state
  const [buildDialogOpen, setBuildDialogOpen] = useState(false);
  const [agentName, setAgentName] = useState("");
  const [agentDescription, setAgentDescription] = useState("");
  const [buildLoading, setBuildLoading] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);

  const fetchRequest = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi(`/agent-requests/${id}`);
      setRequest(data);
      if (data) {
        setAgentName(data.title);
        setAgentDescription(data.description);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load request.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequest();
  }, [id]);

  const handleClaim = async () => {
    try {
      setActionLoading(true);
      const updated = await fetchApi(`/agent-requests/${id}/claim`, {
        method: "POST",
      });
      setRequest(updated);
    } catch (err: any) {
      alert(`Claim failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this request?")) return;
    try {
      setActionLoading(true);
      const updated = await fetchApi(`/agent-requests/${id}/cancel`, {
        method: "POST",
      });
      setRequest(updated);
    } catch (err: any) {
      alert(`Cancel failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleBuildAgentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBuildLoading(true);
    setBuildError(null);

    try {
      const createdAgent = await fetchApi("/agents/", {
        method: "POST",
        body: JSON.stringify({
          name: agentName,
          description: agentDescription,
          skills: request?.requested_skills || [],
          request_id: request?.id,
        }),
      });

      setBuildDialogOpen(false);
      // Navigate directly to the newly created agent to complete review & activation
      router.push(`/agents/${createdAgent.id}`);
    } catch (err: any) {
      setBuildError(err.message || "Failed to create agent against request");
    } finally {
      setBuildLoading(false);
    }
  };

  const getStatusBadge = (status: AgentRequestStatus) => {
    switch (status) {
      case "PENDING":
        return (
          <Badge className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-amber-500/20 pl-3.5 relative text-sm py-1">
            <span className="absolute left-1.5 top-1/2 -translate-y-1/2 flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500"></span>
            </span>
            Pending Builder Claim
          </Badge>
        );
      case "CLAIMED":
        return (
          <Badge className="bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border-blue-500/20 text-sm py-1">
            <Hammer className="w-3.5 h-3.5 mr-1.5" />
            In Development
          </Badge>
        );
      case "FULFILLED":
        return (
          <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 text-sm py-1">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
            Fulfilled & Active
          </Badge>
        );
      case "CANCELLED":
        return (
          <Badge variant="outline" className="text-muted-foreground border-border bg-muted/40 text-sm py-1">
            <XCircle className="w-3.5 h-3.5 mr-1.5" />
            Cancelled
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "Pending";
    try {
      return new Intl.DateTimeFormat("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(dateString));
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="h-8 w-48 bg-muted animate-pulse rounded-md" />
        <div className="h-48 bg-muted/30 animate-pulse rounded-xl" />
        <div className="h-64 bg-muted/30 animate-pulse rounded-xl" />
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-8 text-center space-y-3 max-w-md mx-auto">
        <ShieldAlert className="w-8 h-8 text-red-500 mx-auto" />
        <p className="text-red-500 font-semibold">Request not found or unauthorized</p>
        <p className="text-muted-foreground text-sm">{error}</p>
        <Link href="/requests">
          <Button variant="outline" className="mt-2">
            Back to Requests
          </Button>
        </Link>
      </div>
    );
  }

  const steps = [
    {
      title: "Intake",
      desc: "User requested agent",
      date: request.created_at,
      completed: true,
      active: request.status === "PENDING",
    },
    {
      title: "Claimed",
      desc: request.builder_id ? "Builder assigned" : "Awaiting builder",
      date: request.claimed_at,
      completed: !!request.claimed_at,
      active: request.status === "CLAIMED",
    },
    {
      title: "Handover",
      desc: request.status === "FULFILLED" ? "Agent active & handed over" : "Compliance review",
      date: request.fulfilled_at,
      completed: request.status === "FULFILLED",
      active: request.status === "FULFILLED",
    },
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Top Navigation & Status */}
      <div className="space-y-4">
        <Link
          href="/requests"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to Requests Queue
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight text-foreground">
                {request.title}
              </h1>
              {getStatusBadge(request.status)}
            </div>
            <p className="text-xs text-muted-foreground mt-1 font-mono">
              Request ID: {request.id}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {request.status === "PENDING" && (isBuilder || isAdmin) && (
              <Button
                onClick={handleClaim}
                disabled={actionLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Hammer className="w-4 h-4 mr-2" />
                Claim this Request
              </Button>
            )}

            {request.status === "CLAIMED" && (isBuilder || isAdmin) && (
              <Button
                onClick={() => setBuildDialogOpen(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Bot className="w-4 h-4 mr-2" />
                Build Agent for Request
              </Button>
            )}

            {request.status === "FULFILLED" && request.agent_id && (
              <Link href={`/agents/${request.agent_id}`}>
                <Button className="bg-emerald-600 hover:bg-emerald-700 text-white">
                  <Bot className="w-4 h-4 mr-2" />
                  View Handed-Over Agent
                </Button>
              </Link>
            )}

            {request.status === "PENDING" && (isUser || isAdmin) && (
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={actionLoading}
                className="text-red-500 hover:text-red-600 border-red-500/20 hover:bg-red-500/10"
              >
                Cancel Request
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Lifecycle Progress Stepper */}
      <div className="bg-background border border-border rounded-xl p-6 shadow-xs">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-5">
          Request Lifecycle Tracker
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {steps.map((step, idx) => (
            <div
              key={step.title}
              className={`p-4 rounded-lg border transition-all ${
                step.completed
                  ? "border-blue-500/30 bg-blue-500/5 dark:bg-blue-500/10"
                  : "border-border bg-muted/20 text-muted-foreground"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                    step.completed
                      ? "bg-blue-600 text-white"
                      : "bg-muted text-muted-foreground border border-border"
                  }`}
                >
                  {step.completed ? "✓" : idx + 1}
                </div>
                <span className="font-semibold text-foreground text-sm">
                  {step.title}
                </span>
              </div>
              <p className="text-xs text-muted-foreground pl-7">{step.desc}</p>
              {step.date && (
                <p className="text-[11px] text-muted-foreground pl-7 mt-1">
                  {formatDate(step.date)}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left 2 Cols: Description & Skills */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-background border border-border rounded-xl p-6 shadow-xs space-y-4">
            <h3 className="text-base font-semibold text-foreground">
              Business Specifications & Instructions
            </h3>
            <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
              {request.description}
            </p>
          </div>

          <div className="bg-background border border-border rounded-xl p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-foreground">
                Requested Skills & Integrations
              </h3>
              <span className="text-xs text-muted-foreground">
                {request.requested_skills.length} skills
              </span>
            </div>

            {request.requested_skills && request.requested_skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {request.requested_skills.map((skillId) => (
                  <div
                    key={skillId}
                    className="p-3 rounded-lg border border-border bg-muted/20 flex items-center gap-2 text-sm font-medium text-foreground"
                  >
                    <ShieldCheck className="w-4 h-4 text-blue-500" />
                    <span>{skillId}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No specific skills requested. Builder may select appropriate tools.
              </p>
            )}
          </div>
        </div>

        {/* Right 1 Col: Metadata & Governance Handover */}
        <div className="space-y-6">
          <div className="bg-background border border-border rounded-xl p-6 shadow-xs space-y-4 text-sm">
            <h3 className="font-semibold text-foreground border-b border-border pb-2">
              Assignment & Stakeholders
            </h3>

            <div className="space-y-1">
              <span className="text-xs text-muted-foreground">Requester ID (User)</span>
              <p className="font-mono text-xs bg-muted/40 p-2 rounded truncate">
                {request.requester_id}
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-xs text-muted-foreground">Assigned Builder</span>
              {request.builder_id ? (
                <p className="font-mono text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 p-2 rounded truncate">
                  {request.builder_id}
                </p>
              ) : (
                <p className="text-xs text-amber-500 bg-amber-500/10 p-2 rounded">
                  Unassigned — in team queue
                </p>
              )}
            </div>

            {request.agent_id && (
              <div className="space-y-1">
                <span className="text-xs text-muted-foreground">Linked Agent ID</span>
                <p className="font-mono text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 p-2 rounded truncate">
                  {request.agent_id}
                </p>
              </div>
            )}

            <div className="space-y-1 pt-2 border-t border-border">
              <span className="text-xs text-muted-foreground">Submitted Date</span>
              <p className="text-xs font-medium text-foreground">
                {formatDate(request.created_at)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Build Agent Modal */}
      <Dialog open={buildDialogOpen} onOpenChange={setBuildDialogOpen}>
        <DialogContent className="sm:max-w-[480px] bg-background border-border text-foreground">
          <DialogHeader>
            <DialogTitle>Build Agent for this Request</DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Create an AI agent linked to this request. Upon activation, the agent will be automatically handed over to the requester.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleBuildAgentSubmit} className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Agent Name</Label>
              <Input
                id="agent-name"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                required
                className="bg-background border-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="agent-desc">Description</Label>
              <Textarea
                id="agent-desc"
                value={agentDescription}
                onChange={(e) => setAgentDescription(e.target.value)}
                required
                className="bg-background border-input min-h-[100px]"
              />
            </div>

            <div className="p-3 bg-muted/40 rounded-lg text-xs space-y-1 border border-border">
              <p className="font-medium text-foreground">Linked Skills:</p>
              <div className="flex flex-wrap gap-1">
                {request.requested_skills.map((s) => (
                  <Badge key={s} variant="outline" className="text-[10px]">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>

            {buildError && (
              <p className="text-sm text-red-500 font-medium">{buildError}</p>
            )}

            <DialogFooter className="pt-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setBuildDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={buildLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {buildLoading ? "Building..." : "Create & Open Agent"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
