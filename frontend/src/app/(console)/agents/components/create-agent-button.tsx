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
      <DialogTrigger className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-blue-600 text-white hover:bg-blue-700 h-9 px-4 py-2 border-0">
        <Plus className="h-4 w-4" />
        Create Agent
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] bg-background border-border text-foreground shadow-xl shadow-black/10 dark:shadow-black/50">
        <DialogHeader>
          <DialogTitle>Create New Agent</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Register a new AI agent in GovernAI to begin the compliance process.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-foreground">Name</Label>
            <Input 
              id="name" 
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              placeholder="e.g. Customer Support Bot"
              className="bg-background border-input focus-visible:ring-ring text-foreground"
              required 
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description" className="text-foreground">Description</Label>
            <Textarea 
              id="description" 
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              placeholder="Describe what this agent does..."
              className="bg-background border-input focus-visible:ring-ring min-h-[100px] text-foreground"
              required 
            />
          </div>
          
          {error && <p className="text-sm text-red-500 font-medium">{error}</p>}
          
          <DialogFooter className="pt-4">
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => setOpen(false)}
              className="bg-transparent border-input text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading} className="bg-blue-600 hover:bg-blue-700 text-white">
              {loading ? "Creating..." : "Create Draft"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
