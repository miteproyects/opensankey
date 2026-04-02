"""
Earnings Calendar page for QuarterCharts.
Weekly earnings calendar with day-by-day breakdown, matching Yahoo Finance features.
Data sourced from Yahoo Finance via yfinance library.
"""

import streamlit as st
import pandas as pd
import time
import traceback
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── In-memory cache with TTL ────────────────────────────────────────────
_EARNINGS_CACHE: dict = {}      # key -> (timestamp, data)
_CACHE_TTL = 900                # 15 min TTL


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
# Optimized for speed: small ticker list, no .info calls, persistent cache.

# Debug log — always visible in UI for diagnostics
_DEBUG_LOG: list[str] = []


def _debug(msg: str):
    _DEBUG_LOG.append(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ── Top tickers to scan (kept small for speed ~5-8s) ──
_SCAN_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "MA",
    "NFLX", "CRM", "INTC", "AMD", "ORCL", "CSCO", "PEP", "KO",
    "COST", "NKE", "LLY", "AVGO", "QCOM", "TXN",
    "GS", "BAC", "WFC", "MS", "C",
    "BA", "CAT", "GE", "UPS", "FDX",
    "CVX", "XOM", "COP",
    "PFE", "AMGN", "GILD", "ABT",
    "ADBE", "NOW", "UBER", "ABNB", "SHOP",
    "F", "GM", "DAL", "AAL",
    "DIS", "SBUX", "MCD", "CMG",
    "TGT", "BBY", "LULU",
    "COIN", "PLTR", "SNAP", "ROKU",
    "NET", "CRWD", "PANW", "DDOG",
]


# ── Static company name map (avoids slow .info API calls) ──
_COMPANY_NAMES = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp.", "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.", "META": "Meta Platforms", "NVDA": "NVIDIA Corp.",
    "TSLA": "Tesla Inc.", "JPM": "JPMorgan Chase", "V": "Visa Inc.",
    "JNJ": "Johnson & Johnson", "WMT": "Walmart Inc.", "PG": "Procter & Gamble",
    "UNH": "UnitedHealth Group", "HD": "Home Depot", "MA": "Mastercard Inc.",
    "NFLX": "Netflix Inc.", "CRM": "Salesforce Inc.", "INTC": "Intel Corp.",
    "AMD": "AMD Inc.", "ORCL": "Oracle Corp.", "CSCO": "Cisco Systems",
    "PEP": "PepsiCo Inc.", "KO": "Coca-Cola Co.", "COST": "Costco Wholesale",
    "NKE": "Nike Inc.", "LLY": "Eli Lilly", "AVGO": "Broadcom Inc.",
    "QCOM": "Qualcomm Inc.", "TXN": "Texas Instruments",
    "GS": "Goldman Sachs", "BAC": "Bank of America", "WFC": "Wells Fargo",
    "MS": "Morgan Stanley", "C": "Citigroup Inc.",
    "BA": "Boeing Co.", "CAT": "Caterpillar Inc.", "GE": "GE Aerospace",
    "UPS": "United Parcel Service", "FDX": "FedEx Corp.",
    "CVX": "Chevron Corp.", "XOM": "Exxon Mobil", "COP": "ConocoPhillips",
    "PFE": "Pfizer Inc.", "AMGN": "Amgen Inc.", "GILD": "Gilead Sciences",
    "ABT": "Abbott Labs", "ADBE": "Adobe Inc.", "NOW": "ServiceNow",
    "UBER": "Uber Technologies", "ABNB": "Airbnb Inc.", "SHOP": "Shopify Inc.",
    "F": "Ford Motor Co.", "GM": "General Motors", "DAL": "Delta Air Lines",
    "AAL": "American Airlines", "DIS": "Walt Disney Co.", "SBUX": "Starbucks Corp.",
    "MCD": "McDonald's Corp.", "CMG": "Chipotle Mexican Grill",
    "TGT": "Target Corp.", "BBY": "Best Buy Co.", "LULU": "Lululemon",
    "COIN": "Coinbase Global", "PLTR": "Palantir Technologies",
    "SNAP": "Snap Inc.", "ROKU": "Roku Inc.",
    "NET": "Cloudflare Inc.", "CRWD": "CrowdStrike", "PANW": "Palo Alto Networks",
    "DDOG": "Datadog Inc.",
}


