import { PanelView } from "../panels";
import { useAnswer, type AnswerStore } from "../state";

export function GranularitySlider({ store }: { store: AnswerStore }) {
  const state = useAnswer(store);
  const ready = state.levels.length;
  const building = state.status === "loading" || state.status === "streaming";
  const total = state.expectedLevels ?? ready + (building ? 1 : 0);
  const note = state.notes[state.notes.length - 1];
  if (total === 0) return building ? <p className="progress">{note ?? "Starting…"}</p> : null;
  return (
    <div className="slider">
      <input
        aria-label="Granularity"
        type="range"
        min={0}
        max={total - 1}
        step={1}
        value={state.position}
        onChange={(event) => store.slide(Number(event.target.value))}
        style={{ ["--fill" as string]: `${total > 1 ? (state.position / (total - 1)) * 100 : 0}%` }}
      />
      <ol className="ticks" style={{ gridTemplateColumns: `repeat(${total}, 1fr)` }}>
        {Array.from({ length: total }, (_, i) => {
          const level = state.levels[i];
          return (
            <li key={i}>
              <button
                type="button"
                disabled={!level}
                aria-current={i === state.position}
                onClick={() => store.slide(i)}
              >
                {level ? level.title : "…"}
              </button>
            </li>
          );
        })}
      </ol>
      {building && (
        <p className="progress" aria-live="polite">
          {note ?? (state.expectedLevels ? `Building level ${ready + 1} of ${total}…` : "Starting…")}
        </p>
      )}
      {!building && state.summary && <p className="progress">{state.summary}</p>}
    </div>
  );
}

export function ZoomedAnswer({ store }: { store: AnswerStore }) {
  const state = useAnswer(store);
  const level = state.levels[state.position];
  if (!level) return null;
  const before = new Set((state.levels[state.position - 1]?.panels ?? []).map((p) => p.id));
  return (
    <div className="answer" key={level.index}>
      {level.rationale && <p className="rationale">{level.rationale}</p>}
      <div className="panels">
        {level.panels.map((panel) => (
          <PanelView key={panel.id} panel={panel} fresh={state.position > 0 && !before.has(panel.id)} />
        ))}
      </div>
    </div>
  );
}
