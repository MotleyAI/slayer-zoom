export type ColumnRole = "dimension" | "measure";
export type ValueFormat = "number" | "currency" | "percent";
export type Cell = string | number | boolean | null;

export interface Column {
  key: string;
  label: string;
  role: ColumnRole;
  format: ValueFormat;
}

export interface PanelData {
  columns: Column[];
  rows: Record<string, Cell>[];
}

export type PanelKind = "kpi" | "bar" | "table" | "line" | "delta";

export interface ResolvedPanel {
  id: string;
  kind: PanelKind;
  title: string;
  parent: string | null;
  data: PanelData;
}

export interface ResolvedLevel {
  index: number;
  title: string;
  rationale: string;
  panels: ResolvedPanel[];
}

/** One piece of the answer's text. Level n's text is every segment with level <= n, in order. */
export interface Segment {
  id: string;
  level: number;
  text: string;
  /** The panel shown right after this segment, if it introduces one. */
  panel: string | null;
}

/** A depth at a glance: the question it answers, its finding in a few words, and the summary of the answer so far. */
export interface Digest {
  level: number;
  question: string;
  headline: string;
  summary: string;
}
