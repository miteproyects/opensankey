# super-companias — Ecuador SuperCompañías data extractor

**Worktree**: `.claude/worktrees/crazy-kilby-d4c673`
**Branch**: `claude/crazy-kilby-d4c673`
**Chat label**: `1. Super Compañías`

## Role

Reverse-engineer `tfcsmart.com` to understand how it pulls Ecuadorian financial-statement data from the SuperCompañías. Build a Python extractor that pulls income / balance / cashflow / key-metrics for the top-10 EC companies by total assets. This feeds a future `ec.quartercharts.com` country page.

## Owns

- `ecuador/**` (all extractor code)
- `docs/ecuador/**` (research notes, scraped XBRL samples)
- `tests/ecuador/**`

## Out of scope

- US data sources — those live in `data_fetcher.py` (currency / streamlit will keep using SEC/FMP/Finnhub).
- `app.py` — the legacy Streamlit product.
- DNS / Vercel — different workers.

## Notable

This worker has the **only enlarged `CLAUDE.md`** (57K bytes vs 30K baseline). It contains worker-specific research notes that haven't been consolidated yet. **Don't flatten it** without reading first.

## Tasks

- [ ] T1: Document tfcsmart.com's data flow (network requests, auth, endpoints) — research output goes to `docs/ecuador/tfcsmart-flow.md`.
- [ ] T2: Identify the SuperCompañías public endpoint(s) tfcsmart hits.
- [ ] T3: Pick top-10 EC companies by assets (manual list, validate against SuperCompañías 2024 ranking).
- [ ] T4: Build extractor → JSON-per-company in `ecuador/data/`.
- [ ] T5: Coordinate with `business-model` for the `ec.qc.com` page-design brief.

## Open questions

- Which SuperCompañías portal version? (Old `supercias.gob.ec`, new `appscvs.supercias.gob.ec`, or the API?)
- Spanish-language data — translate field names to EN, or keep ES?
