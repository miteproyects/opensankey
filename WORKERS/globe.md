# globe — world.quartercharts.com 3D globe widget

**Worktree**: `.claude/worktrees/silly-benz-aff74f`
**Chat label**: `QC. Globe`

## Role

Own the entire 3D-globe widget on `world.quartercharts.com`. This is the multi-country landing experience. Each country dot click → that country's `<cc>.quartercharts.com` page (US lives, others coming).

Replaces the old narrow "fix 3 specific bugs" scope with full ownership of the widget.

## Owns

- `world-app/components/Globe*` (Globe.tsx, GlobeControls.tsx, GlobeOverlay.tsx, etc.)
- `world-app/lib/geo*` (projection helpers, country lookup, geo-data loading)
- `world-app/data/countries.geo.json` (or wherever Natural Earth / TopoJSON country borders live)
- `world-app/hooks/useGlobe*`
- Tests for the above

## Out of scope (do NOT touch)

- Header / nav / logos (us-charts owns headers; logo work is folded back into us-charts).
- Search box on the world page → `searching-tool` was retired; if a successor appears, coordinate.
- Backend / API plumbing → `platform` owns.
- Per-country financial data → `super-companias` (EC) and future country workers.

## Open bugs (carried forward from earlier scope)

- [ ] T1: Country borders — confirm they render. Likely needs Natural Earth GeoJSON layer wired to deck.gl / globe.gl.
- [ ] T2: Drag/zoom interactions — verify the controller prop is set + globe-gl is the chosen library.
- [ ] T3: USA dot click → `https://us.quartercharts.com` (or relative redirect if same Vercel project).
- [ ] T4: Coordinate with `dns` (now folded into `platform`) on the redirect target — `us.qc.com` not `usa.qc.com` per memory.
- [ ] T5: Coordinate with `business-model` on which countries show as "live" vs "coming soon".

## Cross-worker coordination

- `Q to=business-model` — country activation order.
- `Q to=platform` — DNS for new country subdomains.
- `Q to=us-charts` — visual handoff when a user clicks the USA dot.

## Open questions

- Which library is the actual current choice — globe.gl, react-globe.gl, deck.gl, or three.js? (Confirm in T1.)
- Performance: is the country GeoJSON pre-simplified or full-fidelity? (Affects drag smoothness on lower-end devices.)
