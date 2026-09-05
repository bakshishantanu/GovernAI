"use client"

import { useState, useEffect, useMemo } from "react"
import { fetchApi } from "@/lib/api-client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Plus, ShieldCheck, AlertCircle, Loader2 } from "lucide-react"

interface Skill {
  id: string
  name: string
  display_name: string
  description: string
  version: string
  trust_level: "VERIFIED" | "COMMUNITY" | "EXPERIMENTAL"
  required_permissions: string[]
}

/** shared with the login form: 2px ink border, paper field, pink focus ring */
const FIELD =
  "h-11 w-full rounded-xl border-2 border-border bg-gv-row px-3.5 text-[14px] font-bold text-foreground placeholder:font-bold placeholder:text-gv-muted focus-visible:ring-2 focus-visible:ring-gv-pink"

const LABEL =
  "text-[11px] font-extrabold uppercase tracking-[0.08em] text-gv-label"

export function CreateAgentButton() {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [skills, setSkills] = useState<Skill[]>([])
  const [skillsLoading, setSkillsLoading] = useState(false)
  const [skillsError, setSkillsError] = useState<string | null>(null)
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])

  const [formData, setFormData] = useState({ name: "", description: "" })

  // Load the skill registry the first time the dialog is opened, not on every page view.
  useEffect(() => {
    if (!open || skills.length > 0) return

    let cancelled = false
    const loadSkills = async () => {
      setSkillsLoading(true)
      setSkillsError(null)
      try {
        const data = await fetchApi("/skills/")
        if (!cancelled) setSkills(Array.isArray(data) ? data : [])
      } catch (err: any) {
        if (!cancelled) setSkillsError(err.message || "Could not load skills")
      } finally {
        if (!cancelled) setSkillsLoading(false)
      }
    }

    loadSkills()
    return () => {
      cancelled = true
    }
  }, [open, skills.length])

  const toggleSkill = (skillId: string) => {
    setSelectedSkills((current) =>
      current.includes(skillId)
        ? current.filter((id) => id !== skillId)
        : [...current, skillId],
    )
  }

  // An agent's permissions are exactly the union of its skills' permissions —
  // showing that here is the clearest place to teach the rule.
  const grantedPermissions = useMemo(() => {
    const union = new Set<string>()
    for (const skill of skills) {
      if (selectedSkills.includes(skill.id)) {
        for (const permission of skill.required_permissions) union.add(permission)
      }
    }
    return Array.from(union).sort()
  }, [skills, selectedSkills])

  const resetForm = () => {
    setFormData({ name: "", description: "" })
    setSelectedSkills([])
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // The compliance check rejects an agent with no skills, so catch it here
    // rather than letting the user create something permanently stuck in DRAFT.
    if (selectedSkills.length === 0) {
      setError("Pick at least one skill. An agent with no skills cannot pass its compliance check.")
      return
    }

    setLoading(true)
    setError(null)

    try {
      await fetchApi("/agents/", {
        method: "POST",
        body: JSON.stringify({
          name: formData.name,
          description: formData.description,
          skills: selectedSkills,
        }),
      })
      setOpen(false)
      resetForm()
      window.dispatchEvent(new Event("agent-created"))
    } catch (err: any) {
      setError(err.message || "Failed to create agent")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) resetForm()
      }}
    >
      <DialogTrigger className="gv-card inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-xl border-2 border-border bg-gv-teal px-[17px] text-[13.5px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px disabled:pointer-events-none disabled:opacity-60">
        <Plus className="h-4 w-4" strokeWidth={2.6} />
        Create Agent
      </DialogTrigger>
      <DialogContent className="gv-panel sm:max-w-[520px] rounded-lg border-2 border-border bg-card text-foreground">
        <DialogHeader>
          <DialogTitle className="font-display text-[22px] leading-none">Create agent</DialogTitle>
          <DialogDescription className="text-[13px] font-bold text-gv-muted">
            It starts as a draft. Nothing runs until its passport is approved.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-1.5">
            <Label htmlFor="name" className={LABEL}>Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              placeholder="e.g. Customer Support Bot"
              className={FIELD}
              maxLength={120}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="description" className={LABEL}>Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              placeholder="Describe what this agent does..."
              className={`${FIELD} min-h-[80px] py-2.5`}
              maxLength={2000}
              required
            />
          </div>

          {/* ── Skill picker ── */}
          <fieldset className="space-y-2">
            <legend className={`${LABEL} mb-2`}>
              Skills{" "}
              <span className="normal-case tracking-normal font-bold text-gv-muted">
                — these decide what it may touch
              </span>
            </legend>

            {skillsLoading && (
              <div className="flex items-center gap-2 text-[13px] font-bold text-gv-muted py-3">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Loading skills…
              </div>
            )}

            {skillsError && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-xl border-2 border-gv-held bg-gv-held/10 p-3 text-[13px] font-bold"
              >
                <AlertCircle className="h-4 w-4 text-gv-held-fg mt-0.5 shrink-0" aria-hidden="true" />
                <span className="text-gv-held-fg">{skillsError}</span>
              </div>
            )}

            {!skillsLoading && !skillsError && skills.length === 0 && (
              <p className="text-[13px] font-bold text-gv-muted py-3">
                No skills are registered, so no agent can be created yet.
              </p>
            )}

            <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
              {skills.map((skill) => {
                const checked = selectedSkills.includes(skill.id)
                return (
                  <label
                    key={skill.id}
                    htmlFor={`skill-${skill.id}`}
                    className={`flex gap-3 rounded-xl border-2 p-3 cursor-pointer transition-colors ${
                      checked
                        ? "border-gv-teal bg-gv-teal/10"
                        : "border-border hover:bg-gv-row-sel"
                    }`}
                  >
                    <input
                      type="checkbox"
                      id={`skill-${skill.id}`}
                      checked={checked}
                      onChange={() => toggleSkill(skill.id)}
                      className="mt-0.5 h-4 w-4 shrink-0 accent-gv-teal"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="text-[13px] font-extrabold text-foreground">
                          {skill.display_name}
                        </span>
                        <span className="text-[10px] font-extrabold uppercase tracking-[0.08em] text-gv-muted">
                          {skill.trust_level}
                        </span>
                      </span>
                      <span className="block text-[12px] font-bold text-gv-muted mt-0.5 line-clamp-2">
                        {skill.description}
                      </span>
                    </span>
                  </label>
                )
              })}
            </div>
          </fieldset>

          {/* ── Granted permissions summary ── */}
          {selectedSkills.length > 0 && (
            <div className="rounded-xl border-2 border-border bg-gv-row p-3">
              <div className="flex items-center gap-2 mb-2">
                <ShieldCheck className="h-3.5 w-3.5 text-gv-cleared-fg" aria-hidden="true" />
                <span className="text-[12px] font-extrabold text-foreground">
                  This agent will be granted {grantedPermissions.length} permission
                  {grantedPermissions.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {grantedPermissions.map((permission) => (
                  <code
                    key={permission}
                    className="rounded-lg border-2 border-border bg-card px-2 py-0.5 text-[11px] font-extrabold text-gv-muted"
                  >
                    {permission}
                  </code>
                ))}
              </div>
              <p className="text-[11px] font-bold text-gv-muted mt-2">
                Nothing more. Permissions come only from the skills you pick.
              </p>
            </div>
          )}

          {error && (
            <p
              role="alert"
              className="gv-chip rounded-xl border-2 border-border bg-gv-held px-3.5 py-2.5 text-[12.5px] font-extrabold text-gv-held-fg"
            >
              {error}
            </p>
          )}

          <DialogFooter className="gap-2 pt-4">
            <Button
              type="button"
              onClick={() => setOpen(false)}
              className="gv-chip h-10 rounded-xl border-2 border-border bg-card px-[15px] text-[13px] font-extrabold text-gv-ink transition-transform hover:bg-gv-row-sel active:translate-x-px active:translate-y-px"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || skillsLoading || selectedSkills.length === 0}
              className="gv-card h-10 rounded-xl border-2 border-border bg-gv-teal px-[17px] text-[13.5px] font-extrabold text-gv-ink transition-transform hover:bg-gv-teal active:translate-x-px active:translate-y-px disabled:opacity-60"
            >
              {loading ? "Creating…" : "Create draft"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
