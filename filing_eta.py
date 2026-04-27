"""
filing_eta.py — Unified 3-source filing-date ETA for QuarterCharts.

Hierarchy (applied identically to sidebar, quarter selector, earnings table):
  1. SEC EDGAR          — data.sec.gov/submissions/CIK{cik}.json  (10-Q / 10-K / 8-K)
  2. Financial Modeling — FMP  /income-statement?period=quarter   (fillingDate, period)
     Prep (FMP)
  3. Finnhub            — /calendar/earnings                       (announcement date)

All three sources are free + REST/JSON. FMP and Finnhub were already wired in via
data_fetcher.get_fiscal_calendar() and earnings_page Finnhub calls; EDGAR is added
here as the new primary.

Public API
  get_filing_eta(ticker, event_label=None, finnhub_date=None) -> dict
      Returns:
        {
          "primary_days":   int|None,   # best available estimate (EDGAR > FMP > Finnhub)
          "primary_source": "edgar" | "fmp" | "finnhub" | None,
          "edgar_days":     int|None,
          "fmp_days":       int|None,
          "finnhub_days":   int|None,
          "edgar_label":    "~ filing in Xd" | "~ filing any day" | None,
          "fmp_label":      ...,
          "finnhub_label":  ...,
          "primary_label":  ...,
        }

  get_filing_cadence(ticker) -> dict
      Returns median gap (in days) from each source, for the quarter selector buttons:
        {
          "primary_median": int|None,
          "primary_source": "edgar" | "fmp" | "finnhub" | None,
          "edgar_median":   int|None,
          "fmp_median":     int|None,
          "finnhub_median": int|None,  # typically None — Finnhub has no filing history
        }
"""

from __future__ import annotations

import os
import time
import calendar as _cal
from datetime import date as _date, timedelta as _td
from typing import Optional

import requests

try:
    import streamlit as st
    _cache = st.cache_data
except Exception:  # pragma: no cover
    def _cache(*_a, **_kw):
        def _deco(fn):
            return fn
        return _deco

# ── Constants ─────────────────────────────────────────────────────────────

_SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "QuarterCharts research@quartercharts.com",
)
_SEC_HEADERS = {"User-Agent": _SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
_SEC_TIMEOUT = 8

_FMP_KEY = os.environ.get("FMP_API_KEY", "")
_FMP_BASE = "https://financialmodelingprep.com/api/v3"

_FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
_FINNHUB_BASE = "https://finnhub.io/api/v1"


# ── EDGAR: ticker → CIK ───────────────────────────────────────────────────

@_cache(ttl=86400, show_spinner=False)
def _edgar_ticker_map() -> dict:
    """Download SEC's ticker → CIK map. Cached 24h."""
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=_SEC_HEADERS,
            timeout=_SEC_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            out = {}
            for v in data.values():
                t = str(v.get("ticker", "")).upper().strip()
                c = v.get("cik_str")
                if t and c:
                    out[t] = int(c)
            return out
    except Exception:
        pass
    return {}


def _ticker_to_cik(ticker: str) -> Optional[str]:
    """Return zero-padded 10-digit CIK for a ticker or None."""
    if not ticker:
        return None
    mp = _edgar_ticker_map()
    cik_int = mp.get(ticker.upper())
    if cik_int is None:
        return None
    return str(cik_int).zfill(10)


# ── EDGAR: submissions feed ───────────────────────────────────────────────

@_cache(ttl=7200, show_spinner=False)
def _edgar_submissions(cik10: str) -> dict:
    """Fetch EDGAR submissions feed for a padded-10 CIK. Cached 2h."""
    try:
        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik10}.json",
            headers=_SEC_HEADERS,
            timeout=_SEC_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json() or {}
    except Exception:
        pass
    return {}


