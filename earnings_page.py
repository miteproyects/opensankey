"""
Earnings Calendar page for Quarter Charts.
Shows upcoming earnings reports in a weekly treemap view,
similar to quarterchart.com/earnings.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import os
from datetime import datetime, timedelta
from functools import lru_cache
import json
import concurrent.futures


# ── FMP helpers (reuse from data_fetcher) ─────────────────────────────────

_FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _fmp_key() -> str:
    return os.environ.get("FMP_API_KEY", "")


def _fmp_available() -> bool:
    return bool(_fmp_key())


# ── Company name map for nicer display ────────────────────────────────────

_COMPANY_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon",
    "META": "Meta", "NVDA": "NVIDIA", "TSLA": "Tesla", "JPM": "JPMorgan",
    "V": "Visa", "JNJ": "Johnson & Johnson", "WMT": "Walmart", "PG": "Procter & Gamble",
    "UNH": "UnitedHealth", "HD": "Home Depot", "MA": "Mastercard", "DIS": "Disney",
    "PYPL": "PayPal", "ADBE": "Adobe", "NFLX": "Netflix", "CRM": "Salesforce",
    "INTC": "Intel", "AMD": "AMD", "ORCL": "Oracle", "CSCO": "Cisco",
    "PEP": "PepsiCo", "KO": "Coca-Cola", "MRK": "Merck", "ABT": "Abbott",
    "TMO": "Thermo Fisher", "COST": "Costco", "NKE": "Nike", "LLY": "Eli Lilly",
    "AVGO": "Broadcom", "QCOM": "Qualcomm", "TXN": "Texas Instruments",
    "HON": "Honeywell", "LOW": "Lowe's", "SBUX": "Starbucks", "MDLZ": "Mondelez",
    "GS": "Goldman Sachs", "BLK": "BlackRock", "AXP": "American Express",
    "MS": "Morgan Stanley", "C": "Citigroup", "BAC": "Bank of America",
    "WFC": "Wells Fargo", "SCHW": "Schwab", "USB": "US Bancorp",
    "DE": "John Deere", "CAT": "Caterpillar", "BA": "Boeing", "GE": "GE Aerospace",
    "RTX": "RTX", "LMT": "Lockheed Martin", "UPS": "UPS", "FDX": "FedEx",
    "MMM": "3M", "IBM": "IBM", "NOW": "ServiceNow", "INTU": "Intuit",
    "ISRG": "Intuitive Surgical", "PANW": "Palo Alto Networks",
    "LRCX": "Lam Research", "KLAC": "KLA Corp", "MRVL": "Marvell",
    "MU": "Micron", "AMAT": "Applied Materials", "SNPS": "Synopsys",
    "CDNS": "Cadence", "ZS": "Zscaler", "CRWD": "CrowdStrike",
    "DDOG": "Datadog", "NET": "Cloudflare", "SNOW": "Snowflake",
    "SQ": "Block", "SHOP": "Shopify", "MELI": "MercadoLibre",
    "SE": "Sea Limited", "BABA": "Alibaba", "JD": "JD.com", "PDD": "PDD Holdings",
    "NIO": "NIO", "LI": "Li Auto", "XPEV": "XPeng",
    "DG": "Dollar General", "DLTR": "Dollar Tree", "TGT": "Target",
    "ULTA": "Ulta Beauty", "LULU": "Lululemon", "GPS": "Gap",
    "LEN": "Lennar", "DHI": "D.R. Horton", "PHM": "PulteGroup",
    "WPM": "Wheaton Precious", "FNV": "Franco-Nevada",
    "FERG": "Ferguson", "HPE": "HP Enterprise",
    "DKS": "Dick's Sporting", "CASY": "Casey's General",
    "FUTU": "Futu Holdings", "BNTX": "BioNTech",
    "DOCU": "DocuSign", "ZM": "Zoom", "OKTA": "Okta",
    "VEEV": "Veeva Systems", "WDAY": "Workday", "SPLK": "Splunk",
    "MDB": "MongoDB", "TEAM": "Atlassian", "U": "Unity",
    "RBLX": "Roblox", "ABNB": "Airbnb", "DASH": "DoorDash",
    "RIVN": "Rivian", "LCID": "Lucid", "F": "Ford", "GM": "General Motors",
    "TM": "Toyota", "HMC": "Honda", "RACE": "Ferrari",
    "BRK-B": "Berkshire", "KHC": "Kraft Heinz", "GIS": "General Mills",
    "K": "Kellanova", "SJM": "Smucker's", "CPB": "Campbell's",
    "CL": "Colgate", "EL": "Estee Lauder", "PFE": "Pfizer",
    "ABBV": "AbbVie", "BMY": "Bristol-Myers", "GILD": "Gilead",
    "AMGN": "Amgen", "REGN": "Regeneron", "VRTX": "Vertex",
    "BIIB": "Biogen", "MRNA": "Moderna",
}

# ── Expanded ticker list for yfinance fallback ────────────────────────────

_MAJOR_TICKERS = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    # Large-cap tech
    "ADBE", "NFLX", "CRM", "INTC", "AMD", "ORCL", "CSCO", "AVGO",
    "QCOM", "TXN", "IBM", "NOW", "INTU", "PANW", "MU", "AMAT",
    "LRCX", "KLAC", "MRVL", "SNPS", "CDNS",
    # Cybersecurity / SaaS
    "ZS", "CRWD", "DDOG", "NET", "SNOW", "DOCU", "ZM", "OKTA",
    "VEEV", "WDAY", "MDB", "TEAM",
    # Fintech / E-commerce
    "PYPL", "SQ", "SHOP", "MELI",
    # Finance
    "JPM", "V", "MA", "GS", "BLK", "AXP", "MS", "C", "BAC",
    "WFC", "SCHW", "USB",
    # Healthcare
    "JNJ", "UNH", "MRK", "ABT", "TMO", "LLY", "PFE", "ABBV",
    "BMY", "GILD", "AMGN", "REGN", "VRTX", "BIIB", "MRNA",
    "ISRG", "BNTX",
    # Consumer
    "WMT", "PG", "HD", "COST", "NKE", "DIS", "SBUX", "PEP", "KO",
    "MDLZ", "LOW", "TGT", "DG", "DLTR", "ULTA", "LULU", "GPS",
    "DKS", "CASY",
    # Industrial
    "HON", "DE", "CAT", "BA", "GE", "RTX", "LMT", "UPS", "FDX", "MMM",
    # Homebuilders
    "LEN", "DHI", "PHM",
    # Auto
    "F", "GM", "RIVN", "LCID", "NIO", "LI", "XPEV",
    # Mining / Resources
    "WPM", "FNV",
    # China / Asia ADRs
    "BABA", "JD", "PDD", "SE", "FUTU",
    # Other
    "FERG", "HPE", "BRK-B", "ABNB", "DASH", "RBLX",
    "KHC", "GIS", "CL", "EL",
]


# ── Data fetching ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_earnings_calendar(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch earnings calendar from FMP for a date range."""
    if not _fmp_available():
        return _fetch_earnings_yfinance(start_date, end_date)

    url = (
        f"{_FMP_BASE}/earning_calendar"
        f"?from={start_date}&to={end_date}&apikey={_fmp_key()}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        return df
    except Exception:
        return _fetch_earnings_yfinance(start_date, end_date)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_caps_batch(symbols: list) -> dict:
    """Fetch market caps + exchange for a batch of symbols via FMP profile."""
    if not _fmp_available() or not symbols:
        return {}

    caps = {}
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        syms = ",".join(batch)
        url = f"{_FMP_BASE}/profile/{syms}?apikey={_fmp_key()}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            for item in resp.json():
                sym = item.get("symbol", "")
                mc = item.get("mktCap", 0)
                ex = item.get("exchangeShortName", "") or item.get("exchange", "") or item.get("stockExchange", "")
                caps[sym] = {"marketCap": mc, "exchange": ex}
        except Exception:
            continue
    return caps


def _fetch_single_ticker_earnings(sym, sd_date, ed_date):
    """Fetch earnings info for a single ticker. Returns dict or None."""
    try:
        import yfinance as yf
        t = yf.Ticker(sym)
        cal = t.calendar
        if cal is not None and isinstance(cal, dict):
            edate = cal.get("Earnings Date", [None])
            if isinstance(edate, list) and edate:
                edate = edate[0]
            if edate is not None:
                if hasattr(edate, "date"):
                    edate = edate.date()
                elif isinstance(edate, str):
                    edate = datetime.strptime(edate[:10], "%Y-%m-%d").date()
                if sd_date <= edate <= ed_date:
                    info = t.fast_info
                    return {
                        "date": str(edate),
                        "symbol": sym,
                        "eps": None,
                        "epsEstimated": cal.get("EPS Estimate"),
                        "revenue": None,
                        "revenueEstimated": cal.get("Revenue Estimate"),
                        "time": "",
                        "marketCap": getattr(info, "market_cap", 0) or 0,
                    }
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_earnings_yfinance(start_date: str, end_date: str) -> pd.DataFrame:
    """Fallback: fetch earnings calendar using yfinance with parallel requests."""
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame()

    sd = datetime.strptime(start_date, "%Y-%m-%d").date()
    ed = datetime.strptime(end_date, "%Y-%m-%d").date()

    rows = []
    # Use ThreadPoolExecutor for parallel fetching
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch_single_ticker_earnings, sym, sd, ed): sym
            for sym in _MAJOR_TICKERS
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                rows.append(result)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ── Week calculation ──────────────────────────────────────────────────────

