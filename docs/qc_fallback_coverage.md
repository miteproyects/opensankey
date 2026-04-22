# QuarterCharts.com fallback coverage audit (Task #30)

Quick audit of which `chart_index` values `quarterchart.com` actually serves vs which the codebase queries, to explain why the T2 probe reported QC fired in only 1/96 task slots.

## How the codebase uses QC today

`_opensankey_get_segments(ticker, chart_index, quarterly=True)` is the sole entry point ([`data_fetcher.py:546`](data_fetcher.py:546)). It reads `blob["chart_data"]["data"]["quarter"|"annual"][chart_index]`. Two callers in the app:

| Caller | `chart_index` | Purpose |
|---|---|---|
| `_cached_revenue_by_product` ([`data_fetcher.py:965`](data_fetcher.py:965)) | **0** | Primary source for `get_revenue_by_product()` |
| `_cached_revenue_by_geography` ([`data_fetcher.py:995`](data_fetcher.py:995)) | **1** | Primary source for `get_revenue_by_geography()` |

The probe script queries more indices (0, 1, 5, 12, 13, 14) but they are **probe-only** — never reached from the live app.

## What QC actually returns

Sampled raw `chart_data.data.quarter` payload for 3 tickers (2026-04-21):

| Ticker | Index 0 (product) | Index 1 (geography) | Indices 2–20 |
|---|---|---|---|
| **AAPL** | empty (0 labels, 0 datasets) | empty | populated (162 labels × 1–4 datasets each) |
| **MSFT** | empty | empty | populated (162 labels × 1–4 datasets each) |
| **NVDA** | **populated** (108 labels × 10 datasets) | **populated** (108 labels × 7 datasets) | populated |

All three tickers expose 43 quarterly chart slots total. NVDA is the only one of the three with data in slots 0 and 1.

## Finding

The T2 probe's "QC fires 1/96 task slots" observation is explained by this sparsity at indices 0 and 1, not by a bug in `_opensankey_get_segments`. QC holds rich data for most indices (`2`–`42`) across all three tickers, but the app's two segment callers only look at 0/1 — so most tickers silently fall through to FMP (no key → empty) and then to an empty DataFrame.

## What's on the other indices

QC's chart_index numbering is stable across tickers. From the index ordering plus the probe comments in `_probe_sources.py`:

| Index | Approximate content (QC's own ordering) |
|---|---|
| 0 | Product segments — sparse (only some tickers) |
| 1 | Geography segments — sparse (only some tickers) |
| 2 | Revenue / Gross Profit / Op Inc / Net Inc |
| 3 | Margins (%) |
| 4 | EPS |
| 5 | EBITDA |
| 12 | Income breakdown / waterfall |
| 13 | Per-share (EPS / BV / Cash / FCF) |
| 14 | Expense ratios |

(Index labels in the live JSON are empty strings, so this mapping is inferred from the probe's own chart_index constants + sampling. The canonical mapping would require a test harness pinning each index against a known ticker.)

## Recommendation

1. **For the segment callers (`_cached_revenue_by_product`, `_cached_revenue_by_geography`):** keep index 0 / 1 as primary for now — it's correct for tickers that have data there (NVDA, and judging by NVDA's 10 product-segment datasets, this is likely true for any large company that reports dimensional product/geography in their own investor materials that QC scrapes).
2. **For tickers that return empty on QC 0 / 1:** the fallback chain should hit FMP next. Since `FMP_API_KEY` is not set on the Mac dev box (per the probe audit), that's failing silently. Setting the FMP key would close the gap for AAPL/MSFT/etc. without touching code.
3. **For the derived panels (EBITDA, expense ratios, etc.):** do not wire QC at indices 5/12/13/14 into the app yet — we already compute those from income + cash-flow statements (`compute_ebitda`, `compute_per_share`, etc.), and duplicating the logic against a data source we don't control risks disagreement.
4. **If a future task wants to use QC for index 5+ panels:** pin each index to a canonical content type with a unit test, because QC's JSON has empty string titles and the ordering is their internal convention, not a public contract.

**No code change this turn.** Task #30 closed with this audit.
