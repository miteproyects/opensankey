# OFFICE.md — Multi-Worker Coordination Spec for QuarterCharts

This is the design spec for the parallel-Claude-Code setup. Read this once, refer back when conflicts surface, never paste into prompts (it's for humans + the orchestrator, not workers).

> **Live roster**: see `~/.qc-office/agents.json` (auto-discovered every ~10s by `~/.qc-office/hooks/discover-agents.py`). The chat count churns as Sebastián spins up new workers and archives old ones — the `agents.json` registry is the source of truth, not any list in this doc.

---

## Why this exists

Sebastián runs ~10–15 parallel Claude Code chats (pinned `QC.*`, formerly `1.*`) across separate git worktrees of `miteproyects`. Each chat is an independent Claude process with its own context window. They share one filesystem and one git repo, so without coordination they'd:

1. Edit the same file simultaneously and overwrite each other.
2. Duplicate work (e.g., Currency and US Charts originally had the same brief).
3. Hold stale information about what peers have already done.
4. Burn tokens narrating intent in human English.

This spec defines a **file-based coordination layer** — locks, events, inbox, lookup — that runs **outside the LLM** via Claude Code hooks. Coordination cost: zero LLM tokens. Workers only spend tokens reading peer state when they actually need to make a decision.

> **Why not Claude Code Agent Teams?** Anthropic's `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` assumes one lead session spawns teammates inside its own project. We have many independent leads across many worktrees — wrong topology. The flag is enabled in settings for future use; the protocol below is what actually runs today.

---

## Architecture at a glance

```
N Claude Code processes (one per worktree)
        │
        │  hooks fire on every tool call / turn boundary
        ▼
   ┌─────────────────────────────────────────┐
   │   ~/.qc-office/  (shared FS, no repo)   │
   │                                         │
   │   agents.json     ← registry            │
   │   inbox/<name>.md ← peer messages       │
   │   locks/<file>    ← file locks          │
   │   events/         ← append-only log     │
   └─────────────────────────────────────────┘
        ▲
        │  on demand: workers read inbox / events
        │  daemon tails events.jsonl + serves SSE
        ▼
   office.quartercharts.com  (Cloudflare-Access-gated)
   ─ isometric office floor (live agent state)
   ─ chat-room feed (decoded events, real-time)
   ─ ttyd-per-worker terminals (iframed)  [Phase 6]
```

### Why `~/.qc-office/` and not the repo?

- Survives `git clean -fdx`, branch switches, worktree resets.
- Not tracked by git → no PR noise from runtime state.
- All worktrees can read/write because it's at user-home, not project-relative.
- Easy to back up / blow away in one place.

---

## Workers — canonical names

Use the **canonical name** in events, not the chat label or worktree slug. The live roster lives in `~/.qc-office/agents.json`, auto-discovered from Claude desktop's session metadata. The shape of each entry:

```jsonc
{
  "<canonical-name>": {
    "role": "orchestrator" | "worker" | "scratch" | "reserve",
    "worktree": "/abs/path/to/worktree",
    "worktree_exists": true,
    "is_archived": false,
    "branch": "claude/...",
    "chat_label": "QC. <Display Name>",
    "scope": "one-line scope description",
    "owns_files": ["glob/**", "..."],
    "_cli_session_id": "<uuid>",
    "_session_metadata": "/path/to/Claude/local_<uuid>.json"
  }
}
```

Canonical names are derived from chat labels by stripping the `QC.` (or legacy `1.`) prefix and slug-casing the rest:
- `QC. Office` → `office`
- `QC. US Charts` → `us-charts`
- `QC. Super Compañías` → `super-companias`

Per-worker scope, file ownership, and bootstrap notes: see `WORKERS/<name>.md`.

---

## The agent language (10-event TOON-style vocabulary)

Every coordination message is one line in `~/.qc-office/events/events.jsonl`. Format:

```
<ISO-8601-utc-Z> <code> key1=value1 key2="value with spaces" key3=value3
```

| Code | Meaning              | Required fields                       | Typical token cost |
| ---- | -------------------- | ------------------------------------- | ------------------ |
| `L`  | Lock acquired        | `file`, `from`, `ttl` (seconds)       | ~8 tokens          |
| `U`  | Lock released        | `file`, `from`                        | ~6 tokens          |
| `S`  | Status / heartbeat   | `from`, `state` (idle/typing/waiting) | ~6 tokens          |
| `T`  | Task started         | `from`, `task_id`, `scope`            | ~10 tokens         |
| `D`  | Task done            | `from`, `task_id`, `summary` (≤30tok) | ~30 tokens         |
| `Q`  | Question to peer     | `from`, `to`, `q_id`, `topic`         | ~12 tokens         |
| `A`  | Answer to peer       | `to`, `q_id`, `data`                  | varies             |
| `R`  | Request room cleared | `from`, `file`, `reason`              | ~12 tokens         |
| `Y`  | Yield room           | `from`, `file`                        | ~6 tokens          |
| `H`  | Halt / escalate      | `from`, `reason`                      | ~12 tokens         |

**Rules:**
- ASCII only. No emoji, no Unicode quotes, no English narration.
- `summary` and `data` fields use double-quotes with escaped internal quotes.
- An agent reading 50 events ≈ 400 tokens. The same exchange in English ≈ 10K tokens.

### Example: globe needs to refactor a shared file

```
2026-04-28T07:15:00Z R from=globe file=world-app/lib/geo.ts reason="adding country borders"
2026-04-28T07:15:01Z Y from=us-charts file=world-app/lib/geo.ts
2026-04-28T07:15:02Z Y from=logo file=world-app/lib/geo.ts
2026-04-28T07:15:03Z L from=globe file=world-app/lib/geo.ts ttl=600
2026-04-28T07:18:42Z U from=globe file=world-app/lib/geo.ts
2026-04-28T07:18:43Z D from=globe task_id=globe-borders summary="added countries layer to deck.gl, 320 lines"
```

Six events, ~70 tokens total. Fully resolved a multi-agent file conflict.

---

## File locking

### Lockfile path

`~/.qc-office/locks/<sanitized-relative-path>.lock`

Sanitization: replace `/` with `__`. Replace `.` in the filename with `__DOT__` only if there are special-char concerns (most paths are safe with just `/` swap).

Examples:
- `app.py` → `~/.qc-office/locks/app.py.lock`
- `docs/foo.md` → `~/.qc-office/locks/docs__foo.md.lock`
- `world-app/components/Globe.tsx` → `~/.qc-office/locks/world-app__components__Globe.tsx.lock`

### Lockfile body

```
owner: globe
acquired: 2026-04-28T07:15:32Z
ttl: 600
worktree: silly-benz-aff74f
pid: 12345
```

### Lifecycle (REVISED 2026-04-28-T1 — locks held for whole turn, not just one tool call)

1. **Acquire** (in `pretooluse-lockcheck.py`, fires before each Edit/Write/MultiEdit/NotebookEdit):
   - If lockfile doesn't exist → atomic `O_CREAT|O_EXCL` create with our identity → exit 0 (proceed).
   - If lockfile exists and `now - acquired > ttl` → stale, take it over → exit 0.
   - If lockfile exists and owner == us → refresh `acquired` (extends TTL) → exit 0.
   - Else → owned by another agent and fresh → **exit 2** with reason. Tool call is blocked. Agent's LLM gets the reason as feedback.

2. **Note** (in `posttooluse-event.py`, fires after each Edit/Write/MultiEdit/NotebookEdit):
   - Logs a `T` event recording what was just touched.
   - **Does NOT release the lock** — the lock is held for the rest of the turn so multi-edit refactors don't get clobbered between Edit calls.

3. **Release** (in `stop-event.py`, fires when the turn ends):
   - Iterates `~/.qc-office/locks/`, finds every lock with `owner == us`, deletes them.
   - Emits one `U` event per released lock.
   - Then logs `S=idle` and `D=turn_end`.

4. **Fence** (max-locks rule):
   - In acquire, count locks owned by us. If ≥ 5 → **exit 2** with "too many locks held". Forces small, focused turns.

### Why the old design (release on PostToolUse) was wrong

In the original Phase 1B design, the lock was acquired in PreToolUse and released in PostToolUse — so a worker only held the lock for the ~50ms duration of a single Edit call. A peer could swoop in and edit the same file 51ms later, which is the exact thing locks are meant to prevent. The 2026-04-28 conflict-test exposed this immediately: logo and globe wrote to the same file with no overlap because both released their locks before the other tried to acquire.

The fix (above): hold the lock until the turn ends. Mental model: "this worker is working on this file" — same as how a human dev would think about it.

### Race-condition handling

The hooks use `os.O_CREAT | os.O_EXCL` on the lockfile path. Two agents racing PreToolUse on the same file → only one syscall succeeds, the loser sees `FileExistsError` and exits 2 with "claimed in a race". Verified end-to-end with two parallel hook invocations 2026-04-28.

---

## The awareness loop (zero-token)

Agents do **not** poll the event log on every turn. That would waste tokens. Instead:

1. **`SessionStart` hook** (when a worker chat opens):
   - Append `S=online` event.
   - Tail last 30 events from `events.jsonl`, filter to entries from peers (not us), inject as a system reminder.

2. **`UserPromptSubmit` hook** (every user turn):
   - Check `~/.qc-office/inbox/<me>.md`. If unread peer messages, prepend their compact form to the user's prompt.
   - Append `S=working` event.

3. **`PreToolUse` hook on Edit | Write | NotebookEdit**:
   - Run `pretooluse-lockcheck.sh`. Block (exit 2) if peer holds the lock.

4. **`PostToolUse` hook on Edit | Write | NotebookEdit**:
   - Release our lock. Append `U` + `T` events.

5. **`Stop` hook** (turn ends):
   - Append `D` event with a 30-token summary derived from the LLM's last assistant message (truncated).

The agent never has to think about coordination — it just does its work, and the hooks make sure peers know.

---

## The inbox

`~/.qc-office/inbox/<name>.md` is a plain markdown file, append-only by hooks, trimmed to last 20 entries.

### When does the inbox get written?

- **Direct messages**: when peer sends `Q` or `A` event with `to=<me>`, the receiving agent's `posttooluse-event.sh` (running on the *sender's* side) writes the message to `inbox/<me>.md`. (Cross-process write — works because filesystem is shared.)
- **Room-clearing**: when peer sends `R` with `file=<one-of-my-locks>`, my next hook fire writes a high-priority entry to my inbox.
- **Halts**: when any agent emits `H`, **all 9** inboxes get a copy + the office worker gets a flagged escalation.

