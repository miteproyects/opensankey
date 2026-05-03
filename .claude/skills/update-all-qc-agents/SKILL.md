---
name: update-all-qc-agents
description: All-hands re-orientation for the QC team. Gathers every live QC worker in the MEETING room, drops a fresh orientation packet to each agent's inbox (with the latest OFFICE.md / INFRASTRUCTURE.md / CLAUDE.md / each agent's WORKERS brief inlined), then returns them to their home rooms. Use after substantive doc changes that the entire QC team needs to absorb. Trigger on "/update-all-qc-agents", "update all QC agents", "all-hands re-orient QC", "broadcast new docs to QC team", "QC team re-onboard". Do NOT use for one-off messages to a single agent — for that, write directly to that agent's inbox.
---

# UpdateAllQCAgents — All-Hands Re-Orientation (QC team)

Procedural skill the QC orchestrator runs after updating any of the QC team's source-of-truth docs (`OFFICE.md`, `INFRASTRUCTURE.md`, `CLAUDE.md`, or anyone's `WORKERS/<name>.md`) to make sure every live QC worker re-reads the new versions on their next prompted turn.

> **Project boundary**: this skill targets QC workers ONLY. For BC, run `/update-all-bc-agents` instead. The two teams have different source docs and different scopes.
>
> **Concurrency guard**: do NOT run this skill while a previous run is still in progress. The 2026-05-03 V2 run started before V1's background patches finished, creating interleaved writes that produced random presence states. Check via `pgrep -f update-all-qc-agents` before starting; if anything matches, wait or kill it.

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

**Use atomic agents.json writes, not per-agent daemon patches** (lesson from the 2026-05-03 run that pegged the daemon doing 16 sequential patches). One atomic write moves all targets at once and avoids any backpressure that could push `/state` past Vercel's 3s proxy timeout.

**BEFORE writing, snapshot each target's original layout** so Phase 5 can restore exactly what was there:

```python
ORIGINAL = {
  n: {
    "presence":         agents[n].get("presence"),
    "pinned":           agents[n].get("pinned"),
    "presence_pinned":  agents[n].get("presence_pinned"),
  } for n in targets
}
```

Then perform a single atomic write that flips every target's presence to `"meetings"`:

```python
import json, pathlib
from datetime import datetime, timezone
p = pathlib.Path.home() / ".qc-office/agents.json"
d = json.loads(p.read_text())
for n in targets:
    m = d["agents"].get(n)
    if not m: continue
    m["presence"]        = "meetings"
    m["presence_pinned"] = True
d["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
p.write_text(json.dumps(d, indent=2))
```

The daemon's discovery loop reads `agents.json` and merges via `PRESERVE_IF_PRESENT` — your presence values survive the next sweep.

**Why not per-agent daemon patches?** During the 2026-05-03 V2 run, 17 sequential `/priority/patch (presence=meetings)` calls held the daemon's write lock long enough that concurrent `/state` requests started timing out, then crashed the daemon under launchd → respawn → repeat. Even after the orientation-drop fix (now async), atomic file writes are 100x faster (microseconds vs seconds) and bypass any potential daemon back-pressure entirely.

**Brief visual beat** after the write:

```python
import time; time.sleep(3)  # let dashboard render the MEETING gather
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

6. **Move targets to ORIENTATION room — single atomic agents.json write, not per-agent daemon patches.** After all inbox packets are written in steps 1–5, flip every target's `presence` to `"orientation"` in one go:

   ```python
   d = json.loads(p.read_text())
   for n in targets:
       m = d["agents"].get(n)
       if not m: continue
       m["presence"] = "orientation"
       m.pop("orientation_started_at", None)  # let daemon backdate via _backdated_stamp_for
   d["updated_at"] = now_iso()
   p.write_text(json.dumps(d, indent=2))
   ```

   The daemon's `_backdated_stamp_for` (Bug 2 fix from 2026-05-03) sets `orientation_started_at` on next discovery sweep. The orientation promotion loop won't fire mid-flow because we'll restore presences in Phase 5 within seconds, before the 60s ceiling.

   **Why not /priority/patch?** Each presence=orientation patch triggers `drop_orientation_packet` server-side which is now async (2026-05-03 fix), but it still holds the daemon's write lock briefly. 16 sequential patches still serialize. The atomic file write is microseconds. We've already written packets in steps 1–5 ourselves — the daemon's drop_orientation_packet would only re-do that work redundantly.

   **Visual beat**:
   ```python
   import time; time.sleep(5)  # agents render in ORIENTATION room
   ```

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

## Phase 5 — Restore original layout (atomic)

**Don't try to "force-clear" stragglers via /priority/patch sequences.** That's what failed in the V2 run. Instead, do one atomic agents.json write that restores every target to the layout snapshot you took in Phase 2:

```python
d = json.loads(p.read_text())
for n, orig in ORIGINAL.items():
    m = d["agents"].get(n)
    if not m: continue
    m["presence"]        = orig["presence"]
    m["pinned"]          = orig["pinned"] if orig["pinned"] is not None else True
    m["presence_pinned"] = orig["presence_pinned"] if orig["presence_pinned"] is not None else (orig["presence"] is not None and orig["presence"].startswith("custom-"))
    m.pop("orientation_started_at", None)  # avoid orientation loop firing post-restore
d["updated_at"] = now_iso()
p.write_text(json.dumps(d, indent=2))
```

This restores:
- **Custom rooms** (`presence="custom-..."`) — the user-defined rooms they were in before the gather
- **Built-in clusters** (`presence="charts-office"`, `"sankey-office"`, etc.) — explicit cluster placements
- **Coffee** (`presence="coffee"`) — agents that were on-break drift back to coffee
- **None / pin-routed** (`presence=null` + `pinned=true`) — agents that route via `clusterFor(name)` to their home cluster
- **Notes** (`presence="notes"`) — qc/notes (scratch role) was already excluded in Phase 1, but if it had been included, it would route home here

**Critical: do NOT shortcut to `presence="agent-ready"` for everyone.** `agent-ready` is a SYSTEM_PRESENCE marker that routes to the AGENT READY *room* unless the agent has both `pinned=true` AND a `KNOWN_DESKS` entry. Many QC agents lack `KNOWN_DESKS` entries (cloud-design, country-matrix, deepseek, research, robocounter, whatsapp at time of writing) and would land in the "default" corridor instead of their actual room. Restore EXACT original presences.

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
