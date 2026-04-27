"""
Earnings Calendar page for QuarterCharts.
Weekly earnings calendar with day-by-day breakdown.
Data sourced from Finnhub.io API — one call per week, instant loads.
"""

import streamlit as st
import requests
import os
import time
import traceback
from datetime import datetime, timedelta, date

# ── Finnhub API ─────────────────────────────────────────────────────────
_FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
_FINNHUB_BASE = "https://finnhub.io/api/v1"

_DEBUG_LOG: list[str] = []


def _debug(msg: str):
    _DEBUG_LOG.append(f"[{time.strftime('%H:%M:%S')}] {msg}")


def _safe_float(val) -> str:
    if val is None or val == "" or val == "-":
        return "-"
    try:
        v = float(val)
        return f"{v:.2f}" if v != 0 else "0.00"
    except (ValueError, TypeError):
        return str(val)


def _map_hour(h: str) -> str:
    """Map Finnhub 'hour' field to display label."""
    h = (h or "").lower().strip()
    if h == "bmo":
        return "BMO"
    if h == "amc":
        return "AMC"
    if h == "dmh":
        return "TAS"
    return "TNS"


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_week_earnings(from_str: str, to_str: str) -> dict:
    """
    Fetch earnings for a date range from Finnhub. Returns dict: date_str -> list[dict].
    Single API call — fast and reliable.
    """
    result = {}
    from_d = date.fromisoformat(from_str)
    to_d = date.fromisoformat(to_str)
    d = from_d
    while d <= to_d:
        result[d.isoformat()] = []
        d += timedelta(days=1)

    _debug(f"Finnhub API: /calendar/earnings?from={from_str}&to={to_str}")
    t0 = time.time()

    try:
        resp = requests.get(
            f"{_FINNHUB_BASE}/calendar/earnings",
            params={"from": from_str, "to": to_str, "token": _FINNHUB_KEY},
            timeout=10,
        )
        _debug(f"Response: status={resp.status_code}, len={len(resp.text)}")

        if resp.status_code == 200:
            data = resp.json()
            earnings = data.get("earningsCalendar", [])
            _debug(f"Earnings rows: {len(earnings)}")

            for item in earnings:
                row_date = item.get("date", "")
                if row_date not in result:
                    continue
                result[row_date].append({
                    "ticker": item.get("symbol", ""),
                    "company": item.get("symbol", ""),
                    "event": f"Q{item.get('quarter', '?')} {item.get('year', '')} Earnings",
                    "call_time": _map_hour(item.get("hour", "")),
                    "eps_estimate": _safe_float(item.get("epsEstimate")),
                    "eps_actual": _safe_float(item.get("epsActual")),
                    "surprise_pct": _compute_surprise(item.get("epsActual"), item.get("epsEstimate")),
                    "revenue_estimate": item.get("revenueEstimate"),
                    "revenue_actual": item.get("revenueActual"),
                    "date": row_date,
                })
        elif resp.status_code == 429:
            _debug("Rate limited — try again in a minute")
        else:
            _debug(f"Error: {resp.status_code} — {resp.text[:200]}")

    except Exception as e:
        _debug(f"Exception: {e}")
        _debug(traceback.format_exc())

    elapsed = time.time() - t0
    total = sum(len(v) for v in result.values())
    _debug(f"Done: {total} earnings in {elapsed:.2f}s")
    return result


def _compute_surprise(actual, estimate) -> str:
    """Compute EPS surprise % from actual and estimate."""
    if actual is None or estimate is None:
        return "-"
    try:
        a, e = float(actual), float(estimate)
        if e == 0:
            return "-"
        surprise = ((a - e) / abs(e)) * 100
        return f"{surprise:.2f}"
    except (ValueError, TypeError):
        return "-"


