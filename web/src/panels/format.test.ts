import { describe, expect, it } from "vitest";
import type { Column } from "../state";
import { chartValue, seriesName } from "./format";

const column = (format: Column["format"]): Column => ({ key: "orders.revenue", label: "Revenue", role: "measure", format });

describe("chart series", () => {
  it("names a series by its label and unit, never by its field", () => {
    expect([seriesName(column("currency")), seriesName(column("percent")), seriesName(column("number"))]).toEqual([
      "Revenue ($)",
      "Revenue (%)",
      "Revenue",
    ]);
  });

  it("plots shares in percent points and other values as SLayer returned them", () => {
    expect([chartValue(0.254, column("percent")), chartValue(1234.5, column("currency")), chartValue(null, column("number"))]).toEqual([
      25.4, 1234.5, 0,
    ]);
  });
});
