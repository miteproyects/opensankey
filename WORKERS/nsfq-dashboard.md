# nsfq-dashboard — Worker

**Worktree (legacy/session)**: `.claude/worktrees/zealous-sanderson-bfd670`
**Branch (legacy/session)**: `claude/zealous-sanderson-bfd670`
**Chat label**: `QC. NSFQ Dashboard`
**Active orchestrator at scoping**: `qc/hq` (frosty-pascal-7bcfe6), 2026-05-03

## Role

Designs and implements the **Office Pricing admin** on the new stack — the FastAPI + Next.js + Postgres replacement for legacy `nsfe_page._render_pricing_admin` (Streamlit). First of 12 admin tabs the new `office.quartercharts.com` will host. V1 → V3 trajectory in `docs/office-pricing-design-v1.md` (currently in zealous-sanderson worktree pending move to `quartercharts.com/docs/`).

## Owns (multi-repo grant — see "Repo grants" below)

- `quartercharts.com/api/src/qc_api/routes/admin/pricing.py` (and downstream routes)
- `quartercharts.com/api/src/qc_api/routes/admin/me.py`
- `quartercharts.com/api/src/qc_api/auth/require_admin.py` (V1 auth dep)
- `quartercharts.com/db/migrations/versions/20260503_*` (Alembic migration)
- `quartercharts.com/db/seeds/pricing_v1.py` (bootstrap seed)
- `quartercharts.com/docs/office-pricing-design.md` (move target for the design doc)
- `qc-office-dashboard/src/app/pricing/**` (Next.js admin UI — granted in Phase B)
- `qc-office-dashboard/src/app/audit/**`

## Repo grants (managed by orchestrator)

The pre-tool-use lock-check hook blocks edits outside the registered worktree. nsfq-dashboard's session worktree is `zealous-sanderson-bfd670` (legacy `miteproyects`); implementation is in two separate repos. Granted **sequentially per PR phase**:

- **Phase A (PRs 1–5: schema + migration + API)**: `repo_worktree = ~/Desktop/OpenTF/quartercharts.com`, `repo_branch = feat/office-pricing`. Active 2026-05-03 onward.
- **Phase B (PRs 6–9: admin UI)**: orchestrator switches `repo_worktree` to `~/Desktop/OpenTF/qc-office-dashboard` and `repo_branch` to a new `feat/office-pricing-ui` branch when nsfq-dashboard signals "API endpoints merged, ready for UI."
- **Phase C (PR 10: public-side migration)**: orchestrator coordinates with `qc/sankey` / `qc/charts` (whichever owns the public surface) and grants temporary cross-team review access.
- **Phase D (PR 11: legacy decommission)**: handled by orchestrator + a designated cleanup pass; nsfq-dashboard's grant ends.

## Routing

- Questions to orchestrator: `Q to=qc/hq` events, or write to `~/.qc-office/inbox/hq.md`.
- Coordination with public-side workers (`qc/sankey`, `qc/charts`): `Q to=<name>` events, ping in MEETING room when needed for design review.
- Halt (blocked > 30 min): emit `H` event, surface to Sebastián.

## Open questions (carried forward from design doc Section 5)

- i18n strategy (V2 milestone)
- Currency-conversion display (V2)
- Plan recommendation engine (V3)
- Subscription-history schema (V3 / Stripe)
- Per-country tax handling (legal review needed before V3)

## Tasks (live)

- [x] T1: Draft `docs/office-pricing-design-v1.md` — done 2026-05-03 (in legacy worktree).
- [ ] T2: PR #1 — DB schema + Alembic migration + bootstrap seed in `quartercharts.com/`. Verify on Neon branch first.
- [ ] T3: PR #2 — `require_admin` + `users.is_admin` + `GET /v1/admin/me`.
- [ ] T4: PR #3 — Plan template CRUD + audit logging.
- [ ] T5: PR #4 — Plan country override CRUD.
- [ ] T6: PR #5 — Country config + chart-keys catalog + audit-read.
- [ ] T7: Move `docs/office-pricing-design-v1.md` from legacy → `quartercharts.com/docs/`.
- [ ] T8: Signal orchestrator to switch grant to qc-office-dashboard repo for UI phase.
