# us-charts — Next.js frontend (us.quartercharts.com)

**Worktree**: `.claude/worktrees/kind-haslett-2451e3`
**Branch**: `claude/kind-haslett-2451e3`
**Chat label**: `1. US Charts`

## Role

Phase 1 frontend for `usa.quartercharts.com` pro-pro: Next.js 15 app router, Tailwind v4, shadcn/ui, TypeScript strict. Deployed on Vercel at `us.quartercharts.com` (the canonical US host per memory note).

## Owns

- `us-app/**`
- `vercel.json` (frontend deploy config)
- Frontend-only `tailwind.config.*`, `next.config.*`, `tsconfig.json` if scaffolded under `us-app/`

## Out of scope (do NOT touch)

- `api/**` — currency owns the backend.
- The Streamlit `app.py` — legacy product.
- `world-app/**` — globe + searching-tool live there.
- DNS — dns owns it.

## Reassignment note

Originally Currency and US Charts had the same brief ("scaffold FastAPI + Next.js"). Reassigned 2026-04-28: **us-charts = frontend only**. The FastAPI work is currency's lane.

## Tasks

- [ ] T1: Scaffold Next.js 15 + Tailwind v4 + shadcn + TS strict in `us-app/`.
- [ ] T2: Deploy to Vercel (private project, `info@quartercharts.com` login).
- [ ] T3: Stub home page (just the QC logo + a "coming soon" — logo worker will install the actual logo).
- [ ] T4: Wire `NEXT_PUBLIC_API_URL` env to `https://api.quartercharts.com`.
- [ ] T5: Coordinate with `logo` (Q event) when ready to receive the SVG header asset.
- [ ] T6: Coordinate with `searching-tool` for the home-page search widget.

## Open questions

- Same as currency: is this a private repo separate from `miteproyects`, or a folder inside it?