# FMP fallback when Finnhub is slow/down. FMP key is shared via env var.
_FMP_KEY = os.environ.get("FMP_API_KEY", "")
_FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _finnhub_ticker_earnings(symbol: str, from_str: str, to_str: str, timeout_s: int) -> dict:
    """Single Finnhub attempt. Returns {'rows': list, 'error': str|None, 'status_code': int|None}."""
    status = None
    try:
        resp = requests.get(
            f"{_FINNHUB_BASE}/calendar/earnings",
            params={"symbol": symbol.upper(), "from": from_str, "to": to_str, "token": _FINNHUB_KEY},
            timeout=timeout_s,
        )
        status = resp.status_code
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception as je:
                return {"rows": [], "error": f"Bad JSON from Finnhub: {je}", "status_code": status}
            results = []
            for item in data.get("earningsCalendar", []) or []:
                results.append({
                    "ticker": item.get("symbol", symbol.upper()),
                    "company": item.get("symbol", symbol.upper()),
                    "event": f"Q{item.get('quarter', '?')} {item.get('year', '')} Earnings",
                    "call_time": _map_hour(item.get("hour", "")),
                    "eps_estimate": _safe_float(item.get("epsEstimate")),
                    "eps_actual": _safe_float(item.get("epsActual")),
                    "surprise_pct": _compute_surprise(item.get("epsActual"), item.get("epsEstimate")),
                    "date": item.get("date", ""),
                })
            return {"rows": results, "error": None, "status_code": status}

        body_snippet = ""
        try:
            body_snippet = (resp.text or "")[:160].strip()
        except Exception:
            body_snippet = ""
        if status == 429:
            err = "Finnhub rate limit hit (HTTP 429)."
        elif status in (401, 403):
            err = f"Finnhub auth error (HTTP {status})."
        elif status and status >= 500:
            err = f"Finnhub server error (HTTP {status})."
        else:
            err = f"Finnhub returned HTTP {status}." + (f" Body: {body_snippet}" if body_snippet else "")
        return {"rows": [], "error": err, "status_code": status}
    except requests.exceptions.Timeout:
        return {"rows": [], "error": "Finnhub request timed out.", "status_code": status}
    except requests.exceptions.RequestException as re:
        return {"rows": [], "error": f"Network error contacting Finnhub: {re}", "status_code": status}
    except Exception as ex:
        return {"rows": [], "error": f"{type(ex).__name__}: {ex}", "status_code": status}


def _fmp_ticker_earnings(symbol: str, timeout_s: int = 20) -> dict:
    """FMP fallback. Returns the same shape as _finnhub_ticker_earnings.
    Uses /historical/earning_calendar/{symbol}, which returns both past and upcoming."""
    if not _FMP_KEY:
        return {"rows": [], "error": "FMP fallback unavailable (no FMP_API_KEY).", "status_code": None}
    status = None
    try:
        resp = requests.get(
            f"{_FMP_BASE}/historical/earning_calendar/{symbol.upper()}",
            params={"apikey": _FMP_KEY},
            timeout=timeout_s,
        )
        status = resp.status_code
        if resp.status_code != 200:
            return {"rows": [], "error": f"FMP returned HTTP {status}.", "status_code": status}
        try:
            rows = resp.json() or []
        except Exception as je:
            return {"rows": [], "error": f"Bad JSON from FMP: {je}", "status_code": status}

        today = date.today()
        cutoff_from = (today - timedelta(days=730)).isoformat()
        cutoff_to = (today + timedelta(days=180)).isoformat()
        results = []
        for item in rows:
            d = (item.get("date") or "")[:10]
            if not d or d < cutoff_from or d > cutoff_to:
                continue
            # FMP 'time': 'bmo' | 'amc' | '' (no TAS/TNS distinction); map best-effort
            ft = (item.get("time") or "").lower().strip()
            if ft == "bmo":
                call_time = "BMO"
            elif ft == "amc":
                call_time = "AMC"
            else:
                call_time = "TNS"
            # Derive quarter/year from the period if present
            period = (item.get("period") or "").upper()  # e.g. "Q1", "Q2"
            # FMP also returns fiscalDateEnding; use it if period missing
            fiscal_end = (item.get("fiscalDateEnding") or "")[:10]
            event_label = f"{period} Earnings" if period else "Earnings"
            if fiscal_end:
                event_label = f"{period} {fiscal_end[:4]} Earnings" if period else f"{fiscal_end[:4]} Earnings"
            results.append({
                "ticker": item.get("symbol", symbol.upper()),
                "company": item.get("symbol", symbol.upper()),
                "event": event_label,
                "call_time": call_time,
                "eps_estimate": _safe_float(item.get("epsEstimated")),
                "eps_actual": _safe_float(item.get("eps")),
                "surprise_pct": _compute_surprise(item.get("eps"), item.get("epsEstimated")),
                "date": d,
            })
        return {"rows": results, "error": None, "status_code": status}
    except requests.exceptions.Timeout:
        return {"rows": [], "error": "FMP request timed out.", "status_code": status}
    except requests.exceptions.RequestException as re:
        return {"rows": [], "error": f"Network error contacting FMP: {re}", "status_code": status}
    except Exception as ex:
        return {"rows": [], "error": f"{type(ex).__name__}: {ex}", "status_code": status}


