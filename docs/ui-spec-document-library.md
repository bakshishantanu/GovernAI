# UI spec: Document library and RAG chat

Backend for this is merged in `feat/document-upload-rag`. Every endpoint below
exists and works today. This document is the contract; nothing here needs a
backend change to build against.

Base URL is the same one the console already uses (`NEXT_PUBLIC_API_URL`), and
every request needs the usual `Authorization: Bearer <token>` header. Responses
are wrapped in the standard `{ "data": ... }` envelope, so `fetchApi` already
unwraps them.

---

## Part 1: The document library

A page listing the org's documents with an upload control. Suggested route:
`/[role]/documents`, sidebar entry "Documents".

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/documents/` | Upload a file. Returns **202** immediately |
| `GET` | `/documents/` | List the org's documents, newest first |
| `GET` | `/documents/{id}` | One document. This is the polling target |
| `DELETE` | `/documents/{id}` | Delete it and every chunk built from it. Returns **204** |

### Upload

`multipart/form-data`, not JSON.

- `file` (required): the file itself
- `title` (optional): display name

Send it as a `FormData`. Do **not** set `Content-Type` yourself, the browser
must set it so the multipart boundary is included.

```ts
const body = new FormData();
body.append("file", file);
if (title) body.append("title", title);
// Authorization header only. No Content-Type.
```

**Please offer the title field.** It is what every citation displays. Without
it a file called `_10-K-2025-As-Filed.pdf` becomes the title "10 K 2025 As
Filed", where "Apple FY2025 10-K" is what a reader wants to see in an answer.

### Document shape

```ts
type Document = {
  id: string;
  title: string;
  filename: string | null;
  mime_type: string | null;
  status: "PENDING" | "PROCESSING" | "READY" | "FAILED";
  error: string | null;
  page_count: number | null;   // null until READY
  chunk_count: number | null;  // null until READY
  access_scope: string[];
  source: string;              // "upload", or "seed" for the demo documents
  created_at: string | null;
};
```

### Status is the whole design problem

Ingestion is asynchronous and **slow**. The real Apple 10-K took about
135 seconds: 80 pages, 149 chunks, each embedded through a rate-limited API.
The upload request returns in well under a second with `status: "PENDING"`, and
the work happens afterwards.

So the flow is:

1. Upload returns 202 with the document at `PENDING`. Put the row in the list
   straight away.
2. Poll `GET /documents/{id}` every 2 to 3 seconds while status is `PENDING` or
   `PROCESSING`.
3. Stop polling at `READY` or `FAILED`.

Please show a **live elapsed timer or indeterminate progress**, not a spinner
that looks stuck. Two minutes of unexplained spinner reads as a hang. There is
no progress percentage available, so honest indeterminate progress plus
"this can take a couple of minutes for a long document" is the right call.

| Status | Show |
|---|---|
| `PENDING` | "Queued" |
| `PROCESSING` | "Reading and indexing…" with elapsed time |
| `READY` | "{page_count} pages, {chunk_count} sections indexed" |
| `FAILED` | The `error` string, verbatim, in an error style |

**Show `error` verbatim.** It is written to be read by the person who uploaded
the file, and it is the only thing distinguishing a failure from a file still
being processed. The most common one is worth recognising:

> "No text could be extracted. If this is a scanned document, it needs OCR,
> which is not supported yet."

### Upload rejections

A refused upload returns **400** with `detail` as a plain sentence. Show it
directly. Causes: unsupported file type, empty file, over the 25 MB limit, or
document search not configured on the server.

**Only `.pdf` is accepted right now.** Set `accept=".pdf"` on the file input,
and please say so visibly near the control, something like "PDF only for now;
Word, PowerPoint and scanned documents are coming". A user who drags in a
`.docx` gets a 400 saying the same thing, but finding out before the upload is
better.

### Delete

Deletes the document and all its chunks. Irreversible, so confirm first, and
say that answers will stop being able to cite it.

---

## Part 2: The chat

The point of the upload is asking questions and getting answers with
citations you can check.

### Chat runs through an agent, deliberately

**There is no separate chat endpoint, and there should not be one.** Questions
go through the existing agent execution flow, which is what already runs the
Document Search skill:

1. The user needs an agent with the **Document Search** skill, ACTIVE.
2. `POST /executions/` with that `agent_id` and the question as the `goal`.
   Exactly what `run-goal-card.tsx` already does.
3. Stream the run, as `execution-stream.tsx` already does.
4. The final answer contains citations.

Requiring an agent is the governance model, not friction to design around. A
run is what constructs the `PolicyEngine`, `AuditService`, `CostService`,
`BudgetGuard` and kill switch, every one of them keyed on `agent_id` and
`org_id` (see `api/execution_runner.py`). A chat path that skipped the agent
would have no passport and therefore no permission check, would write no audit
entry, would record no cost despite spending real money on the LLM call, and
could not be killed or budget-capped.

It would also have nowhere principled to get `permitted_scopes` from. That
value comes from the agent's skill binding; without an agent it would have to
be hardcoded, which is exactly the "enforced structurally, not by prompt
instruction" property the access-scope demo depends on.

So the first-run experience is a UI problem, not an API one:

- Let the user **pick which Document Search agent** they are talking to. A
  small selector at the top of the chat is enough. Fetch candidates from
  `GET /agents/` and keep the ones bound to `document_search`.
- If they have **no** such agent, do not show an empty chat. Show a short
  explanation plus an inline "Create a Document Search agent" action, so the
  reason for the requirement is visible rather than feeling like a dead end.
- Remember the last agent used, so returning to the page is one click.

### Rendering citations

This is the part that matters most, and the part worth real design effort.

An answer comes back with citations inline, in square brackets:

> To halt a misbehaving agent, click Kill on the dashboard. This sets its
> status to SUSPENDED in a single transaction [Kill Switch Runbook].
> Research and development spending rose year over year
> [Apple FY2025 10-K, p.50].

The format is `[<document title>, p.<page>]`, or `[<document title>]` alone for
a document with no pages (the five seeded demo documents).

Please **parse those out and render them as chips or superscripts** rather than
leaving raw brackets in the prose. Clicking one should at minimum show which
document and page. Matching a citation back to a document is a title lookup
against `GET /documents/`.

A caveat to design around: the citation is produced by the model copying a
string it was given. It is verified server-side, but a model can still write
something that matches no document. **Render an unmatched citation as plain
text rather than a broken chip.** Do not throw.

### The tool result, if you show retrieval detail

When the run streams its tool calls, `search_documents` returns:

```ts
type SearchResult = {
  citation: string;        // "Apple FY2025 10-K, p.50" — what the model cites
  chunk_id: string;        // "<document_id>#<chunk_index>"
  document_id: string;
  document_title: string;
  page_number: number | null;
  text: string;            // the retrieved chunk, ~400 words
  relevance_score: number; // 0..1, higher is closer
};
```

A "sources" panel showing these under the answer would be a genuinely good
addition: it shows the user what the model actually read, which is the whole
governance story. `text` is a paragraph or so, so it wants a collapsed or
scrollable treatment.

---

## What to test against

The Apple FY2025 10-K is already ingested and READY in the database: 80 pages,
149 chunks. Questions that retrieve well:

- "How much did the company spend on research and development?" → p.50
- "What are the main risks to the business?" → pp.11, 13, 15

And one that deliberately returns nothing, which is worth designing an empty
state for: "Who is the chief executive officer?" falls below the relevance
floor and the agent should say it cannot find the answer.

---

## Questions for me

- Should uploads be per-user visible, or org-wide as they are now? Currently
  any document uploaded in an org is listed to, and searchable by, everyone in
  that org.
- Should the upload form let the user choose an access scope? It is currently
  fixed to `public`, because that is the only scope the Document Search skill
  is registered with, and offering a scope the skill cannot read would produce
  documents that are silently unsearchable.
