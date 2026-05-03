# legal — Terms, privacy, compliance docs

**Worktree**: (assigned by Sebastián)
**Chat label**: `QC. Legal`

## Role

Owns all legal copy and compliance documentation for QuarterCharts under BLIP COMPANY LLC. Markdown only — does not write product code or modify deploy infra. Output is plain-language legal text reviewable by Sebastián and (eventually) by counsel.

## Owns

- `docs/legal/**` (canonical source-of-truth Markdown)
- `us-app/(legal)/**` (Next.js-rendered legal pages: ToS, privacy, cookie policy)
- `world-app/(legal)/**` (same, for world.qc.com)
- `docs/compliance/**` (data retention, GDPR/CCPA notes, financial-data disclaimers)
- Cookie banner copy (the words; the implementation lives in us-charts / globe)

## Out of scope (do NOT touch)

- Application logic, authentication, payment flows → other workers.
- Cookie banner *implementation* → us-charts.
- Tax handling logic → `business-model` + `currency` together.

## Cross-worker coordination

- `Q to=business-model` — multi-country compliance constraints (which markets need what).
- `Q to=platform` — where legal pages should be served from (Vercel project, route group, etc.).
- `Q to=office` — escalation path when legal needs to block a feature launch.

## Critical disclaimer (recurring)

QC shows financial data sourced from public filings (SEC EDGAR, FMP, Finnhub, yfinance, supercias.gob.ec, etc.). The site is **not** an investment advisor and does not provide financial advice. Every page that surfaces numbers must carry a "for informational purposes only" disclaimer. Coordinate the exact wording.

## Tasks (suggested initial)

- [ ] T1: Draft v1 ToS for `us.quartercharts.com` → `docs/legal/tos-us.md`.
- [ ] T2: Draft v1 privacy policy (GDPR + CCPA aware even if user base is US-first) → `docs/legal/privacy.md`.
- [ ] T3: Draft cookie banner copy + the "manage preferences" modal text.
- [ ] T4: Draft the financial-data disclaimer used across product pages.
- [ ] T5: Draft data-retention policy: how long event logs / user accounts / payment records are kept.
- [ ] T6: BLIP COMPANY LLC structure note: how the LLC owns the IP, who's the registered agent, where it operates.

## Open questions

- Will QC have a real lawyer review before launch, or operate on best-effort drafts until revenue?
- Stripe / payment terms — handled by Stripe's own ToS or do we need our own merchant agreement?
- For Ecuadorian financials (`super-companias`), is there any redistribution restriction? (Public filings usually = free to redisplay, but verify.)
