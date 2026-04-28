# open-slot-1 — Hot-spare worker (reserve)

**Worktree**: (assigned when activated)
**Chat label**: `QC. Open slot 1`
**Role**: `reserve` — empty slot, no scope yet.

## What this is

A pre-allocated chat that Sebastián can activate when a new worker is needed. Living infrastructure (lives in the dashboard, has a desk in the isometric office) but no real responsibilities until repurposed.

## Critical rules

- **Hooks no-op.** Same as `notes` — no lock enforcement, no event broadcasting.
- **No tasks, no ownership.** This chat does not edit code, run scripts, or coordinate with anyone.
- **No peer messages.** Other workers should NOT message `open-slot-1`. If a need arises, escalate to `office`.

## How to activate this slot

When Sebastián wants to spin up a new worker (e.g. "we need a `mx-charts` worker for Mexico"):

1. Sebastián renames the chat from `QC. Open slot 1` to `QC. <NewName>`.
2. Discovery picks up the new title within ~10s (`discover-agents.py` runs every cycle).
3. `office` writes a `WORKERS/<new-name>.md` brief based on Sebastián's intent.
4. `office` updates `agents.json` with `role: worker`, `scope`, `owns_files`.
5. Hooks start enforcing locks for the new worker on its next session.

## How office renders this on the dashboard

- Card shows in a "reserve" cluster (slate color), faded.
- Counts as 0 in the "active workers" header tally.
- Lock count always 0.
- Last-seen / state still tracked (so we can see if Sebastián opens the chat) but doesn't trigger event-log entries.

## When to add a second open slot

If `open-slot-1` is chronically activated (every new worker uses it), Sebastián can create `QC. Open slot 2` and beyond. The dashboard will show all reserves automatically.