### When does an agent read it?

- Automatically: `UserPromptSubmit` hook prepends unread entries to the user's prompt (if any).
- Manually: agent calls `Read` on `~/.qc-office/inbox/<me>.md` when prompted by `syncqc` or similar.

### Read marker

A separator line `<!-- READ: <ISO-timestamp> -->` is inserted by the agent when it reads. Hook prepends only entries below the most recent read marker.

---

## Conflict-resolution rules

1. **Stay in your lane.** Each worker has `owns_files` in `agents.json`. Edits inside your lane: no announcement needed (still acquire lock). Edits outside: emit `R`, wait for `Y` from current owner before locking.
2. **5-lock max** (workers) / **25-lock max** (orchestrators). Forces small commits for workers; gives orchestrators headroom for multi-file refactors.
3. **TTL is sacred.** Default 600s. If your task takes longer, refresh the lock by re-running the same hook (any tool call on the file refreshes). If you go silent for 10+ minutes with the lock held, peers will rip it.
4. **Orchestrators arbitrate.** If two agents both `R` for the same file, any active orchestrator can arbitrate by emitting `H` to the loser. Loser yields and re-queues.
5. **Halt is for humans.** `H` events surface in Sebastián's dashboard with audio. Use sparingly.

## Dashboard drag/drop semantics (2026-05-03)

