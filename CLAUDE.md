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

Ordered, one at a time. Top = do next. Remove items as they complete; promote new items from Current Focus.

**Annual mode is shipped (Task #20 closed at T6).** No active blocker; baton parked on Claude Code.

Bench, in rough priority — Sebastián picks which one to greenlight next:

1. **#28** — T1 product-segment historical stitching. SEC only returns latest filing; older 10-Q segments don't stitch. Touches the same `get_edgar_available_qs_map` filter surface that capped the Annual sidebar year list at ~10 years.
2. **#29** — SEC geographic segments returning None on all 16 probed tickers. Likely a single axis-name mismatch.
3. **#34** — AAPL `_sec_get_cash_flow` sparse-quarter filter (dropping 2008–2010). Low effort to diagnose; same family as #32.
4. **#32** — LLY cashflow SEC=36q vs 70q income. Investigate with #34 together.
5. **#30** — QC fallback coverage audit (fires 1/96 slots). Lower priority.
6. **#31** — Sector field maps for conglomerates/banks/insurers/energy. Largest scope; defer until there's a triage list.
7. **[Ops / Sebastián]** Set `FMP_API_KEY` in Mac shell (`~/.zshrc` or `.env`). Closes the 4-source chain validation, but nothing blocks on it.

---

## Project

**QuarterCharts** — a Streamlit app that visualizes US-listed companies' financial statements from SEC EDGAR, FMP, Finnhub, yfinance, and QuarterChart.com. Charts page shows Income Statement, Cash Flow, Balance Sheet, Key Metrics, and derived panels (Per-Share, EBITDA, Expense Ratios, Income Breakdown, YoY/QoQ).

**Owner:** Sebastián (sebasflores@gmail.com)
**Path on Mac:** `~/Desktop/OpenTF/miteproyects`

---

## Current Focus

**Parked.** Annual mode (Task #20) shipped 2026-04-18 at T6 — commits `60692dd` (#26 dot-ticker), `625a8d0` (#25 gap-fill), `81140c3` (#33 caption + Annual UI). All 6 acceptance items green.

Next focus will be whichever task Sebastián promotes from the Next Actions bench. Likely candidates: #28 (segment stitching), #29 (SEC geo segments), or the #32/#34 cashflow pair.

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
- **`testing_mode_enabled` DB flag** (Task #36, commit `d2c35a2`) — admin-only toggle at `/?page=pricing` under "🔧 Admin controls". When ON, the free-tier paywall is bypassed for every visitor. Default OFF. Helpers: `database.get_testing_mode_enabled()` (fails-closed False), `database.set_testing_mode_enabled(enabled, admin_email)`. Every new paywall gate must check this flag via the same `is_admin(...) or get_testing_mode_enabled()` pattern used in `app.py` / `dashboard_page.py`.
- **Do NOT reintroduce `_gate_allowed = None  # TEMP`** as a shortcut — the admin toggle replaces it. Bypasses that aren't wired to `is_admin` + `get_testing_mode_enabled` will silently open the paywall permanently and will fail the post-commit review on the next sweep.

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
- **#31** [pending] Sector-specific field maps for conglomerates/insurers/banks/energy (deferred)
- **#32** [completed] LLY cashflow gap — closed with #34 in commit `3ef495b`. LLY wasn't hitting the sparse filter; gap-fill was already topping its SEC 36q to 55–56q. Treat remaining gap as an SEC data-availability artifact.
- **#33** [completed] Partial-FY caption now scoped to latest FY only — commit `81140c3` (bundled with Cowork's uncommitted Annual-mode UI work).
- **#34** [completed] Cash-flow sparse filter — commit `3ef495b` removed it. AAPL 2008–2010 cashflow now flows through normally; SEC 51 periods + Finnhub gap-fill 16 → 67 total periods. Keeps behavior symmetric with `get_income_statement` / `get_balance_sheet`.
- **#35** [completed-no-fix] KO regression — verified 2026-04-21 post #36 on :8503 with NSFQ paywall enforced (toggle OFF). KO loads chart page via URL and lowercase/uppercase both normalize correctly. Landing-page form submit couldn't be UI-tested due to Chrome MCP iframe boundary, but the `validate_ticker` path (SEC-primary since `e8bd1d4`) returns True for KO — no code change required.
- **#36** [completed] Admin testing-mode toggle on pricing page — commit `d2c35a2` (2026-04-21 T10). Replaces `e8bd1d4` TEMP paywall bypass with a DB-backed, admin-only toggle. Default OFF (NSFQ enforced). Admins (info@quartercharts.com, sebasflores@gmail.com) get permanent ticker bypass regardless of toggle.

---

## Rolling Log

Add a dated entry after each meaningful session. Prune entries older than ~30 days.

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