def _edgar_recent_filings(ticker: str) -> list[dict]:
    """
    Return recent filings from EDGAR for a ticker as a list of
    {form, filingDate, reportDate, accessionNumber, isXBRL} dicts.
    """
    cik = _ticker_to_cik(ticker)
    if not cik:
        return []
    sub = _edgar_submissions(cik)
    if not sub:
        return []
    recent = (sub.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    fdates = recent.get("filingDate") or []
    rdates = recent.get("reportDate") or []
    accs = recent.get("accessionNumber") or []
    out = []
    n = min(len(forms), len(fdates), len(rdates))
    for i in range(n):
        out.append({
            "form": forms[i],
            "filingDate": fdates[i],
            "reportDate": rdates[i],
            "accessionNumber": accs[i] if i < len(accs) else "",
        })
    return out


def _edgar_quarters(ticker: str) -> list[dict]:
    """Return list of {period_end, filing_date} for historical 10-Q / 10-K filings."""
    qs = []
    for f in _edgar_recent_filings(ticker):
        form = (f.get("form") or "").upper()
        if form not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
            continue
        pe = f.get("reportDate") or ""
        fd = f.get("filingDate") or ""
        if pe and fd:
            qs.append({"period_end": pe, "filing_date": fd})
        if len(qs) >= 12:
            break
    return qs


def _edgar_latest_8k_earnings_date(ticker: str) -> Optional[str]:
    """Return the most recent 8-K Item 2.02 filing date (ISO) if present."""
    # Simple heuristic: use most recent 8-K filing date. A fuller implementation
    # would parse the filing index to confirm Item 2.02, but the 4-business-day
    # rule makes the filing date itself a strong proxy for the announcement.
    for f in _edgar_recent_filings(ticker):
        if (f.get("form") or "").upper() == "8-K":
            return f.get("filingDate") or None
    return None


# ── FMP (already integrated via data_fetcher; thin wrapper for cadence) ───

def _fmp_quarters(ticker: str) -> list[dict]:
    """Return list of {period_end, filing_date} from FMP (via get_fiscal_calendar)."""
    try:
        from data_fetcher import get_fiscal_calendar
        fc = get_fiscal_calendar(ticker) or {}
    except Exception:
        return []
    out = []
    for q in (fc.get("quarters") or []):
        pe = (q.get("period_end") or "")[:10]
        fd = (q.get("filing_date") or "")[:10]
        if pe and fd:
            out.append({"period_end": pe, "filing_date": fd})
    return out


def _fy_end_month(ticker: str) -> Optional[int]:
    """Fiscal year-end month (1..12) from FMP/yfinance via data_fetcher."""
    try:
        from data_fetcher import get_fiscal_calendar
        fc = get_fiscal_calendar(ticker) or {}
        m = fc.get("fy_end_month")
        if m:
            return int(m)
    except Exception:
        pass
    return None


@_cache(ttl=900, show_spinner=False)
def _fmp_next_earnings_date(ticker: str) -> Optional[str]:
    """Return next upcoming earnings date (ISO) from FMP earning_calendar, or None."""
    if not _FMP_KEY:
        return None
    try:
        today = _date.today()
        from_s = today.isoformat()
        to_s = (today + _td(days=120)).isoformat()
        r = requests.get(
            f"{_FMP_BASE}/earning_calendar",
            params={"from": from_s, "to": to_s, "apikey": _FMP_KEY},
            timeout=_SEC_TIMEOUT,
        )
        if r.status_code == 200:
            rows = r.json() or []
            for row in sorted(rows, key=lambda x: str(x.get("date", ""))):
                if str(row.get("symbol", "")).upper() == ticker.upper():
                    d = (row.get("date") or "")[:10]
                    if d >= from_s:
                        return d
    except Exception:
        pass
    return None


# ── Finnhub ───────────────────────────────────────────────────────────────

@_cache(ttl=900, show_spinner=False)
def _finnhub_next_earnings_date(ticker: str) -> Optional[str]:
    """Return next upcoming earnings announcement date (ISO) from Finnhub, or None."""
    try:
        today = _date.today()
        from_s = today.isoformat()
        to_s = (today + _td(days=180)).isoformat()
        r = requests.get(
            f"{_FINNHUB_BASE}/calendar/earnings",
            params={"symbol": ticker.upper(), "from": from_s, "to": to_s, "token": _FINNHUB_KEY},
            timeout=_SEC_TIMEOUT,
        )
        if r.status_code == 200:
            rows = (r.json() or {}).get("earningsCalendar") or []
            rows = sorted(rows, key=lambda x: str(x.get("date", "")))
            for row in rows:
                d = (row.get("date") or "")[:10]
                if d >= from_s:
                    return d
    except Exception:
        pass
    return None


# ── Core: median gap + ETA ────────────────────────────────────────────────

def _median_gap_days(quarters: list[dict]) -> Optional[int]:
    import pandas as _pd
    gaps = []
    for q in quarters or []:
        pe = (q.get("period_end") or "")[:10]
        fd = (q.get("filing_date") or "")[:10]
        if pe and fd:
            try:
                g = (_pd.Timestamp(fd) - _pd.Timestamp(pe)).days
                if 0 < g < 180:
                    gaps.append(g)
            except Exception:
                pass
    if not gaps:
        return None
    gaps.sort()
    return int(gaps[len(gaps) // 2])


def _parse_event_label(event_label: str) -> tuple[Optional[int], Optional[int]]:
    """Parse 'Q1 2026 Earnings' → (1, 2026). Returns (None, None) on failure."""
    if not event_label:
        return None, None
    q_num, q_year = None, None
    try:
        for tok in str(event_label).strip().split():
            if tok.startswith("Q") and tok[1:].isdigit():
                q_num = int(tok[1:])
            elif tok.isdigit() and len(tok) == 4:
                q_year = int(tok)
    except Exception:
        pass
    return q_num, q_year


def _predicted_period_end(q_num: int, q_year: int, fy_end_month: int) -> Optional[_date]:
    try:
        qe_month = ((fy_end_month - 1) + 3 * q_num) % 12 + 1
        pe_year = q_year if qe_month <= fy_end_month else q_year - 1
        last = _cal.monthrange(pe_year, qe_month)[1]
        return _date(pe_year, qe_month, last)
    except Exception:
        return None


def _eta_days_from_median(q_num, q_year, fy_end_month, median_gap) -> Optional[int]:
    if not (q_num and q_year and fy_end_month and median_gap is not None):
        return None
    pe = _predicted_period_end(q_num, q_year, fy_end_month)
    if pe is None:
        return None
    return ( (pe + _td(days=int(median_gap))) - _date.today() ).days


def _eta_days_from_announce(announce_iso: Optional[str]) -> Optional[int]:
    if not announce_iso:
        return None
    try:
        y, m, d = announce_iso[:10].split("-")
        return (_date(int(y), int(m), int(d)) - _date.today()).days
    except Exception:
        return None


def _fmt_label(days: Optional[int]) -> Optional[str]:
    if days is None:
        return None
    if days <= 0:
        return "~ filing any day"
    if days == 1:
        return "~ filing in 1d"
    return f"~ filing in {days}d"


# ── Public API ────────────────────────────────────────────────────────────

def get_filing_cadence(ticker: str) -> dict:
    """
    Return per-source historical median filing gap (period_end → filing_date).
    Used for the quarter-selector 'filing ~Nd' label.
    """
    edgar_med = _median_gap_days(_edgar_quarters(ticker))
    fmp_med = _median_gap_days(_fmp_quarters(ticker))
    primary_med, primary_src = None, None
    for src, val in (("edgar", edgar_med), ("fmp", fmp_med)):
        if val is not None:
            primary_med, primary_src = val, src
            break
    # Clamp to a reasonable 10-Q / 10-K window
    def _clamp(v):
        return None if v is None else max(15, min(95, int(v)))
    return {
        "primary_median": _clamp(primary_med),
        "primary_source": primary_src,
        "edgar_median": _clamp(edgar_med),
        "fmp_median": _clamp(fmp_med),
        "finnhub_median": None,  # Finnhub has no filing-date history
    }


def get_filing_eta(
    ticker: str,
    event_label: Optional[str] = None,
    finnhub_date: Optional[str] = None,
) -> dict:
    """
    Compute days-until-filing from all 3 sources. Select EDGAR > FMP > Finnhub.

    Args:
        ticker:       US equity ticker (e.g. 'META').
        event_label:  Earnings event label like 'Q1 2026 Earnings'. Used with
                      fiscal-year-end month to predict the upcoming period_end.
                      When omitted, the most recent reported quarter is used
                      (sidebar use-case).
        finnhub_date: If the caller already has a Finnhub earnings-calendar date
                      (as the Earnings page does), pass it in to skip a re-fetch.
    """
    fy_m = _fy_end_month(ticker) or 12
    q_num, q_year = _parse_event_label(event_label or "")

    # If no event label, pick the most recent completed fiscal quarter for the
    # "Latest from X" sidebar use-case.
    if not (q_num and q_year):
        try:
            today = _date.today()
            # Last completed quarter end (calendar-based; adjusted for fy)
            # For sidebar: treat as "latest reported quarter"
            candidates = []
            for y in range(today.year - 1, today.year + 1):
                for q in range(1, 5):
                    pe = _predicted_period_end(q, y, fy_m)
                    if pe and pe <= today:
                        candidates.append((q, y, pe))
            if candidates:
                q_num, q_year, _ = max(candidates, key=lambda x: x[2])
        except Exception:
            pass

    # 1) EDGAR
    edgar_quarters = _edgar_quarters(ticker)
    edgar_med = _median_gap_days(edgar_quarters)
    edgar_days = _eta_days_from_median(q_num, q_year, fy_m, edgar_med)
    # If EDGAR has a recent 8-K announcement, prefer that (tighter bound).
    edgar_8k = _edgar_latest_8k_earnings_date(ticker)
    edgar_8k_days = _eta_days_from_announce(edgar_8k) if edgar_8k else None
    # Only use 8-K if it is in the future (otherwise it's the last earnings, not the next).
    if edgar_8k_days is not None and edgar_8k_days >= 0:
        if edgar_days is None or edgar_8k_days < edgar_days:
            edgar_days = edgar_8k_days

    # 2) FMP
    fmp_quarters = _fmp_quarters(ticker)
    fmp_med = _median_gap_days(fmp_quarters)
    fmp_days = _eta_days_from_median(q_num, q_year, fy_m, fmp_med)
    fmp_ann = _fmp_next_earnings_date(ticker)
    fmp_ann_days = _eta_days_from_announce(fmp_ann) if fmp_ann else None
    if fmp_ann_days is not None and fmp_ann_days >= 0:
        if fmp_days is None or fmp_ann_days < fmp_days:
            fmp_days = fmp_ann_days

    # 3) Finnhub (announcement-date proxy)
    finnhub_iso = finnhub_date or _finnhub_next_earnings_date(ticker)
    finnhub_days = _eta_days_from_announce(finnhub_iso)

    # Primary selection
    primary_days, primary_source = None, None
    for src, val in (("edgar", edgar_days), ("fmp", fmp_days), ("finnhub", finnhub_days)):
        if val is not None:
            primary_days, primary_source = val, src
            break

    return {
        "primary_days": primary_days,
        "primary_source": primary_source,
        "primary_label": _fmt_label(primary_days),
        "edgar_days": edgar_days,
        "edgar_label": _fmt_label(edgar_days),
        "fmp_days": fmp_days,
        "fmp_label": _fmt_label(fmp_days),
        "finnhub_days": finnhub_days,
        "finnhub_label": _fmt_label(finnhub_days),
    }


# ── Shared HTML: help-text tooltip ───────────────────────────────────────
#
# The previous `<details>`-based popover has been replaced with a plain-text
# browser tooltip attached via the HTML `title=""` attribute — the direct
# analogue of the locked-quarter-button `_get_help_text()` pattern used by the
# quarter selector (app.py line ~3168). Same ⓘ icon, same content, no custom
# popover DOM, no `<style>` block that has to be juggled around Streamlit's
# `:has(style)` sanitation rule.

import html as _html


def get_filing_eta_help_text(eta: dict) -> str:
    """
    Plain-text tooltip content for the Filing ETA ⓘ icon — the counterpart of
    `_get_help_text()` in app.py for the quarter-selector buttons.

    Returns a multi-line string suitable for an HTML `title=""` attribute.
    Same content as the old `<details>`-based popover:

        Filing ETA sources
        EDGAR ★  ~ filing in 14d
        FMP     n/a
        Finnhub ~ filing in 12d
        ★ = source used · ~ = estimate
    """
    if not eta:
        return ""
    primary_src = (eta.get("primary_source") or "").lower()

    def _row(name: str, src_key: str, label):
        star = " \u2605" if src_key == primary_src else ""
        value = label if label else "n/a"
        return f"{name}{star}: {value}"

    lines = [
        "Filing ETA sources",
        _row("EDGAR",   "edgar",   eta.get("edgar_label")),
        _row("FMP",     "fmp",     eta.get("fmp_label")),
        _row("Finnhub", "finnhub", eta.get("finnhub_label")),
        "\u2605 = source used \u00b7 ~ = estimate",
    ]
    return "\n".join(lines)


def render_eta_info_html(eta: dict, css_class_prefix: str = "qc-eta") -> str:
    """
    Return a small inline HTML snippet: '~ filing in Xd ⓘ' where ⓘ carries a
    browser-native hover tooltip (HTML `title=""`) with the 3-source breakdown.

    This mirrors the locked-quarter-button tooltip style used by
    `_get_help_text()` in app.py: a short, plain-text tooltip on hover. No
    custom `<details>` popover, no `<style>` block in the same markdown call
    (so the `app.py :has(style)` sanitation rule is irrelevant).
    """
    primary = eta.get("primary_label") or ""
    if not primary:
        return ""

    # HTML-escape the tooltip text, then convert real newlines to the numeric
    # character reference `&#10;`. Browsers still render this as a line break
    # inside `title="…"`, but the attribute value no longer contains a literal
    # `\n` — which is critical because Streamlit's markdown renderer tokenises
    # input line-by-line. A literal newline inside an attribute would terminate
    # the current markdown block and blow up the surrounding `<table>` HTML,
    # leaving every row empty.
    help_text = (
        _html.escape(get_filing_eta_help_text(eta), quote=True)
        .replace("\n", "&#10;")
    )

    return (
        f'<span class="{css_class_prefix}-primary">{primary}</span>'
        f'<span class="{css_class_prefix}-info" '
        f'role="img" aria-label="Filing ETA sources" '
        f'title="{help_text}">&#9432;</span>'
    )


# Reusable style block — include once per page. Kept as a separate
# `st.markdown(ETA_INFO_CSS, …)` call so the `:has(style)` sanitation rule in
# app.py only hides this tiny style block, never the surrounding content.
# Only the two classes emitted by `render_eta_info_html` need styling now —
# the old popover CSS is gone along with the popover itself.
ETA_INFO_CSS = """
<style>
.qc-eta-primary {
  color: #fbbf24;
  font-weight: 600;
}
.qc-eta-info {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px; height: 14px;
  margin-left: 4px;
  border-radius: 50%;
  font-size: 11px; line-height: 1;
  color: #93c5fd;
  background: rgba(147,197,253,0.08);
  border: 1px solid rgba(147,197,253,0.35);
  cursor: help;
  transition: background 0.15s ease, color 0.15s ease;
  vertical-align: baseline;
}
.qc-eta-info:hover {
  background: rgba(147,197,253,0.22);
  color: #bfdbfe;
}
</style>
"""
