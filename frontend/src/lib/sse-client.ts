import { createClient } from "@/lib/supabase/client";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * The console's server-sent-events client.
 *
 * Why not the native `EventSource`: it cannot set request headers, and every
 * streaming route on this API sits behind `get_current_user`, which reads a
 * Bearer token. The alternative — passing the token as a query parameter —
 * would put a credential into every access log and proxy trace. So the stream
 * is read from `fetch` instead, which can authenticate properly, and the SSE
 * frames are parsed here.
 *
 * The wire format is the one produced by `backend/app/api/sse.py`:
 *
 *     event: audit.tool.denied\n
 *     data: {"execution_id": "...", "tool": "sql_query"}\n
 *     \n
 *
 * Lines beginning `:` are keep-alive comments and are dropped. Frames are
 * separated by a blank line, so a partial frame is held in the buffer until
 * the rest of it arrives — never parsed early.
 */

export type SseEvent = {
  /** The `event:` field. `"message"` when the server sent none. */
  type: string;
  /** The parsed `data:` payload, or the raw string if it was not JSON. */
  data: any;
};

export type SseHandlers = {
  onEvent: (event: SseEvent) => void;
  /** Called once when the server closes the stream cleanly. */
  onClose?: () => void;
  onError?: (error: Error) => void;
};

async function authHeader(): Promise<string> {
  try {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) return `Bearer ${session.access_token}`;
  } catch {
    // Supabase not configured locally — fall through to the dev token, the
    // same fallback lib/api-client.ts uses.
  }
  return "Bearer dummy-token";
}

/** Split a complete frame into its event name and data payload. */
function parseFrame(frame: string): SseEvent | null {
  let type = "message";
  const dataLines: string[] = [];

  for (const line of frame.split("\n")) {
    if (!line || line.startsWith(":")) continue; // keep-alive comment
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    // One optional space after the colon is part of the format, not the value.
    const value =
      colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "");

    if (field === "event") type = value;
    else if (field === "data") dataLines.push(value);
  }

  if (dataLines.length === 0) return null;

  const raw = dataLines.join("\n");
  try {
    return { type, data: JSON.parse(raw) };
  } catch {
    return { type, data: raw };
  }
}

/**
 * Open a stream and deliver frames until the server closes it or `signal`
 * aborts. Resolves when the stream ends; aborting is not an error.
 */
export async function streamSse(
  endpoint: string,
  { onEvent, onClose, onError }: SseHandlers,
  signal?: AbortSignal,
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        Authorization: await authHeader(),
        Accept: "text/event-stream",
      },
      signal,
      cache: "no-store",
    });

    if (!response.ok || !response.body) {
      throw new Error(
        response.status === 404
          ? "That run does not exist, or it belongs to another organisation."
          : `The live stream could not be opened (HTTP ${response.status}).`,
      );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Frames are separated by a blank line. Anything after the last
      // separator is incomplete and stays in the buffer.
      let split: number;
      while ((split = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, split);
        buffer = buffer.slice(split + 2);
        const parsed = parseFrame(frame);
        if (parsed) onEvent(parsed);
      }
    }

    onClose?.();
  } catch (err: any) {
    // An abort is the caller unmounting, not a failure.
    if (err?.name === "AbortError") return;
    onError?.(err instanceof Error ? err : new Error(String(err)));
  }
}
