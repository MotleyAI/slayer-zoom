import { describe, expect, it } from "vitest";
import { charge, glide, Pull, pulledDepth, returnMs, stage, stretch, THRESHOLD, writingMs } from "./pull";

describe("pull to unlock", () => {
  it("unlocks one depth at a time, only past the threshold", () => {
    expect(pulledDepth(1, THRESHOLD - 1, 4)).toBe(1);
    expect(pulledDepth(1, THRESHOLD, 4)).toBe(2);
    expect(pulledDepth(1, THRESHOLD * 3, 4)).toBe(2);
  });

  it("folds a depth when pulled up, and stays within the depths that have arrived", () => {
    expect(pulledDepth(2, -THRESHOLD, 4)).toBe(1);
    expect(pulledDepth(0, -THRESHOLD, 4)).toBe(0);
    expect(pulledDepth(2, THRESHOLD, 2)).toBe(2);
  });

  it("charges with the pull, both ways, capped", () => {
    expect([charge(0), charge(THRESHOLD / 2), charge(THRESHOLD * 2), charge(-THRESHOLD)]).toEqual([0, 0.5, 1, -1]);
  });

  it("opens room that follows the finger, then resists when nothing more can unlock", () => {
    expect(stretch(-50, true)).toBe(0);
    expect(stretch(100, true)).toBeCloseTo(70);
    expect(stretch(100, false)).toBeLessThan(stretch(100, true));
    expect(stretch(400, false) - stretch(300, false)).toBeLessThan(10);
  });

  it("writes a depth in at thinking speed, about nine words a second, within bounds", () => {
    expect([writingMs(5), writingMs(40), writingMs(500)]).toEqual([1500, 4400, 7000]);
  });

  it("grows the brain from the plain number to the deepest analysis", () => {
    expect([stage(0, 5), stage(2, 5), stage(4, 5), stage(0, 1)]).toEqual([0, 0.5, 1, 0]);
  });
});

describe("a pull gesture", () => {
  it("counts the finger's movement and edge scrolling, not the page following the answer", () => {
    const pull = new Pull(300);
    expect(pull.distance(360, 0)).toBe(60);
    pull.scrolled(40);
    expect(pull.distance(360, 0)).toBe(100);
  });

  it("unlocks one depth per pull: spent until the depth settles, then a full pull again", () => {
    const pull = new Pull(300);
    expect(pull.distance(300 + THRESHOLD, 0)).toBe(THRESHOLD);
    pull.spend(0, 1000);
    pull.scrolled(500);
    expect([pull.isSpent(500), pull.distance(700, 500)]).toEqual([true, 0]);
    expect(pull.distance(700, 1000)).toBe(0);
    expect(pull.distance(700 + THRESHOLD - 1, 1100)).toBeLessThan(THRESHOLD);
  });
});


describe("the cushion and the return", () => {
  it("unlocks at most one depth per press, however far the finger keeps going", () => {
    const pull = new Pull(300);
    pull.lock();
    expect([pull.isSpent(1e9), pull.distance(300 + THRESHOLD * 5, 1e9)]).toEqual([true, 0]);
  });

  it("glides back up at a readable pace: longer for more new content, within bounds", () => {
    expect([returnMs(300), returnMs(2000), returnMs(9000)]).toEqual([1200, 2500, 3200]);
  });

  it("eases in and out, from start to end", () => {
    expect([glide(0), glide(0.5), glide(1)]).toEqual([0, 0.5, 1]);
    expect(glide(0.1)).toBeLessThan(0.1);
    expect(glide(0.9)).toBeGreaterThan(0.9);
  });
});
