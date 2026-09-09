import { createClient } from '@/lib/supabase/client'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

/** Where the dev-only role switcher stores the acting role. */
export const ROLE_STORAGE_KEY = 'govern_ai_role'

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
 * Which dev token to send when Supabase is not configured.
 *
 * The backend accepts one token per role, so switching role locally is just a
 * matter of which literal we send. The role lives in localStorage because the
 * switcher is a client-only development affordance; it is never the security
 * boundary — every endpoint re-derives the role server-side from the token.
 */
function devToken(): string {
  if (typeof window === 'undefined') return 'dummy-token'
  switch (localStorage.getItem(ROLE_STORAGE_KEY)) {
    case 'agent_builder':
      return 'dummy-token-builder'
    case 'user':
      return 'dummy-token-user'
    default:
      return 'dummy-token'
  }
}

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
  if (!SUPABASE_CONFIGURED) return `Bearer ${devToken()}`

  try {
    const supabase = createClient()
    const {
      data: { session },
    } = await supabase.auth.getSession()
    if (session?.access_token) return `Bearer ${session.access_token}`
  } catch {
    // falls through to the dev fallback below
  }
  return `Bearer ${devToken()}`
}

/** One broken compliance rule, as the backend reports it (FRD-02/FRD-03). */
export type ApiViolation = { rule: string; message: string }

/**
 * A failed request, with the parts of the response a caller can actually act on.
 *
 * `status` matters because callers must distinguish "this does not exist" from
 * "the server could not be reached" — a screen that says "no such request"
 * because the API was briefly down is lying to the person reading it.
 *
 * `violations` carries FastAPI's structured `detail` for the compliance check,
 * which returns every broken rule rather than only the first, so a builder can
 * fix an agent in one pass instead of one attempt per problem.
 */
export class ApiError extends Error {
  readonly status: number
  readonly violations: ApiViolation[]

  constructor(message: string, status: number, violations: ApiViolation[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.violations = violations
  }
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
    let violations: ApiViolation[] = []
    try {
      const err = await res.json()
      const detail = err?.detail
      if (typeof detail === 'string') {
        errorMsg = detail
      } else if (detail && typeof detail === 'object') {
        // A structured refusal: `message` is the sentence meant for a person,
        // so prefer it over stringifying the whole object at them.
        if (typeof detail.message === 'string') errorMsg = detail.message
        if (Array.isArray(detail.violations)) violations = detail.violations
      }
    } catch (_e) {
      // Ignore JSON parse errors for non-JSON error responses
    }
    throw new ApiError(errorMsg, res.status, violations)
  }

  const payload = await res.json()
  return payload && typeof payload === 'object' && 'data' in payload ? payload.data : payload
}
