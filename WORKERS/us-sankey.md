# us-sankey — Sankey income-statement flow chart

**Worktree**: (assigned per active session)
**Chat label**: `QC. US Sankey`

## Role

Own the Sankey diagram that visualizes a US company's income-statement flow (revenue → costs → operating income → tax → net income). This is QC's signature chart and a key visual differentiator. Owns the rendering pipeline + the data shaping that turns raw income-statement rows into Sankey nodes/edges.

Lives inside the `us-charts` Next.js app but has its own focused scope so it doesn't get squeezed by general layout work.

## Owns

- `us-app/components/Sankey*` (SankeyChart.tsx, SankeyNode.tsx, SankeyTooltip.tsx, etc.)
- `lib/sankey/**` (data transforms, node/edge builders, layout algorithms)
- `lib/sankey/colors.ts` (color palette — green for revenue, red for costs, etc.)
- Tests for the above
- Sankey-specific docs: `docs/sankey/spec.md`

## Out of scope (do NOT touch)

- General page layout in us-charts.
- Other chart types (bar, line, area) → us-charts.
- Source data fetching → comes from the legacy `data_fetcher.py` (Streamlit) or the future API (`platform` + `currency`).
- Globe / world.qc.com → `globe`.

## Cross-worker coordination

- `Q to=us-charts` — when integrating into a new page or changing shared chart wrapper.
- `Q to=currency` — FX conversion of income-statement values.
- `Q to=business-model` — which Sankey features go behind the paywall (free tier may show only top-level flow; paid shows segment breakdowns).

## Tasks (suggested initial)

- [ ] T1: Pick the rendering library — `d3-sankey` (battle-tested, ugly out of the box), `react-flow` with sankey layout, custom SVG. Document choice in `docs/sankey/spec.md`.
- [ ] T2: Spec the data shape: nodes (Revenue, COGS, R&D, SG&A, Op Income, Tax, Net Income, Other) + edges (with values).
- [ ] T3: First implementation for AAPL using mock data.
- [ ] T4: Wire to real income-statement data once `currency` + `platform` data path is ready.
- [ ] T5: Add hover tooltips with breakdowns.
- [ ] T6: Sankey for segments (segment revenue → segment operating income) — paid-tier feature.

## Open questions

- How many flow levels to show on free vs paid tier?
- Negative values handling (e.g. when operating income is negative) — visual convention?
- Time-series animation: can the Sankey morph from Q4 to Q1? Hard but cool. Defer.
