---
name: update-all-qc-agents
description: All-hands re-orientation for the QC team. Gathers every live QC worker in the MEETING room, drops a fresh orientation packet to each agent's inbox (with the latest OFFICE.md / INFRASTRUCTURE.md / CLAUDE.md / each agent's WORKERS brief inlined), then returns them to their home rooms. Use after substantive doc changes that the entire QC team needs to absorb. Trigger on "/update-all-qc-agents", "update all QC agents", "all-hands re-orient QC", "broadcast new docs to QC team", "QC team re-onboard". Do NOT use for one-off messages to a single agent — for that, write directly to that agent's inbox.
---

# UpdateAllQCAgents — All-Hands Re-Orientation (QC team)

Procedural skill the QC orchestrator runs after updating any of the QC team's source-of-truth docs (`OFFICE.md`, `INFRASTRUCTURE.md`, `CLAUDE.md`, or anyone's `WORKERS/<name>.md`) to make sure every live QC worker re-reads the new versions on their next prompted turn.

> **Project boundary**: this skill targets QC workers ONLY. For BC, run `/update-all-bc-agents` instead. The two teams have different source docs and different scopes.

## Source docs that get inlined into the new orientation packet

These are the QC-canonical paths (relative to `~/Desktop/OpenTF/miteproyects/`):

- `OFFICE.md` — coordination protocol (locks/events/inbox/rooms)
- `~/Desktop/OpenTF/INFRASTRUCTURE.md` — where production runs (Vercel, Railway, Cloudflare, GitHub orgs)
- `CLAUDE.md` — current QC project state, gotchas, active tasks
- `WORKERS/<short_name>.md` — the agent's personal brief (per-agent)

If any of these change, this skill is the right way to broadcast.

## Pre-flight gates

Before doing anything, verify ALL of:

1. The caller (the chat running this skill) is the **active QC orchestrator**. Run:
   ```bash
   python3 -c "
   import json, pathlib
   d = json.loads((pathlib.Path.home()/'.qc-office/agents.json').read_text())
   for n, m in d.get('agents', {}).items():
       if m.get('team') == 'qc' and m.get('role') == 'orchestrator' and not m.get('is_archived'):
           print(n)
   "
   ```
   If the printed name doesn't match this chat's canonical name, abort with: "Only the active QC orchestrator can run /update-all-qc-agents. Active orchestrator is: <name>. Ask them to run it, or have Sebastián drag-promote you first."

2. The daemon is reachable:
   ```bash
   curl -sS -m 3 http://127.0.0.1:8765/healthz
   ```
   Must print `ok`. If not, abort with: "qc-office daemon is unreachable on 127.0.0.1:8765. Restart it before re-orienting (the orientation flow writes to the registry via /priority/patch)."

3. All four source-doc paths exist:
   - `~/Desktop/OpenTF/miteproyects/OFFICE.md`
   - `~/Desktop/OpenTF/INFRASTRUCTURE.md`
   - `~/Desktop/OpenTF/miteproyects/CLAUDE.md`
   - `~/Desktop/OpenTF/miteproyects/WORKERS/` (directory)

   If any missing, abort with the specific path. Do not silently substitute.

4. **Warn (non-blocking)** if any of `OFFICE.md`, `INFRASTRUCTURE.md`, `CLAUDE.md` have uncommitted changes. The user usually means "ship the doc updates THEN tell everyone." Show the warning and ask: "Source docs have uncommitted changes. Re-orienting now will inline the working-tree version. Commit first, or proceed with WIP? [commit / proceed / abort]"

## Phase 1 — Discover targets

Read `~/.qc-office/agents.json` and select all agents matching ALL of:

