# currency — FX / currency conversion layer

**Worktree**: `.claude/worktrees/lucid-khayyam-9b0a8c`
**Chat label**: `QC. Currency`

## Role

The financial-currency-conversion layer used across QC. Converts all financial values between USD and the local currency of whichever country the user is viewing. Provides a single shared library + (optional) microservice that every other front-end / back-end worker calls.

**Note**: this scope reflects the 2026-04-28 reassignment. The earlier "Phase 1 FastAPI backend" scope moved to the new `platform` worker. Currency is now data, not infra.

## Owns

- `currency/**` (the conversion library)
- `lib/fx/**` (alternative path, depending on directory layout chosen)
- `currency/sources/**` (FX rate provider adapters: ECB, OpenExchangeRates, fallbacks)
- `currency/cache/**` (rate caching policy)
- Tests for the above

## Out of scope (do NOT touch)

- Streamlit / FastAPI / Vercel deploy plumbing → `platform` worker owns.
- Country-specific data extraction (e.g. Ecuadorian financials) → `super-companias` for EC, future workers for other countries.
- UI presentation of FX-converted numbers → owned by whichever frontend (`us-charts`, `globe`, etc.) consumes the library.

## Cross-worker coordination

- `Q to=super-companias` — what currency are EC raw values in (USD-denominated since Ecuador is dollarized, but verify)?
- `Q to=us-charts` — how to surface the "values shown in $X" indicator in the UI.
- `Q to=business-model` — pricing tier policy for currency-aware features.

## API surface (proposed, for review)

```
convert(amount: number, from: ISO4217, to: ISO4217, asOf?: date): number
historicalRate(from: ISO4217, to: ISO4217, asOf: date): number
preferredCurrencyForUser(userCountryCode): ISO4217
```

## Tasks (suggested initial)

- [ ] T1: Pick the FX rate source(s). ECB (free, daily) + OpenExchangeRates (free tier, hourly) is a reasonable starting combo. Document in `docs/currency/sources.md`.
- [ ] T2: Build the conversion library with rate caching + fallbacks.
- [ ] T3: Build a tiny FX rate-fetcher daemon or scheduled job (coordinate with `platform`).
- [ ] T4: Integrate into us-charts via `Q` exchange.

## Open questions

- Where does the library live: `miteproyects` repo, separate repo, or shared via npm/PyPI? (Defer to office for cross-cutting infra decisions.)
- Should it be a Python library, a TS library, or both? (Different consumers want different runtimes.)
