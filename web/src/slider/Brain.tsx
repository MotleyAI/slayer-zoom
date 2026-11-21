/**
 * The depth cue on the handle: a brain that grows brighter at each depth, from a plain outline at the single number
 * to a radiant one at the deepest analysis. The ring around it fills as the reader pulls toward the next depth.
 */
export function Brain({ stage, charge, depth }: { stage: number; charge: number; depth: number }) {
  const rays = Math.round(stage * 10);
  const ring = Math.abs(charge);
  return (
    <svg
      className={`brain-cue${stage >= 1 ? " radiant" : ""}`}
      viewBox="-32 -32 64 64"
      aria-hidden
      style={{ ["--stage" as string]: stage }}
    >
      <circle className="ring-track" r={28} />
      <circle
        className={`ring${charge < 0 ? " folding" : ""}`}
        opacity={ring > 0 ? 1 : 0}
        r={28}
        pathLength={1}
        strokeDasharray={`${ring} 1`}
        transform="rotate(-90)"
      />
      <g className="rays">
        {Array.from({ length: rays }, (_, i) => {
          const angle = (i / rays) * Math.PI * 2 - Math.PI / 2;
          return (
            <line
              key={i}
              x1={Math.cos(angle) * 20}
              y1={Math.sin(angle) * 20}
              x2={Math.cos(angle) * 25}
              y2={Math.sin(angle) * 25}
            />
          );
        })}
      </g>
      {/* Keyed by depth so each unlock replays the pulse. */}
      <g className="brain-body" key={depth} transform={`scale(${0.78 + 0.32 * stage})`}>
        <path
          className="lobes"
          d="M-1.5,-14 C-7,-18.5 -16.5,-15 -16.5,-7 C-21,-4 -21,4.5 -16,7.5 C-15,14 -7.5,16.5 -1.5,13 Z M1.5,-14 C7,-18.5 16.5,-15 16.5,-7 C21,-4 21,4.5 16,7.5 C15,14 7.5,16.5 1.5,13 Z"
        />
        <path
          className="folds"
          d="M-12,-8 C-8,-10 -5.5,-6 -9,-2.5 M-14.5,2.5 C-10.5,0.5 -7,4.5 -10.5,8 M-5,-11.5 C-3,-6.5 -6.5,-3 -4,1.5 M-6,6 C-4,8 -4,10 -6,11.5 M12,-8 C8,-10 5.5,-6 9,-2.5 M14.5,2.5 C10.5,0.5 7,4.5 10.5,8 M5,-11.5 C3,-6.5 6.5,-3 4,1.5 M6,6 C4,8 4,10 6,11.5"
        />
      </g>
    </svg>
  );
}
