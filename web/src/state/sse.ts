export interface SseEvent {
  event: string;
  data: unknown;
}

/** Splits a growing text buffer into complete server-sent events, returning the unparsed tail. */
export function takeEvents(buffer: string): { events: SseEvent[]; rest: string } {
  const blocks = buffer.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events = blocks
    .filter((block) => block.trim() !== "")
    .map((block) => {
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      return { event, data: data ? (JSON.parse(data) as unknown) : null };
    });
  return { events, rest };
}
