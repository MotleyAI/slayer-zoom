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