def _check_ticker_earnings(symbol: str, target_dates: set[str]) -> list[dict]:
    """Check a single ticker's earnings dates via yfinance API. No .info call."""
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
                matches.append({
                    "ticker": symbol.upper(),
                    "company": _COMPANY_NAMES.get(symbol.upper(), symbol.upper()),
                    "event": "Earnings Announcement",
                    "call_time": "-",
                    "eps_estimate": _safe_float(row.get("EPS Estimate")),
                    "eps_actual": _safe_float(row.get("Reported EPS")),
                    "surprise_pct": _safe_float(row.get("Surprise(%)")),
                    "date": earn_str,
                })
        return matches
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_week_earnings_cached(week_start_str: str) -> dict:
    """
    Fetch earnings for entire week. Uses @st.cache_data for persistence
    across Streamlit reruns (15 min TTL). Accepts str for hashability.
    """
    week_start = date.fromisoformat(week_start_str)
    days = [week_start + timedelta(days=i) for i in range(7)]
    target_dates = {d.isoformat() for d in days}
    result = {d.isoformat(): [] for d in days}

    _debug(f"Week scan: {len(_SCAN_TICKERS)} tickers, {week_start_str} to {days[-1].isoformat()}")
    t0 = time.time()
    errors = 0

    try:
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(_check_ticker_earnings, sym, target_dates): sym
                for sym in _SCAN_TICKERS
            }
            for future in as_completed(futures, timeout=20):
                try:
                    matches = future.result(timeout=6)
                    for m in matches:
                        d_str = m["date"]
                        if d_str in result:
                            result[d_str].append(m)
                except Exception:
                    errors += 1
    except Exception as e:
        _debug(f"Scan error: {e}")

    elapsed = time.time() - t0
    total = sum(len(v) for v in result.values())
    _debug(f"Done: {total} earnings, {errors} errors, {elapsed:.1f}s")
    return result


def _safe_float(val) -> str:
    if val is None or val == "" or val == "-" or val == "N/A":
        return "-"
    try:
        v = float(str(val).replace(",", ""))
        return f"{v:.2f}" if v != 0 else "0.00"
    except (ValueError, TypeError):
        return str(val)