The dashboard at `office.quartercharts.com` exposes drag-to-relocate for every chip on the floor. Behavior matrix:

| Drop target | Effect |
| --- | --- |
| Built-in cluster (`charts-office`, `meetings`, etc.) | Sets `presence: "<cluster>"`, `presence_pinned: true`. Survives auto-drift. |
| Custom room (user-created via Add Room button) | Sets `presence: "custom-...id"`, `presence_pinned: true`. |
| `MEETINGS` / `MEETINGS-2` | Sticky (renders there regardless of agent state). |
| `WATCHDOGS` | Sticky, same as meetings. |
| `COFFEE` | User-explicit drop sticks even when `pinned=true` (presence_pinned distinguishes user intent from auto-drift). |
| `ORCHESTRATOR` (ADMIN) | `/priority/promote` runs silently — no modal. Multi-orch: adds without demoting. Modal only re-appears on daemon error. |
| Outside any room (corridor) | Snap-to-nearest within 1 tile; otherwise no-op. |

**The two pin flags** distinguish two intents:
- `pinned: true` — defeats automatic drift to system-managed presences (`coffee` from idle, `agent-ready` from orientation graduation, etc.). When pinned, an idle agent stays at home rather than drifting.
- `presence_pinned: true` — user has explicitly placed this agent at this presence (via drag or room-card combobox). Distinct from `pinned` because we want explicit user placements to override even system-presence routing rules. Set by the dashboard's drag handler; preserved across discovery sweeps via `PRESERVE_IF_PRESENT` in `discover-agents.py`.

