"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
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
import { Plus } from "lucide-react"

/** shared with the login form: 2px ink border, paper field, pink focus ring */
const FIELD =
  "h-11 w-full rounded-xl border-2 border-border bg-gv-row px-3.5 text-[14px] font-bold text-foreground placeholder:font-bold placeholder:text-gv-muted focus-visible:ring-2 focus-visible:ring-gv-pink"

const LABEL =
  "text-[11px] font-extrabold uppercase tracking-[0.08em] text-gv-label"

export function CreateAgentButton() {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const [formData, setFormData] = useState({
    name: "",
    description: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    try {
      await fetchApi("/agents/", {
        method: "POST",
        body: JSON.stringify({
          name: formData.name,
          description: formData.description,
          skills: [] // Empty for now per backend requirements
        })
      })
      setOpen(false)
      setFormData({ name: "", description: "" })
      window.dispatchEvent(new Event('agent-created')) // Refresh the client component list
    } catch (err: any) {
      setError(err.message || "Failed to create agent")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="gv-card inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-xl border-2 border-border bg-gv-teal px-[17px] text-[13.5px] font-extrabold text-gv-ink transition-transform active:translate-x-px active:translate-y-px disabled:pointer-events-none disabled:opacity-60">
        <Plus className="h-4 w-4" strokeWidth={2.6} />
        Create Agent
      </DialogTrigger>
      <DialogContent className="gv-panel sm:max-w-[425px] rounded-lg border-2 border-border bg-card text-foreground">
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
              className={`${FIELD} min-h-[100px] py-2.5`}
              required
            />
          </div>

          {error && (
            <p className="gv-chip rounded-xl border-2 border-border bg-gv-held px-3.5 py-2.5 text-[12.5px] font-extrabold text-gv-held-fg">
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
              disabled={loading}
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
