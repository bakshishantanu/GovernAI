"use client";

import { useAuth } from "@/lib/auth-context";
import { AgentList } from "./components/agent-list";
import { CreateAgentButton } from "./components/create-agent-button";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";
import Link from "next/link";

export default function AgentsPage() {
  const { role, isUser } = useAuth();

  const getPageTitle = () => {
    switch (role) {
      case "agent_builder":
        return "My Builds";
      case "user":
        return "My Agents";
      case "admin":
      default:
        return "All Agents";
    }
  };

  const getPageDescription = () => {
    switch (role) {
      case "agent_builder":
        return "Manage AI agents you have developed, configured skills for, and submitted for compliance review.";
      case "user":
        return "AI agents deployed and assigned to you for automated workflows and task execution.";
      case "admin":
      default:
        return "Manage your organization's AI agents, view compliance passports, and track governance policies.";
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-1">
            {getPageTitle()}
          </h1>
          <p className="text-muted-foreground">
            {getPageDescription()}
          </p>
        </div>
        <div>
          {isUser ? (
            <Link href="/request-agent">
              <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                <Sparkles className="h-4 w-4 mr-2" />
                Request an Agent
              </Button>
            </Link>
          ) : (
            <CreateAgentButton />
          )}
        </div>
      </div>
      
      <AgentList />
    </div>
  );
}
