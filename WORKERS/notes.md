# notes — Sebastián's personal scratch pad

**Worktree**: (assigned by Sebastián)
**Chat label**: `QC. Notes`
**Role**: `scratch` — NOT a regular worker.

## What this is

A free-form chat where Sebastián captures product / strategy / architecture ideas for future implementation. Markdown notebook lives here.

## Critical rules (different from regular workers)

- **Hooks no-op for this chat.** No lock enforcement, no S/D event broadcasting, no inbox surfacing. Sebastián's scratch shouldn't pollute the office event log or block other workers.
- **No `R` / `Y` / `Q` / `A` events from this chat.** It doesn't participate in the protocol.
- **Other workers should NOT message this chat.** Treat it as Sebastián-only. If a worker thinks it has something `notes` should know, route through `office` instead.
- **No production code.** Output is `docs/notes/**` Markdown only.

## Owns

- `docs/notes/**` (idea log, future-feature sketches, half-formed thoughts)

## How office handles this worker

- `agents.json` carries `role: scratch`.
- Dashboard renders the card with a quieter style (low-saturation, no pulsing).
- Lockcheck hook short-circuits before any enforcement when the agent's role is `scratch`.
- Discovery still surfaces it (so Sebastián sees it on the dashboard) but skips it from "active worker" counts.

## When notes graduates to a real worker

If a notes idea becomes a real initiative:
1. Sebastián renames the chat from `QC. Notes` to `QC. <NewName>` (or creates a fresh chat).
2. The original `QC. Notes` keeps existing for new ideas.
3. The new worker gets a real `WORKERS/<new-name>.md` brief and `agents.json` entry.

## Index

(Sebastián fills this as ideas accumulate.)

- *(empty)*
