---
name: syncqc
description: Sync QuarterCharts session. Reads CLAUDE.md (project memory) and CHAT.md (live handoff) so the running side catches up on what the other side did and what to do next. Trigger on "syncqc", "sync qc", "syncQC", "syncQC.com", or at the start of any session in the miteproyects folder.
---

# SyncQC — QuarterCharts Session Sync

Single command that replaces `read MD` + `read chat`. Use this at the start of every session or whenever Sebastián wants the other side's latest state.

## Procedure

When triggered:

1. **Identify your side.**
   - **Claude Code** — running in Terminal on Sebastián's Mac, has shell access, can run `streamlit`, hit real APIs, edit the live filesystem.
   - **Cowork** — running in the desktop app, paths look like `/sessions/.../mnt/...`, no shell access to the Mac, no live API access.

2. **Read `CLAUDE.md`** in the project root (`miteproyects/CLAUDE.md`). This has persistent project memory: architecture, tasks, gotchas, acceptance criteria. Don't skim — read the whole thing if it's been a while.

3. **Read `CHAT.md`** in the project root. This has the live turn-by-turn handoff.

4. **Check the STATUS block** in `CHAT.md`:
   - Note the turn number.
   - Note who holds the baton.
   - If the baton is *not* on your side, tell Sebastián — don't act on stale instructions.

5. **Read your inbox section** in `CHAT.md`:
   - Cowork reads `FOR COWORK`.
   - Claude Code reads `FOR CLAUDE CODE`.

6. **Summarize to Sebastián in 3–5 bullets:**
   - What the other side did last turn (from CHAT.md Log + the inbox section).
   - What your inbox instructs you to do next.
   - Any `BLOCKED:` flags or open questions.
   - Whose baton now.
   - Your proposed first action.

7. **Act.** If the inbox instructions are clear, execute them. If ambiguous, ask one clarifying question before proceeding.

## After Finishing Your Turn

1. **Update `CHAT.md`:**
   - Overwrite the *other* side's section with your response + next instructions.
   - Bump `STATUS` (turn number + 1, flip baton, update "Last write").
   - Prepend a one-liner to the `Log` section (newest first): `YYYY-MM-DD T<N> — <your side> — <summary>`.

2. **Update `CLAUDE.md` only if persistent state changed:**
   - New gotcha → add to Gotchas.
   - Task status change → update Active Task List mirror.
   - Architecture decision → note in Architecture Notes.
   - End of meaningful session → Rolling Log entry.

   CLAUDE.md is memory. CHAT.md is the active message. Never duplicate.

## Side-Specific Rules

**Cowork:**
- Do not try to run `_probe_sources.py`, `streamlit`, or anything that needs real network. Hand those tasks to Claude Code via CHAT.md.
- Do synthesize, plan, review, produce deliverables (.docx/.pptx/.xlsx/.pdf), and check Claude Code's work for logical gaps.

**Claude Code:**
- Prefer executing the concrete commands in your inbox before opening new investigations.
- Capture command output (truncated if huge) in CHAT.md FOR COWORK — not just "it worked."
- If a command fails, include the exact error. Never silently retry.

## Escalation

If blocked for any reason (missing dependency, ambiguous request, unexpected API failure), write `BLOCKED: <reason>` in your outbound section, flip baton back, and stop. Do not spin on a problem past two retries.
