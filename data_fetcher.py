"""
Financial data fetcher module using yfinance.

Provides functions to fetch comprehensive financial data for any stock ticker,
including company information, financial statements, cash flow data, balance sheet data,
key metrics, and analyst forecasts. All data is cached via Streamlit for performance.
"""

import json
import re as _re
import pandas as pd
import numpy as np
import yfinance as yf
from yfinance import const as yf_const
import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
import warnings
import requests as _requests

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# FMP (Financial Modeling Prep) configuration
# ---------------------------------------------------------------------------
# Free tier: 250 API calls/day.  Register at https://financialmodelingprep.com/
# Set via environment variable or Streamlit secrets.
import os as _os
_FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _fmp_key() -> str:
    """Return current FMP API key (reads env var each time so sidebar updates work)."""
    return _os.environ.get("FMP_API_KEY", "")


def _fmp_available() -> bool:
    return bool(_fmp_key())


def _period_sort_key(label: str):
    """Sort key for period labels like 'Q1 2024', 'FY 2024', '2024'.
    Returns (year, sub) for ascending chronological order."""
    parts = label.split()
    if len(parts) == 2 and parts[0].startswith("Q"):
        # "Q1 2024" → (2024, 1)
        return (int(parts[1]), int(parts[0][1]))
    if len(parts) == 2 and parts[0] == "FY":
        # "FY 2024" → (2024, 0)
        return (int(parts[1]), 0)
    # Try last element as year (handles "2024" or other formats)
    for p in reversed(parts):
        try:
            return (int(p), 0)
        except ValueError:
            continue
    return (0, 0)


def _sort_df_chronological(df: pd.DataFrame) -> pd.DataFrame:
    """Sort a DataFrame index chronologically (ascending)."""
    if df.empty:
        return df
    return df.sort_index(key=lambda idx: idx.map(_period_sort_key))


# ---------------------------------------------------------------------------
# SEC EDGAR XBRL API (free, no API key required)
# ---------------------------------------------------------------------------
# https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
# Requires User-Agent header per SEC policy.

_SEC_TICKER_MAP: Dict[str, int] = {}  # populated lazily


def _sec_load_ticker_map() -> Dict[str, int]:
    """Load SEC ticker → CIK mapping (cached in module-level dict)."""
    global _SEC_TICKER_MAP
    if _SEC_TICKER_MAP:
        return _SEC_TICKER_MAP
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        resp = _requests.get(url, timeout=15, headers={"User-Agent": "QuarterCharts/1.0 contact@example.com"})
        resp.raise_for_status()
        data = resp.json()
        for entry in data.values():
            _SEC_TICKER_MAP[entry["ticker"].upper()] = int(entry["cik_str"])
    except Exception as exc:
        print(f"[SEC] Failed to load ticker map: {exc}")
    return _SEC_TICKER_MAP


def _sec_get_cik(ticker: str) -> Optional[int]:
    """Get CIK number for a ticker symbol.

    SEC's company_tickers.json stores dual-class symbols with a hyphen
    (e.g. "BRK-B", "BF-B"), while user input and yfinance use a dot
    ("BRK.B"). Normalize before the lookup so both forms resolve.
    """
    mapping = _sec_load_ticker_map()
    key = ticker.upper().replace(".", "-")
    return mapping.get(key)


def _sec_fetch_company_facts(ticker: str) -> Optional[dict]:
    """Fetch all XBRL facts for a company from SEC EDGAR."""
    cik = _sec_get_cik(ticker)
    if cik is None:
        return None
    cik_padded = str(cik).zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    try:
        resp = _requests.get(url, timeout=20, headers={"User-Agent": "QuarterCharts/1.0 contact@example.com"})
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"[SEC] companyfacts/{ticker} (CIK {cik}): {exc}")
        return None


# SEC EDGAR us-gaap concept → friendly name mappings
# Income statement (duration-based → use CY####Q# frames)
_SEC_INCOME_MAP = {
    # Revenue (companies use different tags across eras)
    "Revenues": "Revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenue",
    "SalesRevenueNet": "Revenue",
    "SalesRevenueGoodsNet": "Revenue",
    "SalesRevenueServicesNet": "Revenue",
    "RevenueFromContractWithCustomerIncludingAssessedTax": "Revenue",
    # Cost / Profit
    "CostOfRevenue": "Cost Of Revenue",
    "CostOfGoodsAndServicesSold": "Cost Of Revenue",
    "CostOfGoodsSold": "Cost Of Revenue",
    "GrossProfit": "Gross Profit",
    "OperatingIncomeLoss": "Operating Income",
    "NetIncomeLoss": "Net Income",
    # EPS
    "EarningsPerShareBasic": "Basic EPS",
    "EarningsPerShareDiluted": "Diluted EPS",
    # Expenses
    "ResearchAndDevelopmentExpense": "R&D Expenses",
    "SellingGeneralAndAdministrativeExpense": "SGA Expenses",
    "OperatingExpenses": "Operating Expenses",
    "InterestExpense": "Interest Expense",
    "InterestIncomeExpenseNet": "Interest Income",
    "InvestmentIncomeInterest": "Interest Income",
    "IncomeTaxExpenseBenefit": "Income Tax Expense",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": "Pretax Income",
    # Shares
    "WeightedAverageNumberOfShareOutstandingBasicAndDiluted": "Basic Average Shares",
    "WeightedAverageNumberOfSharesOutstandingBasic": "Basic Average Shares",
    "WeightedAverageNumberOfDilutedSharesOutstanding": "Diluted Average Shares",
}

# Balance sheet (instantaneous → use CY####Q#I frames)
_SEC_BS_MAP = {
    "Assets": "Total Assets",
    "AssetsCurrent": "Current Assets",
    "AssetsNoncurrent": "Non-Current Assets",
    "Liabilities": "Total Liabilities",
    "LiabilitiesCurrent": "Current Liabilities",
    "LiabilitiesNoncurrent": "Non-Current Liabilities",
    "StockholdersEquity": "Stockholders Equity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "Stockholders Equity",
    "CashAndCashEquivalentsAtCarryingValue": "Cash and Cash Equivalents",
    "CashCashEquivalentsAndShortTermInvestments": "Cash and Cash Equivalents",
    "LongTermDebt": "Long Term Debt",
    "LongTermDebtNoncurrent": "Long Term Debt",
    "DebtCurrent": "Total Debt",
    "LongTermDebtAndCapitalLeaseObligations": "Total Debt",
}

# Cash flow (duration-based → use CY####Q# frames)
_SEC_CF_MAP = {
    "NetCashProvidedByUsedInOperatingActivities": "Operating CF",
    "NetCashProvidedByUsedInInvestingActivities": "Investing CF",
    "NetCashProvidedByUsedInFinancingActivities": "Financing CF",
    "PaymentsToAcquirePropertyPlantAndEquipment": "CapEx",
    "CapitalExpenditureDiscontinuedOperations": "CapEx",
    "ShareBasedCompensation": "Stock Based Compensation",
    "AllocatedShareBasedCompensationExpense": "Stock Based Compensation",
    "DepreciationDepletionAndAmortization": "D&A",
    "DepreciationAndAmortization": "D&A",
    "Depreciation": "D&A",
}

# ---------------------------------------------------------------------------
# Sector-specific us-gaap supplements (Task #31)
# ---------------------------------------------------------------------------
# When `info_data.get_sic_sector(ticker)` returns one of these keys, the
# baseline `_SEC_*_MAP` is MERGED with the matching supplement dict before
# extraction — so JPM gets `Net Interest Income` in addition to whatever
# generic revenue lines its XBRL happens to tag. Generic tickers fall
# through to the baseline unchanged (zero overhead).
#
# Keep each supplement narrow: only add tags that the sector genuinely
# uses and the baseline misses. Duplicating a generic tag here with a
# different friendly name would cause column collisions.
_SECTOR_FIELD_MAP: Dict[str, Dict[str, Dict[str, str]]] = {
    "bank": {
        "income": {
            "NetInterestIncome": "Net Interest Income",
            "InterestAndDividendIncomeOperating": "Net Interest Income",
            "InterestIncomeOperating": "Net Interest Income",
            "ProvisionForLoanLeaseAndOtherLosses": "Provision for Loan Losses",
            "ProvisionForCreditLosses": "Provision for Loan Losses",
            "ProvisionForLoanAndLeaseLosses": "Provision for Loan Losses",
            "NoninterestIncome": "Noninterest Income",
            "NoninterestExpense": "Noninterest Expense",
        },
        "balance": {},
        "cashflow": {},
    },
    "insurer": {
        "income": {
            "PremiumsEarnedNet": "Premiums Earned",
            "PremiumsEarnedNetLifeInsurance": "Premiums Earned",
            "PremiumsWrittenNet": "Premiums Written",
            "InsuranceLossesAndLossAdjustmentExpense": "Losses & Loss Adjustment",
            "BenefitsLossesAndExpenses": "Benefits & Losses",
            "PolicyholderBenefitsAndClaimsIncurredNet": "Benefits & Losses",
        },
        "balance": {},
        "cashflow": {},
    },
    "energy": {
        "income": {
            # Energy filers often skip CostOfRevenue and fold into this line.
            "CostsAndExpenses": "Total Costs & Expenses",
        },
        "balance": {
            "OilAndGasPropertyFullCostMethodGross": "Oil & Gas Property (Full Cost, Gross)",
            "OilAndGasPropertyFullCostMethodNet": "Oil & Gas Property (Full Cost, Net)",
            "OilAndGasPropertySuccessfulEffortMethodGross": "Oil & Gas Property (Successful Efforts, Gross)",
            "OilAndGasPropertySuccessfulEffortMethodNet": "Oil & Gas Property (Successful Efforts, Net)",
        },
        "cashflow": {},
    },
}


def _augment_field_map(base_map: dict, ticker: str, statement: str) -> dict:
    """Return *base_map* merged with sector-specific tags for *ticker*.

    *statement* must be one of ``"income"``, ``"balance"``, ``"cashflow"``.
    Falls back to *base_map* unchanged on any lookup error or for
    "general"-sector tickers, so the sector path is additive and never
    regresses behavior for non-sector tickers.
    """
    try:
        from info_data import get_sic_sector
        sector = get_sic_sector(ticker)
    except Exception:
        return base_map
    if sector == "general":
        return base_map
    supplement = _SECTOR_FIELD_MAP.get(sector, {}).get(statement, {})
    if not supplement:
        return base_map
    return {**base_map, **supplement}


