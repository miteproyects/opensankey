---
name: ultrareview
description: Ultra-thorough review of pending changes — a superset of /review and /security-review. Goes beyond a quick PR read: inspects correctness, security, concurrency, performance, backward-compatibility, error handling, tests, docs, UX, and cross-cutting regressions across the whole diff plus the files it touches. Use when the user types "/ultrareview", asks for a "deep review", "ultra review", "full audit", "thorough code review", "pre-merge review", "before I ship this", "before I push", or otherwise signals they want more than a surface-level read. Also trigger when the user has just finished a non-trivial change and asks something like "anything I missed?" or "what would a senior reviewer catch here?". Prefer this skill over /review or /security-review whenever the user uses the word "ultra", "deep", "thorough", "full", "exhaustive", or "everything" in the context of a code review.
---

# /ultrareview

A careful, exhaustive review of pending changes on the current branch (or the explicitly specified diff / PR). The goal is to catch everything a senior reviewer would — bugs, security issues, regressions, performance cliffs, brittle tests, bad UX, stale docs — and report them in a single, prioritised document.

This is meant to be slower and more thorough than `/review`. It composes the scope of `/review` with the scope of `/security-review` and then adds layers of its own. It is intended for use right before merging or pushing, when being wrong is costly.

## When to run this

- Right before the user pushes or merges a non-trivial branch.
- When the user explicitly asks for a deep / thorough / full review.
- When the diff touches auth, payments, data-mutating code, migrations, public APIs, anything user-visible, or anything safety-relevant.
- When the user asks "anything I missed?" or "what would a senior reviewer catch here?".

Do **not** run this for tiny single-file typo fixes — `/review` is enough there. If in doubt, ask the user once whether they want the quick `/review` or the full `/ultrareview`.

## Scope

Review the pending diff **and** the immediate neighbourhood of every changed file. A changed function in file A often interacts with file B; skim B. Do not limit the review to the diff hunks alone.

Specifically cover:

1. **Correctness.** Off-by-one, boundary conditions, `None` / `null` paths, empty-collection paths, type mismatches, unhandled exceptions, silent exception swallowing, wrong operator precedence, timezone bugs, floating-point comparison, mutation of shared state.
2. **Security.** Everything `/security-review` covers, at a minimum — injection (SQL / shell / XSS / SSRF), path traversal, deserialization, SSTI, XXE, IDOR, auth/authorisation gaps, missing CSRF, weak crypto, hard-coded secrets, excessive PII logging, unsafe redirects, unrestricted file upload, prototype pollution, open CORS, timing attacks on comparisons. Treat any new network / file / subprocess call as a surface and ask how a hostile input reaches it.
3. **Concurrency.** Race conditions, non-atomic read-modify-write, missing locks, deadlock potential, thread-unsafe singletons, unsafe shared state across requests, cache stampedes, cache-key collisions.
4. **Performance.** N+1 queries, missing indexes, unbounded loops, unbounded recursion, O(n²) where O(n) fits, blocking I/O on a hot path, synchronous external calls without timeouts, cache TTLs that don't make sense, large payloads held in memory, missing pagination.
5. **Error handling & resilience.** Timeouts, retries with backoff, idempotency, circuit breakers, fallback paths, graceful degradation, user-facing error messages, `finally` blocks that leak resources, log-and-reraise vs log-and-swallow, stack-trace exposure.
6. **Backward compatibility.** Schema / API / CLI / config changes that break existing callers, stored-data migrations, feature-flag hygiene, removed exports, renamed routes, changed response shapes.
7. **Testing.** New tests actually exercise the new behaviour (not just call it). Edge cases covered. No tests that always pass (tautologies). Flaky patterns (sleep-based waits, time.now, network). Good-enough coverage before merge.
8. **Docs & changelog.** Public API / CLI / config changes reflected in docs, READMEs, changelogs. Internal docstrings updated. Comments still match the code.
9. **UX.** Copy is clear and non-scary. Errors are actionable. Accessibility preserved (labels, alt text, contrast, focus order, keyboard nav). Mobile / narrow-viewport regressions. Loading and empty states.
10. **Observability.** Logs at the right level, no PII leaks, traces / metrics for new hot paths, feature flags have kill-switches.
11. **Operational.** New env vars documented and defaulted safely. Migrations have a rollback path. Feature flags default-off in prod if risky. Background jobs are idempotent and retryable.
12. **Repo hygiene.** Dead code, TODOs without tickets, committed debugger statements, `console.log` / `print`, committed local paths or hostnames, files that shouldn't be committed (keys, `.env`, large binaries), commit-message clarity.

