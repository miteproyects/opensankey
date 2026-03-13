"""
Data fetching module for the Open Sankey company info/profile page.

Provides comprehensive financial data for company profile pages, including:
- Company description and metadata
- Fundamental metrics (valuation, margins, efficiency)
- Technical metrics (price, volume, moving averages)
- DCF valuation inputs
- Ownership and insider trading data
- Financial health scoring

All primary data functions are cached for 1 hour via Streamlit.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import warnings
import re
import threading
import time as _time

try:
    import requests
except ImportError:
    requests = None  # type: ignore

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Shared in-process yfinance cache
# ---------------------------------------------------------------------------
# Eliminates redundant HTTP calls when multiple functions fetch the same
# ticker data within the same Streamlit process.  Each entry expires after
# _YF_CACHE_TTL seconds.  Thread-safe for use with ThreadPoolExecutor.
# ---------------------------------------------------------------------------

_YF_CACHE_TTL = 3600  # 1 hour — matches @st.cache_data TTLs

_yf_lock = threading.Lock()
_yf_cache: Dict[str, Dict[str, Any]] = {}  # {ticker: {prop: (value, timestamp)}}


def _yf_get(ticker: str, prop: str):
    """Return a cached yfinance Ticker property (info, quarterly_balance_sheet, etc.).

    First call fetches from Yahoo Finance; subsequent calls within TTL return
    the cached value instantly.  Safe to call from multiple threads.
    """
    now = _time.monotonic()
    cache_key = f"{ticker}::{prop}"

    with _yf_lock:
        entry = _yf_cache.get(cache_key)
        if entry is not None:
            val, ts = entry
            if now - ts < _YF_CACHE_TTL:
                return val

    # Fetch outside the lock (allow parallel fetches for DIFFERENT props)
    stock = yf.Ticker(ticker)
    if prop == "info":
        val = stock.info or {}
    elif prop == "quarterly_balance_sheet":
        val = stock.quarterly_balance_sheet
    elif prop == "quarterly_financials":
        val = stock.quarterly_financials
    elif prop == "quarterly_cashflow":
        val = stock.quarterly_cashflow
    elif prop == "cashflow":
        val = stock.cashflow
    elif prop == "financials":
        val = stock.financials
    elif prop == "balance_sheet":
        val = stock.balance_sheet
    elif prop == "institutional_holders":
        val = stock.institutional_holders
    elif prop == "insider_transactions":
        val = stock.insider_transactions
    else:
        val = getattr(stock, prop, None)

    with _yf_lock:
        _yf_cache[cache_key] = (val, now)

    return val


# ---------------------------------------------------------------------------
# quarterchart.com scraper — supplementary data for fields yfinance lacks
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def _fetch_opensankey_supplement(ticker: str) -> Dict[str, str]:
    """Scrape quarterchart.com/info/{ticker} for fields yfinance misses.

    The page embeds company data as HTML-encoded JSON in the SSR HTML.
    We parse specific fields using regex on the raw response.

    Returns a dict with keys: ceo, ipo_date, cagr, employees, payout_ratio.
    Empty dict on failure.
    """
    if requests is None:
        return {}
    url = f"https://quarterchart.com/info/{ticker.upper()}"
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code != 200:
            return {}
        html = resp.text
        result: Dict[str, str] = {}

        # The JSON is HTML-encoded with &quot; for quotes
        # Extract fields using regex on the encoded JSON

        # CEO: "ceo_name": "Jen-Hsun Huang"
        m = re.search(r'ceo_name&quot;:\s*&quot;([^&]+)&quot;', html)
        if m:
            result["ceo"] = m.group(1).strip()

        # IPO Date: "ipo_date": "1999-01-22T00:00:00Z"
        m = re.search(r'ipo_date&quot;:\s*&quot;(\d{4}-\d{2}-\d{2})', html)
        if m:
            result["ipo_date"] = m.group(1).strip()

        # CAGR: "cagr_since_ipo": 0.30651876...
        m = re.search(r'cagr_since_ipo&quot;:\s*([\d.]+)', html)
        if m:
            try:
                cagr_decimal = float(m.group(1))
                result["cagr"] = str(round(cagr_decimal * 100, 2))
            except ValueError:
                pass

        # Employees: "employees": 36000.0
        m = re.search(r'employees&quot;:\s*([\d.]+)', html)
        if m:
            try:
                result["employees"] = str(int(float(m.group(1))))
            except ValueError:
                pass

        # Payout Ratio: "payout_ratio": 0.01
        m = re.search(r'payout_ratio&quot;:\s*([\d.]+)', html)
        if m:
            try:
                result["payout_ratio"] = m.group(1).strip()
            except ValueError:
                pass

        # NOTE: DCF-related fields (WACC, FCF estimates, growth rates) are
        # intentionally NOT scraped here. They are calculated from live yfinance
        # data in get_dcf_data() so values stay fresh regardless of when the
        # user opens the app. Only fields yfinance truly cannot provide are
        # scraped here (CEO name, exact IPO date, CAGR since IPO).

        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Company Icon
# ---------------------------------------------------------------------------

def get_company_icon(ticker: str, sector: str = "", industry: str = "") -> str:
    """Return a representative emoji for a company based on ticker, sector, or industry."""
    _ticker_icons = {
        # Tech / Chips
        "NVDA": "🟢", "AMD": "🔴", "INTC": "🔵", "QCOM": "📡", "AVGO": "📡",
        "TSM": "🏭", "MU": "💾", "MRVL": "📡", "ARM": "🧠", "SMCI": "🖥️",
        # Big Tech
        "AAPL": "🍎", "MSFT": "🪟", "GOOG": "🔍", "GOOGL": "🔍",
        "AMZN": "📦", "META": "👁️", "NFLX": "🎬", "TSLA": "⚡",
        # Consumer / Food & Drink
        "KO": "🥤", "PEP": "🥤", "SBUX": "☕", "MCD": "🍔",
        "WMT": "🛒", "COST": "🛒", "TGT": "🎯", "NKE": "👟",
        "DIS": "🏰", "CMCSA": "📺", "HD": "🔨", "LOW": "🏠",
        # Finance
        "JPM": "🏦", "BAC": "🏦", "GS": "🏦", "MS": "🏦",
        "V": "💳", "MA": "💳", "AXP": "💳", "PYPL": "💰",
        "BRK.A": "🦎", "BRK.B": "🦎", "BLK": "⬛",
        # Healthcare / Pharma
        "JNJ": "💊", "PFE": "💊", "MRK": "💊", "ABBV": "💊",
        "UNH": "🏥", "LLY": "💊", "NVO": "💉", "MRNA": "🧬",
        # Energy
        "XOM": "🛢️", "CVX": "🛢️", "COP": "🛢️", "SLB": "⛽",
        # Automotive
        "F": "🚗", "GM": "🚙", "TM": "🚗", "RIVN": "🛻",
        # Airlines / Travel
        "DAL": "✈️", "UAL": "✈️", "LUV": "✈️", "BA": "✈️",
        "ABNB": "🏡", "BKNG": "🧳", "MAR": "🏨", "HLT": "🏨",
        # Social / Gaming
        "SNAP": "👻", "PINS": "📌", "SPOT": "🎵", "RBLX": "🎮",
        "EA": "🎮", "TTWO": "🎮", "ATVI": "🎮", "U": "🎮",
        # Crypto / Fintech
        "COIN": "🪙", "SQ": "💲", "MSTR": "₿",
        # Telecom
        "T": "📱", "VZ": "📱", "TMUS": "📱",
        # Defense
        "LMT": "🛡️", "RTX": "🚀", "NOC": "🛡️", "GD": "🛡️",
        # Space
        "SPCE": "🚀", "RKLB": "🚀",
    }
    if ticker in _ticker_icons:
        return _ticker_icons[ticker]

    _sector_icons = {
        "Technology": "💻", "Communication Services": "📡",
        "Consumer Cyclical": "🛍️", "Consumer Defensive": "🛒",
        "Financial Services": "🏦", "Healthcare": "🏥",
        "Energy": "⚡", "Industrials": "🏗️",
        "Basic Materials": "⛏️", "Real Estate": "🏢",
        "Utilities": "💡",
    }
    if sector in _sector_icons:
        return _sector_icons[sector]

    ind = industry.lower() if industry else ""
    if "bank" in ind: return "🏦"
    if "pharma" in ind or "drug" in ind: return "💊"
    if "software" in ind: return "💻"
    if "semiconductor" in ind: return "🔲"
    if "auto" in ind: return "🚗"
    if "airline" in ind: return "✈️"
    if "restaurant" in ind or "food" in ind: return "🍽️"
    if "retail" in ind: return "🛍️"
    if "oil" in ind or "gas" in ind: return "🛢️"
    if "insurance" in ind: return "🛡️"

    return "📊"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_num(val: Optional[float], prefix: str = "", suffix: str = "", decimals: int = 2) -> str:
    """Format a number with B/M/K suffixes and optional prefix/suffix.

    Parameters
    ----------
    val : float or None
        The number to format.
    prefix : str
        Prefix to add (e.g., "$").
    suffix : str
        Suffix to add (e.g., "x").
    decimals : int
        Number of decimal places.

    Returns
    -------
    str
        Formatted number string, or "N/A" if None or NaN.
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    try:
        val = float(val)
        sign = "-" if val < 0 else ""
        val = abs(val)

        if val >= 1e12:
            formatted = f"{val / 1e12:.{decimals}f}T"
        elif val >= 1e9:
            formatted = f"{val / 1e9:.{decimals}f}B"
        elif val >= 1e6:
            formatted = f"{val / 1e6:.{decimals}f}M"
        elif val >= 1e3:
            formatted = f"{val / 1e3:.{decimals}f}K"
        else:
            formatted = f"{val:.{decimals}f}"

        return f"{prefix}{sign}{formatted}{suffix}"
    except (ValueError, TypeError):
        return "N/A"


