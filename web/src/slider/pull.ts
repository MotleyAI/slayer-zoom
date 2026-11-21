/** How far, in pixels, the reader pulls the handle to unlock the next depth (or, pulling up, to fold one). */
export const THRESHOLD = 120;

/** The room the pull opens under the answer: it follows the finger, then resists when nothing more can unlock. */
export function stretch(dy: number, canUnlock: boolean): number {
  if (dy <= 0) return 0;
  const free = canUnlock ? THRESHOLD : THRESHOLD / 3;
  return dy <= free ? dy * 0.7 : free * 0.7 + Math.sqrt(dy - free) * 3;
}

/** How charged the pull is: 1 unlocks the next depth, -1 folds the current one. */
export function charge(dy: number): number {
  return Math.max(-1, Math.min(1, dy / THRESHOLD));
}

/** The depth a pull lands on: one deeper or shallower once it passes the threshold, within what has arrived. */
export function pulledDepth(depth: number, dy: number, reachable: number): number {
  if (dy >= THRESHOLD && depth < reachable) return depth + 1;
  if (dy <= -THRESHOLD && depth > 0) return depth - 1;
  return depth;
}

/**
 * How long a newly unlocked depth takes to write itself in: about 110 ms a word (nine words a second, close to
 * reading pace), so the text appears at thinking speed; at least 1.5 s, at most 7 s for a very long depth.
 */
export function writingMs(words: number): number {
  return Math.max(1500, Math.min(7000, words * 110));
}

/** A beat before the first word of a new depth, while the brain levels up: the answer seems to think first. */
export const THINK_MS = 600;

/** The brain's stage for a depth: 0 at the plain number, 1 at the deepest analysis. */
export function stage(depth: number, total: number): number {
  return total > 1 ? Math.max(0, Math.min(1, depth / (total - 1))) : 0;
}

/**
 * One pull gesture. Its distance is the finger's own movement plus any page scrolling the reader asked for by
 * holding the finger at the window's edge; the page following a depth as it unfolds does not count. After an unlock
 * the gesture is spent until the new depth has settled, then it rearms from wherever the finger is, so each further
 * depth takes another full pull.
 */
export class Pull {
  private origin: number;
  private edge = 0;
  private spentUntil = 0;
  private rearm = false;

  constructor(clientY: number) {
    this.origin = clientY;
  }

  distance(clientY: number, now: number): number {
    if (now < this.spentUntil) return 0;
    if (this.rearm) {
      this.origin = clientY;
      this.edge = 0;
      this.rearm = false;
    }
    return clientY - this.origin + this.edge;
  }

  /** The reader held the finger at an edge and the page scrolled by `by` pixels: that counts as pulling. */
  scrolled(by: number): void {
    this.edge += by;
  }

  /** A depth was unlocked or folded: ignore the gesture until it settles, then start counting again. */
  spend(now: number, ms: number): void {
    this.spentUntil = now + ms;
    this.rearm = true;
  }

  isSpent(now: number): boolean {
    return now < this.spentUntil;
  }

  /** This press has unlocked its depth: nothing more until the finger lifts and pulls again. */
  lock(): void {
    this.spentUntil = Number.POSITIVE_INFINITY;
  }
}

/**
 * How long the page takes to glide back up to the start of the answer after a new depth: slow enough to see how much
 * was added (about 0.8 px per ms), never a jump and never a long wait.
 */
export function returnMs(distance: number): number {
  return Math.max(1200, Math.min(3200, Math.abs(distance) / 0.8));
}

/** Ease in and out, so the glide starts and lands softly. */
export function glide(t: number): number {
  return t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;
}
