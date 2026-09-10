"use client";

import { useState, useEffect } from "react";
import { fetchApi } from "@/lib/api-client";
import { Skill } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { 
  Sparkles, 
  Puzzle, 
  CheckCircle2, 
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";

const FALLBACK_SKILLS: Skill[] = [
  {
    id: "ticketing",
    name: "ticketing",
    display_name: "Ticketing & ITSM",
    description: "Create, update, and resolve enterprise support tickets and service requests.",
    trust_level: "verified"
  },
  {
    id: "solr_search",
    name: "solr_search",
    display_name: "Enterprise Search",
    description: "Full-text search over enterprise document collections, governed per agent.",
    trust_level: "verified"
  },
  {
    id: "document_search",
    name: "document_search",
    display_name: "Knowledge Search (RAG)",
    description: "Semantic search across internal corporate knowledge bases, wikis, and SOPs.",
    trust_level: "verified"
  }
];

export function RequestAgentForm() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [availableSkills, setAvailableSkills] = useState<Skill[]>(FALLBACK_SKILLS);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successRequestId, setSuccessRequestId] = useState<string | null>(null);

  useEffect(() => {
    async function loadSkills() {
      try {
        const data = await fetchApi("/skills/");
        if (Array.isArray(data) && data.length > 0) {
          setAvailableSkills(data);
        }
      } catch (err) {
        // Use fallback skills in local development
        console.warn("Using default skills list", err);
      }
    }
    loadSkills();
  }, []);

  const toggleSkill = (skillId: string) => {
    setSelectedSkills(prev => 
      prev.includes(skillId) 
        ? prev.filter(id => id !== skillId)
        : [...prev, skillId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError("Please fill out both the title and description.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi("/agent-requests/", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          requested_skills: selectedSkills,
        }),
      });

      setSuccessRequestId(response.id);
    } catch (err: any) {
      setError(err.message || "Failed to submit agent request.");
    } finally {
      setLoading(false);
    }
  };

  if (successRequestId) {
    return (
      <div className="bg-background border border-border rounded-xl p-8 max-w-2xl mx-auto text-center space-y-6 shadow-sm">
        <div className="w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle2 className="w-8 h-8" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Agent Request Submitted!</h2>
          <p className="text-muted-foreground mt-2 max-w-md mx-auto">
            Your request has been routed to the Agent Builder team queue. You can track progress in your Requests queue.
          </p>
        </div>

        <div className="bg-muted/40 border border-border rounded-lg p-4 font-mono text-xs text-muted-foreground text-left max-w-md mx-auto">
          <div><span className="text-foreground font-semibold">Request ID:</span> {successRequestId}</div>
          <div className="mt-1"><span className="text-foreground font-semibold">Title:</span> {title}</div>
          <div className="mt-1"><span className="text-foreground font-semibold">Status:</span> <span className="text-amber-500 font-semibold">PENDING</span></div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Link href={`/requests/${successRequestId}`}>
            <Button className="bg-blue-600 hover:bg-blue-700 text-white w-full sm:w-auto">
              View Request Status
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
          <Button 
            variant="outline"
            onClick={() => {
              setTitle("");
              setDescription("");
              setSelectedSkills([]);
              setSuccessRequestId(null);
            }}
            className="w-full sm:w-auto"
          >
            Submit Another Request
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8 max-w-3xl">
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 text-red-500 text-sm">
          <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Unable to submit request</p>
            <p className="text-xs mt-0.5 text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Basic Info */}
      <div className="bg-background border border-border rounded-xl p-6 space-y-5 shadow-sm">
        <div className="flex items-center gap-2 border-b border-border pb-3">
          <Sparkles className="w-5 h-5 text-blue-500" />
          <h2 className="text-lg font-semibold text-foreground">1. Agent Overview</h2>
        </div>

        <div className="space-y-2">
          <Label htmlFor="title" className="text-foreground font-medium">
            Agent Name / Title <span className="text-red-500">*</span>
          </Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. IT Helpdesk Assistant, Quarterly Sales Analyst"
            className="bg-background border-input focus-visible:ring-ring text-foreground"
            required
          />
          <p className="text-xs text-muted-foreground">
            A concise title that describes what this agent is for.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="description" className="text-foreground font-medium">
            Business Requirements & Description <span className="text-red-500">*</span>
          </Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the tasks this agent should perform, expected inputs/outputs, guardrails, and target workflow..."
            className="bg-background border-input focus-visible:ring-ring min-h-[140px] text-foreground"
            required
          />
          <p className="text-xs text-muted-foreground">
            Provide enough detail so the Agent Builder understands tool requirements and compliance boundaries.
          </p>
        </div>
      </div>

      {/* Requested Skills */}
      <div className="bg-background border border-border rounded-xl p-6 space-y-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <Puzzle className="w-5 h-5 text-indigo-500" />
            <h2 className="text-lg font-semibold text-foreground">2. Required Skills & Tools</h2>
          </div>
          <span className="text-xs text-muted-foreground">
            {selectedSkills.length} selected
          </span>
        </div>

        <p className="text-sm text-muted-foreground">
          Select the enterprise capabilities this agent will need. The builder will configure and verify governance compliance for each skill.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          {availableSkills.map((skill) => {
            const isSelected = selectedSkills.includes(skill.id || skill.name);
            const skillId = skill.id || skill.name;
            return (
              <div
                key={skillId}
                onClick={() => toggleSkill(skillId)}
                className={`p-4 rounded-lg border text-left cursor-pointer transition-all duration-200 select-none ${
                  isSelected
                    ? "border-blue-500 bg-blue-500/10 dark:bg-blue-500/15 ring-1 ring-blue-500"
                    : "border-border bg-background hover:bg-muted/30 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground text-sm">
                      {skill.display_name || skill.name}
                    </span>
                    {skill.trust_level && (
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 uppercase">
                        {skill.trust_level}
                      </Badge>
                    )}
                  </div>
                  <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                    isSelected ? "bg-blue-600 border-blue-600 text-white" : "border-slate-300 dark:border-slate-600"
                  }`}>
                    {isSelected && <CheckCircle2 className="w-3 h-3" />}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                  {skill.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex items-center justify-between pt-2">
        <Link href="/requests">
          <Button variant="ghost" type="button" className="text-muted-foreground">
            Cancel
          </Button>
        </Link>
        <Button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 shadow-sm"
        >
          {loading ? (
            "Submitting Request..."
          ) : (
            <>
              Submit Request to Builders
              <ArrowRight className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
