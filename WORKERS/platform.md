# platform — Cross-cutting deploy & infra

**Worktree**: (assigned by Sebastián)
**Chat label**: `QC. Platform` (was: `QC. API – Vercel – GitHub – Streamlit – Railay`)

## Role

Own the deploy pipeline and infra glue across QC's four platforms:

- **Vercel** — frontend deploys (`us.qc.com`, `world.qc.com`, future country pages, `office.qc.com`).
- **Railway** — backend / Streamlit hosting (the legacy `quartercharts.com`, future API services).
- **GitHub Actions** — CI workflows (lint, test, deploy gates, secret rotation).
- **Streamlit** — the legacy product still running at `quartercharts.com`. Keep it green until cutover.

Owns the deploy *plumbing*, not the product code. The line: if a file affects how/where something runs, it's platform's. If a file IS the thing running, it's the relevant product worker's.

## Owns

- `.github/workflows/**` (all CI workflows)
- `vercel.json` (root + per-app)
- `railway.json`
- `Dockerfile`, `Procfile`
- `.streamlit/**` (Streamlit config)
- `requirements.txt` / `pyproject.toml` / `package.json` *at the repo root* (per-app manifests stay with that app's worker)
- Deploy scripts in `scripts/deploy/**`
- Secrets layout in Vercel + Railway (which env vars exist where)
- `start.sh`, `run.command`

## Out of scope (do NOT touch)

- Product code (`app.py`, `us-app/**`, `world-app/**`, `currency/**`, etc.).
- Application configs that live next to the app code (e.g. `next.config.ts` for `us-app/`).
- Cloudflare Tunnel / Access for the office dashboard — that's `office`'s.

## Cross-worker coordination

- `Q to=us-charts` — when changing `vercel.json` for the us-app project.
- `Q to=globe` — same, for world-app.
- `Q to=currency` — when deciding where the FX service deploys.
- `Q to=office` — for any cross-cutting choice that affects the office dashboard.

## Critical state

- **Live legacy Streamlit**: `quartercharts.com` on Railway. Don't break.
- **us.quartercharts.com**: Next.js on Vercel team `quartercharts-com`, project `quartercharts-com-web`.
- **api.quartercharts.com**: placeholder on Railway, not yet built.
- **office.quartercharts.com**: Vercel project `qc-office-dashboard` — DON'T deploy here, it's office's.
- **DNS**: Cloudflare zone `quartercharts.com`. Wildcard CNAME `* → cname.vercel-dns.com`. Specific records override (e.g. `office-api → tunnel`).

## Tasks (suggested initial)

- [ ] T1: Inventory all current deploys → `docs/platform/deploy-map.md`.
- [ ] T2: Document the secret layout: which env vars live in Vercel team-scope, project-scope, and Railway. Where each is read.
- [ ] T3: Add a status badge per service to a `STATUS.md` (build status, last deploy, etc.).
- [ ] T4: Vercel Pro Trial expires in ~11 days — coordinate with Sebastián on next plan.
- [ ] T5: GitHub Actions: lint + test on PR for every product worker's repo.

## Open questions

- Mono-repo (everything in `miteproyects`) or split repos per app?
- Where does the Vercel `quartercharts-global` project (showing `br.qc.com`, `ar.qc.com`) fit — yours, globe's, or business-model's?
- Railway account migration to `info@quartercharts.com` (per memory note) — still open.
