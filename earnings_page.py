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
_FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "d77c5b1r01qp6afl34h0d77c5b1r01qp6afl34hg")
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


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_ticker_earnings(symbol: str) -> list[dict]:
    """Fetch earnings for a specific ticker from Finnhub (past 2 years + next 6 months)."""
    today = date.today()
    from_str = (today - timedelta(days=730)).isoformat()
    to_str = (today + timedelta(days=180)).isoformat()

    try:
        resp = requests.get(
            f"{_FINNHUB_BASE}/calendar/earnings",
            params={"symbol": symbol.upper(), "from": from_str, "to": to_str, "token": _FINNHUB_KEY},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("earningsCalendar", []):
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
            return results
    except Exception:
        pass
    return []


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
  letter-spacing: -0.01em;
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
.ec-empty { text-align: center; padding: 56px 20px; font-family: Inter, system-ui, sans-serif; }
.ec-empty-icon { font-size: 2.5rem; margin-bottom: 14px; opacity: 0.4; }
.ec-empty-text { font-size: 0.95rem; font-weight: 500; color: #475569; }
.ec-empty-sub { font-size: 0.82rem; color: #334155; margin-top: 4px; }

/* ── Search banner ── */
.ec-search-banner { background: linear-gradient(135deg, #172554 0%, #1e3a5f 50%, #172554 100%); border: 1px solid rgba(59,130,246,0.3); border-radius: 14px; padding: 18px 22px; margin-bottom: 20px; font-family: Inter, system-ui, sans-serif; }
.ec-search-banner h3 { color: #60a5fa; font-size: 1.05rem; font-weight: 700; margin: 0 0 3px; }
.ec-search-banner p { color: #93c5fd; font-size: 0.82rem; margin: 0; opacity: 0.8; }

/* ── Glossary ── */
.ec-glossary { margin-top: 32px; padding: 20px; background: linear-gradient(135deg, #0f172a, #1e293b); border: 1px solid #1e293b; border-radius: 14px; font-family: Inter, system-ui, sans-serif; }
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
    sc1, sc2, sc3 = st.columns([1, 3, 1])
    with sc2:
        search_query = st.text_input(
            "Search",
            placeholder="Search by ticker symbol (e.g. AAPL, MSFT, NVDA)",
            key="ec_search",
            label_visibility="collapsed",
        )

    if search_query and search_query.strip():
        _render_ticker_search(search_query.strip().upper())
        _render_footer()
        _render_debug()
        return

    # ── Week navigation ──
    today = date.today()
    if "ec_week_offset" not in st.session_state:
        st.session_state.ec_week_offset = 0

    week_start = _get_week_start(today) + timedelta(weeks=st.session_state.ec_week_offset)
    week_end = week_start + timedelta(days=6)

    # Date range — standalone centered line
    st.markdown(
        f'<div style="text-align:center;margin:8px 0 4px;">'
        f'<span class="ec-date-label">{_format_date_range(week_start)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

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

    # Prev / Next — separate row with spacing below
    nav_container = st.container()
    with nav_container:
        st.markdown('<div class="ec-nav-wrap">', unsafe_allow_html=True)
        nav_l, nav_spacer, nav_r = st.columns([1, 5, 1])
        with nav_l:
            if st.button("\u2190 Prev", key="ec_prev", use_container_width=True):
                st.session_state.ec_week_offset -= 1
                st.rerun()
        with nav_r:
            if st.button("Next \u2192", key="ec_next", use_container_width=True):
                st.session_state.ec_week_offset += 1
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    # Add spacing between nav and day pills
    st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

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
            day_abbr = _DAY_MAP[wd][:2]
            count_text = str(count) if count > 0 else "-"
            label = f"{day_abbr}{d.day} · {count_text}"

            if st.button(
                label,
                key=f"ec_day_{d.isoformat()}",
                use_container_width=True,
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
            f'<div class="ec-empty-icon">📊</div>'
            f'<div class="ec-empty-text">No earnings reports scheduled</div>'
            f'<div class="ec-empty-sub">{_DAY_MAP[wd]}, {sel_date.strftime("%B %d, %Y")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        _render_earnings_table(day_earnings)

    _render_debug()
    _render_footer()


def _render_debug():
    with st.expander("Data fetch diagnostics", expanded=False):
        if _DEBUG_LOG:
            for line in _DEBUG_LOG:
                st.code(line, language=None)
        else:
            st.caption("No debug messages — data served from cache.")


def _render_ticker_search(symbol: str):
    st.markdown(
        f'<div class="ec-search-banner">'
        f'<h3>Earnings for {symbol}</h3>'
        f'<p>Showing upcoming and recent earnings dates</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.spinner(f"Fetching earnings for {symbol}..."):
        results = _fetch_ticker_earnings(symbol)

    if not results:
        st.info(f"No earnings data found for **{symbol}**. Verify the ticker symbol and try again.")
        return

    today_str = date.today().isoformat()
    upcoming = [r for r in results if r["date"] >= today_str]
    past = [r for r in results if r["date"] < today_str]

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


def _render_earnings_table(earnings: list[dict], show_date: bool = False):
    _auth_params = ""
    if st.session_state.get("session_token"):
        _auth_params = f"&_sid={st.session_state.session_token}"

    order = {"BMO": 0, "AMC": 1, "TAS": 2, "TNS": 3}
    earnings_sorted = sorted(earnings, key=lambda x: (order.get(x.get("call_time", "TNS"), 3), x.get("ticker", "")))

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
        date_col = f'<td>{e.get("date", "")}</td>' if show_date else ''

        rows_html += (
            f'<tr><td><a class="ec-ticker" href="{ticker_link}" target="_self">{ticker}</a></td>'
            f'<td><span class="ec-event">{event}</span></td>{date_col}'
            f'<td>{badge}</td><td>{eps_est_html}</td>'
            f'<td>{eps_actual_html}</td><td>{surprise_html}</td></tr>'
        )

    date_th = '<th>Date</th>' if show_date else ''

    table_html = (
        f'<div class="ec-table-wrap"><table class="ec-table"><thead><tr>'
        f'<th>Symbol</th><th>Event</th>{date_th}'
        f'<th>Call Time</th><th>EPS Est.</th><th>Reported</th><th>Surprise</th>'
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

    st.caption(
        "Earnings data powered by Finnhub.io. Dates, estimates, and reported figures are for "
        "informational purposes only. QuarterCharts does not guarantee accuracy or completeness. "
        "This is not financial advice — verify with official SEC EDGAR filings and company IR pages."
    )
