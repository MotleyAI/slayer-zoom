import { HorizontalBarChart } from "@openuidev/react-ui/parts/Charts/BarChart/HorizontalBarChart";
import { LineChartCondensed } from "@openuidev/react-ui/parts/Charts/LineChart/LineChartCondensed";
import { MetricIndicatorInline } from "@openuidev/react-ui/parts/MetricIndicator";
import { Table as UiTable, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@openuidev/react-ui/parts/Table/Table";
import { memo } from "react";
import type { Column, PanelData, ResolvedPanel } from "../state";
import { chartValue, formatCell, labelOf, measures, seriesName, visibleColumns } from "./format";

const CHART_HEIGHT = 220;

/** Chart rows: the dimension label as the category, the measure as SLayer returned it, named with its unit. */
function chartRows(data: PanelData, label: (row: PanelData["rows"][number]) => string, measure: Column) {
  const name = seriesName(measure);
  return data.rows.map((row) => ({ category: label(row), [name]: chartValue(row[measure.key] ?? null, measure) }));
}

function Kpi({ data }: { data: PanelData }) {
  const [measure] = measures(data);
  const row = data.rows[0];
  if (!measure || !row) return <p className="empty">No data</p>;
  return <MetricIndicatorInline value={formatCell(row[measure.key] ?? null, measure)} subtext={measure.label} />;
}

function Bars({ data }: { data: PanelData }) {
  const [measure] = measures(data);
  if (!measure) return null;
  const dims = visibleColumns(data).filter((c) => c.role === "dimension");
  const rows = chartRows(data, (row) => labelOf(row, dims), measure);
  return (
    <figure className="chart">
      <HorizontalBarChart data={rows} categoryKey="category" height={rows.length * 60 + 80} />
      <figcaption>
        {data.rows.map((row, i) => (
          <span key={i}>
            {labelOf(row, dims)} <strong>{formatCell(row[measure.key] ?? null, measure, { compact: true })}</strong>
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

function Table({ data, signed = false }: { data: PanelData; signed?: boolean }) {
  const columns = visibleColumns(data);
  return (
    <UiTable>
      <TableHeader>
        <TableRow>
          {columns.map((c) => (
            <TableHead key={c.key} align={c.role === "measure" ? "right" : "left"}>
              {c.label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.rows.map((row, i) => (
          <TableRow key={i}>
            {columns.map((c) => {
              const value = row[c.key] ?? null;
              const tone = signed && c.format === "percent" && typeof value === "number" ? (value < 0 ? "down" : "up") : "";
              return (
                <TableCell key={c.key} align={c.role === "measure" ? "right" : "left"} className={tone}>
                  {formatCell(value, c, { signed })}
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </UiTable>
  );
}

function Line({ data }: { data: PanelData }) {
  const [measure, ...others] = measures(data);
  const [x] = data.columns.filter((c) => c.role === "dimension");
  if (!measure || !x) return null;
  const rows = chartRows(data, (row) => formatCell(row[x.key] ?? null, x), measure);
  const last = data.rows[data.rows.length - 1];
  return (
    <figure className="chart">
      <LineChartCondensed data={rows} categoryKey="category" height={CHART_HEIGHT} showDots />
      {last && others.length > 0 && (
        <figcaption>
          {others.map((c) => (
            <span key={c.key}>
              {c.label}: <strong>{formatCell(last[c.key] ?? null, c)}</strong>
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}

/** One panel, drawn with OpenUI components. Memoized: the answer re-renders on every pixel of a resize. */
export const PanelView = memo(function PanelView({ panel }: { panel: ResolvedPanel }) {
  const body = {
    kpi: <Kpi data={panel.data} />,
    bar: <Bars data={panel.data} />,
    table: <Table data={panel.data} />,
    line: <Line data={panel.data} />,
    delta: <Table data={panel.data} signed />,
  }[panel.kind];
  return (
    <section className={`panel panel-${panel.kind}`}>
      <h3>{panel.title}</h3>
      {body}
    </section>
  );
});
