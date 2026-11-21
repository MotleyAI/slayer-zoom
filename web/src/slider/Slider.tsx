import { Fragment, useRef, type ReactNode } from "react";
import { PanelView } from "../panels";
import { lastPosition, useAnswer, type AnswerStore } from "../state";
import { reveal, withFallbacks, type Piece } from "./stretch";

const GLIDE_MS = 450;

export function GranularitySlider({ store }: { store: AnswerStore }) {
  const state = useAnswer(store);
  const frame = useRef(0);
  const ready = state.levels.length;
  const building = state.status === "loading" || state.status === "streaming";
  const total = state.expectedLevels ?? ready + (building ? 1 : 0);
  const note = state.notes[state.notes.length - 1];
  if (total === 0) return building ? <p className="progress">{note ?? "Starting…"}</p> : null;
  const reachable = lastPosition(state);

  /** Clicking a level name glides there, so the text visibly unfolds instead of jumping. */
  const glide = (target: number) => {
    cancelAnimationFrame(frame.current);
    const from = store.getState().position;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min((now - start) / GLIDE_MS, 1);
      store.slide(from + (target - from) * (1 - (1 - t) ** 3));
      if (t < 1) frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
  };

  return (
    <div className="slider">
      <input
        aria-label="Detail"
        type="range"
        min={0}
        max={Math.max(total - 1, 0)}
        step={0.005}
        value={state.position}
        onChange={(event) => {
          cancelAnimationFrame(frame.current);
          store.slide(Number(event.target.value));
        }}
        style={{
          ["--fill" as string]: `${total > 1 ? (state.position / (total - 1)) * 100 : 0}%`,
          ["--reach" as string]: `${total > 1 ? (reachable / (total - 1)) * 100 : 0}%`,
        }}
      />
      <ol className="ticks" style={{ gridTemplateColumns: `repeat(${total}, 1fr)` }}>
        {Array.from({ length: total }, (_, i) => {
          const level = state.levels[i];
          const near = Math.abs(state.position - i) < 0.5;
          return (
            <li key={i}>
              <button type="button" disabled={!level || i > reachable} aria-current={near} onClick={() => glide(i)}>
                {level ? level.title : "…"}
              </button>
            </li>
          );
        })}
      </ol>
      {building && <p className="progress" aria-live="polite">{note ?? "Building the answer…"}</p>}
    </div>
  );
}

/** The answer as one growing text, with each chart right after the sentence that introduces it. */
export function ZoomedAnswer({ store }: { store: AnswerStore }) {
  const state = useAnswer(store);
  if (state.levels.length === 0) return null;
  const segments = withFallbacks(state.narration, state.levels);
  const pieces = reveal(segments, state.levels, state.position);
  const blocks: ReactNode[] = [];
  let paragraph: Piece[] = [];
  const flush = () => {
    if (paragraph.length) blocks.push(<Paragraph key={`p-${paragraph[0].segment.id}`} pieces={paragraph} />);
    paragraph = [];
  };
  for (const piece of pieces) {
    if (piece.shown > 0) paragraph.push(piece);
    if (piece.panel) {
      flush();
      blocks.push(
        <div className="inline-panel" key={`panel-${piece.panel.id}`}>
          <PanelView panel={piece.panel} fresh={false} />
        </div>,
      );
    }
  }
  flush();
  return (
    <article className="answer">
      {blocks}
    </article>
  );
}

function Paragraph({ pieces }: { pieces: Piece[] }) {
  return (
    <p className="stretch">
      {pieces.map((piece) => (
        <Fragment key={piece.segment.id}>
          <span className={`segment level-${piece.segment.level}`}>
            {piece.words.slice(0, piece.shown).map((word, i) => (
              <span className="word" key={i}>
                {word}{" "}
              </span>
            ))}
          </span>
        </Fragment>
      ))}
    </p>
  );
}
