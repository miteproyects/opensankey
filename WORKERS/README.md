# WORKERS/ — per-worker briefs

One MD per active worker, named with the canonical name from `~/.qc-office/agents.json`.

Each brief is the **single source of truth** for that worker's:
- Scope (what they're allowed to touch)
- Owned files (lock-priority lanes)
- Active task list
- Open questions for `office` to route

When a worker reads `syncqc`, they read `CLAUDE.md` + `OFFICE.md` (read-once) + their own `WORKERS/<me>.md`. They do **not** read other workers' briefs unless arbitrating.

The orchestrator (`office`) is the only writer of these files. Workers write back via:
- **Q events** to ask `office` to update their brief.
- **D events** with `task_id` referencing entries in their own `## Tasks` section.

See `OFFICE.md` (root of repo) for the full spec.
