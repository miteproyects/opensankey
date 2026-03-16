"""
Data fetching module for the Open Sankey company info/profile page.

Uses SEC EDGAR XBRL CompanyFacts API for all financial data instead of Yahoo Finance.
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
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import warnings
import re
import requests

warnings.filterwarnings("ignore")

# SEC EDGAR headers for API requests
_SEC_HEADERS = {
    "User-Agent": "OpenSankey contact@opensankey.com",
    "Accept-Encoding": "gzip, deflate",
}

# XBRL tag mappings for income statement
_XBRL_INCOME_TAGS = {
    "Total Revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "Cost Of Revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
    ],
    "Gross Profit": ["GrossProfit"],
    "Operating Income": ["OperatingIncomeLoss"],
    "Interest Expense": ["InterestExpense", "InterestExpenseDebt"],
    "Net Income": ["NetIncomeLoss", "ProfitLoss"],
    "EPS": ["EarningsPerShareBasic", "EarningsPerShareDiluted"],
}

# XBRL tag mappings for balance sheet
_XBRL_BALANCE_TAGS = {
    "Total Assets": ["Assets"],
    "Current Assets": ["AssetsCurrent"],
    "Cash And Cash Equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    "Accounts Receivable": ["AccountsReceivableNetCurrent"],
    "Inventory": ["InventoryNet"],
    "Net PPE": ["PropertyPlantAndEquipmentNet"],
    "Goodwill": ["Goodwill"],
    "Total Liabilities": ["Liabilities"],
    "Current Liabilities": ["LiabilitiesCurrent"],
    "Accounts Payable": ["AccountsPayableCurrent"],
    "Current Debt": ["DebtCurrent", "ShortTermBorrowings"],
    "Long Term Debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "Stockholders Equity": ["StockholdersEquity"],
}

# XBRL tag mappings for cash flow
_XBRL_CASHFLOW_TAGS = {
    "Operating Cash Flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "Capital Expenditure": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "Free Cash Flow": ["FreeCashFlow"],
}


@st.cache_data(ttl=3600, show_spinner=False)
def _ticker_to_cik(ticker: str) -> Optional[str]:
    """Convert stock ticker to SEC CIK number (zero-padded to 10 digits)."""
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=_SEC_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                return str(entry["cik_str"]).zfill(10)
    except Exception as e:
        print(f"[info_data] _ticker_to_cik error: {e}")
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_edgar_facts(cik: str) -> Optional[dict]:
    """Fetch CompanyFacts JSON from SEC EDGAR."""
    try:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        resp = requests.get(url, headers=_SEC_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[info_data] _fetch_edgar_facts error: {e}")
    return None


def _get_xbrl_value(facts: dict, tag_list: list, form_type: str = "10-K",
                     unit: str = "USD") -> Optional[float]:
    """Extract a single XBRL value from CompanyFacts for the most recent filing.

    Tries ALL tags and picks the one with the most recent end date (handles
    XBRL tag transitions like Revenues → RevenueFromContract…).

    Parameters:
    - facts: Full CompanyFacts JSON dict
    - tag_list: List of XBRL tags to try
    - form_type: "10-K" for annual, "10-Q" for quarterly
    - unit: "USD" for dollar amounts, "shares" for share counts,
            "pure" for ratios (EPS)

    Returns the most recent value or None.
    """
    gaap = facts.get("facts", {}).get("us-gaap", {})

    best_val = None
    best_end = ""

    for tag in tag_list:
        concept = gaap.get(tag, {})
        # Try the requested unit, also check USD/shares for EPS
        entries = concept.get("units", {}).get(unit, [])
        if not entries and unit == "USD":
            entries = concept.get("units", {}).get("USD/shares", [])

        for entry in entries:
            form = entry.get("form", "")
            fp = entry.get("fp", "")
            end = entry.get("end", "")
            val = entry.get("val")
            filed = entry.get("filed", "")
            if val is None or not end:
                continue
            if form != form_type:
                continue
            if form_type == "10-K" and fp != "FY":
                continue
            # Keep the entry with the most recent end date; break ties by filed
            if end > best_end or (end == best_end and filed > (best_val or ("", ""))[1] if isinstance(best_val, tuple) else ""):
                best_val = val
                best_end = end

    return float(best_val) if best_val is not None else None


def _get_xbrl_two_years(facts: dict, tag_list: list, form_type: str = "10-K",
                         unit: str = "USD") -> Tuple[Optional[float], Optional[float]]:
    """Get the two most recent annual values for a metric (current, previous).

    Returns (current_value, previous_value) tuple.
    """
    gaap = facts.get("facts", {}).get("us-gaap", {})

    # Collect all (end_date, filed_date, val) across all tags
    all_entries: Dict[str, Tuple[float, str]] = {}

    for tag in tag_list:
        concept = gaap.get(tag, {})
        entries = concept.get("units", {}).get(unit, [])
        if not entries and unit == "USD":
            entries = concept.get("units", {}).get("USD/shares", [])

        for entry in entries:
            form = entry.get("form", "")
            fp = entry.get("fp", "")
            end = entry.get("end", "")
            val = entry.get("val")
            filed = entry.get("filed", "")
            if val is None or not end:
                continue
            if form != form_type:
                continue
            if form_type == "10-K" and fp != "FY":
                continue
            if end not in all_entries or filed > all_entries[end][1]:
                all_entries[end] = (val, filed)

    if not all_entries:
        return None, None

    sorted_dates = sorted(all_entries.keys(), reverse=True)
    current = float(all_entries[sorted_dates[0]][0]) if len(sorted_dates) > 0 else None
    previous = float(all_entries[sorted_dates[1]][0]) if len(sorted_dates) > 1 else None
    return current, previous


def _get_company_name(facts: dict, ticker: str) -> str:
    """Extract company name from EDGAR facts."""
    try:
        entity_info = facts.get("entityName")
        if entity_info:
            return entity_info
    except Exception:
        pass
    return ticker.upper()


# ---------------------------------------------------------------------------
# Company Description
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_company_description(ticker: str) -> Dict[str, Any]:
    """Fetch comprehensive company profile information from SEC EDGAR.

    For data not available in EDGAR (price, website, logo), returns N/A defaults.

    Returns a dictionary with keys:
    - name: Company name
    - ticker: Stock ticker
    - price: N/A (real-time data not in EDGAR)
    - description: Company description (from EDGAR if available)
    - logo_url: N/A
    - sector: N/A (not in EDGAR)
    - industry: N/A (not in EDGAR)
    - country: Country from EDGAR
    - exchange: N/A
    - ceo: N/A
    - ipo_date: N/A
    - employees: N/A
    - website: N/A
    - cagr: N/A
    - div_yield: N/A
    - payout_ratio: N/A
    - market_cap: N/A
    """
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return _make_empty_company_description(ticker)

        facts = _fetch_edgar_facts(cik)
        if not facts:
            return _make_empty_company_description(ticker)

        name = _get_company_name(facts, ticker)

        return {
            "name": name,
            "ticker": ticker.upper(),
            "price": None,  # Real-time price not available from EDGAR
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
    except Exception as exc:
        print(f"[info_data] get_company_description({ticker}): {exc}")
        return _make_empty_company_description(ticker)


def _make_empty_company_description(ticker: str) -> Dict[str, Any]:
    """Return default company description when data unavailable."""
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
# Helpers
# ---------------------------------------------------------------------------

def _fmt_num(val: Optional[float], prefix: str = "", suffix: str = "", decimals: int = 2) -> str:
    """Format a number with B/M/K suffixes and optional prefix/suffix."""
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
    """Format a number as percentage."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    try:
        return f"{float(val) * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def _gc(value: Optional[float], is_growth: bool = False) -> str:
    """Color helper: green/red for growth, blue default."""
    if value is None:
        return "blue"
    if is_growth:
        return "green" if value > 0 else ("red" if value < 0 else "blue")
    return "blue"


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_fundamentals(ticker: str) -> List[List[Tuple[str, str, str]]]:
    """Fetch fundamental metrics from SEC EDGAR.

    Returns a list of rows, where each row contains 4 tuples.
    Each tuple is (label, value_str, color).

    For metrics not available from EDGAR, returns N/A.
    """
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return [[("N/A", "N/A", "blue")] * 4] * 10

        facts = _fetch_edgar_facts(cik)
        if not facts:
            return [[("N/A", "N/A", "blue")] * 4] * 10

        # ── Income statement (current + previous year for growth) ──
        rev_cur, rev_prev = _get_xbrl_two_years(facts, _XBRL_INCOME_TAGS["Total Revenue"])
        cogs = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Cost Of Revenue"])
        gp = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Gross Profit"])
        if not gp and rev_cur and cogs:
            gp = rev_cur - cogs
        oi = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Operating Income"])
        ni_cur, ni_prev = _get_xbrl_two_years(facts, _XBRL_INCOME_TAGS["Net Income"])
        interest = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Interest Expense"])
        eps = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["EPS"], unit="USD/shares")

        # ── Balance sheet ──
        tot_assets = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Total Assets"])
        cur_assets = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Assets"])
        cash = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Cash And Cash Equivalents"])
        inventory = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Inventory"])
        ar = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Accounts Receivable"])
        cur_liab = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Liabilities"])
        lt_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Long Term Debt"])
        equity = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Stockholders Equity"])
        tot_liab = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Total Liabilities"])
        total_debt = (lt_debt or 0) + (_get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Debt"]) or 0)

        # ── Margins & returns ──
        gm = (gp / rev_cur) if rev_cur and gp else None
        om = (oi / rev_cur) if rev_cur and oi else None
        pm = (ni_cur / rev_cur) if rev_cur and ni_cur else None
        roe = (ni_cur / equity) if equity and ni_cur and equity != 0 else None
        roa = (ni_cur / tot_assets) if tot_assets and ni_cur else None
        roce = (oi / (equity + (lt_debt or 0))) if oi and equity else None

        # ── Growth ──
        rev_growth = ((rev_cur / rev_prev) - 1) if rev_cur and rev_prev and rev_prev != 0 else None
        ni_growth = ((ni_cur / ni_prev) - 1) if ni_cur and ni_prev and ni_prev != 0 else None

        # ── Liquidity ──
        cr = (cur_assets / cur_liab) if cur_assets and cur_liab and cur_liab != 0 else None
        qr = ((cur_assets - (inventory or 0)) / cur_liab) if cur_assets and cur_liab and cur_liab != 0 else None
        cash_ratio = (cash / cur_liab) if cash and cur_liab and cur_liab != 0 else None

        # ── Leverage ──
        de = (total_debt / equity) if equity and equity != 0 else None
        da = (total_debt / tot_assets) if tot_assets and tot_assets != 0 else None
        lt_de = ((lt_debt or 0) / equity) if equity and equity != 0 and lt_debt else None
        lt_cap = ((lt_debt or 0) / ((lt_debt or 0) + equity)) if equity and lt_debt else None
        int_cov = (oi / interest) if oi and interest and interest != 0 else None

        # ── Efficiency / turnover ──
        at = (rev_cur / tot_assets) if rev_cur and tot_assets and tot_assets != 0 else None
        inv_to = (cogs / inventory) if cogs and inventory and inventory != 0 else None
        rec_to = (rev_cur / ar) if rev_cur and ar and ar != 0 else None

        def _r2(v):
            return f"{v:.2f}" if v is not None else "N/A"

        # ── Build rows ──
        rows = [
            [("EV", "N/A", "blue"),
             ("P/E", "N/A", "blue"),
             ("Forward P/E", "N/A", "blue"),
             ("PEG", "N/A", "blue")],

            [("P/S", "N/A", "blue"),
             ("P/B", "N/A", "blue"),
             ("P/CF", "N/A", "blue"),
             ("P/FCF", "N/A", "blue")],

            [("Revenue", _fmt_num(rev_cur, prefix="$"), "blue"),
             ("Rev Growth", _pct_str(rev_growth), _gc(rev_growth, True)),
             ("Net Income", _fmt_num(ni_cur, prefix="$"), _gc(ni_cur, True)),
             ("NI Growth", _pct_str(ni_growth), _gc(ni_growth, True))],

            [("EPS", f"${eps:.2f}" if eps is not None else "N/A", "blue"),
             ("Interest Exp", _fmt_num(interest, prefix="$"), "blue"),
             ("COGS", _fmt_num(cogs, prefix="$"), "blue"),
             ("Gross Profit", _fmt_num(gp, prefix="$"), "blue")],

            [("Tot Assets", _fmt_num(tot_assets, prefix="$"), "blue"),
             ("Tot Liabilities", _fmt_num(tot_liab, prefix="$"), "blue"),
             ("Equity", _fmt_num(equity, prefix="$"), "blue"),
             ("LT Debt", _fmt_num(lt_debt, prefix="$"), "blue")],

            [("Gross Margin", _pct_str(gm), _gc(gm)),
             ("Op. Margin", _pct_str(om), _gc(om)),
             ("Profit Margin", _pct_str(pm), _gc(pm)),
             ("ROCE", _pct_str(roce), _gc(roce))],

            [("ROA", _pct_str(roa), _gc(roa)),
             ("ROE", _pct_str(roe), _gc(roe)),
             ("Asset TO", _r2(at), "blue"),
             ("Recv. TO", _r2(rec_to), "blue")],

            [("Current Ratio", _r2(cr), "blue"),
             ("Quick Ratio", _r2(qr), "blue"),
             ("Cash Ratio", _r2(cash_ratio), "blue"),
             ("Inv. TO", _r2(inv_to), "blue")],

            [("Debt/Equity", _r2(de), "blue"),
             ("Debt/Assets", _r2(da), "blue"),
             ("Lt Debt/Eq", _r2(lt_de), "blue"),
             ("Lt Debt/Cap", _pct_str(lt_cap), "blue")],

            [("Interest Cov.", _r2(int_cov), "blue"),
             ("Cash", _fmt_num(cash, prefix="$"), "blue"),
             ("Op. Income", _fmt_num(oi, prefix="$"), _gc(oi, True)),
             ("Revenue", _fmt_num(rev_cur, prefix="$"), "blue")],
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
    """Fetch technical metrics (price, volume, moving averages).

    Returns a list of 3 rows, where each row contains 4 tuples.
    Each tuple is (label, value_str, color).

    Note: Real-time price, volume, and moving averages are not available from EDGAR.
    Returns N/A for all technical metrics.
    """
    try:
        rows = [
            # Row 1: Price, One Day Var., Short Interest, Beta
            [
                ("Price", "N/A", "blue"),
                ("1D Change", "N/A", "blue"),
                ("Short Int.", "N/A", "blue"),
                ("Beta", "N/A", "blue"),
            ],
            # Row 2: Day Low, Day High, Year Low, Year High
            [
                ("Day Low", "N/A", "blue"),
                ("Day High", "N/A", "blue"),
                ("52w Low", "N/A", "blue"),
                ("52w High", "N/A", "blue"),
            ],
            # Row 3: Volume, Avg Volume, Avg 50, Avg 200
            [
                ("Volume", "N/A", "blue"),
                ("Avg Vol", "N/A", "blue"),
                ("Avg 50d", "N/A", "blue"),
                ("Avg 200d", "N/A", "blue"),
            ],
        ]
        return rows
    except Exception as exc:
        print(f"[info_data] get_technicals({ticker}): {exc}")
        return [[("N/A", "N/A", "blue")] * 4] * 3


# ---------------------------------------------------------------------------
# DCF Data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_dcf_data(ticker: str) -> Dict[str, Any]:
    """Fetch inputs for DCF valuation model from SEC EDGAR.

    Returns dict with: current_fcf, wacc, fcf_growth_rates, terminal_growth_rate,
    discount_rate, shares_outstanding, net_debt.

    When EDGAR data is unavailable, returns sensible defaults.
    """
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return _get_dcf_defaults()

        facts = _fetch_edgar_facts(cik)
        if not facts:
            return _get_dcf_defaults()

        # ── Cash flow data ──
        ocf = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Operating Cash Flow"])
        capex = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Capital Expenditure"])
        fcf_direct = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Free Cash Flow"])

        # FCF = OCF - CapEx (CapEx is reported as positive payments)
        if fcf_direct:
            current_fcf = fcf_direct
        elif ocf and capex:
            current_fcf = ocf - capex
        elif ocf:
            current_fcf = ocf * 0.8  # rough estimate
        else:
            ni = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Net Income"])
            current_fcf = ni * 0.9 if ni else 0

        # ── Shares outstanding ──
        shares = _get_xbrl_value(facts,
            ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding",
             "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
             "WeightedAverageNumberOfDilutedSharesOutstanding"],
            unit="shares")

        # ── Net debt ──
        lt_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Long Term Debt"]) or 0
        cur_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Debt"]) or 0
        cash = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Cash And Cash Equivalents"]) or 0
        net_debt = lt_debt + cur_debt - cash

        return {
            "current_fcf": current_fcf or 0,
            "base_growth_rate": 0.08,
            "terminal_growth_rate": 0.03,
            "discount_rate": 0.10,
            "wacc": 0.10,
            "fcf_growth_rates": [0.08, 0.07, 0.06, 0.05, 0.04],
            "shares_outstanding": shares or 1,
            "net_debt": net_debt,
            "risk_free_rate": 0.04,
        }
    except Exception as exc:
        print(f"[info_data] get_dcf_data({ticker}): {exc}")
        return _get_dcf_defaults()


def _get_dcf_defaults() -> Dict[str, Any]:
    """Return default DCF data when unavailable."""
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
    """Fetch ownership structure (not available from EDGAR).

    Returns a dictionary with keys:
    - institutional_holders: Empty list (not in EDGAR)
    - insider_pct: N/A
    - institutional_pct: N/A
    - public_pct: N/A
    """
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
    """Fetch insider trading activity (not available from EDGAR).

    Returns a dictionary with keys:
    - recent_trades: Empty list
    - monthly_activity: Empty list
    """
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
def get_score(ticker: str) -> int:
    """Calculate financial health score (0-100) from SEC EDGAR data.

    When EDGAR data is unavailable, returns 50 (neutral score).
    """
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return 50

        facts = _fetch_edgar_facts(cik)
        if not facts:
            return 50

        # Get key metrics from EDGAR
        revenue = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Total Revenue"])
        gross_profit = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Gross Profit"])
        operating_income = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Operating Income"])
        net_income = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Net Income"])

        total_assets = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Total Assets"])
        current_assets = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Assets"])
        current_liab = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Liabilities"])
        equity = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Stockholders Equity"])
        total_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Long Term Debt"])

        score = 0

        # Profitability (20 pts max)
        if revenue:
            if gross_profit:
                gm = gross_profit / revenue
                score += 5 if gm > 0.4 else (3 if gm > 0.2 else 1)
            if operating_income:
                om = operating_income / revenue
                score += 5 if om > 0.2 else (3 if om > 0.1 else 1)
            if net_income:
                pm = net_income / revenue
                score += 5 if pm > 0.1 else (3 if pm > 0.05 else 1)

        if equity and net_income:
            roe = net_income / equity
            score += 5 if roe > 0.15 else (3 if roe > 0.1 else 1)

        # Liquidity (20 pts max)
        if current_assets and current_liab:
            cr = current_assets / current_liab
            score += 5 if cr > 2 else (3 if cr > 1.5 else 1)

        # Leverage (15 pts max)
        if total_assets and total_debt:
            da = total_debt / total_assets
            score += 5 if da < 0.3 else (3 if da < 0.5 else 1)

        if equity and total_debt:
            de = total_debt / equity
            score += 5 if de < 0.5 else (3 if de < 1.0 else 1)

        # Asset efficiency (10 pts max)
        if revenue and total_assets:
            at = revenue / total_assets
            score += 5 if at > 1.5 else (3 if at > 1 else 1)

        return min(100, score)
    except Exception as exc:
        print(f"[info_data] get_score({ticker}): {exc}")
        return 50


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

    return "📊"