Both default to `false`. Both survive discovery sweeps.

---


<!-- ROLES-LEGEND-v1 -->
## Roles in `agents.json`

The protocol distinguishes four roles. Hooks branch on these:

| Role | Hooks behavior | Lock cap | Use case |
| --- | --- | --- | --- |
| `orchestrator` | Full participation. Lock + event spam allowed. | 25 | One or more orchestrator chats per team (`hq`, `hq-2`, etc.). |
| `worker` | Full participation. Standard. | 5 | All real product workers (us-charts, globe, currency, etc.). |
| `scratch` | **No-op.** No locks, no event log entries, no inbox surfacing. | n/a | Sebastián's personal pads (`notes`). |
| `reserve` | **No-op.** Same as scratch. | n/a | Empty hot-spares (`open-slot-1`). |

Non-participating roles (`scratch`, `reserve`) are still discovered and shown on the dashboard, but they don't block other workers and aren't blocked by them.

> **Multi-orchestrator support** (added 2026-05-03 per Sebastián's directive): a team can have **multiple live orchestrators**. Drag-to-ADMIN on the dashboard ADDS the dragged agent as a co-orchestrator without demoting any existing one. Office-inbox notifications use "ORCHESTRATOR ADDED" wording, not "HANDOFF". Workers route Q events to ANY active orchestrator. The legacy demote-then-promote takeover flow can still be invoked manually via two `/priority/patch` calls (demote outgoing → promote incoming) but is no longer the default of `/priority/promote`.

## Roadmap

| Phase | Scope                                                                                  | Status |
| ----- | -------------------------------------------------------------------------------------- | ------ |
| 0     | Rotate the office password (Sebastián chooses, stores in Apple Passwords).             | ⏳     |
| 1A    | `~/.qc-office/` bootstrap, `agents.json`, this spec, per-worker `WORKERS/<name>.md`.   | ✅     |
| 1B    | Hook scripts in `.claude/hooks/`. Inert until Phase 1C wires them in.                  | ⏳     |
| 1C    | `.claude/settings.json` enables Agent Teams flag + registers hooks.                    | ⏳     |
| 1D    | Smoke test: 3 workers each lock a file simultaneously; verify queueing + events.       | ⏳     |
| 2     | Replace file-based events with NATS JetStream on Railway. Hooks publish to NATS too.   | ⏳     |
| 3     | `office.quartercharts.com` Next.js dashboard on Vercel. Auth-gated. WebSocket bridge.  | ⏳     |
| 4     | `ttyd` per worker on Mac, tunneled via Cloudflare, iframed in dashboard.               | ⏳     |
| 5     | Cool visual layer (isometric office or force-graph). Replaces grid placeholder.        | ⏳     |
| 6     | Optional: room-clearing UX, audio cues, dashboard-driven worker spawn/kill.            | ⏳     |

---

## Critical caveats

- **Hooks must finish in <200ms** or they degrade Claude Code responsiveness. All hook scripts use only filesystem ops — no network calls until Phase 2.
- **The `~/.qc-office/` directory is per-machine, not per-user-account.** If Sebastián logs in on a second Mac, that Mac has its own coordination layer. Phase 2 (NATS) fixes this.
- **Worktrees share a git history.** Two agents pushing different commits to different branches is fine; two agents committing to the same branch will conflict at push time. The lock layer prevents same-file edits but doesn't prevent same-branch commits — keep `branch ≠ branch` between agents (already true today).
- **The `office` worker (this chat) is special.** It owns this spec, the registry, and the dashboard. It does NOT edit app code unless explicitly assigned. Other workers route questions here via `Q to=office`.

---

## How to use this as a non-orchestrator worker

You're one of the 8 non-`office` workers? Three things:

1. **Read your `WORKERS/<your-name>.md` file.** That's your scope and file ownership.
2. **Don't read this whole spec.** The hooks handle coordination. You'll get nudged when peers need something.
3. **Speak in events when prompted.** If asked to broadcast intent, emit one of the 10 codes — never English narration. The orchestrator decodes for Sebastián.

---

## How to use this as the orchestrator (`office`)

That's me. My job:
- Maintain `agents.json` (this is the source of truth — chat names can drift).
- Watch `events/events.jsonl` for `H` escalations.
- Arbitrate `R`/`Y` ties.
- Curate `WORKERS/*.md` briefs as scopes evolve.
- Build & maintain the dashboard (Phase 3+).
- Don't touch app code without an explicit assignment from Sebastián.

### Orchestrator broadcast protocol — added 2026-05-04 by Sebastián directive

**When you finish a task OR push a commit, broadcast to ALL other live orchestrators — not selected ones.**

Two-step protocol, mandatory:

1. **Append an entry** to `~/.qc-office/broadcasts/orchestrators.md`:
   - Heading: `### YYYY-MM-DDTHH:MMZ — <topic>` (UTC).
   - Body: what you shipped, why it matters cross-orch, any operational fact every orch needs (env vars, conventions, registry shapes).
   - Sign with your canonical agent name (`qc/hq`, `qc/sankey`, etc.).
2. **Drop a pointer line** into each peer orchestrator's inbox at `~/.qc-office/inbox/<short>.md`:
   - One bullet per orchestrator, format `- \`<ts>\` **Broadcast from: qc/<you>** · **<topic>** ... see broadcasts/orchestrators.md`.
   - Use Python or `_drop_inbox_line` directly — there's no HTTP route for this.
   - The list is canonical: every orch with `role=orchestrator AND is_archived=false` in `agents.json`. Re-read on each broadcast — the roster changes when Sebastián drag-promotes new ones.

**No "selective" broadcasting.** Even if a finish-task only seems relevant to one peer, broadcast to all — the cost is one inbox line per orch, the benefit is no missed coordination. If something is truly per-PR-audit-ask or per-routing-decision, that's a direct inbox message, NOT a broadcast (the file's "What does NOT belong" section already covers this).

**Why**: prod was down 18 min on 2026-05-04T02:22Z because PR #313's lifespan-raise behavior wasn't broadcast to qc/sankey before merge. Cross-orch invisibility is the failure mode. Broadcast first, then ship.

The `~/.qc-office/broadcasts/orchestrators.md` header lists the canonical roster and the posting/reading rules. Read on session start when you have a free turn.

---

*Last updated: 2026-04-29 by office-2 (eager-mendeleev-bbe58e). Orchestrator role transferred from qc/office (eloquent-lewin-7c8efe) on 2026-04-29 after the original chat hit attach failures; new active brief lives at `WORKERS/office-2.md`.*
