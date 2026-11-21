# galaxy-brain (Galaxy brain UX experiment by Motley)

A granularity slider for data answers on SLayer. The plan is in `docs/plan.md`; milestones are GitHub issues #1–#5.

## How to work here

- This repo uses living-architecture. Before changing code, follow the `/la:living-architecture` skill: read
  `architecture/index.yaml`, `architecture/system.arc42.md` and the arc42 file of every element you touch, and obey
  their principles. Never edit `architecture/` without explicit approval of that specific edit.
- Make each change through `/la:pr` on a branch named after its issue (for example `1-walking-skeleton`).
- Before declaring a change done, run: `uv run pytest -q`, `uv run ruff check src tests`, `la-typecheck`,
  `la-arch-check`, `npx -y likec4@1 validate architecture`, `la-check-conventions`.
- Pinned tooling: living-architecture 0.13.0 (`uv tool install living-architecture==0.13.0` and
  `npm install -g living-architecture@0.13.0`), basedpyright 1.40.2.
