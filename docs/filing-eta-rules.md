# Filing ETA — 3-Source Implementation Rules

**Scope.** This document is the single source of truth for the `~ filing in Xd ⓘ` feature. It applies to **every** surface where that label appears. The sidebar *Latest from [TICKER]* block, the quarter-selector filing-buffer tooltip, every row of the Earnings Calendar (weekly day view **and** past/upcoming tables of the ticker search), and any future surface that wants to show a filing ETA **must** go through this engine and present the same ⓘ popover UX.

## Summary of the implementation

### 1. New module `filing_eta.py` — a single, cached engine used by all three `~` features

Exposes:

- `get_filing_eta(ticker, event_label, finnhub_date)` — returns the full source dict used by the ⓘ popover (`primary_days`, `primary_label`, `primary_source`, plus `edgar_*`, `fmp_*`, `finnhub_*`).
- `get_filing_cadence(ticker)` — per-source median gap in days (for the quarter-selector locked-button tooltip).
- `render_eta_info_html(eta_dict)` — produces the primary label followed by the ⓘ icon with the hover/click popover.
- `ETA_INFO_CSS` — the single CSS block that controls the ⓘ popover look, overflow behaviour, and `:hover` / `[open]` show rules. Anywhere the popover is rendered the CSS must be injected (once per Streamlit markdown call) or the popover will be clipped by the surrounding scroll container.

It:

- Hits **SEC EDGAR first** via the official `data.sec.gov/submissions/CIK{cik}.json` endpoint. Free, no API key, requires just a descriptive `User-Agent` header (set to `QuarterCharts research@quartercharts.com`, overridable via `SEC_USER_AGENT` env var). Reads historical 10-Q / 10-K `filingDate` + `reportDate` plus the most recent 8-K.
- Falls back to **FMP** via `get_fiscal_calendar()` (already integrated) for quarter history, plus FMP `/earning_calendar` for the upcoming announcement date when no history is available.
- Falls through to **Finnhub** `/calendar/earnings` only as a last resort (announcement-date proxy).
- Caches ticker → CIK for 24 h, submissions for 2 h, earning calendars for 15 min.

### 2. Sidebar "Latest from [TICKER]" Filing ETA (`app.py`)

The hard-coded FMP-only block was replaced with a call to `get_filing_eta()`. The primary label is rendered inline followed by a small `ⓘ` icon; hovering or tab-focusing that icon reveals a popover showing `SEC EDGAR ★ | FMP | Finnhub` with each source's estimate and a `★` marker on the source currently being used. Graceful `n/a` when a source has no data.

### 3. Quarter-selector filing buffer (`app.py`)

The FMP-only median was replaced with `get_filing_cadence()` (EDGAR → FMP → Finnhub). Each locked quarter button now carries an enhanced Streamlit `help` tooltip that includes the per-source medians and which source was chosen (e.g. `Sources: EDGAR=30d, FMP=30d, Finnhub=n/a · using EDGAR`).

### 4. Earnings page Date column (`earnings_page.py`)

`_compute_filing_eta_days` was replaced with `_compute_filing_eta_sources`, which pulls all three sources in one call. The row now renders `2026-04-29 · ~ filing in 13d ⓘ` where the ⓘ popover shows all three source values.

This applies to **every** `_render_earnings_table` call — including the weekly day view and the ticker-search upcoming/past tables. `ETA_INFO_CSS` is injected once per table render.

### 5. Verification

- `ast.parse` clean on `filing_eta.py`, `earnings_page.py`, `app.py`.
- Offline simulation confirms:
  - `_fmt_label` handles all edge cases (`None`, 0, negative, 1, N).
  - `_predicted_period_end` correct for calendar-year (META, fy=12), Apple (fy=9), and NVDA-style (fy=1).
  - `_median_gap_days` on META-like quarters = 29 d.
  - ETA days for META Q1 2026 = 13 d (matches the current sidebar & earnings-page value).
  - `render_eta_info_html` produces clean HTML with star marker on primary source and `n/a` rows when a source is missing.

## Invariants — things that must not regress

- Callers never fetch filings themselves. They call `get_filing_eta(...)` / `get_filing_cadence(...)` and render `render_eta_info_html(...)`.
- The ⓘ hover UI is a plain-text browser tooltip built via the HTML `title="…"` attribute (mirrors `_get_help_text()` for the quarter-selector buttons). The tooltip content comes from `get_filing_eta_help_text(eta)` — keep that function as the single source of truth.
- **CRITICAL — the `title="…"` value must never contain a literal newline character.** `st.markdown(unsafe_allow_html=True)` routes through react-markdown, which tokenises input line-by-line; a raw `\n` inside an attribute terminates the current markdown block and blows up the surrounding `<table>` HTML so every row renders empty. Fix: HTML-escape the help text, then `.replace("\n", "&#10;")`. Browsers still render the numeric char ref as a line break inside the tooltip, but the attribute string itself is single-line so the tokeniser is unaffected.
- `ETA_INFO_CSS` is injected once anywhere `render_eta_info_html` is rendered. It styles only the amber primary label and the circular ⓘ icon — no popover CSS anymore.
- **CRITICAL — never concatenate `ETA_INFO_CSS` with visible HTML in the same `st.markdown` call inside the main block-container.** `app.py` line ~145 ships a global rule
  `.block-container>.stVerticalBlock>[data-testid="stElementContainer"]:has(style):not(:has(.nav-bar)){position:absolute!important;height:0!important;overflow:hidden!important}`
  whose job is to hide injected `<style>`-only blocks. `:has(style)` matches any `stElementContainer` that contains a `<style>` anywhere inside, so a combined `<style>…</style><div class="ec-table-wrap">…</div>` markdown collapses the whole table to `height:0` — rows end up in the DOM but invisibly stacked on top of each other. The fix is to inject `ETA_INFO_CSS` via its own `st.markdown(...)` (it will be hidden as intended) and render the content via a separate `st.markdown(...)`. The sidebar is not affected because sidebar elements are not direct `.block-container > .stVerticalBlock` children.
- The source order in the popover is always **EDGAR, FMP, Finnhub** with `★` on the `primary_source`. Missing sources render `n/a` — they are never hidden.
- `primary_source` is picked in priority order: EDGAR → FMP → Finnhub. Never lie about the source being used.

## When to apply

Any surface that wants to show a filing ETA **must**:

1. Call `get_filing_eta(ticker, event_label, finnhub_date)` — do not reinvent.
2. Inject `ETA_INFO_CSS` into the page / component markdown.
3. Render `render_eta_info_html(eta_dict)` inline where the `~ filing in Xd ⓘ` belongs.

If a surface shows a per-ticker schedule-like item (sidebar block, calendar row, search row, watchlist row, etc.) and the earnings date is in the future, the ETA **must** appear. No exceptions — consistency across surfaces is the point.