# Short TTL on failure so transient errors don't stick for 15 minutes; full TTL on success.
@st.cache_data(ttl=60, show_spinner=False)
def _fetch_ticker_earnings_raw(symbol: str) -> dict:
    """
    Fetch earnings for a specific ticker (past 2 years + next 6 months).

    Strategy:
      1. Try Finnhub with a generous timeout.
      2. Retry Finnhub once on timeout / 5xx / connection error (short backoff).
      3. Fall back to FMP's /historical/earning_calendar/{symbol}.
    Returns {'rows': list[dict], 'error': str|None, 'status_code': int|None, 'source': str}.
    The caller uses 'error' to surface actionable feedback when no rows are returned.
    """
    today = date.today()
    from_str = (today - timedelta(days=730)).isoformat()
    to_str = (today + timedelta(days=180)).isoformat()

    # 1) Finnhub primary attempt (25s timeout).
    first = _finnhub_ticker_earnings(symbol, from_str, to_str, timeout_s=25)
    if first.get("rows"):
        return {**first, "source": "finnhub"}

    # 2) Retry Finnhub once if it timed out, 5xx'd, or hit a transient network error.
    err1 = first.get("error") or ""
    status1 = first.get("status_code")
    transient = (
        "timed out" in err1.lower()
        or "network error" in err1.lower()
        or (isinstance(status1, int) and status1 >= 500)
    )
    second = None
    if transient:
        time.sleep(0.6)
        second = _finnhub_ticker_earnings(symbol, from_str, to_str, timeout_s=25)
        if second.get("rows"):
            return {**second, "source": "finnhub"}

    # 3) FMP fallback for any Finnhub failure, OR for an empty-but-successful
    #    Finnhub response (which happens occasionally for valid tickers).
    finnhub_ok_empty = (first.get("error") is None and not first.get("rows"))
    finnhub_failed = (first.get("error") is not None) and (second is None or second.get("error") is not None)
    if finnhub_failed or finnhub_ok_empty:
        fmp = _fmp_ticker_earnings(symbol, timeout_s=20)
        if fmp.get("rows"):
            return {**fmp, "source": "fmp"}
        # Combine errors for diagnostics, prefer the original Finnhub error text.
        combined_err = first.get("error") or (second.get("error") if second else None) or fmp.get("error")
        if finnhub_ok_empty and not fmp.get("error"):
            # Both APIs returned empty — treat as genuine "no data for this ticker".
            return {"rows": [], "error": None, "status_code": first.get("status_code"), "source": "finnhub"}
        return {"rows": [], "error": combined_err, "status_code": first.get("status_code"), "source": "none"}

    # Shouldn't reach here, but return the best info we have.
    return {**first, "source": "finnhub"}


def _fetch_ticker_earnings(symbol: str) -> list[dict]:
    """Back-compat wrapper. Returns just the rows; callers that need the error
    context should use _fetch_ticker_earnings_raw directly."""
    return _fetch_ticker_earnings_raw(symbol).get("rows") or []


# ── Week helpers ──────────────────────────────────────────────────────

