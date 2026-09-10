/**
 * Shared SSE wire-format parsing, used by every `fetch` + `ReadableStream`
 * stream client in the console (`fetch` rather than `EventSource`, because
 * EventSource cannot carry the Authorization header these endpoints require
 * — D-024). One place for this so `/executions/{id}/stream` and
 * `/events/stream` cannot drift apart.
 */

export type SseFrame = { event: string; data: unknown };

/** Splits one buffered SSE chunk into complete frames, keeping any partial tail for next time. */
export function extractFrames(buffer: string): { frames: string[]; rest: string } {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  return { frames: parts, rest };
}

/** Parses one complete frame. Returns null for a heartbeat comment or a malformed frame. */
export function parseFrame(frame: string): SseFrame | null {
  if (frame.startsWith(":")) return null; // heartbeat comment
  let event = "message";
  let dataLine = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
  }
  if (!dataLine) return null;
  try {
    return { event, data: JSON.parse(dataLine) };
  } catch {
    return null;
  }
}

/**
 * Reads an SSE response body, calling `onFrame` for every parsed frame until
 * the stream ends or `signal` aborts. Heartbeats and malformed frames are
 * swallowed silently — callers only ever see real events.
 */
export async function readSseBody(
  body: ReadableStream<Uint8Array>,
  onFrame: (frame: SseFrame) => void,
  signal: AbortSignal,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (!signal.aborted) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { frames, rest } = extractFrames(buffer);
    buffer = rest;
    for (const raw of frames) {
      const parsed = parseFrame(raw);
      if (parsed) onFrame(parsed);
    }
  }
}
