import { PanelView } from "../panels";
import { useAnswer, type AnswerStore } from "../state";

export function GranularitySlider({ store }: { store: AnswerStore }) {
  const state = useAnswer(store);
  const total = Math.max(state.expectedLevels, state.levels.length);
  if (total === 0) return null;
  const ready = state.levels.length;
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
      {ready < total && <p className="progress">Building level {ready + 1} of {total}…</p>}
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
