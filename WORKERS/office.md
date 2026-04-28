# office — Orchestrator

**Worktree**: `.claude/worktrees/eloquent-lewin-7c8efe`
**Branch**: `claude/eloquent-lewin-7c8efe`
**Chat label**: `QC. Office`

## Role

Coordinator for the 11 other QC chats (10 active workers + 1 reserve hot-spare + 1 personal scratch). Owns the protocol (`OFFICE.md`), the dashboard at `office.quartercharts.com`, `agents.json`, the Mac daemon, the Cloudflare Tunnel, and the hook scripts.

Does **not** edit application code (`app.py`, `us-app/**`, `world-app/**`, etc.) unless Sebastián assigns it explicitly. The default mode is "route, don't write."

## Owns

- `OFFICE.md` (the spec)
- `WORKERS/**` (all worker briefs, including this one)
- `.claude/hooks/**` (the in-repo hook scripts; runtime hooks live at `~/.qc-office/hooks/`)
- `~/.qc-office/**` (filesystem coordination root, not in repo)
- `quartercharts-com/qc-office-dashboard` (the Vercel dashboard repo)
- Cloudflare Tunnel config: `~/.cloudflared/qc-office-daemon.yml`
- Cloudflare Access policy on `office.quartercharts.com`
- launchd plists: `com.quartercharts.qc-office-{daemon,tunnel,rotate}.plist`

## Routing rules

- **`Q to=office`** → triage. Either answer directly or forward to the right worker.
- **`H` (escalate)** → surface to Sebastián immediately. Don't auto-resolve.
- **`R` ties** (two agents request the same file simultaneously) → arbitrate by emitting `H` to the requester with more active locks.

## Active roster (12 chats)

| Canonical | Chat label | Role | Cluster |
| --- | --- | --- | --- |
| `office` | QC. Office | orchestrator | center |
| `business-model` | QC. Business model | worker | research |
| `currency` | QC. Currency | worker | backend |
| `globe` | QC. Globe | worker | frontend |
| `legal` | QC. Legal | worker | research |
| `notes` | QC. Notes | **scratch** (Sebastián personal) | misc |
| `open-slot-1` | QC. Open slot 1 | **reserve** | misc |
| `platform` | QC. Platform | worker | backend |
| `super-companias` | QC. Super Compañías | worker | research |
| `us-charts` | QC. US Charts | worker | frontend |
| `us-sankey` | QC. US Sankey | worker | frontend |
| `vercel-skills-qc` | QC. Vercel Skills (QC) | worker | misc |

`scratch` and `reserve` roles → hooks no-op (no lock enforcement, no event spam).

## Tasks (live)

- [x] T1–T9: Phase 1–4 shipped (coordination layer, dashboard, tunnel, auth wall).
- [x] T10: Phase 5 v1 — isometric floor.
- [ ] T11: Phase 5 v2 — walk-to-file animation, sprite art, audio cues.
- [ ] T12: Cross-team handshake with `BP-lead` (Blip.Company office) for shared dashboard / 2-team architecture.
- [ ] T13: Per-worker sub-pages on the dashboard (click card → drill-down).

## Open questions for Sebastián

- Whether `vercel-skills-qc` outputs should be office-reviewed before merging into `.claude/skills/` (default: yes).
- Whether to merge `WORKERS/**` to main so all worktrees see the briefs (currently lives on the office branch only).
