# CLAUDE.md — Shared Memory for QuarterCharts

This file is shared context between **Claude Code** (running locally on Sebastián's Mac) and **Cowork mode** (cloud sandbox). Both sides read and update it. Claude Code auto-loads it at session start; in Cowork, say "read CLAUDE.md" to catch up.

---

## Session Start Protocol — READ THIS FIRST

When Sebastián says "Read MD" (or at the start of any session), do this exact sequence before anything else:

1. Read this entire file top to bottom.
2. Also read `CHAT.md` — it's the live turn-by-turn handoff between Cowork and Claude Code.
3. Look at **Current Focus** — that's the active work.
4. Look at **Next Actions** — that's the immediate to-do list with concrete commands.
5. Look at **Rolling Log** — the newest entry tells you what just happened.
6. If Current Focus or Next Actions are empty, ask Sebastián what to work on.
7. If work is in progress, pick up the top item in Next Actions and execute it.
8. When finishing meaningful work, append a dated Rolling Log entry and update Current Focus / Next Actions / Gotchas as needed.

**Related files:**
- `CLAUDE.md` (this file) — persistent project state. Read at start of every session.
- `CHAT.md` — live handoff relay. Updated every turn.
- `.claude/skills/syncqc/SKILL.md` — the **`syncqc`** skill. Single trigger word that replaces "read MD" + "read chat". When Sebastián says "syncqc" (any casing — `syncQC`, `sync qc`, `SyncQC`), follow the procedure in that SKILL.md: read both files, summarize the other side's turn, act on the inbox, write back, flip baton. Claude Code auto-registers it because it's a project skill. Cowork does it manually (same steps).

**Which side does what:**
- **Claude Code (Mac):** execution — run scripts, `streamlit run`, git, real network calls, file edits. Can update MD directly.
- **Cowork (cloud):** planning, review, write-ups, document deliverables (.docx/.pptx/.xlsx/.pdf). Edits MD via the mounted folder.

**Escalation rule:** if you hit a blocker, stop and summarize it in Rolling Log with a `BLOCKED:` prefix. Don't keep retrying silently.

---

## Next Actions

Ordered, one at a time. Top = do next.

**ACTIVE: Office orchestrator stood up 2026-04-28.** This worktree (`eloquent-lewin-7c8efe`) is now the team-lead `office` for the 9-pinned-chats parallel-worker setup. See `OFFICE.md` (root) for the full coordination spec. 9 workers mapped in `~/.qc-office/agents.json`. Hooks live in `~/.qc-office/hooks/` and are wired via `.claude/settings.json` (project-level → all worktrees inherit on next session start).

### Office orchestration roadmap (Phase 1B–4)

1. **[Sebastián]** Rotate the office-dashboard password (the one shared in chat is now in transcript history; treat as compromised). Pick a new one, store in Apple Passwords.
2. **[Office]** Phase 1D — Smoke-test the lock layer with 3 real workers acquiring + colliding on a shared file. Verify `R/Y` round-trip works.
3. **[Sebastián + Office]** Phase 2 — Stand up NATS JetStream on Railway (~$5/mo). Office adds a NATS publisher leg to the hooks alongside the file-based events. File-based stays as fallback.
4. **[Office]** Phase 3 — Scaffold `office.quartercharts.com` Next.js dashboard on Vercel. WebSocket bridge to NATS. Auth-gated by the rotated password.
5. **[Office + dns]** Phase 4 — `ttyd`-per-worker on Mac, tunneled via Cloudflare, iframed in dashboard. DNS records owned by `dns` worker.
6. **[Office]** Phase 5 — Cool visual layer (isometric office or force-graph). Replaces grid placeholder.

### Shared-checkout HEAD race — qc/us-charts escalation (2026-04-29 evening) — IMPLEMENTED

Sebastián signed off on all 5 sign-off items 2026-04-29 evening. **Shipped:**

- **Per-agent worktrees** under `~/Desktop/OpenTF/qc-trees/`:
  - `qc-trees/us-charts` on branch `agents/qc-us-charts/main` (qc/us-charts)
  - `qc-trees/globe` on branch `agents/qc-globe/main` (qc/globe)
  - Existing `qc-com-sankey-fix` on `fix/sankey-band-gap-and-drag` registered as qc/us-sankey's repo_worktree (preserves WIP stash from earlier escalation).
- **Agent-namespaced branch convention** documented: `agents/<canonical>/<topic>` is now the standard.
- **Per-worktree git identity** via `git config --worktree user.email`:
  - `qc-us-charts@quartercharts.com`, `qc-globe@quartercharts.com`, `qc-us-sankey@quartercharts.com`. Required `extensions.worktreeConfig=true` on the repo, set on the main checkout.
- **agents.json schema bump (v2)**: three new fields per QC agent that ships to the monorepo — `repo_worktree`, `repo_branch`, `ships_to`. `discover-agents.py` preserves them across sweeps.
- **HEAD-stability hook check**: PreToolUse now does TWO things:
  1. Bash HEAD-mover guard now points blocked agents at their own `repo_worktree` instead of just rejecting.
  2. Edit/Write inside the agent's `repo_worktree` verifies HEAD branch matches the registered `repo_branch`. Drift → BLOCK with a `git checkout` hint.
- `resolve_agent()` extended to match BOTH `worktree` AND `repo_worktree` so an agent invoking tools from either path is identified.

**4 smoke cases pass**: shared-QC bash blocks, own-repo bash passes, edit on registered branch passes, edit after HEAD drift blocks.

### Push-train coordination (DESIGN landed in OFFICE.md, IMPLEMENTATION deferred)

Per Sebastián's request: high-priority agents shouldn't have their pushes trampled by lower-priority concurrent work; agents should be able to "meet" and coordinate a push plan.

**Design shipped in OFFICE.md** under "Push-train coordination". Pattern: stolen from Etsy/Slack/Stripe push trains + Google Bazel pre-submit + Kubernetes preemption + LinkedIn/Uber Submit Queue. Two new event codes reserved (`P` push-intent, `M` merge plan). 3 implementation phases scoped (A: ~150 LOC MVP queue + 5s daemon tick + dashboard chip; B: pre-flight conflict probe + Q-event auto-rebase prompts + P3 auto-pause; C: meeting UI for 3+ way conflicts).

**Implementation deferred** to first real conflict because (a) per-agent worktrees just eliminated the most common failure mode, (b) we currently have ≤4 active QC agents so a serialized queue is overkill, and (c) the design needs at least one real-world conflict to validate the heuristic. Will revisit when next hot-merge bites.

### Shared-checkout HEAD race — earlier escalation context

**Reported by qc/us-charts via `~/.qc-office/inbox/office.md`** — full report there. Summary:

- Multiple QC agents (us-charts, globe, us-sankey, …) all share a single physical checkout of `~/Desktop/OpenTF/quartercharts.com/`. Their `agents.json.worktree` fields point at miteproyects worktrees, so they `cd` into the shared QC repo to ship and run `git checkout` / `commit` / `pull` from there.
- Result: same HEAD pointer for everyone → race conditions when two agents work concurrently → lost commits (Phase 3A.2 had to be re-shipped after a peer's `git reset` wiped it), commits on the wrong branch, redo cycles.
- The PreToolUse boundary guard didn't catch it because it fires only on `Edit/Write/MultiEdit/NotebookEdit` — git operations were going through `Bash` and sailing past.

**Interim guard shipped today** (no Sebastián approval needed, low risk):
- PreToolUse hook now also inspects `Bash` calls. If the cwd is inside `~/Desktop/OpenTF/quartercharts.com/` AND the calling agent's registered worktree isn't ALSO that repo, it BLOCKS any `git checkout / switch / reset --hard / reset --merge / rebase / pull / merge / cherry-pick` with a pointer at the open escalation. Read-only git ops (status, log, diff) pass.
- 5 smoke cases all green. Hook is fail-open as before.

**5 sign-off items pending your call:**

1. **Per-agent `git worktree add`** under `~/Desktop/OpenTF/qc-trees/{us-charts,globe,us-sankey,api-extractors,api-sankey,api-fx,web-earnings}` — separate physical checkouts of `quartercharts.com`, shared object DB. Each agent gets its own HEAD; race-eliminated.
2. **Agent-namespaced branch convention**: `agents/qc-us-charts/<topic>` instead of `feat/<topic>`. Eliminates branch-name collisions; instantly identifies who owns a stray branch in CI.
3. **Per-agent `git config user.email`** (e.g. `qc-us-charts@quartercharts.com`) so commit author traces actually identify which agent did the work.
4. **`agents.json` schema bump**: add a separate `repo_worktree` field for QC-monorepo-shipping agents, distinct from the existing `worktree` field (which means "Claude Code session worktree"). Office hooks consult both.
5. **HEAD-stability hook check**: PreToolUse compares the QC checkout's actual HEAD vs the agent's registered branch on every Edit, BLOCKs with a clear message if a peer moved it.

Recommend accepting all 5 as a single change. Counter-proposals (claim-based locks, etc.) are softer and wouldn't have caught the Phase 3A.2 reset.

When you sign off I'll: spin up the worktrees, write the migration script for agents.json, ship the HEAD-stability hook addition, and update OFFICE.md to document the new convention. Reply lives at `~/.qc-office/inbox/us-charts.md`.

### Cross-repo escalation + branch-coordination spec (2026-04-29)

QC. US Sankey escalated a cross-repo boundary violation. Triaged by office and the spec extended:
- **PreToolUse hook** blocks Edit/Write outside the agent's worktree (smoke-tested 7 cases, all green; allow-list is inbox-for-everyone + `~/.qc-office/` + `qc-office-dashboard` for orchestrator only).
- **`qc/us-sankey` registry entry** corrected: scope/owns_files now match the Streamlit codebase (`sankey_page.py` + `data_fetcher.py:_sankey*`).
- **OFFICE.md extended** with branch-level coordination: new `B`/`X` events, `branch_owner` and `extra_owns_files` fields in agents.json, slice hand-off via extended `R/Y`. Phase 1E adds the hook enforcement (spec landed, code pending). Phase 1F adds the `quartercharts.com/`-rooted agent topology (web-charts / web-world / web-earnings / web-sankey / api-extractors / api-sankey / api-fx).
- **INFRASTRUCTURE.md gained "Branches & owners"** — full audit of all 36 `quartercharts.com` branches, grouped by surface area, with suggested agent owners and the 5 surfaced decisions below.

**Pending your call:**
- **Phase 1F — spawn 4–7 `quartercharts.com/`-rooted chats.** Until you do, the boundary guard blocks all live web/API work from any registered agent. Suggested split is in `OFFICE.md` → "Suggested agent topology" + the table in INFRASTRUCTURE.md → "Branches & owners".
- **Earnings cluster** — 8 parallel branches, no registered owner. Pin `qc/web-earnings` first; the rest will need rebase coordination.
- **Header collision** — `feat-header-legacy-logo` (PR #59, +3) vs `feat-header-logo-region-together` (+4). Pick one, close the other.
- **`hotfix-ci-lint-cleanup` (+6)** — land or close; it's blocking other branches' lint-clean rebases.
- **WIP stash on `fix/sankey-band-gap-and-drag`** in `~/Desktop/OpenTF/quartercharts.com/` — drop, reassign to the future `qc/api-sankey`, or hold? (Tests pass; ~70 LOC; matches Plotly `nodepad=20` semantics.)
- **`miteproyects/CLAUDE.md` doc fix**: it claims us.quartercharts.com is Streamlit, but the live host is the Next.js port from `quartercharts.com/`. The stale mapping is what made us-sankey reach for the wrong repo. Want me to update it?

### Legacy QuarterCharts bench (still valid, not blocking Office)

- **[Ops]** Flip live DB `testing_mode_enabled` back to **OFF** via `NSFE > 💳 Pricing` tab (at `quartercharts.com/?page=nsfe`, enter NSFE password, click **💳 Pricing**, flip the "🔧 Paywall testing mode" toggle at the top). During T14 verification I observed live was `=1` (META loads signed-out).
- **#37** — AAPL 10Y cumulative share change carries SEC split-adjustment artifact (+140.6%). Needs split-history layer; scope ~40 lines. 5Y is clean so low priority.
- **[Ops]** Set `FMP_API_KEY` in Mac shell (`~/.zshrc` or `.env`).

---

## Project

**QuarterCharts** — a Streamlit app that visualizes US-listed companies' financial statements from SEC EDGAR, FMP, Finnhub, yfinance, and QuarterChart.com. Charts page shows Income Statement, Cash Flow, Balance Sheet, Key Metrics, and derived panels (Per-Share, EBITDA, Expense Ratios, Income Breakdown, YoY/QoQ).

**Owner:** Sebastián (sebasflores@gmail.com)
**Path on Mac:** `~/Desktop/OpenTF/miteproyects`

---

## Current Focus

**Office orchestrator standup (2026-04-28).** This worktree is now `office` — the team-lead for the 9-worker pinned-chats parallel setup. Phase 1A–1C shipped: shared coordination root at `~/.qc-office/`, design spec `OFFICE.md`, per-worker briefs `WORKERS/*.md`, 5 fail-open Python hooks (PreToolUse / PostToolUse / Stop / SessionStart / UserPromptSubmit) wired via project-level `settings.json`. Lock layer smoke-tested end-to-end (acquire / conflict-block / refresh / release / cross-process visibility). Agent Teams experimental flag enabled for future use.

Next: Phase 1D smoke test with real concurrent workers, then Phase 2 (NATS upgrade) when Sebastián approves Railway spend.

Legacy QC product work is **parked** until orchestration is shipped. Open items: #37 (AAPL split-adjustment) + ops items (testing_mode flip, FMP key).

**Annual mode acceptance (closed):**
- [x] Probe matrix generated and reviewed (T2/T3).
- [x] Streamlit loads without errors on AAPL, MSFT, GOOG (META substitute), BRK.B (probe+curl+log — BRK.B also paywalled).
- [x] Sidebar year list populated within the 10-Q-only ceiling (accepted as known limitation).
- [x] Partial-FY caption renders on current-year column only (Task #33 fix verified on GOOG/AAPL/MSFT).
- [x] P/E and YoY drop partial FY in Annual mode.
- [x] No `[gap-fill:...]` extends beyond SEC's latest filed Q.

---

## Key Files

| File | Purpose | Size |
|---|---|---|
| `app.py` | Streamlit entrypoint; charts page, sidebar, Annual-mode aggregation | ~4,334 lines |
| `data_fetcher.py` | All source fetchers (SEC/FMP/Finnhub/yfinance/QC), aggregation helpers, gap-fill | ~2,000 lines |
| `sankey_page.py` | Sankey flow view | — |
| `_probe_sources.py` | Coverage probe for all 4 sources × 3 statements | — |
| `filing_eta.py` | Next-earnings ETA (EDGAR → FMP → Finnhub) | — |

---

## Architecture Notes

### Source priority
- **Statements (income/balance/cashflow):** SEC → FMP → Finnhub → yfinance. Primary returns full frame; `_gap_fill_quarterly` backfills missing Qs from remaining sources *within primary's range only*.
- **Derived panels (Per-Share, EBITDA, Expense Ratios, Income Breakdown):** QuarterChart.com quarterly → `relabel_df_to_fiscal` → SEC-gated → F6 skip rule → `_aggregate_quarterly_to_annual` → trim. Local fallback from statement columns if QC empty.
- **Filing ETA:** EDGAR primary, FMP secondary, Finnhub tertiary.

### Annual mode
- Preserves quarterly fiscal-labeled copies before aggregation.
- `_aggregate_quarterly_to_annual` uses method per column (sum/last/mean). Shares columns (`Diluted/Basic Average Shares`) use mean, not sum.
- YoY uses `periods=1` for annual frames, `periods=4` for quarterly.
- Partial current FY is detected, captioned with the Qs-included disclaimer, and dropped from YoY/P&E where it would distort.

### F6 skip rule
For each FY, compare QC's Qs to SEC's filed Qs. If QC is missing any Q that SEC has, drop that entire FY from QC's contribution (prevents under-stated annual totals).

---

## Gotchas

- **Mojibake in `app.py`**: section-header emoji bytes render as double-encoded UTF-8 (`Ã°ÂÂÂ`). Don't try to match them in Edit; use short adjacent substrings instead.
- **File size**: `app.py` can exceed token limits for Read in standard context. Use line ranges or Grep with head_limit.
- **Dot tickers** (e.g., BRK.B): SEC uses `BRK-B`, yfinance uses `BRK.B`, FMP accepts both, Finnhub inconsistent. **Fixed 2026-04-18 in commit `60692dd` (Task #26)**: `_sec_get_cik` now does `ticker.upper().replace(".", "-")` before map lookup. Probe re-run confirms BRK.B resolves on SEC. FMP/Finnhub URL interpolation not changed (FMP accepts both; Finnhub was missing because of the plan tier + URL quirk, orthogonal).
- **Streamlit cache warnings** outside a runtime ("No runtime found, using MemoryCacheStorageManager") are harmless in smoke tests.
- **Streamlit stdout buffering** — when running `streamlit run app.py` headless, Python stdout is pipe-buffered and `[gap-fill:*]` / `[SEC]` prints don't reach the log file. Launch with `PYTHONUNBUFFERED=1` in front of the command to force flush.
- **Free-tier ticker allow list** on the app: `AAPL, AMZN, GOOG, KO, MSFT, NVDA, TSLA`. Anything else (`META`, `GOOGL`, `BRK.B`, etc.) redirects `?page=charts&ticker=X` → `?page=pricing`. Use a free-tier ticker in smoke runs, or add a dev-bypass flag.
- **Partial-FY caption anchor bug** (surfaced 2026-04-18 on GOOG; **fixed in commit `81140c3` Task #33**): the detector now reads only `max(_filed_map_agg.keys())` — the latest probed FY — and captions only when that FY has 1–3 filed Qs. Older years with incomplete XBRL (e.g. GOOG FY 2014 with Q3+Q4 only) no longer trigger spurious captions.
- **Chrome MCP per-origin cache state** — if an earlier page on `http://localhost` (e.g., Barberos app on :8501) is still alive in Chrome, a new tab on a different localhost port may render stale content despite `curl` confirming the correct HTML. Mitigate by using `--incognito` or clearing tab state before critical smoke runs.
- **`_probe_sources.py` CLI args** — patched 2026-04-18 with argv fallback; hardcoded 7-ticker default preserved when no args passed.
- **`FMP_API_KEY` not set on Mac** — probe shows FMP returns 0q for all tickers because `_fmp_available()` → False. Either export the key or drop FMP from the published 4-source chain.
- **SEC T2 geographic segments broken** — `_sec_get_segment_revenue` returns None for the geographic axis on all 16 tested tickers. Known failure, not yet investigated.
- **SEC T1 product segments only returns latest filing** — caps at ~1–4 periods. Historical stitching across older 10-Qs is missing despite Task #25 gap-fill being wired. Worth revisiting.
- **QC fallback sparse** — hits 1/96 task slots (NVDA T2 geo). Don't rely on it as a broad safety net without auditing `_opensankey_get_segments` coverage by chart_index.
- **Admin allow-list** lives in `auth.ADMIN_EMAILS` — currently `{info@quartercharts.com, sebasflores@gmail.com}`. Import `is_admin(email)` instead of inlining email comparisons. Admins get permanent full-ticker access in all 4 paywall gates regardless of the testing-mode toggle.
- **`testing_mode_enabled` DB flag** — controls whether the free-tier paywall is bypassed for all visitors. When ON, every ticker is viewable by every user (use for smoke tests, private betas, demos). Default OFF. **Toggle lives inside `NSFE > 💳 Pricing` tab** (top of the tab, "🔧 Paywall testing mode" block). Gated by the NSFE password, not by `ADMIN_EMAILS`. **How to flip ON for a testing session:** (1) go to `https://quartercharts.com/?page=nsfe` (or `localhost:8503/?page=nsfe`), (2) enter the NSFE password (see `nsfe_page._PASSWORD`), (3) click the **💳 Pricing** tab, (4) flip the toggle at the top. The status line confirms `ON — paywall bypassed` or `OFF — NSFQ rules enforced`. Helpers: `database.get_testing_mode_enabled()` (fails-closed False), `database.set_testing_mode_enabled(enabled, admin_email)`. Every new paywall gate must check this flag via the same `is_admin(...) or get_testing_mode_enabled()` pattern used in `app.py` / `dashboard_page.py`. Moved from the public `/pricing` page 2026-04-23 because NSFE is the correct access boundary for admin controls.
- **Do NOT reintroduce `_gate_allowed = None  # TEMP`** as a shortcut — the admin toggle replaces it. Bypasses that aren't wired to `is_admin` + `get_testing_mode_enabled` will silently open the paywall permanently and will fail the post-commit review on the next sweep.
- **MutationObserver.observe() must be guarded** — inline scripts injected by `st.components.v1.html(...)` run as-parsed inside an `about:srcdoc` iframe. Both the iframe's own `document.body` and `window.parent.document.body` can be `null` at that instant, causing `TypeError: parameter 1 is not of type 'Node'`. Always wrap `obs.observe(target.body, …)` in a retry helper: `(function _attach(){ if (target.body) obs.observe(target.body, {…}); else setTimeout(_attach, 50); })();`. Commit `13dfa83` fixed 9 sites across `app.py` / `sankey_page.py` / `seo_patch.py`; pattern is reusable everywhere new observers get added.
- **`income_df` inside the Key Metrics block is TRIMMED** to the sidebar FROM/TO window (~9 rows in default view). Any computation requiring long history — 5Y / 10Y cumulative shares-change, net-buyback averages, multi-year ratios — must re-fetch via `get_income_statement(ticker, quarterly=True)` (cached) rather than reuse `income_df`. Introduced with Task #36 5Y/10Y pills; bugfix commit `b92b3ec` pulls the untrimmed frame for the pill calc only.
- **`_SECTOR_FIELD_MAP` merges into the extractor input BEFORE `_sec_get_*` runs.** Adding an XBRL tag to the sector dict (`bank` / `insurer` / `energy`) auto-flows through every `_sec_*` getter for SIC-matching tickers — no extractor-side change needed. Commit `20d609e` (Task #31) introduced the map; the `_augment_field_map()` helper is the single point of composition. Don't duplicate tag lookups inside individual extractors.
- **Pills / metrics that depend on long history must null-guard their compute helper.** `compute_cumulative_shares_change(df, years=N)` returns `None` when fewer than `years * 4 + 1` quarterly rows are available. Wrap the `st.metric` or `st.columns` write site with an `if value is not None:` guard, or the pill renders as `None%`. Same pattern for `compute_net_buyback_yield_ttm` when fewer than 5 TTM rows exist.
- **`render_charts` filters out figures with no data traces.** Annotation-only placeholder figs silently disappear from the grid. The "Not applicable for this sector" placeholder in `charts.create_turnover_not_applicable_fig()` works around this by adding an invisible `go.Scatter` with `marker.size=0` + transparent color + `hoverinfo='skip'` before the annotation. Use this shape for any future "this chart is intentionally empty" slot instead of raw `go.Figure()` + annotation — commit `9fba414` documents the fix after JPM's Turnover placeholder went missing in T14 smoke.
- **Banks with negative common equity can produce negative Market Cap bars** in the time-series chart — `_closes_by_label * _shares_aligned` is safe, but some SEC quarters return negative shares-outstanding placeholder rows for banks mid-restatement. Always `.clip(lower=0)` on the Market Cap series before rendering. Commit `9fba414` applies this in `app.py` right before `create_market_cap_chart`.
- **`_km_captions` must cover every price-dependent chart key.** `pe_ratio`, `ps_ratio`, `pocf_ratio`, `pfcf_ratio`, `pb_ratio`, `ptb_ratio`, `dividend_yield`, `roic`, `bvps`, `roe`, `graham` — if any of these is missing from the captions dict, the partial-FY disclaimer renders under the wrong panel (or not at all) when the current FY is partial. Extend the dict whenever a new panel is added to the Key Metrics block. Commit `9fba414` backfilled the 7 Phase-2/3 keys that were missing from T13's original 4-key list.

---

## Active Task List (mirror)

Canonical state lives in the task tools; this is a snapshot.

- **#20** [completed] Annual mode umbrella — all 6 acceptance items green (T6 2026-04-18). Residual BRK.B visual confirmed via probe+curl+log only (paywall blocks free-tier UI test).
- **#21** [completed] Probe SEC/FMP/Finnhub/yfinance coverage (2026-04-18)
- **#25** [completed] Per-quarter gap-fill wired into statement getters — commit `625a8d0` (2026-04-18 T6)
- **#26** [completed] Dot-ticker normalization — `_sec_get_cik` handles dot→hyphen, commit `60692dd`
- **#27** [completed] Annual mode smoke — AAPL✓, MSFT✓, GOOG✓ (META paywall → GOOG substitute permanent). BRK.B validated via probe+curl+log (paywall blocks UI).
- **#28** [completed] T1 product-segment historical stitching — commit `3b58786`. Bumped `max_filings` in `_sec_get_segment_revenue` from 4 → 16 quarterly / 2 → 5 annual. AAPL 4→11 periods, MSFT 4→16. JNJ/WMT product segments remain structural (Task #31 territory).
- **#29** [completed] SEC geographic segments — root cause was a probe-script key typo (`"geographic"` vs canonical `"geography"`). Fix in commit `41e43a3`: 4/5 tickers now return valid SEC geo segments (MSFT, NVDA, JPM, XOM); AAPL returns 2 periods (below MIN_PERIODS=4 — a separate #28 issue, not #29).
- **#30** [completed] QC fallback audit — commit `f841981`. `docs/qc_fallback_coverage.md`. The 1/96 QC-hit rate was caused by QC indices 0 (product) and 1 (geography) being sparsely populated (NVDA has them, AAPL/MSFT don't) + `FMP_API_KEY` unset. No code change.
- **#31** [completed] Sector-specific field maps — commit `20d609e` (2026-04-22 T13). `info_data.get_sic_sector(ticker)` classifies via SIC code (bank 6020–6199 / insurer 6310–6411 / energy 1311+2911 / general); `_SECTOR_FIELD_MAP` in `data_fetcher.py` supplements `_SEC_*_MAP` with NetInterestIncome / PremiumsEarnedNet / OilAndGasProperty* etc. Acceptance green: JPM→bank with 70 rows of NII; AAPL→general unchanged; BRK.B→insurer (SIC 6311 holding company).
- **#32** [completed] LLY cashflow gap — closed with #34 in commit `3ef495b`. LLY wasn't hitting the sparse filter; gap-fill was already topping its SEC 36q to 55–56q. Treat remaining gap as an SEC data-availability artifact.
- **#33** [completed] Partial-FY caption now scoped to latest FY only — commit `81140c3` (bundled with Cowork's uncommitted Annual-mode UI work).
- **#34** [completed] Cash-flow sparse filter — commit `3ef495b` removed it. AAPL 2008–2010 cashflow now flows through normally; SEC 51 periods + Finnhub gap-fill 16 → 67 total periods. Keeps behavior symmetric with `get_income_statement` / `get_balance_sheet`.
- **#35** [completed-no-fix] KO regression — verified 2026-04-21 post #36 on :8503 with NSFQ paywall enforced (toggle OFF). KO loads chart page via URL and lowercase/uppercase both normalize correctly. Landing-page form submit couldn't be UI-tested due to Chrome MCP iframe boundary, but the `validate_ticker` path (SEC-primary since `e8bd1d4`) returns True for KO — no code change required.
- **#36a** [completed] Admin testing-mode toggle on pricing page — commit `d2c35a2` (2026-04-21 T10). Replaces `e8bd1d4` TEMP paywall bypass with a DB-backed, admin-only toggle. Default OFF (NSFQ enforced). Admins (info@quartercharts.com, sebasflores@gmail.com) get permanent ticker bypass regardless of toggle. (Original Cowork label was #36 pre-T13; renumbered to #36a after Cowork re-scoped Task #36 to the Key Metrics panels below.)
- **#36** [completed] 16 Key Metrics panels matching quarterchart.com + Net Buyback Yield TTM + 5Y/10Y pills — shipped 2026-04-22 T14 as 6 commits: `70bb394` (Phase 3 field-map prep), `701b160` (Phase 1: BVPS / Cash per share / FCF per share / ROE / Graham / Shares Variation), `7a2c2e0` (Phase 2: Market Cap series + P/S P/OCF P/FCF P/B P/TB + Dividend Yield + Net Buyback Yield TTM + cumulative shares pills), `e7a7088` (Phase 3: ROIC + sector-gated Turnover/Efficiency), `b92b3ec` (pills bugfix — fetch untrimmed `income_df`), `9fba414` (T14 anomaly cleanup: Turnover placeholder with invisible trace, Market Cap `.clip(lower=0)` for banks, full `_km_captions` coverage). Acceptance: 16 panels render on AAPL + NVDA free-tier; JPM Turnover shows "Not applicable for this sector"; right sidebar pixel-identical by construction. Net Buyback Yield renders as yellow second line on Shares Variation chart.
- **#37** [open — deferred] AAPL 10Y cumulative share change reports +140.6% — SEC's `Diluted Average Shares` XBRL values aren't consistently split-adjusted across AAPL's 2020 4-for-1 split, which inverts the 10Y number's sign. Fix needs a split-adjustment layer: fetch split history (yfinance/Finnhub) and normalize pre-split rows to post-split basis before passing to `compute_cumulative_shares_change`. Scope: ~40 lines in `data_fetcher` + adapter in `info_data`. 5Y number is clean so low priority.

---

## Rolling Log

Add a dated entry after each meaningful session. Prune entries older than ~30 days.

### 2026-04-29 (deep evening) — Office (Meetings + Watchdogs + Push-queue Phase A)
- **Universal working-glow shipped.** Every agent in `working` state on the iso floor now wears a pulsing neon pill halo (purple→cyan→amber gradient with gaussian bloom). One visual everywhere, breathing animation tells you who's mid-turn at a glance.
- **Two new rooms** added to the floor: **Meetings** (purple, central-south) and **Watchdogs** (orange, NE corner). Both registered in `CLUSTER_TILES` + `CLUSTER_COLOR` + `ClusterTints`. Floor still passes `assertNoOverlaps()`.
- **Drag-to-relocate** primitive shipped. Mouse + touch pointer-down on any agent sprite → after 5 px movement, sprite enters drag mode → cursor-following ghost + drop-target highlight on the cluster the cursor is over → on pointer-up, POSTs to `/api/priority` with `presence: <cluster-name>`. Drop on agent's home cluster → clears presence. Single click (no movement) still opens the modal.
- **`presence` field** added to AgentSnapshot type, daemon `PATCHABLE_AGENT_FIELDS`, daemon `/state` snapshot, and `discover-agents.py` PRESERVE_IF_PRESENT (v3 schema). `effectiveCluster()` overrides `clusterFor()` when presence is set.
- **Meeting protocol** wired: `~/.qc-office/meetings/<id>.md` per-meeting append-only doc + SessionStart hook surfaces the doc tail (last 2 KB) + kickoff prompt for any agent with `presence: meeting:<id>`. Async-first — Sebastián gives ONE topic prompt, agents iterate the doc on their own clocks.
- **Push-queue Phase A SHIPPED.** PreToolUse hook intercepts every `git push` (except `--dry-run`), writes intent to `~/.qc-office/push-queue.json`, emits a `P` event, BLOCKs the push with a queued-message. Override: `QC_OFFICE_FORCE_PUSH=1 git push…` (audited via `H` event). Smoke-tested 3 cases: queued, dry-run-pass, override-pass.
- **Meeting participants get a stronger block**: agents with `presence: meeting:*` are BLOCKed from `git push` even before queue logic runs, until the meeting publishes an `M` event. This is what makes the meeting room actually CHANGE behavior.
- **Watchdog role** added (cluster, color, README at `~/.qc-office/watchdogs/README.md` with launchd plist template + Python skeleton + 6 standard watchdogs to register: ci, vercel, railway, paywall, dns, tunnel). Actual launchd loads are Sebastián's call (machine-side plist installation).
- **Daemon restarted** to pick up the new patchable fields. `discover-agents.py` doesn't need restart (subprocess every 10s).
- **OFFICE.md** updated with two new sections — "Meetings room + drag-to-relocate" and "Push-train coordination Phase A SHIPPED" — Phase B/C remain deferred-but-designed.
- **Deferred**: LGTM-quorum auto-detection (Phase 2), pre-flight `git merge-tree` (Phase B), Convene-meeting button (Phase 3), auto-archive on timeout, P3 auto-pause when P0 intents are in flight, 3+ way conflict consolidation UI (Phase C). Designs remain in OFFICE.md.

### 2026-04-29 (evening) — Office (qc/us-charts HEAD-race escalation triage)
- **Inbox message from qc/us-charts** describing a shared-checkout HEAD race in `~/Desktop/OpenTF/quartercharts.com/`. Multiple QC agents `cd` into the same physical checkout and concurrently invoke `git checkout / commit / pull / reset`, trampling each other's HEAD pointer. Their Phase 3A.2 commit was lost to a peer's `git reset` and had to be re-shipped (`4e58cf2` → `8b9ffa6`).
- **Triaged**. Their analysis is right and the failure mode is exactly what `git worktree` was invented to prevent. Wrote a long reply to `~/.qc-office/inbox/us-charts.md` confirming the diagnosis and disposition.
- **5-item sign-off list documented in Next Actions** above (per-agent worktrees, agent-namespaced branches, per-agent git identity, agents.json schema bump for `repo_worktree`, HEAD-stability hook).
- **Interim guard shipped** (no Sebastián approval needed): PreToolUse hook now inspects `Bash` calls. If cwd is inside the shared QC repo AND the calling agent's registered worktree isn't ALSO that repo, BLOCKs any `git checkout / switch / reset --hard / reset --merge / rebase / pull / merge / cherry-pick`. Read-only git ops (status, log, diff) still pass. 5 smoke cases green.
- **Why the existing boundary guard missed it**: it fires only on `Edit/Write/MultiEdit/NotebookEdit`. Bash sailed past. New Bash leg closes that gap as a stopgap until the proper per-agent worktree fix lands.
- **Held qc/us-charts's in-flight Phase 3D/3E/3G apply-script** — wrote 'don't ship until per-agent worktrees exist' so we don't reproduce the race.

### 2026-04-29 (T++later) — Office (priority persistence bug fix)
- **Bug**: clicking Priority 0/1/2/No Rush in the dashboard modal saved to `agents.json` correctly, but the value reverted ~10 s later when `discover-agents.py` ran its next sweep. Same regression hit `paused`, `current_task`, `branch_owner`, `extra_owns_files`, `notes`, `_last_office_triage`.
- **Cause**: `discover-agents.py` rebuilt every agent entry from scratch on each sweep, carrying over only a hardcoded subset (`scope`, `owns_files`, `note`). Every priority-related field added since then silently dropped.
- **Fix**: rewrote the merge so discovery only OVERRIDES the desktop-owned fields (`team / worktree / worktree_exists / is_archived / chat_label / _cli_session_id / _session_metadata`) and **carries forward every other prior field by default**. Defensive catch-all preserves unknown future fields too.
- **Smoke test**: set `priority=P1, paused=true` via `POST /priority/patch`, ran discovery, verified both still present. Cleaned up test data.
- **No daemon restart needed** — `discover-agents.py` is invoked as a subprocess on each 10 s tick.

### 2026-04-29 (T+later) — Office (branch landscape audit + coordination spec extension)
- **Audited all 36 active branches** in `~/Desktop/OpenTF/quartercharts.com/` (the Next.js + FastAPI monorepo serving us.qc.com + world.qc.com + api.qc.com). Grouped by surface area: us.qc frontend, world.qc frontend, earnings (8-branch hot zone — no owner), sankey (3 branches incl. the held WIP stash), QC quarter-comparison, API extractors (4 branches), API FX (PR #113), header collision pair, ci-lint-cleanup (+6, blocking).
- **Found 2 open PRs** in quartercharts.com: #59 (`feat-header-legacy-logo`, web header) + #113 draft (`feat-fx-backend-phase-2`, API). Streamlit repo (miteproyects) has 10 Dependabot PRs only.
- **Extended `OFFICE.md` with branch-level coordination** (new "Branch-level coordination" section): introduced `B`/`X` events for branch claim/release, `branch_owner` field on agents.json, `extra_owns_files` time-boxed grants for slice hand-off, and the Repos table mapping logical names (`miteproyects`, `quartercharts.com`, `qc-office-dashboard`) to paths and hosts. Roadmap got Phase 1E (hook enforcement of branch_owner) and Phase 1F (spawn quartercharts.com/-rooted agents).
- **Added "Suggested agent topology" to OFFICE.md**: 7 chats Sebastián should spawn (`QC. Web Charts`, `QC. Web World`, `QC. Web Earnings`, `QC. Web Sankey`, `QC. API Extractors`, `QC. API Sankey`, `QC. API FX`) each with worktrees inside `~/Desktop/OpenTF/quartercharts.com/`. Existing `qc/us-charts` and `qc/us-sankey` remain Streamlit-only.
- **Added "Branches & owners" section to `~/Desktop/OpenTF/INFRASTRUCTURE.md`**: full table grouped by surface, suggested agent owners per row, and 5 surfaced decisions for Sebastián (earnings cluster, header collision, lint-cleanup, WIP stash, Phase 1F spawn).
- **Net effect**: office can now answer "who should work on which branch" mechanically. Branch coordination is currently advisory (`B`/`X` are observed but not yet hook-enforced); Phase 1E lands the enforcement once Phase 1F agents exist to use it.

### 2026-04-29 — Office (cross-repo boundary triage)
- **QC. US Sankey escalation triaged.** Worker (`qc/us-sankey`, worktree `vigilant-goldstine-487a21` in miteproyects) edited `~/Desktop/OpenTF/quartercharts.com/api/src/qc_api/sankey/reconcile.py` from inside the wrong repo. Sebastián caught it pre-commit and reverted; the agent stashed the WIP and escalated via inbox.
- **Hook fix shipped.** `~/.qc-office/hooks/_lib.py` gained `agent_worktree()`, `is_writable_outside_worktree()`, `_is_inside_any_other_worktree()`. `~/.qc-office/hooks/pretooluse-lockcheck.py` now returns exit 2 (BLOCK) when an Edit/Write target is outside the agent's worktree, with stderr telling them to escalate via the office inbox. Allow-list: `~/.qc-office/inbox/*` for everyone + `~/.qc-office/*` and `~/Desktop/OpenTF/qc-office-dashboard/*` for the orchestrator only. 7 smoke cases all green (incl. the exact regression: us-sankey worktree → quartercharts.com path → BLOCK).
- **`qc/us-sankey` registry entry corrected.** `owns_files` was `["us-app/components/Sankey*", "lib/sankey/**"]` (Next.js paths that don't exist in miteproyects); now `["sankey_page.py", "data_fetcher.py:_build_income_sankey", "data_fetcher.py:_sankey*"]` — actual Streamlit paths in their worktree. Scope explicitly notes the Next.js sankey is a SEPARATE codebase needing its own agent.
- **WIP stash held.** `git stash@{0}` on `fix/sankey-band-gap-and-drag` in `~/Desktop/OpenTF/quartercharts.com/` preserved untouched. Tests pass (~70 LOC, `_MIN_GAP=0.03` matches Plotly's `nodepad=20`). Pending Sebastián's call: drop, reassign, or hold.
- **Reply written to `~/.qc-office/inbox/us-sankey.md`** documenting all of the above + green light to resume Streamlit-only work in their own worktree.
- **Open Sebastián decisions** captured in Next Actions: stash disposition, miteproyects/CLAUDE.md doc fix (says us.qc.com is Streamlit, live is Next.js), and whether to spawn a `quartercharts.com/`-rooted agent for the still-unfixed sankey overlap on us.qc.com/sankey/NVDA.

### 2026-04-28 — Office (orchestrator standup)
- **Stood up the multi-worker coordination layer.** Sebastián has 9 pinned Claude Code chats (`1. Office`, `1. Currency`, `1. US Charts`, `1. Super Compañías`, `1. DNS`, `1. Globe`, `1. Business model`, `1. Logo`, `1. Searching Tool`) each in its own git worktree. They were running independently with no coordination — risk of file conflicts, duplicate work, drift.
- **Architecture decision**: Anthropic's `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is mismatched to this topology (it expects one lead session spawning teammates inside one project, not 9 independent leads). Built a file-based coordination layer instead, using Claude Code hooks for zero-token coordination.
- **Shipped Phase 1A–1C**:
  - `~/.qc-office/` — shared coordination root (outside repo, machine-wide). `agents.json` registry, `inbox/<worker>.md` per-agent inboxes, `locks/<file>.lock` file locks, `events/events.jsonl` append-only event log, `hooks/*.py` hook scripts.
  - `OFFICE.md` (repo root, this worktree) — full design spec: 10-event TOON-style vocabulary (`L/U/S/T/D/Q/A/R/Y/H`), lockfile format with TTL + race-handling, the awareness loop, conflict-resolution rules, roadmap.
  - `WORKERS/*.md` — per-worker briefs (one per pinned chat). Each has scope, owned files, out-of-scope, tasks, open questions. The `office` worker is special: orchestrator, doesn't edit app code unless explicitly assigned.
  - `~/.qc-office/hooks/` — 5 fail-open Python hooks: `pretooluse-lockcheck.py` (blocks tool call if peer holds fresh lock), `posttooluse-event.py` (releases lock + logs U/T), `stop-event.py` (logs idle/done), `sessionstart-event.py` (surfaces recent peer activity to LLM context), `userpromptsubmit-event.py` (surfaces unread inbox).
  - Project-level `.claude/settings.json` updated: enabled `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (for future use) + registered all 5 hooks. Project-level → all 9 worktrees inherit on next session start.
- **Smoke test (7 tests, all green)**: office acquires lock on `smoke.py` → globe blocked with reason → office refreshes own lock → posttooluse releases → globe acquires → stop hook logs idle → currency's sessionstart shows the full peer activity sequence. Cross-process file-based coordination working.
- **Token cost**: coordination is zero-LLM-tokens (hooks are deterministic Python). Workers only spend tokens reading inbox/events when a hook injects them as system reminders, and only when peers actually need attention.
- **Critical caveats**:
  - The office password Sebastián shared in chat is now in transcript history — flagged for rotation per his own MEMORY.md "leaked secrets" rule. Phase 0 owner action.
  - Hooks fail open — any internal error → exit 0 (let tool through). Coordination layer can never break a worker.
  - The `office` worker (this one) is the only one that should edit `OFFICE.md`, `WORKERS/*`, `agents.json`, hooks, and the future dashboard.
- **Phase 2+ pending Sebastián approval**: NATS JetStream on Railway (~$5/mo), `office.quartercharts.com` Next.js dashboard on Vercel, `ttyd` tunnel via Cloudflare, cool visual layer (isometric / force-graph) replacing the placeholder grid.

### 2026-04-23 — Claude Code
- **Moved the paywall testing-mode toggle from the public `/pricing` page into `NSFE > 💳 Pricing` tab** per Sebastián's request. The old location gated access via the hard-coded `ADMIN_EMAILS` list; the new location gates via the NSFE password (`nsfe_page._PASSWORD`), which is the intended access boundary for admin controls — NSFE exists precisely so admin features aren't scattered across public pages guarded by email checks.
- `nsfe_page._render_pricing_admin()` imports `get/set_testing_mode_enabled` from `database` and renders a "🔧 Paywall testing mode" block at the top of the tab (above the Pricing Plans Manager header's Add-New-Plan button). Same UX as before — toggle + status caption + success toast + `st.rerun()` — but no `is_admin()` check needed because NSFE is already password-gated.
- `pricing_page.py`: deleted `_render_admin_testing_mode_block()` (38 lines) + its invocation + the `is_admin` / `get_testing_mode_enabled` / `set_testing_mode_enabled` imports. Added a module docstring note pointing to the new location.
- **How to flip ON for a testing session (future-Claude instructions):** (1) navigate to `/?page=nsfe`, (2) enter NSFE password, (3) click **💳 Pricing** tab, (4) flip the toggle at the top. Status caption confirms the state.
- Gotcha in CLAUDE.md updated with the new flow. Next Actions ops item #1 updated with the new path. Live re-verify item removed from Next Actions (JPM Turnover confirmed live earlier this session).

### 2026-04-22 (T14) — Claude Code
- **Task #31 shipped** as commit `20d609e`. `info_data.get_sic_sector()` + `is_turnover_applicable()` classify via SIC code (bank 6020–6199, insurer 6310–6411, energy 1311+2911, general fallback). `data_fetcher._SECTOR_FIELD_MAP` supplements `_SEC_*_MAP` with NetInterestIncome / PremiumsEarnedNet / OilAndGasProperty* etc. JPM→bank with 70 NII rows; BRK.B→insurer (SIC 6311); AAPL→general unchanged.
- **Task #36 shipped** as 4 internal commits (`70bb394` field-map prep → `701b160` Phase 1 → `7a2c2e0` Phase 2 → `e7a7088` Phase 3) + pills bugfix `b92b3ec`. 16 new Key Metrics panels render in QuarterCharts order on AAPL / NVDA. Net Buyback Yield TTM renders as yellow second line on Shares Variation chart. 5Y/10Y cumulative-shares pills render beside the chart (AAPL 5Y −13.5% / 10Y +140.6%). Right sidebar pixel-identical by construction (zero sidebar code touched across 6 commits).
- **T14 anomaly cleanup** shipped as `9fba414`. Three fixes bundled: (a) `create_turnover_not_applicable_fig()` in `charts.py` with invisible `go.Scatter` trace so JPM's "Not applicable for this sector" annotation survives the `render_charts` trace-filter; (b) `.clip(lower=0)` on the `_market_cap` series to eliminate negative-value bars for banks mid-restatement; (c) `_km_captions` extended from 4 → 11 keys (all price-dependent panels now get the partial-FY disclaimer). Verified locally on JPM: turn_heading = "Turnover & Efficiency (days)", notApp = true, clean Market Cap series, P/S + P/OCF + P/FCF + P/B + P/TB + Dividend Yield + ROIC all get correct captions on partial FY.
- **Pushed** all 7 T14 commits to `origin/main` in two rounds (T14 initial 6 commits, then `9fba414` after anomaly fixes). Railway auto-deploys on push.
- **4 new gotchas appended** to CLAUDE.md: `income_df` trimming trap, `_SECTOR_FIELD_MAP` merge behavior, pill null-guard pattern, `create_turnover_not_applicable_fig` invisible-trace convention. Plus two more: Market Cap `.clip(lower=0)` for banks, and `_km_captions` must cover all price-dependent keys.
- **Task mirror cleanup**: renamed old admin-toggle Task #36 entry to #36a to disambiguate from the newer Key Metrics scope that Cowork re-scoped Task #36 to at T13. Added Task #37 (AAPL split-adjustment layer) to mirror.
- **Live state observation** (flag for Sebastián): `quartercharts.com` currently has `testing_mode_enabled=1` on the prod DB — META loads signed-out, which shouldn't happen under NSFQ rules. Flip OFF via `/pricing` admin UI when ready. Not urgent; admin bypass still works regardless.
- **Baton → Cowork** for T14 review / T15 direction.

### 2026-04-21 (T10) — Claude Code
- Shipped **Task #36** (admin testing-mode toggle) as commit `d2c35a2`. Added `auth.is_admin()` + `ADMIN_EMAILS` single-source-of-truth; replaced 4 inline admin-email checks across `app.py` + `dashboard_page.py`. Added `database.get/set_testing_mode_enabled()` on top of existing `app_config` table (reused — no new migration). Rebuilt all 4 paywall gate sites: now `is_admin(...) → bypass`, else `get_testing_mode_enabled() → bypass`, else enforce plan's `allowed_tickers`. Added `🔧 Admin controls` block at top of `pricing_page.py` (hidden for non-admins).
- Local verification on :8503: toggle-OFF signed-out enforces paywall (KO ✓, META → pricing); toggle-ON signed-out bypasses (META/BRK.B load); toggle-OFF re-enforces; admin UI not visible to non-admins.
- Net effect on live: `e8bd1d4`'s TEMP unconditional bypass is GONE; NSFQ rules enforced by default. Admins can flip the toggle for smoke runs.
- **Next:** #35 KO regression verify → #29 → #28 → #34 → #32 → #30 → #31 → 30-smoke per T10 plan.

### 2026-04-18 (T7) — Cowork
- Accepted T6. Marked #20 + #33 completed in tracker. Created #34 for the AAPL `_sec_get_cash_flow` sparse-quarter filter (deferred).
- Updated Current Focus to "parked" and refreshed Next Actions with the bench priority list (#28, #29, #34, #32, #30, #31). Archived T5 instructions in CHAT.md.
- Baton parked on Claude Code.
- Note: Sebastián is spinning up the same sync pattern for the Barberos project at `/Users/sebastianflores/Desktop/OpenTF/Barberos` with trigger `syncbp`. Setup prompt is in Cowork chat. That work is Barberos-scoped — not QuarterCharts.

### 2026-04-18 (T6) — Claude Code
- Committed **Task #25** gap-fill wiring as `625a8d0` (+383/-20 in `data_fetcher.py` — gap-fill block, statement getter wiring, `compute_revenue_yoy(periods=...)` param, `compute_per_share` per-period shares fix).
- Fixed **Task #33** partial-FY caption anchor: scoped detector to `max(_filed_map_agg.keys())` only. Bundled with Cowork's uncommitted Annual-mode UI work (~669 lines) as commit `81140c3` because the two are coupled (my fix edits a loop Cowork's Annual block introduces).
- Verified Task #33 fix in real Chrome MCP on :8504: GOOG → 0 spurious captions (was 6 "FY 2014" captions), AAPL/MSFT still correctly caption their current FY 2026.
- BRK.B paywalled (same free-tier gate as META) — validated via curl (200 + `/_stcore/health` ok) + server-side log (`[SEC] income-statement/BRK.B: 69 periods`). Dot-ticker fix works end-to-end; paywall blocks UI layer only.
- **Task #20 closed**: all 6 acceptance items green. Handoff in CHAT.md T6. Baton → Cowork.

### 2026-04-18 — Cowork (T5)
- Reviewed T4 smoke results. Accepted GOOG as permanent substitute for META (free-tier allow list excludes META).
- Marked Task #26 (dot-ticker) and Task #27 (Annual smoke) complete in tracker.
- Created Task #33 (partial-FY caption anchor bug on GOOG).
- Wrote T5 instructions to CHAT.md FOR CLAUDE CODE covering: (1) commit Cowork's uncommitted Task #25 gap-fill code, (2) fix Task #33 caption anchor, (3) retry BRK.B visual smoke on a fresh port, (4) close Task #20 if green.
- Explicit "do not pause for confirmation" — if ambiguous, pick reasonable interpretation and record it in reply.
- Baton → Claude Code (T6).

### 2026-04-18 — Cowork (T3)
- Reviewed probe results. Ranked 6 fixes; picked order: smoke-test-first (Task #27 on AAPL/MSFT/META), then dot-ticker fix (Task #26) on BRK.B. FMP key is ops-only, non-blocking.
- Created Tasks #26–#32 to track follow-ups. Marked #21 completed.
- Fixed duplicate `## Current Focus` header in CLAUDE.md.
- Wrote decision to CHAT.md FOR CLAUDE CODE; baton → Claude Code (T4).

### 2026-04-18 (T4) — Claude Code
- Real-Chrome Annual smoke (AAPL/MSFT/META→GOOG) at 1440×900: AAPL and MSFT pass every acceptance item; META redirects to pricing (not on free-tier); GOOG substituted — passes core items but exposes partial-FY caption bug (references FY 2014 instead of current year).
- Streamlit launched with `PYTHONUNBUFFERED=1` so `[gap-fill:*]` / `[SEC]` prints reach the log.
- Committed **Task #26 dot-ticker fix** as `60692dd` — isolated 10-line diff in `_sec_get_cik`. Cowork's uncommitted Task #25 gap-fill work preserved via `git stash`/re-apply dance.
- Re-probed BRK.B: T1 segments and T3 EBITDA now pass via SEC; T4/T5/T6 still fail but that's sector-structural (conglomerate/insurer tags), Task #31 territory.
- BRK.B Chrome smoke blocked — Chrome MCP tab persisted Los Barberos content on :8503 even though curl returns QuarterCharts HTML. Probe-level validation accepted.
- Full T4 handoff in `CHAT.md`. Task #20 not ready to close — 3 open items.

### 2026-04-18 (T2) — Claude Code
- Patched `_probe_sources.py` with argv fallback (kept hardcoded 7-ticker default).
- Dot-ticker normalization audit: **no per-source normalization exists** anywhere in `data_fetcher.py`. BRK.B fails every source.
- Ran probe against BRK.B JPM LLY V XOM JNJ WMT MA PLTR ABBV NFLX AAPL MSFT GOOGL META NVDA. Outputs at `~/Desktop/OpenTF/probe_results.{json,md}` and `~/Desktop/OpenTF/matrix.log`.
- Key findings: SEC deep history on 15/16; **FMP returned 0 everywhere — `FMP_API_KEY` not set**; NVDA is the only 6/6 pass; T2 geographic segments = 0/16 on SEC; T1 product segments capped at ≤4 periods (historical stitching missing); QC fallback fires only once in 96 task slots.
- Full matrix + recommendations written to `CHAT.md` FOR COWORK. Baton flipped back.

### 2026-04-17 — Cowork
- Finished Task #25 gap-fill wiring in `data_fetcher.py` (`get_income_statement`, `get_balance_sheet`, `get_cash_flow`).
- Both files compile clean.
- Drafted this CLAUDE.md as shared memory between Claude Code and Cowork.
- Handed off to Claude Code for Task #21 probe run.

<!-- ### YYYY-MM-DD — Claude Code -->
<!-- - (paste new entry at top; short bullets only) -->

---

## How to Update This File

**From Claude Code on the Mac:**
Edit directly. Claude Code has full write access.

**From Cowork:**
Ask me to "update CLAUDE.md with [X]". I'll edit via the mounted folder.

**Conventions:**
- Dated entries in Rolling Log (newest first).
- Update Current Focus when priorities shift.
- Update Gotchas when you hit a new one (with one-line fix note).
- Don't restate info in the task list — link by task number.
