import { describe, expect, it, vi } from "vitest";
import { createAnswerStore } from "./store";

const level = (index: number) => ({ index, title: `L${index}`, rationale: "", panels: [] });

function sseResponse(chunks: string[]): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(new TextEncoder().encode(chunk)));
      controller.close();
    },
  });
  return new Response(stream, { headers: { "content-type": "text/event-stream" } });
}

const body = [
  `event: ladder\ndata: {"question":"q","levels":3}\n\n`,
  `event: level\ndata: ${JSON.stringify(level(0))}\n\nevent: le`,
  `vel\ndata: ${JSON.stringify(level(1))}\n\n`,
  `event: level\ndata: ${JSON.stringify(level(2))}\n\nevent: done\ndata: {}\n\n`,
];

describe("answer store", () => {
  it("collects every streamed level, even when events split across chunks", async () => {
    const store = createAnswerStore(vi.fn(async () => sseResponse(body)));
    await store.ask("q");
    expect(store.getState().levels.map((l) => l.index)).toEqual([0, 1, 2]);
    expect(store.getState().status).toBe("done");
  });

  it("slides without calling the server again", async () => {
    const fetchImpl = vi.fn(async () => sseResponse(body));
    const store = createAnswerStore(fetchImpl);
    await store.ask("q");
    for (const position of [2, 0, 1, 2, 1]) store.slide(position);
    expect(store.getState().position).toBe(1);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("keeps the slider within the levels that have arrived", async () => {
    const store = createAnswerStore(vi.fn(async () => sseResponse(body.slice(0, 2))));
    await store.ask("q");
    store.slide(4);
    expect(store.getState().position).toBe(0);
  });

  it("reports server errors", async () => {
    const store = createAnswerStore(vi.fn(async () => sseResponse([`event: error\ndata: {"message":"nope"}\n\n`])));
    await store.ask("q");
    expect(store.getState()).toMatchObject({ status: "error", error: "nope" });
  });
});

describe("answer store with a live agent", () => {
  const live = [
    `event: ladder\ndata: {"question":"q","levels":null}\n\n`,
    `event: note\ndata: {"text":"Reading the context."}\n\n`,
    `event: level\ndata: ${JSON.stringify(level(0))}\n\n`,
    `event: note\ndata: {"text":"Splitting by store."}\n\n`,
    `event: level\ndata: ${JSON.stringify(level(1))}\n\n`,
    `event: done\ndata: {"summary":"Revenue, then by store."}\n\n`,
  ];

  it("keeps the level count open and collects notes until the agent is done", async () => {
    const store = createAnswerStore(vi.fn(async () => sseResponse(live.slice(0, 3))));
    const seen: (number | null)[] = [];
    store.subscribe(() => seen.push(store.getState().expectedLevels));
    await store.ask("q");
    expect(seen).toContain(null);
    expect(store.getState().notes).toEqual(["Reading the context."]);
    expect(store.getState().levels).toHaveLength(1);
  });

  it("ends with the agent's summary", async () => {
    const store = createAnswerStore(vi.fn(async () => sseResponse(live)));
    await store.ask("q");
    expect(store.getState()).toMatchObject({ status: "done", summary: "Revenue, then by store." });
    expect(store.getState().notes).toEqual(["Reading the context.", "Splitting by store."]);
  });
});

describe("answer store with narration", () => {
  const seg = (id: string, lvl: number) => ({ id, level: lvl, text: "Text.", panel: null });
  const narrated = [
    `event: ladder\ndata: {"question":"q","levels":3}\n\n`,
    `event: level\ndata: ${JSON.stringify(level(0))}\n\n`,
    `event: narration\ndata: ${JSON.stringify({ level: 0, segments: [seg("a", 0)] })}\n\n`,
    `event: level\ndata: ${JSON.stringify(level(1))}\n\n`,
    `event: narration\ndata: ${JSON.stringify({ level: 1, segments: [seg("a", 0), seg("b", 1)] })}\n\n`,
    `event: level\ndata: ${JSON.stringify(level(2))}\n\n`,
  ];

  it("keeps the latest text and slides continuously, but not past the last narrated level", async () => {
    const store = createAnswerStore(vi.fn(async () => sseResponse(narrated)));
    await store.ask("q");
    expect(store.getState().narration.map((s) => s.id)).toEqual(["a", "b"]);
    store.slide(0.37);
    expect(store.getState().position).toBeCloseTo(0.37);
    store.slide(2);
    expect(store.getState().position).toBe(1);
  });
});
