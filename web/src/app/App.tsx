import { useMemo, useState, type FormEvent } from "react";
import { GranularitySlider, ZoomedAnswer } from "../slider";
import { createAnswerStore, useAnswer } from "../state";
import "./styles.css";

const DEMO_QUESTION = "What is our revenue year to date?";

export function App() {
  const store = useMemo(() => createAnswerStore(), []);
  const state = useAnswer(store);
  const [question, setQuestion] = useState(DEMO_QUESTION);
  const busy = state.status === "loading" || state.status === "streaming";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (question.trim()) void store.ask(question.trim());
  };

  return (
    <main>
      <header>
        <h1>slayer-zoom</h1>
        <p>One question, answered at the granularity you choose.</p>
      </header>
      <form onSubmit={submit} className="ask">
        <input value={question} onChange={(e) => setQuestion(e.target.value)} aria-label="Question" />
        <button type="submit" disabled={busy}>
          {busy ? "Answering…" : "Ask"}
        </button>
      </form>
      {state.status === "error" && <p className="error">{state.error}</p>}
      <GranularitySlider store={store} />
      <ZoomedAnswer store={store} />
    </main>
  );
}
