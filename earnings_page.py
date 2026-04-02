"""
Earnings Calendar page for QuarterCharts.
Weekly earnings calendar with day-by-day breakdown, matching Yahoo Finance features.
Data sourced from Yahoo Finance via yfinance library.
"""

import streamlit as st
import pandas as pd
import requests
import json
import time
import hashlib
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── In-memory cache with TTL ────────────────────────────────────────────
_EARNINGS_CACHE: dict = {}      # key -> (timestamp, data)
_CACHE_TTL = 900                # 15 min TTL — earnings dates rarely change intraday


def _cache_key(d: date) -> str:
    return f"earnings_{d.isoformat()}"


def _get_cached(key: str):
    if key in _EARNINGS_CACHE:
        ts, data = _EARNINGS_CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return data
        del _EARNINGS_CACHE[key]
    return None


def _set_cached(key: str, data):
    _EARNINGS_CACHE[key] = (time.time(), data)


# ── Yahoo Finance Earnings Fetcher ──────────────────────────────────────
# Uses yfinance library (handles auth/crumb internally) as primary source,
# with a screener API fallback. Avoids direct HTML scraping which gets
# blocked from server IPs.


def _fetch_earnings_for_date(target_date: date) -> list[dict]:
    """
    Fetch earnings for a single date.
    Primary: yfinance screener API. Fallback: yfinance ticker calendar.
    """
    cache_key = _cache_key(target_date)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    results = _fetch_via_yf_screener(target_date)

    _set_cached(cache_key, results)
    return results