def _map_call_time(raw: str) -> str:
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
        company = symbol.upper()
        try:
            company = tk.info.get("shortName", symbol.upper())
        except Exception:
            pass
        for idx, row in cal.iterrows():
            d = idx.date() if hasattr(idx, 'date') else idx
            results.append({
                "ticker": symbol.upper(),
                "company": company,
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


# ── Week helpers ──────────────────────────────────────────────────────

def _get_week_start(d: date) -> date:
    """Get Sunday of the week containing date d."""
    return d - timedelta(days=d.weekday() + 1) if d.weekday() != 6 else d


def _format_date_range(week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    if week_start.month == week_end.month:
        return f"{week_start.strftime('%b %d')} – {week_end.strftime('%d, %Y')}"
    elif week_start.year == week_end.year:
        return f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
    else:
        return f"{week_start.strftime('%b %d, %Y')} – {week_end.strftime('%b %d, %Y')}"


_DAY_MAP = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


# ── Styles ─────────────────────────────────────────────────────────────

_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Hero ── */
.ec-hero {
    text-align: center;
    padding: 40px 20px 8px;
}
.ec-hero h1 {
    font-size: 2.6rem;
    font-weight: 900;
    background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 8px;
    font-family: Inter, system-ui, sans-serif;
    letter-spacing: -0.03em;
}
.ec-hero p {
    font-size: 1rem;
    color: #64748b;
    margin: 0;
    font-family: Inter, system-ui, sans-serif;
    letter-spacing: 0.01em;
}

/* ── Week nav ── */
.ec-date-range {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e2e8f0;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 10px 28px;
    font-family: Inter, system-ui, sans-serif;
    display: inline-block;
    letter-spacing: 0.01em;
}

/* ── Day selector pills ── */
.ec-day-pill {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    padding: 12px 10px 10px;
    border-radius: 14px;
    border: 2px solid transparent;
    background: #0f172a;
    min-width: 90px;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    text-decoration: none;
    font-family: Inter, system-ui, sans-serif;
}
.ec-day-pill:hover {
    border-color: #334155;
    background: #1e293b;
    transform: translateY(-2px);
}
.ec-day-pill.active {
    border-color: #3b82f6;
    background: linear-gradient(135deg, #172554, #1e3a5f);
    box-shadow: 0 4px 24px rgba(59,130,246,0.2), 0 0 0 1px rgba(59,130,246,0.1);
}
.ec-day-pill .day-name {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin-bottom: 4px;
}
.ec-day-pill.active .day-name { color: #93c5fd; }
.ec-day-pill .day-num {
    font-size: 1.3rem;
    font-weight: 800;
    color: #e2e8f0;
    line-height: 1.2;
}
.ec-day-pill.active .day-num { color: #fff; }
.ec-day-pill .day-count {
    font-size: 0.65rem;
    font-weight: 600;
    color: #475569;
    margin-top: 4px;
    white-space: nowrap;
}
.ec-day-pill.active .day-count { color: #60a5fa; }
.ec-day-pill .day-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #3b82f6;
    margin-top: 4px;
}
.ec-day-pill .day-dot.empty { background: transparent; }

/* ── Section header ── */
.ec-section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 28px 0 16px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-section-header h2 {
    font-size: 1.15rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0;
}
.ec-section-header .ec-count-badge {
    background: linear-gradient(135deg, #1e40af, #3b82f6);
    color: #fff;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 12px;
    border-radius: 20px;
    letter-spacing: 0.02em;
}

/* ── Earnings table ── */
.ec-table-wrap {
    border-radius: 16px;
    border: 1px solid #1e293b;
    overflow: hidden;
    margin-bottom: 20px;
    background: #0f172a;
}
.ec-table {
    width: 100%;
    border-collapse: collapse;
    font-family: Inter, system-ui, sans-serif;
}
.ec-table thead th {
    background: linear-gradient(180deg, #1e293b, #0f172a);
    color: #64748b;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 14px 16px;
    text-align: left;
    border-bottom: 1px solid #1e293b;
    position: sticky;
    top: 0;
    z-index: 1;
}
.ec-table tbody tr {
    border-bottom: 1px solid rgba(30,41,59,0.5);
    transition: all 0.15s ease;
}
.ec-table tbody tr:hover {
    background: linear-gradient(90deg, rgba(59,130,246,0.06), rgba(59,130,246,0.02));
}
.ec-table tbody td {
    padding: 14px 16px;
    font-size: 0.88rem;
    color: #94a3b8;
    vertical-align: middle;
}
.ec-ticker {
    color: #60a5fa;
    font-weight: 700;
    text-decoration: none;
    cursor: pointer;
    font-size: 0.9rem;
    letter-spacing: 0.02em;
    transition: color 0.15s;
}
.ec-ticker:hover { color: #93c5fd; }
.ec-company {
    color: #cbd5e1;
    font-weight: 500;
    font-size: 0.85rem;
}
.ec-event {
    color: #475569;
    font-size: 0.78rem;
    font-style: italic;
}

/* Call time badges */
.ec-badge-bmo {
    background: rgba(59,130,246,0.12);
    color: #60a5fa;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    border: 1px solid rgba(59,130,246,0.2);
}
.ec-badge-amc {
    background: rgba(168,85,247,0.12);
    color: #c084fc;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    border: 1px solid rgba(168,85,247,0.2);
}
.ec-badge-other {
    background: rgba(100,116,139,0.1);
    color: #64748b;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 0.72rem;
    font-weight: 600;
    border: 1px solid rgba(100,116,139,0.15);
}

/* EPS + Surprise */
.ec-eps-positive { color: #22c55e; font-weight: 600; }
.ec-eps-negative { color: #ef4444; font-weight: 600; }
.ec-eps-neutral { color: #475569; }
.ec-surprise-positive {
    color: #22c55e;
    font-weight: 700;
    font-size: 0.82rem;
    background: rgba(34,197,94,0.08);
    padding: 2px 8px;
    border-radius: 6px;
}
.ec-surprise-negative {
    color: #ef4444;
    font-weight: 700;
    font-size: 0.82rem;
    background: rgba(239,68,68,0.08);
    padding: 2px 8px;
    border-radius: 6px;
}

/* ── Empty state ── */
.ec-empty {
    text-align: center;
    padding: 64px 20px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-empty-icon {
    font-size: 3rem;
    margin-bottom: 16px;
    opacity: 0.4;
}
.ec-empty-text {
    font-size: 1rem;
    font-weight: 500;
    color: #475569;
}
.ec-empty-sub {
    font-size: 0.85rem;
    color: #334155;
    margin-top: 6px;
}

/* ── Search banner ── */
.ec-search-banner {
    background: linear-gradient(135deg, #172554 0%, #1e3a5f 50%, #172554 100%);
    border: 1px solid rgba(59,130,246,0.3);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 24px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-search-banner h3 {
    color: #60a5fa;
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0 0 4px;
}
.ec-search-banner p {
    color: #93c5fd;
    font-size: 0.85rem;
    margin: 0;
    opacity: 0.8;
}

/* ── Footer glossary ── */
.ec-glossary {
    margin-top: 36px;
    padding: 24px;
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid #1e293b;
    border-radius: 16px;
    font-family: Inter, system-ui, sans-serif;
}
.ec-glossary h4 {
    color: #64748b;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 0 0 16px;
}
.ec-glossary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
}
.ec-glossary-item {
    display: flex;
    align-items: baseline;
    gap: 8px;
}
.ec-glossary-item .term {
    color: #94a3b8;
    font-size: 0.78rem;
    font-weight: 700;
    white-space: nowrap;
    min-width: 40px;
}
.ec-glossary-item .def {
    color: #475569;
    font-size: 0.75rem;
    line-height: 1.5;
}

/* ── Responsive ── */
@media (max-width: 768px) {
    .ec-hero h1 { font-size: 1.8rem; }
    .ec-day-pill { min-width: 70px; padding: 8px 6px; }
    .ec-day-pill .day-num { font-size: 1rem; }
    .ec-table thead th, .ec-table tbody td { padding: 10px 10px; font-size: 0.8rem; }
    .ec-glossary-grid { grid-template-columns: 1fr; }
}
</style>
"""


# ── Main Render Function ────────────────────────────────────────────────

def render_earnings_page():
    """Render the Earnings Calendar page."""
    global _DEBUG_LOG
    _DEBUG_LOG = []  # Reset on each render

    st.markdown(_STYLES, unsafe_allow_html=True)

    # ── Hero ──
    st.markdown("""
    <div class="ec-hero">
        <h1>Earnings Calendar</h1>
        <p>Track upcoming and recent earnings announcements across the market</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Search bar ──
    search_col1, search_col2, search_col3 = st.columns([1, 3, 1])
    with search_col2:
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

    nav_c1, nav_c2, nav_c3, nav_c4, nav_c5 = st.columns([2, 1, 3, 1, 2])
    with nav_c2:
        if st.button("◂ Prev", key="ec_prev", use_container_width=True):
            st.session_state.ec_week_offset -= 1
            st.rerun()
    with nav_c4:
        if st.button("Next ▸", key="ec_next", use_container_width=True):
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

    # ── Fetch week data (cached — fast after first load) ──
    _debug("Starting data fetch...")
    try:
        with st.spinner("Loading earnings data..."):
            week_data = _fetch_week_earnings_cached(week_start.isoformat())
    except Exception as e:
        _debug(f"FATAL fetch error: {e}")
        _debug(traceback.format_exc())
        week_data = {(week_start + timedelta(days=i)).isoformat(): [] for i in range(7)}

    # ── Day selector pills ──
    days_in_week = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        count = len(week_data.get(d.isoformat(), []))
        days_in_week.append((d, count))

    # Determine selected day
    if "ec_selected_day" not in st.session_state:
        st.session_state.ec_selected_day = None

    selected_day = st.session_state.ec_selected_day
    if selected_day:
        try:
            sel_date = date.fromisoformat(selected_day)
            if sel_date < week_start or sel_date > week_start + timedelta(days=6):
                selected_day = None
        except Exception:
            selected_day = None

    if not selected_day:
        if week_start <= today <= week_start + timedelta(days=6):
            selected_day = today.isoformat()
        else:
            for d, count in days_in_week:
                if count > 0:
                    selected_day = d.isoformat()
                    break
            if not selected_day:
                selected_day = (week_start + timedelta(days=1)).isoformat()

    # Render day pill buttons
    day_cols = st.columns(7)
    for i, (d, count) in enumerate(days_in_week):
        with day_cols[i]:
            is_active = d.isoformat() == selected_day
            wd = d.weekday()
            day_name = _DAY_MAP[wd]

            # Build rich HTML pill content
            active_cls = "active" if is_active else ""
            dot_cls = "" if count > 0 else "empty"
            count_text = f"{count} report{'s' if count != 1 else ''}" if count > 0 else "—"

            pill_html = f"""
            <div class="ec-day-pill {active_cls}" style="width:100%;text-align:center;">
                <span class="day-name">{day_name}</span>
                <span class="day-num">{d.day}</span>
                <span class="day-count">{count_text}</span>
                <span class="day-dot {dot_cls}"></span>
            </div>
            """
            st.markdown(pill_html, unsafe_allow_html=True)

            if st.button(
                f"Select {day_name}",
                key=f"ec_day_{d.isoformat()}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                label_visibility="collapsed",
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

    count_badge = f'<span class="ec-count-badge">{len(day_earnings)} report{"s" if len(day_earnings) != 1 else ""}</span>' if day_earnings else ''
    st.markdown(f"""
    <div class="ec-section-header">
        <h2>{day_title}</h2>
        {count_badge}
    </div>
    """, unsafe_allow_html=True)

    if not day_earnings:
        st.markdown(f"""
        <div class="ec-empty">
            <div class="ec-empty-icon">📊</div>
            <div class="ec-empty-text">No earnings reports scheduled</div>
            <div class="ec-empty-sub">{_DAY_MAP[wd]}, {sel_date.strftime('%B %d, %Y')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        _render_earnings_table(day_earnings, sel_date)

    # ── Debug + Footer ──
    _render_debug()
    _render_footer()


def _render_debug():
    """Always render debug diagnostics so we can see what happens on Railway."""
    with st.expander("Data fetch diagnostics", expanded=False):
        if _DEBUG_LOG:
            for line in _DEBUG_LOG:
                st.code(line, language=None)
        else:
            st.caption("No debug messages logged — fetch may not have run (data may be cached).")
        # Show yfinance version
        try:
            import yfinance as yf
            st.caption(f"yfinance version: {yf.__version__}")
        except Exception:
            st.caption("yfinance not available")


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

    today_str = date.today().isoformat()
    upcoming = [r for r in results if r["date"] >= today_str]
    past = [r for r in results if r["date"] < today_str]

    if upcoming:
        st.markdown(f"""
        <div class="ec-section-header">
            <h2>Upcoming Earnings</h2>
            <span class="ec-count-badge">{len(upcoming)}</span>
        </div>
        """, unsafe_allow_html=True)
        _render_earnings_table(upcoming, None, show_date=True)

    if past:
        st.markdown(f"""
        <div class="ec-section-header">
            <h2>Past Earnings</h2>
            <span class="ec-count-badge">{len(past)}</span>
        </div>
        """, unsafe_allow_html=True)
        _render_earnings_table(past, None, show_date=True)


def _render_earnings_table(earnings: list[dict], sel_date=None, show_date: bool = False):
    """Render the earnings HTML table."""
    _auth_params = ""
    if st.session_state.get("session_token"):
        _auth_params = f"&_sid={st.session_state.session_token}"

    order = {"BMO": 0, "AMC": 1, "TAS": 2, "TNS": 3, "-": 4}
    earnings_sorted = sorted(earnings, key=lambda x: (order.get(x.get("call_time", "-"), 4), x.get("ticker", "")))

    rows_html = ""
    for e in earnings_sorted:
        ticker = e.get("ticker", "")
        company = e.get("company", ticker)
        event = e.get("event", "Earnings Announcement")
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
            eps_actual_html = '<span class="ec-eps-neutral">–</span>'

        if surprise != "-":
            try:
                val = float(surprise)
                cls = "ec-surprise-positive" if val >= 0 else "ec-surprise-negative"
                sign = "+" if val > 0 else ""
                surprise_html = f'<span class="{cls}">{sign}{surprise}%</span>'
            except (ValueError, TypeError):
                surprise_html = f'<span class="ec-eps-neutral">{surprise}</span>'
        else:
            surprise_html = '<span class="ec-eps-neutral">–</span>'

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
                    <th>Event</th>
                    {date_th}
                    <th>Call Time</th>
                    <th>EPS Est.</th>
                    <th>Reported</th>
                    <th>Surprise</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def _render_footer():
    """Render glossary and disclaimer footer."""
    st.markdown("""
    <div class="ec-glossary">
        <h4>Glossary</h4>
        <div class="ec-glossary-grid">
            <div class="ec-glossary-item"><span class="term">BMO</span><span class="def">Before Market Open — reported before 9:30 AM ET</span></div>
            <div class="ec-glossary-item"><span class="term">AMC</span><span class="def">After Market Close — reported after 4:00 PM ET</span></div>
            <div class="ec-glossary-item"><span class="term">TAS</span><span class="def">Time Already Supplied / During Market Hours</span></div>
            <div class="ec-glossary-item"><span class="term">TNS</span><span class="def">Time Not Supplied — exact time not announced</span></div>
            <div class="ec-glossary-item"><span class="term">EPS Est.</span><span class="def">Consensus analyst estimate for Earnings Per Share</span></div>
            <div class="ec-glossary-item"><span class="term">Reported</span><span class="def">Actual EPS reported by the company</span></div>
            <div class="ec-glossary-item"><span class="term">Surprise</span><span class="def">% difference between reported and estimated EPS</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption(
        "Earnings data sourced from Yahoo Finance via yfinance. Dates, estimates, and reported figures are for "
        "informational purposes only and may change. QuarterCharts does not guarantee accuracy or completeness. "
        "This is not financial advice — verify with official SEC EDGAR filings and company IR pages."
    )
