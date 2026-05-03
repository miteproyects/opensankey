---
name: update-all-bc-agents
description: All-hands re-orientation for the BC (Blip.Company) team. Gathers every live BC worker in the MEETING room, drops a fresh orientation packet to each agent's inbox (with the latest BC source-of-truth docs and the agent's WORKERS brief inlined), then returns them to their home rooms. Use after substantive doc changes that the entire BC team needs to absorb. Trigger on "/update-all-bc-agents", "update all BC agents", "all-hands re-orient BC", "broadcast new docs to BC team", "BC team re-onboard". Do NOT mix with QC — BC has its own source docs and scope.
---

# UpdateAllBCAgents — All-Hands Re-Orientation (BC team)

Procedural skill the BC orchestrator runs after updating any of the BC team's source-of-truth docs to make sure every live BC worker re-reads the new versions on their next prompted turn.

> **Project boundary**: this skill targets BC workers ONLY. For QC, run `/update-all-qc-agents` instead. **BC and QC are separate projects with separate docs and separate scopes — never bridge them in a single re-orientation.**

## BC source docs that get inlined into the new orientation packet

> ⚠️ **The BC team's documentation is still maturing as of 2026-05-03.** Edit the list below as BC's docs get written. The skill is built to gracefully handle missing entries — any path in this list that doesn't exist on disk will be inlined as "(NOT YET WRITTEN — placeholder)".

Default paths to inline (relative to `~/Desktop/OpenTF/`, unless absolute):

- **`miteproyects/OFFICE.md`** — the SHARED coordination protocol. Same file QC reads, but the spec is team-agnostic so BC reads it too. (If/when BC forks its own coordination protocol, point this entry at the BC version and add a note to the rolling log.)
- **`Blip LLC/blip-company.md`** — BC's project-state file, analogous to QC's `CLAUDE.md`. **Path TBD until BC creates this.**
- **`Blip LLC/INFRASTRUCTURE.md`** — BC's infra map, analogous to QC's `~/Desktop/OpenTF/INFRASTRUCTURE.md`. **Path TBD until BC creates this.**
- **`miteproyects/WORKERS/<short_name>.md`** — the agent's personal brief. Today BC briefs live alongside QC briefs in the same `WORKERS/` directory; if BC moves to its own `WORKERS-BC/` directory, update this entry.

When BC creates its own `BLIP.md` / `BC_OFFICE.md` / etc., add them to this list and bump the rolling-log entry below.

## Pre-flight gates

Before doing anything, verify ALL of:

1. The caller (the chat running this skill) is the **active BC orchestrator**. Run:
   ```bash
   python3 -c "
   import json, pathlib
   d = json.loads((pathlib.Path.home()/'.qc-office/agents.json').read_text())
   for n, m in d.get('agents', {}).items():
       if m.get('team') == 'bc' and m.get('role') == 'orchestrator' and not m.get('is_archived'):
           print(n)
   "
   ```
   If the printed name doesn't match this chat's canonical name, abort with: "Only the active BC orchestrator can run /update-all-bc-agents. Active orchestrator is: <name>. Ask them to run it, or have Sebastián drag-promote you first."

   **Special case (2026-05-03)**: BC's office is currently DELETED (Sebastián's instruction "delete for now office BP. we will create a new office for BP later."). If there's no live BC orchestrator, abort with: "No active BC orchestrator. BC office is currently deleted; ask Sebastián to spin up a new BC orchestrator before running /update-all-bc-agents."

2. The daemon is reachable:
   ```bash
   curl -sS -m 3 http://127.0.0.1:8765/healthz
   ```
   Must print `ok`. If not, abort.

3. At least the SHARED `OFFICE.md` exists at `~/Desktop/OpenTF/miteproyects/OFFICE.md`. Each BC-specific path in the list above is best-effort — missing paths get a placeholder, they don't abort.

4. **Warn (non-blocking)** if any of the source docs that DO exist have uncommitted changes.

## Phase 1 — Discover targets

Read `~/.qc-office/agents.json` and select all agents matching ALL of:

- `team == "bc"`
- `is_archived == false`
- `role != "orchestrator"`
- `scope` does NOT start with `"DELETED "` (soft-deleted by Sebastián even when not archive-flagged — bc/office is currently in this state)

Apply `--exclude <name1>,<name2>` if the user passed it.

Print the final target list with a confirmation prompt:

```
About to re-orient N BC agents:
  - bc/<name1> (chat: "BC. <Label>", presence: <current>)
  - bc/<name2> ...
Source docs at this moment:
  miteproyects/OFFICE.md          last modified <ts>, <N> bytes
  Blip LLC/blip-company.md        (NOT YET WRITTEN)
  Blip LLC/INFRASTRUCTURE.md      (NOT YET WRITTEN)
Proceed? [yes/no]
```

If user says no, exit cleanly.

