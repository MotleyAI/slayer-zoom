import "@openuidev/react-ui/styles/openui-defaults.css";
import "@openuidev/react-ui/styles/shared.css";
import "@openuidev/react-ui/styles/card.css";
import "@openuidev/react-ui/styles/table.css";
import "@openuidev/react-ui/styles/metricIndicator.css";
import "@openuidev/react-ui/styles/charts.css";
import "@openuidev/react-ui/styles/tooltipWrapper.css";
import { Card } from "@openuidev/react-ui/parts/Card/Card";
import { ThemeProvider } from "@openuidev/react-ui/parts/ThemeProvider/ThemeProvider";
import { useSystemThemeMode } from "@openuidev/react-ui/parts/ThemeProvider/useSystemThemeMode";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { PanelView } from "../panels";
import { lastPosition, useAnswer, type AnswerStore, type Digest, type Segment } from "../state";
import { Brain } from "./Brain";
import { depthStarts, outlineOf, type OutlineEntry } from "./digest";
import { charge, glide, Pull, pulledDepth, returnMs, stage, stretch, THINK_MS, writingMs } from "./pull";
import { reveal, withFallbacks, type Piece } from "./stretch";

const FOLD_MS = 280;
const SETTLE_MS = 300;
const EDGE = 56;
const SCROLL_STEP = 8;
const TOP_GAP = 16;
const BOTTOM_GAP = 24;
const PAUSE_MS = 900;
const FRESH_MS = 4000;

function wordsBetween(segments: Segment[], from: number, to: number): number {
  return segments
    .filter((s) => s.level > from && s.level <= to)
    .reduce((sum, s) => sum + s.text.split(/\s+/).filter(Boolean).length, 0);
}

/**
 * The answer at a depth the reader unlocks. It always shows its current depth in full. Pulling the handle down opens
 * room while the brain charges; past the threshold the next depth writes itself into the text and its charts unfold.
 * Pulling up folds a depth away. Near the bottom of the window the page scrolls, so the pull can go on.
 */
