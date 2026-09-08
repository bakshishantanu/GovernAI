import { createClient } from '@/lib/supabase/client'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

/**
 * True only when real Supabase credentials are configured. This repo's
 * local dev runs with neither var set (no .env.local; the dev-token bypass
 * in backend/.env's AUTH_ALLOW_DEV_TOKEN is the intended auth path instead),
 * so createClient() falls back to a placeholder host,
 * "https://dummy.supabase.co", inside src/lib/supabase/client.ts.
 */
const SUPABASE_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
)

/**
 * Bug found and fixed 2026-09-08 while wiring the app shell to the live
 * backend. `supabase.auth.getSession()` against the placeholder host is not
 * simply slow — it is genuinely nondeterministic: confirmed live, sometimes
 * it settles in under a second, sometimes it is still pending 8+ seconds
 * later on an otherwise-identical fresh page load. A timeout race around it
 * was tried first and made the symptom intermittent rather than fixing it —
 * a `Promise.race` only stops *waiting*, it does not stop whatever the SDK
 * is doing to the shared GoTrueClient/localStorage lock underneath, so the
 * next call could still be starved by it. The `session?.access_token`
 * fallback to `dummy-token` was therefore unreachable in practice: sidebar,
 * header, and every future screen built on fetchApi() would randomly hang
 * rather than showing real seeded data.
 *
 * The actual fix is to never call the SDK at all when there is nothing for
 * it to do — with no configured Supabase project, there is no session to
 * fetch, so `SUPABASE_CONFIGURED` short-circuits straight to the intended
 * dev fallback. This is deterministic (no network call, no SDK involved)
 * and changes nothing once real NEXT_PUBLIC_SUPABASE_* values are set.
 */
export async function getAuthHeader(): Promise<string> {
  if (!SUPABASE_CONFIGURED) return 'Bearer dummy-token'

  try {
    const supabase = createClient()
    const {
      data: { session },
    } = await supabase.auth.getSession()
    if (session?.access_token) return `Bearer ${session.access_token}`
  } catch {
    // falls through to the dev fallback below
  }
  return 'Bearer dummy-token'
}

export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  headers.set('Authorization', await getAuthHeader())

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    let errorMsg = 'An error occurred while communicating with the server.'
    try {
      const err = await res.json()
      if (err.detail) {
        errorMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      }
    } catch (e) {
      // Ignore JSON parse errors for non-JSON error responses
    }
    throw new Error(errorMsg)
  }

  const payload = await res.json()
  return payload.data // FastAPI returns { data: ... } Envelope
}