def _sec_extract_facts(
    company_facts: dict,
    field_map: dict,
    quarterly: bool = True,
    instantaneous: bool = False,
) -> pd.DataFrame:
    """
    Extract quarterly or annual data from SEC EDGAR companyfacts JSON.

    Parameters
    ----------
    company_facts : dict
        Full companyfacts JSON response.
    field_map : dict
        Mapping of us-gaap concept names to friendly names.
    quarterly : bool
        If True, extract quarterly data; otherwise annual.
    instantaneous : bool
        If True, look for CY####Q#I frames (point-in-time, for balance sheet).
        If False, look for CY####Q# frames (duration, for income/cash flow).

    Notes
    -----
    For companies with non-December fiscal year-ends (e.g. NVIDIA with Jan FYE),
    Q4 data only appears in the annual 10-K filing (CY#### frame), not as CY####Q4.
    For duration items (income/cash flow): Q4 = Annual - (Q1 + Q2 + Q3).
    For instantaneous items (balance sheet): Q4 = CY####I (annual snapshot).
    """
    us_gaap = company_facts.get("facts", {}).get("us-gaap", {})
    if not us_gaap:
        return pd.DataFrame()

    # Collect data: period_label → {metric: value}
    records: Dict[str, Dict[str, float]] = {}
    # Also collect annual data for Q4 derivation
    annual_records: Dict[str, Dict[str, float]] = {}

    for concept_name, friendly_name in field_map.items():
        concept_data = us_gaap.get(concept_name)
        if not concept_data:
            continue

        units = concept_data.get("units", {})
        entries = units.get("USD", []) or units.get("USD/shares", []) or units.get("shares", [])
        if not entries:
            continue

        for entry in entries:
            frame = entry.get("frame", "")
            if not frame:
                continue

            val = entry.get("val")
            if val is None:
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            if quarterly:
                # --- Quarterly frames: CY####Q# or CY####Q#I ---
                if instantaneous:
                    # Match quarterly instantaneous: CY2024Q1I
                    m_q = _re.match(r"^CY(\d{4})(Q[1-4])I$", frame)
                    # Match annual instantaneous: CY2024I (year-end snapshot)
                    m_a = _re.match(r"^CY(\d{4})I$", frame) if not m_q else None
                else:
                    # Match quarterly duration: CY2024Q1
                    m_q = _re.match(r"^CY(\d{4})(Q[1-4])$", frame)
                    # Match annual duration: CY2024
                    m_a = _re.match(r"^CY(\d{4})$", frame) if not m_q else None

                if m_q:
                    label = f"{m_q.group(2)} {m_q.group(1)}"  # "Q1 2024"
                    if label not in records:
                        records[label] = {}
                    if friendly_name not in records[label]:
                        records[label][friendly_name] = val
                elif m_a:
                    year = m_a.group(1)
                    if year not in annual_records:
                        annual_records[year] = {}
                    if friendly_name not in annual_records[year]:
                        annual_records[year][friendly_name] = val
            else:
                # Annual mode
                if instantaneous:
                    if not _re.match(r"^CY\d{4}I$", frame):
                        continue
                    label = frame[2:-1]  # "2024"
                else:
                    if not _re.match(r"^CY\d{4}$", frame):
                        continue
                    label = frame[2:]  # "2024"

                if label not in records:
                    records[label] = {}
                if friendly_name not in records[label]:
                    records[label][friendly_name] = val

    # --- Derive Q4 from annual data for years missing Q4 ---
    if quarterly and annual_records:
        for year, annual_vals in annual_records.items():
            q4_label = f"Q4 {year}"
            if q4_label in records:
                continue  # Already have Q4 from quarterly frames

            if instantaneous:
                # Balance sheet: Q4 = annual year-end snapshot directly
                if q4_label not in records:
                    records[q4_label] = {}
                for metric, annual_val in annual_vals.items():
                    if metric not in records[q4_label]:
                        records[q4_label][metric] = annual_val
            else:
                # Duration items: Q4 = Annual - (Q1 + Q2 + Q3)
                q1 = records.get(f"Q1 {year}", {})
                q2 = records.get(f"Q2 {year}", {})
                q3 = records.get(f"Q3 {year}", {})
                if not (q1 or q2 or q3):
                    continue  # No quarterly data for this year at all

                if q4_label not in records:
                    records[q4_label] = {}
                for metric, annual_val in annual_vals.items():
                    if metric in records[q4_label]:
                        continue
                    # Only derive Q4 if the metric exists in ALL of Q1, Q2, Q3.
                    # If any quarter is missing this metric, the subtraction
                    # Annual - (Q1+Q2+Q3) would be wrong (defaulting to 0
                    # inflates Q4 with the full annual value).
                    if metric not in q1 or metric not in q2 or metric not in q3:
                        continue
                    q1_val = q1[metric]
                    q2_val = q2[metric]
                    q3_val = q3[metric]
                    q_sum = q1_val + q2_val + q3_val
                    q4_val = annual_val - q_sum
                    records[q4_label][metric] = q4_val

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(records, orient="index")
    df.index.name = "Period"

    # Sort ascending
    df = _sort_df_chronological(df)

    # Compute Gross Profit from Revenue - Cost Of Revenue where missing
    if "Revenue" in df.columns and "Cost Of Revenue" in df.columns:
        if "Gross Profit" not in df.columns:
            df["Gross Profit"] = df["Revenue"] - df["Cost Of Revenue"]
        else:
            mask = df["Gross Profit"].isna() & df["Revenue"].notna() & df["Cost Of Revenue"].notna()
            df.loc[mask, "Gross Profit"] = df.loc[mask, "Revenue"] - df.loc[mask, "Cost Of Revenue"]

    # Compute Free CF if we have Operating CF and CapEx
    if "Operating CF" in df.columns and "CapEx" in df.columns and "Free CF" not in df.columns:
        df["Free CF"] = df["Operating CF"] - df["CapEx"].abs()

    return df


