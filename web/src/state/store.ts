import { useSyncExternalStore } from "react";
import { takeEvents } from "./sse";
import type { ResolvedLevel } from "./types";

export type Status = "idle" | "loading" | "streaming" | "done" | "error";

export interface AnswerState {
  question: string;
  status: Status;
  expectedLevels: number;
  levels: ResolvedLevel[];
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
  levels: [],
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
      set({ status: "streaming", expectedLevels: (data as { levels: number }).levels });
    } else if (event === "level") {
      set({ levels: [...state.levels, data as ResolvedLevel] });
    } else if (event === "done") {
      set({ status: "done" });
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
      const last = Math.max(state.levels.length - 1, 0);
      set({ position: Math.min(Math.max(Math.round(position), 0), last) });
    },
  };
}

export function useAnswer(store: AnswerStore): AnswerState {
  return useSyncExternalStore(store.subscribe, store.getState);
}
