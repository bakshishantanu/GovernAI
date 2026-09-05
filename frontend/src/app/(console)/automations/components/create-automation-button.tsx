"use client";

import { useState } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, OctagonX } from "lucide-react";

/**
 * Build a rule by choosing a trigger and an action.
 *
 * Only the triggers and actions the backend genuinely implements are offered.
 * There is no "send an email" option, because there is no mail infrastructure
 * behind one — an inert control in a governance console is worse than a
 * missing feature, because someone will rely on it.
 *
 * The sentence under the form is the rule read back in plain English, built
 * from the values the form will actually post. Someone creating a rule that
 * can suspend an agent should be able to check what they built without
 * decoding a JSON config.
 */

const FIELD =
  "w-full rounded-xl border-2 border-border bg-gv-paper px-3 py-2 text-[13.5px] font-semibold text-foreground placeholder:text-gv-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gv-pink";

const LABEL = "text-[11px] font-extrabold uppercase tracking-[0.07em] text-gv-label";

type TriggerType = "TOOL_DENIED" | "SPEND_THRESHOLD" | "AGENT_SUSPENDED";
type ActionType = "SUSPEND_AGENT" | "RAISE_ALERT";

const TRIGGER_OPTIONS: { value: TriggerType; label: string; help: string }[] = [
  {
    value: "TOOL_DENIED",
    label: "A tool call is denied",
    help: "Counts denials in the audit log over a window you choose.",
  },
  {
    value: "SPEND_THRESHOLD",
    label: "Spend reaches a share of the cap",
    help: "Measured against the same cap the budget guard enforces.",
  },
  {
    value: "AGENT_SUSPENDED",
    label: "An agent is suspended",
    help: "Only counts suspensions by a person, never one an automation caused.",
  },
];

const ACTION_OPTIONS: { value: ActionType; label: string; help: string }[] = [
  {
    value: "RAISE_ALERT",
    label: "Raise an alert",
    help: "Records it in the run history below. Nothing is emailed — there is no mail service.",
  },
  {
    value: "SUSPEND_AGENT",
    label: "Suspend the agent",
    help: "Stops the agent immediately, the same as the kill switch. Writes an audit entry.",
  },
];