export function ResizableAnswer({ store }: { store: AnswerStore }) {
  const state = useAnswer(store);
  const mode = useSystemThemeMode();
  const reachable = lastPosition(state);
  const segments = useMemo(() => withFallbacks(state.narration, state.levels), [state.narration, state.levels]);
  const [depth, setDepth] = useState(0);
  const [pull, setPull] = useState(0);
  const depthRef = useRef(0);
  const reachRef = useRef(reachable);
  const drag = useRef<{ pull: Pull; clientY: number } | null>(null);
  const writing = useRef(0);
  const scrolling = useRef(0);
  const handle = useRef<HTMLDivElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const article = useRef<HTMLElement>(null);
  const [fresh, setFresh] = useState<number | null>(null);
  const freshTimer = useRef(0);
  // After an unlock the page tours the new depth: it follows the section down as it writes, pauses at its end, then
  // glides back up to the start of the answer. Any scrolling of the reader's own ends the tour.
  const tour = useRef<{ phase: "follow" | "pause" | "return" | null; timer: number; frame: number }>({
    phase: null,
    timer: 0,
    frame: 0,
  });
  reachRef.current = reachable;

  const endTour = () => {
    window.clearTimeout(tour.current.timer);
    cancelAnimationFrame(tour.current.frame);
    if (tour.current.phase === null) return;
    tour.current.phase = null;
    window.clearTimeout(freshTimer.current);
    freshTimer.current = window.setTimeout(() => setFresh(null), FRESH_MS);
  };
  const returnToTop = () => {
    tour.current.phase = "return";
    const from = window.scrollY;
    const to = Math.max(0, from + (card.current?.getBoundingClientRect().top ?? 0) - TOP_GAP);
    if (to >= from) return endTour();
    const ms = returnMs(from - to);
    const start = performance.now();
    const step = (now: number) => {
      if (tour.current.phase !== "return") return;
      const t = Math.min((now - start) / ms, 1);
      window.scrollTo(0, from + (to - from) * glide(t));
      if (t < 1) tour.current.frame = requestAnimationFrame(step);
      else endTour();
    };
    tour.current.frame = requestAnimationFrame(step);
  };

  const go = (next: number) => {
    const from = depthRef.current;
    depthRef.current = next;
    setDepth(next);
    endTour();
    if (next <= from) return;
    tour.current.phase = "follow";
    window.clearTimeout(freshTimer.current);
    setFresh(next);
  };

  // While the new section writes itself in, and through the pause at its end, keep the handle on screen.
  useEffect(() => {
    const el = article.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      const phase = tour.current.phase;
      const box = handle.current?.getBoundingClientRect();
      if (!box || (phase !== "follow" && phase !== "pause")) return;
      const over = box.bottom + BOTTOM_GAP - window.innerHeight;
      if (over > 0) window.scrollBy(0, over);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [state.levels.length > 0]);

  // The reader's own scrolling ends the tour: never fight them for the page.
  useEffect(() => {
    const stop = () => {
      if (tour.current.phase !== null) endTour();
    };
    const keys = (event: globalThis.KeyboardEvent) => {
      // Keys on the handle unlock depths; they start a tour rather than end one.
      if (event.target === handle.current) return;
      if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(event.key)) stop();
    };
    window.addEventListener("wheel", stop, { passive: true });
    window.addEventListener("touchmove", stop, { passive: true });
    window.addEventListener("keydown", keys);
    return () => {
      window.removeEventListener("wheel", stop);
      window.removeEventListener("touchmove", stop);
      window.removeEventListener("keydown", keys);
    };
  }, []);

  // A new question starts again at the single number.
  useEffect(() => go(0), [state.question]);

  // Write the unlocked depth in word by word, or fold it away.
  useEffect(() => {
    const from = store.getState().position;
    const to = Math.min(depth, reachable);
    if (from === to) return;
    const grows = to > from;
    const ms = grows ? writingMs(wordsBetween(segments, Math.floor(from), to)) : FOLD_MS;
    // A new depth (not text arriving mid-write) waits a beat before its first word.
    const start = performance.now() + (grows && from === Math.floor(from) ? THINK_MS : 0);
    const step = (now: number) => {
      const t = Math.max(0, Math.min((now - start) / ms, 1));
      store.slide(from + (to - from) * (grows ? t : 1 - (1 - t) ** 2));
      if (t < 1) writing.current = requestAnimationFrame(step);
      else if (grows && tour.current.phase === "follow") {
        // Linger at the end of the new section, then glide back up so the reader sees how much was added.
        tour.current.phase = "pause";
        tour.current.timer = window.setTimeout(returnToTop, PAUSE_MS);
      }
    };
    cancelAnimationFrame(writing.current);
    writing.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(writing.current);
  }, [depth, reachable, segments, store]);

  const track = () => {
    const current = drag.current;
    if (!current) return;
    const now = performance.now();
    const dy = current.pull.distance(current.clientY, now);
    const from = depthRef.current;
    const next = pulledDepth(from, dy, reachRef.current);
    if (next !== from) {
      go(next);
      // A hard cushion: a press unlocks one depth at most; the next takes a new, deliberate pull. A fold waits
      // until it has settled.
      if (next > from) current.pull.lock();
      else current.pull.spend(now, FOLD_MS + SETTLE_MS);
      setPull(0);
    } else {
      setPull(dy);
    }
  };
  // While the finger rests near the window's edge in the direction of the pull, scroll the page so the pull can go
  // on. Only this scrolling counts toward the pull; the page following an unfolding depth does not.
  const edgeScroll = () => {
    const current = drag.current;
    if (!current) return;
    const now = performance.now();
    if (!current.pull.isSpent(now)) {
      const dy = current.pull.distance(current.clientY, now);
      const step =
        current.clientY > window.innerHeight - EDGE && dy > 0 ? SCROLL_STEP : current.clientY < EDGE && dy < 0 ? -SCROLL_STEP : 0;
      if (step) {
        const before = window.scrollY;
        window.scrollBy(0, step);
        current.pull.scrolled(window.scrollY - before);
      }
    }
    track();
    scrolling.current = requestAnimationFrame(edgeScroll);
  };
  const release = () => {
    drag.current = null;
    cancelAnimationFrame(scrolling.current);
    setPull(0);
  };
  const onKey = (event: KeyboardEvent) => {
    const moves: Record<string, number> = {
      ArrowDown: depthRef.current + 1,
      PageDown: depthRef.current + 1,
      ArrowUp: depthRef.current - 1,
      PageUp: depthRef.current - 1,
      Home: 0,
      End: reachRef.current,
    };
    const target = moves[event.key];
    if (target === undefined) return;
    event.preventDefault();
    go(Math.max(0, Math.min(target, reachRef.current)));
  };

  const building = state.status === "loading" || state.status === "streaming";
  const total = Math.max(state.expectedLevels ?? state.levels.length + (building ? 1 : 0), state.levels.length);
  const note = state.notes[state.notes.length - 1];
  if (state.levels.length === 0) return building ? <p className="progress">{note ?? "Starting…"}</p> : null;

  const shown = Math.min(depth, reachable);
  const current = state.levels[shown];
  const next = state.levels[shown + 1];
  const canUnlock = shown < reachable;
  const room = stretch(pull, canUnlock);
  const label = `Depth ${shown + 1} of ${total}: ${current?.title ?? ""}`;
  const invite = canUnlock
    ? `${charge(pull) > 0.85 ? "Almost there: keep pulling" : "Pull"} to unlock ${next?.title ?? "the next depth"}`
    : shown + 1 < total
      ? (note ?? "Thinking deeper…")
      : "That is the deepest analysis";

  return (
    <ThemeProvider mode={mode}>
      <Card variant="card" width="full" className="answer-card" ref={card}>
        <Outline
          entries={outlineOf(total, state.levels, state.digests, shown, reachable)}
          onPick={(index) => go(Math.max(0, Math.min(index, reachRef.current)))}
        />
        <article className="answer" ref={article}>{blocks(reveal(segments, state.levels, state.position), state.digests, fresh)}</article>
        <div className="pull-room" style={{ height: room }} aria-hidden>
          {room > 24 && <span>{invite}</span>}
        </div>
        <div
          ref={handle}
          className="pull-handle"
          role="slider"
          tabIndex={0}
          title={`${label}. ${invite}.`}
          aria-label="Depth of the answer: pull down to unlock more"
          aria-valuemin={1}
          aria-valuemax={total}
          aria-valuenow={shown + 1}
          aria-valuetext={label}
          data-pulling={pull !== 0 || undefined}
          onKeyDown={onKey}
          onPointerDown={(event) => {
            // No pulling while the page tours a depth that just unlocked.
            if (tour.current.phase !== null) return;
            if (event.currentTarget.hasPointerCapture?.(event.pointerId) === false) {
              try {
                event.currentTarget.setPointerCapture(event.pointerId);
              } catch {
                // A synthetic or already-released pointer: the pull still works while it stays on the handle.
              }
            }
            drag.current = { pull: new Pull(event.clientY), clientY: event.clientY };
            cancelAnimationFrame(scrolling.current);
            scrolling.current = requestAnimationFrame(edgeScroll);
          }}
          onPointerMove={(event) => {
            if (!drag.current) return;
            drag.current.clientY = event.clientY;
            track();
          }}
          onPointerUp={release}
          onPointerCancel={release}
        >
          <Brain stage={stage(shown, total)} charge={charge(pull)} depth={shown} />
          {shown === 0 && canUnlock && pull === 0 && <span className="hint">Pull down to think deeper</span>}
        </div>
        {building && shown === reachable && pull === 0 && (
          <p className="progress" aria-live="polite">
            {note ?? "Thinking deeper…"}
          </p>
        )}
      </Card>
    </ThemeProvider>
  );
}

