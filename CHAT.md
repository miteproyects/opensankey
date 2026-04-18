# CHAT.md — Live Handoff Channel

This file is a turn-by-turn relay between **Cowork** (Sebastián's desktop Claude app) and **Claude Code** (Sebastián's Mac terminal). Sebastián types `read chat` on either side and that side follows the protocol below.

**Not the same as `CLAUDE.md`.** CLAUDE.md holds persistent project state (architecture, tasks, gotchas). CHAT.md is the live message board — it changes every turn.

---

## Protocol — READ FIRST

When Sebastián says `read chat`:

1. Identify which side you are: **COWORK** (desktop app) or **CLAUDE CODE** (Mac terminal).
2. Read the section addressed to **you** (`FOR COWORK` or `FOR CLAUDE CODE`).
3. Act on it:
   - **Cowork:** plan, analyze, review, draft deliverables. Do *not* try to run code locally.
   - **Claude Code:** execute, code, run shell, hit real network.
4. Overwrite the section addressed to the **other** side with your response/next instructions.
5. Update the **STATUS** block (turn number, last writer, whose baton).
6. Append one line to the **Log** (newest at top).
7. Tell Sebastián what you did and what the other side will do next.

**Also re-read `CLAUDE.md`** for project state — CHAT.md never duplicates it.

**Escalation:** if blocked, write `BLOCKED: <reason>` in your outbound section and hand baton back.

---

## STATUS

- **Turn:** 1
- **Last write:** 2026-04-17 — Cowork
- **Baton:** CLAUDE CODE (you act next)

---

## FOR CLAUDE CODE (from Cowork)

> This is what Claude Code reads when Sebastián types `read chat` on the Mac.

**Context:** Task #25 (per-quarter historical gap-fill) is complete and wired into `data_fetcher.py`. Both files compile. We need to validate the gap-fill with a live source-coverage probe before exercising Annual mode in Streamlit.

**Do next (in this order):**

1. Patch `_probe_sources.py` so it accepts CLI tickers, falling back to the hardcoded list when none are given. Minimal diff:
   ```python
   import sys
   if len(sys.argv) > 1:
       TICKERS = [t.upper() for t in sys.argv[1:]]
   ```

2. Grep `data_fetcher.py` for how dot-tickers (e.g. `BRK.B`) are normalized per source. SEC uses `BRK-B`, yfinance uses `BRK.B`, FMP accepts both, Finnhub is inconsistent. Report which sources have normalization and which don't. **Do not fix yet** — just surface the gaps.

3. Run the probe with the 16-ticker set:
   ```
   python3 _probe_sources.py BRK.B JPM LLY V XOM JNJ WMT MA PLTR ABBV NFLX AAPL MSFT GOOGL META NVDA
   ```
   Print output as: `TICKER statement source: N quarters [YYYYQ# – YYYYQ#]`. Flag any source/ticker returning 0 or <8 quarters.

4. Write results into **FOR COWORK** below:
   - coverage matrix summary (don't paste all raw lines — group by pattern)
   - dot-ticker normalization audit (which sources lack it)
   - anomalies (sources that 404, timeouts, unexpected gaps)
   - a recommendation: keep FMP → Finnhub → yfinance priority, or swap per statement type

5. Update **STATUS** (Turn 2, baton back to COWORK), append Log entry, tell Sebastián you're done.

---

## FOR COWORK (from Claude Code)

> This is what Cowork reads when Sebastián types `read chat` in the desktop app.

*(empty — awaiting first response from Claude Code)*

---

## Log (newest first, append-only)

- 2026-04-17 T1 — Cowork — CHAT.md created; baton handed to Claude Code for probe run (Task #21).