def _get_week_start(d: date) -> date:
    """Get Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


def _format_date_range(week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    today = date.today()
    # Determine label
    if week_start <= today <= week_end:
        label = "This Week"
    elif week_start > today:
        label = "Next Week" if (week_start - today).days <= 7 else "Upcoming"
    else:
        label = "Past Week" if (today - week_end).days <= 7 else "Week"
    if week_start.month == week_end.month:
        dates = f"{week_start.strftime('%b %d')} &ndash; {week_end.strftime('%d, %Y')}"
    elif week_start.year == week_end.year:
        dates = f"{week_start.strftime('%b %d')} &ndash; {week_end.strftime('%b %d, %Y')}"
    else:
        dates = f"{week_start.strftime('%b %d, %Y')} &ndash; {week_end.strftime('%b %d, %Y')}"
    return f"{label}: {dates}"


_DAY_MAP = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


# ── Styles ─────────────────────────────────────────────────────────────

_STYLES = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

.ec-hero { text-align: center; padding: 32px 20px 20px; }
.ec-hero h1 {
  font-size: 2.4rem; font-weight: 900;
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; margin: 0 0 6px;
  font-family: Inter, system-ui, sans-serif; letter-spacing: -0.03em;
}
.ec-hero p { font-size: 0.95rem; color: #64748b; margin: 0 0 8px; font-family: Inter, system-ui, sans-serif; }

/* ── Week nav bar ── */
.ec-nav-row {
  display: flex; align-items: center; justify-content: space-between;
  margin: 4px 0 24px; font-family: Inter, system-ui, sans-serif;
}
.ec-nav-btn {
  background: #ffffff; color: #475569; border: 1px solid #e2e8f0;
  border-radius: 10px; padding: 10px 22px; font-size: 0.85rem; font-weight: 600;
  cursor: pointer; transition: all 0.2s ease; text-decoration: none;
  font-family: Inter, system-ui, sans-serif; display: inline-flex; align-items: center; gap: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.ec-nav-btn:hover { background: #f1f5f9; color: #1e293b; border-color: #cbd5e1; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
.ec-date-label {
  font-size: 1.05rem; font-weight: 800; color: #1e293b;
  font-family: Inter, system-ui, sans-serif; white-space: nowrap;
  letter-spacing: -0.01em; display: inline-block;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 10px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* ── Day selector pills ── */
.ec-day-row {
  display: grid; grid-template-columns: repeat(7, 1fr);
  gap: 8px; margin: 0 0 24px; font-family: Inter, system-ui, sans-serif;
}
.ec-day-pill {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 10px 4px; border-radius: 12px; cursor: pointer;
  border: 1px solid #1e293b; background: #0f172a;
  transition: all 0.15s ease; text-decoration: none; min-height: 72px;
}
.ec-day-pill:hover { border-color: #3b82f6; background: rgba(59,130,246,0.06); }
.ec-day-pill.active {
  background: linear-gradient(135deg, #1d4ed8, #2563eb);
  border-color: #3b82f6; box-shadow: 0 2px 12px rgba(59,130,246,0.25);
}
.ec-day-pill .day-name { font-size: 0.72rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
.ec-day-pill.active .day-name { color: rgba(255,255,255,0.7); }
.ec-day-pill .day-num { font-size: 1.15rem; font-weight: 800; color: #e2e8f0; margin: 2px 0; }
.ec-day-pill.active .day-num { color: #fff; }
.ec-day-pill .day-count { font-size: 0.7rem; font-weight: 600; color: #475569; }
.ec-day-pill.active .day-count { color: rgba(255,255,255,0.8); }

/* ── Section header ── */
.ec-section-header { display: flex; align-items: center; gap: 12px; margin: 24px 0 14px; font-family: Inter, system-ui, sans-serif; }
.ec-section-header h2 { font-size: 1.15rem; font-weight: 800; color: #1e293b !important; -webkit-text-fill-color: #1e293b !important; margin: 0; }
.ec-section-header .ec-count-badge {
  background: linear-gradient(135deg, #1e40af, #3b82f6); color: #fff;
  font-size: 0.7rem; font-weight: 700; padding: 3px 12px; border-radius: 20px;
}

/* ── Table ── */
.ec-table-wrap { border-radius: 14px; border: 1px solid #1e293b; overflow: hidden; margin-bottom: 20px; background: #0f172a; }
.ec-table { width: 100%; border-collapse: collapse; font-family: Inter, system-ui, sans-serif; }
.ec-table thead th {
  background: linear-gradient(180deg, #1e293b, #0f172a); color: #64748b;
  font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
  padding: 12px 14px; text-align: left; border-bottom: 1px solid #1e293b;
}
.ec-table tbody tr { border-bottom: 1px solid rgba(30,41,59,0.5); transition: all 0.15s ease; }
.ec-table tbody tr:hover { background: linear-gradient(90deg, rgba(59,130,246,0.06), rgba(59,130,246,0.02)); }
.ec-table tbody td { padding: 11px 14px; font-size: 0.85rem; color: #94a3b8; vertical-align: middle; }
.ec-ticker { color: #60a5fa; font-weight: 700; text-decoration: none; cursor: pointer; font-size: 0.88rem; letter-spacing: 0.02em; }
.ec-ticker:hover { color: #93c5fd; }
.ec-event { color: #475569; font-size: 0.76rem; font-style: italic; }

.ec-badge-bmo { background: rgba(59,130,246,0.12); color: #60a5fa; padding: 3px 10px; border-radius: 8px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em; border: 1px solid rgba(59,130,246,0.2); }
.ec-badge-amc { background: rgba(168,85,247,0.12); color: #c084fc; padding: 3px 10px; border-radius: 8px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em; border: 1px solid rgba(168,85,247,0.2); }
.ec-badge-other { background: rgba(100,116,139,0.1); color: #64748b; padding: 3px 10px; border-radius: 8px; font-size: 0.7rem; font-weight: 600; border: 1px solid rgba(100,116,139,0.15); }

.ec-eps-positive { color: #22c55e; font-weight: 600; }
.ec-eps-negative { color: #ef4444; font-weight: 600; }
.ec-eps-neutral { color: #475569; }
.ec-surprise-positive { color: #22c55e; font-weight: 700; font-size: 0.8rem; background: rgba(34,197,94,0.08); padding: 2px 8px; border-radius: 6px; }
.ec-surprise-negative { color: #ef4444; font-weight: 700; font-size: 0.8rem; background: rgba(239,68,68,0.08); padding: 2px 8px; border-radius: 6px; }

/* ── Empty state ── */
.ec-empty { text-align: center; padding: 48px 20px; font-family: Inter, system-ui, sans-serif; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; margin: 12px 0; }
.ec-empty-icon { font-size: 2rem; margin-bottom: 12px; }
.ec-empty-text { font-size: 1rem; font-weight: 600; color: #64748b; }

/* ── Search banner ── */
.ec-search-banner { background: linear-gradient(135deg, #172554 0%, #1e3a5f 50%, #172554 100%); border: 1px solid rgba(59,130,246,0.3); border-radius: 14px; padding: 18px 22px; margin-top: 24px; margin-bottom: 20px; font-family: Inter, system-ui, sans-serif; }
.ec-search-banner h3 { color: #60a5fa; font-size: 1.05rem; font-weight: 700; margin: 0 0 3px; }
.ec-search-banner p { color: #93c5fd; font-size: 0.82rem; margin: 0; opacity: 0.8; }

/* ── Glossary ── */
.ec-glossary { margin-top: 32px; margin-bottom: 28px; padding: 20px; background: linear-gradient(135deg, #0f172a, #1e293b); border: 1px solid #1e293b; border-radius: 14px; font-family: Inter, system-ui, sans-serif; }
.ec-glossary h4 { color: #64748b; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 14px; }
.ec-glossary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.ec-glossary-item { display: flex; align-items: baseline; gap: 8px; }
.ec-glossary-item .term { color: #94a3b8; font-size: 0.75rem; font-weight: 700; min-width: 40px; }
.ec-glossary-item .def { color: #475569; font-size: 0.72rem; line-height: 1.4; }

@media (max-width: 768px) {
  .ec-hero h1 { font-size: 1.7rem; }
  .ec-day-row { gap: 4px; }
  .ec-day-pill { padding: 8px 2px; min-height: 60px; }
  .ec-day-pill .day-num { font-size: 1rem; }
  .ec-table thead th, .ec-table tbody td { padding: 8px 8px; font-size: 0.78rem; }
  .ec-glossary-grid { grid-template-columns: 1fr; }
  .ec-week-nav .ec-date-label { font-size: 0.85rem; padding: 8px 16px; }
}
</style>"""


