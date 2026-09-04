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

export function CreateAgentButton() {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [skills, setSkills] = useState<Skill[]>([])
  const [skillsLoading, setSkillsLoading] = useState(false)
  const [skillsError, setSkillsError] = useState<string | null>(null)
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])

  const [formData, setFormData] = useState({ name: "", description: "" })

  // Load the registry the first time the dialog is opened, not on every page view.
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
      <DialogTrigger className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-blue-600 text-white hover:bg-blue-700 h-9 px-4 py-2 border-0">
        <Plus className="h-4 w-4" />
        Create Agent
      </DialogTrigger>
      <DialogContent className="sm:max-w-[520px] bg-background border-border text-foreground shadow-xl shadow-black/10 dark:shadow-black/50">
        <DialogHeader>
          <DialogTitle>Create New Agent</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Register a new AI agent in GovernAI to begin the compliance process.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-foreground">Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Customer Support Bot"
              className="bg-background border-input focus-visible:ring-ring text-foreground"
              maxLength={120}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description" className="text-foreground">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe what this agent does..."
              className="bg-background border-input focus-visible:ring-ring min-h-[72px] text-foreground"
              maxLength={2000}
              required
            />
          </div>

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-foreground mb-2">
              Skills <span className="text-muted-foreground font-normal">— these decide what it may touch</span>
            </legend>

            {skillsLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-3">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Loading skills…
              </div>
            )}

            {skillsError && (
              <div role="alert" className="flex items-start gap-2 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm">
                <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" aria-hidden="true" />
                <span className="text-red-500">{skillsError}</span>
              </div>
            )}

            {!skillsLoading && !skillsError && skills.length === 0 && (
              <p className="text-sm text-muted-foreground py-3">
                No skills are registered, so no agent can be created yet.
              </p>
            )}

            <div className="space-y-2 max-h-[190px] overflow-y-auto pr-1">
              {skills.map((skill) => {
                const checked = selectedSkills.includes(skill.id)
                return (
                  <label
                    key={skill.id}
                    htmlFor={`skill-${skill.id}`}
                    className={`flex gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                      checked
                        ? "border-blue-500/50 bg-blue-500/5"
                        : "border-border hover:bg-muted/40"
                    }`}
                  >
                    <input
                      type="checkbox"
                      id={`skill-${skill.id}`}
                      checked={checked}
                      onChange={() => toggleSkill(skill.id)}
                      className="mt-0.5 h-4 w-4 shrink-0 accent-blue-600"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">{skill.display_name}</span>
                        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                          {skill.trust_level}
                        </span>
                      </span>
                      <span className="block text-xs text-muted-foreground mt-0.5 line-clamp-2">
                        {skill.description}
                      </span>
                    </span>
                  </label>
                )
              })}
            </div>
          </fieldset>

          {selectedSkills.length > 0 && (
            <div className="rounded-md border border-border bg-muted/30 p-3">
              <div className="flex items-center gap-2 mb-2">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" />
                <span className="text-xs font-medium text-foreground">
                  This agent will be granted {grantedPermissions.length} permission
                  {grantedPermissions.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {grantedPermissions.map((permission) => (
                  <code
                    key={permission}
                    className="rounded bg-background border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground"
                  >
                    {permission}
                  </code>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground mt-2">
                Nothing more. Permissions come only from the skills you pick.
              </p>
            </div>
          )}

          {error && (
            <p role="alert" className="text-sm text-red-500 font-medium">
              {error}
            </p>
          )}

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              className="bg-transparent border-input text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || skillsLoading || selectedSkills.length === 0}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {loading ? "Creating…" : "Create Draft"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
