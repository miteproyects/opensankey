"""
Watchlist page for Open Sankey.
Lets users build a personal watchlist of up to 20 companies with live market
data, similar to quarterchart.com/watchlist.
"""

import streamlit as st
import pandas as pd
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Persistence ───────────────────────────────────────────────────────────

_WATCHLIST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "watchlist_data.json"
)

_MAX_COMPANIES = 20


def _load_watchlist() -> list:
    """Load watchlist tickers from disk."""
    if os.path.exists(_WATCHLIST_FILE):
        try:
            with open(_WATCHLIST_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[:_MAX_COMPANIES]
        except Exception:
            pass
    return ["NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "TSM", "META", "AVGO", "TSLA"]


def _save_watchlist(tickers: list):
    """Save watchlist tickers to disk."""
    try:
        with open(_WATCHLIST_FILE, "w") as f:
            json.dump(tickers[:_MAX_COMPANIES], f)
    except Exception:
        pass


# ── Ticker validation ─────────────────────────────────────────────────────

def _validate_ticker(sym: str) -> dict | None:
    """
    Validate a ticker symbol. Returns dict with symbol + name if valid,
    or None if invalid.  Uses multiple fallback strategies so tickers like
    KO, V, T, etc. that sometimes lack fast_info still get recognised.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(sym)

        # Strategy 1: fast_info
        try:
            fi = t.fast_info
            price = getattr(fi, "last_price", None)
            if price and price > 0:
                name = sym
                try:
                    name = t.info.get("shortName") or t.info.get("longName") or sym
                except Exception:
                    pass
                return {"symbol": sym, "name": name}
        except Exception:
            pass

        # Strategy 2: t.info dict (slower but more reliable for some tickers)
        try:
            info = t.info
            if info and info.get("regularMarketPrice"):
                return {
                    "symbol": sym,
                    "name": info.get("shortName") or info.get("longName") or sym,
                }
            if info and info.get("currentPrice"):
                return {
                    "symbol": sym,
                    "name": info.get("shortName") or info.get("longName") or sym,
                }
            if info and info.get("shortName") and info.get("marketCap"):
                return {
                    "symbol": sym,
                    "name": info.get("shortName") or sym,
                }
        except Exception:
            pass

        # Strategy 3: try to get history (1 day)
        try:
            hist = t.history(period="1d")
            if not hist.empty:
                name = sym
                try:
                    name = t.info.get("shortName") or sym
                except Exception:
                    pass
                return {"symbol": sym, "name": name}
        except Exception:
            pass

    except Exception:
        pass
    return None


# ── Search helper ─────────────────────────────────────────────────────────

# A small map of common company names → tickers for instant search
_NAME_TO_TICKER = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "meta": "META", "facebook": "META", "nvidia": "NVDA",
    "tesla": "TSLA", "broadcom": "AVGO", "taiwan semiconductor": "TSM",
    "tsmc": "TSM", "jpmorgan": "JPM", "jp morgan": "JPM", "visa": "V",
    "walmart": "WMT", "netflix": "NFLX", "adobe": "ADBE", "coca-cola": "KO",
    "coca cola": "KO", "coke": "KO", "pepsi": "PEP", "pepsico": "PEP",
    "intel": "INTC", "amd": "AMD", "advanced micro": "AMD",
    "qualcomm": "QCOM", "salesforce": "CRM", "disney": "DIS",
    "walt disney": "DIS", "nike": "NKE", "mcdonalds": "MCD",
    "mcdonald's": "MCD", "starbucks": "SBUX", "boeing": "BA",
    "ibm": "IBM", "oracle": "ORCL", "cisco": "CSCO",
    "paypal": "PYPL", "uber": "UBER", "airbnb": "ABNB",
    "palantir": "PLTR", "snowflake": "SNOW", "spotify": "SPOT",
    "shopify": "SHOP", "coinbase": "COIN", "robinhood": "HOOD",
    "rivian": "RIVN", "lucid": "LCID", "nio": "NIO",
    "berkshire": "BRK-B", "berkshire hathaway": "BRK-B",
    "johnson & johnson": "JNJ", "johnson and johnson": "JNJ",
    "procter & gamble": "PG", "procter and gamble": "PG",
    "exxon": "XOM", "exxonmobil": "XOM", "chevron": "CVX",
    "pfizer": "PFE", "moderna": "MRNA", "unitedhealth": "UNH",
    "home depot": "HD", "costco": "COST",
    "mastercard": "MA", "american express": "AXP", "amex": "AXP",
    "goldman sachs": "GS", "morgan stanley": "MS",
    "bank of america": "BAC", "wells fargo": "WFC",
    "citigroup": "C", "caterpillar": "CAT", "3m": "MMM",
    "general electric": "GE", "ge": "GE",
    "sony": "SONY", "samsung": "005930.KS", "toyota": "TM",
    "arm": "ARM", "arm holdings": "ARM",
}


def _search_by_name(query: str) -> str | None:
    """Try to resolve a company name to a ticker symbol."""
    q = query.lower().strip()
    # Direct match
    if q in _NAME_TO_TICKER:
        return _NAME_TO_TICKER[q]
    # Partial match
    for name, ticker in _NAME_TO_TICKER.items():
        if q in name or name in q:
            return ticker
    return None


# ── Data fetching ─────────────────────────────────────────────────────────

def _fetch_single_ticker(sym: str) -> dict:
    """Fetch market data for a single ticker."""
    try:
        import yfinance as yf
        t = yf.Ticker(sym)

        # Try fast_info first
        price = 0
        prev_close = 0
        market_cap = 0
        try:
            fi = t.fast_info
            price = getattr(fi, "last_price", None) or 0
            prev_close = getattr(fi, "previous_close", None) or 0
            market_cap = getattr(fi, "market_cap", None) or 0
        except Exception:
            pass

        # Fallback to info dict if fast_info didn't work
        full_info = {}
        try:
            full_info = t.info or {}
        except Exception:
            pass

        if not price:
            price = full_info.get("regularMarketPrice") or full_info.get("currentPrice") or 0
        if not prev_close:
            prev_close = full_info.get("regularMarketPreviousClose") or full_info.get("previousClose") or 0
        if not market_cap:
            market_cap = full_info.get("marketCap") or 0

        # 1D change
        change_pct = 0.0
        if prev_close and price:
            change_pct = ((price - prev_close) / prev_close) * 100

        # P/E ratio
        pe = None
        try:
            pe = getattr(t.fast_info, "pe_ratio", None)
        except Exception:
            pass
        if pe is None:
            pe = full_info.get("trailingPE") or full_info.get("forwardPE")

        # Company name
        name = full_info.get("shortName") or full_info.get("longName") or sym

        # Earnings date
        earnings_date = None
        try:
            cal = t.calendar
            if cal and isinstance(cal, dict):
                edate = cal.get("Earnings Date", [None])
                if isinstance(edate, list) and edate:
                    edate = edate[0]
                if edate is not None:
                    if hasattr(edate, "strftime"):
                        earnings_date = edate.strftime("%m/%d/%Y")
                    else:
                        earnings_date = str(edate)[:10]
        except Exception:
            pass

        return {
            "symbol": sym,
            "name": name,
            "marketCap": market_cap,
            "price": price,
            "change_pct": change_pct,
            "pe": pe,
            "earnings_date": earnings_date or "not scheduled yet",
        }
    except Exception:
        return {
            "symbol": sym, "name": sym, "marketCap": 0,
            "price": 0, "change_pct": 0, "pe": None,
            "earnings_date": "N/A",
        }


def _fetch_ticker_all(sym: str) -> dict:
    """Fetch ALL data for one ticker: price, name, P/E, market cap, earnings.
    Uses fast_info first (quick), then info dict only if needed."""
    try:
        import yfinance as yf
        t = yf.Ticker(sym)

        # ── fast_info: quick price + market cap ──
        price = prev_close = market_cap = 0
        try:
            fi = t.fast_info
            price = getattr(fi, "last_price", None) or 0
            prev_close = getattr(fi, "previous_close", None) or 0
            market_cap = getattr(fi, "market_cap", None) or 0
        except Exception:
            pass

        # ── info dict: name, P/E, fallback price ──
        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass

        if not price:
            price = info.get("regularMarketPrice") or info.get("currentPrice") or 0
        if not prev_close:
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or 0
        if not market_cap:
            market_cap = info.get("marketCap") or 0

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        pe = info.get("trailingPE") or info.get("forwardPE")
        name = info.get("shortName") or info.get("longName") or sym

        # ── earnings date ──
        earnings_date = None
        try:
            cal = t.calendar
            if cal and isinstance(cal, dict):
                edate = cal.get("Earnings Date", [None])
                if isinstance(edate, list) and edate:
                    edate = edate[0]
                if edate is not None:
                    earnings_date = edate.strftime("%m/%d/%Y") if hasattr(edate, "strftime") else str(edate)[:10]
        except Exception:
            pass

        return {
            "symbol": sym, "name": name, "marketCap": market_cap,
            "price": price, "change_pct": change_pct, "pe": pe,
            "earnings_date": earnings_date or "not scheduled yet",
        }
    except Exception:
        return {
            "symbol": sym, "name": sym, "marketCap": 0,
            "price": 0, "change_pct": 0, "pe": None,
            "earnings_date": "N/A",
        }


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_watchlist_data(tickers_tuple: tuple) -> pd.DataFrame:
    """Fetch live market data for all watchlist tickers in parallel.
    Cached for 30 minutes to avoid repeated slow API calls."""
    if not tickers_tuple:
        return pd.DataFrame()

    result_map = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_ticker_all, sym): sym
                   for sym in tickers_tuple}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                result_map[sym] = future.result()
            except Exception:
                result_map[sym] = {
                    "symbol": sym, "name": sym, "marketCap": 0,
                    "price": 0, "change_pct": 0, "pe": None,
                    "earnings_date": "N/A",
                }

    # Preserve original order
    rows = [result_map.get(sym, {
        "symbol": sym, "name": sym, "marketCap": 0,
        "price": 0, "change_pct": 0, "pe": None,
        "earnings_date": "N/A",
    }) for sym in tickers_tuple]

    return pd.DataFrame(rows)


# ── Formatting helpers ────────────────────────────────────────────────────

def _fmt_market_cap(mc: float) -> str:
    if not mc or mc <= 0:
        return "N/A"
    if mc >= 1e12:
        return f"${mc/1e12:.2f}T"
    elif mc >= 1e9:
        return f"${mc/1e9:.2f}B"
    elif mc >= 1e6:
        return f"${mc/1e6:.0f}M"
    return f"${mc:,.0f}"


def _fmt_price(p: float) -> str:
    if not p or p <= 0:
        return "N/A"
    return f"${p:,.2f}"


def _fmt_change(pct: float) -> str:
    if pct > 0:
        return f'<span style="color:#4caf50;">&#x2299; {pct:.2f}%</span>'
    elif pct < 0:
        return f'<span style="color:#f44336;">&#x2299; {pct:.2f}%</span>'
    return f'<span style="color:#999;">0.00%</span>'


def _fmt_pe(pe) -> str:
    if pe is None or pe == 0:
        return "N/A"
    try:
        return f"{float(pe):.2f}"
    except (ValueError, TypeError):
        return "N/A"


# ── Main page renderer ────────────────────────────────────────────────────

def render_watchlist_page():
    """Render the full Watchlist page."""

    # ── Initialize session state ───────────────────────────────────────────
    if "watchlist_tickers" not in st.session_state:
        st.session_state.watchlist_tickers = _load_watchlist()

    # ── Inject page-specific CSS ───────────────────────────────────────────
    st.markdown("""
    <style>
    .watchlist-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 300;
        margin-bottom: 0.2rem;
        color: #212529;
        font-family: 'Georgia', serif;
        letter-spacing: -0.5px;
    }
    .watchlist-subtitle {
        text-align: center;
        color: #888;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .watchlist-section-title {
        font-weight: 700;
        font-size: 1.1rem;
        margin: 1.2rem 0 0.8rem 0;
        color: #212529;
    }
    .watchlist-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.92rem;
    }
    .watchlist-table th {
        text-align: left;
        padding: 12px 10px;
        border-bottom: 2px solid #dee2e6;
        color: #495057;
        font-weight: 600;
        font-size: 0.85rem;
        white-space: nowrap;
    }
    .watchlist-table td {
        padding: 14px 10px;
        border-bottom: 1px solid #f0f0f0;
        vertical-align: middle;
    }
    .watchlist-table tr:hover td {
        background: #f8f9fa;
    }
    .company-name {
        font-weight: 700;
        color: #212529;
        font-size: 0.95rem;
    }
    .company-ticker {
        color: #6c757d;
        font-size: 0.82rem;
    }
    .earnings-date {
        font-style: italic;
        color: #6c757d;
        font-size: 0.88rem;
    }
    .wl-limit-warn {
        text-align: center;
        color: #856404;
        background: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 0.88rem;
        margin: 8px 0;
    }
    .company-name a {
        color: #212529;
        text-decoration: none;
    }
    .company-name a:hover {
        color: #2475fc;
        text-decoration: underline;
    }
    .company-ticker a {
        color: #6c757d;
        text-decoration: none;
        font-size: 0.78rem;
    }
    .company-ticker a:hover {
        color: #2475fc;
    }
    /* Style the search input */
    div[data-testid="stTextInput"] input {
        font-size: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Title ─────────────────────────────────────────────────────────────
    st.markdown('<h1 class="watchlist-title">My Watchlist</h1>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="watchlist-subtitle">'
        'Track your favorite companies with live market data</p>',
        unsafe_allow_html=True,
    )

    # ── Handle remove actions FIRST (before rendering) ─────────────────────
    for key in list(st.session_state.keys()):
        if key.startswith("wl_remove_") and st.session_state[key]:
            sym = key.replace("wl_remove_", "")
            if sym in st.session_state.watchlist_tickers:
                st.session_state.watchlist_tickers.remove(sym)
                _save_watchlist(st.session_state.watchlist_tickers)
                st.rerun()

    # ── Handle quick-add actions ───────────────────────────────────────────
    for key in list(st.session_state.keys()):
        if key.startswith("wl_qadd_") and st.session_state[key]:
            sym = key.replace("wl_qadd_", "")
            if (sym not in st.session_state.watchlist_tickers
                    and len(st.session_state.watchlist_tickers) < _MAX_COMPANIES):
                st.session_state.watchlist_tickers.append(sym)
                _save_watchlist(st.session_state.watchlist_tickers)
                st.rerun()

    # ── Add Companies section ─────────────────────────────────────────────
    st.markdown('<p class="watchlist-section-title">Add Companies</p>',
                unsafe_allow_html=True)

    add_col1, add_col2 = st.columns([5, 1])
    with add_col1:
        new_ticker = st.text_input(
            "Search company by name or ticker",
            key="watchlist_search",
            placeholder="Search company by name or ticker  (e.g. KO, Apple, TSLA)",
            label_visibility="collapsed",
        )
    with add_col2:
        add_clicked = st.button("Add", key="watchlist_add_btn",
                                use_container_width=True, type="primary")

    if add_clicked and new_ticker:
        query = new_ticker.strip()

        # Check limit
        if len(st.session_state.watchlist_tickers) >= _MAX_COMPANIES:
            st.warning(f"Watchlist is full ({_MAX_COMPANIES} companies max). Remove one first.")
        else:
            # Try as direct ticker first
            ticker_upper = query.upper()

            # Also try name-to-ticker lookup
            name_match = _search_by_name(query)
            candidates = []
            if name_match and name_match != ticker_upper:
                candidates = [ticker_upper, name_match]
            else:
                candidates = [ticker_upper]

            added = False
            for candidate in candidates:
                if candidate in st.session_state.watchlist_tickers:
                    st.info(f"{candidate} is already in your watchlist.")
                    added = True
                    break

                result = _validate_ticker(candidate)
                if result:
                    st.session_state.watchlist_tickers.insert(0, candidate)
                    _save_watchlist(st.session_state.watchlist_tickers)
                    st.rerun()
                    added = True
                    break

            if not added:
                st.warning(f"Could not find '{query}'. Try using the ticker symbol (e.g. KO, AAPL, MSFT).")

    # Show limit info
    tickers = st.session_state.watchlist_tickers
    count = len(tickers)
    remaining = _MAX_COMPANIES - count

    # ── Your Companies ────────────────────────────────────────────────────
    st.markdown(
        f'<p class="watchlist-section-title">'
        f'Your Companies ({count}/{_MAX_COMPANIES})</p>',
        unsafe_allow_html=True,
    )

    if remaining <= 3 and remaining > 0:
        st.markdown(
            f'<div class="wl-limit-warn">You can add {remaining} more '
            f'{"company" if remaining == 1 else "companies"}</div>',
            unsafe_allow_html=True,
        )

    if not tickers:
        st.info("Your watchlist is empty. Add some companies above!")
        return

    # Fetch data
    with st.spinner("Loading market data..."):
        df = _fetch_watchlist_data(tuple(tickers))

    if df.empty:
        st.warning("Could not fetch market data. Please try again later.")
        return

    # ── Build table HTML ──────────────────────────────────────────────────
    rows_html = ""
    for _, row in df.iterrows():
        sym = row["symbol"]
        name = row["name"]
        mc = _fmt_market_cap(row["marketCap"])
        price = _fmt_price(row["price"])
        change = _fmt_change(row["change_pct"])
        pe = _fmt_pe(row["pe"])
        earnings = row.get("earnings_date", "N/A")
        if earnings in ("not scheduled yet", "N/A"):
            earnings_html = f'<span class="earnings-date">{earnings}</span>'
        else:
            earnings_html = earnings
        profile_url = f"?page=profile&ticker={sym}"
        charts_url = f"?page=charts&ticker={sym}"
        rows_html += (
            f'<tr>'
            f'<td><div class="company-name"><a href="{profile_url}" target="_self">{name}</a></div>'
            f'<div class="company-ticker"><a href="{charts_url}" target="_self">{sym}</a></div></td>'
            f'<td>{mc}</td>'
            f'<td>{price}</td>'
            f'<td>{change}</td>'
            f'<td>{pe}</td>'
            f'<td>{earnings_html}</td>'
            f'<td style="text-align:center;font-size:1.3rem;color:#ffc107;">★</td>'
            f'</tr>'
        )

    table_html = (
        '<table class="watchlist-table">'
        '<thead><tr>'
        '<th>Name</th><th>Market Cap</th><th>Share Price</th>'
        '<th>1D Change</th><th>P/E Ratio</th>'
        '<th>Earnings date<br><span style="font-weight:400;color:#aaa;font-size:0.75rem;">can change</span></th>'
        '<th>Actions</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody></table>'
    )

    st.markdown(table_html, unsafe_allow_html=True)

    # ── Remove buttons (★ toggle — click to remove) ───────────────────────
    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.85rem; color:#888; margin-bottom:8px;">'
        'Click to remove from watchlist:</p>',
        unsafe_allow_html=True,
    )

    num_cols = min(len(tickers), 6)
    if num_cols > 0:
        rows_of_btns = [tickers[i:i + num_cols] for i in range(0, len(tickers), num_cols)]
        for btn_row in rows_of_btns:
            cols = st.columns(num_cols)
            for i, sym in enumerate(btn_row):
                with cols[i]:
                    st.button(
                        f"★ {sym}",
                        key=f"wl_remove_{sym}",
                        use_container_width=True,
                    )

    # ── Quick-add popular tickers ─────────────────────────────────────────
    popular = [
        "NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA",
        "TSM", "AVGO", "JPM", "V", "WMT", "NFLX", "ADBE",
        "KO", "PEP", "DIS", "NKE", "CRM", "AMD",
    ]
    available = [t for t in popular if t not in tickers]

    if available and count < _MAX_COMPANIES:
        st.markdown("---")
        st.markdown(
            '<p style="font-size:0.85rem; color:#888; margin-bottom:8px;">'
            'Quick add popular companies:</p>',
            unsafe_allow_html=True,
        )
        num_cols2 = min(len(available), 7)
        rows_of_adds = [available[i:i + num_cols2] for i in range(0, len(available), num_cols2)]
        for add_row in rows_of_adds:
            cols2 = st.columns(num_cols2)
            for i, sym in enumerate(add_row):
                with cols2[i]:
                    st.button(
                        f"+ {sym}",
                        key=f"wl_qadd_{sym}",
                        use_container_width=True,
                    )
    elif count >= _MAX_COMPANIES:
        st.markdown("---")
        st.markdown(
            f'<div class="wl-limit-warn">Watchlist is full ({_MAX_COMPANIES}/{_MAX_COMPANIES}). '
            f'Remove a company to add more.</div>',
            unsafe_allow_html=True,
        )
