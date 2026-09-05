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
 *
 * `EventSource` reconnects on its own; `fetch` does not, so reconnection is
 * implemented here — see `streamSse`.
 */

export type SseEvent = {
  /** The `event:` field. `"message"` when the server sent none. */
  type: string;
  /** The parsed `data:` payload, or the raw string if it was not JSON. */
  data: any;
};

export type SseHandlers = {
  onEvent: (event: SseEvent) => void;
  /** The connection is open and frames may start arriving. */
  onOpen?: () => void;
  /** Called once when the stream ends and will not be retried. */
  onClose?: () => void;
  /** A drop that is about to be retried. Not a failure yet. */
  onReconnecting?: (attempt: number, delayMs: number) => void;
  /** Terminal: either the failure is not retryable, or the attempts ran out. */
  onError?: (error: Error) => void;
};

export type RetryOptions = {
  /** 0 disables reconnection entirely. */
  maxAttempts?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
};

export type StreamOptions = {
  retry?: RetryOptions;
  /**
   * Whether a stream that ended should be reopened.
   *
   * The transport cannot tell "the server finished with us" from "the network
   * dropped" — both look like the response body ending. Only the caller knows,
   * because only the caller has seen the protocol-level `done` frame. So the
   * decision lives with the caller rather than being guessed here.
   *
   * Defaults to false, which preserves the per-execution stream's behaviour:
   * the server closes that one deliberately once the run is over.
   */
  shouldReconnect?: () => boolean;
};

const DEFAULT_RETRY: Required<RetryOptions> = {
  maxAttempts: 5,
  baseDelayMs: 500,
  maxDelayMs: 10_000,
};

/** An HTTP status the server will keep returning; retrying cannot help. */
class TerminalStreamError extends Error {}

function backoffDelay(attempt: number, retry: Required<RetryOptions>): number {
  const exponential = retry.baseDelayMs * 2 ** (attempt - 1);
  const capped = Math.min(exponential, retry.maxDelayMs);
  // Jitter, so that many console tabs dropped by one server restart do not
  // all reconnect on the same tick and knock it over again.
  return Math.round(capped * (0.5 + Math.random() * 0.5));
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

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

  for (const raw_line of frame.split("\n")) {
    const line = raw_line.replace(/\r$/, ""); // tolerate CRLF from a proxy
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

/** One connection attempt. Returns when the body ends; throws on failure. */
async function openStream(
  endpoint: string,
  handlers: SseHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const { onEvent, onOpen } = handlers;

  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      Authorization: await authHeader(),
      Accept: "text/event-stream",
    },
    signal,
    cache: "no-store",
  });

  if (!response.ok || !response.body) {
    // A 4xx means the request itself is wrong — a missing run, an expired
    // token. Reconnecting would only repeat it, so these do not retry.
    if (response.status >= 400 && response.status < 500) {
      throw new TerminalStreamError(
        response.status === 404
          ? "That run does not exist, or it belongs to another organisation."
          : response.status === 401 || response.status === 403
            ? "You are not signed in, or not allowed to watch this run."
            : `The live stream could not be opened (HTTP ${response.status}).`,
      );
    }
    throw new Error(`The live stream could not be opened (HTTP ${response.status}).`);
  }

  onOpen?.();

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
}

/**
 * Open a stream, deliver frames, and reopen it if it drops.
 *
 * Resolves when the stream is finished for good, or when `signal` aborts;
 * aborting is not an error. Reconnection is **off by default** — see
 * `StreamOptions.shouldReconnect` for why the caller has to decide.
 */
export async function streamSse(
  endpoint: string,
  handlers: SseHandlers,
  signal?: AbortSignal,
  options: StreamOptions = {},
): Promise<void> {
  const retry = { ...DEFAULT_RETRY, ...(options.retry ?? {}) };
  const shouldReconnect = options.shouldReconnect ?? (() => false);
  let attempt = 0;

  while (true) {
    try {
      await openStream(endpoint, handlers, signal);

      // The body ended. Whether that means "finished" or "dropped" is the
      // caller's judgement, not something the transport can see.
      if (!shouldReconnect()) {
        handlers.onClose?.();
        return;
      }
    } catch (err: any) {
      if (err?.name === "AbortError") return; // the caller unmounted
      if (err instanceof TerminalStreamError) {
        handlers.onError?.(err);
        return;
      }
      if (!shouldReconnect()) {
        handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
        return;
      }
    }

    attempt += 1;
    if (attempt > retry.maxAttempts) {
      handlers.onError?.(
        new Error(
          `Lost the live connection and could not get it back after ${retry.maxAttempts} attempts.`,
        ),
      );
      return;
    }

    const delay = backoffDelay(attempt, retry);
    handlers.onReconnecting?.(attempt, delay);

    try {
      await sleep(delay, signal);
    } catch {
      return; // aborted while waiting
    }
  }
}