def _fetch_via_yf_screener(target_date: date) -> list[dict]:
    """
    Use yfinance's internal session to query the Yahoo Finance screener
    for earnings on a specific date. This works server-side because
    yfinance handles crumb/cookie auth.
    """
    results = []

    try:
        import yfinance as yf

        # yfinance exposes a shared session with valid crumb+cookies
        # Use it to hit the screener endpoint
        session = yf.utils.get_yf_logger  # just to trigger module init
        # Build a session with proper Yahoo auth
        yf_session = requests.Session()
        yf_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36",
        })

        # Step 1: Get crumb and cookies from Yahoo
        try:
            yf_session.get("https://fc.yahoo.com", timeout=5)
        except Exception:
            pass
        crumb_resp = yf_session.get(
            "https://query2.finance.yahoo.com/v1/test/getcrumb",
            timeout=5,
        )
        crumb = crumb_resp.text.strip() if crumb_resp.status_code == 200 else ""

        if not crumb:
            return []

        # Step 2: Query the screener for earnings on this date
        date_str = target_date.strftime("%Y-%m-%d")
        # Unix timestamps for start/end of day
        from datetime import timezone as tz
        day_start = int(datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz.utc).timestamp())
        day_end = int(datetime.combine(target_date, datetime.max.time()).replace(tzinfo=tz.utc).timestamp())

        payload = {
            "offset": 0,
            "size": 100,
            "sortField": "companyshortname",
            "sortType": "ASC",
            "quoteType": "EQUITY",
            "query": {
                "operator": "and",
                "operands": [
                    {"operator": "eq", "operands": ["region", "us"]},
                    {"operator": "gte", "operands": ["earnings_date", day_start]},
                    {"operator": "lte", "operands": ["earnings_date", day_end]},
                ],
            },
            "userId": "",
            "userIdType": "guid",
        }

        resp = yf_session.post(
            f"https://query2.finance.yahoo.com/v1/finance/screener?crumb={crumb}",
            json=payload,
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
            for q in quotes:
                ticker = q.get("symbol", "")
                if not ticker:
                    continue

                # Determine call time from earningsTimestamp vs market hours
                call_time = "-"
                earn_ts = q.get("earningsTimestamp")
                if earn_ts:
                    from datetime import timezone as tz2
                    earn_dt = datetime.fromtimestamp(earn_ts, tz=tz2.utc)
                    hour_et = (earn_dt.hour - 5) % 24  # rough UTC to ET
                    if hour_et < 10:
                        call_time = "BMO"
                    elif hour_et >= 16:
                        call_time = "AMC"
                    else:
                        call_time = "TAS"

                # Get EPS data
                eps_est = q.get("epsForward") or q.get("epsCurrentYear")
                eps_trail = q.get("epsTrailingTwelveMonths")

                results.append({
                    "ticker": ticker,
                    "company": q.get("shortName") or q.get("longName") or ticker,
                    "event": "Earnings Announcement",
                    "call_time": call_time,
                    "eps_estimate": _safe_float(eps_est),
                    "eps_actual": "-",
                    "surprise_pct": "-",
                    "date": target_date.isoformat(),
                })

        return results

    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


def _safe_float(val) -> str:
    if val is None or val == "" or val == "-" or val == "N/A":
        return "-"
    try:
        v = float(str(val).replace(",", ""))
        return f"{v:.2f}" if v != 0 else "0.00"
    except (ValueError, TypeError):
        return str(val)


def _normalize_yf_row(item: dict, target_date: date) -> dict | None:
    """Normalize a Yahoo Finance JSON row to our standard format."""
    try:
        ticker = item.get("ticker") or item.get("symbol") or ""
        if not ticker:
            return None

        return {
            "ticker": ticker.upper(),
            "company": item.get("companyshortname") or item.get("companyShortName") or item.get("shortName") or ticker,
            "event": item.get("eventname") or item.get("eventName") or "Earnings Announcement",
            "call_time": _map_call_time(item.get("startdatetimetype") or item.get("startDateTimeType") or ""),
            "eps_estimate": _safe_float(item.get("epsestimate") or item.get("epsEstimate")),
            "eps_actual": _safe_float(item.get("epsactual") or item.get("epsActual")),
            "surprise_pct": _safe_float(item.get("epssurprisepct") or item.get("epsSurprisePct")),
            "date": target_date.isoformat(),
        }
    except Exception:
        return None


def _map_call_time(raw: str) -> str:
    """Map Yahoo's startdatetimetype to readable call time."""
    raw = raw.upper().strip()
    if raw in ("BMO", "BEFORE_MARKET_OPEN", "PREMARKET"):
        return "BMO"
    if raw in ("AMC", "AFTER_MARKET_CLOSE", "AFTERMARKET"):
        return "AMC"
    if raw in ("TNS", "TIME_NOT_SUPPLIED"):
        return "TNS"
    if raw in ("TAS", "DURING_MARKET"):
        return "TAS"
    return "-"


# ── yfinance fallback for single-ticker search ─────────────────────────

def _fetch_ticker_earnings(symbol: str) -> list[dict]:
    """Fetch earnings dates for a specific ticker using yfinance."""
    cache_key = f"ticker_earnings_{symbol.upper()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf
        tk = yf.Ticker(symbol.upper())
        cal = tk.get_earnings_dates(limit=12)
        if cal is None or cal.empty:
            _set_cached(cache_key, [])
            return []

        results = []
        for idx, row in cal.iterrows():
            d = idx.date() if hasattr(idx, 'date') else idx
            results.append({
                "ticker": symbol.upper(),
                "company": tk.info.get("shortName", symbol.upper()) if hasattr(tk, 'info') else symbol.upper(),
                "event": "Earnings Announcement",
                "call_time": "-",
                "eps_estimate": _safe_float(row.get("EPS Estimate")),
                "eps_actual": _safe_float(row.get("Reported EPS")),
                "surprise_pct": _safe_float(row.get("Surprise(%)")),
                "date": str(d),
            })

        _set_cached(cache_key, results)
        return results

    except Exception:
        _set_cached(cache_key, [])
        return []


# ── Parallel fetch for a week ───────────────────────────────────────────

def _fetch_week_earnings(week_start: date) -> dict[str, list[dict]]:
    """
    Fetch earnings for an entire week (Mon-Fri) using parallel requests.
    Returns dict mapping date_str -> list of earnings rows.
    """
    days = []
    for i in range(7):  # Sun through Sat
        d = week_start + timedelta(days=i)
        days.append(d)

    result = {}
    # Check cache first to minimize network calls
    uncached_days = []
    for d in days:
        ck = _cache_key(d)
        c = _get_cached(ck)
        if c is not None:
            result[d.isoformat()] = c
        else:
            uncached_days.append(d)

    if uncached_days:
        # Parallel fetch uncached days (max 3 workers to be respectful)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(_fetch_earnings_for_date, d): d for d in uncached_days}
            for future in as_completed(futures):
                d = futures[future]
                try:
                    data = future.result()
                    result[d.isoformat()] = data
                except Exception:
                    result[d.isoformat()] = []

    return result


# ── Week calculation helpers ────────────────────────────────────────────

def _get_week_start(d: date) -> date:
    """Get Sunday of the week containing date d."""
    return d - timedelta(days=d.weekday() + 1) if d.weekday() != 6 else d


def _format_date_range(week_start: date) -> str:
    """Format 'Mar 29, 2026 - Apr 4, 2026'."""
    week_end = week_start + timedelta(days=6)
    if week_start.month == week_end.month:
        return f"{week_start.strftime('%b %d')} - {week_end.strftime('%d, %Y')}"
    elif week_start.year == week_end.year:
        return f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
    else:
        return f"{week_start.strftime('%b %d, %Y')} - {week_end.strftime('%b %d, %Y')}"


# ── Page Styles ─────────────────────────────────────────────────────────

_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.ec-hero {
    text-align: center;
    padding: 32px 20px 16px;
}
.ec-hero h1 {
    font-size: 2rem;
    font-weight: 800;
    color: #f8fafc;
    margin: 0 0 6px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-hero p {
    font-size: 0.95rem;
    color: #94a3b8;
    margin: 0;
    font-family: Inter, system-ui, sans-serif;
}

/* Week nav bar */
.ec-week-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    margin: 20px 0 24px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-week-nav .ec-arrow {
    width: 36px; height: 36px;
    border-radius: 8px;
    border: 1px solid #334155;
    background: #1e293b;
    color: #94a3b8;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 16px;
    text-decoration: none;
}
.ec-arrow:hover { background: #334155; color: #f1f5f9; }
.ec-date-range {
    font-size: 1rem;
    font-weight: 600;
    color: #e2e8f0;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 8px 20px;
    font-family: Inter, system-ui, sans-serif;
}

/* Day selector cards */
.ec-days-row {
    display: flex;
    gap: 10px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 24px;
}
.ec-day-card {
    min-width: 140px;
    padding: 14px 18px;
    border-radius: 12px;
    border: 2px solid #334155;
    background: #1e293b;
    text-align: left;
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: Inter, system-ui, sans-serif;
    text-decoration: none;
    display: block;
}
.ec-day-card:hover { border-color: #3b82f6; transform: translateY(-1px); }
.ec-day-card.active {
    border-color: #3b82f6;
    background: #172554;
    box-shadow: 0 0 20px rgba(59,130,246,0.15);
}
.ec-day-label {
    font-size: 0.85rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 6px;
}
.ec-day-count {
    font-size: 0.78rem;
    color: #3b82f6;
    font-weight: 600;
}
.ec-day-count::before {
    content: '';
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #3b82f6;
    margin-right: 6px;
    vertical-align: middle;
}

/* Earnings table */
.ec-table-wrap {
    border-radius: 12px;
    border: 1px solid #1e293b;
    overflow: hidden;
    margin-bottom: 24px;
}
.ec-table-header {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f1f5f9;
    padding: 16px 20px 12px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-table {
    width: 100%;
    border-collapse: collapse;
    font-family: Inter, system-ui, sans-serif;
}
.ec-table thead th {
    background: #0f172a;
    color: #94a3b8;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 10px 16px;
    text-align: left;
    border-bottom: 1px solid #1e293b;
    position: sticky;
    top: 0;
}
.ec-table tbody tr {
    border-bottom: 1px solid #1e293b;
    transition: background 0.1s;
}
.ec-table tbody tr:hover { background: #172554; }
.ec-table tbody td {
    padding: 12px 16px;
    font-size: 0.88rem;
    color: #cbd5e1;
    vertical-align: middle;
}
.ec-ticker {
    color: #3b82f6;
    font-weight: 700;
    text-decoration: none;
    cursor: pointer;
}
.ec-ticker:hover { color: #60a5fa; text-decoration: underline; }
.ec-company { color: #e2e8f0; font-weight: 500; }
.ec-event { color: #94a3b8; font-size: 0.82rem; }
.ec-badge-bmo {
    background: #1e3a5f;
    color: #60a5fa;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.03em;
}
.ec-badge-amc {
    background: #3b1f4a;
    color: #c084fc;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.03em;
}
.ec-badge-other {
    background: #1e293b;
    color: #64748b;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
}
.ec-eps-positive { color: #22c55e; font-weight: 600; }
.ec-eps-negative { color: #ef4444; font-weight: 600; }
.ec-eps-neutral { color: #94a3b8; }
.ec-surprise-positive { color: #22c55e; font-weight: 600; font-size: 0.82rem; }
.ec-surprise-negative { color: #ef4444; font-weight: 600; font-size: 0.82rem; }

/* Empty state */
.ec-empty {
    text-align: center;
    padding: 48px 20px;
    color: #64748b;
    font-family: Inter, system-ui, sans-serif;
}
.ec-empty-icon { font-size: 2.5rem; margin-bottom: 12px; }
.ec-empty-text { font-size: 1rem; font-weight: 500; }

/* Footer notes */
.ec-footer-notes {
    margin-top: 32px;
    padding: 20px 24px;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-footer-notes h4 {
    color: #94a3b8;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 10px;
}
.ec-footer-notes p, .ec-footer-notes li {
    color: #64748b;
    font-size: 0.78rem;
    line-height: 1.6;
    margin: 0 0 6px;
}
.ec-footer-notes ul { padding-left: 16px; margin: 0; }

/* Search result banner */
.ec-search-banner {
    background: linear-gradient(135deg, #172554, #1e3a5f);
    border: 1px solid #1e40af;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-search-banner h3 {
    color: #60a5fa;
    font-size: 1rem;
    font-weight: 700;
    margin: 0 0 4px;
}
.ec-search-banner p {
    color: #93c5fd;
    font-size: 0.85rem;
    margin: 0;
}

@media (max-width: 768px) {
    .ec-hero h1 { font-size: 1.5rem; }
    .ec-day-card { min-width: 100px; padding: 10px 12px; }
    .ec-table thead th, .ec-table tbody td { padding: 8px 10px; font-size: 0.8rem; }
    .ec-days-row { gap: 6px; }
}
</style>
"""


# ── Main Render Function ────────────────────────────────────────────────

def render_earnings_page():
    """Render the Earnings Calendar page."""

    st.markdown(_STYLES, unsafe_allow_html=True)

    # ── Hero ──
    st.markdown("""
    <div class="ec-hero">
        <h1>Earnings Calendar</h1>
        <p>Track upcoming and recent earnings announcements across the market</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Search bar ──
    search_col1, search_col2, search_col3 = st.columns([1, 2, 1])
    with search_col2:
        search_query = st.text_input(
            "Find earnings for symbols",
            placeholder="Search by ticker (e.g. AAPL, MSFT, NVDA)",
            key="ec_search",
            label_visibility="collapsed",
        )

    # ── Handle ticker search ──
    if search_query and search_query.strip():
        _render_ticker_search(search_query.strip().upper())
        _render_footer_notes()
        return

    # ── Week navigation state ──
    today = date.today()
    if "ec_week_offset" not in st.session_state:
        st.session_state.ec_week_offset = 0

    # Navigation buttons
    nav_c1, nav_c2, nav_c3, nav_c4, nav_c5 = st.columns([2, 1, 3, 1, 2])
    with nav_c2:
        if st.button("‹", key="ec_prev", use_container_width=True):
            st.session_state.ec_week_offset -= 1
            st.rerun()
    with nav_c4:
        if st.button("›", key="ec_next", use_container_width=True):
            st.session_state.ec_week_offset += 1
            st.rerun()

    week_start = _get_week_start(today) + timedelta(weeks=st.session_state.ec_week_offset)

    with nav_c3:
        st.markdown(
            f'<div style="text-align:center;padding:6px 0;">'
            f'<span class="ec-date-range">{_format_date_range(week_start)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Fetch entire week data (parallel) ──
    with st.spinner("Loading earnings data..."):
        week_data = _fetch_week_earnings(week_start)

    # ── Day selector cards ──
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    days_in_week = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        d_str = d.isoformat()
        count = len(week_data.get(d_str, []))
        days_in_week.append((d, count))

    # Default to today if in range, otherwise first day with data, else Monday
    if "ec_selected_day" not in st.session_state:
        st.session_state.ec_selected_day = None

    # Reset selected day when week changes
    selected_day = st.session_state.ec_selected_day
    if selected_day:
        try:
            sel_date = date.fromisoformat(selected_day)
            if sel_date < week_start or sel_date > week_start + timedelta(days=6):
                selected_day = None
        except Exception:
            selected_day = None

    if not selected_day:
        # Default: today if in this week, else first day with earnings, else Monday
        if week_start <= today <= week_start + timedelta(days=6):
            selected_day = today.isoformat()
        else:
            # Pick first day with data
            for d, count in days_in_week:
                if count > 0:
                    selected_day = d.isoformat()
                    break
            if not selected_day:
                selected_day = (week_start + timedelta(days=1)).isoformat()  # Monday

    # Day selector buttons
    day_cols = st.columns(7)
    for i, (d, count) in enumerate(days_in_week):
        with day_cols[i]:
            is_active = d.isoformat() == selected_day
            label = f"{day_names[d.weekday() + 1] if d.weekday() < 6 else 'Sun'}, {d.strftime('%b %-d')}"
            # Fix day name mapping: weekday() returns 0=Mon...6=Sun
            wd = d.weekday()
            day_label_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
            label = f"{day_label_map[wd]}, {d.strftime('%b')} {d.day}"

            if st.button(
                f"{label}\n{'● ' + str(count) + ' Earnings' if count > 0 else 'No Earnings'}",
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
    day_label_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    day_title = f"Earnings On {day_label_map[wd]}, {sel_date.strftime('%b')} {sel_date.day}"

    st.markdown(f"### {day_title}")

    if not day_earnings:
        st.markdown("""
        <div class="ec-empty">
            <div class="ec-empty-icon">📅</div>
            <div class="ec-empty-text">No earnings announcements scheduled for this day</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        _render_earnings_table(day_earnings, sel_date)

    # ── Footer ──
    _render_footer_notes()


def _render_ticker_search(symbol: str):
    """Render search results for a specific ticker."""
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

    # Split into upcoming and past
    today_str = date.today().isoformat()
    upcoming = [r for r in results if r["date"] >= today_str]
    past = [r for r in results if r["date"] < today_str]

    if upcoming:
        st.markdown("#### Upcoming Earnings")
        _render_earnings_table(upcoming, None, show_date=True)

    if past:
        st.markdown("#### Past Earnings")
        _render_earnings_table(past, None, show_date=True)


def _render_earnings_table(earnings: list[dict], sel_date: date | None, show_date: bool = False):
    """Render the earnings HTML table."""

    # Get current ticker from query params for linking
    current_ticker = st.query_params.get("ticker", "AAPL")
    _auth_params = ""
    if st.session_state.get("session_token"):
        _auth_params = f"&_sid={st.session_state.session_token}"

    # Sort: BMO first, then AMC, then others
    order = {"BMO": 0, "AMC": 1, "TAS": 2, "TNS": 3, "-": 4}
    earnings_sorted = sorted(earnings, key=lambda x: (order.get(x.get("call_time", "-"), 4), x.get("ticker", "")))

    # Build table HTML
    date_col_header = '<th>Date</th>' if show_date else ''

    rows_html = ""
    for e in earnings_sorted:
        ticker = e.get("ticker", "")
        company = e.get("company", ticker)
        event = e.get("event", "Earnings Announcement")
        call_time = e.get("call_time", "-")
        eps_est = e.get("eps_estimate", "-")
        eps_actual = e.get("eps_actual", "-")
        surprise = e.get("surprise_pct", "-")

        # Call time badge
        if call_time == "BMO":
            badge = '<span class="ec-badge-bmo">BMO</span>'
        elif call_time == "AMC":
            badge = '<span class="ec-badge-amc">AMC</span>'
        else:
            badge = f'<span class="ec-badge-other">{call_time}</span>'

        # EPS styling
        eps_est_html = f'<span class="ec-eps-neutral">{eps_est}</span>'
        if eps_actual != "-":
            try:
                val = float(eps_actual)
                cls = "ec-eps-positive" if val >= 0 else "ec-eps-negative"
                eps_actual_html = f'<span class="{cls}">{eps_actual}</span>'
            except (ValueError, TypeError):
                eps_actual_html = f'<span class="ec-eps-neutral">{eps_actual}</span>'
        else:
            eps_actual_html = f'<span class="ec-eps-neutral">-</span>'

        # Surprise styling
        if surprise != "-":
            try:
                val = float(surprise)
                cls = "ec-surprise-positive" if val >= 0 else "ec-surprise-negative"
                sign = "+" if val > 0 else ""
                surprise_html = f'<span class="{cls}">{sign}{surprise}%</span>'
            except (ValueError, TypeError):
                surprise_html = f'<span class="ec-eps-neutral">{surprise}</span>'
        else:
            surprise_html = f'<span class="ec-eps-neutral">-</span>'

        # Ticker link — goes to QuarterCharts charts page
        ticker_link = f'/?page=charts&ticker={ticker}{_auth_params}'

        date_col = f'<td>{e.get("date", "")}</td>' if show_date else ''

        rows_html += f"""
        <tr>
            <td><a class="ec-ticker" href="{ticker_link}" target="_self">{ticker}</a></td>
            <td><span class="ec-company">{company}</span></td>
            <td><span class="ec-event">{event}</span></td>
            {date_col}
            <td>{badge}</td>
            <td>{eps_est_html}</td>
            <td>{eps_actual_html}</td>
            <td>{surprise_html}</td>
        </tr>
        """

    date_th = '<th>Date</th>' if show_date else ''

    table_html = f"""
    <div class="ec-table-wrap">
        <table class="ec-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Event Name</th>
                    {date_th}
                    <th>Call Time</th>
                    <th>EPS Estimate</th>
                    <th>Reported EPS</th>
                    <th>Surprise %</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)
    st.caption(f"Showing {len(earnings_sorted)} earnings announcement{'s' if len(earnings_sorted) != 1 else ''}")


def _render_footer_notes():
    """Render data attribution and glossary footer."""
    st.markdown("---")
    st.markdown("#### Glossary & Notes")
    st.markdown("""
**BMO** — Before Market Open. The company reports earnings before the stock market opens (typically before 9:30 AM ET).

**AMC** — After Market Close. The company reports earnings after the market closes (typically after 4:00 PM ET).

**TAS** — Time Already Supplied / During Market Hours.

**TNS** — Time Not Supplied. The exact reporting time has not been announced.

**EPS Estimate** — The consensus Wall Street analyst estimate for Earnings Per Share for the reporting period.

**Reported EPS** — The actual Earnings Per Share reported by the company. Available after the announcement.

**Surprise %** — The percentage difference between Reported EPS and the consensus EPS Estimate. Positive means the company beat expectations.
""")
    st.markdown("#### Data Source & Disclaimer")
    st.caption(
        "Earnings calendar data is sourced from Yahoo Finance. Earnings dates, estimates, and reported figures are provided "
        "for informational purposes only and may be subject to change. QuarterCharts does not guarantee the accuracy, "
        "completeness, or timeliness of this data.\n\n"
        "Consensus EPS estimates are compiled from analyst forecasts and may differ from other sources. Actual earnings "
        "results are reported by the companies themselves via SEC filings (8-K, 10-Q, 10-K) and press releases.\n\n"
        "This information does not constitute financial advice. Always verify earnings dates and estimates with official "
        "company investor relations pages and SEC EDGAR filings before making investment decisions."
    )
