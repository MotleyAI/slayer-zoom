import { describe, expect, it } from "vitest";
import type { Digest, ResolvedLevel, Segment } from "../state";
import { depthStarts, outlineOf } from "./digest";
import type { Piece } from "./stretch";

const level = (index: number, title: string): ResolvedLevel => ({ index, title, rationale: "", panels: [] });
const levels = [level(0, "Number"), level(1, "Split"), level(2, "Mix"), level(3, "Trend")];
const digest = (lvl: number, headline: string): Digest => ({ level: lvl, question: `Q${lvl}?`, headline, summary: `S${lvl}.` });
const digests = [digest(0, "$2.03M"), digest(1, "Brooklyn leads"), digest(2, "Beverages")];

describe("outline", () => {
  it("shows what each unlocked depth found, and what is still to come", () => {
    const outline = outlineOf(5, levels, digests, 1, 2).map((e) => `${e.state}:${e.label}:${e.reachable ? "y" : "n"}`);
    expect(outline).toEqual(["done:$2.03M:y", "current:Brooklyn leads:y", "next:Mix:y", "locked:Trend:n", "locked:Thinking…:n"]);
  });

  it("falls back to the level title while a depth has no digest yet", () => {
    expect(outlineOf(2, levels, [], 1, 1).map((e) => e.label)).toEqual(["Number", "Split"]);
  });
});

describe("question headings", () => {
  const piece = (id: string, lvl: number, shown: number): Piece => ({
    segment: { id, level: lvl, text: "a b", panel: null } as Segment,
    words: ["a", "b"],
    shown,
    panel: null,
  });

  it("go before the first visible segment of each deeper depth, in reading order", () => {
    const pieces = [piece("answer", 0, 2), piece("trend", 2, 2), piece("split", 1, 2), piece("mix", 2, 2), piece("next", 3, 0)];
    expect([...depthStarts(pieces)]).toEqual([
      ["trend", 2],
      ["split", 1],
    ]);
  });
});