def get_week_range(offset: int = 0) -> tuple:
    """Get Monday–Friday date range for a given week offset from current week."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    friday = monday + timedelta(days=4)
    return monday, friday


# ── Treemap chart creation ────────────────────────────────────────────────

# Day color palettes matching quarterchart.com style (light teal/cyan shades)
_DAY_COLORS = {
    0: "#7dd3c8",  # Monday — lighter teal
    1: "#5ec4b6",  # Tuesday — medium-light teal
    2: "#4db6ac",  # Wednesday — medium teal
    3: "#3aaa9e",  # Thursday — medium-dark teal
    4: "#2e9e91",  # Friday — darker teal
}

_DAY_HEADER_COLORS = {
    0: "#5faaa1",  # Monday
    1: "#4e9e94",  # Tuesday
    2: "#3d9187",  # Wednesday
    3: "#2d857a",  # Thursday
    4: "#1d786e",  # Friday
}


def create_earnings_treemap(df: pd.DataFrame, day_label: str, day_idx: int = 0) -> go.Figure:
    """Create a treemap figure for one day's earnings.

    Args:
        df: DataFrame with earnings data for this day
        day_label: Display label for the day
        day_idx: 0=Monday through 4=Friday, used for color selection
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No earnings scheduled",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#999"),
        )
        fig.update_layout(
            height=150,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # Sort by market cap descending
    df = df.sort_values("marketCap", ascending=False).head(50)

    labels = df["symbol"].tolist()
    values = df["marketCap"].tolist()
    values = [max(v, 1e6) if pd.notna(v) else 1e6 for v in values]

    # Build hover text
    customdata = []
    for _, row in df.iterrows():
        sym = row["symbol"]
        mc = row.get("marketCap", 0)
        name = _COMPANY_NAMES.get(sym, "")
        if mc and mc > 0:
            if mc >= 1e12:
                mc_str = f"${mc/1e12:.1f}T"
            elif mc >= 1e9:
                mc_str = f"${mc/1e9:.0f}B"
            elif mc >= 1e6:
                mc_str = f"${mc/1e6:.0f}M"
            else:
                mc_str = ""
        else:
            mc_str = ""
        customdata.append([mc_str, name])

    # Uniform teal color for the day with subtle rank-based variation
    base_color = _DAY_COLORS.get(day_idx, "#4db6ac")
    n = len(labels)
    colors = []
    for i in range(n):
        rank_frac = i / max(n - 1, 1)
        r, g, b = _hex_to_rgb(base_color)
        factor = 1.08 - (rank_frac * 0.15)
        r2 = min(255, int(r * factor))
        g2 = min(255, int(g * factor))
        b2 = min(255, int(b * factor))
        colors.append(f"rgb({r2},{g2},{b2})")

    fig = go.Figure(go.Treemap(
        labels=labels,
        values=values,
        parents=[""] * n,
        textinfo="label",
        textfont=dict(size=16, color="white", family="Arial, sans-serif"),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Market Cap: %{customdata[0]}<br>"
            "%{customdata[1]}"
            "<extra></extra>"
        ),
        customdata=customdata,
        marker=dict(
            colors=colors,
            line=dict(width=2, color="white"),
        ),
        tiling=dict(pad=3),
    ))

    num_companies = len(df)
    if num_companies <= 3:
        h = 200
    elif num_companies <= 10:
        h = 300
    elif num_companies <= 20:
        h = 380
    else:
        h = 440

    fig.update_layout(
        height=h,
        margin=dict(l=2, r=2, t=2, b=2),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# ── Main page renderer ────────────────────────────────────────────────────

def render_earnings_page():
    """Render the full Earnings Calendar page."""

    # ── Inject page-specific CSS ───────────────────────────────────────────
    st.markdown("""
    <style>
    /* Earnings page specific styles */
    .earnings-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 300;
        margin-bottom: 0.2rem;
        color: #212529;
        font-family: 'Georgia', serif;
        letter-spacing: -0.5px;
    }
    .earnings-nav-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 24px;
        border: 2px solid #4db6ac;
        border-radius: 8px;
        background: white;
        color: #4db6ac;
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
    }
    .earnings-nav-btn:hover {
        background: #4db6ac;
        color: white;
    }
    .earnings-date-range {
        text-align: center;
        font-size: 1.15rem;
        padding-top: 8px;
        color: #333;
        font-weight: 500;
    }
    .day-header {
        color: white;
        padding: 10px 16px;
        border-radius: 10px 10px 0 0;
        font-weight: 600;
        font-size: 1rem;
        margin-top: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .day-header .count {
        font-weight: 400;
        opacity: 0.85;
        font-size: 0.9rem;
    }
    .day-empty {
        background: #f8f9fa;
        padding: 35px;
        text-align: center;
        color: #aaa;
        border-radius: 0 0 10px 10px;
        margin-bottom: 8px;
        border: 1px solid #e8e8e8;
        border-top: none;
        font-size: 0.95rem;
    }
    .company-count {
        text-align: center;
        color: #6c757d;
        font-size: 0.9rem;
        margin-bottom: 10px;
    }
    .exchange-section {
        text-align: center;
        margin-top: 20px;
        padding: 15px 0;
    }
    .exchange-title {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 12px;
        color: #333;
    }
    /* -- Earnings Responsive -- */
    @media (max-width: 768px) {
        .earnings-title { font-size: 1.8rem !important; }
        .earnings-nav-btn { padding: 8px 14px !important; font-size: 0.82rem !important; }
        .earnings-date-range { font-size: 0.95rem !important; }
        .day-header { padding: 8px 12px !important; font-size: 0.9rem !important; }
        .day-empty { padding: 20px !important; font-size: 0.85rem !important; }
    }
    @media (max-width: 480px) {
        .earnings-title { font-size: 1.4rem !important; }
        .earnings-nav-btn { padding: 6px 10px !important; font-size: 0.75rem !important; }
        .day-header { font-size: 0.82rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Week navigation state ─────────────────────────────────────────────
    if "earnings_week_offset" not in st.session_state:
        st.session_state.earnings_week_offset = 0

    monday, friday = get_week_range(st.session_state.earnings_week_offset)
    start_str = monday.strftime("%Y-%m-%d")
    end_str = friday.strftime("%Y-%m-%d")

    # ── Title ─────────────────────────────────────────────────────────────
    st.markdown('<h1 class="earnings-title">Earnings Calendar</h1>',
                unsafe_allow_html=True)

    # ── Navigation row ────────────────────────────────────────────────────
    nav_left, nav_center, nav_right = st.columns([1, 2, 1])

    with nav_left:
        if st.button("‹  Prev. Week", key="earn_prev", use_container_width=True):
            st.session_state.earnings_week_offset -= 1
            st.rerun()

    with nav_center:
        st.markdown(
            f'<p class="earnings-date-range">'
            f'From {monday.strftime("%m/%d")} to {friday.strftime("%m/%d")}</p>',
            unsafe_allow_html=True,
        )

    with nav_right:
        if st.button("Next Week  ›", key="earn_next", use_container_width=True):
            st.session_state.earnings_week_offset += 1
            st.rerun()

    # ── Fetch data ────────────────────────────────────────────────────────
    with st.spinner("Loading earnings calendar…"):
        df = fetch_earnings_calendar(start_str, end_str)

    if df.empty:
        st.info(
            "No earnings data available for this week. "
            "This may be because:\n"
            "- No FMP API key is set (set `FMP_API_KEY` environment variable)\n"
            "- No companies are reporting earnings this week\n"
            "- The API is temporarily unavailable"
        )
        _render_day_grid_empty(monday)
        _render_exchange_filters(has_exchange_data=False)
        return

    # Ensure date column is string
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # ── Fetch market caps + exchange if not present ─────────────────────
    if "marketCap" not in df.columns:
        symbols = df["symbol"].unique().tolist()[:200]
        profiles = fetch_market_caps_batch(symbols)
        df["marketCap"] = df["symbol"].map(
            lambda s: profiles.get(s, {}).get("marketCap", 0)
        ).fillna(0)
        if "exchange" not in df.columns:
            df["exchange"] = df["symbol"].map(
                lambda s: profiles.get(s, {}).get("exchange", "")
            )
    else:
        df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce").fillna(0)
        # FMP earnings data has marketCap but no exchange — enrich from profiles
        if "exchange" not in df.columns:
            symbols = df["symbol"].unique().tolist()[:200]
            profiles = fetch_market_caps_batch(symbols)
            df["exchange"] = df["symbol"].map(
                lambda s: profiles.get(s, {}).get("exchange", "")
            )

    # ── DEBUG: show exchange values ──────────────────────────────────────
    if "exchange" in df.columns:
        st.write("DEBUG exchange values:", df[["symbol", "exchange"]].to_dict("records"))
    else:
        st.write("DEBUG: no exchange column in df. Columns:", list(df.columns))
    # DEBUG: show raw profile response for first symbol
    if _fmp_available() and not df.empty:
        _test_sym = df["symbol"].iloc[0]
        try:
            _test_url = f"{_FMP_BASE}/profile/{_test_sym}?apikey={_fmp_key()}"
            _test_resp = requests.get(_test_url, timeout=10)
            _test_data = _test_resp.json()
            if _test_data:
                _keys = list(_test_data[0].keys())
                _ex_fields = {k: _test_data[0].get(k) for k in _keys if "exchange" in k.lower() or "exch" in k.lower()}
                st.write(f"DEBUG profile keys for {_test_sym}:", _ex_fields, "all keys:", _keys[:20])
        except Exception as e:
            st.write(f"DEBUG profile error: {e}")

    # ── Exchange filters (render first so Streamlit reads state) ──────────
    has_exchange = "exchange" in df.columns
    _render_exchange_filters(has_exchange_data=has_exchange)

    # ── Apply exchange filters ──────────────────────────────────────────────────
    st.write("DEBUG selected:", _get_selected_exchanges())
    if has_exchange:
        before_count = len(df)
        df = _filter_by_exchange(df)
        st.write(f"DEBUG filter: {before_count} -> {len(df)} rows")

    # ── Count display ─────────────────────────────────────────────────────────
    total = len(df)
    st.markdown(
        f'<p class="company-count">{total} companies reporting this week</p>',
        unsafe_allow_html=True,
    )

    # ── Render day-by-day treemaps ────────────────────────────────────────────
    days = []
    for i in range(5):  # Monday to Friday
        day_date = monday + timedelta(days=i)
        day_str = day_date.strftime("%Y-%m-%d")
        day_name = day_date.strftime("%A %m/%d")
        day_df = df[df["date"] == day_str].copy()
        days.append((day_name, day_df, day_str, i))

    # Layout: two columns, left = Mon/Tue, right = Wed/Thu/Fri
    col_left, col_right = st.columns(2)

    with col_left:
        for day_name, day_df, _, day_idx in days[:2]:
            _render_day_section(day_name, day_df, day_idx)

    with col_right:
        for day_name, day_df, _, day_idx in days[2:]:
            _render_day_section(day_name, day_df, day_idx)


def _render_day_grid_empty(monday):
    """Render empty day grid when no data is available."""
    days = []
    for i in range(5):
        day_date = monday + timedelta(days=i)
        day_name = day_date.strftime("%A %m/%d")
        days.append((day_name, i))

    col_left, col_right = st.columns(2)
    with col_left:
        for day_name, day_idx in days[:2]:
            _render_day_section(day_name, pd.DataFrame(), day_idx)
    with col_right:
        for day_name, day_idx in days[2:]:
            _render_day_section(day_name, pd.DataFrame(), day_idx)


def _render_day_section(day_name: str, day_df: pd.DataFrame, day_idx: int = 0):
    """Render a single day's earnings section with header and treemap."""
    count = len(day_df)
    header_bg = _DAY_HEADER_COLORS.get(day_idx, "#4db6ac")
    # If empty, use a muted gray
    if count == 0:
        header_bg = "#90a4ae"

    count_text = f"{count} {'company' if count == 1 else 'companies'}"

    st.markdown(
        f'<div class="day-header" style="background:{header_bg};">'
        f'{day_name}'
        f'<span class="count">{count_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if day_df.empty:
        st.markdown('<div class="day-empty">No earnings scheduled</div>',
                    unsafe_allow_html=True)
    else:
        fig = create_earnings_treemap(day_df, day_name, day_idx)
        st.plotly_chart(fig, use_container_width=True, key=f"tree_{day_name}")

        # Compact list below the treemap
        top = day_df.nlargest(10, "marketCap")
        items = []
        for _, row in top.iterrows():
            mc = row.get("marketCap", 0)
            if mc >= 1e12:
                mc_s = f"${mc/1e12:.1f}T"
            elif mc >= 1e9:
                mc_s = f"${mc/1e9:.0f}B"
            elif mc >= 1e6:
                mc_s = f"${mc/1e6:.0f}M"
            else:
                mc_s = ""
            time_s = ""
            t = row.get("time", "")
            if t == "bmo":
                time_s = "Before Open"
            elif t == "amc":
                time_s = "After Close"

            name = _COMPANY_NAMES.get(row["symbol"], "")
            parts = [f"<b>{row['symbol']}</b>"]
            if mc_s:
                parts.append(mc_s)
            if time_s:
                parts.append(time_s)
            items.append(" ".join(parts))

        if items:
            st.markdown(
                f"<p style='font-size:0.78rem; color:#777; line-height:1.6;'>"
                f"{' &middot; '.join(items)}</p>",
                unsafe_allow_html=True,
            )


# ── Exchange filter mapping ──────────────────────────────────────────────────────────
# Maps filter checkbox names to actual FMP exchange values
_EXCHANGE_MAP = {
    "NYSE": ["NYSE", "New York Stock Exchange", "AMEX", "NYSEArca"],
    "NASDAQ": ["NASDAQ", "NasdaqGS", "NasdaqGM", "NasdaqCM", "Nasdaq"],
    "JPX": ["JPX", "TSE", "Tokyo"],
    "HKSE": ["HKSE", "HKG", "Hong Kong"],
    "EURONEXT": ["EURONEXT", "Paris", "Amsterdam", "Brussels", "Lisbon",
                 "LSE", "London", "XETRA", "Frankfurt", "SIX", "Swiss"],
    "TSX": ["TSX", "TSXV", "Toronto"],
}


def _get_selected_exchanges() -> list:
    """Return list of selected exchange filter names from session state."""
    exchanges = ["NYSE", "NASDAQ", "JPX", "HKSE", "EURONEXT", "TSX", "Others"]
    return [ex for ex in exchanges if st.session_state.get(f"ex_{ex}", True)]


def _filter_by_exchange(df: pd.DataFrame) -> pd.DataFrame:
    """Filter DataFrame by selected exchange checkboxes."""
    if "exchange" not in df.columns:
        return df

    selected = _get_selected_exchanges()
    all_exchanges = ["NYSE", "NASDAQ", "JPX", "HKSE", "EURONEXT", "TSX", "Others"]

    if len(selected) == len(all_exchanges):
        return df

    # Build set of ALL known exchange values (for categorization)
    all_known = set()
    for ex_name in _EXCHANGE_MAP:
        for val in _EXCHANGE_MAP[ex_name]:
            all_known.add(val.upper())

    # Build set of SELECTED exchange values
    selected_vals = set()
    for ex_name in selected:
        if ex_name in _EXCHANGE_MAP:
            for val in _EXCHANGE_MAP[ex_name]:
                selected_vals.add(val.upper())

    include_others = "Others" in selected

    def row_matches(exchange_val):
        if pd.isna(exchange_val) or str(exchange_val).strip() == "":
            return include_others
        ex_upper = str(exchange_val).strip().upper()
        # Check if it matches a SELECTED exchange
        if ex_upper in selected_vals:
            return True
        # Check partial matches against selected exchanges
        for ex_name in selected:
            if ex_name != "Others" and ex_name in _EXCHANGE_MAP:
                for pattern in _EXCHANGE_MAP[ex_name]:
                    if pattern.upper() in ex_upper or ex_upper in pattern.upper():
                        return True
        # Check if it matches ANY known exchange (even deselected)
        if ex_upper in all_known:
            return False  # Known exchange but not selected
        for ex_name in _EXCHANGE_MAP:
            for pattern in _EXCHANGE_MAP[ex_name]:
                if pattern.upper() in ex_upper or ex_upper in pattern.upper():
                    return False  # Known exchange but not selected
        # Truly unknown exchange — use "Others" setting
        return include_others

    mask = df["exchange"].apply(row_matches)
    return df[mask].copy()


def _render_exchange_filters(has_exchange_data: bool = False):
    """Render exchange filter checkboxes at the bottom."""
    st.markdown("---")
    st.markdown(
        '<div class="exchange-section">'
        '<p class="exchange-title">Exchange Filters</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    exchanges = ["NYSE", "NASDAQ", "JPX", "HKSE", "EURONEXT", "TSX", "Others"]
    is_disabled = not has_exchange_data
    # Initialize session state defaults (only once)
    for ex in exchanges:
        if f"ex_{ex}" not in st.session_state:
            st.session_state[f"ex_{ex}"] = True
    n_cols = min(len(exchanges), 4)
    for row_start in range(0, len(exchanges), n_cols):
        row_exs = exchanges[row_start:row_start + n_cols]
        cols = st.columns(n_cols)
        for i, ex in enumerate(row_exs):
            with cols[i]:
                st.checkbox(
                    ex, key=f"ex_{ex}",
                    disabled=is_disabled,
                )

    if not has_exchange_data:
        st.caption(
            "Exchange filtering is available with FMP API key. "
            "Set the `FMP_API_KEY` environment variable to enable full features."
        )
