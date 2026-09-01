import { createClient } from '@/lib/supabase/client'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const supabase = createClient()
  const { data: { session } } = await supabase.auth.getSession()

  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  } else {
    // Fallback for local development when Supabase isn't configured
    headers.set('Authorization', `Bearer dummy-token`)
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    let errorMsg = 'An error occurred while communicating with the server.'
    try {
      const err = await res.json()
      errorMsg = err.detail || errorMsg
    } catch (e) {
      // Ignore JSON parse errors for non-JSON error responses
    }
    throw new Error(errorMsg)
  }

  const payload = await res.json()
  return payload.data // FastAPI returns { data: ... } Envelope
}
