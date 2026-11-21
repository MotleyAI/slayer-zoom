import type { ResolvedLevel, ResolvedPanel, Segment } from "../state";

/** A visible piece of text: the words shown so far, and the panel it introduces once it is complete. */
export interface Piece {
  segment: Segment;
  words: string[];
  shown: number;
  panel: ResolvedPanel | null;
}

function firstAppearance(levels: ResolvedLevel[]): Map<string, { level: number; panel: ResolvedPanel }> {
  const seen = new Map<string, { level: number; panel: ResolvedPanel }>();
  levels.forEach((level) => level.panels.forEach((panel) => seen.has(panel.id) || seen.set(panel.id, { level: level.index, panel })));
  return seen;
}

/**
 * The text to reveal: the narration, plus a plain segment for any panel the narration never introduces (and, with
 * no narration at all, each level's rationale), so every panel has a place in the text.
 */
export function withFallbacks(segments: Segment[], levels: ResolvedLevel[]): Segment[] {
  const introduced = new Set(segments.map((s) => s.panel).filter(Boolean));
  const result = [...segments];
  const narrated = new Set(segments.map((s) => s.level));
  for (const level of levels) {
    if (!narrated.has(level.index) && level.rationale) {
      result.push({ id: `rationale_${level.index}`, level: level.index, text: level.rationale, panel: null });
    }
  }
  for (const [id, { level, panel }] of firstAppearance(levels)) {
    if (!introduced.has(id)) result.push({ id: `fallback_${id}`, level, text: "", panel: panel.id });
  }
  return result;
}

/**
 * What the reader sees at a slider position. Levels up to floor(position) are shown in full; the next level's
 * words appear in reading order in proportion to the fractional part (all of them just before the next whole
 * position), and each of its panels appears as soon as the segment introducing it is complete.
 */
export function reveal(segments: Segment[], levels: ResolvedLevel[], position: number): Piece[] {
  const base = Math.floor(position);
  const fraction = position - base;
  const panels = firstAppearance(levels);
  const growing = segments.filter((s) => s.level === base + 1);
  const total = growing.reduce((sum, s) => sum + words(s.text).length, 0) + 1;
  let budget = Math.floor(fraction * total + 1e-9);
  const pieces: Piece[] = [];
  for (const segment of segments) {
    if (segment.level > base + 1 || !levels[segment.level]) continue;
    const list = words(segment.text);
    const panel = segment.panel ? (panels.get(segment.panel)?.panel ?? null) : null;
    if (segment.level <= base) {
      pieces.push({ segment, words: list, shown: list.length, panel });
      continue;
    }
    const shown = Math.min(list.length, budget);
    const panelShown = panel !== null && budget > 0 && budget >= list.length;
    budget = Math.max(budget - list.length, 0);
    if (shown > 0 || panelShown) pieces.push({ segment, words: list, shown, panel: panelShown ? panel : null });
  }
  return pieces;
}

function words(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}