/** The analysis at a glance: every depth, with what each unlocked one found and what is still to come. */
function Outline({ entries, onPick }: { entries: OutlineEntry[]; onPick: (index: number) => void }) {
  return (
    <nav className="overview" aria-label="Depths of the analysis">
      <ol className="outline">
        {entries.map((entry) => (
          <li key={entry.index} data-state={entry.state}>
            <button type="button" disabled={!entry.reachable} onClick={() => onPick(entry.index)}>
              <span className="dot" aria-hidden />
              <span className="label">{entry.label}</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** The answer's paragraphs, with each depth's question before its first sentence and each panel after the
 * segment that introduces it. */
function blocks(pieces: Piece[], digests: Digest[], fresh: number | null): ReactNode[] {
  const result: ReactNode[] = [];
  const starts = depthStarts(pieces);
  let paragraph: Piece[] = [];
  const flush = () => {
    if (paragraph.length) {
      result.push(<Paragraph key={`p-${paragraph[0]!.segment.id}`} pieces={paragraph} fresh={fresh} />);
    }
    paragraph = [];
  };
  for (const piece of pieces) {
    const starting = starts.get(piece.segment.id);
    const question = starting === undefined ? undefined : digests.find((d) => d.level === starting)?.question;
    if (question) {
      flush();
      result.push(
        <h4 className={`depth-question${starting === fresh ? " fresh" : ""}`} key={`q-${starting}`}>
          {question}
        </h4>,
      );
    }
    if (piece.shown > 0) paragraph.push(piece);
    if (piece.panel) {
      flush();
      result.push(
        <div className="inline-panel" key={`panel-${piece.panel.id}`}>
          <PanelView panel={piece.panel} />
        </div>,
      );
    }
  }
  flush();
  return result;
}

function Paragraph({ pieces, fresh }: { pieces: Piece[]; fresh: number | null }) {
  return (
    <p className="stretch">
      {pieces.map((piece) => (
        <span
          className={`segment level-${piece.segment.level}${piece.segment.level === fresh ? " fresh" : ""}`}
          key={piece.segment.id}
        >
          {piece.words.slice(0, piece.shown).map((word, i) => (
            <span className="word" key={i}>
              {word}{" "}
            </span>
          ))}
        </span>
      ))}
    </p>
  );
}
