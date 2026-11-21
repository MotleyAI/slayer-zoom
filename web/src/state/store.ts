import { useSyncExternalStore } from "react";
import { takeEvents } from "./sse";
import type { Digest, ResolvedLevel, Segment } from "./types";

export type Status = "idle" | "loading" | "streaming" | "done" | "error";

export interface AnswerState {
  question: string;
  status: Status;
  /** How many levels the answer will have, or null while an agent is still deciding. */
  expectedLevels: number | null;
  /** The agent's progress notes, oldest first. */
  notes: string[];
  summary: string;
  levels: ResolvedLevel[];
  /** The answer's text so far, in reading order. */
  narration: Segment[];
  /** One digest per narrated level, in level order. */
  digests: Digest[];
  /** The last level whose text has arrived, or -1 when the answer has no text. */
  narratedThrough: number;
  /** Continuous slider position: 2.4 shows level 2 in full and 40% of level 3's added text. */
  position: number;
  error: string | null;
}

export interface AnswerStore {
  getState(): AnswerState;
  subscribe(listener: () => void): () => void;
  /** Ask a question: the only action that talks to the server. */
  ask(question: string): Promise<void>;
  /** Move the slider. Purely local: the levels are already here. */
  slide(position: number): void;
}

const INITIAL: AnswerState = {
  question: "",
  status: "idle",
  expectedLevels: 0,
  notes: [],
  summary: "",
  levels: [],
  narration: [],
  digests: [],
  narratedThrough: -1,
  position: 0,
  error: null,
};

export function createAnswerStore(fetchImpl: typeof fetch = (...args) => fetch(...args), base = "/api"): AnswerStore {
  let state = INITIAL;
  const listeners = new Set<() => void>();
  const set = (patch: Partial<AnswerState>) => {
    state = { ...state, ...patch };
    listeners.forEach((listener) => listener());
  };

  const handle = (event: string, data: unknown) => {
    if (event === "ladder") {
      set({ status: "streaming", expectedLevels: (data as { levels: number | null }).levels });
    } else if (event === "note") {
      set({ notes: [...state.notes, (data as { text: string }).text] });
    } else if (event === "level") {
      set({ levels: [...state.levels, data as ResolvedLevel] });
    } else if (event === "narration") {
      const { level, segments, digests = [] } = data as { level: number; segments: Segment[]; digests?: Digest[] };
      set({ narration: segments, digests, narratedThrough: Math.max(state.narratedThrough, level) });
    } else if (event === "done") {
      set({ status: "done", summary: (data as { summary?: string }).summary ?? "" });
    } else if (event === "error") {
      set({ status: "error", error: (data as { message: string }).message });
    }
  };

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    async ask(question) {
      set({ ...INITIAL, question, status: "loading" });
      try {
        const response = await fetchImpl(`${base}/answer`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ question }),
        });
        if (!response.ok || !response.body) throw new Error(`The server answered ${response.status}`);
        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          const { events, rest } = takeEvents(buffer + value);
          buffer = rest;
          events.forEach(({ event, data }) => handle(event, data));
        }
        if (state.status === "streaming") set({ status: "done" });
      } catch (error) {
        set({ status: "error", error: error instanceof Error ? error.message : String(error) });
      }
    },
    slide(position) {
      set({ position: Math.min(Math.max(position, 0), lastPosition(state)) });
    },
  };
}

/** The furthest the slider can go: the last level that has its data and, if the answer has text, its text. */
export function lastPosition(state: AnswerState): number {
  const ready = state.narratedThrough < 0 ? state.levels.length : Math.min(state.levels.length, state.narratedThrough + 1);
  return Math.max(ready - 1, 0);
}

export function useAnswer(store: AnswerStore): AnswerState {
  return useSyncExternalStore(store.subscribe, store.getState);
}