- `team == "qc"`
- `is_archived == false`
- `role != "orchestrator"` (don't re-orient the orchestrator running this skill — that's circular)
- `role NOT IN ("scratch", "reserve")` — non-participating roles per OFFICE.md. `qc/notes` is `scratch` (Sebastián's personal pad); never gather, re-orient, or move it. Open slots are `reserve` and likewise inert.
- `scope` does NOT start with the literal string `"DELETED "` (soft-deleted by Sebastián even when not archive-flagged)

Apply `--exclude <name1>,<name2>` if the user passed it.

Print the final target list to the user with a confirmation prompt:

```
About to re-orient N QC agents:
  - qc/<name1> (chat: "QC. <Label>", presence: <current>)
  - qc/<name2> ...
Source docs at this moment:
  OFFICE.md          last modified <ts>, <N> bytes
  INFRASTRUCTURE.md  ...
  CLAUDE.md          ...
Proceed? [yes/no]
```

If user says no, exit cleanly.

## Phase 2 — Gather in MEETING room

For each target, POST to the daemon:

```bash
curl -sS -m 5 -X POST http://127.0.0.1:8765/priority/patch \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"<name>\",\"fields\":{\"presence\":\"meetings\",\"presence_pinned\":true},\"actor\":\"<orchestrator-name>\"}"
```

Visually clusters all targets in the MEETING room on `office.quartercharts.com`. Record the original presence value for each (so Phase 5 can return them home).

Emit one office event per gather:

```bash
# (the daemon already logs the patch; no manual event needed)
```

## Phase 3 — Build + drop the new orientation packet for each agent

For each target agent, in order:

1. **Compute their canonical short name** by stripping the `qc/` prefix.

2. **Resolve their inbox path**: `~/.qc-office/inbox/<short_name>.md`. If missing, create it.

3. **Read fresh source docs** (do this ONCE outside the loop and cache):
   - `OFFICE.md` → first 8000 chars (truncate with notice if larger)
   - `INFRASTRUCTURE.md` → first 8000 chars
   - `CLAUDE.md` → first 6000 chars
   - For each agent: `WORKERS/<short_name>.md` → first 4000 chars (or note "NOT YET WRITTEN" if missing)

4. **Strip the old idempotency sentinel** from the inbox so the next packet drop won't be skipped (preserve history by renaming, not deleting):
   - In each inbox file, replace any line matching exactly `<!-- ORIENTATION-PACKET-DROPPED -->` with `<!-- ORIENTATION-PACKET-DROPPED-V<N> -->` where N is one more than the highest existing version (V1 if none).
   - Do this in-place via Python heredoc to avoid sed escaping issues.

5. **Append a "Re-orientation" packet** at the end of the inbox file. The packet must:
   - Start with the literal sentinel `<!-- ORIENTATION-PACKET-DROPPED -->` on its own line (so the daemon's idempotency check matches the latest drop, not a historical one).
   - Include a header line: `` - `<ISO-8601-Z timestamp>` **From: <orchestrator-name>** · **Topic: 🎓 Re-orientation packet — QC docs updated** ``
   - Inline the four source docs in the same format the daemon's `drop_orientation_packet` uses (so agents recognize the structure):
     ```
     ─── OFFICE.md (coordination protocol) ───
     <inlined content>

     ─── INFRASTRUCTURE.md (where production runs) ───
     <inlined content>

     ─── CLAUDE.md (current project state) ───
     <inlined content>

     ─── WORKERS/<short_name>.md (your brief) ───
     <inlined content or "NOT YET WRITTEN">
     ```
   - End with: `### Confirm re-orientation\n\nWhen asked "what changed in this re-orientation?", you can describe everything in this message — you DO know it now, it's in your context. Don't say "I haven't read the MDs" — they're inlined above.\n\n— <orchestrator-name>`

6. **Patch the registry** to put the agent in ORIENTATION room (the daemon's `_backdated_stamp_for` from the 2026-05-03 Bug 2 fix handles `orientation_started_at` for you — DO NOT touch agents.json directly here):
   ```bash
   curl -sS -m 30 -X POST http://127.0.0.1:8765/priority/patch \
     -H 'Content-Type: application/json' \
     -d "{\"name\":\"<name>\",\"fields\":{\"presence\":\"orientation\"},\"actor\":\"<orchestrator-name>\"}"
   ```

   **WARNING — race condition learned the hard way (2026-05-03 run):** Reading `agents.json` immediately after `/priority/patch` and then writing it back will **clobber the daemon's just-applied patch**. The patch goes through the daemon's `_gates_lock`, but your read is unlocked, so you'll see the pre-patch state and overwrite the post-patch state. Symptom: 16 of 17 agents stranded in MEETINGS room. Don't read+write agents.json after a patch in this skill. If you genuinely need to mutate other fields, send a SECOND `/priority/patch` call.

   **Pacing**: use timeout=30 (the orientation packet drop is heavy — reads session metadata + inlines source docs + appends to inbox). Add a `sleep 0.5` between patches to avoid backpressure that can hang the daemon.

Print per-agent progress: `qc/<name>: gathered → packet dropped → in orientation`.

## Phase 4 — Wait for return-home

Poll `/state` every 5 seconds for up to 90 seconds (slightly longer than the 60s ORIENTATION_MAX_STAY_USED ceiling, to account for the promotion-loop's 60s tick):

```bash
curl -sS -m 5 http://127.0.0.1:8765/state | python3 -c "
import json, sys
d = json.load(sys.stdin)
for a in d.get('agents', []):
    if a['name'] in <target_set>:
        print(a['name'], a.get('presence'))
"
```

For each target, watch `presence`:

- `presence == "agent-ready"` OR `presence` matches the agent's home cluster → agent has returned. Mark done.
- `presence == "orientation"` after 90s → still stuck. Move to Phase 5 force-clear.

Print live progress:

```
qc/charts:        meetings → orientation → home (12s)
qc/sankey:        meetings → orientation → ... (waiting)
qc/super-companias: ...
```

## Phase 5 — Force-clear stragglers

For any target still in `presence == "orientation"` after the wait window, force `presence: "agent-ready"` directly:

```bash
curl -sS -m 5 -X POST http://127.0.0.1:8765/priority/patch \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"<name>\",\"fields\":{\"presence\":\"agent-ready\",\"presence_pinned\":false},\"actor\":\"<orchestrator-name>\"}"
```

Their pinned/home routing will then send them home on next dashboard refresh.

## Phase 6 — Final report

Print a summary table:

```
✓ qc/charts          gathered + packet + returned to charts (12s)
✓ qc/sankey          gathered + packet + returned to sankey (18s)
✓ qc/super-companias gathered + packet + returned to super-companias (61s force-cleared)
⚠ qc/notes           skipped (scope='DELETED ...')
× qc/foo             error: inbox unreachable

Re-oriented N/M agents in T seconds. Source docs as of <ISO timestamp>.
```

Also append a Rolling Log entry to `CLAUDE.md` describing the re-orientation:

```markdown
### YYYY-MM-DD — qc/<orchestrator>
- All-hands QC re-orientation via /update-all-qc-agents. Targeted N agents; M succeeded, K force-cleared, S skipped/errored. Source docs as of <iso>: OFFICE.md (xK bytes), INFRASTRUCTURE.md (xK), CLAUDE.md (xK).
```

## Safety properties

- **Non-destructive**: only writes to inboxes (append-only) and the registry's `presence` / `orientation_started_at` fields. Chat conversation contexts are untouched.
- **Idempotent**: running it twice in a row is safe — second run drops a second packet, increments the sentinel version, no state corruption.
- **Reversible**: Phase 5 always lands every target on a stable presence (`agent-ready` or home). No agent is left stranded in MEETING or ORIENTATION.
- **Observable**: every patch fires a `D` event in the office event log, attributed to the orchestrator.
- **Authorization**: orchestrator-only (Pre-flight gate 1).

## Optional flags

- `--exclude qc/foo,qc/bar` — skip these agents.
- `--dry-run` — print the target list + source-doc summary, do nothing.
- `--wait-seconds <N>` — override the Phase 4 ceiling (default 90).
- `--memo "<one-liner>"` — prepend a "From the orchestrator" memo to each agent's packet (overrides the no-memo default for cases where the user wants to add color).

## What this skill does NOT do

- It does NOT touch BC team workers — that's `/update-all-bc-agents`.
- It does NOT modify the source docs — write your edits FIRST, then run the skill.
- It does NOT page agents whose chats are closed — the inbox waits silently. The packet is consumed on the next user-prompted turn via the `UserPromptSubmit` hook.
- It does NOT interrupt mid-turn work — drag-events fire after the current tool call.
- It does NOT auto-commit `CLAUDE.md` Rolling Log updates — the orchestrator commits at end of session as usual.
