"""
Data fetching module for the Quarter Charts company info/profile page.

Uses SEC EDGAR XBRL CompanyFacts API for financial-statement data (income,
balance sheet, cash flow) and Yahoo Finance for market/price data (quote,
technicals, ownership, insider trades, company metadata).

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
import yfinance as yf

warnings.filterwarnings("ignore")

# SEC EDGAR headers for API requests
_SEC_HEADERS = {
    "User-Agent": "QuarterCharts contact@quartercharts.com",
    "Accept-Encoding": "gzip, deflate",
}

# ---------------------------------------------------------------------------
# Sector classification (SIC code → sector) — Task #31
# ---------------------------------------------------------------------------
# SEC's Standard Industrial Classification codes map filers to high-level
# sectors. We key on just 3 sectors where us-gaap tag expectations diverge
# meaningfully from the generic Industrial/Tech pattern:
#
#   banks     — report NetInterestIncome / ProvisionForLoanLosses /
#               NoninterestIncome instead of CostOfRevenue / GrossProfit.
#   insurers  — report PremiumsEarnedNet / InsuranceLossesAndLossAdjustment
#               / BenefitsLossesAndExpenses.
#   energy    — report OilAndGasPropertyFullCostMethod* on the balance
#               sheet; also often skip CostOfRevenue and fold everything
#               into a single "Total Costs and Expenses" line.
#
# Everything else is "general" — the existing _SEC_*_MAP handles them.
#
# SIC code ranges (SEC list):
#   6020–6199  Depository Institutions & Commercial Banks
#   6310–6411  Life Insurance, Hospital & Medical, Fire/Marine/Casualty
#   1311       Crude Petroleum & Natural Gas (upstream)
#   2911       Petroleum Refining
#
# Adding more sectors later is just one `((lo, hi), "name")` tuple plus a
# matching supplement in `data_fetcher._SECTOR_FIELD_MAP`.

_SIC_SECTOR_RANGES = [
    ((6020, 6199), "bank"),
    ((6310, 6411), "insurer"),
    ((1311, 1311), "energy"),
    ((2911, 2911), "energy"),
]


@st.cache_data(ttl=86400, show_spinner=False)
def _sec_fetch_submission_meta(ticker: str) -> Optional[dict]:
    """Fetch `submissions/CIK{n}.json` for a ticker.

    Cached for 24h because SIC codes almost never change. Returns None on
    any failure so callers can fall back to "general" sector.
    """
    # Lazy import to avoid a circular dependency with data_fetcher, which
    # imports `get_sic_sector` from this module inside `_augment_field_map`.
    from data_fetcher import _sec_get_cik
    cik = _sec_get_cik(ticker)
    if cik is None:
        return None
    cik_padded = str(cik).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    try:
        resp = requests.get(url, timeout=10, headers=_SEC_HEADERS)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def get_sic_sector(ticker: str) -> str:
    """Return one of {"bank", "insurer", "energy", "general"} for *ticker*.

    Reads the SIC code from SEC's submissions endpoint (cached). Tickers
    whose SIC is unknown or outside the ranges above fall through to
    "general", which means the existing `_SEC_*_MAP` fields are used
    unchanged. Never raises — returns "general" on any error.
    """
    meta = _sec_fetch_submission_meta(ticker)
    if not meta:
        return "general"
    try:
        sic = int(meta.get("sic") or 0)
    except (TypeError, ValueError):
        return "general"
    for (lo, hi), sector in _SIC_SECTOR_RANGES:
        if lo <= sic <= hi:
            return sector
    return "general"


def is_turnover_applicable(sector: str) -> bool:
    """Return True iff DSO/DPO/DIO turnover metrics make sense for *sector*.

    Banks and insurers don't have meaningful receivables / payables /
    inventory in the traditional sense — their "working capital" is loans,
    premiums, and reserves, not merchandise flow. Rendering DSO/DPO/DIO
    for them would be misleading.
    """
    return sector not in {"bank", "insurer"}


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
    "Total Liabilities": ["Liabilities", "LiabilitiesNoncurrent"],
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
# Yahoo Finance helper (market/price data only)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _yf_info(ticker: str) -> dict:
    """Fetch the Yahoo Finance .info dict (cached 1 h). Returns {} on failure."""
    try:
        return dict(yf.Ticker(ticker).info or {})
    except Exception as e:
        print(f"[info_data] _yf_info({ticker}): {e}")
        return {}


# ---------------------------------------------------------------------------
# Company Description
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_company_description(ticker: str) -> Dict[str, Any]:
    """Fetch company profile merging EDGAR (name) + Yahoo Finance (market data).

    Returns a dictionary with keys matching the profile page expectations.
    """
    try:
        # EDGAR for company name
        cik = _ticker_to_cik(ticker)
        facts = _fetch_edgar_facts(cik) if cik else None
        name = _get_company_name(facts, ticker) if facts else ticker.upper()

        # Yahoo Finance for market / metadata
        info = _yf_info(ticker)

        # 5-year price CAGR
        cagr = None
        try:
            h5 = yf.Ticker(ticker).history(period="5y", interval="1mo")
            if h5 is not None and len(h5) >= 12:
                cagr = (pow(float(h5["Close"].iloc[-1]) / float(h5["Close"].iloc[0]),
                            1 / (len(h5) / 12)) - 1)
        except Exception:
            pass

        return {
            "name": name,
            "ticker": ticker.upper(),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "description": info.get("longBusinessSummary", ""),
            "logo_url": info.get("logo_url", ""),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "ceo": _extract_ceo(info),
            "ipo_date": info.get("ipoDate", "N/A") or "N/A",
            "employees": info.get("fullTimeEmployees"),
            "website": info.get("website", "N/A") or "N/A",
            "cagr": cagr,
            "div_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "market_cap": info.get("marketCap"),
        }
    except Exception as exc:
        print(f"[info_data] get_company_description({ticker}): {exc}")
        return _make_empty_company_description(ticker)


def _extract_ceo(info: dict) -> str:
    """Try to pull the CEO name from YF companyOfficers."""
    try:
        officers = info.get("companyOfficers", [])
        for o in officers:
            title = (o.get("title") or "").lower()
            if "ceo" in title or "chief executive" in title:
                return o.get("name", "N/A")
    except Exception:
        pass
    return "N/A"


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
        if tot_liab is None and tot_assets and equity:
            tot_liab = tot_assets - equity  # Assets = Liabilities + Equity
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

        # ── Valuation multiples from Yahoo Finance ──
        info = _yf_info(ticker)
        ev = info.get("enterpriseValue")
        pe = info.get("trailingPE")
        fpe = info.get("forwardPE")
        peg = info.get("pegRatio")
        ps = info.get("priceToSalesTrailing12Months")
        pb = info.get("priceToBook")
        pcf = None
        pfcf = None
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        ocf_yf = info.get("operatingCashflow")
        shares_yf = info.get("sharesOutstanding")
        if price and ocf_yf and shares_yf and shares_yf > 0:
            pcf = price / (ocf_yf / shares_yf)
        fcf_yf = info.get("freeCashflow")
        if price and fcf_yf and shares_yf and shares_yf > 0 and fcf_yf > 0:
            pfcf = price / (fcf_yf / shares_yf)

        # ── Build rows ──
        rows = [
            [("EV", _fmt_num(ev, prefix="$"), "blue"),
             ("P/E", _r2(pe), "blue"),
             ("Forward P/E", _r2(fpe), "blue"),
             ("PEG", _r2(peg), "blue")],

            [("P/S", _r2(ps), "blue"),
             ("P/B", _r2(pb), "blue"),
             ("P/CF", _r2(pcf), "blue"),
             ("P/FCF", _r2(pfcf), "blue")],

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
    """Fetch technical / market metrics from Yahoo Finance.

    Returns a list of 3 rows, where each row contains 4 tuples (label, value_str, color).
    """
    try:
        info = _yf_info(ticker)
        if not info:
            raise ValueError("No YF data")

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change = ((price - prev) if price and prev else None)
        change_pct = (change / prev * 100) if change is not None and prev else None
        change_str = f"{change:+.2f} ({change_pct:+.2f}%)" if change is not None else "N/A"
        change_color = "green" if (change or 0) >= 0 else "red"

        def _p(v, pre="$"):
            return f"{pre}{v:,.2f}" if v else "N/A"

        rows = [
            [
                ("Price", _p(price), "blue"),
                ("1D Change", change_str, change_color),
                ("Short Int.", _fmt_num(info.get("sharesShort")), "blue"),
                ("Beta", f"{info['beta']:.2f}" if info.get("beta") else "N/A", "blue"),
            ],
            [
                ("Day Low", _p(info.get("dayLow")), "blue"),
                ("Day High", _p(info.get("dayHigh")), "blue"),
                ("52w Low", _p(info.get("fiftyTwoWeekLow")), "blue"),
                ("52w High", _p(info.get("fiftyTwoWeekHigh")), "blue"),
            ],
            [
                ("Volume", _fmt_num(info.get("volume")), "blue"),
                ("Avg Vol", _fmt_num(info.get("averageVolume")), "blue"),
                ("Avg 50d", _p(info.get("fiftyDayAverage")), "blue"),
                ("Avg 200d", _p(info.get("twoHundredDayAverage")), "blue"),
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
    """Fetch inputs for DCF valuation model from EDGAR + Yahoo Finance.

    Uses YF freeCashflow (more reliable) with EDGAR as fallback.
    Estimates WACC from beta when available.

    Returns dict with: current_fcf, wacc, fcf_growth_rates, terminal_growth_rate,
    discount_rate, shares_outstanding, net_debt.
    """
    try:
        # ── Yahoo Finance data (preferred for FCF, shares, beta) ──
        info = _yf_info(ticker)

        # FCF: prefer YF (accounts for all capex properly)
        current_fcf = info.get("freeCashflow")

        # Fallback to EDGAR if YF FCF unavailable
        if not current_fcf:
            cik = _ticker_to_cik(ticker)
            facts = _fetch_edgar_facts(cik) if cik else None
            if facts:
                ocf = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Operating Cash Flow"])
                capex = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Capital Expenditure"])
                fcf_direct = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Free Cash Flow"])
                if fcf_direct:
                    current_fcf = fcf_direct
                elif ocf and capex:
                    current_fcf = ocf - capex
                elif ocf:
                    current_fcf = ocf * 0.8

        if not current_fcf or current_fcf <= 0:
            ni = info.get("netIncomeToCommon")
            current_fcf = ni * 0.85 if ni and ni > 0 else 0

        # Shares outstanding (YF is most current)
        shares = info.get("sharesOutstanding")
        if not shares:
            cik = _ticker_to_cik(ticker)
            facts = _fetch_edgar_facts(cik) if cik else None
            if facts:
                shares = _get_xbrl_value(facts,
                    ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding",
                     "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
                     "WeightedAverageNumberOfDilutedSharesOutstanding"],
                    unit="shares")

        # Net debt (YF preferred)
        total_debt_yf = info.get("totalDebt")
        total_cash_yf = info.get("totalCash")
        if total_debt_yf is not None and total_cash_yf is not None:
            net_debt = total_debt_yf - total_cash_yf
        else:
            # EDGAR fallback
            cik = _ticker_to_cik(ticker)
            facts = _fetch_edgar_facts(cik) if cik else None
            if facts:
                lt_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Long Term Debt"]) or 0
                cur_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Debt"]) or 0
                cash = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Cash And Cash Equivalents"]) or 0
                net_debt = lt_debt + cur_debt - cash
            else:
                net_debt = 0

        # Estimate WACC from beta (CAPM-based)
        beta = info.get("beta", 1.0) or 1.0
        risk_free = 0.04  # ~10Y Treasury
        equity_premium = 0.055  # long-run equity risk premium
        cost_of_equity = risk_free + beta * equity_premium
        # Blended WACC (assume ~30% debt at 5% cost, 70% equity)
        wacc = 0.70 * cost_of_equity + 0.30 * 0.05
        wacc = max(0.06, min(0.15, wacc))  # clamp 6-15%

        # Growth rates — use YF earnings growth as anchor if available
        eg = info.get("earningsGrowth")
        rg = info.get("revenueGrowth")
        base_growth = 0.06  # default
        if eg and abs(eg) < 2:
            base_growth = max(0.02, min(0.25, abs(eg)))
        elif rg and abs(rg) < 2:
            base_growth = max(0.02, min(0.20, abs(rg)))

        # Declining growth over 5 years
        growth_rates = [
            base_growth,
            base_growth * 0.85,
            base_growth * 0.70,
            base_growth * 0.60,
            base_growth * 0.50,
        ]

        terminal_growth = 0.025  # long-run GDP-ish

        return {
            "current_fcf": current_fcf or 0,
            "base_growth_rate": base_growth,
            "terminal_growth_rate": terminal_growth,
            "discount_rate": wacc,
            "wacc": wacc,
            "fcf_growth_rates": growth_rates,
            "shares_outstanding": shares or 1,
            "net_debt": net_debt,
            "risk_free_rate": risk_free,
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
    """Fetch ownership structure from Yahoo Finance.

    Returns a dictionary with keys:
    - institutional_holders: list of dicts
    - insider_pct: float
    - institutional_pct: float
    - public_pct: float
    """
    try:
        t = yf.Ticker(ticker)
        info = _yf_info(ticker)

        insider_pct = info.get("heldPercentInsiders", 0) or 0
        inst_pct = info.get("heldPercentInstitutions", 0) or 0
        public_pct = max(0, 1 - insider_pct - inst_pct)

        # Top institutional holders
        holders = []
        try:
            ih = t.institutional_holders
            if ih is not None and not ih.empty:
                for _, row in ih.head(10).iterrows():
                    holders.append({
                        "holder": row.get("Holder", "Unknown"),
                        "shares": row.get("Shares", 0),
                        "pct_out": row.get("% Out", 0),
                        "value": row.get("Value", 0),
                    })
        except Exception:
            pass

        return {
            "institutional_holders": holders,
            "insider_pct": insider_pct,
            "institutional_pct": inst_pct,
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
    """Fetch insider trading activity from Yahoo Finance.

    Returns a dictionary with keys:
    - recent_trades: list of dicts
    - monthly_activity: list of dicts
    """
    try:
        t = yf.Ticker(ticker)
        trades = []

        try:
            it = t.insider_transactions
            if it is not None and not it.empty:
                for _, row in it.head(20).iterrows():
                    trades.append({
                        "insider": row.get("Insider", "Unknown"),
                        "relation": row.get("Position", ""),
                        "date": str(row.get("Start Date", "")),
                        "transaction": row.get("Transaction", ""),
                        "shares": row.get("Shares", 0),
                        "value": row.get("Value", 0),
                    })
        except Exception:
            pass

        # Monthly buy/sell aggregation
        monthly = []
        try:
            ip = t.insider_purchases
            if ip is not None and not ip.empty:
                for _, row in ip.iterrows():
                    monthly.append({
                        "period": row.get("Period", ""),
                        "buys": row.get("Purchases", 0),
                        "sells": row.get("Sales", 0),
                        "shares_bought": row.get("Shares Purchased", 0),
                        "shares_sold": row.get("Shares Sold", 0),
                    })
        except Exception:
            pass

        return {
            "recent_trades": trades,
            "monthly_activity": monthly,
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
    """Calculate financial health score (0-100) using EDGAR + Yahoo Finance.

    Matches the detailed score_tab breakdown in profile_page.py:
      Profitability  20 pts  (Gross Margin, Profit Margin, ROE, ROA)
      Liquidity      20 pts  (Current, Quick, Cash, OCF ratios)
      Leverage       25 pts  (D/E, Interest Cov, D/A, LtD/Cap, Altman Z)
      Efficiency     15 pts  (Asset TO, Inventory TO, Receivables TO)
      Growth         10 pts  (EPS growth, Price CAGR)
      Valuation      10 pts  (P/E, P/B)
                    --------
                    100 pts
    """
    def _st(val, tiers):
        if val is None:
            return 0
        for threshold, pts in tiers:
            if val >= threshold:
                return pts
        return 0

    try:
        # ── EDGAR data ──
        cik = _ticker_to_cik(ticker)
        facts = _fetch_edgar_facts(cik) if cik else None
        if not facts:
            return 50

        rev = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Total Revenue"])
        gp = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Gross Profit"])
        cogs = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Cost Of Revenue"])
        if not gp and rev and cogs:
            gp = rev - cogs
        oi = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Operating Income"])
        ni = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Net Income"])
        interest = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Interest Expense"])

        ta = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Total Assets"])
        ca = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Assets"])
        cash = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Cash And Cash Equivalents"])
        inv = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Inventory"])
        ar = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Accounts Receivable"])
        cl = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Liabilities"])
        ltd = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Long Term Debt"])
        cur_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Debt"])
        teq = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Stockholders Equity"])
        tl = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Total Liabilities"])
        if tl is None and ta and teq:
            tl = ta - teq
        td = (ltd or 0) + (cur_debt or 0)

        ocf = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Operating Cash Flow"])

        ni_cur, ni_prev = _get_xbrl_two_years(facts, _XBRL_INCOME_TAGS["Net Income"])
        eps_cur, eps_prev = _get_xbrl_two_years(facts, _XBRL_INCOME_TAGS["EPS"], unit="USD/shares")

        # ── Yahoo Finance data ──
        info = _yf_info(ticker)

        # ── Profitability (20 pts) ──
        gm_pct = (gp / rev * 100) if rev and gp else 0
        pm_pct = (ni / rev * 100) if rev and ni else 0
        roe_pct = (ni / teq * 100) if teq and ni and teq != 0 else 0
        roa_pct = (ni / ta * 100) if ta and ni and ta != 0 else 0
        prof = (_st(gm_pct, [(60,5),(40,4),(20,3),(10,2),(0.01,1)])
              + _st(pm_pct, [(20,5),(10,4),(5,3),(0.01,2)])
              + _st(roe_pct, [(25,5),(15,4),(10,3),(5,2),(0.01,1)])
              + _st(roa_pct, [(15,5),(10,4),(5,3),(2,2),(0.01,1)]))

        # ── Liquidity (20 pts) ──
        cr = (ca / cl) if ca and cl and cl > 0 else None
        qr = ((ca - (inv or 0)) / cl) if ca and cl and cl > 0 else None
        cashr = (cash / cl) if cash is not None and cl and cl > 0 else None
        ocfr = (ocf / cl) if ocf is not None and cl and cl > 0 else None
        liq = (_st(cr, [(3,5),(2,4),(1.5,3),(1,2),(0.5,1)])
             + _st(qr, [(2,5),(1.5,4),(1,3),(0.5,2),(0.2,1)])
             + _st(cashr, [(1,5),(0.5,4),(0.3,3),(0.15,2),(0.05,1)])
             + _st(ocfr, [(1.5,5),(1,4),(0.5,3),(0.2,2),(0.05,1)]))

        # ── Leverage (25 pts) ──
        de_ratio = (td / teq) if teq and teq != 0 else None
        int_cov = abs(oi / interest) if oi and interest and abs(interest) > 0 else None
        da = (td / ta) if ta and ta > 0 else None
        ldc = (ltd / (ltd + teq)) if ltd is not None and teq is not None and (ltd + teq) > 0 else None
        wc = (ca - cl) if ca is not None and cl is not None else None
        mc = info.get("marketCap")
        re_val = _get_xbrl_value(facts, ["RetainedEarningsAccumulatedDeficit"], form_type="10-K")
        az = None
        if ta and ta > 0 and all(v is not None for v in [wc, re_val, oi, mc, tl, rev]):
            az = 1.2*(wc/ta) + 1.4*(re_val/ta) + 3.3*(oi/ta) + 0.6*(mc/tl if tl and tl > 0 else 0) + 1.0*(rev/ta)

        de_s = 0
        if de_ratio is not None:
            if de_ratio <= 0.1: de_s = 5
            elif de_ratio <= 0.3: de_s = 4
            elif de_ratio <= 0.5: de_s = 3
            elif de_ratio <= 1.0: de_s = 2
            elif de_ratio <= 2.0: de_s = 1
        da_s = 0
        if da is not None:
            if da <= 0.1: da_s = 5
            elif da <= 0.2: da_s = 4
            elif da <= 0.3: da_s = 3
            elif da <= 0.5: da_s = 2
            elif da <= 0.7: da_s = 1
        ldc_s = 0
        if ldc is not None:
            if ldc <= 0.1: ldc_s = 5
            elif ldc <= 0.2: ldc_s = 4
            elif ldc <= 0.3: ldc_s = 3
            elif ldc <= 0.5: ldc_s = 2
            elif ldc <= 0.7: ldc_s = 1
        lev = (de_s
             + _st(int_cov, [(10,5),(5,4),(3,3),(1.5,2),(1,1)])
             + da_s + ldc_s
             + _st(az, [(3,5),(2.5,4),(1.8,3),(1.2,2),(0.5,1)]))

        # ── Efficiency (15 pts) ──
        at = (rev / ta) if rev and ta and ta > 0 else None
        invt = (cogs / inv) if cogs and inv and inv > 0 else None
        rt = (rev / ar) if rev and ar and ar > 0 else None
        eff = (_st(at, [(2,5),(1.5,4),(1,3),(0.5,2),(0.2,1)])
             + _st(invt, [(8,5),(5,4),(4,3),(2,2),(1,1)])
             + _st(rt, [(8,5),(5,4),(4,3),(2,2),(1,1)]))

        # ── Growth (10 pts) ──
        epsg_pct = None
        if eps_cur is not None and eps_prev is not None and eps_prev != 0:
            epsg_pct = ((eps_cur / eps_prev) - 1) * 100
        elif ni_cur is not None and ni_prev is not None and ni_prev != 0:
            epsg_pct = ((ni_cur / ni_prev) - 1) * 100
        if epsg_pct is None:
            _eg = info.get("earningsGrowth")
            if _eg is not None:
                epsg_pct = _eg * 100 if abs(_eg) < 10 else _eg
        cagr_v = None
        try:
            h5 = yf.Ticker(ticker).history(period="5y", interval="1mo")
            if h5 is not None and len(h5) >= 12:
                cagr_v = (pow(float(h5["Close"].iloc[-1]) / float(h5["Close"].iloc[0]),
                              1 / (len(h5) / 12)) - 1) * 100
        except Exception:
            pass
        gro = (_st(epsg_pct, [(30,5),(15,4),(5,3),(0.01,2)])
             + _st(cagr_v, [(25,5),(15,4),(8,3),(3,2),(0.01,1)]))

        # ── Valuation (10 pts) ──
        pe = info.get("trailingPE")
        pb = info.get("priceToBook")
        pe_s = 0
        if pe and pe > 0:
            if pe <= 10: pe_s = 5
            elif pe <= 15: pe_s = 4
            elif pe <= 20: pe_s = 3
            elif pe <= 30: pe_s = 2
            elif pe <= 50: pe_s = 1
        pb_s = 0
        if pb and pb > 0:
            if pb <= 1: pb_s = 5
            elif pb <= 2: pb_s = 4
            elif pb <= 3: pb_s = 3
            elif pb <= 5: pb_s = 2
            elif pb <= 10: pb_s = 1
        val = pe_s + pb_s

        return min(100, prof + liq + lev + eff + gro + val)
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


# ---------------------------------------------------------------------------
# Key Metrics — Group A (derivable panels, Phase 1 of Task #36)
# ---------------------------------------------------------------------------
# Group A = everything that can be computed from SEC income + balance +
# cashflow + shares alone, without any price lookup. Phase 1 ships these
# panels; Phase 2 wires in the price-dependent ratios (P/S, P/B, etc.) on
# top of the same DataFrame.

def _pick_shares_series(income_df: pd.DataFrame) -> Optional[pd.Series]:
    """Return the best per-period shares series from an income DataFrame.

    Prefers diluted over basic. Returns ``None`` if neither column exists
    or is entirely empty, so callers can degrade gracefully.
    """
    for col in ("Diluted Average Shares", "Basic Average Shares"):
        if col in income_df.columns:
            s = pd.to_numeric(income_df[col], errors="coerce").replace(0, np.nan)
            if s.notna().sum() > 0:
                return s
    return None


def compute_key_metrics_group_a(
    income_df: pd.DataFrame,
    balance_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return a wide DataFrame with the Phase 1 Key Metrics columns.

    Columns produced (each may be absent if the underlying inputs are):
      - Shares YoY %               (from Diluted Shares pct_change(4))
      - BVPS                       (Stockholders Equity / Diluted Shares)
      - Cash/Share                 (Cash & Equivalents / Diluted Shares)
      - FCF/Share                  (Free CF / Diluted Shares)
      - ROE %                      (Net Income / Stockholders Equity × 100)
      - Graham Number              (√(22.5 × Diluted EPS × BVPS))

    The returned index is the union of rows present in `income_df`,
    `balance_df`, and `cashflow_df` that have a valid shares denominator.
    `Shares YoY %` uses a 4-period lag for quarterly frames; callers that
    pass annual frames will get yearly YoY for free.

    Never raises — missing inputs degrade to empty columns, empty frame
    on full failure.
    """
    if income_df is None or income_df.empty:
        return pd.DataFrame()

    shares = _pick_shares_series(income_df)
    if shares is None:
        return pd.DataFrame()

    out = pd.DataFrame(index=income_df.index)

    # Shares YoY % — 4-period lag is correct for quarterly; for annual
    # frames this reduces to a 4-year lag, so downstream annual callers
    # should re-use Shares YoY % on the quarterly frame, not the annual
    # one. Graceful fallback to 1-period diff if there's <4 rows.
    periods = 4 if len(shares) > 4 else 1
    out["Shares YoY %"] = (shares.pct_change(periods=periods) * 100).round(2)

    # BVPS — balance sheet equity aligned to income_df index.
    if not balance_df.empty and "Stockholders Equity" in balance_df.columns:
        eq = pd.to_numeric(balance_df["Stockholders Equity"], errors="coerce")
        eq_aligned = eq.reindex(out.index)
        bvps = (eq_aligned / shares).round(4)
        out["BVPS"] = bvps
    else:
        out["BVPS"] = np.nan

    # Cash/Share
    if not balance_df.empty and "Cash and Cash Equivalents" in balance_df.columns:
        cash = pd.to_numeric(balance_df["Cash and Cash Equivalents"], errors="coerce")
        out["Cash/Share"] = (cash.reindex(out.index) / shares).round(4)
    else:
        out["Cash/Share"] = np.nan

    # FCF/Share — Free CF is computed by get_cash_flow when both Operating
    # CF and CapEx are present. Tolerate its absence.
    if not cashflow_df.empty and "Free CF" in cashflow_df.columns:
        fcf = pd.to_numeric(cashflow_df["Free CF"], errors="coerce")
        out["FCF/Share"] = (fcf.reindex(out.index) / shares).round(4)
    else:
        out["FCF/Share"] = np.nan

    # ROE % — Net Income / Stockholders Equity × 100. We divide period
    # Net Income by period-end equity; a cleaner version would use
    # average-of-period equity, but that requires two-period alignment
    # and downstream charting tolerates the simpler form fine.
    if ("Net Income" in income_df.columns
            and not balance_df.empty
            and "Stockholders Equity" in balance_df.columns):
        ni = pd.to_numeric(income_df["Net Income"], errors="coerce")
        eq = pd.to_numeric(balance_df["Stockholders Equity"], errors="coerce").reindex(out.index)
        roe = (ni / eq.replace(0, np.nan) * 100).round(2)
        out["ROE %"] = roe
    else:
        out["ROE %"] = np.nan

    # Graham Number = √(22.5 × EPS × BVPS). Only defined for positive EPS
    # and positive BVPS; mask out the rest so the chart doesn't choke on
    # imaginary numbers.
    if "Diluted EPS" in income_df.columns and "BVPS" in out.columns:
        eps = pd.to_numeric(income_df["Diluted EPS"], errors="coerce")
        bv = out["BVPS"]
        prod = 22.5 * eps * bv
        graham = np.sqrt(prod.where(prod > 0))
        out["Graham Number"] = graham.round(2)
    else:
        out["Graham Number"] = np.nan

    return out