export function CreateAutomationButton({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [trigger, setTrigger] = useState<TriggerType>("TOOL_DENIED");
  const [action, setAction] = useState<ActionType>("RAISE_ALERT");
  const [count, setCount] = useState(3);
  const [windowMinutes, setWindowMinutes] = useState(60);
  const [percent, setPercent] = useState(80);

  const reset = () => {
    setName("");
    setTrigger("TOOL_DENIED");
    setAction("RAISE_ALERT");
    setCount(3);
    setWindowMinutes(60);
    setPercent(80);
    setError(null);
  };

  const triggerConfig = () => {
    if (trigger === "TOOL_DENIED") {
      return { count, window_minutes: windowMinutes, cooldown_minutes: 10 };
    }
    if (trigger === "SPEND_THRESHOLD") {
      return { percent_of_cap: percent, cooldown_minutes: 10 };
    }
    return { cooldown_minutes: 10 };
  };

  const sentence = () => {
    const when =
      trigger === "TOOL_DENIED"
        ? `${count} denied tool call${count === 1 ? "" : "s"} within ${windowMinutes} minutes`
        : trigger === "SPEND_THRESHOLD"
          ? `spend reaches ${percent}% of the agent's cap`
          : "an agent is suspended by a person";
    const then = action === "SUSPEND_AGENT" ? "suspend the agent" : "raise an alert";
    return `When ${when}, ${then}.`;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (saving) return;

    setSaving(true);
    setError(null);
    try {
      await fetchApi("/automations/", {
        method: "POST",
        body: JSON.stringify({
          name,
          description: sentence(),
          enabled: true,
          trigger_type: trigger,
          trigger_config: triggerConfig(),
          action_type: action,
          action_config: {},
        }),
      });
      setOpen(false);
      reset();
      onCreated();
    } catch (err: any) {
      setError(err.message || "Could not create the automation");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger className="gv-card inline-flex h-9 items-center justify-center gap-2 whitespace-nowrap rounded-xl border-2 border-border bg-gv-teal px-3.5 text-[13px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px">
        <Plus className="h-4 w-4" strokeWidth={2.6} />
        New rule
      </DialogTrigger>

      <DialogContent className="gv-panel max-h-[85vh] overflow-y-auto rounded-lg border-2 border-border bg-card text-foreground sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle className="font-display text-[22px] leading-none">New rule</DialogTitle>
          <DialogDescription className="text-[13px] font-bold text-gv-muted">
            Pick something the platform already records, and what should happen when it does.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="automation-name" className={LABEL}>
              Name
            </Label>
            <Input
              id="automation-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Suspend repeat offenders"
              className={FIELD}
              maxLength={120}
              required
            />
          </div>

          <fieldset className="space-y-2">
            <legend className={`${LABEL} mb-2`}>When this happens</legend>
            {TRIGGER_OPTIONS.map((option) => (
              <label
                key={option.value}
                htmlFor={`trigger-${option.value}`}
                className={`flex gap-3 rounded-xl border-2 p-3 cursor-pointer transition-colors ${
                  trigger === option.value
                    ? "border-gv-teal bg-gv-teal/10"
                    : "border-border hover:bg-gv-row-sel"
                }`}
              >
                <input
                  type="radio"
                  id={`trigger-${option.value}`}
                  name="trigger"
                  checked={trigger === option.value}
                  onChange={() => setTrigger(option.value)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-gv-teal"
                />
                <span className="min-w-0">
                  <span className="block text-[13px] font-extrabold text-foreground">
                    {option.label}
                  </span>
                  <span className="block text-[12px] font-semibold text-gv-muted">
                    {option.help}
                  </span>
                </span>
              </label>
            ))}
          </fieldset>

          {trigger === "TOOL_DENIED" && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="rule-count" className={LABEL}>
                  Denials
                </Label>
                <Input
                  id="rule-count"
                  type="number"
                  min={1}
                  max={100}
                  value={count}
                  onChange={(e) => setCount(Number(e.target.value))}
                  className={FIELD}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rule-window" className={LABEL}>
                  Within (minutes)
                </Label>
                <Input
                  id="rule-window"
                  type="number"
                  min={1}
                  max={1440}
                  value={windowMinutes}
                  onChange={(e) => setWindowMinutes(Number(e.target.value))}
                  className={FIELD}
                />
              </div>
            </div>
          )}

          {trigger === "SPEND_THRESHOLD" && (
            <div className="space-y-2">
              <Label htmlFor="rule-percent" className={LABEL}>
                Percent of cap
              </Label>
              <Input
                id="rule-percent"
                type="number"
                min={1}
                max={1000}
                value={percent}
                onChange={(e) => setPercent(Number(e.target.value))}
                className={FIELD}
              />
            </div>
          )}

          <fieldset className="space-y-2">
            <legend className={`${LABEL} mb-2`}>Do this</legend>
            {ACTION_OPTIONS.map((option) => (
              <label
                key={option.value}
                htmlFor={`action-${option.value}`}
                className={`flex gap-3 rounded-xl border-2 p-3 cursor-pointer transition-colors ${
                  action === option.value
                    ? "border-gv-teal bg-gv-teal/10"
                    : "border-border hover:bg-gv-row-sel"
                }`}
              >
                <input
                  type="radio"
                  id={`action-${option.value}`}
                  name="action"
                  checked={action === option.value}
                  onChange={() => setAction(option.value)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-gv-teal"
                />
                <span className="min-w-0">
                  <span className="block text-[13px] font-extrabold text-foreground">
                    {option.label}
                  </span>
                  <span className="block text-[12px] font-semibold text-gv-muted">
                    {option.help}
                  </span>
                </span>
              </label>
            ))}
          </fieldset>

          {/* The rule read back, built from what the form will actually post. */}
          <p className="rounded-xl border-2 border-border bg-gv-head p-3 text-[13px] font-extrabold text-foreground">
            {sentence()}
          </p>

          {action === "SUSPEND_AGENT" && (
            <p className="flex items-start gap-2 rounded-xl border-2 border-gv-held bg-gv-held/10 p-3 text-[12.5px] font-bold text-gv-held-fg">
              <OctagonX className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2.6} aria-hidden="true" />
              This rule can stop an agent on its own. It will not fire again for the same agent
              for ten minutes, and every decision is recorded.
            </p>
          )}

          {error && (
            <p role="alert" className="text-[13px] font-extrabold text-gv-held">
              {error}
            </p>
          )}

          <DialogFooter>
            <button
              type="submit"
              disabled={saving}
              className="gv-card inline-flex h-10 items-center gap-2 rounded-xl border-2 border-border bg-gv-teal px-[17px] text-[13.5px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px disabled:opacity-60"
            >
              <Plus className="h-4 w-4" strokeWidth={2.6} />
              {saving ? "Creating…" : "Create rule"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
