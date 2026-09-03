# ADR 0002: Supabase over Neon for Database and Auth

## Context
GovernAI requires a robust PostgreSQL database to store relational state (Agents, Executions, Passports, Policies) as well as vector embeddings (pgvector) for document context (RAG). Furthermore, the application requires an authentication system capable of providing standard JSON Web Tokens (JWTs) and user management. We evaluated Supabase and Neon as potential providers.

## Decision
We chose **Supabase** over Neon.

## Rationale
While Neon provides excellent serverless PostgreSQL autoscaling, Supabase provides an integrated suite that drastically accelerates development for this MVP:
1. **Integrated Authentication:** Supabase provides out-of-the-box Auth (GoTrue) that natively integrates with PostgreSQL Row Level Security (RLS). This means we don't have to manage a separate identity provider (like Auth0 or Clerk) and write custom sync logic.
2. **pgvector Support:** Supabase supports `pgvector` natively, which is crucial for our Stage B and Stage C RAG requirements.
3. **Server-Sent Events (SSE) / Realtime:** Supabase's Realtime component can act as a fallback or enhancement for streaming state updates to the UI, though we primarily rely on our own EventBus for backend SSE.

## Consequences
- We are tightly coupled to the Supabase Auth ecosystem (JWT format, user metadata).
- We can leverage Supabase's UI for rapid local development and production database management.
