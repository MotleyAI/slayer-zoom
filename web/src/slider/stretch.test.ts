import { describe, expect, it } from "vitest";
import type { ResolvedLevel, Segment } from "../state";
import { reveal, withFallbacks } from "./stretch";

const panel = (id: string) => ({ id, kind: "kpi" as const, title: id.toUpperCase(), parent: null, data: { columns: [], rows: [] } });
const levels: ResolvedLevel[] = [
  { index: 0, title: "Number", rationale: "The number.", panels: [panel("total")] },
  { index: 1, title: "Split", rationale: "Where it comes from.", panels: [panel("total"), panel("by_store")] },
];
const segments: Segment[] = [
  { id: "answer", level: 0, text: "Revenue is two million.", panel: "total" },
  { id: "stores", level: 1, text: "Brooklyn leads the four stores.", panel: "by_store" },
  { id: "tail", level: 0, text: "That is good.", panel: null },
];
const shown = (position: number) =>
  reveal(segments, levels, position).map((p) => `${p.segment.id}:${p.shown}${p.panel ? `+${p.panel.id}` : ""}`);

describe("stretchtext reveal", () => {
  it("shows whole levels at whole positions", () => {
    expect(shown(0)).toEqual(["answer:4+total", "tail:3"]);
    expect(shown(1)).toEqual(["answer:4+total", "stores:5+by_store", "tail:3"]);
  });

  it("reveals the next level word by word, in place, with its panel once its sentence is complete", () => {
    expect(shown(0.5)).toEqual(["answer:4+total", "stores:3", "tail:3"]);
    expect(shown(0.7)).toEqual(["answer:4+total", "stores:4", "tail:3"]);
    expect(shown(0.84)).toEqual(["answer:4+total", "stores:5+by_store", "tail:3"]);
    expect(shown(0.99)).toEqual(["answer:4+total", "stores:5+by_store", "tail:3"]);
  });

  it("grows monotonically: moving right never hides a word", () => {
    let before = 0;
    for (let p = 0; p <= 1; p += 0.01) {
      const words = reveal(segments, levels, p).reduce((n, piece) => n + piece.shown, 0);
      expect(words).toBeGreaterThanOrEqual(before);
      before = words;
    }
  });

  it("gives every panel a place when the text never introduces it", () => {
    const filled = withFallbacks([], levels);
    expect(filled.map((s) => s.id)).toEqual(["rationale_0", "rationale_1", "fallback_total", "fallback_by_store"]);
    expect(reveal(filled, levels, 1).filter((p) => p.panel).map((p) => p.panel?.id)).toEqual(["total", "by_store"]);
  });
});