## Phase 2 — Gather in MEETING room

Identical to `/update-all-qc-agents` Phase 2, but with BC names. Record original presence per target.

## Phase 3 — Build + drop the new orientation packet for each agent

Identical procedure to `/update-all-qc-agents` Phase 3, with three differences:

1. **Source docs**: use the BC list at the top of this file. For each path that doesn't exist, inline `(NOT YET WRITTEN — placeholder, BC docs in flight)` instead of crashing.

2. **Header line in the packet** identifies it as a BC re-orientation:
   ```
   - `<ISO-8601-Z>` **From: <bc-orchestrator-name>** · **Topic: 🎓 Re-orientation packet — BC docs updated**
   ```

3. **Inline structure** uses BC-appropriate section names:
   ```
   ─── miteproyects/OFFICE.md (coordination protocol — shared with QC) ───
   <inlined>

   ─── Blip LLC/blip-company.md (BC project state) ───
   <inlined or "(NOT YET WRITTEN — placeholder)">

   ─── Blip LLC/INFRASTRUCTURE.md (BC infrastructure) ───
   <inlined or "(NOT YET WRITTEN — placeholder)">

   ─── WORKERS/<short_name>.md (your brief) ───
   <inlined or "(NOT YET WRITTEN)">
   ```

The sentinel-strip + sentinel-replant + presence-patch + stamp-clear logic is identical to the QC skill.

Print per-agent progress: `bc/<name>: gathered → packet dropped → in orientation`.

## Phase 4 — Wait for return-home

Identical to `/update-all-qc-agents` Phase 4. Poll `/state` for up to 90s (override via `--wait-seconds`). BC agents go through the same orientation-promotion-loop logic since the daemon is team-agnostic.

## Phase 5 — Force-clear stragglers

Identical to `/update-all-qc-agents` Phase 5.

## Phase 6 — Final report

Identical structure, but the rolling-log entry goes to BC's project-state file (when it exists) — NOT to QC's `CLAUDE.md`. If BC's project-state file doesn't yet exist, append the entry to `~/.qc-office/inbox/<bc-orchestrator-name>.md` so it's preserved until BC's docs catch up.

Example log entry:
```markdown
### YYYY-MM-DD — bc/<orchestrator>
- All-hands BC re-orientation via /update-all-bc-agents. Targeted N agents; M succeeded, K force-cleared, S skipped/errored. Source docs as of <iso>: miteproyects/OFFICE.md (xK bytes), Blip LLC/blip-company.md (NOT YET WRITTEN — placeholder).
```

## Safety properties

- **Non-destructive**: identical to the QC skill. Inbox-append-only + presence/stamp registry fields.
- **Idempotent**: identical.
- **Reversible**: identical — Phase 5 always lands every target on a stable presence.
- **Observable**: every patch fires a `D` event in the office event log, attributed to the BC orchestrator.
- **Authorization**: BC orchestrator-only (Pre-flight gate 1).
- **Project isolation**: this skill MUST NOT read, write, or reference QC source docs (`miteproyects/CLAUDE.md`, `~/Desktop/OpenTF/INFRASTRUCTURE.md`, etc.) other than the SHARED `OFFICE.md`. If you find yourself wanting QC content in a BC packet, stop — that's a sign BC needs its own version of that doc.

## Optional flags

- `--exclude bc/foo,bc/bar` — skip these agents.
- `--dry-run` — print the target list + source-doc summary, do nothing.
- `--wait-seconds <N>` — override the Phase 4 ceiling (default 90).
- `--memo "<one-liner>"` — prepend a memo to each agent's packet.

## What this skill does NOT do

- It does NOT touch QC team workers — that's `/update-all-qc-agents`.
- It does NOT auto-create missing BC source docs. If `Blip LLC/blip-company.md` doesn't exist, the packet contains a placeholder and the BC team is responsible for writing the doc.
- It does NOT bridge teams. If you want both teams re-oriented, run both skills sequentially. They share the daemon and the office event log but no other state.
- It does NOT page closed chats. Inbox content waits silently for the next user-prompted turn.

## Open follow-ups for BC

When BC stabilizes, replace these placeholder lines:

- [ ] Create `~/Desktop/OpenTF/Blip LLC/blip-company.md` (BC's analogue to `CLAUDE.md`).
- [ ] Create `~/Desktop/OpenTF/Blip LLC/INFRASTRUCTURE.md` (BC's infra map).
- [ ] Decide whether BC forks `OFFICE.md` or keeps the shared spec.
- [ ] Decide whether `WORKERS/` stays mixed-team or BC moves to `WORKERS-BC/` (and update Phase 3 path resolution accordingly).
- [ ] Spin up a live BC orchestrator (per Sebastián's "we will create a new office for BP later" plan). Until then, `/update-all-bc-agents` aborts at Pre-flight gate 1.
