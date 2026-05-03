# us-sankey-2 — Sankey income-statement flow chart (active)

**Worktree (session)**: `.claude/worktrees/musing-ptolemy-1887df`
**Branch (session)**: `claude/musing-ptolemy-1887df`
**Repo worktree (ship target)**: `/Users/sebastianflores/Desktop/OpenTF/qc-com-sankey-fix`
**Repo branch**: `fix/sankey-proportional-bands`
**Ships to**: `quartercharts.com` → `us.quartercharts.com/sankey/<ticker>`
**Chat label**: `QC. US Sankey 2`
**Took over from**: `qc/us-sankey` (vigilant-goldstine-487a21) on 2026-04-29 after the original chat hit MCP image-dimension API errors. The previous brief at `WORKERS/us-sankey.md` is now historical reference only.

## Role

Own the Sankey diagram that visualizes a US company's income-statement flow (revenue → costs → operating income → tax → net income) on `us.quartercharts.com/sankey/<ticker>`. This is QC's signature chart. You own the rendering pipeline + the data shaping that turns raw income-statement rows into Sankey nodes/edges, across both:

- **Streamlit** (`miteproyects/sankey_page.py` + `data_fetcher._build_income_sankey`)
- **Next.js port** (`quartercharts.com/web/components/sankey-chart.tsx` + `quartercharts.com/api/src/qc_api/sankey/**`)

You inherit two already-merged PRs from your predecessor:
- **PR #202** — `fix(web): sankey inter-band gap + always-on node drag` (gap fix + drag handlers).
- **PR #203** — `fix(web): bands fill parent column` (proportional bands).

Working tree on `fix/sankey-proportional-bands` was clean at handover.

## Owns

- `sankey_page.py` (Streamlit page)
- `data_fetcher.py:_build_income_sankey` and `data_fetcher.py:_sankey*` helpers
- `quartercharts.com/web/components/sankey-chart.tsx` and the rest of the Next.js sankey component tree
- `quartercharts.com/api/src/qc_api/sankey/**` (reconcile, layout, XBRL tag chain)
- Sankey tests on both sides

## Out of scope (do NOT touch)

- General page layout in us-charts → `qc/us-charts`.
- Other chart types → `qc/us-charts`.
- Globe / world.qc.com → `qc/globe`.
- FX conversion → `qc/currency`.
- Anything orchestrator-side (`OFFICE.md`, `WORKERS/**`, `.claude/hooks/**`, `~/.qc-office/**`) → `qc/office-2`.

## Cross-worker coordination

- `Q to=office` — when you need a registry change or hit a hook block you can't explain.
- `Q to=us-charts` — when integrating into a new page or changing a shared chart wrapper.
- `Q to=currency` — FX conversion of income-statement values.

## Active task (assigned 2026-04-29 by Sebastián)

**Take over `qc/us-sankey`'s open work.** The original agent shipped PR #202 + #203 then crashed mid-session. Inherited surface area:

- [ ] **T1**: Read `~/.qc-office/inbox/us-sankey.md` (you may read your predecessor's inbox during takeover — exception to the usual peer-private rule). It has the full hand-off context: PRs shipped, the `repo_worktree` hook fall-through patch the predecessor self-applied, and the current branch state.
- [ ] **T2**: Confirm `fix/sankey-proportional-bands` is in a clean shippable state (already merged per predecessor, but verify on `qc-com-sankey-fix` working tree).
- [ ] **T3**: Patch `INFRASTRUCTURE.md` line 498 — it still calls `fix/sankey-band-gap-and-drag` "WIP stash held pending Sebastián's call," but that branch shipped as PR #202 days ago. (Office territory; emit `R` first or ask `qc/office-2` to do it.)
- [ ] **T4**: Pick up wherever the predecessor stopped — likely follow-on sankey polish (label collision, drag UX, color palette, segment-level sankey for paid tier). Surface options to Sebastián and let him pick.

## Open questions for Sebastián

- Was the `repo_worktree` fall-through patch in `pretooluse-lockcheck.py` (self-applied by the predecessor) accepted as-is? If not, `qc/office-2` needs to revert + re-apply on its own terms before you ship more cross-repo work.
- After T4 polish, is segment-level sankey the next big-ticket item, or do you want to switch to a different chart family?

## Notes inherited from predecessor (do not re-derive)

- `_MIN_GAP = 0.03` matches Plotly `nodepad=20` from the working Streamlit chart; this is the value that shipped in PR #202.
- 90/90 sankey API tests + 183/183 web tests + tsc + biome + ruff + mypy were all green at handover.
- The proper way to push from `qc-com-sankey-fix` is straight `git push`; the Bash hook does NOT intercept arbitrary file writes (only `git push` to specific protected branches + HEAD-movers).