def _sec_get_income_statement(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Fetch income statement from SEC EDGAR, augmented with sector-specific
    us-gaap tags when applicable (Task #31)."""
    facts = _sec_fetch_company_facts(ticker)
    if facts is None:
        return pd.DataFrame()
    field_map = _augment_field_map(_SEC_INCOME_MAP, ticker, "income")
    return _sec_extract_facts(facts, field_map, quarterly=quarterly, instantaneous=False)


def _sec_get_balance_sheet(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Fetch balance sheet from SEC EDGAR, augmented with sector-specific
    us-gaap tags when applicable (Task #31)."""
    facts = _sec_fetch_company_facts(ticker)
    if facts is None:
        return pd.DataFrame()
    field_map = _augment_field_map(_SEC_BS_MAP, ticker, "balance")
    return _sec_extract_facts(facts, field_map, quarterly=quarterly, instantaneous=True)


def _sec_get_cash_flow(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Fetch cash flow statement from SEC EDGAR, augmented with sector-specific
    us-gaap tags when applicable (Task #31)."""
    facts = _sec_fetch_company_facts(ticker)
    if facts is None:
        return pd.DataFrame()
    field_map = _augment_field_map(_SEC_CF_MAP, ticker, "cashflow")
    return _sec_extract_facts(facts, field_map, quarterly=quarterly, instantaneous=False)


# ---------------------------------------------------------------------------
# quarterchart.com data source (free, no API key)
# ---------------------------------------------------------------------------
# Extracts segment data from the inline JSON blob on quarterchart.com/chart/{TICKER}.
# Data is in fiscal-year labels – we convert to calendar quarters using the
# company's fiscal-year-end month from yfinance.


@st.cache_data(ttl=3600, show_spinner=False)
def _opensankey_fetch_json(ticker: str) -> Optional[dict]:
    """Fetch and parse the inline JSON blob from quarterchart.com."""
    url = f"https://quarterchart.com/chart/{ticker.upper()}"
    try:
        resp = _requests.get(
            url, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; QuarterCharts/1.0)"},
        )
        resp.raise_for_status()
        html = resp.text
        # The JSON blob sits inside a <script> tag and starts with {"company_info"
        start = html.find('{"company_info"')
        if start < 0:
            return None
        # Walk forward finding matching braces
        depth, end = 0, start
        for i in range(start, len(html)):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        blob = json.loads(html[start:end])
        return blob
    except Exception as exc:
        print(f"[QuarterCharts] Failed to fetch {ticker}: {exc}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _get_fy_end_month(ticker: str) -> int:
    """Get fiscal year end month (1-12) from yfinance."""
    try:
        info = yf.Ticker(ticker).info
        ts = info.get("lastFiscalYearEnd")
        if ts:
            dt = datetime.fromtimestamp(ts)
            return dt.month
    except Exception:
        pass
    return 12  # default: calendar year = fiscal year


def _fiscal_to_calendar_label(fiscal_label: str, fy_end_month: int) -> str:
    """Convert a fiscal-year label to a calendar-quarter/year label.

    Uses the MIDDLE month of each fiscal quarter to determine the calendar
    quarter.  This avoids labelling a period as e.g. "Q1 2026" when the
    fiscal quarter only barely crosses into January 2026.

    Example (NVIDIA, FY ends January = month 1):
      FY2026 Q4 (Nov-Jan) → middle = Dec → **Q4 2025**
      FY2026 Q1 (Feb-Apr) → middle = Mar → Q1 2025

    Annual: uses the middle of the fiscal year (6 months from start).
    """
    parts = fiscal_label.split()

    if fy_end_month == 12:
        # Standard calendar FY — no shift needed
        if len(parts) == 2 and parts[0] == "FY":
            return parts[1]  # "FY 2025" → "2025"
        return fiscal_label  # "Q1 2025" stays the same

    # --- Annual: "FY YYYY" → calendar year of mid-point ---
    if len(parts) == 2 and parts[0] == "FY":
        fy_year = int(parts[1])
        mid_raw = fy_end_month + 6  # middle of 12-month fiscal year
        cal_year = fy_year - 1 if mid_raw <= 12 else fy_year
        return str(cal_year)

    # --- Quarterly: "Qn YYYY" → calendar quarter via middle month ---
    if len(parts) != 2 or not parts[0].startswith("Q"):
        return fiscal_label
    fq = int(parts[0][1])      # fiscal quarter 1-4
    fy_year = int(parts[1])    # fiscal year

    # Middle month of fiscal Qn  (2nd of the 3 months in the quarter)
    mid_month_raw = fy_end_month + 3 * fq - 1
    mid_month = ((mid_month_raw - 1) % 12) + 1

    # Calendar year: if mid_month_raw ≤ 12 → still in fy_year-1
    cal_year = fy_year - 1 if mid_month_raw <= 12 else fy_year

    # Calendar quarter from the middle month
    cal_quarter = (mid_month - 1) // 3 + 1

    return f"Q{cal_quarter} {cal_year}"


def sec_to_fiscal_label(sec_label: str, fy_end_month: int) -> str:
    """Convert an SEC calendar-quarter label to a fiscal-quarter label.

    SEC EDGAR uses frames like CY2026Q1 → "Q1 2026" (calendar convention).
    This function converts to fiscal convention: "Q3 2026" for ORCL (FY May).

    For December FY companies, labels are returned unchanged.

    Parameters
    ----------
    sec_label : str   e.g. "Q1 2026" or "2025" (annual)
    fy_end_month : int  1-12

    Returns
    -------
    str   e.g. "Q3 2026"
    """
    if fy_end_month == 12:
        return sec_label  # Standard calendar year — no conversion

    parts = sec_label.split()

    # Annual label: "2025" → stays the same (or convert to FY)
    if len(parts) == 1 and parts[0].isdigit():
        return sec_label

    if len(parts) != 2 or not parts[0].startswith("Q"):
        return sec_label

    cq = int(parts[0][1])   # calendar quarter 1-4
    cy = int(parts[1])      # calendar year

    # Build map: calendar quarter → fiscal quarter
    # Fiscal Qn ends at month (fy_end_month + n*3) mod 12
    cq_to_fq = {}
    for fq in range(1, 5):
        end_m = (fy_end_month + fq * 3) % 12
        if end_m == 0:
            end_m = 12
        cq_num = (end_m - 1) // 3 + 1  # which calendar quarter this month falls in
        cq_to_fq[cq_num] = fq

    fq = cq_to_fq.get(cq, cq)

    # Fiscal year: if the period end month <= fy_end_month → same year;
    # otherwise → next year (because FY spans two calendar years)
    end_m = (fy_end_month + fq * 3) % 12
    if end_m == 0:
        end_m = 12
    if end_m <= fy_end_month:
        fy_year = cy
    else:
        fy_year = cy + 1

    return f"Q{fq} {fy_year}"


def relabel_df_to_fiscal(df: pd.DataFrame, fy_end_month: int) -> pd.DataFrame:
    """Relabel a DataFrame index from SEC labels to fiscal labels."""
    if fy_end_month == 12 or df.empty:
        return df
    new_index = [sec_to_fiscal_label(lbl, fy_end_month) for lbl in df.index]
    df = df.copy()
    df.index = new_index
    return df


def _opensankey_get_segments(
    ticker: str, chart_index: int, quarterly: bool = True
) -> pd.DataFrame:
    """Extract segment data from quarterchart.com.

    chart_index: 0 = product segments, 1 = geography segments.
    Returns DataFrame with calendar-quarter labels as index.
    """
    blob = _opensankey_fetch_json(ticker)
    if not blob:
        return pd.DataFrame()

    try:
        freq_key = "quarter" if quarterly else "annual"
        charts = blob.get("chart_data", {}).get("data", {}).get(freq_key, [])
        if chart_index >= len(charts):
            return pd.DataFrame()

        chart = charts[chart_index]
        labels = chart.get("labels", [])
        datasets = chart.get("datasets", [])
        if not labels or not datasets:
            return pd.DataFrame()

        # Fiscal → calendar conversion
        fy_end_month = _get_fy_end_month(ticker)

        records: Dict[str, Dict[str, float]] = {}
        for ds in datasets:
            seg_name = ds.get("label", "")
            data = ds.get("data", [])
            if not seg_name:
                continue
            for i, val in enumerate(data):
                if i >= len(labels) or not val:
                    continue
                fiscal_label = labels[i]
                cal_label = _fiscal_to_calendar_label(fiscal_label, fy_end_month)
                if cal_label not in records:
                    records[cal_label] = {}
                try:
                    records[cal_label][seg_name] = float(val)
                except (ValueError, TypeError):
                    pass

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(records, orient="index")
        df.index.name = "Period"

        # Drop columns that are all zero (obsolete segments)
        df = df.loc[:, (df != 0).any()]

        # Sort chronologically
        df = _sort_df_chronological(df)
        return df

    except Exception as exc:
        print(f"[QuarterCharts] segments/{ticker}: {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Revenue Segmentation (Product & Geography)
# ---------------------------------------------------------------------------
# Primary: quarterchart.com data source (free, no API key)
# Fallback: FMP free-tier stable endpoints (250 calls/day)

def _fmp_get_segments(ticker: str, seg_type: str, quarterly: bool = True) -> pd.DataFrame:
    """
    Fetch revenue segmentation from FMP stable API.

    Parameters
    ----------
    ticker : str
        Stock symbol.
    seg_type : str
        "product" or "geographic".
    quarterly : bool
        Quarterly or annual data.  Note: free-tier only supports annual (FY).
        When quarterly=True we still fetch annual data and display it.

    Returns
    -------
    pd.DataFrame
        Index = period labels ("FY 2024" or "Q1 2024"), columns = segment names,
        values = revenue.
    """
    if not _fmp_available():
        return pd.DataFrame()

    endpoint = f"revenue-{seg_type}-segmentation"

    # Free tier: period=quarter returns 402. Try quarter first, fallback to no period (annual).
    urls = []
    if quarterly:
        urls.append(
            f"https://financialmodelingprep.com/stable/{endpoint}"
            f"?symbol={ticker}&period=quarter&structure=flat&apikey={_fmp_key()}"
        )
    # Annual / default (works on free tier)
    urls.append(
        f"https://financialmodelingprep.com/stable/{endpoint}"
        f"?symbol={ticker}&structure=flat&apikey={_fmp_key()}"
    )

    data = None
    for url in urls:
        try:
            resp = _requests.get(url, timeout=10)
            print(f"[FMP] {endpoint} → {resp.status_code}")
            if resp.status_code in (402, 403):
                continue
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list):
                print(f"[FMP] {endpoint}/{ticker}: {len(data)} records")
                break
            data = None
        except Exception as exc:
            print(f"[FMP] {endpoint}/{ticker}: {exc}")

    if not data or not isinstance(data, list):
        return pd.DataFrame()

    records: Dict[str, Dict[str, float]] = {}
    for item in data:
        date_str = item.get("date", "")
        if not date_str:
            continue
        try:
            dt = pd.Timestamp(date_str)
        except Exception:
            continue

        # Build period label
        period_val = item.get("period", "")
        if period_val in ("Q1", "Q2", "Q3", "Q4"):
            label = f"{period_val} {dt.year}"
        elif period_val == "FY":
            label = f"FY {dt.year}"
        elif quarterly:
            label = _quarter_label(dt)
        else:
            label = str(dt.year)

        if label in records:
            continue

        # Parse segment values — new stable API nests them under "data"
        seg_data = item.get("data", None)
        if isinstance(seg_data, dict):
            # New stable format: {"data": {"Automotive": 123, "Gaming": 456}}
            row: Dict[str, float] = {}
            for seg_name, val in seg_data.items():
                if val is not None:
                    try:
                        row[seg_name] = float(val)
                    except (ValueError, TypeError):
                        pass
            if row:
                records[label] = row
        else:
            # Legacy flat format: {"Automotive": 123, "Gaming": 456, "date": "..."}
            row = {}
            skip_keys = {"date", "symbol", "period", "fiscalYear",
                         "reportedCurrency", "structure"}
            for key, val in item.items():
                if key in skip_keys:
                    continue
                if val is not None:
                    try:
                        row[key] = float(val)
                    except (ValueError, TypeError):
                        pass
            if row:
                records[label] = row

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(records, orient="index")
    df.index.name = "Period"

    df = _sort_df_chronological(df)
    return df


def _sec_get_segment_revenue(ticker: str, quarterly: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Extract revenue segmentation from SEC EDGAR XBRL filings.

    Parses the company's XBRL instance documents to find dimensional
    revenue breakdowns by operating segment and geography.

    Returns
    -------
    dict
        {"product": DataFrame, "geography": DataFrame} — each may be empty.
    """
    result = {"product": pd.DataFrame(), "geography": pd.DataFrame()}

    cik = _sec_get_cik(ticker)
    if cik is None:
        return result
    cik_padded = str(cik).zfill(10)
    headers = {"User-Agent": "QuarterCharts/1.0 contact@example.com"}

    # 1) Get list of recent filings
    try:
        sub_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        resp = _requests.get(sub_url, timeout=5, headers=headers)
        resp.raise_for_status()
        sub_data = resp.json()
    except Exception as exc:
        print(f"[SEC] submissions/{ticker}: {exc}")
        return result

    recent = sub_data.get("filings", {}).get("recent", {})
    if not recent:
        return result

    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    filing_dates = recent.get("filingDate", [])

    # 2) Find recent 10-Q and 10-K filings.
    #
    # History depth: a 10-K plus three 10-Qs per year = 4 filings/year. Scan
    # the last 16 filings (~4 years) for quarterly and the last 5 10-Ks
    # (~5 years) for annual so the returned segment frames have enough
    # periods to render meaningful trend charts. The per-filing cost is a
    # few hundred ms (FilingSummary.xml + 1–3 R-report HTMLs), so 16 scans
    # is well under the 1h cache TTL set by `_cached_revenue_by_*`. Tickers
    # with smaller histories just return whatever exists.
    target_forms = {"10-Q", "10-K"} if quarterly else {"10-K"}
    max_filings = 16 if quarterly else 5
    filing_urls = []

    for i, form in enumerate(forms):
        if form in target_forms and i < len(accessions) and i < len(primary_docs):
            accn = accessions[i].replace("-", "")
            doc = primary_docs[i]
            # Build the XBRL instance document URL
            # Try R files (structured report) first
            base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn}"
            filing_urls.append({
                "form": form,
                "accn": accessions[i],
                "accn_nd": accn,
                "doc": doc,
                "base": base,
                "date": filing_dates[i] if i < len(filing_dates) else "",
            })
            if len(filing_urls) >= max_filings:
                break

    if not filing_urls:
        return result

    # 3) For each filing, try to get the XBRL viewer JSON or parse the instance doc
    import xml.etree.ElementTree as ET

    product_records: Dict[str, Dict[str, float]] = {}
    geo_records: Dict[str, Dict[str, float]] = {}

    for filing in filing_urls:
        # Try to fetch the R report files for segment data
        # SEC EDGAR provides FilingSummary.xml which lists available reports
        summary_url = f"{filing['base']}/FilingSummary.xml"
        try:
            resp = _requests.get(summary_url, timeout=5, headers=headers)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
        except Exception:
            continue

        # Find reports related to revenue segments
        ns = {"": "http://www.sec.gov/summarystyle"}
        reports = root.findall(".//Report") or root.findall(".//{http://www.sec.gov/summarystyle}Report")
        if not reports:
            # Try without namespace
            try:
                reports = [r for r in root.iter() if r.tag.endswith("Report")]
            except Exception:
                continue

        for report in reports:
            long_name = (report.findtext("LongName") or
                        report.findtext("{http://www.sec.gov/summarystyle}LongName") or "")
            short_name = (report.findtext("ShortName") or
                         report.findtext("{http://www.sec.gov/summarystyle}ShortName") or "")
            html_file = (report.findtext("HtmlFileName") or
                        report.findtext("{http://www.sec.gov/summarystyle}HtmlFileName") or "")

            name_lower = (long_name + " " + short_name).lower()

            # Look for segment/disaggregation revenue reports
            is_segment = any(kw in name_lower for kw in [
                "segment", "disaggregat", "revenue by", "product", "geographic",
                "operating segment", "reportable segment",
            ])
            if not is_segment or not html_file:
                continue

            # Fetch the R report HTML and parse it for segment data
            report_url = f"{filing['base']}/{html_file}"
            try:
                resp = _requests.get(report_url, timeout=5, headers=headers)
                resp.raise_for_status()
                html = resp.text
            except Exception:
                continue

            # Parse the HTML table for segment revenue data
            _parse_segment_html(html, filing, name_lower,
                               product_records, geo_records, quarterly)

    # Build DataFrames
    for name, records in [("product", product_records), ("geography", geo_records)]:
        if records:
            df = pd.DataFrame.from_dict(records, orient="index")
            df.index.name = "Period"

            df = _sort_df_chronological(df)
            result[name] = df

    return result


def _parse_segment_html(
    html: str,
    filing: dict,
    report_name: str,
    product_records: Dict[str, Dict[str, float]],
    geo_records: Dict[str, Dict[str, float]],
    quarterly: bool,
):
    """Parse an SEC EDGAR R-report HTML table for segment revenue data."""
    try:
        dfs = pd.read_html(html)
    except Exception:
        return

    for df in dfs:
        if df.empty or len(df) < 2:
            continue

        # The first column usually contains segment names
        # Other columns contain values for different periods
        first_col = df.columns[0] if len(df.columns) > 0 else None
        if first_col is None:
            continue

        # Check if this table has revenue/segment data
        cell_strs = df.iloc[:, 0].astype(str).str.lower()
        has_revenue = cell_strs.str.contains("revenue|net revenue|total", regex=True).any()
        if not has_revenue:
            continue

        # Determine if this is product or geographic segmentation
        geo_keywords = ["united states", "americas", "asia", "europe", "china",
                       "taiwan", "singapore", "japan", "korea", "emea", "apac"]
        prod_keywords = ["data center", "gaming", "compute", "graphics",
                        "professional", "automotive", "oem", "cloud", "enterprise"]

        all_text = " ".join(cell_strs.tolist()).lower()
        is_geo = any(kw in all_text for kw in geo_keywords)
        is_prod = any(kw in all_text for kw in prod_keywords)
        if "geographic" in report_name:
            is_geo = True
        if "product" in report_name or "segment" in report_name:
            is_prod = True

        target = geo_records if is_geo else product_records if is_prod else None
        if target is None:
            continue

        # Parse period from filing date
        try:
            dt = pd.Timestamp(filing["date"])
            label = _quarter_label(dt) if quarterly else str(dt.year)
        except Exception:
            continue

        if label in target:
            continue

        # Extract segment names and values from the table
        row_data: Dict[str, float] = {}
        for _, row in df.iterrows():
            seg_name = str(row.iloc[0]).strip()
            if not seg_name or seg_name.lower() in ("nan", "none", ""):
                continue
            # Skip total/header rows
            if any(kw in seg_name.lower() for kw in ["total", "consolidated", "revenue"]):
                continue
            # Get the most recent value (last numeric column)
            for col_idx in range(len(row) - 1, 0, -1):
                try:
                    val = float(str(row.iloc[col_idx]).replace(",", "").replace("$", "").replace("(", "-").replace(")", ""))
                    if val != 0:
                        # SEC reports in millions typically
                        row_data[seg_name] = val * 1e6 if abs(val) < 1e6 else val
                        break
                except (ValueError, TypeError):
                    continue

        if row_data:
            target[label] = row_data


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_revenue_by_product(ticker: str, quarterly: bool, _fmp: str = "") -> pd.DataFrame:
    """Inner cached function. Tries quarterchart.com first, falls back to FMP."""
    # --- Primary: quarterchart.com data source (free, no API key) ---
    try:
        df = _opensankey_get_segments(ticker, 0, quarterly=quarterly)
        if not df.empty and len(df) >= 2:
            print(f"[QuarterCharts] product-segments/{ticker}: {len(df)} periods, {len(df.columns)} segments")
            return df
    except Exception as exc:
        print(f"[QuarterCharts] product-segments/{ticker}: {exc}")

    # --- Fallback: FMP ---
    if _fmp:
        try:
            df = _fmp_get_segments(ticker, "product", quarterly=quarterly)
            if not df.empty and len(df) >= 2:
                print(f"[FMP] product-segments/{ticker}: {len(df)} periods, {len(df.columns)} segments")
                return df
        except Exception as exc:
            print(f"[FMP] product-segments/{ticker}: {exc}")

    return pd.DataFrame()


def get_revenue_by_product(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Fetch revenue by product/operating segment (quarterchart.com → FMP fallback)."""
    return _cached_revenue_by_product(ticker, quarterly, _fmp=_fmp_key())


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_revenue_by_geography(ticker: str, quarterly: bool, _fmp: str = "") -> pd.DataFrame:
    """Inner cached function. Tries quarterchart.com first, falls back to FMP."""
    # --- Primary: quarterchart.com data source (free, no API key) ---
    try:
        df = _opensankey_get_segments(ticker, 1, quarterly=quarterly)
        if not df.empty and len(df) >= 2:
            print(f"[QuarterCharts] geo-segments/{ticker}: {len(df)} periods, {len(df.columns)} segments")
            return df
    except Exception as exc:
        print(f"[QuarterCharts] geo-segments/{ticker}: {exc}")

    # --- Fallback: FMP ---
    if _fmp:
        try:
            df = _fmp_get_segments(ticker, "geographic", quarterly=quarterly)
            if not df.empty and len(df) >= 2:
                print(f"[FMP] geo-segments/{ticker}: {len(df)} periods, {len(df.columns)} segments")
                return df
        except Exception as exc:
            print(f"[FMP] geo-segments/{ticker}: {exc}")

    return pd.DataFrame()


def get_revenue_by_geography(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Fetch revenue by geographic region (quarterchart.com → FMP fallback)."""
    return _cached_revenue_by_geography(ticker, quarterly, _fmp=_fmp_key())


def _camel2title(s: str, acronyms: Optional[List[str]] = None) -> str:
    """Convert CamelCase to 'Title Case With Spaces', preserving *acronyms*.

    Mirrors yfinance ``utils.camel2title`` logic so our index names match the
    standard yfinance DataFrame output.

    Examples (no acronyms):  TotalRevenue → Total Revenue
    Examples (acronyms=["EPS"]): BasicEPS → Basic EPS
    """
    # Step 1: insert space between lower→upper transitions
    out = _re.sub(r"([a-z])([A-Z])", r"\1 \2", s)

    if acronyms:
        # Step 2: insert space after known acronyms when followed by a new word
        for a in acronyms:
            out = _re.sub(rf"({a})([A-Z][a-z])", rf"\1 \2", out)
        # Step 3: title-case non-acronym words, leave acronyms intact
        words = out.split(" ")
        words = [w if w in acronyms else w.title() for w in words]
        return " ".join(words)

    return out.title()


# Acronym lists matching yfinance's pretty-print behaviour per statement type
_ACRONYMS_INCOME = ["EBIT", "EBITDA", "EPS", "NI"]
_ACRONYMS_BS = ["PPE"]
_ACRONYMS_CF = ["PPE"]
_API_ACRONYMS = {
    "financials": _ACRONYMS_INCOME,
    "balance-sheet": _ACRONYMS_BS,
    "cash-flow": _ACRONYMS_CF,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_large_number(num: Optional[float]) -> str:
    """Format large numbers into human-readable strings (T / B / M / K)."""
    if num is None or (isinstance(num, float) and np.isnan(num)):
        return "N/A"
    try:
        num = float(num)
        sign = "-" if num < 0 else ""
        num = abs(num)
        if num >= 1e12:
            return f"${sign}{num / 1e12:.2f}T"
        elif num >= 1e9:
            return f"${sign}{num / 1e9:.2f}B"
        elif num >= 1e6:
            return f"${sign}{num / 1e6:.2f}M"
        elif num >= 1e3:
            return f"${sign}{num / 1e3:.2f}K"
        else:
            return f"${sign}{num:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _quarter_label(date: pd.Timestamp) -> str:
    """Convert a period-end timestamp to a calendar quarter label.

    Uses the **middle month** of the reporting period (≈ 1 month before the
    period end) so that a fiscal quarter barely crossing into a new calendar
    quarter is attributed to the quarter where the majority of the period falls.

    Examples (NVIDIA, FY ends January):
      period end Jan 26 2026 → mid ≈ Dec 2025 → Q4 2025
      period end Apr 27 2025 → mid ≈ Mar 2025 → Q1 2025
    For standard Dec-FY companies results are unchanged:
      period end Mar 31 → mid ≈ Feb → Q1  (same)
      period end Jun 30 → mid ≈ May → Q2  (same)
    """
    mid = date - pd.DateOffset(months=1)
    q = (mid.month - 1) // 3 + 1
    return f"Q{q} {mid.year}"


def _safe_get(df: pd.DataFrame, names: List[str]) -> Optional[pd.Series]:
    """Return the first matching row from *df* (metrics × dates) given candidate names."""
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def _fetch_fmp_statement(ticker: str, statement: str, limit: int = 20, quarterly: bool = True) -> pd.DataFrame:
    """
    Fetch a financial statement from Financial Modeling Prep API.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol.
    statement : str
        One of "income-statement", "balance-sheet-statement", "cash-flow-statement".
    limit : int
        Number of periods to fetch (default 20).
    quarterly : bool
        If True fetch quarterly data, else annual.

    Returns
    -------
    pd.DataFrame
        DataFrame with period labels as index, metric names as columns (chart-ready).
    """
    if not _fmp_available():
        return pd.DataFrame()

    period = "quarter" if quarterly else "annual"
    url = f"{_FMP_BASE}/{statement}/{ticker}?period={period}&limit={limit}&apikey={_fmp_key()}"

    try:
        resp = _requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[FMP] {statement}/{ticker}: {exc}")
        return pd.DataFrame()

    if not data or isinstance(data, dict):  # Error response is dict
        return pd.DataFrame()

    return data  # Return raw JSON list - will be transformed by statement-specific functions


# FMP field name → our friendly name mappings
_FMP_INCOME_MAP = {
    "revenue": "Revenue",
    "costOfRevenue": "Cost Of Revenue",
    "grossProfit": "Gross Profit",
    "operatingIncome": "Operating Income",
    "netIncome": "Net Income",
    "ebitda": "EBITDA",
    "researchAndDevelopmentExpenses": "R&D Expenses",
    "sellingGeneralAndAdministrativeExpenses": "SGA Expenses",
    "operatingExpenses": "Operating Expenses",
    "interestExpense": "Interest Expense",
    "interestIncome": "Interest Income",
    "incomeTaxExpense": "Income Tax Expense",
    "incomeBeforeTax": "Pretax Income",
    "eps": "Basic EPS",
    "epsdiluted": "Diluted EPS",
    "weightedAverageShsOut": "Basic Average Shares",
    "weightedAverageShsOutDil": "Diluted Average Shares",
}

_FMP_BS_MAP = {
    "totalAssets": "Total Assets",
    "totalCurrentAssets": "Current Assets",
    "totalNonCurrentAssets": "Non-Current Assets",
    "totalLiabilities": "Total Liabilities",
    "totalCurrentLiabilities": "Current Liabilities",
    "totalNonCurrentLiabilities": "Non-Current Liabilities",
    "totalStockholdersEquity": "Stockholders Equity",
    "cashAndCashEquivalents": "Cash and Cash Equivalents",
    "totalDebt": "Total Debt",
    "longTermDebt": "Long Term Debt",
}

_FMP_CF_MAP = {
    "operatingCashFlow": "Operating CF",
    "netCashUsedForInvestingActivites": "Investing CF",
    "netCashUsedProvidedByFinancingActivities": "Financing CF",
    "freeCashFlow": "Free CF",
    "capitalExpenditure": "CapEx",
    "stockBasedCompensation": "Stock Based Compensation",
    "depreciationAndAmortization": "D&A",
    "changeInCash": "Cash and Cash Equivalents",
}


def _fmp_json_to_df(data: list, field_map: dict, quarterly: bool = True) -> pd.DataFrame:
    """Convert FMP JSON response list into a chart-ready DataFrame."""
    if not data:
        return pd.DataFrame()

    records = {}
    for item in data:
        try:
            dt = pd.Timestamp(item.get("date", item.get("fillingDate", "")))
        except Exception:
            continue

        label = _quarter_label(dt) if quarterly else str(dt.year)

        # Skip duplicate periods (keep the first/most recent filing)
        if label in records:
            continue

        row = {}
        for fmp_key, friendly_name in field_map.items():
            val = item.get(fmp_key)
            if val is not None and val != 0:
                try:
                    row[friendly_name] = float(val)
                except (ValueError, TypeError):
                    pass

        if row:
            records[label] = row

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(records, orient="index")
    df.index.name = "Period"

    # Sort ascending by date
    df = _sort_df_chronological(df)
    return df


def _fetch_extended_quarterly_raw(ticker_str: str, api_name: str, max_quarters: int = 20) -> pd.DataFrame:
    """
    Fetch extended quarterly financial data by making multiple batched API calls.

    Yahoo's timeseries API returns at most ~5 quarters per request. By shifting
    ``period2`` backwards we can stitch together more history (up to *max_quarters*).

    Parameters
    ----------
    ticker_str : str
        Stock ticker symbol.
    api_name : str
        One of ``"financials"``, ``"balance-sheet"``, ``"cash-flow"`` – matching
        the keys in ``yfinance.const.fundamentals_keys``.
    max_quarters : int
        Stop once we have at least this many quarters (default 20 ≈ 5 years).

    Returns
    -------
    pd.DataFrame
        Raw DataFrame in yfinance convention (index = metric names, columns =
        ``pd.Timestamp`` dates sorted newest → oldest).  Returns empty DataFrame
        on failure.
    """
    try:
        keys = yf_const.fundamentals_keys[api_name]
    except KeyError:
        return pd.DataFrame()

    acronyms = _API_ACRONYMS.get(api_name)

    # Use yfinance's managed session (handles cookies / crumb / consent)
    stock = yf.Ticker(ticker_str)
    data_mgr = getattr(stock, "_data", None)
    if data_mgr is None:
        return pd.DataFrame()

    all_data: Dict[pd.Timestamp, Dict[str, float]] = {}
    end_ts = int(pd.Timestamp.now("UTC").ceil("D").timestamp())
    min_ts = int(pd.Timestamp("2010-01-01").timestamp())

    for _batch in range(5):  # max 5 batches → ~25 quarters
        type_params = ",".join(f"quarterly{k}" for k in keys)
        url = (
            f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
            f"{ticker_str}?symbol={ticker_str}&type={type_params}"
            f"&period1={min_ts}&period2={end_ts}"
        )
        try:
            resp = data_mgr.cache_get(url=url, timeout=15)
            payload = json.loads(resp.text)
        except Exception:
            break

        results = payload.get("timeseries", {}).get("result", [])
        if not results:
            break

        batch_timestamps: set = set()
        new_data_found = False

        for r in results:
            if "timestamp" in r:
                batch_timestamps.update(r["timestamp"])
            for k, v in r.items():
                if k in ("meta", "timestamp") or not isinstance(v, list):
                    continue
                metric_name = _camel2title(k.replace("quarterly", "", 1), acronyms=acronyms)
                for entry in v:
                    try:
                        dt = pd.Timestamp(entry["asOfDate"])
                        val = float(entry["reportedValue"]["raw"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if dt not in all_data:
                        all_data[dt] = {}
                        new_data_found = True
                    elif metric_name in all_data[dt]:
                        continue  # already have this cell
                    all_data[dt][metric_name] = val
                    new_data_found = True

        if not batch_timestamps:
            break

        # Nothing new in this batch → stop (we've exhausted the API)
        if not new_data_found and _batch > 0:
            break

        # Shift window: set end_ts to 1 day before the oldest date we saw
        oldest = min(batch_timestamps)
        end_ts = oldest - 86400

        if end_ts <= min_ts or len(all_data) >= max_quarters:
            break

    if not all_data:
        return pd.DataFrame()

    # Build a DataFrame matching yfinance's convention (metrics × dates)
    dates_sorted = sorted(all_data.keys(), reverse=True)
    all_metrics = sorted({m for d in all_data.values() for m in d})
    df = pd.DataFrame(index=all_metrics, columns=dates_sorted, dtype=float)
    for dt, metrics in all_data.items():
        for metric, val in metrics.items():
            df.loc[metric, dt] = val

    return df


def _build_period_df(
    raw: pd.DataFrame,
    mapping: Dict[str, List[str]],
    quarterly: bool = True,
) -> pd.DataFrame:
    """
    Transform a raw yfinance statement (metrics×dates) into a chart-ready DataFrame
    with period labels as the index and friendly metric names as columns.

    Parameters
    ----------
    raw : pd.DataFrame
        Raw statement from yfinance (rows = metric names, cols = dates).
    mapping : dict
        ``{friendly_name: [list_of_possible_yfinance_row_names]}``.
    quarterly : bool
        If True, label periods as "Q# YYYY"; otherwise "YYYY".

    Returns
    -------
    pd.DataFrame
        Index = period labels sorted ascending, columns = friendly names.
    """
    if raw is None or raw.empty:
        return pd.DataFrame()

    records: Dict[str, Dict[str, float]] = {}
    dates = raw.columns  # dates are columns in raw yfinance DataFrames

    for date in dates:
        label = _quarter_label(date) if quarterly else str(date.year)
        row: Dict[str, float] = {}
        for friendly, candidates in mapping.items():
            series = _safe_get(raw, candidates)
            if series is not None:
                val = series.get(date, np.nan)
                row[friendly] = float(val) if not pd.isna(val) else np.nan
        if row:
            records[label] = row

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(records, orient="index")
    df.index.name = "Period"

    # Sort ascending by date  – custom sort: "Q1 2024" < "Q2 2024" etc.
    df = _sort_df_chronological(df)
    return df


# ---------------------------------------------------------------------------
# Company info
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def get_company_info(ticker: str) -> Dict[str, Any]:
    """Fetch company-level information and key valuation snapshot."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        if not info:
            return {}
        return {
            "company_name": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap"),
            "market_cap_fmt": format_large_number(info.get("marketCap")),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio") or info.get("trailingPegRatio"),
            "price_to_book": info.get("priceToBook"),
            "enterprise_value": info.get("enterpriseValue"),
            "ev_fmt": format_large_number(info.get("enterpriseValue")),
            "current_price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "shares_fmt": format_large_number(info.get("sharesOutstanding")),
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country", "N/A"),
            "website": info.get("website", "N/A"),
            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "profit_margins": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "free_cashflow": info.get("freeCashflow"),
            "operating_cashflow": info.get("operatingCashflow"),
            "total_revenue": info.get("totalRevenue"),
            "gross_margins": info.get("grossMargins"),
            "operating_margins": info.get("operatingMargins"),
        }
    except Exception as exc:
        print(f"[data_fetcher] get_company_info({ticker}): {exc}")
        return {}


# ---------------------------------------------------------------------------
# Per-quarter historical gap-fill (SEC → FMP → Finnhub → yfinance).
# ---------------------------------------------------------------------------
# When the primary source (SEC EDGAR) returns a quarterly series with one or
# more missing quarters in the middle of its range, we try to backfill just
# those missing quarters from the other sources in the documented order.
# This preserves SEC as the authoritative source for Qs it has filed, while
# recovering history that SEC didn't include (e.g. pre-IPO restatements,
# revised filings, or XBRL concept gaps for older filings).
#
# QuarterChart.com is deliberately excluded from this chain — it's reserved
# for derived panels (expense ratios, per-share, EBITDA, income breakdown).

# Finnhub friendly-name map — same output column names as SEC/FMP/yfinance.
_FINNHUB_INCOME_MAP: Dict[str, List[str]] = {
    "Revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "Cost Of Revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold",
                         "CostOfGoodsSold"],
    "Gross Profit": ["GrossProfit"],
    "Operating Expenses": ["OperatingExpenses"],
    "Operating Income": ["OperatingIncomeLoss"],
    "R&D Expenses": ["ResearchAndDevelopmentExpense"],
    "SGA Expenses": ["SellingGeneralAndAdministrativeExpense"],
    "Net Income": ["NetIncomeLoss"],
    "Interest Expense": ["InterestExpense"],
    "Income Tax Expense": ["IncomeTaxExpenseBenefit"],
    "Pretax Income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "Basic EPS": ["EarningsPerShareBasic"],
    "Diluted EPS": ["EarningsPerShareDiluted"],
    "Basic Average Shares": ["WeightedAverageNumberOfSharesOutstandingBasic"],
    "Diluted Average Shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}
_FINNHUB_BS_MAP: Dict[str, List[str]] = {
    "Total Assets": ["Assets"],
    "Current Assets": ["AssetsCurrent"],
    "Non-Current Assets": ["AssetsNoncurrent"],
    "Total Liabilities": ["Liabilities"],
    "Current Liabilities": ["LiabilitiesCurrent"],
    "Non-Current Liabilities": ["LiabilitiesNoncurrent"],
    "Stockholders Equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "Cash and Cash Equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
        "Cash",
    ],
    "Long Term Debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "Total Debt": ["LongTermDebtAndCapitalLeaseObligations", "DebtCurrent"],
}
_FINNHUB_CF_MAP: Dict[str, List[str]] = {
    "Operating CF": ["NetCashProvidedByUsedInOperatingActivities"],
    "Investing CF": ["NetCashProvidedByUsedInInvestingActivities"],
    "Financing CF": ["NetCashProvidedByUsedInFinancingActivities"],
    "CapEx": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "Stock Based Compensation": [
        "ShareBasedCompensation", "AllocatedShareBasedCompensationExpense",
    ],
    "D&A": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization", "Depreciation",
    ],
}


def _finnhub_fetch_statement(ticker: str, statement: str) -> pd.DataFrame:
    """Fetch a single Finnhub quarterly statement (income/balance/cashflow).

    Returns a DataFrame with fiscal-calendar labels ("Q1 2024") and friendly
    column names aligned with SEC/FMP/yfinance output.
    """
    section_map = {"income": "ic", "balance": "bs", "cashflow": "cf"}
    field_map_map = {
        "income": _FINNHUB_INCOME_MAP,
        "balance": _FINNHUB_BS_MAP,
        "cashflow": _FINNHUB_CF_MAP,
    }
    if statement not in section_map:
        return pd.DataFrame()
    try:
        token = _finnhub_key()
        if not token:
            return pd.DataFrame()
        r = _requests.get(
            "https://finnhub.io/api/v1/stock/financials-reported",
            params={"symbol": ticker.upper(), "freq": "quarterly", "token": token},
            timeout=15,
        )
        if r.status_code != 200:
            return pd.DataFrame()
        data = (r.json() or {}).get("data", []) or []
    except Exception as exc:
        print(f"[Finnhub] financials-reported/{ticker}: {exc}")
        return pd.DataFrame()
    if not data:
        return pd.DataFrame()
    section = section_map[statement]
    field_map = field_map_map[statement]
    rows: Dict[str, Dict[str, float]] = {}
    for rec in data:
        q, y = rec.get("quarter"), rec.get("year")
        if not (q and y):
            continue
        try:
            q_i, y_i = int(q), int(y)
        except Exception:
            continue
        # Finnhub publishes Q0 for annual summaries — skip those for quarterly.
        if q_i == 0:
            continue
        label = f"Q{q_i} {y_i}"
        report = (rec.get("report") or {}).get(section, []) or []
        if not isinstance(report, list):
            continue
        row: Dict[str, float] = {}
        for item in report:
            concept = str(item.get("concept", ""))
            # Strip namespace prefixes ("us-gaap:" or "us-gaap_")
            concept = concept.split(":")[-1].replace("us-gaap_", "")
            try:
                val = float(item.get("value"))
            except Exception:
                continue
            for out_name, cands in field_map.items():
                if concept in cands and out_name not in row:
                    row[out_name] = val
        if row:
            # Prefer the first entry for a label (Finnhub may include amended
            # filings; the first record is the most recent in API order).
            if label not in rows:
                rows[label] = row
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = "Period"
    df = _sort_df_chronological(df)
    return df


def _enumerate_expected_qs(labels) -> List[str]:
    """Given an iterable of "Q# YYYY" labels, return the full continuous
    quarterly sequence from earliest to latest (inclusive).  Non-quarterly
    labels are ignored.
    """
    tuples: List[Tuple[int, int]] = []
    for lbl in labels:
        try:
            parts = str(lbl).strip().split()
            if (len(parts) == 2 and parts[0].startswith("Q")
                    and parts[0][1:].isdigit() and parts[1].isdigit()):
                tuples.append((int(parts[1]), int(parts[0][1:])))
        except Exception:
            continue
    if not tuples:
        return []
    tuples.sort()
    (y0, q0), (y1, q1) = tuples[0], tuples[-1]
    out: List[str] = []
    y, q = y0, q0
    while (y, q) <= (y1, q1):
        out.append(f"Q{q} {y}")
        q += 1
        if q > 4:
            q = 1
            y += 1
    return out


def _fetch_source_quarterly(ticker: str, statement: str, source: str) -> pd.DataFrame:
    """Dispatch to a single non-SEC source for a single quarterly statement.

    Returns a DataFrame indexed by "Q# YYYY" calendar-quarter labels with
    friendly column names aligned with SEC output.  Empty DataFrame if the
    source is unavailable or returns no data.
    """
    try:
        if source == "fmp":
            if not _fmp_available():
                return pd.DataFrame()
            endpoint_map = {
                "income":   ("income-statement",        _FMP_INCOME_MAP),
                "balance":  ("balance-sheet-statement", _FMP_BS_MAP),
                "cashflow": ("cash-flow-statement",     _FMP_CF_MAP),
            }
            endpoint, fmap = endpoint_map[statement]
            data = _fetch_fmp_statement(ticker, endpoint, limit=40, quarterly=True)
            if not isinstance(data, list) or not data:
                return pd.DataFrame()
            return _fmp_json_to_df(data, fmap, quarterly=True)
        elif source == "finnhub":
            return _finnhub_fetch_statement(ticker, statement)
        elif source == "yfinance":
            stock = yf.Ticker(ticker)
            raw_attr_map = {
                "income":   ("financials",    "quarterly_income_stmt",   _INCOME_MAP),
                "balance":  ("balance-sheet", "quarterly_balance_sheet", _BS_MAP),
                "cashflow": ("cash-flow",     "quarterly_cashflow",      _CF_MAP),
            }
            api_name, attr, fmap = raw_attr_map[statement]
            raw = _fetch_extended_quarterly_raw(ticker, api_name)
            if raw is None or raw.empty:
                raw = getattr(stock, attr, None)
            if raw is None or raw.empty:
                return pd.DataFrame()
            return _build_period_df(raw, fmap, quarterly=True)
    except Exception as exc:
        print(f"[gap-fill:{source}] {ticker}/{statement}: {exc}")
    return pd.DataFrame()


def _gap_fill_quarterly(primary_df: pd.DataFrame, ticker: str, statement: str,
                         primary: str = "sec") -> pd.DataFrame:
    """Backfill missing quarters in `primary_df` from the remaining sources
    in order: FMP → Finnhub → yfinance (skipping whichever source was primary).

    Only fills gaps WITHIN the existing range (min Q to max Q); does not
    forward-fill future quarters the primary hasn't published yet.
    """
    if primary_df is None or primary_df.empty:
        return primary_df
    expected = _enumerate_expected_qs(primary_df.index)
    if not expected:
        return primary_df
    have = set(primary_df.index)
    missing = [q for q in expected if q not in have]
    if not missing:
        return primary_df

    source_order = [s for s in ("fmp", "finnhub", "yfinance") if s != primary]
    merged = primary_df.copy()
    for src_name in source_order:
        if not missing:
            break
        src_df = _fetch_source_quarterly(ticker, statement, src_name)
        if src_df is None or src_df.empty:
            continue
        fillable = [q for q in missing if q in src_df.index]
        if not fillable:
            continue
        cols_in_both = [c for c in merged.columns if c in src_df.columns]
        if not cols_in_both:
            continue
        # Build rows aligned to merged's columns (NaN for missing cols)
        add = pd.DataFrame(index=fillable, columns=merged.columns, dtype=float)
        for c in cols_in_both:
            add[c] = src_df.loc[fillable, c]
        # Preserve any non-numeric columns by leaving them as NaN.
        merged = pd.concat([merged, add], axis=0)
        for q in fillable:
            missing.remove(q)
        print(f"[gap-fill:{src_name}] {ticker}/{statement}: filled {len(fillable)} Qs "
              f"({fillable[0]} … {fillable[-1]})")

    return _sort_df_chronological(merged)


# ---------------------------------------------------------------------------
# Income Statement
# ---------------------------------------------------------------------------

_INCOME_MAP: Dict[str, List[str]] = {
    "Revenue": ["Total Revenue", "Operating Revenue", "Revenue"],
    "Cost Of Revenue": ["Cost Of Revenue", "CostOfRevenue"],
    "Gross Profit": ["Gross Profit", "GrossProfit"],
    "Operating Income": ["Operating Income", "OperatingIncome", "Operating Expense"],
    "Net Income": ["Net Income", "NetIncome", "Net Income Common Stockholders"],
    "EBITDA": ["EBITDA", "Ebitda", "Normalized EBITDA"],
    "R&D Expenses": [
        "Research And Development",
        "Research Development",
        "ResearchAndDevelopment",
    ],
    "SGA Expenses": [
        "Selling General And Administration",
        "Selling General and Administrative",
        "SellingGeneralAndAdministration",
    ],
    "Operating Expenses": ["Operating Expense", "Total Operating Expenses", "Operating Expenses"],
    "Interest Expense": ["Interest Expense", "InterestExpense", "Net Interest Income"],
    "Income Tax Expense": ["Tax Provision", "IncomeTaxExpense", "Income Tax Expense"],
    "Pretax Income": ["Pretax Income", "PretaxIncome", "Income Before Tax"],
    "Basic EPS": ["Basic EPS", "BasicEPS"],
    "Diluted EPS": ["Diluted EPS", "DilutedEPS"],
    "Basic Average Shares": [
        "Basic Average Shares",
        "BasicAverageShares",
        "Diluted Average Shares",
    ],
    "Diluted Average Shares": [
        "Diluted Average Shares",
        "DilutedAverageShares",
    ],
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_income_statement(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Return a chart-ready income statement DataFrame (period x metrics). v2"""
    # 1) SEC EDGAR (free, no API key, authoritative SEC data, 20+ quarters)
    try:
        df = _sec_get_income_statement(ticker, quarterly=quarterly)
        if not df.empty and len(df) >= 4:
            print(f"[SEC] income-statement/{ticker}: {len(df)} periods")
            if quarterly:
                df = _gap_fill_quarterly(df, ticker, "income", primary="sec")
            return df
    except Exception as exc:
        print(f"[SEC] income-statement/{ticker} error: {exc}")

    # 2) FMP (free tier, 250 calls/day, 20+ quarters)
    if _fmp_available():
        try:
            fmp_data = _fetch_fmp_statement(ticker, "income-statement", limit=20, quarterly=quarterly)
            if isinstance(fmp_data, list) and fmp_data:
                df = _fmp_json_to_df(fmp_data, _FMP_INCOME_MAP, quarterly=quarterly)
                if not df.empty:
                    if quarterly:
                        df = _gap_fill_quarterly(df, ticker, "income", primary="fmp")
                    return df
        except Exception as exc:
            print(f"[FMP] income-statement fallback: {exc}")

    # 3) yfinance fallback
    try:
        stock = yf.Ticker(ticker)
        if quarterly:
            raw = _fetch_extended_quarterly_raw(ticker, "financials")
            if raw is None or raw.empty:
                raw = getattr(stock, "quarterly_income_stmt", None)
                if raw is None or raw.empty:
                    raw = stock.quarterly_financials
        else:
            raw = getattr(stock, "income_stmt", None)
            if raw is None or raw.empty:
                raw = stock.financials
        df = _build_period_df(raw, _INCOME_MAP, quarterly=quarterly)
        if quarterly and df is not None and not df.empty:
            df = _gap_fill_quarterly(df, ticker, "income", primary="yfinance")
        return df
    except Exception as exc:
        print(f"[data_fetcher] get_income_statement({ticker}): {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Balance Sheet
# ---------------------------------------------------------------------------

_BS_MAP: Dict[str, List[str]] = {
    "Total Assets": ["Total Assets", "TotalAssets"],
    "Current Assets": ["Current Assets", "CurrentAssets", "Total Current Assets"],
    "Non-Current Assets": [
        "Total Non Current Assets",
        "Non Current Assets",
        "NonCurrentAssets",
    ],
    "Total Liabilities": [
        "Total Liabilities Net Minority Interest",
        "Total Liabilities",
        "TotalLiabilities",
    ],
    "Current Liabilities": ["Current Liabilities", "CurrentLiabilities", "Total Current Liabilities"],
    "Non-Current Liabilities": [
        "Total Non Current Liabilities Net Minority Interest",
        "Non Current Liabilities",
        "NonCurrentLiabilities",
    ],
    "Stockholders Equity": [
        "Stockholders Equity",
        "Total Stockholder Equity",
        "StockholdersEquity",
        "Total Equity Gross Minority Interest",
    ],
    "Cash and Cash Equivalents": [
        "Cash And Cash Equivalents",
        "Cash And Cash Equivalents And Short Term Investments",
        "CashAndCashEquivalents",
    ],
    "Total Debt": ["Total Debt", "TotalDebt", "Net Debt"],
    "Long Term Debt": ["Long Term Debt", "LongTermDebt", "Long Term Debt And Capital Lease Obligation"],
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_balance_sheet(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Return a chart-ready balance sheet DataFrame (period × metrics).

    Data source priority: SEC EDGAR → FMP → yfinance.
    """
    # 1) SEC EDGAR
    try:
        df = _sec_get_balance_sheet(ticker, quarterly=quarterly)
        if not df.empty and len(df) >= 4:
            print(f"[SEC] balance-sheet/{ticker}: {len(df)} periods")
            if quarterly:
                df = _gap_fill_quarterly(df, ticker, "balance", primary="sec")
            return df
    except Exception as exc:
        print(f"[SEC] balance-sheet/{ticker} error: {exc}")

    # 2) FMP
    if _fmp_available():
        try:
            fmp_data = _fetch_fmp_statement(ticker, "balance-sheet-statement", limit=20, quarterly=quarterly)
            if isinstance(fmp_data, list) and fmp_data:
                df = _fmp_json_to_df(fmp_data, _FMP_BS_MAP, quarterly=quarterly)
                if not df.empty:
                    if quarterly:
                        df = _gap_fill_quarterly(df, ticker, "balance", primary="fmp")
                    return df
        except Exception as exc:
            print(f"[FMP] balance-sheet fallback: {exc}")

    # 3) yfinance fallback
    try:
        stock = yf.Ticker(ticker)
        if quarterly:
            raw = _fetch_extended_quarterly_raw(ticker, "balance-sheet")
            if raw is None or raw.empty:
                raw = getattr(stock, "quarterly_balance_sheet", None)
        else:
            raw = getattr(stock, "balance_sheet", None)
        if raw is None or raw.empty:
            raw = pd.DataFrame()
        df = _build_period_df(raw, _BS_MAP, quarterly=quarterly)
        if quarterly and df is not None and not df.empty:
            df = _gap_fill_quarterly(df, ticker, "balance", primary="yfinance")
        return df
    except Exception as exc:
        print(f"[data_fetcher] get_balance_sheet({ticker}): {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Cash Flow
# ---------------------------------------------------------------------------

_CF_MAP: Dict[str, List[str]] = {
    "Operating CF": ["Operating Cash Flow", "OperatingCashFlow", "Total Cash From Operating Activities"],
    "Investing CF": [
        "Investing Activities",
        "Cash Flow From Continuing Investing Activities",
        "Investing Cash Flow",
        "Total Cashflows From Investing Activities",
    ],
    "Financing CF": [
        "Financing Activities",
        "Cash Flow From Continuing Financing Activities",
        "Financing Cash Flow",
        "Total Cash From Financing Activities",
    ],
    "Free CF": ["Free Cash Flow", "FreeCashFlow"],
    "CapEx": ["Capital Expenditure", "Capital Expenditures", "CapitalExpenditure"],
    "Stock Based Compensation": [
        "Stock Based Compensation",
        "StockBasedCompensation",
    ],
    "D&A": [
        "Depreciation And Amortization",
        "DepreciationAndAmortization",
        "Depreciation Amortization And Accretion",
        "Depreciation",
    ],
    "Cash and Cash Equivalents": [
        "Changes In Cash",
        "Change In Cash Supplemental As Reported",
        "Net Change in Cash",
    ],
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_cash_flow(ticker: str, quarterly: bool = True) -> pd.DataFrame:
    """Return a chart-ready cash flow DataFrame (period × metrics).

    Data source priority: SEC EDGAR → FMP → yfinance.
    """
    # 1) SEC EDGAR
    #
    # Task #34 (2026-04-21): removed the previous sparse-quarter filter
    # (`_has_recent and _has_all_q`). That filter was dropping SEC data
    # for tickers like AAPL whose 2008–2010 cash-flow XBRL has missing
    # Q1/Q3 rows — the check rejected the entire frame instead of
    # accepting the quarters that ARE present and letting
    # `_gap_fill_quarterly` backfill the holes from Finnhub/yfinance.
    # Keeping the behavior symmetric with `get_income_statement` and
    # `get_balance_sheet`, which accept any non-empty SEC frame with
    # ≥4 periods and rely on gap-fill to patch the gaps.
    try:
        df = _sec_get_cash_flow(ticker, quarterly=quarterly)
        if not df.empty and len(df) >= 4:
            print(f"[SEC] cash-flow/{ticker}: {len(df)} periods")
            if quarterly:
                df = _gap_fill_quarterly(df, ticker, "cashflow", primary="sec")
            return df
    except Exception as exc:
        print(f"[SEC] cash-flow/{ticker} error: {exc}")

    # 2) FMP
    if _fmp_available():
        try:
            fmp_data = _fetch_fmp_statement(ticker, "cash-flow-statement", limit=20, quarterly=quarterly)
            if isinstance(fmp_data, list) and fmp_data:
                df = _fmp_json_to_df(fmp_data, _FMP_CF_MAP, quarterly=quarterly)
                if not df.empty:
                    if quarterly:
                        df = _gap_fill_quarterly(df, ticker, "cashflow", primary="fmp")
                    return df
        except Exception as exc:
            print(f"[FMP] cash-flow fallback: {exc}")

    # 3) yfinance fallback
    try:
        stock = yf.Ticker(ticker)
        if quarterly:
            raw = _fetch_extended_quarterly_raw(ticker, "cash-flow")
            if raw is None or raw.empty:
                raw = getattr(stock, "quarterly_cashflow", None)
        else:
            raw = getattr(stock, "cashflow", None)
        if raw is None or raw.empty:
            raw = pd.DataFrame()
        df = _build_period_df(raw, _CF_MAP, quarterly=quarterly)
        if quarterly and df is not None and not df.empty:
            df = _gap_fill_quarterly(df, ticker, "cashflow", primary="yfinance")
        return df
    except Exception as exc:
        print(f"[data_fetcher] get_cash_flow({ticker}): {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Derived metric helpers (computed from the fetched statements)
# ---------------------------------------------------------------------------

def compute_margins(income_df: pd.DataFrame) -> pd.DataFrame:
    """Compute margin percentages from the income statement DataFrame."""
    if income_df.empty or "Revenue" not in income_df.columns:
        return pd.DataFrame()
    out = pd.DataFrame(index=income_df.index)
    rev = income_df["Revenue"].replace(0, np.nan)
    if "Gross Profit" in income_df.columns:
        out["Gross Margin %"] = (income_df["Gross Profit"] / rev * 100).round(2)
    if "Operating Income" in income_df.columns:
        out["Operating Margin %"] = (income_df["Operating Income"] / rev * 100).round(2)
    if "Net Income" in income_df.columns:
        out["Net Margin %"] = (income_df["Net Income"] / rev * 100).round(2)
    return out


def compute_eps(income_df: pd.DataFrame, info: Dict[str, Any]) -> pd.DataFrame:
    """Compute EPS series – both Basic and Diluted when available."""
    if income_df.empty:
        return pd.DataFrame()
    out = pd.DataFrame(index=income_df.index)
    if "Basic EPS" in income_df.columns:
        out["EPS"] = income_df["Basic EPS"]
    elif "Net Income" in income_df.columns and info.get("shares_outstanding"):
        out["EPS"] = income_df["Net Income"] / info["shares_outstanding"]
    if "Diluted EPS" in income_df.columns:
        out["EPS Diluted"] = income_df["Diluted EPS"]
    return out


def compute_revenue_yoy(income_df: pd.DataFrame, periods: int = 4) -> pd.DataFrame:
    """Compute revenue growth vs `periods` rows earlier.

    Default periods=4 — for quarterly data, 4 rows back = 1 year (YoY).
    For annual data (labels like "2024"), pass periods=1.
    """
    if income_df.empty or "Revenue" not in income_df.columns:
        return pd.DataFrame()
    rev = income_df["Revenue"]
    if len(rev) <= periods:
        # Not enough history for requested lag — fall back to 1-step change
        yoy = rev.pct_change() * 100
    else:
        yoy = rev.pct_change(periods=periods) * 100
    out = pd.DataFrame({"Revenue YoY Growth %": yoy.round(2)}, index=income_df.index)
    return out.dropna()


def compute_per_share(
    income_df: pd.DataFrame,
    cf_df: pd.DataFrame,
    fallback_shares: Optional[float] = None,
) -> pd.DataFrame:
    """Compute per-share metrics using per-period share counts.

    Root fix: prefers the ``Diluted Average Shares`` column (or ``Basic Average
    Shares`` fallback) from ``income_df``, which gives the correct share count
    FOR THAT PERIOD. Older behavior divided every historical flow by today's
    shares outstanding, which distorted historical Revenue/share & NI/share
    whenever the share count had changed materially (buybacks, issuances).

    If the income DataFrame has no per-period shares column, falls back to the
    spot ``fallback_shares`` value so behavior degrades gracefully.
    """
    if income_df.empty:
        return pd.DataFrame()

    # Per-period shares (prefer Diluted)
    shares_series: Optional[pd.Series] = None
    for col in ("Diluted Average Shares", "Basic Average Shares"):
        if col in income_df.columns:
            s = pd.to_numeric(income_df[col], errors="coerce").replace(0, np.nan)
            if s.notna().sum() > 0:
                shares_series = s
                break

    has_spot = fallback_shares is not None and fallback_shares != 0
    if shares_series is None and not has_spot:
        return pd.DataFrame()

    def _per_share(numer: pd.Series) -> pd.Series:
        """Divide numer by per-period shares where available, spot shares otherwise."""
        if shares_series is not None:
            denom = shares_series.reindex(numer.index)
            result = numer / denom
            if has_spot:
                # Fill NaN rows where per-period shares were missing
                result = result.where(result.notna(), numer / fallback_shares)
            return result
        return numer / fallback_shares

    out = pd.DataFrame(index=income_df.index)
    if "Revenue" in income_df.columns:
        out["Revenue Per Share"] = _per_share(income_df["Revenue"]).round(4)
    if "Net Income" in income_df.columns:
        out["Net Income Per Share"] = _per_share(income_df["Net Income"]).round(4)
    if not cf_df.empty and "Operating CF" in cf_df.columns:
        common = out.index.intersection(cf_df.index)
        if len(common):
            # Align per-period shares onto cf_df rows for the intersection
            if shares_series is not None:
                denom = shares_series.reindex(common)
                res = cf_df.loc[common, "Operating CF"] / denom
                if has_spot:
                    res = res.where(res.notna(),
                                    cf_df.loc[common, "Operating CF"] / fallback_shares)
            else:
                res = cf_df.loc[common, "Operating CF"] / fallback_shares
            out.loc[common, "Operating Cash Flow Per Share"] = res.round(4)
    return out


def compute_qoq_revenue(income_df: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
    """Compute revenue growth vs the previous period.

    Default periods=1 — for quarterly data that's Q-over-Q. For annual data,
    QoQ is semantically identical to YoY (pct_change(1)); callers may prefer
    to hide this panel entirely in Annual mode.
    """
    if income_df.empty or "Revenue" not in income_df.columns:
        return pd.DataFrame()
    rev = income_df["Revenue"]
    qoq = rev.pct_change(periods=periods) * 100
    out = pd.DataFrame({"QoQ Revenue Growth %": qoq.round(2)}, index=income_df.index)
    return out.dropna()


def compute_expense_ratios(income_df: pd.DataFrame, cf_df: pd.DataFrame) -> pd.DataFrame:
    """Compute expense-to-revenue ratios: R&D/Rev, Capex/Rev, SBC/Rev."""
    if income_df.empty or "Revenue" not in income_df.columns:
        return pd.DataFrame()
    out = pd.DataFrame(index=income_df.index)
    rev = income_df["Revenue"].replace(0, np.nan)
    if "R&D Expenses" in income_df.columns:
        out["R&D to Revenue"] = (income_df["R&D Expenses"] / rev).round(4)
    # Align cash-flow data with income index (strip whitespace for safety)
    cf_aligned = cf_df.copy()
    if cf_aligned.index.dtype == "object":
        cf_aligned.index = cf_aligned.index.str.strip()
    else:
        cf_aligned.index = cf_aligned.index.astype(str).str.strip()
    if income_df.index.dtype == "object":
        inc_idx_stripped = income_df.index.str.strip()
    else:
        inc_idx_stripped = income_df.index.astype(str).str.strip()
    # Capex to Revenue (from cash flow statement)
    if "CapEx" in cf_aligned.columns:
        capex_series = cf_aligned["CapEx"].abs()
        capex_mapped = pd.Series(
            [capex_series.get(lbl, np.nan) for lbl in inc_idx_stripped],
            index=income_df.index,
        )
        out["Capex to Revenue"] = (capex_mapped / rev).round(4)
    # SBC to Revenue
    if "Stock Based Compensation" in cf_aligned.columns:
        sbc_series = cf_aligned["Stock Based Compensation"]
        sbc_mapped = pd.Series(
            [sbc_series.get(lbl, np.nan) for lbl in inc_idx_stripped],
            index=income_df.index,
        )
        out["SBC to Revenue"] = (sbc_mapped / rev).round(4)
    elif "Stock Based Compensation" in income_df.columns:
        out["SBC to Revenue"] = (income_df["Stock Based Compensation"] / rev).round(4)
    return out


def compute_ebitda(income_df: pd.DataFrame, cf_df: pd.DataFrame) -> pd.DataFrame:
    """Compute EBITDA = Operating Income + D&A.  Falls back to income_df['EBITDA'] if present."""
    if "EBITDA" in income_df.columns:
        return income_df[["EBITDA"]].dropna()
    if income_df.empty or "Operating Income" not in income_df.columns:
        return pd.DataFrame()
    if cf_df.empty or "D&A" not in cf_df.columns:
        return pd.DataFrame()
    # Align D&A from cash flow to income index
    cf_aligned = cf_df.copy()
    if cf_aligned.index.dtype == "object":
        cf_aligned.index = cf_aligned.index.str.strip()
    else:
        cf_aligned.index = cf_aligned.index.astype(str).str.strip()
    if income_df.index.dtype == "object":
        inc_idx_stripped = income_df.index.str.strip()
    else:
        inc_idx_stripped = income_df.index.astype(str).str.strip()
    da_series = cf_aligned["D&A"].abs()
    da_mapped = pd.Series(
        [da_series.get(lbl, np.nan) for lbl in inc_idx_stripped],
        index=income_df.index,
    )
    ebitda = income_df["Operating Income"] + da_mapped
    out = pd.DataFrame({"EBITDA": ebitda}, index=income_df.index)
    return out.dropna()


def compute_income_breakdown(income_df: pd.DataFrame) -> pd.DataFrame:
    """Build a waterfall-ready DataFrame (Revenue → Net Income) from an income
    statement. Used as a LOCAL fallback when QuarterChart's income-breakdown
    feed is unavailable.

    Columns returned (in order; any missing source columns are simply omitted):
        Revenue, Cost of Revenue, Gross Profit, Operating Expenses,
        Operating Income, Net Income
    """
    if income_df.empty or "Revenue" not in income_df.columns:
        return pd.DataFrame()
    col_map = [
        ("Revenue", "Revenue"),
        ("Cost Of Revenue", "Cost of Revenue"),
        ("Gross Profit", "Gross Profit"),
        ("Operating Expenses", "Operating Expenses"),
        ("Operating Income", "Operating Income"),
        ("Net Income", "Net Income"),
    ]
    out = pd.DataFrame(index=income_df.index)
    for src, dst in col_map:
        if src in income_df.columns:
            out[dst] = income_df[src]
    # Drop rows that are entirely NaN
    out = out.dropna(how="all")
    return out


def compute_effective_tax_rate(income_df: pd.DataFrame) -> pd.DataFrame:
    """Compute effective tax rate % from income tax expense and pretax income."""
    if income_df.empty:
        return pd.DataFrame()
    tax_col = "Income Tax Expense" if "Income Tax Expense" in income_df.columns else None
    pretax_col = "Pretax Income" if "Pretax Income" in income_df.columns else None
    if tax_col is None or pretax_col is None:
        return pd.DataFrame()
    pretax = income_df[pretax_col].replace(0, np.nan)
    rate = (income_df[tax_col] / pretax * 100).round(2)
    out = pd.DataFrame({"Effective Tax Rate %": rate}, index=income_df.index)
    return out.dropna()


# ---------------------------------------------------------------------------
# Analyst Forecast
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def get_analyst_forecast(ticker: str) -> Dict[str, Any]:
    """Fetch analyst price targets, recommendations and earnings estimates."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        forecast: Dict[str, Any] = {
            "target_mean": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "target_median": info.get("targetMedianPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "recommendation": info.get("recommendationKey"),
            "recommendation_mean": info.get("recommendationMean"),
            "current_price": info.get("regularMarketPrice") or info.get("currentPrice"),
        }
        if forecast["target_mean"] and forecast["current_price"]:
            forecast["upside_pct"] = round(
                (forecast["target_mean"] - forecast["current_price"])
                / forecast["current_price"]
                * 100,
                2,
            )
        # Earnings estimates
        try:
            ee = stock.earnings_estimate
            if ee is not None and not ee.empty:
                forecast["earnings_estimate"] = ee.to_dict()
        except Exception:
            pass
        try:
            re = stock.revenue_estimate
            if re is not None and not re.empty:
                forecast["revenue_estimate"] = re.to_dict()
        except Exception:
            pass
        return {k: v for k, v in forecast.items() if v is not None}
    except Exception as exc:
        print(f"[data_fetcher] get_analyst_forecast({ticker}): {exc}")
        return {}


# ---------------------------------------------------------------------------
# Ticker validation
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def validate_ticker(ticker: str) -> bool:
    """Check whether *ticker* is a real US-listed equity.

    Priority: SEC EDGAR ticker map (authoritative, cached locally, no rate
    limits) → Yahoo Finance (fallback for foreign / ADR tickers SEC may not
    have). yfinance alone is too flaky for the landing-page validator: it
    rate-limits easily, returns partial dicts missing `regularMarketPrice`,
    and mishandles dot-tickers (e.g. `BRK.B` returns 404 while `BRK-B`
    works). SEC fixes all of those because `_sec_get_cik` already
    normalizes dot→hyphen (commit 60692dd, Task #26).
    """
    if not ticker:
        return False
    # 1) SEC EDGAR — cached company_tickers.json. Handles BRK.B, BF.B, etc.
    try:
        if _sec_get_cik(ticker) is not None:
            return True
    except Exception:
        pass
    # 2) yfinance fallback — for foreign/ADR tickers SEC doesn't list.
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return bool(info and ("regularMarketPrice" in info or "currentPrice" in info))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Fiscal Calendar helper
# ---------------------------------------------------------------------------

_MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _build_quarter_month_ranges(fy_end: int) -> list:
    """Given FY end month (1-12), return [(start_m, end_m)] for Q1-Q4."""
    q_starts = []
    for qi in range(4):
        start_m = (fy_end % 12) + 1 + qi * 3
        while start_m > 12:
            start_m -= 12
        end_m = start_m + 2
        while end_m > 12:
            end_m -= 12
        q_starts.append((start_m, end_m))
    return q_starts


@st.cache_data(ttl=7200, show_spinner=False)
def get_fiscal_calendar(ticker: str) -> dict:
    """
    Return fiscal-year calendar info for a ticker.

    Uses three data sources in priority order:
      1. FMP quarterly income-statement (has period, calendarYear, fillingDate)
      2. yfinance quarterly_income_stmt (has period-end dates)
      3. yfinance info.lastFiscalYearEnd (FY end month only)

    Always returns at least Q1-Q4 month ranges. Filing/period dates
    are included when available from FMP.
    """
    _FULL_MONTHS = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    result = {
        "fy_end_month": 12,
        "fy_end_label": "December",
        "quarters": [],
    }

    # ── Step 1: Get FY end month (yfinance is fast, cached 24h) ──
    fy_end = _get_fy_end_month(ticker)
    result["fy_end_month"] = fy_end
    result["fy_end_label"] = _FULL_MONTHS[fy_end]

    # ── Step 2: Build Q1-Q4 month ranges ──
    q_ranges = _build_quarter_month_ranges(fy_end)

    # ── Step 3: Try FMP for rich quarter data (period, fillingDate, calendarYear) ──
    fmp_ok = False
    if _fmp_available():
        try:
            raw = _fetch_fmp_statement(ticker, "income-statement", limit=8, quarterly=True)
            if isinstance(raw, list) and raw:
                raw = sorted(raw, key=lambda x: x.get("date", ""), reverse=True)

                # Refine FY end month from actual Q4 record if available
                for item in raw:
                    if item.get("period") == "Q4":
                        q4_date = item.get("date", "")
                        if q4_date:
                            try:
                                fy_end = pd.Timestamp(q4_date).month
                                result["fy_end_month"] = fy_end
                                result["fy_end_label"] = _FULL_MONTHS[fy_end]
                                q_ranges = _build_quarter_month_ranges(fy_end)
                            except Exception:
                                pass
                        break

                for item in raw[:8]:
                    period = item.get("period", "")
                    if not period or not period.startswith("Q"):
                        continue
                    cal_year = item.get("calendarYear", "")
                    date_str = item.get("date", "")
                    filling = item.get("fillingDate", "") or item.get("acceptedDate", "")
                    qi = int(period[1]) - 1
                    start_m, end_m = q_ranges[qi] if qi < len(q_ranges) else (0, 0)
                    months_str = f"{_MONTH_NAMES[start_m]} – {_MONTH_NAMES[end_m]}" if start_m else ""

                    result["quarters"].append({
                        "quarter": period,
                        "months": months_str,
                        "period_end": date_str,
                        "filing_date": filling,
                        "earnings_date": "",
                        "label": f"{period} FY{cal_year}" if cal_year else period,
                        "calendar_year": cal_year,
                    })
                if result["quarters"]:
                    fmp_ok = True
        except Exception as exc:
            print(f"[FiscalCal] FMP error for {ticker}: {exc}")

    # ── Step 4: Fallback — Finnhub earnings calendar (same source as Earnings page) ──
    # NOTE: Finnhub "date" = earnings report date, NOT period end date.
    if not fmp_ok:
        try:
            from datetime import date as _date, timedelta as _td
            _today = _date.today()
            _from = (_today - _td(days=730)).isoformat()
            _to = (_today + _td(days=180)).isoformat()
            _fh_resp = _requests.get(
                f"{_FINNHUB_BASE}/calendar/earnings",
                params={"symbol": ticker.upper(), "from": _from, "to": _to, "token": _finnhub_key()},
                timeout=10,
            )
            if _fh_resp.status_code == 200:
                _fh_data = _fh_resp.json().get("earningsCalendar", [])
                _fh_data.sort(key=lambda x: x.get("date", ""), reverse=True)
                _seen_labels = set()
                for it in _fh_data[:12]:
                    q = it.get("quarter")
                    yr = it.get("year")
                    dt_str = it.get("date", "")
                    if q is None or yr is None or not dt_str:
                        continue
                    label = f"Q{q} FY{yr}"
                    if label in _seen_labels:
                        continue
                    _seen_labels.add(label)
                    qi = int(q) - 1
                    start_m, end_m = q_ranges[qi] if qi < len(q_ranges) else (0, 0)
                    months_str = f"{_MONTH_NAMES[start_m]} – {_MONTH_NAMES[end_m]}" if start_m else ""
                    result["quarters"].append({
                        "quarter": f"Q{q}",
                        "months": months_str,
                        "period_end": "",  # Finnhub doesn't have period end
                        "filing_date": "",
                        "earnings_date": dt_str,  # This is the earnings report date
                        "label": label,
                        "calendar_year": str(yr),
                    })
                if result["quarters"]:
                    fmp_ok = True
        except Exception as exc:
            print(f"[FiscalCal] Finnhub fallback error for {ticker}: {exc}")

    # ── Step 5: Fallback — build quarters from yfinance quarterly data ──
    if not fmp_ok:
        try:
            stock = yf.Ticker(ticker)
            qf = getattr(stock, "quarterly_income_stmt", None)
            if qf is not None and not qf.empty:
                dates = sorted(qf.columns, reverse=True)[:8]
                for dt in dates:
                    ts = pd.Timestamp(dt)
                    month_offset = (ts.month - fy_end - 1) % 12
                    fq = month_offset // 3 + 1
                    fy_year = ts.year if ts.month <= fy_end or fy_end == 12 else ts.year + 1
                    if fy_end != 12 and fq <= (12 - fy_end) // 3:
                        fy_year = ts.year

                    qi = fq - 1
                    start_m, end_m = q_ranges[qi] if qi < len(q_ranges) else (0, 0)
                    months_str = f"{_MONTH_NAMES[start_m]} – {_MONTH_NAMES[end_m]}" if start_m else ""

                    result["quarters"].append({
                        "quarter": f"Q{fq}",
                        "months": months_str,
                        "period_end": ts.strftime("%Y-%m-%d"),
                        "filing_date": "",
                        "earnings_date": "",
                        "label": f"Q{fq} FY{fy_year}",
                        "calendar_year": str(ts.year),
                    })
        except Exception as exc:
            print(f"[FiscalCal] yfinance fallback error for {ticker}: {exc}")

    # ── Step 5: Absolute fallback — build Q1-Q4 ranges without specific dates ──
    if not result["quarters"]:
        cur_year = datetime.now().year
        for qi in range(4):
            fq = qi + 1
            start_m, end_m = q_ranges[qi]
            months_str = f"{_MONTH_NAMES[start_m]} – {_MONTH_NAMES[end_m]}" if start_m else ""
            result["quarters"].append({
                "quarter": f"Q{fq}",
                "months": months_str,
                "period_end": "",
                "filing_date": "",
                "earnings_date": "",
                "label": f"Q{fq} FY{cur_year}",
                "calendar_year": str(cur_year),
            })

    return result


# ---------------------------------------------------------------------------
# Next Earnings Date (Finnhub — same source as Earnings Calendar page)
# ---------------------------------------------------------------------------
_FINNHUB_BASE = "https://finnhub.io/api/v1"


def _finnhub_key() -> str:
    return _os.environ.get(
        "FINNHUB_API_KEY",
        "d77c5b1r01qp6afl34h0d77c5b1r01qp6afl34hg",
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_next_earnings(ticker: str) -> dict:
    """
    Fetch the next upcoming earnings date for a ticker from Finnhub.

    Same data source as the Earnings Calendar page.

    Returns dict with:
        date       : str  ("2026-05-28")
        quarter    : str  ("Q1")
        year       : str  ("2026")  — fiscal year
        event      : str  ("Q1 FY2026 Earnings")
        call_time  : str  ("AMC" / "BMO" / "TAS" / "TNS")
        eps_estimate: str
    Returns empty dict if no upcoming earnings found.
    """
    from datetime import date as _date, timedelta as _td

    today = _date.today()
    from_str = today.isoformat()
    to_str = (today + _td(days=120)).isoformat()

    try:
        resp = _requests.get(
            f"{_FINNHUB_BASE}/calendar/earnings",
            params={
                "symbol": ticker.upper(),
                "from": from_str,
                "to": to_str,
                "token": _finnhub_key(),
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("earningsCalendar", [])
            # Sort by date ascending, pick the first future one
            future = [
                it for it in items
                if it.get("date", "") >= from_str
            ]
            future.sort(key=lambda x: x.get("date", ""))
            if future:
                it = future[0]
                q = it.get("quarter", "?")
                yr = it.get("year", "")
                hour = (it.get("hour", "") or "").lower().strip()
                call_map = {"bmo": "BMO", "amc": "AMC", "dmh": "TAS"}
                return {
                    "date": it.get("date", ""),
                    "quarter": f"Q{q}" if q != "?" else "",
                    "year": str(yr),
                    "event": f"Q{q} FY{yr} Earnings" if q != "?" else "Earnings",
                    "call_time": call_map.get(hour, "TBD"),
                    "eps_estimate": it.get("epsEstimate"),
                }
    except Exception as exc:
        print(f"[NextEarnings] {ticker}: {exc}")

    return {}
