import type { Cell, Column, PanelData } from "../state";

const MONTH = /^(\d{4})-(\d{2})-01T00:00:00$/;

/** Display only: turns a value SLayer computed into text. Never derives a new number. */
export function formatCell(value: Cell, column: Column, { compact = false, signed = false } = {}): string {
  if (value === null) return "–";
  if (typeof value === "number") {
    if (column.format === "percent") {
      return new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1, signDisplay: signed ? "exceptZero" : "auto" }).format(value);
    }
    if (column.format === "currency") {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        notation: compact ? "compact" : "standard",
        maximumFractionDigits: compact ? 2 : Math.abs(value) < 100 ? 2 : 0,
      }).format(value);
    }
    return new Intl.NumberFormat("en-US", { notation: compact ? "compact" : "standard", maximumFractionDigits: 2 }).format(value);
  }
  if (typeof value === "string") {
    const month = MONTH.exec(value);
    if (month) return new Date(Number(month[1]), Number(month[2]) - 1, 1).toLocaleString("en-US", { month: "short", year: "numeric" });
  }
  return String(value);
}

/** Columns worth showing: drops dimensions that hold the same value on every row, like the YTD year bucket. */
export function visibleColumns(data: PanelData): Column[] {
  return data.columns.filter(
    (column) =>
      column.role === "measure" ||
      data.rows.length < 2 ||
      new Set(data.rows.map((row) => row[column.key])).size > 1,
  );
}

export function measures(data: PanelData): Column[] {
  return data.columns.filter((column) => column.role === "measure");
}

export function labelOf(row: Record<string, Cell>, dimensions: Column[]): string {
  return dimensions.map((column) => formatCell(row[column.key] ?? null, column)).join(" · ");
}
