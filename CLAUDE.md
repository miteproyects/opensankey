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

1. **[Claude Code]** Patch `_probe_sources.py` to accept CLI tickers with fallback to hardcoded list. Diff:
   ```python
   import sys
   if len(sys.argv) > 1:
       TICKERS = [t.upper() for t in sys.argv[1:]]
   ```
2. **[Claude Code]** Grep `data_fetcher.py` for dot-ticker normalization (`BRK.B` → `BRK-B` etc.) across SEC / FMP / Finnhub / yfinance. Report which sources normalize and which don't. Do NOT fix yet.
3. **[Claude Code]** Run probe with the full 16-ticker set:
   ```
   python3 _probe_sources.py BRK.B JPM LLY V XOM JNJ WMT MA PLTR ABBV NFLX AAPL MSFT GOOGL META NVDA
   ```
   Output format: `TICKER statement source: N quarters [YYYYQ# – YYYYQ#]`. Flag sources with 0 or <8 quarters.
4. **[Claude Code]** Append Rolling Log entry with probe results + any dot-ticker failures.
5. **[Cowork]** On next "Read MD", review probe matrix and decide: keep FMP → Finnhub → yfinance priority, or swap per statement type.
6. **[Claude Code]** `streamlit run app.py` and exercise Annual mode on a ticker with known SEC gaps. Watch for `[gap-fill:...]` log lines. Verify sidebar Annual year list expands to include newly fillable years. Verify partial-FY caption renders on current-year column.
7. **[Claude Code]** Mark Task #21 complete in TodoWrite when probe is reviewed. Mark Task #20 complete once end-to-end Annual mode test passes.

---

## Current Focus

**QuarterCharts** — a Streamlit app that visualizes US-listed companies' financial statements from SEC EDGAR, FMP, Finnhub, yfinance, and QuarterChart.com. Charts page shows Income Statement, Cash Flow, Balance Sheet, Key Metrics, and derived panels (Per-Share, EBITDA, Expense Ratios, Income Breakdown, YoY/QoQ).

**Owner:** Sebastián (sebasflores@gmail.com)
**Path on Mac:** `~/Desktop/OpenTF/miteproyects`

---

## Current Focus

Annual mode rollout (Task #20 umbrella). Just finished **Task #25** — per-quarter historical gap-fill wired into `data_fetcher.py`. Now in the **testing phase**: run the coverage probe (Task #21), then exercise Annual mode end-to-end in Streamlit.

**Acceptance for "Annual mode done":**
- [ ] Probe matrix generated and reviewed; source priority confirmed or adjusted.
- [ ] Streamlit Annual mode loads without errors on AAPL, MSFT, META, BRK.B.
- [ ] Sidebar year list includes years previously blocked by SEC gaps (gap-fill working).
- [ ] Partial-FY caption renders on current-year column only.
- [ ] P/E and YoY correctly drop the partial FY in Annual mode.
- [ ] No `[gap-fill:...]` lines extend beyond SEC's latest filed Q.

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
- **Dot tickers** (e.g., BRK.B): SEC uses `BRK-B`, yfinance uses `BRK.B`, FMP accepts both, Finnhub inconsistent. Normalization per source may still be missing — check `data_fetcher.py` before blaming the probe.
- **Streamlit cache warnings** outside a runtime ("No runtime found, using MemoryCacheStorageManager") are harmless in smoke tests.
- **`_probe_sources.py` CLI args** — as of last check, script ignored `sys.argv` and used hardcoded 7 tickers. Claude Code was asked to patch with argv fallback.

---

## Active Task List (mirror)

Canonical state lives in the task tools; this is a snapshot.

- **#20** [in_progress] Annual mode umbrella
- **#21** [pending] Probe SEC/FMP/Finnhub/yfinance coverage — blocked on live network (Mac only)
- **#25** [completed] F4 per-quarter gap-fill

---

## Rolling Log

Add a dated entry after each meaningful session. Prune entries older than ~30 days.

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
