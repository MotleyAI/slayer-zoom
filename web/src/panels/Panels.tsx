import type { PanelData, ResolvedPanel } from "../state";
import { formatCell, labelOf, measures, visibleColumns } from "./format";

function Kpi({ data }: { data: PanelData }) {
  const [measure] = measures(data);
  const row = data.rows[0];
  if (!measure || !row) return <p className="empty">No data</p>;
  return <p className="kpi">{formatCell(row[measure.key] ?? null, measure)}</p>;
}

function Bars({ data }: { data: PanelData }) {
  const [measure] = measures(data);
  if (!measure) return null;
  const dims = visibleColumns(data).filter((c) => c.role === "dimension");
  const values = data.rows.map((row) => (typeof row[measure.key] === "number" ? (row[measure.key] as number) : 0));
  const max = Math.max(...values, 0) || 1;
  return (
    <ul className="bars">
      {data.rows.map((row, i) => (
        <li key={i}>
          <span className="bar-label">{labelOf(row, dims)}</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${((values[i] ?? 0) / max) * 100}%` }} />
          </span>
          <span className="bar-value">{formatCell(row[measure.key] ?? null, measure, { compact: true })}</span>
        </li>
      ))}
    </ul>
  );
}

function Table({ data, signed = false }: { data: PanelData; signed?: boolean }) {
  const columns = visibleColumns(data);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.role}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => {
                const value = row[c.key] ?? null;
                const tone = signed && c.format === "percent" && typeof value === "number" ? (value < 0 ? "down" : "up") : "";
                return (
                  <td key={c.key} className={`${c.role} ${tone}`}>
                    {formatCell(value, c, { signed })}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Line({ data }: { data: PanelData }) {
  const [measure, ...others] = measures(data);
  const [x] = data.columns.filter((c) => c.role === "dimension");
  if (!measure || !x) return null;
  const points = data.rows.map((row) => (typeof row[measure.key] === "number" ? (row[measure.key] as number) : 0));
  const max = Math.max(...points, 0) || 1;
  const width = 600;
  const height = 160;
  const step = points.length > 1 ? width / (points.length - 1) : 0;
  const path = points.map((v, i) => `${i === 0 ? "M" : "L"}${(i * step).toFixed(1)},${(height - (v / max) * height).toFixed(1)}`).join(" ");
  const last = data.rows[data.rows.length - 1];
  return (
    <figure className="line">
      <svg viewBox={`-4 -8 ${width + 8} ${height + 16}`} role="img" aria-label={`${measure.label} by ${x.label}`}>
        <path d={path} />
        {points.map((v, i) => (
          <circle key={i} cx={i * step} cy={height - (v / max) * height} r={3.5}>
            <title>{`${formatCell(data.rows[i]?.[x.key] ?? null, x)}: ${formatCell(v, measure)}`}</title>
          </circle>
        ))}
      </svg>
      <figcaption>
        <span>{formatCell(data.rows[0]?.[x.key] ?? null, x)}</span>
        {last &&
          others.map((c) => (
            <span key={c.key}>
              {c.label}: <strong>{formatCell(last[c.key] ?? null, c)}</strong>
            </span>
          ))}
        <span>{formatCell(last?.[x.key] ?? null, x)}</span>
      </figcaption>
    </figure>
  );
}

export function PanelView({ panel, fresh }: { panel: ResolvedPanel; fresh: boolean }) {
  const body = {
    kpi: <Kpi data={panel.data} />,
    bar: <Bars data={panel.data} />,
    table: <Table data={panel.data} />,
    line: <Line data={panel.data} />,
    delta: <Table data={panel.data} signed />,
  }[panel.kind];
  return (
    <section className={`panel panel-${panel.kind}${fresh ? " fresh" : ""}`}>
      <h3>
        {panel.title}
        {fresh && <span className="badge">new</span>}
      </h3>
      {body}
    </section>
  );
}