def _pct_str(val: Optional[float], decimals: int = 2) -> str:
    """Format a number as percentage.

    Parameters
    ----------
    val : float or None
        The decimal value (e.g., 0.15 for 15%).
    decimals : int
        Number of decimal places.

    Returns
    -------
    str
        Formatted percentage string (e.g., "15.00%").
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    try:
        return f"{float(val) * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def _safe_get(df: pd.DataFrame, names: List[str]) -> Optional[pd.Series]:
    """Return the first matching row from DataFrame (metrics × dates).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with metric names as index.
    names : list of str
        List of candidate metric names to search for.

    Returns
    -------
    pd.Series or None
        The first matching row, or None if not found.
    """
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


# ---------------------------------------------------------------------------
# Company Description
# ---------------------------------------------------------------------------


def _calc_div_yield(info: dict) -> Optional[float]:
    """Calculate dividend yield, preferring dividendRate / price for accuracy."""
    try:
        div_rate = info.get("dividendRate")
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if div_rate and price and price > 0:
            return div_rate / price  # Returns as decimal ratio (0.0002 = 0.02%)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return info.get("dividendYield")


def _get_ceo(info: dict, ticker: str = "") -> str:
    """Extract CEO name from companyOfficers, with robust title matching."""
    officers = info.get("companyOfficers") or []
    # Priority 1: exact CEO-related titles
    ceo_terms = [
        "chief executive officer", "ceo", "chief executive",
        "president & ceo", "president and ceo", "president, ceo",
        "co-founder, president", "president, chief executive",
        "founder, president", "founder & ceo", "founder and ceo",
        "founder, ceo",
    ]
    for term in ceo_terms:
        for o in officers:
            title = (o.get("title", "") or "").lower()
            if term in title:
                return o.get("name", "N/A")
    # Priority 2: title contains "president" (often the top exec)
    for o in officers:
        title = (o.get("title", "") or "").lower()
        if "president" in title and "vice" not in title:
            return o.get("name", "N/A")
    # Priority 3: title contains "founder" (many CEOs are founders)
    for o in officers:
        title = (o.get("title", "") or "").lower()
        if "founder" in title:
            return o.get("name", "N/A")
    # Fallback: first officer
    if officers:
        return officers[0].get("name", "N/A")
    return "N/A"


def _get_ipo_date(info: dict, ticker_or_stock=None) -> str:
    """Extract IPO date from info, converting epoch if needed.
    Falls back to earliest date in max history if no IPO field available."""
    ipo = info.get("ipoDate")
    if ipo:
        return str(ipo)
    epoch = info.get("firstTradeDateEpochUtc")
    if epoch and isinstance(epoch, (int, float)):
        try:
            return datetime.utcfromtimestamp(epoch).strftime("%Y-%m-%d")
        except Exception:
            pass
    # Fallback: get earliest date from max history
    if ticker_or_stock is not None:
        try:
            stock = ticker_or_stock if hasattr(ticker_or_stock, 'history') else yf.Ticker(ticker_or_stock)
            hist_max = stock.history(period="max", interval="1mo")
            if hist_max is not None and len(hist_max) > 0:
                return hist_max.index[0].strftime("%Y-%m-%d")
        except Exception:
            pass
    return "N/A"


def _map_exchange(exchange_code: str) -> str:
    """Map yfinance exchange codes to human-readable names."""
    _map = {
        "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "NAS": "NASDAQ",
        "NYQ": "NYSE", "NYSE": "NYSE", "NYS": "NYSE",
        "ASE": "AMEX", "PCX": "NYSE ARCA", "BTS": "BATS",
        "LSE": "London", "TYO": "Tokyo", "HKG": "Hong Kong",
    }
    return _map.get(exchange_code, exchange_code)


@st.cache_data(ttl=3600)
def get_company_description(ticker: str) -> Dict[str, Any]:
    """Fetch comprehensive company profile information.

    Returns a dictionary with keys:
    - name: Company name
    - ticker: Stock ticker
    - price: Current stock price
    - description: Company description
    - logo_url: Logo URL
    - sector: Business sector
    - industry: Industry classification
    - country: Country of incorporation
    - exchange: Stock exchange listing
    - ceo: CEO name
    - ipo_date: IPO date
    - employees: Number of employees
    - website: Official website
    - cagr: 5-year CAGR (estimated from revenue)
    - div_yield: Dividend yield
    - payout_ratio: Dividend payout ratio
    - market_cap: Market capitalization

    Parameters
    ----------
    ticker : str
        Stock ticker symbol (e.g., "NVDA", "AAPL").

    Returns
    -------
    dict
        Company information dictionary with sensible defaults for missing data.
    """
    try:
        info = _yf_get(ticker, "info")

        # Get 5-year stock price CAGR
        # Uses split-adjusted close prices from yfinance (correct investment return)
        cagr = None
        try:
            stock = yf.Ticker(ticker)
            hist_5y = stock.history(period="5y", interval="1d")
            if hist_5y is not None and len(hist_5y) >= 200:
                price_now = float(hist_5y["Close"].iloc[-1])
                price_then = float(hist_5y["Close"].iloc[0])
                date_range = (hist_5y.index[-1] - hist_5y.index[0]).days
                n_years = date_range / 365.25
                if price_then > 0 and n_years >= 1:
                    cagr = round((pow(price_now / price_then, 1 / n_years) - 1) * 100, 2)
        except Exception:
            pass

        # Build base result from yfinance
        result = {
            "name": info.get("longName") or info.get("shortName", ticker),
            "ticker": ticker.upper(),
            "price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "description": info.get("longBusinessSummary", ""),
            "logo_url": info.get("logo_url", ""),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "exchange": _map_exchange(info.get("exchange", "")),
            "ceo": _get_ceo(info, ticker),
            "ipo_date": _get_ipo_date(info, ticker),
            "employees": info.get("fullTimeEmployees"),
            "website": info.get("website", "N/A"),
            "cagr": cagr,
            "div_yield": _calc_div_yield(info),
            "payout_ratio": info.get("payoutRatio"),
            "market_cap": info.get("marketCap"),
        }

        # Supplement with quarterchart.com data ONLY for fields yfinance truly misses.
        # CEO name, IPO date, and CAGR since IPO are the primary needs.
        # Employees and payout_ratio are fallbacks only if yfinance returned None.
        qc = _fetch_opensankey_supplement(ticker)
        if qc:
            # CEO — yfinance often lacks the actual CEO (e.g., NVDA misses Jensen Huang)
            if qc.get("ceo"):
                result["ceo"] = qc["ceo"]
            # IPO Date — yfinance ipoDate/firstTradeDateEpochUtc is often None
            if qc.get("ipo_date"):
                result["ipo_date"] = qc["ipo_date"]
            # CAGR since IPO — not a standard yfinance field
            if qc.get("cagr"):
                try:
                    result["cagr"] = float(qc["cagr"])
                except (ValueError, TypeError):
                    pass
            # Employees — only if yfinance returned None
            if not result.get("employees") and qc.get("employees"):
                try:
                    result["employees"] = int(qc["employees"])
                except (ValueError, TypeError):
                    pass
            # Payout Ratio — only if yfinance returned None
            if result.get("payout_ratio") is None and qc.get("payout_ratio"):
                try:
                    result["payout_ratio"] = float(qc["payout_ratio"])
                except (ValueError, TypeError):
                    pass

        return result
    except Exception as exc:
        print(f"[info_data] get_company_description({ticker}): {exc}")
        return {
            "name": ticker,
            "ticker": ticker.upper(),
            "price": None,
            "description": "",
            "logo_url": "",
            "sector": "N/A",
            "industry": "N/A",
            "country": "N/A",
            "exchange": "N/A",
            "ceo": "N/A",
            "ipo_date": "N/A",
            "employees": None,
            "website": "N/A",
            "cagr": None,
            "div_yield": None,
            "payout_ratio": None,
            "market_cap": None,
        }


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_fundamentals(ticker: str) -> List[List[Tuple[str, str, str]]]:
    """Fetch fundamental metrics using stock.info (most reliable source)."""

    def _gc(value, is_growth=False):
        """Color helper: green/red for growth, blue default."""
        if value is None:
            return "blue"
        if is_growth:
            return "green" if value > 0 else ("red" if value < 0 else "blue")
        return "blue"

    try:
        info = _yf_get(ticker, "info")

        # --- Extract all metrics from info dict (most reliable) ---
        ev = info.get("enterpriseValue")
        pe = info.get("trailingPE")
        fpe = info.get("forwardPE")
        peg = info.get("pegRatio") or info.get("trailingPegRatio")
        ps = info.get("priceToSalesTrailing12Months")
        pb = info.get("priceToBook")

        # Cash flow ratios
        ocf = info.get("operatingCashflow")
        fcf = info.get("freeCashflow")
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        shares = info.get("sharesOutstanding")
        mcap = info.get("marketCap")

        pcf = round(mcap / ocf, 1) if mcap and ocf and ocf > 0 else None
        pfcf = round(mcap / fcf, 1) if mcap and fcf and fcf > 0 else None

        # Revenue & EPS
        revenue = info.get("totalRevenue")
        eps = info.get("trailingEps")
        revenue_growth = info.get("revenueGrowth")  # YoY
        earnings_growth = info.get("earningsGrowth")

        # Margins
        gross_margin = info.get("grossMargins")
        operating_margin = info.get("operatingMargins")
        profit_margin = info.get("profitMargins")

        # Returns
        roa = info.get("returnOnAssets")
        roe = info.get("returnOnEquity")

        # Ratios
        current_ratio = info.get("currentRatio")
        quick_ratio = info.get("quickRatio")
        de_ratio = info.get("debtToEquity")
        if de_ratio is not None:
            de_ratio = de_ratio / 100.0  # yfinance returns as percentage

        # Piotroski-like score
        piotroski_score = 0
        piotroski_max = 9
        if roa and roa > 0: piotroski_score += 1
        if ocf and ocf > 0: piotroski_score += 1
        if revenue_growth and revenue_growth > 0: piotroski_score += 1
        if earnings_growth and earnings_growth > 0: piotroski_score += 1
        if profit_margin and profit_margin > 0.05: piotroski_score += 1
        if current_ratio and current_ratio > 1.0: piotroski_score += 1
        if de_ratio is not None and de_ratio < 1.0: piotroski_score += 1
        if roe and roe > 0.10: piotroski_score += 1
        if fcf and ocf and fcf > 0 and ocf > 0: piotroski_score += 1

        # Try to get some additional data from financial statements
        roce = None
        z_score = None
        cash_ratio = None
        ocf_ratio = None
        debt_to_assets = None
        lt_debt_eq = None
        lt_debt_cap = None
        interest_cov = None
        inv_turnover = None
        asset_turnover = None
        recv_turnover = None

        try:
            bs = _yf_get(ticker, "quarterly_balance_sheet")
            inc = _yf_get(ticker, "quarterly_financials")
            cf = _yf_get(ticker, "quarterly_cashflow")

            if bs is not None and not bs.empty:
                ta = _safe_get(bs, ["Total Assets"])
                ca = _safe_get(bs, ["Current Assets"])
                cl = _safe_get(bs, ["Current Liabilities"])
                td = _safe_get(bs, ["Total Debt"])
                ltd = _safe_get(bs, ["Long Term Debt"])
                eq = _safe_get(bs, ["Stockholders Equity", "Total Stockholders Equity", "Stockholders' Equity", "Total Equity Gross Minority Interest"])
                cash = _safe_get(bs, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
                inv = _safe_get(bs, ["Inventory"])
                ar = _safe_get(bs, ["Net Receivables", "Accounts Receivable"])

                # Cash ratio
                if cash is not None and cl is not None and len(cash) > 0 and len(cl) > 0:
                    cl_val = float(cl.iloc[0])
                    if cl_val > 0:
                        cash_ratio = float(cash.iloc[0]) / cl_val
                        if ocf:
                            ocf_ratio = ocf / cl_val

                # Debt/Assets
                if td is not None and ta is not None and len(td) > 0 and len(ta) > 0:
                    ta_val = float(ta.iloc[0])
                    if ta_val > 0:
                        debt_to_assets = float(td.iloc[0]) / ta_val

                # LT debt ratios
                if ltd is not None and eq is not None and len(ltd) > 0 and len(eq) > 0:
                    eq_val = float(eq.iloc[0])
                    ltd_val = float(ltd.iloc[0])
                    if eq_val > 0:
                        lt_debt_eq = ltd_val / eq_val
                        lt_debt_cap = ltd_val / (ltd_val + eq_val) if (ltd_val + eq_val) > 0 else None

                # Asset turnover
                if revenue and ta is not None and len(ta) > 0:
                    ta_val = float(ta.iloc[0])
                    if ta_val > 0:
                        asset_turnover = revenue / ta_val

                # Receivables turnover
                if revenue and ar is not None and len(ar) > 0:
                    ar_val = float(ar.iloc[0])
                    if ar_val > 0:
                        recv_turnover = revenue / ar_val

                # Inventory turnover
                if inv is not None and len(inv) > 0 and inc is not None and not inc.empty:
                    cogs_s = _safe_get(inc, ["Cost Of Revenue"])
                    if cogs_s is not None and len(cogs_s) > 0:
                        inv_val = float(inv.iloc[0])
                        if inv_val > 0:
                            inv_turnover = float(cogs_s.iloc[0]) / inv_val

                # Altman Z
                if all(s is not None and len(s) > 0 for s in [ca, cl, ta]):
                    ta_val = float(ta.iloc[0])
                    if ta_val > 0:
                        x1 = (float(ca.iloc[0]) - float(cl.iloc[0])) / ta_val
                        x2 = (roa or 0)
                        x3 = (operating_margin or 0)
                        x4 = (revenue or 0) / ta_val if ta_val > 0 else 0
                        z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*1.0 + 1.0*x4

                # ROCE
                if eq is not None and td is not None and len(eq) > 0 and len(td) > 0:
                    cap_employed = float(eq.iloc[0]) + float(td.iloc[0])
                    if cap_employed > 0 and operating_margin and revenue:
                        op_income = operating_margin * revenue
                        roce = op_income / cap_employed

            # Interest coverage
            if inc is not None and not inc.empty:
                oi_s = _safe_get(inc, ["Operating Income", "EBIT"])
                ie_s = _safe_get(inc, ["Interest Expense"])
                if oi_s is not None and ie_s is not None and len(oi_s) > 0 and len(ie_s) > 0:
                    ie_val = abs(float(ie_s.iloc[0]))
                    if ie_val > 0:
                        interest_cov = float(oi_s.iloc[0]) / ie_val

        except Exception:
            pass  # Financial statements optional

        # Multi-year growth from annual financials
        rev_1y = revenue_growth
        rev_3y = None
        rev_5y = None
        eps_1y = earnings_growth
        eps_3y = None
        eps_5y = None
        sales_qoq = None
        eps_qoq = None
        sales_qoq_avg = None
        eps_qoq_avg = None

        try:
            ann_fin = _yf_get(ticker, "financials")
            if ann_fin is not None and not ann_fin.empty:
                # Revenue multi-year growth
                if "Total Revenue" in ann_fin.index:
                    rev_series = ann_fin.loc["Total Revenue"].dropna()
                    rev_list = [float(x) for x in rev_series if x > 0]
                    if len(rev_list) >= 4 and rev_list[3] > 0:
                        rev_3y = (rev_list[0] / rev_list[3]) - 1  # Cumulative 3Y

                # EPS multi-year from net income / shares
                if "Net Income" in ann_fin.index:
                    ni_series = ann_fin.loc["Net Income"].dropna()
                    ni_list = [float(x) for x in ni_series]
                    if len(ni_list) >= 4 and ni_list[3] > 0:
                        eps_3y = (ni_list[0] / ni_list[3]) - 1

            # 5-year growth — try annual income_stmt first, fall back to quarterly
            try:
                inc5 = _yf_get(ticker, "financials")  # income_stmt == financials in yfinance
                if inc5 is not None and not inc5.empty and "Total Revenue" in inc5.index:
                    rev5_series = inc5.loc["Total Revenue"].dropna()
                    rev5_list = [float(x) for x in rev5_series if x > 0]
                    # yfinance may only have 4 years — use 4Y as 5Y proxy
                    if len(rev5_list) >= 4 and rev5_list[-1] > 0:
                        rev_5y = (rev5_list[0] / rev5_list[-1]) - 1
                    if "Net Income" in inc5.index:
                        ni5_series = inc5.loc["Net Income"].dropna()
                        ni5_list = [float(x) for x in ni5_series]
                        if len(ni5_list) >= 4 and ni5_list[-1] > 0:
                            eps_5y = (ni5_list[0] / ni5_list[-1]) - 1
            except Exception:
                pass

            # QoQ from quarterly financials
            qf = _yf_get(ticker, "quarterly_financials")
            if qf is not None and not qf.empty:
                if "Total Revenue" in qf.index:
                    q_rev = qf.loc["Total Revenue"].dropna()
                    q_rev_list = [float(x) for x in q_rev if x > 0]
                    if len(q_rev_list) >= 2 and q_rev_list[1] > 0:
                        sales_qoq = (q_rev_list[0] / q_rev_list[1]) - 1
                    if len(q_rev_list) >= 5:
                        qoq_rates = [(q_rev_list[i] / q_rev_list[i+1]) - 1 for i in range(min(4, len(q_rev_list)-1)) if q_rev_list[i+1] > 0]
                        if qoq_rates:
                            sales_qoq_avg = sum(qoq_rates) / len(qoq_rates)
                if "Net Income" in qf.index:
                    q_ni = qf.loc["Net Income"].dropna()
                    q_ni_list = [float(x) for x in q_ni]
                    if len(q_ni_list) >= 2 and q_ni_list[1] > 0:
                        eps_qoq = (q_ni_list[0] / q_ni_list[1]) - 1
                    if len(q_ni_list) >= 5:
                        eq_rates = [(q_ni_list[i] / q_ni_list[i+1]) - 1 for i in range(min(4, len(q_ni_list)-1)) if q_ni_list[i+1] > 0]
                        if eq_rates:
                            eps_qoq_avg = sum(eq_rates) / len(eq_rates)
        except Exception:
            pass

        # P/FCF using TTM FCF for accuracy
        try:
            q_cf = _yf_get(ticker, "quarterly_cashflow")
            if q_cf is not None and not q_cf.empty:
                fcf_q = _safe_get(q_cf, ["Free Cash Flow", "FreeCashFlow"])
                if fcf_q is not None and len(fcf_q) >= 4:
                    ttm_fcf = sum(float(x) for x in fcf_q.iloc[:4])
                    if ttm_fcf > 0 and mcap:
                        pfcf = round(mcap / ttm_fcf, 2)
        except Exception:
            pass

        # Build rows
        rows = [
            [("EV", _fmt_num(ev, prefix="$"), "blue"),
             ("P/E", _fmt_num(pe, decimals=1), _gc(pe)),
             ("Forward P/E", _fmt_num(fpe, decimals=1), _gc(fpe)),
             ("PEG", _fmt_num(peg, decimals=2), _gc(peg))],

            [("P/S", _fmt_num(ps, decimals=2), _gc(ps)),
             ("P/B", _fmt_num(pb, decimals=2), _gc(pb)),
             ("P/CF", _fmt_num(pcf, decimals=1), _gc(pcf)),
             ("P/FCF", _fmt_num(pfcf, decimals=1), _gc(pfcf))],

            [("Sales", _fmt_num(revenue, prefix="$"), "blue"),
             ("Sales 1Y", _pct_str(rev_1y), _gc(rev_1y, True)),
             ("Sales 3Y", _pct_str(rev_3y), _gc(rev_3y, True)),
             ("Sales 5Y", _pct_str(rev_5y), _gc(rev_5y, True))],

            [("EPS", f"${eps:.2f}" if eps else "N/A", "blue"),
             ("EPS 1Y", _pct_str(eps_1y), _gc(eps_1y, True)),
             ("EPS 3Y", _pct_str(eps_3y), _gc(eps_3y, True)),
             ("EPS 5Y", _pct_str(eps_5y), _gc(eps_5y, True))],

            [("Sales QoQ", _pct_str(sales_qoq), _gc(sales_qoq, True)),
             ("EPS QoQ", _pct_str(eps_qoq), _gc(eps_qoq, True)),
             ("Sales QoQ Avg", _pct_str(sales_qoq_avg), _gc(sales_qoq_avg, True)),
             ("EPS QoQ Avg", _pct_str(eps_qoq_avg), _gc(eps_qoq_avg, True))],

            [("Gross Margin", _pct_str(gross_margin), _gc(gross_margin)),
             ("Operating Margin", _pct_str(operating_margin), _gc(operating_margin)),
             ("Profit Margin", _pct_str(profit_margin), _gc(profit_margin)),
             ("ROCE", _pct_str(roce), _gc(roce))],

            [("ROA", _pct_str(roa), _gc(roa)),
             ("ROE", _pct_str(roe), _gc(roe)),
             ("Altman Z", _fmt_num(z_score, decimals=2), "blue"),
             ("Piotroski", f"{piotroski_score}/{piotroski_max}", "blue")],

            [("Current Ratio", _fmt_num(current_ratio, decimals=2), "blue"),
             ("Quick Ratio", _fmt_num(quick_ratio, decimals=2), "blue"),
             ("Cash Ratio", _fmt_num(cash_ratio, decimals=2), "blue"),
             ("Op. CF Ratio", _fmt_num(ocf_ratio, decimals=2), "blue")],

            [("Debt/Equity", _fmt_num(de_ratio, decimals=2) if de_ratio is not None else "N/A", "blue"),
             ("Debt/Assets", _fmt_num(debt_to_assets, decimals=2), "blue"),
             ("Lt Debt/Eq", _fmt_num(lt_debt_eq, decimals=2), "blue"),
             ("Lt Debt/Cap", _pct_str(lt_debt_cap), "blue")],

            [("Intrst Cov.", _fmt_num(interest_cov, decimals=2), _gc(interest_cov)),
             ("Inventory TO", _fmt_num(inv_turnover, decimals=2), "blue"),
             ("Asset TO", _fmt_num(asset_turnover, decimals=2), "blue"),
             ("Receivables TO", _fmt_num(recv_turnover, decimals=2), "blue")],
        ]

        return rows
    except Exception as exc:
        print(f"[info_data] get_fundamentals({ticker}): {exc}")
        return [[("N/A", "N/A", "blue")] * 4] * 10


# ---------------------------------------------------------------------------
# Technical Metrics
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_technicals(ticker: str) -> List[List[Tuple[str, str, str]]]:
    """Fetch technical metrics for 3-row table display.

    Returns a list of 3 lists (rows), where each inner list contains 4 tuples.
    Each tuple is (label, value_str, color).

    Row structure:
    - Row 1: Price, One Day Var., Short Interest, Beta
    - Row 2: Day Low, Day High, Year Low, Year High
    - Row 3: Volume, Avg Volume, Avg 50, Avg 200

    Color: green for values above current price, red for below.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol.

    Returns
    -------
    list of lists of tuples
        3 rows × 4 columns of (label, value, color).
    """
    try:
        info = _yf_get(ticker, "info")

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        one_day_change = info.get("regularMarketChange")
        one_day_change_pct = info.get("regularMarketChangePercent")

        short_interest = info.get("shortRatio")
        beta = info.get("beta")

        day_low = info.get("dayLow")
        day_high = info.get("dayHigh")
        year_low = info.get("fiftyTwoWeekLow")
        year_high = info.get("fiftyTwoWeekHigh")

        volume = info.get("volume")
        avg_volume = info.get("averageVolume")

        # Moving averages (50-day and 200-day)
        avg_50 = info.get("fiftyDayAverage")
        avg_200 = info.get("twoHundredDayAverage")

        def _color_vs_price(value):
            if value is None or price is None:
                return "blue"
            return "green" if value > price else ("red" if value < price else "blue")

        rows = [
            # Row 1: Price, One Day Var., Short Interest, Beta
            [
                ("Price", _fmt_num(price, prefix="$", decimals=2), "blue"),
                ("1D Change", f"{_fmt_num(one_day_change, prefix='$', decimals=2)} ({_pct_str(one_day_change_pct)})" if one_day_change else "N/A", "blue"),
                ("Short Int.", _fmt_num(short_interest, decimals=2), "blue"),
                ("Beta", _fmt_num(beta, decimals=2), "blue"),
            ],
            # Row 2: Day Low, Day High, Year Low, Year High
            [
                ("Day Low", _fmt_num(day_low, prefix="$", decimals=2), _color_vs_price(day_low)),
                ("Day High", _fmt_num(day_high, prefix="$", decimals=2), _color_vs_price(day_high)),
                ("52w Low", _fmt_num(year_low, prefix="$", decimals=2), _color_vs_price(year_low)),
                ("52w High", _fmt_num(year_high, prefix="$", decimals=2), _color_vs_price(year_high)),
            ],
            # Row 3: Volume, Avg Volume, Avg 50, Avg 200
            [
                ("Volume", _fmt_num(volume), "blue"),
                ("Avg Vol", _fmt_num(avg_volume), "blue"),
                ("Avg 50d", _fmt_num(avg_50, prefix="$", decimals=2), _color_vs_price(avg_50)),
                ("Avg 200d", _fmt_num(avg_200, prefix="$", decimals=2), _color_vs_price(avg_200)),
            ],
        ]

        return rows
    except Exception as exc:
        print(f"[info_data] get_technicals({ticker}): {exc}")
        return [[("N/A", "N/A", "blue")] * 4] * 3


# ---------------------------------------------------------------------------
# DCF Data
# ---------------------------------------------------------------------------

def _get_risk_free_rate() -> float:
    """Fetch current 10-Year US Treasury yield as the risk-free rate.

    Uses the ^TNX ticker (CBOE 10-Year Treasury Note Yield Index) from yfinance.
    Falls back to a conservative estimate if unavailable.
    """
    try:
        tnx = yf.Ticker("^TNX")
        hist = tnx.history(period="5d")
        if hist is not None and not hist.empty:
            # ^TNX reports yield as a percentage (e.g., 4.25 = 4.25%)
            latest_yield = float(hist["Close"].dropna().iloc[-1])
            return latest_yield / 100  # Convert to decimal: 4.25 → 0.0425
    except Exception:
        pass
    return 0.04  # Conservative fallback: 4%


def _get_effective_tax_rate_cached(ticker: str) -> float:
    """Calculate effective tax rate using shared cache. Falls back to 21%."""
    try:
        inc = _yf_get(ticker, "financials")
        if inc is not None and not inc.empty:
            tax_row = _safe_get(inc, ["Tax Provision", "Income Tax Expense"])
            pretax_row = _safe_get(inc, ["Pretax Income", "Income Before Tax"])
            if tax_row is not None and pretax_row is not None:
                if len(tax_row) >= 1 and len(pretax_row) >= 1:
                    tax = float(tax_row.iloc[0])
                    pretax = float(pretax_row.iloc[0])
                    if pretax > 0:
                        rate = tax / pretax
                        return max(0.05, min(0.45, rate))
    except Exception:
        pass
    return 0.21


def _get_effective_tax_rate(stock) -> float:
    """Calculate effective tax rate from financial statements.

    Falls back to US statutory rate (21%) if not calculable.
    """
    try:
        inc = stock.financials
        if inc is not None and not inc.empty:
            tax_row = _safe_get(inc, ["Tax Provision", "Income Tax Expense"])
            pretax_row = _safe_get(inc, ["Pretax Income", "Income Before Tax"])
            if tax_row is not None and pretax_row is not None:
                if len(tax_row) >= 1 and len(pretax_row) >= 1:
                    tax = float(tax_row.iloc[0])
                    pretax = float(pretax_row.iloc[0])
                    if pretax > 0:
                        rate = tax / pretax
                        return max(0.05, min(0.45, rate))  # Bound: 5%-45%
    except Exception:
        pass
    return 0.21  # US statutory corporate rate


@st.cache_data(ttl=3600)
def get_dcf_data(ticker: str) -> Dict[str, Any]:
    """Fetch inputs for DCF valuation model using real-time market data.

    All values are derived from live yfinance data — no external scraping.
    This ensures the DCF calculator is always fresh regardless of when the
    user opens the app.

    Financial best practices applied:
    - Risk-free rate: Live 10-Year US Treasury yield (^TNX)
    - WACC: CAPM with live beta, dynamic risk-free rate, company-specific debt
    - Tax rate: Effective rate from financial statements (fallback: 21%)
    - FCF: TTM from quarterly cash flow statements
    - Growth rates: Blended from historical FCF + analyst revenue growth estimates
    - Terminal growth: 3% (long-term nominal GDP growth approximation)
    - Discount rate: 10% default (user-adjustable, industry standard for equity)

    Returns dict with: current_fcf, wacc, fcf_growth_rates, terminal_growth_rate,
    discount_rate, shares_outstanding, net_debt.
    """
    try:
        info = _yf_get(ticker, "info")

        # ── 1. Current FCF (Trailing Twelve Months) ─────────────────────────
        fcf_current = None

        # Best: Sum last 4 quarterly FCF values for true TTM
        try:
            q_cf = _yf_get(ticker, "quarterly_cashflow")
            if q_cf is not None and not q_cf.empty:
                fcf_q = _safe_get(q_cf, ["Free Cash Flow", "FreeCashFlow"])
                if fcf_q is not None and len(fcf_q) >= 4:
                    ttm_fcf = sum(float(x) for x in fcf_q.iloc[:4])
                    if ttm_fcf > 0:
                        fcf_current = ttm_fcf
                elif fcf_q is not None and len(fcf_q) >= 1:
                    fcf_current = float(fcf_q.iloc[0]) * 4  # Annualize

                # Fallback: OCF - CapEx
                if not fcf_current:
                    ocf_s = _safe_get(q_cf, ["Operating Cash Flow"])
                    capex_s = _safe_get(q_cf, ["Capital Expenditure"])
                    if ocf_s is not None and capex_s is not None and len(ocf_s) >= 4 and len(capex_s) >= 4:
                        ttm_ocf = sum(float(x) for x in ocf_s.iloc[:4])
                        ttm_capex = sum(abs(float(x)) for x in capex_s.iloc[:4])
                        fcf_current = ttm_ocf - ttm_capex
        except Exception:
            pass

        # Second fallback: yfinance info field
        if not fcf_current:
            fcf_current = info.get("freeCashflow")

        # Third fallback: Most recent annual FCF
        if not fcf_current:
            try:
                a_cf = _yf_get(ticker, "cashflow")
                if a_cf is not None and not a_cf.empty:
                    fcf_a = _safe_get(a_cf, ["Free Cash Flow", "FreeCashFlow"])
                    if fcf_a is not None and len(fcf_a) > 0:
                        fcf_current = float(fcf_a.iloc[0])
            except Exception:
                pass

        # ── 2. WACC (Weighted Average Cost of Capital) ──────────────────────
        # Uses CAPM with live market data
        risk_free_rate = _get_risk_free_rate()
        equity_risk_premium = 0.055  # Damodaran long-term average (~5.5%)
        beta = info.get("beta", 1.0) or 1.0

        cost_of_equity = risk_free_rate + beta * equity_risk_premium

        market_cap = info.get("marketCap") or 100e9
        total_debt = info.get("totalDebt", 0) or 0

        wacc = cost_of_equity  # Default: all-equity
        if total_debt > 0:
            # Cost of debt from actual interest expense
            cost_of_debt = 0.05  # fallback
            try:
                income_stmt = _yf_get(ticker, "financials") or pd.DataFrame()
                ie_series = _safe_get(income_stmt, ["Interest Expense"])
                if ie_series is not None and len(ie_series) > 0:
                    ie = abs(float(ie_series.iloc[0]))
                    if total_debt > 0:
                        cost_of_debt = max(0.02, min(0.15, ie / total_debt))
            except Exception:
                pass

            tax_rate = _get_effective_tax_rate_cached(ticker)

            total_capital = market_cap + total_debt
            weight_equity = market_cap / total_capital
            weight_debt = total_debt / total_capital
            wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))

        wacc = max(0.06, min(0.25, wacc))  # Bound: 6%-25%

        # ── 3. FCF Growth Rates (5-year projection) ─────────────────────────
        # Strategy: blend historical FCF growth with analyst revenue estimates,
        # then apply mean-reversion decay toward terminal growth rate.
        terminal_growth = 0.03  # ~Long-term nominal GDP growth

        fcf_growth_rates = [0.10, 0.08, 0.06, 0.05, 0.04]  # Conservative default

        # 3a. Historical FCF growth from annual statements
        hist_fcf_growth = None
        try:
            cf_stmt = _yf_get(ticker, "cashflow")
            if cf_stmt is not None and not cf_stmt.empty:
                fcf_series = _safe_get(cf_stmt, ["Free Cash Flow", "FreeCashFlow"])
                if fcf_series is not None and len(fcf_series) >= 2:
                    fcf_list = [float(x) for x in fcf_series.dropna().iloc[:5] if x > 0]
                    if len(fcf_list) >= 2:
                        growth_rates_hist = []
                        for i in range(len(fcf_list) - 1):
                            if fcf_list[i+1] > 0:
                                g = (fcf_list[i] / fcf_list[i+1]) - 1
                                growth_rates_hist.append(max(-0.5, min(2.0, g)))
                        if growth_rates_hist:
                            # Weighted average: more weight to recent years
                            weights = list(range(len(growth_rates_hist), 0, -1))
                            hist_fcf_growth = float(np.average(growth_rates_hist, weights=weights))
        except Exception:
            pass

        # 3b. Analyst revenue growth estimates (forward-looking)
        analyst_growth = None
        try:
            # Try yfinance growth_estimates
            ge = yf.Ticker(ticker).growth_estimates
            if ge is not None and not ge.empty and ticker.upper() in ge.columns:
                col = ge[ticker.upper()]
                # Look for "Next 5 Years (per annum)" or similar rows
                for idx_label in col.index:
                    if "next 5" in str(idx_label).lower() or "next five" in str(idx_label).lower():
                        val = col[idx_label]
                        if pd.notna(val) and isinstance(val, (int, float)):
                            analyst_growth = float(val)
                            break
                # Fallback: "Next Year" estimate
                if analyst_growth is None:
                    for idx_label in col.index:
                        if "next year" in str(idx_label).lower():
                            val = col[idx_label]
                            if pd.notna(val) and isinstance(val, (int, float)):
                                analyst_growth = float(val)
                                break
        except Exception:
            pass

        # Fallback: revenue growth from yfinance info
        if analyst_growth is None:
            rg = info.get("revenueGrowth")
            if rg is not None and isinstance(rg, (int, float)):
                analyst_growth = float(rg)

        # 3c. Blend historical + analyst into projected growth rates
        base_growth = None
        if hist_fcf_growth is not None and analyst_growth is not None:
            # Blend: 50% historical FCF, 50% analyst forward estimate
            base_growth = 0.5 * hist_fcf_growth + 0.5 * analyst_growth
        elif hist_fcf_growth is not None:
            base_growth = hist_fcf_growth
        elif analyst_growth is not None:
            base_growth = analyst_growth

        if base_growth is not None:
            base_growth = max(-0.3, min(1.5, base_growth))  # Cap: -30% to +150%
            # Mean-reversion decay: linearly interpolate from base_growth to terminal over 5 years
            fcf_growth_rates = []
            for i in range(5):
                # Year 1 = full base_growth, year 5 ≈ near terminal
                weight = i / 5  # 0, 0.2, 0.4, 0.6, 0.8
                decayed = base_growth * (1 - weight) + terminal_growth * weight
                fcf_growth_rates.append(max(terminal_growth, decayed))

        # ── 4. Shares Outstanding ───────────────────────────────────────────
        shares_outstanding = info.get("sharesOutstanding") or 1

        # ── 5. Net Debt (Enterprise Value - Market Cap) ─────────────────────
        net_debt = 0
        try:
            ev = info.get("enterpriseValue")
            mc = info.get("marketCap")
            if ev and mc:
                net_debt = ev - mc
        except Exception:
            pass

        return {
            "current_fcf": fcf_current or 0,
            "base_growth_rate": fcf_growth_rates[0] if fcf_growth_rates else 0.05,
            "terminal_growth_rate": terminal_growth,
            "discount_rate": 0.10,  # Industry standard 10% (user-adjustable)
            "wacc": wacc,  # Live CAPM calculation
            "fcf_growth_rates": fcf_growth_rates,
            "shares_outstanding": shares_outstanding,
            "net_debt": net_debt,
            "risk_free_rate": risk_free_rate,  # For transparency in UI
        }
    except Exception as exc:
        print(f"[info_data] get_dcf_data({ticker}): {exc}")
        return {
            "current_fcf": 0,
            "base_growth_rate": 0.05,
            "terminal_growth_rate": 0.03,
            "discount_rate": 0.10,
            "wacc": 0.10,
            "fcf_growth_rates": [0.10, 0.08, 0.06, 0.05, 0.04],
            "shares_outstanding": 1,
            "net_debt": 0,
            "risk_free_rate": 0.04,
        }


# ---------------------------------------------------------------------------
# Ownership Data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_ownership_data(ticker: str) -> Dict[str, Any]:
    """Fetch ownership structure and major institutional holders.

    Returns a dictionary with keys:
    - institutional_holders: List of {name, pct_held} (top 10)
    - insider_pct: Percentage held by insiders
    - institutional_pct: Percentage held by institutions
    - public_pct: Percentage held by public

    Parameters
    ----------
    ticker : str
        Stock ticker symbol.

    Returns
    -------
    dict
        Ownership data with institutional holders list and percentages.
    """
    try:
        info = _yf_get(ticker, "info")

        institutional_holders = []
        insider_pct = info.get("heldPercentInsiders", info.get("insidersPercentHeld", 0)) or 0
        institutional_pct = info.get("heldPercentInstitutions", info.get("institutionsPercentHeld", 0)) or 0
        public_pct = max(0, 1.0 - insider_pct - institutional_pct)

        # Try to get institutional holders
        try:
            holders = _yf_get(ticker, "institutional_holders")
            if holders is not None and not holders.empty:
                for idx, row in holders.head(10).iterrows():
                    holder_name = row.get("Holder", row.get("holder", ""))
                    pct = row.get("pctHeld", row.get("Shares percent held", row.get("% Out", 0)))
                    try:
                        pct = float(pct) if pct else 0
                    except (ValueError, TypeError):
                        pct = 0
                    institutional_holders.append({
                        "name": str(holder_name),
                        "pct_held": pct,
                    })
        except Exception as e:
            print(f"[info_data] institutional_holders error: {e}")

        return {
            "institutional_holders": institutional_holders,
            "insider_pct": insider_pct,
            "institutional_pct": institutional_pct,
            "public_pct": public_pct,
        }
    except Exception as exc:
        print(f"[info_data] get_ownership_data({ticker}): {exc}")
        return {
            "institutional_holders": [],
            "insider_pct": 0,
            "institutional_pct": 0,
            "public_pct": 1.0,
        }


# ---------------------------------------------------------------------------
# Insider Trades
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_insider_trades(ticker: str) -> Dict[str, Any]:
    """Fetch insider trading activity.

    Returns a dictionary with keys:
    - trades: List of last 10 insider trades {name, shares, price, security_name, date}
    - monthly_activity: List of {month, bought, sold} for bar chart

    Parameters
    ----------
    ticker : str
        Stock ticker symbol.

    Returns
    -------
    dict
        Insider trades list and monthly activity summary.
    """
    try:
        trades = []
        monthly_activity = {}

        # Try to get insider trades
        try:
            insider_df = _yf_get(ticker, "insider_transactions")
            if insider_df is not None and not insider_df.empty:
                for idx, row in insider_df.iterrows():
                    # yfinance columns: Insider, Position, Text, Transaction,
                    #   Shares, Value, Start Date, Ownership, URL
                    insider_name = str(row.get("Insider", row.get("Insider Trading", "")))
                    if insider_name == "nan":
                        insider_name = ""

                    # "Text" has description (e.g. "Sale at price..."),
                    # "Transaction" has moneyText (may be NaN)
                    text_val = row.get("Text", "")
                    tx_val = row.get("Transaction", "")
                    # Use whichever is not NaN/empty
                    transaction_type = ""
                    for v in [text_val, tx_val]:
                        s = str(v).strip() if v is not None else ""
                        if s and s.lower() != "nan":
                            transaction_type = s
                            break

                    shares_val = row.get("Shares", 0)
                    try:
                        shares_val = int(float(shares_val)) if shares_val and str(shares_val).lower() != "nan" else 0
                    except (ValueError, TypeError):
                        shares_val = 0

                    # Value is total $ value of transaction
                    price_val = row.get("Value", 0)
                    try:
                        price_val = float(price_val) if price_val and str(price_val).lower() != "nan" else 0
                    except (ValueError, TypeError):
                        price_val = 0
                    # Convert total value to per-share price
                    if shares_val and shares_val > 0 and price_val > 0:
                        price_per_share = round(price_val / shares_val, 2)
                    else:
                        price_per_share = 0

                    # Date from Start Date column
                    date_val = row.get("Start Date", row.get("Date", ""))
                    if hasattr(date_val, 'strftime'):
                        date_str = date_val.strftime("%Y-%m-%d")
                    elif hasattr(idx, 'strftime'):
                        date_str = idx.strftime("%Y-%m-%d")
                    else:
                        date_str = str(date_val)[:10] if date_val else str(idx)[:10]

                    relation = str(row.get("Ownership", row.get("Position", "")))
                    if relation == "nan":
                        relation = ""

                    trades.append({
                        "insider_name": insider_name,
                        "relation": relation,
                        "transaction_date": date_str,
                        "transaction_type": transaction_type,
                        "shares": shares_val,
                        "price": price_per_share,
                    })

                    # Aggregate into monthly activity
                    month_key = date_str[:7] if len(date_str) >= 7 else "unknown"
                    if month_key not in monthly_activity:
                        monthly_activity[month_key] = {"bought": 0, "sold": 0}

                    # yfinance Text field examples:
                    #   "Sale at price 136.00 per share."
                    #   "Conversion of Exercise of derivative security"
                    #   "Purchase at price 24.50 per share."
                    tx_lower = transaction_type.lower()
                    if any(kw in tx_lower for kw in ["buy", "purchase", "acqui", "exercise"]):
                        monthly_activity[month_key]["bought"] += abs(shares_val)
                    elif any(kw in tx_lower for kw in ["sell", "sale", "dispos", "gift"]):
                        monthly_activity[month_key]["sold"] += abs(shares_val)

                    if len(trades) >= 20:
                        break
        except Exception as e:
            print(f"[info_data] insider_trades parse error: {e}")
            import traceback
            traceback.print_exc()

        # Convert monthly activity to list format
        monthly_list = [
            {"month": month, "bought": data["bought"], "sold": data["sold"]}
            for month, data in sorted(monthly_activity.items())
        ]

        return {
            "recent_trades": trades,
            "monthly_activity": monthly_list,
        }
    except Exception as exc:
        print(f"[info_data] get_insider_trades({ticker}): {exc}")
        return {
            "recent_trades": [],
            "monthly_activity": [],
        }


# ---------------------------------------------------------------------------
# DCF Valuation Calculator
# ---------------------------------------------------------------------------

def calculate_dcf(
    fcf: float,
    growth_rates: List[float],
    terminal_growth: float,
    discount_rate: float,
    shares_outstanding: float,
    net_debt: float,
) -> Optional[float]:
    """Calculate DCF-based equity value per share.

    Pure calculation function (not cached). Uses the DCF formula:
    Enterprise Value = PV(FCF in projection period) + PV(Terminal Value)
    Equity Value = Enterprise Value - Net Debt
    Per Share Value = Equity Value / Shares Outstanding

    Parameters
    ----------
    fcf : float
        Current free cash flow.
    growth_rates : list of float
        Annual growth rates for projection period (typically 5 rates for 5 years).
    terminal_growth : float
        Perpetual growth rate for terminal value (Gordon growth).
    discount_rate : float
        Discount rate / WACC.
    shares_outstanding : float
        Number of shares outstanding.
    net_debt : float
        Total debt minus cash.

    Returns
    -------
    float or None
        Equity value per share, or None if calculation fails.
    """
    try:
        if fcf <= 0 or shares_outstanding <= 0 or discount_rate <= 0:
            return None

        # Project FCF for each period
        pv_fcf = 0
        current_fcf = fcf
        for i, growth_rate in enumerate(growth_rates):
            year = i + 1
            current_fcf = current_fcf * (1 + growth_rate)
            pv = current_fcf / ((1 + discount_rate) ** year)
            pv_fcf += pv

        # Terminal value using Gordon growth
        terminal_fcf = current_fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** len(growth_rates))

        # Enterprise and equity value
        enterprise_value = pv_fcf + pv_terminal
        equity_value = enterprise_value - net_debt

        if equity_value <= 0:
            return None

        equity_per_share = equity_value / shares_outstanding
        return equity_per_share
    except Exception as exc:
        print(f"[info_data] calculate_dcf(): {exc}")
        return None


# ---------------------------------------------------------------------------
# Financial Health Score
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def _score_tiered(value: Optional[float], thresholds: list) -> int:
    """Score a value 0-5 based on threshold tiers.

    thresholds is a list of (min_val, points) sorted descending by threshold.
    Example: [(8, 5), (5, 4), (4, 3), (2, 2), (1, 1)] means >=8 → 5pts, >=5 → 4pts, etc.
    """
    if value is None:
        return 0
    for threshold, points in thresholds:
        if value >= threshold:
            return points
    return 0


def get_score(ticker: str, _version: int = 3) -> int:
    """Calculate financial health score (0-100).

    Categories (100 total):
    - Profitability: 20 pts (Gross Margin, Profit Margin, ROE, ROA — each 5)
    - Liquidity: 20 pts (Current Ratio, Quick Ratio, Cash Ratio, Op CF Ratio — each 5)
    - Leverage: 25 pts (D/E, Interest Coverage, D/A, LT Debt/Cap, Altman Z — each 5)
    - Efficiency: 15 pts (Asset Turnover, Inventory Turnover, Receivables Turnover — each 5)
    - Growth: 10 pts (EPS Growth 1Y, CAGR — each 5)
    - Valuation: 10 pts (P/E Ratio, P/B Ratio — each 5)
    """
    try:
        info = _yf_get(ticker, "info")

        _qbs = _yf_get(ticker, "quarterly_balance_sheet")
        bs = _qbs if _qbs is not None and not _qbs.empty else (_yf_get(ticker, "balance_sheet") or pd.DataFrame())
        _qcf = _yf_get(ticker, "quarterly_cashflow")
        cf = _qcf if _qcf is not None and not _qcf.empty else (_yf_get(ticker, "cashflow") or pd.DataFrame())
        _qfin = _yf_get(ticker, "quarterly_financials")
        inc = _qfin if _qfin is not None and not _qfin.empty else (_yf_get(ticker, "financials") or pd.DataFrame())

        score = 0
        breakdown = {}

        # Helper to get a float from info or balance sheet
        def _bs_val(keys):
            s = _safe_get(bs, keys)
            return float(s.iloc[0]) if s is not None and len(s) > 0 else None

        def _cf_val(keys):
            s = _safe_get(cf, keys)
            return float(s.iloc[0]) if s is not None and len(s) > 0 else None

        def _inc_val(keys):
            s = _safe_get(inc, keys)
            return float(s.iloc[0]) if s is not None and len(s) > 0 else None

        # ── Profitability 20/20 ──
        gross_margin = info.get("grossMargins")  # decimal
        profit_margin = info.get("profitMargins")
        roe = info.get("returnOnEquity")
        roa = info.get("returnOnAssets")

        # Convert to percentages for thresholding
        gm_pct = (gross_margin * 100) if gross_margin else None
        pm_pct = (profit_margin * 100) if profit_margin else None
        roe_pct = (roe * 100) if roe else None
        roa_pct = (roa * 100) if roa else None

        # Gross Margin: >=60% → 5, >=40% → 4, >=20% → 3, >=10% → 2, >0 → 1
        gm_s = _score_tiered(gm_pct, [(60, 5), (40, 4), (20, 3), (10, 2), (0.01, 1)])
        pm_s = _score_tiered(pm_pct, [(20, 5), (10, 4), (5, 3), (0.01, 2)])
        roe_s = _score_tiered(roe_pct, [(25, 5), (15, 4), (10, 3), (5, 2), (0.01, 1)])
        roa_s = _score_tiered(roa_pct, [(15, 5), (10, 4), (5, 3), (2, 2), (0.01, 1)])

        profitability = gm_s + pm_s + roe_s + roa_s
        score += profitability
        breakdown["profitability"] = {"total": profitability, "max": 20,
            "gross_margin": gm_s, "profit_margin": pm_s, "roe": roe_s, "roa": roa_s}

        # ── Liquidity 20/20 ──
        current_ratio = info.get("currentRatio")
        quick_ratio = info.get("quickRatio")

        # Cash ratio = (cash + short_term_investments) / current_liabilities
        cash = _bs_val(["Cash And Cash Equivalents", "Cash"])
        short_inv = _bs_val(["Short Term Investments", "OtherShortTermInvestments"])
        curr_liab = _bs_val(["Current Liabilities", "Total Current Liabilities"])
        cash_ratio = None
        if cash is not None and curr_liab and curr_liab > 0:
            numerator = cash + (short_inv if short_inv else 0)
            cash_ratio = numerator / curr_liab

        # Operating cash flow ratio = OCF / current liabilities
        ocf = _cf_val(["Operating Cash Flow"])
        ocf_ratio = None
        if ocf is not None and curr_liab and curr_liab > 0:
            ocf_ratio = ocf / curr_liab

        cr_s = _score_tiered(current_ratio, [(3, 5), (2, 4), (1.5, 3), (1, 2), (0.5, 1)])
        qr_s = _score_tiered(quick_ratio, [(2, 5), (1.5, 4), (1, 3), (0.5, 2), (0.2, 1)])
        cashr_s = _score_tiered(cash_ratio, [(1, 5), (0.5, 4), (0.3, 3), (0.15, 2), (0.05, 1)])
        ocfr_s = _score_tiered(ocf_ratio, [(1.5, 5), (1, 4), (0.5, 3), (0.2, 2), (0.05, 1)])

        liquidity = cr_s + qr_s + cashr_s + ocfr_s
        score += liquidity
        breakdown["liquidity"] = {"total": liquidity, "max": 20,
            "current_ratio": cr_s, "quick_ratio": qr_s, "cash_ratio": cashr_s, "ocf_ratio": ocfr_s}

        # ── Leverage 25/25 ──
        de_raw = info.get("debtToEquity")  # yfinance: percentage (e.g. 17.22)
        de_ratio = (de_raw / 100) if de_raw and de_raw > 5 else de_raw  # Convert to ratio

        # Interest coverage
        interest_exp = _inc_val(["Interest Expense"])
        ebit = _inc_val(["EBIT", "Operating Income"])
        int_coverage = None
        if ebit is not None and interest_exp and abs(interest_exp) > 0:
            int_coverage = abs(ebit / interest_exp)

        # Debt to assets
        total_debt = info.get("totalDebt") or _bs_val(["Total Debt", "Long Term Debt"])
        total_assets = _bs_val(["Total Assets"])
        debt_to_assets = None
        if total_debt is not None and total_assets and total_assets > 0:
            debt_to_assets = total_debt / total_assets

        # LT debt to capitalization
        lt_debt = _bs_val(["Long Term Debt"])
        total_equity = _bs_val(["Total Stockholders Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"])
        lt_debt_cap = None
        if lt_debt is not None and total_equity is not None:
            cap = lt_debt + total_equity
            if cap > 0:
                lt_debt_cap = lt_debt / cap

        # Altman Z-Score = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MktCap/TL) + 1.0*(Rev/TA)
        altman_z = None
        try:
            wc = _bs_val(["Working Capital"])
            if wc is None:
                ca = _bs_val(["Current Assets", "Total Current Assets"])
                cl = curr_liab
                if ca is not None and cl is not None:
                    wc = ca - cl
            re = _bs_val(["Retained Earnings"])
            mkt_cap = info.get("marketCap")
            total_liab = _bs_val(["Total Liabilities Net Minority Interest", "Total Liab"])
            tot_rev = info.get("totalRevenue")
            if total_assets and total_assets > 0 and all(v is not None for v in [wc, re, ebit, mkt_cap, total_liab, tot_rev]):
                ta = total_assets
                altman_z = (1.2 * (wc / ta) + 1.4 * (re / ta) + 3.3 * (ebit / ta)
                           + 0.6 * (mkt_cap / total_liab if total_liab > 0 else 0) + 1.0 * (tot_rev / ta))
        except Exception:
            pass

        # Score leverage (lower debt = higher score)
        de_s = _score_tiered(1 - (de_ratio if de_ratio is not None else 1), [(0.8, 5), (0.6, 4), (0.4, 3), (0, 2)]) if de_ratio is not None else 0
        if de_ratio is not None and de_ratio <= 0.1:
            de_s = 5
        elif de_ratio is not None and de_ratio <= 0.3:
            de_s = 4
        elif de_ratio is not None and de_ratio <= 0.5:
            de_s = 3
        elif de_ratio is not None and de_ratio <= 1.0:
            de_s = 2
        elif de_ratio is not None and de_ratio <= 2.0:
            de_s = 1
        else:
            de_s = 0

        ic_s = _score_tiered(int_coverage, [(10, 5), (5, 4), (3, 3), (1.5, 2), (1, 1)])
        da_s = 0
        if debt_to_assets is not None:
            if debt_to_assets <= 0.1: da_s = 5
            elif debt_to_assets <= 0.2: da_s = 4
            elif debt_to_assets <= 0.3: da_s = 3
            elif debt_to_assets <= 0.5: da_s = 2
            elif debt_to_assets <= 0.7: da_s = 1

        ldc_s = 0
        if lt_debt_cap is not None:
            if lt_debt_cap <= 0.1: ldc_s = 5
            elif lt_debt_cap <= 0.2: ldc_s = 4
            elif lt_debt_cap <= 0.3: ldc_s = 3
            elif lt_debt_cap <= 0.5: ldc_s = 2
            elif lt_debt_cap <= 0.7: ldc_s = 1

        az_s = _score_tiered(altman_z, [(3, 5), (2.5, 4), (1.8, 3), (1.2, 2), (0.5, 1)])

        leverage = de_s + ic_s + da_s + ldc_s + az_s
        score += leverage
        breakdown["leverage"] = {"total": leverage, "max": 25,
            "debt_equity": de_s, "interest_coverage": ic_s, "debt_assets": da_s,
            "lt_debt_cap": ldc_s, "altman_z": az_s}

        # ── Efficiency 15/15 ──
        tot_rev = info.get("totalRevenue")
        asset_turnover = None
        if tot_rev and total_assets and total_assets > 0:
            asset_turnover = tot_rev / total_assets

        inventory = _bs_val(["Inventory"])
        cogs = abs(_inc_val(["Cost Of Revenue"]) or 0)
        inv_turnover = None
        if cogs and inventory and inventory > 0:
            inv_turnover = cogs / inventory

        ar = _bs_val(["Accounts Receivable", "Net Receivables"])
        recv_turnover = None
        if tot_rev and ar and ar > 0:
            recv_turnover = tot_rev / ar

        at_s = _score_tiered(asset_turnover, [(2, 5), (1.5, 4), (1, 3), (0.5, 2), (0.2, 1)])
        it_s = _score_tiered(inv_turnover, [(8, 5), (5, 4), (4, 3), (2, 2), (1, 1)])
        rt_s = _score_tiered(recv_turnover, [(8, 5), (5, 4), (4, 3), (2, 2), (1, 1)])

        efficiency = at_s + it_s + rt_s
        score += efficiency
        breakdown["efficiency"] = {"total": efficiency, "max": 15,
            "asset_turnover": at_s, "inventory_turnover": it_s, "receivables_turnover": rt_s}

        # ── Growth 10/10 ──
        eps_growth = info.get("earningsGrowth")
        if eps_growth is None:
            eps_series = _safe_get(inc, ["Basic EPS", "Diluted EPS"])
            if eps_series is not None and len(eps_series) >= 4:
                old = float(eps_series.iloc[min(4, len(eps_series)-1)])
                if old > 0:
                    eps_growth = (float(eps_series.iloc[0]) / old) - 1

        # CAGR (stock price 5-year)
        cagr_val = None
        try:
            hist_5y = yf.Ticker(ticker).history(period="5y", interval="1mo")
            if hist_5y is not None and len(hist_5y) >= 12:
                p_now = float(hist_5y["Close"].iloc[-1])
                p_then = float(hist_5y["Close"].iloc[0])
                n_years = len(hist_5y) / 12
                if p_then > 0 and n_years > 0:
                    cagr_val = (pow(p_now / p_then, 1 / n_years) - 1) * 100  # as pct
        except Exception:
            pass

        epsg_s = 0
        if eps_growth is not None:
            epsg_pct = eps_growth * 100 if abs(eps_growth) < 10 else eps_growth
            epsg_s = _score_tiered(epsg_pct, [(30, 5), (15, 4), (5, 3), (0.01, 2)])

        cagr_s = _score_tiered(cagr_val, [(25, 5), (15, 4), (8, 3), (3, 2), (0.01, 1)])

        growth = epsg_s + cagr_s
        score += growth
        breakdown["growth"] = {"total": growth, "max": 10,
            "eps_growth": epsg_s, "cagr": cagr_s}

        # ── Valuation 10/10 ──
        pe = info.get("trailingPE")
        pb = info.get("priceToBook")

        # Lower P/E is better for value
        pe_s = 0
        if pe is not None and pe > 0:
            if pe <= 10: pe_s = 5
            elif pe <= 15: pe_s = 4
            elif pe <= 20: pe_s = 3
            elif pe <= 30: pe_s = 2
            elif pe <= 50: pe_s = 1

        pb_s = 0
        if pb is not None and pb > 0:
            if pb <= 1: pb_s = 5
            elif pb <= 2: pb_s = 4
            elif pb <= 3: pb_s = 3
            elif pb <= 5: pb_s = 2
            elif pb <= 10: pb_s = 1

        valuation = pe_s + pb_s
        score += valuation
        breakdown["valuation"] = {"total": valuation, "max": 10,
            "pe_ratio": pe_s, "pb_ratio": pb_s}

        return max(0, min(100, score))
    except Exception as exc:
        print(f"[info_data] get_score({ticker}): {exc}")
        return 50


def get_score_breakdown(ticker: str) -> Dict[str, Any]:
    """Return score with full category breakdown for display."""
    try:
        info = _yf_get(ticker, "info")
        _qbs = _yf_get(ticker, "quarterly_balance_sheet")
        bs = _qbs if _qbs is not None and not _qbs.empty else (_yf_get(ticker, "balance_sheet") or pd.DataFrame())
        _qcf = _yf_get(ticker, "quarterly_cashflow")
        cf = _qcf if _qcf is not None and not _qcf.empty else (_yf_get(ticker, "cashflow") or pd.DataFrame())
        _qfin = _yf_get(ticker, "quarterly_financials")
        inc = _qfin if _qfin is not None and not _qfin.empty else (_yf_get(ticker, "financials") or pd.DataFrame())

        def _bs_val(keys):
            s = _safe_get(bs, keys)
            return float(s.iloc[0]) if s is not None and len(s) > 0 else None

        def _cf_val(keys):
            s = _safe_get(cf, keys)
            return float(s.iloc[0]) if s is not None and len(s) > 0 else None

        def _inc_val(keys):
            s = _safe_get(inc, keys)
            return float(s.iloc[0]) if s is not None and len(s) > 0 else None

        # Compute all raw values for display
        raw = {
            "gross_margin": f"{info.get('grossMargins', 0)*100:.0f}%" if info.get('grossMargins') else "N/A",
            "profit_margin": f"{info.get('profitMargins', 0)*100:.0f}%" if info.get('profitMargins') else "N/A",
            "roe": f"{info.get('returnOnEquity', 0)*100:.0f}%" if info.get('returnOnEquity') else "N/A",
            "roa": f"{info.get('returnOnAssets', 0)*100:.0f}%" if info.get('returnOnAssets') else "N/A",
            "current_ratio": f"{info.get('currentRatio', 0):.2f}" if info.get('currentRatio') else "N/A",
            "quick_ratio": f"{info.get('quickRatio', 0):.2f}" if info.get('quickRatio') else "N/A",
        }
        return {"score": get_score(ticker), "raw": raw}
    except Exception:
        return {"score": 50, "raw": {}}
