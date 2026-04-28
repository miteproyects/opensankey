# business-model — Multi-country biz model & docs

**Worktree**: `.claude/worktrees/gallant-swartz-5ac5a7`
**Chat label**: `QC. Business model`

## Role

Define the business model for the multi-country expansion of QuarterCharts. **Output is documents, not code.** Owns the canonical product model: `world.qc.com` (landing) → per-country pages (`us.qc.com`, `ec.qc.com`, `mx.qc.com`, …) → ticker pages. Defines paywall tiers per market, the acquirer narrative for BLIP COMPANY LLC, and pricing strategy.

## Owns

- `docs/business-model/**`
- `docs/pricing/**`
- `docs/market-research/**`
- `docs/acquirer-narrative/**`

## Out of scope (do NOT touch)

- All application code (read-only).
- DNS / infra (`platform` worker owns).
- Legal copy itself (`legal` worker owns; coordinate via `Q to=legal` for compliance touchpoints).

## Cross-worker coordination

- `Q to=globe` — which countries to show as "live" vs "coming soon" on the world map.
- `Q to=super-companias` — EC-specific data-source strategy.
- `Q to=legal` — compliance constraints for new markets.

## Tasks (suggested initial)

- [ ] T1: Document the page hierarchy: world.qc → country.qc → ticker page → `docs/business-model/site-map.md`.
- [ ] T2: Per-country pricing strategy, US + EC + MX first → `docs/pricing/per-country.md`.
- [ ] T3: Acquirer narrative one-pager — why QC is acquirable, who the natural buyers are, what's needed to be ready (revenue, TAM, differentiation) → `docs/acquirer-narrative/v1.md`.
- [ ] T4: Define legal entity flow: BLIP COMPANY LLC owns all domains/payments per memory note → `docs/business-model/legal-structure.md`.

## Open questions

- Will country pages share auth/account, or per-country accounts?
- Stripe — one Stripe account per country (for tax compliance) or one global with VAT/IGV/IVA logic?
- When does QC start charging (free-tier sunset date)?
