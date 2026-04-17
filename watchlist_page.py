"""
Watchlist page for Quarter Charts.
Lets users build a personal watchlist of up to 20 companies with live market
data, similar to quarterchart.com/watchlist.
"""

import streamlit as st
import pandas as pd
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Persistence ───────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_WATCHLIST_FILE = os.path.join(_BASE_DIR, "watchlist_data.json")
_NAME_CACHE_FILE = os.path.join(_BASE_DIR, "watchlist_names_cache.json")

_MAX_COMPANIES = 20


# ── Company name cache ────────────────────────────────────────────────────
# Company names rarely change, so we cache them on disk to avoid repeated
# slow yfinance .info calls that are prone to rate-limiting.

def _load_name_cache() -> dict:
    """Load cached company names from disk."""
    if os.path.exists(_NAME_CACHE_FILE):
        try:
            with open(_NAME_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_name_cache(cache: dict):
    """Save company name cache to disk."""
    try:
        with open(_NAME_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _default_watchlist_from_pool() -> list:
    """Return the admin-managed ticker pool (NSFQ → 'Manage Available Tickers')
    as the default watchlist. Falls back to a hard-coded list if the DB is
    unreachable, so the page always renders something sensible."""
    try:
        from database import get_ticker_pool
        pool = get_ticker_pool() or []
        if pool:
            return list(pool)[:_MAX_COMPANIES]
    except Exception:
        pass
    return ["NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "TSM", "META", "AVGO", "TSLA"]


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
    return _default_watchlist_from_pool()


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


def _fetch_ticker_all(sym: str, name_cache: dict | None = None) -> dict:
    """Fetch ALL data for one ticker: price, name, P/E, market cap, earnings.
    Uses fast_info first (quick), then info dict only if needed.
    Accepts a name_cache dict to avoid redundant .info calls for names."""
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
        # Only call t.info if we actually need data from it (name or P/E).
        # This is the slow call that gets rate-limited.
        info = {}
        cached_name = (name_cache or {}).get(sym)
        need_info = not cached_name  # only fetch info if name not cached
        if need_info:
            try:
                info = t.info or {}
            except Exception:
                pass
            # Small delay to reduce rate-limiting
            time.sleep(0.15)

        if not price:
            price = info.get("regularMarketPrice") or info.get("currentPrice") or 0
        if not prev_close:
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or 0
        if not market_cap:
            market_cap = info.get("marketCap") or 0

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

        # ── P/E ratio: try multiple sources ──
        pe = None
        try:
            pe = info.get("trailingPE") or info.get("forwardPE")
        except Exception:
            pass
        if pe is None and not need_info:
            # We skipped info earlier; try a targeted fetch for P/E
            try:
                quick_info = t.info or {}
                pe = quick_info.get("trailingPE") or quick_info.get("forwardPE")
                # Also grab name if we didn't have it
                if not cached_name:
                    cached_name = quick_info.get("shortName") or quick_info.get("longName")
            except Exception:
                pass

        # ── Company name: use cache first, then info dict ──
        name = cached_name or info.get("shortName") or info.get("longName") or sym

        # ── earnings date: try get_earnings_dates() (more reliable) ──
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
                    elif isinstance(edate, (int, float)):
                        # Handle UNIX timestamps
                        from datetime import datetime
                        earnings_date = datetime.fromtimestamp(edate).strftime("%m/%d/%Y")
                    else:
                        earnings_date = str(edate)[:10]
        except Exception:
            pass

        # Fallback: try get_earnings_dates if calendar failed
        if not earnings_date:
            try:
                edates = t.get_earnings_dates(limit=4)
                if edates is not None and not edates.empty:
                    from datetime import datetime
                    now = datetime.now()
                    future_dates = edates.index[edates.index >= pd.Timestamp(now)]
                    if len(future_dates) > 0:
                        earnings_date = future_dates[0].strftime("%m/%d/%Y")
                    else:
                        # Show the most recent past date
                        earnings_date = edates.index[0].strftime("%m/%d/%Y")
            except Exception:
                pass

        return {
            "symbol": sym, "name": name, "marketCap": market_cap,
            "price": price, "change_pct": change_pct, "pe": pe,
            "earnings_date": earnings_date or "not scheduled yet",
        }
    except Exception:
        return {
            "symbol": sym, "name": (name_cache or {}).get(sym, sym),
            "marketCap": 0, "price": 0, "change_pct": 0, "pe": None,
            "earnings_date": "N/A",
        }


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_watchlist_data(tickers_tuple: tuple) -> pd.DataFrame:
    """Fetch live market data for all watchlist tickers in parallel.
    Cached for 30 minutes to avoid repeated slow API calls.
    Uses a persistent name cache to avoid rate-limiting on .info calls."""
    if not tickers_tuple:
        return pd.DataFrame()

    # Load name cache — company names rarely change
    name_cache = _load_name_cache()

    result_map = {}
    # Use max_workers=3 to reduce Yahoo Finance rate-limiting.
    # yfinance's .info is not fully thread-safe at high concurrency.
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_fetch_ticker_all, sym, name_cache): sym
                   for sym in tickers_tuple}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                result_map[sym] = future.result()
            except Exception:
                result_map[sym] = {
                    "symbol": sym, "name": name_cache.get(sym, sym),
                    "marketCap": 0, "price": 0, "change_pct": 0,
                    "pe": None, "earnings_date": "N/A",
                }

    # Update name cache with any new names we fetched
    updated = False
    for sym, data in result_map.items():
        fetched_name = data.get("name", sym)
        if fetched_name and fetched_name != sym and name_cache.get(sym) != fetched_name:
            name_cache[sym] = fetched_name
            updated = True
    if updated:
        _save_name_cache(name_cache)

    # Preserve original order
    rows = [result_map.get(sym, {
        "symbol": sym, "name": name_cache.get(sym, sym), "marketCap": 0,
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
    .wl-remove-link {
        display: inline-block;
        color: #b0b0b0;
        font-size: 1.15rem;
        line-height: 1;
        text-decoration: none;
        padding: 4px 8px;
        border-radius: 6px;
        transition: color 0.15s, background 0.15s;
    }
    .wl-remove-link:hover {
        color: #dc2626;
        background: #fee2e2;
    }
    /* Style the search input */
    div[data-testid="stTextInput"] input {
        font-size: 16px;
    }
    /* -- Watchlist Responsive -- */
    .watchlist-scroll-wrap { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .watchlist-scroll-wrap .watchlist-table { min-width: 620px; }
    @media (max-width: 768px) {
        .watchlist-title { font-size: 1.8rem !important; }
        .watchlist-subtitle { font-size: 0.85rem !important; }
        .watchlist-table { font-size: 0.82rem !important; }
        .watchlist-table th { padding: 8px 6px !important; font-size: 0.78rem !important; }
        .watchlist-table td { padding: 10px 6px !important; }
        .company-name { font-size: 0.85rem !important; }
    }
    @media (max-width: 480px) {
        .watchlist-title { font-size: 1.4rem !important; }
        .watchlist-table th { padding: 6px 4px !important; font-size: 0.72rem !important; }
        .watchlist-table td { padding: 8px 4px !important; font-size: 0.78rem !important; }
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

    # ── Handle URL-based remove (?wl_remove=SYM) ──────────────────────────
    # The Remove column in the table is a plain <a> because the table is
    # rendered as raw HTML; clicks round-trip through the URL. We consume
    # the param, mutate state, clear the param, and rerun to avoid the
    # action re-firing on refresh.
    _qp_remove = st.query_params.get("wl_remove")
    if _qp_remove:
        _sym_to_remove = str(_qp_remove).upper().strip()
        if _sym_to_remove in st.session_state.watchlist_tickers:
            st.session_state.watchlist_tickers.remove(_sym_to_remove)
            _save_watchlist(st.session_state.watchlist_tickers)
        # Strip the param so refresh doesn't re-trigger the removal.
        try:
            del st.query_params["wl_remove"]
        except Exception:
            pass
        st.rerun()

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

    add_col1, add_col2 = st.columns([4, 1])
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
    # Preserve the current ticker query-param (if any) so the URL round-trip
    # for ?wl_remove= doesn't drop the rest of the address-bar state.
    _cur_ticker_qp = st.query_params.get("ticker", "")
    _base_qs = "page=watchlist"
    if _cur_ticker_qp:
        _base_qs += f"&ticker={_cur_ticker_qp}"

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
        remove_url = f"?{_base_qs}&wl_remove={sym}"
        rows_html += (
            f'<tr>'
            f'<td><div class="company-name"><a href="{profile_url}" target="_self">{name}</a></div>'
            f'<div class="company-ticker"><a href="{charts_url}" target="_self">{sym}</a></div></td>'
            f'<td>{mc}</td>'
            f'<td>{price}</td>'
            f'<td>{change}</td>'
            f'<td>{pe}</td>'
            f'<td>{earnings_html}</td>'
            f'<td style="text-align:center;">'
            f'<a class="wl-remove-link" href="{remove_url}" target="_self"'
            f' title="Remove {sym} from watchlist"'
            f' aria-label="Remove {sym} from watchlist">&#x1F5D1;</a>'
            f'</td>'
            f'</tr>'
        )

    table_html = (
        '<div class="watchlist-scroll-wrap">'
        '<table class="watchlist-table">'
        '<thead><tr>'
        '<th>Name</th><th>Market Cap</th><th>Share Price</th>'
        '<th>1D Change</th><th>P/E Ratio</th>'
        '<th>Earnings date<br><span style="font-weight:400;color:#aaa;font-size:0.75rem;">can change</span></th>'
        '<th style="text-align:center;">Remove</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody></table>'
        '</div>'
    )

    st.markdown(table_html, unsafe_allow_html=True)

    # NOTE: The "Click to remove from watchlist" grid and the
    # "Quick add popular companies" grid were removed per product request.
    # The wl_remove_* / wl_qadd_* session-state handlers at the top of
    # render_watchlist_page() are kept intact so buttons can be re-enabled
    # later without re-plumbing the logic.

    if count >= _MAX_COMPANIES:
        st.markdown("---")
        st.markdown(
            f'<div class="wl-limit-warn">Watchlist is full ({_MAX_COMPANIES}/{_MAX_COMPANIES}). '
            f'Remove a company to add more.</div>',
            unsafe_allow_html=True,
        )
