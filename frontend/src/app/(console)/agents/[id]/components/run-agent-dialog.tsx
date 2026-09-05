"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api-client";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Play } from "lucide-react";

/**
 * Start a run and go straight to watching it.
 *
 * `POST /executions/` returns 202 with the id *before* the run begins (D-019),
 * which is the whole reason a live view is possible: by the time this pushes
 * to `/runs/{id}`, the stream is open before the first tool call happens. Do
 * not make this wait for a result — there isn't one yet, by design.
 */

const FIELD =
  "w-full rounded-xl border-2 border-border bg-gv-paper px-3 py-2 text-[13.5px] font-semibold text-foreground placeholder:text-gv-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gv-pink";

const LABEL = "text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label";

export function RunAgentDialog({ agentId }: { agentId: string }) {
  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (starting) return;

    setStarting(true);
    setError(null);
    try {
      const execution = await fetchApi("/executions/", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, goal }),
      });
      if (!execution?.id) throw new Error("The run started but returned no id.");
      setOpen(false);
      setGoal("");
      router.push(`/runs/${execution.id}`);
    } catch (err: any) {
      setError(err.message || "Could not start the run");
    } finally {
      setStarting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="gv-card inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-xl border-2 border-border bg-gv-teal px-[17px] text-[13.5px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px">
        <Play className="h-4 w-4" strokeWidth={2.6} />
        Run agent
      </DialogTrigger>

      <DialogContent className="gv-panel rounded-lg border-2 border-border bg-card text-foreground sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="font-display text-[22px] leading-none">Start a run</DialogTitle>
          <DialogDescription className="text-[13px] font-bold text-gv-muted">
            Every tool call is checked against this agent&apos;s passport and its budget. You will
            watch that happen live.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="run-goal" className={LABEL}>
              Goal
            </Label>
            <Textarea
              id="run-goal"
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder="e.g. Summarise last quarter's support tickets by theme"
              className={`${FIELD} min-h-[96px]`}
              maxLength={2000}
              required
            />
          </div>

          {error && (
            <p role="alert" className="text-[13px] font-extrabold text-gv-held">
              {error}
            </p>
          )}

          <DialogFooter>
            <button
              type="submit"
              disabled={starting}
              className="gv-card inline-flex h-10 items-center gap-2 rounded-xl border-2 border-border bg-gv-teal px-[17px] text-[13.5px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px disabled:opacity-60"
            >
              <Play className="h-4 w-4" strokeWidth={2.6} />
              {starting ? "Starting…" : "Start and watch"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