## How to run it

### 1. Establish the diff

Figure out what "pending" means in this context:

- If the user specified a PR, branch, or commit range — use that.
- Else prefer the current branch vs its merge base with the default branch (`git merge-base HEAD origin/main` or `origin/master`).
- Fall back to `git status` + unstaged + staged.

Gather the raw diff (`git diff <base>...HEAD`), the list of changed files, and the recent commit messages on the branch. Do this in parallel.

### 2. Orient

Before critiquing, understand the change. Read the full commit messages, then the diff, then the files touched. For non-trivial functions, read the callers too — a behaviour change in a helper affects everything downstream.

If the repo has a `CLAUDE.md`, project-specific rules in `docs/`, or a `CODEOWNERS`, read them. If there are project invariants in docs (e.g. "all callers must go through module X"), check that they still hold.

### 3. Review, by layer

Go through the twelve scope areas in order. For each, do a focused pass — don't jump around. Take notes per file so the final report can be sorted by file and by severity.

Two rules of thumb:

- **Be specific.** "There's a race condition" is not a finding. "Lines 204-218 read `cache[key]` then write it back unconditionally — two concurrent requests on the same `key` will clobber each other; use `setdefault` or a lock" is a finding.
- **Prefer reproducible evidence.** If a claim can be verified with a unit test, quote what that test would look like. If a claim is a judgement call, say so.

### 4. Verify what you can

Where verifying is cheap, verify:

- Run the project's linter / type-checker on the changed files if the repo has one.
- Run the relevant tests.
- If the change affects a runnable artefact (a script, a server, a CLI), actually run it against a realistic input. For web UIs, run on localhost and click through the changed surface.

Never claim "I tested this" unless you actually did.

### 5. Write the report

Structure the output as follows, in prose — not dense bullet lists:

```
# /ultrareview — <branch or scope>

## Summary
One paragraph. What this change does, what's good about it, what the top risks are.

## Blocking issues
Findings that should be fixed before merging. Each finding has:
- File and line range
- What's wrong
- Why it matters (one sentence)
- The smallest fix that would resolve it

## Non-blocking issues
Nice-to-haves, style nits, future cleanups. Same format, lower urgency.

## Tests
What's tested, what's not, what new tests would be worth adding.

## Docs & changelog
What needs updating.

## Verification I ran
Exact commands and their results.

## Questions for the author
Anything you can't tell from the diff alone.
```

Keep the report honest. If the change is fine, say so — don't manufacture findings. A one-line "looks good, nothing blocking, small nits below" is a legitimate `/ultrareview` output for a clean change.

## Output rules

- Save the report to a file the user can reopen: `/<repo>/.ultrareview-<short-sha>.md`. If the repo is read-only, fall back to the workspace folder.
- Also surface the **Blocking issues** section inline in the chat so the user sees it immediately.
- Use the repo's terminology. If the repo calls them "quarter buttons" or "ticker search", don't invent new names.
- Do not reproduce large chunks of source code in the report — reference by file + line.

## Philosophy

The purpose of this skill is not to find as many issues as possible; it is to make the user more confident that the change is safe to ship. Err toward fewer, higher-quality findings. A report that lists two real bugs is worth more than a report that lists twenty nits.

If you're unsure whether something is a real issue, say so. "I'm not sure whether X is intentional — if it is, ignore this; if not, see line Y" is a valid finding. Senior reviewers flag uncertainty instead of hiding it.
