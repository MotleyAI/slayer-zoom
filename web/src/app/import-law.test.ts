/// <reference types="vite/client" />
import { describe, expect, it } from "vitest";

const OWNERS = ["panels", "slider"];
const sources = import.meta.glob<string>(["../**/*.ts", "../**/*.tsx", "!../**/*.test.ts"], {
  query: "?raw",
  import: "default",
  eager: true,
});
const OPENUI = /(?:from\s+|import\s+)["']@openuidev\//;
const element = (path: string) => path.replace(/^\.\.\//, "").split("/")[0] ?? "";

describe("import law", () => {
  it("lets only the panels and the resizable answer import OpenUI", () => {
    const offenders = Object.entries(sources)
      .filter(([path, text]) => OPENUI.test(text) && !OWNERS.includes(element(path)))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });

  it("sees the OpenUI imports it guards", () => {
    const importers = Object.entries(sources).filter(([, text]) => OPENUI.test(text)).map(([path]) => element(path));
    expect(new Set(importers)).toEqual(new Set(OWNERS));
  });
});