# ── Main Render ────────────────────────────────────────────────────────

def render_earnings_page():
    global _DEBUG_LOG
    _DEBUG_LOG = []

    st.markdown(_STYLES, unsafe_allow_html=True)

    # ── Hero ──
    st.markdown(
        '<div class="ec-hero">'
        '<h1>Earnings Calendar</h1>'
        '<p>Track upcoming and recent earnings announcements across the market</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Search bar ──
    st.markdown(
        '<style>'
        'div[data-testid="stTextInput"].ec-search-input input {'
        '  border-radius: 10px !important; border: 1.5px solid #e2e8f0 !important;'
        '  background: #f8fafc !important; padding: 12px 18px !important;'
        '  font-size: 0.95rem !important; color: #334155 !important;'
        '  box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;'
        '}'
        'div[data-testid="stTextInput"].ec-search-input input:focus {'
        '  border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;'
        '}'
        '</style>',
        unsafe_allow_html=True,
    )
    # If a search was just submitted, clear the input and rerun so it appears fresh
    if st.session_state.get("_ec_pending_symbol"):
        pending = st.session_state.pop("_ec_pending_symbol")
        st.session_state["ec_search"] = ""
        st.session_state["_ec_show_symbol"] = pending

    # Check if we should show search results (from a previous submit)
    show_symbol = st.session_state.pop("_ec_show_symbol", None)

    sc1, sc2, sc3 = st.columns([1, 4, 1])
    with sc2:
        search_query = st.text_input(
            "Search",
            placeholder="Search by ticker symbol (e.g. AAPL, MSFT, NVDA)",
            key="ec_search",
            label_visibility="collapsed",
        )

    st.markdown('<div style="margin-bottom:20px;"></div>', unsafe_allow_html=True)

    if search_query and search_query.strip():
        # Store the symbol and rerun so the input clears
        st.session_state["_ec_pending_symbol"] = search_query.strip().upper()
        st.rerun()

    if show_symbol:
        _render_ticker_search(show_symbol)
        _render_footer()
        _render_debug()
        return

    # ── Week navigation ──
    today = date.today()
    if "ec_week_offset" not in st.session_state:
        st.session_state.ec_week_offset = 0

    week_start = _get_week_start(today) + timedelta(weeks=st.session_state.ec_week_offset)
    week_end = week_start + timedelta(days=6)

    # Style the Prev / Next buttons to match new design
    st.markdown(
        '<style>'
        '.ec-nav-wrap [data-testid="stHorizontalBlock"] { margin-bottom: 20px !important; }'
        '.ec-nav-wrap button[kind="secondary"] {'
        '  background: #ffffff !important; color: #475569 !important;'
        '  border: 1px solid #e2e8f0 !important; border-radius: 10px !important;'
        '  padding: 10px 22px !important; font-size: 0.85rem !important;'
        '  font-weight: 600 !important; box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;'
        '  transition: all 0.2s ease !important;'
        '}'
        '.ec-nav-wrap button[kind="secondary"]:hover {'
        '  background: #f1f5f9 !important; color: #1e293b !important;'
        '  border-color: #cbd5e1 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;'
        '}'
        '</style>',
        unsafe_allow_html=True,
    )

    # Prev / Date label / Next — single row
    nav_container = st.container()
    with nav_container:
        st.markdown('<div class="ec-nav-wrap">', unsafe_allow_html=True)
        nav_l, nav_center, nav_r = st.columns([1, 5, 1])
        with nav_l:
            if st.button("\u2190 Prev", key="ec_prev", width='stretch'):
                st.session_state.ec_week_offset -= 1
                st.rerun()
        with nav_center:
            st.markdown(
                f'<div style="text-align:center;padding-top:4px;">'
                f'<span class="ec-date-label">{_format_date_range(week_start)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with nav_r:
            if st.button("Next \u2192", key="ec_next", width='stretch'):
                st.session_state.ec_week_offset += 1
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Fetch week data (single Finnhub API call, cached 15 min) ──
    _debug(f"Fetching: {week_start.isoformat()} to {week_end.isoformat()}")
    try:
        with st.spinner("Loading earnings data..."):
            week_data = _fetch_week_earnings(week_start.isoformat(), week_end.isoformat())
        total = sum(len(v) for v in week_data.values())
        _debug(f"Result: {total} total earnings across 7 days")
    except Exception as e:
        _debug(f"FATAL: {e}")
        _debug(traceback.format_exc())
        week_data = {(week_start + timedelta(days=i)).isoformat(): [] for i in range(7)}

    # ── Day selector (HTML pills — uniform size) ──
    days_in_week = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        count = len(week_data.get(d.isoformat(), []))
        days_in_week.append((d, count))

    if "ec_selected_day" not in st.session_state:
        st.session_state.ec_selected_day = None

    selected_day = st.session_state.ec_selected_day
    if selected_day:
        try:
            sel = date.fromisoformat(selected_day)
            if sel < week_start or sel > week_end:
                selected_day = None
        except Exception:
            selected_day = None

    if not selected_day:
        if week_start <= today <= week_end:
            selected_day = today.isoformat()
        else:
            for d, count in days_in_week:
                if count > 0:
                    selected_day = d.isoformat()
                    break
            if not selected_day:
                selected_day = (week_start + timedelta(days=1)).isoformat()

    # Inject CSS to make all day buttons the same height
    st.markdown(
        '<style>'
        '[data-testid="stHorizontalBlock"] button[kind="secondary"],'
        '[data-testid="stHorizontalBlock"] button[kind="primary"] {'
        '  min-height: 52px !important; white-space: nowrap !important;'
        '}</style>',
        unsafe_allow_html=True,
    )

    # Build day pills — short labels that never wrap: "Mon 30 · 207"
    day_cols = st.columns(7)
    for i, (d, count) in enumerate(days_in_week):
        with day_cols[i]:
            is_active = d.isoformat() == selected_day
            wd = d.weekday()
            day_name = _DAY_MAP[wd]
            label = f"{day_name} {d.day}"

            if st.button(
                label,
                key=f"ec_day_{d.isoformat()}",
                width='stretch',
                type="primary" if is_active else "secondary",
            ):
                st.session_state.ec_selected_day = d.isoformat()
                st.rerun()

    # ── Selected day table ──
    try:
        sel_date = date.fromisoformat(selected_day)
    except Exception:
        sel_date = today

    day_earnings = week_data.get(selected_day, [])
    wd = sel_date.weekday()
    day_title = f"Earnings on {_DAY_MAP[wd]}, {sel_date.strftime('%B')} {sel_date.day}"

    count_badge = (
        f'<span class="ec-count-badge">{len(day_earnings)} report{"s" if len(day_earnings) != 1 else ""}</span>'
        if day_earnings else ''
    )
    st.markdown(
        f'<div class="ec-section-header"><h2>{day_title}</h2>{count_badge}</div>',
        unsafe_allow_html=True,
    )

    if not day_earnings:
        st.markdown(
            f'<div class="ec-empty">'
            f'<div class="ec-empty-icon">\U0001f515</div>'
            f'<div class="ec-empty-text">No reports scheduled</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        _render_earnings_table(day_earnings)

    _render_debug()
    _render_footer()


def _render_debug():
    # Debug diagnostics hidden from users; _DEBUG_LOG still collected internally
    pass


def _render_ticker_search(symbol: str):
    st.markdown(
        f'<div class="ec-search-banner">'
        f'<h3>Earnings for {symbol}</h3>'
        f'<p>Showing upcoming and recent earnings dates</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.spinner(f"Fetching earnings for {symbol}..."):
        fetch = _fetch_ticker_earnings_raw(symbol)
    results = fetch.get("rows") or []

    if not results:
        err = fetch.get("error")
        if err:
            # API/network failure — give the user something actionable instead of
            # the misleading "Verify the ticker symbol" message.
            st.error(
                f"Couldn't load earnings for **{symbol}** right now. {err}\n\n"
                "This is a temporary data-source issue; please retry in a moment."
            )
        else:
            st.info(
                f"No earnings data found for **{symbol}**. "
                "Verify the ticker symbol and try again."
            )
        return

    today_str = date.today().isoformat()
    upcoming = sorted([r for r in results if r["date"] >= today_str], key=lambda r: r["date"])
    past = sorted([r for r in results if r["date"] < today_str], key=lambda r: r["date"], reverse=True)

    if upcoming:
        st.markdown(
            f'<div class="ec-section-header"><h2>Upcoming Earnings</h2>'
            f'<span class="ec-count-badge">{len(upcoming)}</span></div>',
            unsafe_allow_html=True,
        )
        _render_earnings_table(upcoming, show_date=True)

    if past:
        st.markdown(
            f'<div class="ec-section-header"><h2>Past Earnings</h2>'
            f'<span class="ec-count-badge">{len(past)}</span></div>',
            unsafe_allow_html=True,
        )
        _render_earnings_table(past, show_date=True)


def _compute_filing_eta_sources(ticker: str, event_label: str, finnhub_date_str: str) -> dict:
    """
    Unified 3-source filing-ETA lookup via filing_eta.get_filing_eta().
    Returns the full source dict (primary_days / edgar_days / fmp_days / finnhub_days
    plus matching labels). Empty dict on failure.
    """
    try:
        from filing_eta import get_filing_eta
        return get_filing_eta(ticker, event_label=event_label, finnhub_date=finnhub_date_str) or {}
    except Exception:
        return {}


def _render_earnings_table(earnings: list[dict], show_date: bool = False, show_filing_eta: bool | None = None):
    """
    Render the earnings table.

    - show_date=True: adds a Date column. For future rows, the date is followed
      inline by `~ filing in Xd ⓘ` (search view — rows have heterogeneous dates).
    - show_filing_eta=True: adds a dedicated "Filing" column showing just
      `~ filing in Xd ⓘ` for future rows. Used by the weekly day view where
      every row shares the selected day, so a Date column would be redundant
      but the per-ticker filing ETA is still useful.
    - If show_filing_eta is None it defaults to False when show_date=True (the
      inline format already covers it) and True when show_date=False (so the
      weekly view always shows the 3-source ETA — see docs/filing-eta-rules.md).
    """
    _auth_params = ""
    if st.session_state.get("session_token"):
        _auth_params = f"&_sid={st.session_state.session_token}"

    # Default: inline ETA is enough when show_date=True; otherwise add a column.
    if show_filing_eta is None:
        show_filing_eta = not show_date

    order = {"BMO": 0, "AMC": 1, "TAS": 2, "TNS": 3}
    earnings_sorted = sorted(earnings, key=lambda x: (order.get(x.get("call_time", "TNS"), 3), x.get("ticker", "")))

    _today_iso = date.today().isoformat()

    rows_html = ""
    for e in earnings_sorted:
        ticker = e.get("ticker", "")
        event = e.get("event", "")
        call_time = e.get("call_time", "-")
        eps_est = e.get("eps_estimate", "-")
        eps_actual = e.get("eps_actual", "-")
        surprise = e.get("surprise_pct", "-")

        if call_time == "BMO":
            badge = '<span class="ec-badge-bmo">BMO</span>'
        elif call_time == "AMC":
            badge = '<span class="ec-badge-amc">AMC</span>'
        else:
            badge = f'<span class="ec-badge-other">{call_time}</span>'

        eps_est_html = f'<span class="ec-eps-neutral">{eps_est}</span>'

        if eps_actual != "-":
            try:
                val = float(eps_actual)
                cls = "ec-eps-positive" if val >= 0 else "ec-eps-negative"
                eps_actual_html = f'<span class="{cls}">{eps_actual}</span>'
            except (ValueError, TypeError):
                eps_actual_html = f'<span class="ec-eps-neutral">{eps_actual}</span>'
        else:
            eps_actual_html = '<span class="ec-eps-neutral">&ndash;</span>'

        if surprise != "-":
            try:
                val = float(surprise)
                cls = "ec-surprise-positive" if val >= 0 else "ec-surprise-negative"
                sign = "+" if val > 0 else ""
                surprise_html = f'<span class="{cls}">{sign}{surprise}%</span>'
            except (ValueError, TypeError):
                surprise_html = f'<span class="ec-eps-neutral">{surprise}</span>'
        else:
            surprise_html = '<span class="ec-eps-neutral">&ndash;</span>'

        ticker_link = f'/?page=charts&ticker={ticker}{_auth_params}'

        _d_str = e.get("date", "") or ""

        # Compute the 3-source ETA inner HTML once per row; reused by either
        # the inline-Date path or the dedicated Filing column.
        _eta_inner = ""
        if _d_str and _d_str >= _today_iso and (show_date or show_filing_eta):
            try:
                _eta_sources = _compute_filing_eta_sources(ticker, event, _d_str)
                if _eta_sources and _eta_sources.get("primary_label"):
                    try:
                        from filing_eta import render_eta_info_html
                        _eta_inner = render_eta_info_html(_eta_sources) or ""
                    except Exception:
                        _eta_inner = ""
            except Exception:
                _eta_inner = ""

        _eta_suffix_html = f' &middot; {_eta_inner}' if (show_date and _eta_inner) else ''
        date_col = f'<td>{_d_str}{_eta_suffix_html}</td>' if show_date else ''

        filing_col = ''
        if show_filing_eta:
            filing_col = (
                f'<td>{_eta_inner}</td>'
                if _eta_inner
                else '<td><span class="ec-eps-neutral">&ndash;</span></td>'
            )

        rows_html += (
            f'<tr><td><a class="ec-ticker" href="{ticker_link}" target="_self">{ticker}</a></td>'
            f'<td><span class="ec-event">{event}</span></td>{date_col}'
            f'<td>{badge}</td><td>{eps_est_html}</td>'
            f'<td>{eps_actual_html}</td><td>{surprise_html}</td>{filing_col}</tr>'
        )

    date_th = '<th>Date</th>' if show_date else ''
    filing_th = '<th>Filing</th>' if show_filing_eta else ''

    # IMPORTANT: inject ETA_INFO_CSS in a SEPARATE st.markdown call from the
    # table HTML. app.py has a CSS rule (line ~145) that hides any
    # stElementContainer containing a <style> tag via
    # `position:absolute; height:0; overflow:hidden`. If we concatenate the
    # <style> with the table HTML into one markdown block, the CSS rule
    # collapses the whole table to zero height — rows are in the DOM but
    # invisible. Emitting the <style> alone lets that rule hide only the style
    # block (its intended purpose), leaving the table container in normal flow.
    try:
        from filing_eta import ETA_INFO_CSS as _eta_css
        if _eta_css:
            st.markdown(_eta_css, unsafe_allow_html=True)
    except Exception:
        pass

    table_html = (
        f'<div class="ec-table-wrap"><table class="ec-table"><thead><tr>'
        f'<th>Symbol</th><th>Event</th>{date_th}'
        f'<th>Call Time</th><th>EPS Est.</th><th>Reported</th><th>Surprise</th>{filing_th}'
        f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


def _render_footer():
    st.markdown(
        '<div class="ec-glossary"><h4>Glossary</h4><div class="ec-glossary-grid">'
        '<div class="ec-glossary-item"><span class="term">BMO</span><span class="def">Before Market Open &mdash; reported before 9:30 AM ET</span></div>'
        '<div class="ec-glossary-item"><span class="term">AMC</span><span class="def">After Market Close &mdash; reported after 4:00 PM ET</span></div>'
        '<div class="ec-glossary-item"><span class="term">TAS</span><span class="def">During Market Hours</span></div>'
        '<div class="ec-glossary-item"><span class="term">TNS</span><span class="def">Time Not Supplied &mdash; exact time not announced</span></div>'
        '<div class="ec-glossary-item"><span class="term">EPS Est.</span><span class="def">Consensus analyst estimate for Earnings Per Share</span></div>'
        '<div class="ec-glossary-item"><span class="term">Reported</span><span class="def">Actual EPS reported by the company</span></div>'
        '<div class="ec-glossary-item"><span class="term">Surprise</span><span class="def">% difference between reported and estimated EPS</span></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p style="margin-top:24px; font-size:0.82rem; color:#94a3b8; line-height:1.6; font-family:Inter,system-ui,sans-serif;">'
        'Earnings data powered by Finnhub.io. Dates, estimates, and reported figures are for '
        'informational purposes only. QuarterCharts does not guarantee accuracy or completeness. '
        'This is not financial advice &mdash; verify with official SEC EDGAR filings and company IR pages.'
        '</p>',
        unsafe_allow_html=True,
    )
