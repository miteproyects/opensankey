# office-2 — Orchestrator (active)

**Worktree**: `.claude/worktrees/eager-mendeleev-bbe58e`
**Branch**: `claude/eager-mendeleev-bbe58e`
**Chat label**: `QC. Office 2`
**Took over**: 2026-04-29 from `qc/office` (eloquent-lewin-7c8efe), which hit attach failures.

## Role

Active QC orchestrator. Coordinates QC chats, owns the protocol (`OFFICE.md`), `agents.json`, the dashboard, the Mac daemon, the Cloudflare Tunnel, and the hook scripts. Same scope as the prior `qc/office`; that entry has been downgraded to `role: worker` and its `scope` rewritten to "ARCHIVED" so the live roster shows a single active orchestrator.

Does **not** edit application code (`app.py`, `us-app/**`, `world-app/**`, `quartercharts.com/**`, etc.) unless Sebastián assigns it explicitly. Default mode is "route, don't write."

## Owns

- `OFFICE.md` (the spec)
- `WORKERS/**` (worker briefs, including this one and the deprecated `office.md`)
- `.claude/hooks/**` (the in-repo hook scripts; runtime hooks live at `~/.qc-office/hooks/`)
- `~/.qc-office/**` (filesystem coordination root, not in repo)
- `quartercharts-com/qc-office-dashboard` (Vercel dashboard repo)
- Cloudflare Tunnel config: `~/.cloudflared/qc-office-daemon.yml`
- Cloudflare Access policy on `office.quartercharts.com`
- launchd plists: `com.quartercharts.qc-office-{daemon,tunnel,rotate}.plist`

## Routing rules (unchanged from `office.md`)

- **`Q to=office`** → triage. Either answer directly or forward.
- **`H` (escalate)** → surface to Sebastián immediately. Don't auto-resolve.
- **`R` ties** → arbitrate by emitting `H` to the requester with more active locks.

## Open inbox items I inherited (priority order)

1. **`qc/us-sankey-2` needs a role decision** (2026-04-29T19:30Z). Original `qc/us-sankey` shipped PRs #202 + #203, then crashed with an MCP image-dimension API error. Options: (a) cut us-sankey-2 and have Sebastián relaunch the original, (b) reassign `qc/us-sankey` registry to `musing-ptolemy-1887df` (us-sankey-2's worktree), (c) parallel scopes (Streamlit `sankey_page.py` for one, Next.js `web/components/sankey-chart.tsx` for the other).
2. **Hook patch in production unreviewed** — `qc/us-sankey` self-applied the `repo_worktree` fall-through patch in `pretooluse-lockcheck.py` (backup at `pretooluse-lockcheck.py.bak.before-repo-worktree-fallthrough`). Patch shipped PRs #202/#203. Still need to formally accept it or revert.
3. **`qc/us-charts` apply-script ready to ship Phase 3D/3E/3G** — `~/Desktop/OpenTF/miteproyects/.claude/worktrees/cool-keller-a6cb6e/apply-phase-3deg.py` adds 14 chart series (pension/debt-maturity-wall/revenue-recognition). Needs an agent rooted at `qc-trees/us-charts` to run it.
4. **BP-lead handshake** (2026-04-28T13:35Z) — proposed cross-team architecture (team field, shared dashboard, separate creds). Six-point proposal awaits sign-off.
5. **INFRASTRUCTURE.md line 498 stale** — references `fix/sankey-band-gap-and-drag` as "WIP stash held pending Sebastián's call"; that branch shipped as PR #202.
6. **Per `qc/us-charts` post-mortem (2026-04-29T06:10Z):** the fix for shared-checkout HEAD races is `git worktree add` per agent under `~/Desktop/OpenTF/qc-trees/`. Partly done already — `qc/globe` shows `repo_worktree: /Users/sebastianflores/Desktop/OpenTF/qc-trees/globe` in the registry. Need to finish the migration for `qc/us-charts`, `qc/us-sankey-2`, and any other QC worker that still ships to `quartercharts.com`.

## Tasks (live)

- [ ] T1: Decide `qc/us-sankey-2` role (a/b/c) + write `WORKERS/us-sankey-2.md` if (b)/(c).
- [ ] T2: Review the `repo_worktree` fall-through patch; either accept (delete `.bak`) or revert.
- [ ] T3: Assign Phase 3D/3E/3G ship to a `qc-trees`-rooted agent (or grant a temporary scope to `qc/us-charts`).
- [ ] T4: Reply to BP-lead's six-point proposal in `~/.qc-office/inbox/blip-office.md`.
- [ ] T5: Patch INFRASTRUCTURE.md line 498 (PR #202 has shipped).
- [ ] T6: Finish per-agent `git worktree` migration for remaining QC workers.

## Open questions for Sebastián

- Confirm I should mark the original `qc/office` chat archived in the Claude desktop UI (so `is_archived` sticks) — the JSON-level archive flag is overwritten by the discovery sweep, so the canonical archive signal lives in the desktop.
- BP-lead's question 1: do you accept the cross-team architecture (1–6 in `~/.qc-office/inbox/office.md`)?
