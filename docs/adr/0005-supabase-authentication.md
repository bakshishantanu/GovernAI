# ADR 0005: Supabase Authentication Integration

## Context
The GovernAI backend is a FastAPI application that needs to securely identify which user and organization is making an API request. Since we chose Supabase (ADR 0002), we need to validate their JWTs securely in Python without blocking the async event loop.

## Decision
We implemented a custom FastAPI dependency (`get_current_user` in `app/domain/auth/middleware.py`) that uses `PyJWT` to locally decode and cryptographically verify the Supabase JWT signature using the `SUPABASE_JWT_SECRET`.

## Rationale
1. **Stateless Verification:** By verifying the JWT locally using the shared secret (HS256), we avoid making a network request to Supabase for every API call, ensuring latency remains exceptionally low.
2. **App Metadata Extraction:** Supabase allows injecting custom claims into `app_metadata`. We extract `org_id` and `role` directly from the validated token payload, removing the need for a secondary database lookup to determine a user's tenancy.
3. **Local Dev Bypass:** For rapid local development, the dependency accepts a `dummy-token` to automatically mock an Admin user, unblocking frontend and backend development when a local Supabase container isn't running.

## Consequences
- The backend *must* have the correct `SUPABASE_JWT_SECRET` environment variable injected at runtime.
- We rely on Supabase database triggers to correctly populate the `app_metadata.org_id` upon user signup.