# ---------------------------------------------------------------------------
# Key Metrics — Group B (Phase 2 price-dependent panels, Task #36)
# ---------------------------------------------------------------------------
# Group B needs per-period market cap (closes × shares) to compute the
# "P/X" ratios and Dividend Yield. Dividend Yield uses TTM dividends as
# the numerator, period-end price as the denominator. Net Buyback Yield
# uses TTM (Stock Issued - Stock Repurchased) as the numerator, period-
# end market cap as the denominator.

def compute_net_buyback_yield_ttm(
    cashflow_df: pd.DataFrame,
    market_cap_series: pd.Series,
) -> pd.Series:
    """Return TTM Net Buyback Yield %, aligned to *market_cap_series*' index.

    Numerator : trailing-4-quarters sum of (Stock Issued − Stock Repurchased),
                sign-flipped so that NET buybacks come out positive. Stock
                Repurchased is reported as a positive outflow in cashflow
                statements (payments for repurchase), Stock Issued as a
                positive inflow.
    Denominator : `market_cap_series` (period-end market cap, shares × close).

    Sign convention: POSITIVE Net Buyback Yield = buybacks > issuance (net
    shrink). NEGATIVE = net dilution. Matches how GuruFocus/QuarterCharts
    render it.

    Returns empty Series on any missing input.
    """
    if cashflow_df is None or cashflow_df.empty or market_cap_series is None or market_cap_series.empty:
        return pd.Series(dtype=float)
    if "Stock Repurchased" not in cashflow_df.columns and "Stock Issued" not in cashflow_df.columns:
        return pd.Series(dtype=float)

    repurchased = pd.to_numeric(
        cashflow_df.get("Stock Repurchased", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0)
    issued = pd.to_numeric(
        cashflow_df.get("Stock Issued", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0)
    # Net buyback flow (positive = net buybacks). Repurchased is an outflow
    # so we subtract; Issued is an inflow so it reduces net buyback.
    net_buyback = repurchased.abs() - issued.abs()
    # TTM = rolling 4-quarter sum. For annual frames pass a 1-period window
    # (caller must align first).
    window = 4 if len(net_buyback) >= 4 else max(1, len(net_buyback))
    ttm = net_buyback.rolling(window, min_periods=1).sum()

    # Align both series on a common index, then compute the ratio.
    common = ttm.index.intersection(market_cap_series.index)
    if common.empty:
        return pd.Series(dtype=float)
    yield_pct = (ttm.loc[common] / market_cap_series.loc[common].replace(0, np.nan) * 100).round(2)
    return yield_pct


def compute_cumulative_shares_change(
    shares_series: pd.Series,
    years: int = 5,
) -> Optional[float]:
    """Return cumulative shares change over the last *years* years, in %.

    Negative = net buybacks / share count shrank.
    Positive = net dilution.
    Returns None if not enough history (need at least `years * 4` quarterly
    rows, i.e. the earliest available sample).
    """
    if shares_series is None or shares_series.empty:
        return None
    s = pd.to_numeric(shares_series, errors="coerce").dropna()
    if s.empty:
        return None
    window = years * 4
    if len(s) < window + 1:
        return None
    latest = s.iloc[-1]
    anchor = s.iloc[-(window + 1)]
    if anchor == 0:
        return None
    return round((latest - anchor) / anchor * 100, 2)
