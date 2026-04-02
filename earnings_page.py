"""
Earnings Calendar page for QuarterCharts.
Weekly earnings calendar with day-by-day breakdown, matching Yahoo Finance features.
Data sourced from Yahoo Finance via yfinance library.
"""

import streamlit as st
import pandas as pd
import time
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
# Uses ONLY yfinance Python API (get_earnings_dates) — no web scraping.
# Scans a broad list of tickers in parallel to find earnings on each date.

# Debug log — visible in UI for diagnostics
_DEBUG_LOG: list[str] = []


def _debug(msg: str):
    _DEBUG_LOG.append(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ── Broad ticker universe for scanning ──
_SCAN_TICKERS = [
    # Mega/large caps
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "BRK-B",
    "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "MA", "DIS", "PYPL",
    "NFLX", "CRM", "INTC", "AMD", "ORCL", "CSCO", "PEP", "KO", "MRK",
    "ABT", "TMO", "COST", "NKE", "LLY", "AVGO", "QCOM", "TXN", "HON",
    "LOW", "SBUX", "MDLZ", "GS", "BLK", "AXP", "MS", "C", "BAC", "WFC",
    "DE", "CAT", "BA", "GE", "RTX", "LMT", "UPS", "FDX", "T", "VZ",
    "CMCSA", "TMUS", "CVX", "XOM", "COP", "SLB", "EOG", "MPC", "PSX",
    "PFE", "BMY", "GILD", "AMGN", "REGN", "VRTX", "ISRG", "MDT",
    "DHR", "SYK", "ZTS", "CI", "ELV", "HCA", "MCK", "CVS",
    "SCHW", "MMM", "IBM", "ACN", "NOW", "SNOW", "UBER",
    "ABNB", "SQ", "SHOP", "PLTR", "RIVN", "LCID", "F", "GM",
    "AAL", "DAL", "UAL", "LUV", "MAR", "HLT", "WYNN", "MGM",
    "ADBE", "INTU", "PANW", "CRWD", "ZS", "NET", "DDOG", "MDB",
    "COIN", "HOOD", "SOFI", "AFRM", "UPST", "BILL", "HUBS",
    # Mid-caps & popular earnings movers
    "ROKU", "SNAP", "PINS", "TTD", "RBLX", "U", "DKNG", "PENN",
    "CHWY", "ETSY", "W", "BKNG", "EXPE", "ABNB", "DASH",
    "ZM", "DOCU", "OKTA", "TWLO", "FIVN", "RNG",
    "CLX", "KMB", "SJM", "GIS", "K", "CPB", "HSY", "MKC",
    "TGT", "DG", "DLTR", "ROST", "TJX", "BBY", "LULU",
    "FIS", "FISV", "GPN", "SYF", "DFS", "COF", "AIG",
    "MET", "PRU", "AFL", "TRV", "CB", "ALL", "PGR",
    "SO", "DUK", "NEE", "AEP", "D", "SRE", "EXC", "XEL",
    "AMT", "PLD", "CCI", "EQIX", "SPG", "O", "WELL", "DLR",
    "USB", "PNC", "TFC", "FITB", "KEY", "RF", "CFG", "HBAN",
    "LEN", "DHI", "PHM", "TOL", "KBH", "NVR",
    "ON", "MCHP", "KLAC", "LRCX", "AMAT", "ASML", "SNPS", "CDNS",
    "ENPH", "FSLR", "RUN", "SEDG",
    "WDAY", "VEEV", "ANSS", "CDNS", "SNPS", "FTNT", "SPLK",
    "CMG", "YUM", "QSR", "MCD", "SBUX", "DPZ", "WEN", "JACK",
    "CL", "EL", "CHD", "MNST", "STZ", "BF-B", "DEO", "SAM",
]
# Deduplicate
_SCAN_TICKERS = list(dict.fromkeys(_SCAN_TICKERS))


def _fetch_earnings_for_date(target_date: date) -> list[dict]:
    """Fetch earnings for a single date using yfinance API only."""
    cache_key = _cache_key(target_date)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    results = _scan_tickers_for_date(target_date)
    _set_cached(cache_key, results)
    return results


def _check_ticker_earnings(symbol: str, target_dates: set[str]) -> list[dict]:
    """
    Check a single ticker's upcoming earnings dates via yfinance API.
    Returns list of matching rows for any of the target_dates.
    """
    import yfinance as yf

    try:
        tk = yf.Ticker(symbol)
        cal = tk.get_earnings_dates(limit=8)
        if cal is None or cal.empty:
            return []

        matches = []
        for idx, row in cal.iterrows():
            earn_date = idx.date() if hasattr(idx, 'date') else idx
            earn_str = str(earn_date)
            if earn_str in target_dates:
                eps_est = row.get("EPS Estimate")
                eps_actual = row.get("Reported EPS")
                surprise = row.get("Surprise(%)")

                # Get company name from fast_info (faster than .info)
                company_name = symbol
                try:
                    info = tk.fast_info
                    # fast_info doesn't have shortName, but we can try
                    company_name = symbol
                except Exception:
                    pass
                try:
                    company_name = tk.info.get("shortName", symbol)
                except Exception:
                    pass

                matches.append({
                    "ticker": symbol.upper(),
                    "company": company_name,
                    "event": "Earnings Announcement",
                    "call_time": "-",
                    "eps_estimate": _safe_float(eps_est),
                    "eps_actual": _safe_float(eps_actual),
                    "surprise_pct": _safe_float(surprise),
                    "date": earn_str,
                })
        return matches
    except Exception:
        return []


def _scan_tickers_for_date(target_date: date) -> list[dict]:
    """Scan ticker universe via yfinance API to find earnings on target_date."""
    target_str = target_date.isoformat()
    target_set = {target_str}
    results = []

    _debug(f"Scanning {len(_SCAN_TICKERS)} tickers for {target_str}")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {
            executor.submit(_check_ticker_earnings, sym, target_set): sym
            for sym in _SCAN_TICKERS
        }
        for future in as_completed(futures, timeout=30):
            try:
                matches = future.result(timeout=8)
                results.extend(matches)
            except Exception:
                continue

    elapsed = time.time() - t0
    _debug(f"Scan done: {len(results)} earnings found in {elapsed:.1f}s")
    return results


def _safe_float(val) -> str:
    if val is None or val == "" or val == "-" or val == "N/A":
        return "-"
    try:
        v = float(str(val).replace(",", ""))
        return f"{v:.2f}" if v != 0 else "0.00"
    except (ValueError, TypeError):
        return str(val)



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
    Fetch earnings for an entire week in a single parallel ticker scan.
    Much faster than 7 separate scans — checks all 7 days per ticker call.
    Returns dict mapping date_str -> list of earnings rows.
    """
    days = [week_start + timedelta(days=i) for i in range(7)]

    result = {}
    all_cached = True
    for d in days:
        ck = _cache_key(d)
        c = _get_cached(ck)
        if c is not None:
            result[d.isoformat()] = c
        else:
            result[d.isoformat()] = []
            all_cached = False

    if all_cached:
        return result

    # Scan all tickers once, checking against all 7 days in the week
    target_dates = {d.isoformat() for d in days}
    _debug(f"Week scan: {week_start.isoformat()} to {days[-1].isoformat()} ({len(_SCAN_TICKERS)} tickers)")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {
            executor.submit(_check_ticker_earnings, sym, target_dates): sym
            for sym in _SCAN_TICKERS
        }
        for future in as_completed(futures, timeout=45):
            try:
                matches = future.result(timeout=8)
                for m in matches:
                    d_str = m["date"]
                    if d_str in result:
                        result[d_str].append(m)
            except Exception:
                continue

    elapsed = time.time() - t0
    total = sum(len(v) for v in result.values())
    _debug(f"Week scan done: {total} total earnings in {elapsed:.1f}s")

    # Cache each day's results
    for d in days:
        _set_cached(_cache_key(d), result[d.isoformat()])

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

    # ── Debug diagnostics (temporary) ──
    if _DEBUG_LOG:
        with st.expander("🔧 Data fetch diagnostics", expanded=False):
            for line in _DEBUG_LOG:
                st.text(line)

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
