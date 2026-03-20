"""
Sankey diagram page – Income Statement & Balance Sheet visualizations.
Fixed-position nodes with vivid 11-color palette, KPI metric cards,
and Pretax Income waterfall matching QuarterCharts deployed style.
"""
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO 
import numpy as np
import requests

# ─── Demo / sample data for when Yahoo Finance is rate-limited ─────────────
def _get_demo_data(ticker: str):
    """Return hardcoded sample financial data so Sankey always renders."""
    # NVDA-like data (FY2025 approximate values in USD)
    demo_income = {
        "Total Revenue":                        [130497e6, 96307e6],
        "Cost Of Revenue":                      [29168e6,  22249e6],
        "Gross Profit":                         [101329e6, 74058e6],
        "Research And Development":             [12893e6,  8675e6],
        "Selling General And Administration":   [3362e6,   2654e6],
        "Reconciled Depreciation":              [1957e6,   1508e6],
        "Other Operating Expense":              [0,        0],
        "Operating Income":                     [83117e6,  61221e6],
        "Interest Expense":                     [246e6,    257e6],
        "Pretax Income":                        [85765e6,  63610e6],
        "Tax Provision":                        [11628e6,  8486e6],
        "Net Income":                           [72880e6,  55042e6],
    }
    demo_balance = {
        "Total Assets":                         [112198e6, 65728e6],
        "Current Assets":                       [68934e6,  44345e6],
        "Cash And Cash Equivalents":            [8495e6,   7280e6],
        "Total Non Current Assets":             [43264e6,  21383e6],
        "Net PPE":                              [5743e6,   3914e6],
        "Total Liabilities Net Minority Interest": [30085e6, 22017e6],
        "Current Liabilities":                  [17574e6,  10631e6],
        "Current Debt":                         [0,        0],
        "Long Term Debt":                       [8462e6,   8459e6],
        "Accounts Payable":                     [5353e6,   2642e6],
        "Stockholders Equity":                  [82113e6,  43711e6],
        "Retained Earnings":                    [68148e6,  29817e6],
    }
    cols = [pd.Timestamp("2025-01-26"), pd.Timestamp("2024-01-28")]
    income_df = pd.DataFrame(demo_income, index=["2025", "2024"]).T
    income_df.columns = cols
    balance_df = pd.DataFrame(demo_balance, index=["2025", "2024"]).T
    balance_df.columns = cols
    info = {"shortName": ticker.upper(), "longName": f"{ticker.upper()} Corporation"}
    return income_df, balance_df, info


# ─── Vivid 11-color palette (one per node) ────────────────────────────────
VIVID = [
    "#22c55e",  # 0  Revenue (green)
    "#ef4444",  # 1  COGS (red)
    "#3b82f6",  # 2  Gross Profit (blue)
    "#f59e0b",  # 3  R&D (amber)
    "#f97316",  # 4  SG&A (orange)
    "#a855f7",  # 5  D&A / Other OpEx (purple)
    "#06b6d4",  # 6  Operating Income (cyan)
    "#64748b",  # 7  Interest (slate)
    "#6366f1",  # 8  Pretax Income (indigo)
    "#ec4899",  # 9  Tax (pink)
    "#84cc16",  # 10 Net Income (lime)
]

# Balance Sheet palette
BS_COLORS = {
    "asset":     "#3b82f6",  # blue
    "asset2":    "#6366f1",  # indigo
    "liability": "#f97316",  # orange
    "equity":    "#22c55e",  # green
    "cash":      "#06b6d4",  # cyan
    "invest":    "#a855f7",  # purple
    "ppe":       "#8b5cf6",  # violet
    "debt":      "#ef4444",  # red
    "payable":   "#f59e0b",  # amber
    "retained":  "#14b8a6",  # teal
    "other":     "#64748b",  # slate
}


def _rgba(hex_color, alpha=0.42):
    """Convert hex to rgba string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _fmt(val):
    """Format a number as $XXB or $XXM."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    av = abs(val)
    if av >= 1e12:
        return f"${val/1e12:.1f}T"
    if av >= 1e9:
        return f"${val/1e9:.2f}B"
    if av >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


def _safe(df, key, default=0):
    """Safely extract a value from a yfinance DataFrame column."""
    if df is None or df.empty:
        return default
    for idx in df.index:
        name = str(idx)
        if key.lower() in name.lower():
            val = df.iloc[df.index.get_loc(idx), 0]
            if pd.notna(val):
                return float(val)
    return default


def _safe_prev(df, key, default=0):
    """Extract previous period value (column index 1) for YoY calc."""
    if df is None or df.empty or df.shape[1] < 2:
        return default
    for idx in df.index:
        name = str(idx)
        if key.lower() in name.lower():
            val = df.iloc[df.index.get_loc(idx), 1]
            if pd.notna(val):
                return float(val)
    return default


def _yoy(current, previous):
    """Calculate year-over-year percentage change."""
    if previous and previous != 0:
        return ((current - previous) / abs(previous)) * 100
    return None


def _yoy_delta(current, previous, label="YoY"):
    """Format YoY as delta string for st.metric."""
    pct = _yoy(current, previous)
    if pct is None:
        return None
    return f"{pct:+.1f}% {label}"


def _reorder_df_for_comparison(df, period_a, period_b, quarterly=False):
    """Reorder DataFrame columns so period_a is col 0, period_b is col 1."""
    if df is None or df.empty or df.shape[1] < 2:
        return df
    cols = list(df.columns)
    col_dates = []
    for c in cols:
        try:
            col_dates.append(pd.Timestamp(c))
        except Exception:
            col_dates.append(None)

    def _find(period_str):
        if quarterly:
            parts = period_str.split()
            q_num = int(parts[0][1])
            yr = int(parts[1])
            for i, d in enumerate(col_dates):
                if d and d.year == yr and ((d.month - 1) // 3 + 1) == q_num:
                    return i
        else:
            yr = int(period_str)
            for i, d in enumerate(col_dates):
                if d and d.year == yr:
                    return i
            for i, d in enumerate(col_dates):
                if d and d.year == yr + 1 and d.month <= 6:
                    return i
        return None

    idx_a = _find(period_a) if period_a else 0
    idx_b = _find(period_b) if period_b else 1
    if idx_a is None:
        idx_a = 0
    if idx_b is None:
        idx_b = 1 if idx_a != 1 else min(2, len(cols) - 1)
    if idx_a == idx_b:
        idx_b = (idx_a + 1) % len(cols)
    new_order = [idx_a, idx_b]
    for i in range(len(cols)):
        if i not in new_order:
            new_order.append(i)
    return df.iloc[:, new_order]


# ─── SEC EDGAR data source ──────────────────────────────────────────────────
_SEC_HEADERS = {
    "User-Agent": "QuarterCharts contact@quartercharts.com",
    "Accept-Encoding": "gzip, deflate",
}

# XBRL tag mappings: DataFrame row name → list of possible us-gaap tags (first match wins)
_XBRL_INCOME_TAGS = {
    "Total Revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "Cost Of Revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ],
    "Gross Profit": ["GrossProfit"],
    "Research And Development": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    ],
    "Selling General And Administration": [
        "SellingGeneralAndAdministrativeExpense",
    ],
    "Reconciled Depreciation": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
    ],
    "Other Operating Expenses": [
        "OtherOperatingIncomeExpenseNet",
        "OtherCostAndExpenseOperating",
    ],
    "Operating Income": [
        "OperatingIncomeLoss",
    ],
    "Interest Expense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestIncomeExpenseNonoperatingNet",
    ],
    "Pretax Income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "Tax Provision": [
        "IncomeTaxExpenseBenefit",
    ],
    "Net Income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
}

_XBRL_BALANCE_TAGS = {
    "Total Assets": ["Assets"],
    "Current Assets": ["AssetsCurrent"],
    "Cash And Cash Equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    "Other Short Term Investments": [
        "ShortTermInvestments",
        "AvailableForSaleSecuritiesCurrent",
        "MarketableSecuritiesCurrent",
    ],
    "Accounts Receivable": [
        "AccountsReceivableNetCurrent",
        "AccountsReceivableNet",
    ],
    "Inventory": [
        "InventoryNet",
    ],
    "Total Non Current Assets": [],  # Derived: Assets - AssetsCurrent
    "Net PPE": [
        "PropertyPlantAndEquipmentNet",
    ],
    "Goodwill": ["Goodwill"],
    "Other Intangible Assets": [
        "IntangibleAssetsNetExcludingGoodwill",
        "FiniteLivedIntangibleAssetsNet",
    ],
    "Investments And Advances": [
        "LongTermInvestments",
        "InvestmentsAndAdvances",
        "MarketableSecuritiesNoncurrent",
    ],
    "Total Liabilities Net Minority Interest": [
        "Liabilities",
    ],
    "Current Liabilities": ["LiabilitiesCurrent"],
    "Total Non Current Liabilities Net Minority Interest": [
        "LiabilitiesNoncurrent",
    ],
    "Accounts Payable": [
        "AccountsPayableCurrent",
    ],
    "Current Debt": [
        "DebtCurrent",
        "ShortTermBorrowings",
    ],
    "Current Deferred Revenue": [
        "DeferredRevenueCurrent",
        "ContractWithCustomerLiabilityCurrent",
    ],
    "Long Term Debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
    ],
    "Stockholders Equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "Retained Earnings": [
        "RetainedEarningsAccumulatedDeficit",
    ],
}


@st.cache_data(ttl=3600, show_spinner=False)
def _ticker_to_cik(ticker: str) -> str:
    """Convert stock ticker to SEC CIK number (zero-padded to 10 digits)."""
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=_SEC_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_edgar_facts(cik: str) -> dict:
    """Fetch CompanyFacts JSON from SEC EDGAR."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    resp = requests.get(url, headers=_SEC_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _edgar_build_df(facts: dict, tag_map: dict, form_filter: str = "10-K",
                    quarterly_income: bool = False) -> pd.DataFrame:
    """Build a yfinance-compatible DataFrame from EDGAR CompanyFacts.

    Args:
        facts: Full CompanyFacts JSON
        tag_map: Dict mapping display_name → list of XBRL tags
        form_filter: "10-K" for annual, "10-Q" for quarterly
        quarterly_income: If True, compute individual-quarter income values.
                          Uses frame-based data (CYxxxxQn) when available,
                          then fills gaps by subtracting consecutive YTD values
                          from 10-Q/10-K cumulative filings.

    Returns:
        DataFrame with index=metric names, columns=dates (desc), values=USD
    """
    import re
    from datetime import datetime
    gaap = facts.get("facts", {}).get("us-gaap", {})
    rows = {}

    for display_name, xbrl_tags in tag_map.items():
        if not xbrl_tags:
            continue  # Skip derived fields (e.g., Total Non Current Assets)

        best_vals = None       # {end_date: val} from the best tag so far
        best_max_date = ""     # most recent end date from best tag

        for tag in xbrl_tags:
            concept = gaap.get(tag)
            if not concept:
                continue
            entries = concept.get("units", {}).get("USD", [])
            if not entries:
                continue

            vals = {}

            if form_filter == "10-K":
                # ── Annual data: straightforward, one entry per year ──
                for e in entries:
                    form = e.get("form", "")
                    fp = e.get("fp", "")
                    end = e.get("end", "")
                    val = e.get("val")
                    filed = e.get("filed", "")
                    if val is None or not end:
                        continue
                    if form != "10-K" or fp != "FY":
                        continue
                    if end not in vals or filed > vals[end][1]:
                        vals[end] = (val, filed)

            elif form_filter == "10-Q" and not quarterly_income:
                # ── Balance sheet: point-in-time values ──
                for e in entries:
                    form = e.get("form", "")
                    fp = e.get("fp", "")
                    end = e.get("end", "")
                    val = e.get("val")
                    filed = e.get("filed", "")
                    if val is None or not end:
                        continue
                    if form in ("10-Q", "10-K") and fp in ("Q1","Q2","Q3","Q4","FY"):
                        if end not in vals or filed > vals[end][1]:
                            vals[end] = (val, filed)

            elif form_filter == "10-Q" and quarterly_income:
                # ══════════════════════════════════════════════════════
                # QUARTERLY INCOME: YTD-subtraction approach
                # ══════════════════════════════════════════════════════
                # SEC EDGAR 10-Q entries for income items report
                # CUMULATIVE year-to-date values:
                #   Q1 → 3-month value (individual = cumulative)
                #   Q2 → 6-month cumulative (Q1+Q2)
                #   Q3 → 9-month cumulative (Q1+Q2+Q3)
                # Recent years also have CYxxxxQn frame entries with
                # individual quarter values, but older years do not.
                #
                # Strategy:
                #   Pass 1: Use frame-based entries (CYxxxxQn = individual)
                #   Pass 2: YTD subtraction for missing quarters:
                #           Q1_ind = cum_Q1 (always individual)
                #           Q2_ind = cum_Q2 - cum_Q1
                #           Q3_ind = cum_Q3 - cum_Q2
                #   Pass 3: Q4 = FY_annual - cum_Q3
                # ══════════════════════════════════════════════════════

                # ── Pass 1: Collect frame-based individual quarter values ──
                for e in entries:
                    frame = e.get("frame", "")
                    end = e.get("end", "")
                    val = e.get("val")
                    filed = e.get("filed", "")
                    if val is None or not end:
                        continue
                    if frame and re.match(r"CY\d{4}Q\d$", frame):
                        if end not in vals or filed > vals[end][1]:
                            vals[end] = (val, filed)

                # ── Pass 2: YTD subtraction for missing quarters ──
                # Collect cumulative (max val) per end date from 10-Q
                cum_by_end = {}  # end_date → (max_val, filed, fp)
                fy_annual = {}   # end_date → (val, filed)
                for e in entries:
                    form = e.get("form", "")
                    fp = e.get("fp", "")
                    end = e.get("end", "")
                    val = e.get("val")
                    filed = e.get("filed", "")
                    if val is None or not end:
                        continue
                    if form == "10-Q" and fp in ("Q1", "Q2", "Q3"):
                        # Take maximum val per end date = cumulative YTD
                        if end not in cum_by_end or val > cum_by_end[end][0]:
                            cum_by_end[end] = (val, filed, fp)
                        elif val == cum_by_end[end][0] and filed > cum_by_end[end][1]:
                            cum_by_end[end] = (val, filed, fp)
                    elif form == "10-K" and fp == "FY":
                        if end not in fy_annual or filed > fy_annual[end][1]:
                            fy_annual[end] = (val, filed)

                # Sort end dates chronologically
                sorted_ends = sorted(cum_by_end.keys())

                # Walk through quarters, subtracting previous cumulative
                prev_cum = 0
                for end_date in sorted_ends:
                    cum_val, filed, fp = cum_by_end[end_date]

                    if fp == "Q1":
                        prev_cum = 0  # Reset at fiscal year boundary

                    if end_date not in vals:
                        individual = cum_val - prev_cum
                        if individual >= 0:
                            vals[end_date] = (individual, filed)

                    prev_cum = cum_val

                # ── Pass 3: Q4 = FY_annual - Q3_cumulative ──
                for fy_end, (fy_val, fy_filed) in fy_annual.items():
                    if fy_end in vals:
                        continue
                    # Find the latest Q3 cumulative before this FY end
                    last_q3_cum = None
                    for end_date in sorted_ends:
                        if end_date < fy_end:
                            if cum_by_end[end_date][2] == "Q3":
                                last_q3_cum = cum_by_end[end_date][0]
                    if last_q3_cum is not None:
                        q4 = fy_val - last_q3_cum
                        if q4 >= 0:
                            vals[fy_end] = (q4, fy_filed)

            if vals:
                # Pick the tag whose data is most recent (handles tag
                # transitions like Revenues → RevenueFromContract…)
                tag_max_date = max(vals.keys())
                if best_vals is None or tag_max_date > best_max_date:
                    best_vals = vals
                    best_max_date = tag_max_date

        if best_vals:
            rows[display_name] = {k: v[0] for k, v in best_vals.items()}

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).T
    df.columns = pd.to_datetime(df.columns)
    df = df.sort_index(axis=1, ascending=False)  # Most recent first

    # Compute derived fields
    if "Total Non Current Assets" in tag_map and "Total Non Current Assets" not in df.index:
        if "Total Assets" in df.index and "Current Assets" in df.index:
            nca = df.loc["Total Assets"] - df.loc["Current Assets"]
            df.loc["Total Non Current Assets"] = nca

    if "Total Non Current Liabilities Net Minority Interest" in tag_map:
        if "Total Non Current Liabilities Net Minority Interest" not in df.index:
            if "Total Liabilities Net Minority Interest" in df.index and "Current Liabilities" in df.index:
                ncl = df.loc["Total Liabilities Net Minority Interest"] - df.loc["Current Liabilities"]
                df.loc["Total Non Current Liabilities Net Minority Interest"] = ncl

    return df


# ─── Node label → metric mapping ─────────────────────────────────────────
# Maps the display name in each Sankey node to the DataFrame row key.
# Used to pull historical time-series when a user clicks a node.

INCOME_NODE_METRICS = {
    "Revenue":          "Total Revenue",
    "Cost of Revenue":  "Cost Of Revenue",
    "Gross Profit":     "Gross Profit",
    "R&D":              "Research And Development",
    "SG&A":             "Selling General And Administration",
    "D&A":              "Reconciled Depreciation",
    "Other OpEx":       "Other Operating Expenses",
    "Operating Income": "Operating Income",
    "Interest Exp.":    "Interest Expense",
    "Pretax Income":    "Pretax Income",
    "Income Tax":       "Tax Provision",
    "Net Income":       "Net Income",
}

BALANCE_NODE_METRICS = {
    "Total Assets":       "Total Assets",
    "Current Assets":     "Current Assets",
    "Non-Current Assets": "Total Non Current Assets",
    "Cash":               "Cash And Cash Equivalents",
    "ST Investments":     "Other Short Term Investments",
    "Receivables":        "Accounts Receivable",
    "Inventory":          "Inventory",
    "PPE":                "Net PPE",
    "Goodwill":           "Goodwill",
    "Intangibles":        "Other Intangible Assets",
    "Investments":        "Investments And Advances",
    "Total Liabilities":  "Total Liabilities Net Minority Interest",
    "Current Liab.":      "Current Liabilities",
    "Non-Current Liab.":  "Total Non Current Liabilities Net Minority Interest",
    "Accounts Payable":   "Accounts Payable",
    "Short-Term Debt":    "Current Debt",
    "Deferred Revenue":   "Current Deferred Revenue",
    "Long-Term Debt":     "Long Term Debt",
    "Equity":             "Stockholders Equity",
    "Retained Earnings":  "Retained Earnings",
}


# ─── Node info: "What it means" + "How to read it" for Sankey popups ──────
INCOME_NODE_INFO = {
    "Revenue": {
        "meaning": "Total sales or income generated from the company's core business operations before any costs are subtracted.",
        "reading": "Revenue is the starting point of the Sankey flow. It splits into Cost of Revenue (consumed) and Gross Profit (retained). Growing revenue is the most fundamental growth signal.",
    },
    "Cost of Revenue": {
        "meaning": "Direct costs attributable to producing the goods or services sold, including materials, manufacturing labor, and direct overhead.",
        "reading": "This is value consumed from Revenue. A shrinking share of Revenue going to COGS means improving gross margins and better pricing power or efficiency.",
    },
    "Gross Profit": {
        "meaning": "Revenue minus Cost of Revenue. The profit remaining after paying direct production costs.",
        "reading": "Gross Profit flows into operating expenses and Operating Income. A growing Gross Profit with stable or expanding margins indicates a healthy, scalable business.",
    },
    "R&D": {
        "meaning": "Research & Development spending. Investment in new products, technologies, and innovation.",
        "reading": "R&D is value consumed from Gross Profit. High R&D spending signals investment in future growth (especially in tech). Ideally R&D grows slower than revenue over time.",
    },
    "SG&A": {
        "meaning": "Selling, General & Administrative expenses. Includes sales teams, marketing, management salaries, office costs, and corporate overhead.",
        "reading": "SG&A is value consumed from Gross Profit. Rising SG&A may indicate scaling sales efforts. Declining SG&A as a % of revenue shows operating leverage.",
    },
    "D&A": {
        "meaning": "Depreciation & Amortization. Non-cash charges that allocate the cost of physical assets (depreciation) and intangible assets (amortization) over their useful life.",
        "reading": "D&A is a non-cash expense that reduces Operating Income. High D&A relative to capex may indicate aging assets. It is added back in cash flow calculations.",
    },
    "Other OpEx": {
        "meaning": "Other operating expenses not classified as R&D, SG&A, or D&A. May include restructuring charges, litigation costs, or one-time items.",
        "reading": "Watch for spikes in Other OpEx which may indicate one-time charges. Consistently high Other OpEx warrants investigation into what costs are being categorized here.",
    },
    "Operating Income": {
        "meaning": "Gross Profit minus all operating expenses (R&D, SG&A, D&A). Measures profit from core business operations before interest and taxes.",
        "reading": "Operating Income shows core business profitability. It flows into Pretax Income after accounting for interest. Growing Operating Income faster than Revenue means improving operating leverage.",
    },
    "Interest Exp.": {
        "meaning": "Interest paid on the company's debt obligations (bonds, loans, credit facilities).",
        "reading": "Interest expense reduces Operating Income before arriving at Pretax Income. High interest expense relative to operating income indicates heavy debt load and financial risk.",
    },
    "Pretax Income": {
        "meaning": "Income before income tax expense. Operating Income minus interest expense plus any non-operating income.",
        "reading": "Pretax Income flows into Income Tax and Net Income. Comparing Pretax to Operating Income reveals the impact of debt financing on profitability.",
    },
    "Income Tax": {
        "meaning": "Federal, state, and foreign income taxes owed on the company's pretax income for the period.",
        "reading": "Tax is value consumed from Pretax Income. Effective tax rates of 15-25% are typical for US companies. Very low rates may use international structures or tax credits.",
    },
    "Net Income": {
        "meaning": "The bottom line: total profit after all expenses, interest, and taxes. This is what belongs to shareholders.",
        "reading": "Net Income is the final destination of the Sankey flow. It represents the value retained by the company. Growing Net Income as a percentage of Revenue shows improving overall efficiency.",
    },
}

BALANCE_NODE_INFO = {
    "Total Assets": {
        "meaning": "Everything the company owns or controls that has economic value. The starting point of the balance sheet.",
        "reading": "Total Assets split into Current Assets (liquid, < 1 year) and Non-Current Assets (long-term). Growing assets generally indicates a growing business.",
    },
    "Current Assets": {
        "meaning": "Assets expected to be converted to cash or consumed within one year. Includes cash, investments, receivables, and inventory.",
        "reading": "Current Assets should comfortably exceed Current Liabilities (current ratio > 1). High current assets relative to total assets means strong short-term liquidity.",
    },
    "Non-Current Assets": {
        "meaning": "Long-term assets not expected to be converted to cash within one year. Includes property, equipment, goodwill, and investments.",
        "reading": "Heavy non-current assets indicate a capital-intensive business. Watch for goodwill as a large percentage, which may indicate acquisition-heavy growth strategy.",
    },
    "Cash": {
        "meaning": "Cash and cash equivalents. The most liquid asset, including bank deposits and short-term instruments convertible to cash within 90 days.",
        "reading": "Strong cash position provides safety and flexibility. Compare to total debt to assess net cash/debt position. Tech companies often hold large cash reserves.",
    },
    "ST Investments": {
        "meaning": "Short-term investments and marketable securities. Liquid investments that can be sold within one year.",
        "reading": "ST Investments supplement cash. Together with cash, they form the company's total liquidity. Large ST Investment positions are common in cash-rich tech companies.",
    },
    "Receivables": {
        "meaning": "Accounts receivable. Money owed to the company by customers for goods or services already delivered.",
        "reading": "Rising receivables faster than revenue may indicate collection problems or aggressive revenue recognition. Compare Days Sales Outstanding (DSO) to industry norms.",
    },
    "Inventory": {
        "meaning": "Goods available for sale or raw materials/work-in-progress. Relevant for manufacturing and retail companies.",
        "reading": "Rising inventory faster than sales growth may signal demand weakness. Low inventory turnover ties up capital. Service companies typically have minimal inventory.",
    },
    "Other Current": {
        "meaning": "Other current assets not specifically classified. May include prepaid expenses, tax receivables, or other short-term items.",
        "reading": "Usually a smaller category. Significant increases warrant investigation into what specific items are driving the change.",
    },
    "PPE": {
        "meaning": "Property, Plant & Equipment. Physical assets like land, buildings, machinery, and equipment, net of accumulated depreciation.",
        "reading": "High PPE indicates capital-intensive operations (manufacturing, utilities). Rising PPE shows investment in physical capacity. Declining PPE may mean underinvestment.",
    },
    "Goodwill": {
        "meaning": "The premium paid above fair value of net assets in acquisitions. Represents intangible value like brand, customer relationships, and synergies.",
        "reading": "Large goodwill indicates acquisition-driven growth. Goodwill impairments are a risk if acquisitions underperform. Goodwill never increases organically.",
    },
    "Intangibles": {
        "meaning": "Identifiable intangible assets such as patents, trademarks, software, and customer relationships acquired in business combinations.",
        "reading": "Unlike goodwill, intangibles are amortized over time. High intangibles relative to total assets means the company's value is largely in intellectual property.",
    },
    "Investments": {
        "meaning": "Long-term investments including equity stakes in other companies, joint ventures, and held-to-maturity securities.",
        "reading": "Large investment portfolios are common in financial companies and conglomerates. Strategic investments may generate returns not captured in operating income.",
    },
    "Other Non-Current": {
        "meaning": "Other long-term assets including deferred tax assets, right-of-use assets, and other non-current items.",
        "reading": "Check for large deferred tax assets which may indicate accumulated losses. Right-of-use assets reflect operating lease commitments.",
    },
    "Total Liabilities": {
        "meaning": "Total obligations the company owes to others. Splits into Current Liabilities (due within 1 year) and Non-Current Liabilities (long-term debt).",
        "reading": "Compare Total Liabilities to Total Assets (debt-to-assets ratio). High leverage amplifies returns but increases risk. Declining leverage ratios are generally positive.",
    },
    "Current Liab.": {
        "meaning": "Obligations due within one year including accounts payable, short-term debt, and accrued expenses.",
        "reading": "Current Liabilities should be comfortably covered by Current Assets. Rising current liabilities faster than current assets may signal liquidity pressure.",
    },
    "Non-Current Liab.": {
        "meaning": "Long-term obligations not due within one year, primarily long-term debt and lease obligations.",
        "reading": "Long-term debt structure matters: fixed vs variable rate, maturity dates, and covenants. Manageable long-term debt at low rates can be advantageous.",
    },
    "Accounts Payable": {
        "meaning": "Money the company owes to suppliers for goods and services received but not yet paid for.",
        "reading": "Rising payables can indicate better negotiating power (longer payment terms) or cash flow management. Very high payables may signal payment difficulties.",
    },
    "Short-Term Debt": {
        "meaning": "Debt obligations due within one year including current portion of long-term debt, commercial paper, and credit lines.",
        "reading": "Short-term debt must be refinanced or repaid soon. High short-term debt with low cash creates refinancing risk. Compare to available cash and credit facilities.",
    },
    "Deferred Revenue": {
        "meaning": "Payments received from customers for goods or services not yet delivered. Common in subscription and software businesses.",
        "reading": "Growing deferred revenue is a positive sign as it indicates strong future revenue visibility. Declining deferred revenue may signal slowing new bookings.",
    },
    "Other CL": {
        "meaning": "Other current liabilities including accrued expenses, tax payables, and other short-term obligations.",
        "reading": "Usually includes routine accruals. Significant changes may reflect timing of tax payments, bonuses, or other periodic obligations.",
    },
    "Long-Term Debt": {
        "meaning": "Bonds, loans, and other borrowings with maturities beyond one year. The primary component of long-term financing.",
        "reading": "Evaluate debt levels relative to EBITDA (Debt/EBITDA ratio). Check debt maturity schedule for near-term refinancing needs. Low-rate fixed debt can be strategic.",
    },
    "Other LT Liab.": {
        "meaning": "Other non-current liabilities including pension obligations, long-term lease liabilities, and deferred tax liabilities.",
        "reading": "Large pension obligations can be a significant future burden. Deferred tax liabilities may indicate temporary timing differences that will reverse.",
    },
    "Equity": {
        "meaning": "Stockholders' equity. The residual value after subtracting total liabilities from total assets. Represents shareholders' ownership stake.",
        "reading": "Growing equity indicates value creation. Negative equity (liabilities > assets) is a red flag unless driven by aggressive share buybacks in profitable companies.",
    },
    "Retained Earnings": {
        "meaning": "Cumulative net income retained in the business since inception, minus dividends paid to shareholders.",
        "reading": "Growing retained earnings means the company is building value internally. Negative retained earnings indicate accumulated losses over the company's history.",
    },
    "Other Equity": {
        "meaning": "Other equity components including additional paid-in capital, treasury stock (buybacks), and accumulated other comprehensive income.",
        "reading": "Large treasury stock (negative) indicates significant share buybacks. AOCI fluctuations reflect unrealized gains/losses on investments and foreign currency.",
    },
}


def _get_historical_series(df, yf_key):
    """Extract a full time-series row from a yfinance DataFrame.

    Returns a pandas Series with datetime index and float values,
    sorted chronologically (oldest first).

    Matching strategies (tried in order):
    1. Exact substring match (handles legacy spaced indices)
    2. Space-removed substring match (handles CamelCase indices like
       "TotalRevenue" when yf_key is "Total Revenue")
    3. Word-stem matching — all significant word stems (first 5 chars of
       words >= 3 chars) must appear in the index name
    """
    if df is None or df.empty:
        return None

    def _extract(idx_label):
        """Try to extract a valid numeric Series from a DataFrame row."""
        row = df.loc[idx_label].dropna().astype(float)
        if not row.empty:
            row.index = pd.to_datetime(row.index)
            return row.sort_index()
        return None

    key_lower = yf_key.lower()
    key_nospace = key_lower.replace(" ", "").replace("_", "")

    # Strategy 1: exact substring match (works for legacy spaced indices)
    for idx in df.index:
        if key_lower in str(idx).lower():
            result = _extract(idx)
            if result is not None:
                return result

    # Strategy 2: space-removed match (handles CamelCase like "NetPPE", "TotalRevenue")
    for idx in df.index:
        idx_nospace = str(idx).lower().replace(" ", "").replace("_", "")
        if key_nospace in idx_nospace or idx_nospace in key_nospace:
            result = _extract(idx)
            if result is not None:
                return result

    # Strategy 3: all significant word-stems (first 5 chars) present
    # Uses words >= 3 chars (not 4) to handle short words like "Net", "PPE", "Tax"
    key_words = [w[:5].lower() for w in yf_key.replace("_", " ").split() if len(w) >= 3]
    if key_words:
        for idx in df.index:
            idx_lower = str(idx).lower()
            # Also check with spaces removed for CamelCase
            idx_nospace_check = idx_lower.replace(" ", "")
            if all(stem in idx_lower or stem in idx_nospace_check for stem in key_words):
                result = _extract(idx)
                if result is not None:
                    return result

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_quarterly_data(ticker: str):
    """Fetch quarterly income & balance sheet from SEC EDGAR for historical charts."""
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return pd.DataFrame(), pd.DataFrame()
        facts = _fetch_edgar_facts(cik)
        q_income = _edgar_build_df(facts, _XBRL_INCOME_TAGS, form_filter="10-Q", quarterly_income=True)
        q_balance = _edgar_build_df(facts, _XBRL_BALANCE_TAGS, form_filter="10-Q", quarterly_income=False)
        return q_income, q_balance
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_annual_data(ticker: str):
    """Fetch annual income & balance sheet from SEC EDGAR for historical charts."""
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return pd.DataFrame(), pd.DataFrame()
        facts = _fetch_edgar_facts(cik)
        a_income = _edgar_build_df(facts, _XBRL_INCOME_TAGS, form_filter="10-K")
        a_balance = _edgar_build_df(facts, _XBRL_BALANCE_TAGS, form_filter="10-K")
        return a_income, a_balance
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


def _show_metric_popup(ticker, node_label, view):
    """Show a popup (dialog) with historical chart + Quarterly/Annual & period selectors."""

    # Determine which mapping to use
    metric_map = INCOME_NODE_METRICS if view == "income" else BALANCE_NODE_METRICS

    clean_label = node_label.split("<br>")[0].strip()
    if "  " in clean_label: clean_label = clean_label.split("  ")[0].strip()
    yf_key = metric_map.get(clean_label)
    if not yf_key:
        return

    # ── Inject custom CSS for the timeframe buttons ──
    st.markdown("""
    <style>
    .tf-row {
        display: flex; gap: 0; border-radius: 12px; overflow: hidden;
        border: 2px solid #3b82f6; width: fit-content; margin: 0 auto 6px;
    }
    .tf-btn {
        padding: 10px 28px; font-size: 0.95rem; font-weight: 600;
        font-family: Inter, system-ui, sans-serif; cursor: pointer;
        border: none; transition: all 0.15s ease;
        background: #fff; color: #3b82f6;
    }
    .tf-btn.active { background: #3b82f6; color: #fff; }
    .tf-btn:not(:last-child) { border-right: 2px solid #3b82f6; }
    .pd-row {
        display: flex; gap: 0; border-radius: 10px; overflow: hidden;
        border: 2px solid #3b82f6; width: fit-content; margin: 0 auto 10px;
    }
    .pd-btn {
        padding: 8px 24px; font-size: 0.85rem; font-weight: 600;
        font-family: Inter, system-ui, sans-serif; cursor: pointer;
        border: none; transition: all 0.15s ease;
        background: #fff; color: #3b82f6;
    }
    .pd-btn.active { background: #3b82f6; color: #fff; }
    .pd-btn:not(:last-child) { border-right: 2px solid #3b82f6; }
    @media (max-width: 480px) {
        .tf-btn { padding: 8px 18px; font-size: 0.82rem; }
        .pd-btn { padding: 6px 16px; font-size: 0.78rem; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Node info: "What it means" + "How to read it" ──
    info_map = INCOME_NODE_INFO if view == "income" else BALANCE_NODE_INFO
    node_info = info_map.get(clean_label, {})
    if node_info:
        meaning = node_info.get("meaning", "")
        reading = node_info.get("reading", "")
        if meaning:
            st.markdown(
                f'<div style="margin:4px 0 10px 0;">'
                f'<span style="color:#2475fc;font-weight:600;font-size:0.82rem;'
                f'text-transform:uppercase;letter-spacing:0.5px;">What it means</span>'
                f'<p style="margin:4px 0 0 0;color:#495057;font-size:0.88rem;line-height:1.55;">'
                f'{meaning}</p></div>',
                unsafe_allow_html=True,
            )
        if reading:
            st.markdown(
                f'<div style="margin:0 0 10px 0;padding-top:8px;'
                f'border-top:1px solid #f0f0f0;">'
                f'<span style="color:#2475fc;font-weight:600;font-size:0.82rem;'
                f'text-transform:uppercase;letter-spacing:0.5px;">How to read it</span>'
                f'<p style="margin:4px 0 0 0;color:#495057;font-size:0.88rem;line-height:1.55;">'
                f'{reading}</p></div>',
                unsafe_allow_html=True,
            )
        st.divider()

    # ── Frequency toggle: Quarterly / Annual ──
    freq_key = f"tf_freq_{view}_{clean_label}"
    if freq_key not in st.session_state:
        st.session_state[freq_key] = "Quarterly"

    # ── Period toggle: 1Y / 2Y / 4Y / MAX ──
    period_key = f"tf_period_{view}_{clean_label}"
    if period_key not in st.session_state:
        st.session_state[period_key] = "4Y"

    # Render frequency toggle
    freq_cols = st.columns([1, 2, 1])
    with freq_cols[1]:
        fc = st.columns(2)
        for i, lbl in enumerate(["Quarterly", "Annual"]):
            if fc[i].button(lbl, key=f"{freq_key}_{lbl}",
                            type="primary" if st.session_state[freq_key] == lbl else "secondary",
                            use_container_width=True):
                st.session_state[freq_key] = lbl

    # Render period selector
    period_cols = st.columns([1, 3, 1])
    with period_cols[1]:
        pc = st.columns(4)
        for i, lbl in enumerate(["1Y", "2Y", "4Y", "MAX"]):
            if pc[i].button(lbl, key=f"{period_key}_{lbl}",
                            type="primary" if st.session_state[period_key] == lbl else "secondary",
                            use_container_width=True):
                st.session_state[period_key] = lbl

    freq = st.session_state[freq_key]
    period = st.session_state[period_key]

    # ── Fetch data based on frequency ──
    if freq == "Quarterly":
        q_income, q_balance = _fetch_quarterly_data(ticker)
        src_df = q_income if view == "income" else q_balance
        freq_label = "Quarterly"
        tick_dt = "M3"
    else:
        a_income, a_balance = _fetch_annual_data(ticker)
        src_df = a_income if view == "income" else a_balance
        freq_label = "Annual"
        tick_dt = "M12"

    series = _get_historical_series(src_df, yf_key)

    # ── Fallback: compute "Other OpEx" as residual when not directly available ──
    if (series is None or series.empty) and yf_key == "Other Operating Expenses":
        gp = _get_historical_series(src_df, "Gross Profit")
        rd = _get_historical_series(src_df, "Research And Development")
        sga = _get_historical_series(src_df, "Selling General And Administration")
        da = _get_historical_series(src_df, "Reconciled Depreciation")
        oi = _get_historical_series(src_df, "Operating Income")
        if gp is not None and oi is not None:
            common = gp.index
            for s in [rd, sga, da, oi]:
                if s is not None:
                    common = common.intersection(s.index)
            if len(common) > 0:
                _rd = rd.reindex(common, fill_value=0) if rd is not None else 0
                _sga = sga.reindex(common, fill_value=0) if sga is not None else 0
                _da = da.reindex(common, fill_value=0) if da is not None else 0
                computed = gp.reindex(common) - _rd - _sga - _da - oi.reindex(common)
                computed = computed.clip(lower=0)
                if not computed.empty and computed.sum() > 0:
                    series = computed.sort_index()

    # ── Fallback: compute "Investments" as residual when not directly available ──
    if (series is None or series.empty) and yf_key == "Investments And Advances":
        nca = _get_historical_series(src_df, "Total Non Current Assets")
        ppe = _get_historical_series(src_df, "Net PPE")
        gw = _get_historical_series(src_df, "Goodwill")
        intang = _get_historical_series(src_df, "Other Intangible Assets")
        if nca is not None:
            common = nca.index
            for s in [ppe, gw, intang]:
                if s is not None:
                    common = common.intersection(s.index)
            if len(common) > 0:
                _ppe = ppe.reindex(common, fill_value=0) if ppe is not None else 0
                _gw = gw.reindex(common, fill_value=0) if gw is not None else 0
                _intang = intang.reindex(common, fill_value=0) if intang is not None else 0
                computed = nca.reindex(common) - _ppe - _gw - _intang
                computed = computed.clip(lower=0)
                if not computed.empty and computed.sum() > 0:
                    series = computed.sort_index()

    if series is None or series.empty:
        st.warning(f"No {freq_label.lower()} data available for **{clean_label}**.")
        return

    # ── Filter by period ──
    if period != "MAX":
        years = int(period.replace("Y", ""))
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        series = series[series.index >= cutoff]

    if series.empty:
        st.warning(f"No {freq_label.lower()} data in selected period for **{clean_label}**.")
        return

    # Determine scale
    max_val = series.abs().max()
    if max_val >= 1e12:
        divisor, suffix = 1e12, "T"
    elif max_val >= 1e9:
        divisor, suffix = 1e9, "B"
    elif max_val >= 1e6:
        divisor, suffix = 1e6, "M"
    else:
        divisor, suffix = 1, ""

    scaled_values = [v / divisor for v in series.values]

    period_label = "All Time" if period == "MAX" else f"Last {period}"

    # Build chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index,
        y=scaled_values,
        mode="lines+markers" if len(series) > 1 else "markers",
        name=freq_label,
        line=dict(color="#3b82f6", width=2.5),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.10)",
        hovertemplate=f"%{{x|%b %Y}}<br>$%{{y:.2f}}{suffix}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(
            text=f"{clean_label} — {freq_label} ({period_label})",
            font=dict(size=16, family="Inter, sans-serif", color="#1e293b"),
        ),
        height=400,
        margin=dict(l=60, r=20, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#475569"),
        showlegend=False,
        xaxis=dict(
            showgrid=True, gridcolor="rgba(0,0,0,0.06)",
            dtick=tick_dt, tickformat="%b\n%Y",
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(0,0,0,0.06)",
            tickprefix="$", ticksuffix=suffix,
            tickformat=",.1f" if divisor >= 1e9 else ",.0f",
            title=None,
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtons": [["toImage"]]}, key=f"hist_{freq}_{period}")

    # ── Navigation pills inside popup ──
    st.divider()
    all_metrics = list(metric_map.keys())
    popup_nav_key = f"popup_nav_{view}"
    nav_sel = st.pills(
        "Navigate metrics",
        all_metrics,
        default=clean_label,
        key=popup_nav_key,
    )
    if nav_sel and nav_sel != clean_label:
        st.session_state[f"popup_active_{view}"] = nav_sel
        st.rerun()


def _inject_sankey_click_js(metric_map):
    """Inject JS that bridges Sankey node clicks to the matching pill button.

    When a user clicks a Sankey node, the JS extracts the node label,
    finds the corresponding pill button in the parent document, and clicks it.
    This triggers the existing st.pills → st.dialog flow.
    """
    # Build a JS set of valid pill labels for fast lookup
    valid_labels = list(metric_map.keys())
    labels_js = ", ".join(f'"{lbl}"' for lbl in valid_labels)

    js = f"""
    <script>
    (function() {{
        const VALID = new Set([{labels_js}]);
        const parentDoc = window.parent.document;

        function attach() {{
            // Find all Plotly charts in parent
            const plots = parentDoc.querySelectorAll('.js-plotly-plot');
            if (!plots.length) return false;

            let attached = false;
            plots.forEach(function(plotDiv) {{
                if (plotDiv._sankey_click_bound) return;
                plotDiv.on('plotly_click', function(data) {{
                    if (!data || !data.points || !data.points[0]) return;
                    var pt = data.points[0];
                    // Sankey nodes expose label; links expose source/target
                    var raw = pt.label || '';
                    // Strip value after <br> or double-space
                    var label = raw.split(/<br>|  /)[0].replace(/\\n/g, '').trim();
                    if (!label || !VALID.has(label)) return;

                    // Find pill buttons (Streamlit renders them in [role=radiogroup])
                    var btns = parentDoc.querySelectorAll('[role="radiogroup"] button');
                    for (var i = 0; i < btns.length; i++) {{
                        if (btns[i].textContent.trim() === label) {{
                            btns[i].click();
                            break;
                        }}
                    }}
                }});
                plotDiv._sankey_click_bound = true;
                attached = true;
            }});
            return attached;
        }}

        // Retry until chart is rendered
        if (!attach()) {{
            var obs = new MutationObserver(function() {{
                if (attach()) obs.disconnect();
            }});
            obs.observe(parentDoc.body, {{ childList: true, subtree: true }});
            setTimeout(function() {{ obs.disconnect(); }}, 8000);
        }}
    }})();
    </script>
    """
    components.html(js, height=0)


def _generate_sankey_pdf(income_df, balance_df, info, ticker, view="income"):
    """Generate a professional PDF with actual Sankey flow diagram + KPI cards.

    Income Statement  → Sankey diagram matching the on-screen Plotly version.
    Balance Sheet     → Sankey diagram matching the on-screen Plotly version.
    Uses matplotlib only (no kaleido needed).  Returns PDF bytes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.path import Path
    from matplotlib.backends.backend_pdf import PdfPages
    import numpy as np

    buf = BytesIO()
    company = info.get("shortName", info.get("longName", ticker))

    # Fetch company logo for PDF title
    _logo_img = None
    try:
        from PIL import Image as _PILImage
        _logo_resp = requests.get(
            f"https://financialmodelingprep.com/image-stock/{ticker}.png",
            timeout=3,
        )
        if _logo_resp.status_code == 200 and len(_logo_resp.content) > 100:
            _logo_img = _PILImage.open(BytesIO(_logo_resp.content)).convert("RGBA")
    except Exception:
        pass

    def _fmts(v):
        """Short format for labels."""
        av = abs(v)
        if av >= 1e12: return f"${v/1e12:.1f}T"
        if av >= 1e9:  return f"${v/1e9:.1f}B"
        if av >= 1e6:  return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"

    def _hex_to_rgba(hex_color, alpha=0.35):
        """Convert hex color to RGBA tuple for matplotlib."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
        return (r, g, b, alpha)

    def _draw_kpi_row(fig, kpis, y_bottom=0.88, height=0.06):
        """Draw a KPI card row at the top of a figure."""
        ax_kpi = fig.add_axes([0.06, y_bottom, 0.88, height])
        ax_kpi.set_xlim(0, len(kpis))
        ax_kpi.set_ylim(0, 1)
        ax_kpi.axis("off")
        bg = mpatches.FancyBboxPatch(
            (0.02, -0.1), len(kpis) - 0.04, 1.2,
            boxstyle="round,pad=0.05",
            facecolor="#f8fafc", edgecolor="#e2e8f0", linewidth=1,
        )
        ax_kpi.add_patch(bg)
        for i, (lbl, val) in enumerate(kpis):
            xc = i + 0.5
            ax_kpi.text(xc, 0.72, lbl, ha="center", va="center",
                        fontsize=9, color="#64748b")
            ax_kpi.text(xc, 0.25, _fmts(val), ha="center", va="center",
                        fontsize=14, color="#1e293b", fontweight="bold")
            if i < len(kpis) - 1:
                ax_kpi.axvline(x=i + 1, color="#e2e8f0", linewidth=1.5)

    def _draw_sankey(ax, node_list, link_list, total_height):
        """Draw a Sankey diagram on ax.

        node_list: [(label, value, x, y_center, color), ...]
           x in [0,1], y_center in [0,1] (0=bottom, 1=top)
        link_list: [(src_idx, tgt_idx, value, color), ...]
        total_height: the max value for scaling bar heights.
        """
        if not node_list:
            return

        ax.set_xlim(-0.05, 1.08)
        ax.set_ylim(-0.05, 1.05)
        ax.axis("off")

        bar_w = 0.025  # node bar width
        scale = 0.85 / max(total_height, 1)  # scale factor to convert value → y height

        # Precompute node positions (in axis coords)
        node_rects = []  # (x, y_bottom, width, height, color, label, value)
        for label, value, nx, ny, color in node_list:
            h = max(abs(value) * scale, 0.008)  # minimum visible height
            y_bot = ny - h / 2
            node_rects.append((nx, y_bot, bar_w, h, color, label, value))

        # Track how much of each node's top/bottom is used by links
        node_out_offset = [0.0] * len(node_list)  # outgoing: from top down
        node_in_offset = [0.0] * len(node_list)   # incoming: from top down

        # Draw links as bezier curves
        for src_i, tgt_i, val, lcolor in link_list:
            if val <= 0:
                continue
            s_x, s_yb, s_w, s_h, _, _, _ = node_rects[src_i]
            t_x, t_yb, t_w, t_h, _, _, _ = node_rects[tgt_i]

            link_h = max(val * scale, 0.003)

            # Source: start from top, go down
            s_top = s_yb + s_h - node_out_offset[src_i]
            s_y1 = s_top
            s_y0 = s_top - link_h
            node_out_offset[src_i] += link_h

            # Target: start from top, go down
            t_top = t_yb + t_h - node_in_offset[tgt_i]
            t_y1 = t_top
            t_y0 = t_top - link_h
            node_in_offset[tgt_i] += link_h

            # Draw bezier band from (s_x + s_w, s_y0..s_y1) to (t_x, t_y0..t_y1)
            x0 = s_x + s_w
            x1 = t_x
            xm = (x0 + x1) / 2

            # Upper edge
            verts_upper = [
                (x0, s_y1),
                (xm, s_y1),
                (xm, t_y1),
                (x1, t_y1),
            ]
            # Lower edge (reversed)
            verts_lower = [
                (x1, t_y0),
                (xm, t_y0),
                (xm, s_y0),
                (x0, s_y0),
            ]

            verts = verts_upper + verts_lower + [(x0, s_y1)]
            codes = [
                Path.MOVETO,
                Path.CURVE4, Path.CURVE4, Path.CURVE4,
                Path.LINETO,
                Path.CURVE4, Path.CURVE4, Path.CURVE4,
                Path.CLOSEPOLY,
            ]

            path = Path(verts, codes)
            rgba = _hex_to_rgba(lcolor, 0.35)
            patch = mpatches.PathPatch(path, facecolor=rgba, edgecolor="none",
                                       linewidth=0, zorder=1)
            ax.add_patch(patch)

        # Draw node bars
        for i, (nx, y_bot, w, h, color, label, value) in enumerate(node_rects):
            rect = mpatches.FancyBboxPatch(
                (nx, y_bot), w, h,
                boxstyle="round,pad=0.002",
                facecolor=color, edgecolor="none", linewidth=0, zorder=3,
            )
            ax.add_patch(rect)

            # Label to the right (or left for rightmost column)
            txt = f"{label}\n{_fmts(value)}"
            if nx > 0.85:
                ax.text(nx + w + 0.012, y_bot + h / 2, txt,
                        ha="left", va="center", fontsize=8,
                        color="#1e293b", fontweight="medium", zorder=4)
            elif nx < 0.08:
                ax.text(nx - 0.012, y_bot + h / 2, txt,
                        ha="right", va="center", fontsize=8,
                        color="#1e293b", fontweight="medium", zorder=4)
            else:
                ax.text(nx + w + 0.012, y_bot + h / 2, txt,
                        ha="left", va="center", fontsize=7.5,
                        color="#1e293b", fontweight="medium", zorder=4)

    try:
        with PdfPages(buf) as pdf:
            if view == "income":
                # ── Extract data (same as _build_income_sankey) ──
                revenue       = _safe(income_df, "Total Revenue")
                cogs          = abs(_safe(income_df, "Cost Of Revenue"))
                gross_profit  = _safe(income_df, "Gross Profit")
                rd            = abs(_safe(income_df, "Research And Development"))
                sga           = abs(_safe(income_df, "Selling General And Administration"))
                da            = abs(_safe(income_df, "Reconciled Depreciation"))
                if da == 0:
                    da = abs(_safe(income_df, "Depreciation And Amortization"))
                other_opex    = abs(_safe(income_df, "Other Operating Expense"))
                op_income     = _safe(income_df, "Operating Income")
                interest      = abs(_safe(income_df, "Interest Expense"))
                pretax        = _safe(income_df, "Pretax Income") or _safe(income_df, "Income Before Tax")
                tax           = abs(_safe(income_df, "Tax Provision"))
                net_income    = _safe(income_df, "Net Income")

                if revenue == 0:
                    return b""

                # Fix derived
                if gross_profit == 0:
                    gross_profit = revenue - cogs
                if op_income == 0:
                    op_income = gross_profit - rd - sga - da - other_opex
                if pretax == 0:
                    pretax = op_income - interest
                if net_income == 0:
                    net_income = pretax - tax

                # Ensure positive
                revenue = max(revenue, 0)
                cogs = max(cogs, 0)
                gross_profit = max(gross_profit, 0)
                rd = max(rd, 0)
                sga = max(sga, 0)
                da = max(da, 0)
                other_opex = max(other_opex, 0)
                op_income = max(op_income, 0)
                interest = max(interest, 0)
                pretax = max(pretax, 0)
                tax = max(tax, 0)
                net_income = max(net_income, 0)

                # ── Build nodes: (label, value, x, y_center, color) ──
                # Layout: 5 columns matching the Plotly Sankey
                X1, X2, X3, X4, X5 = 0.02, 0.22, 0.48, 0.70, 0.88
                nodes = []
                nmap = {}

                def add_n(name, val, x, y, ci):
                    nmap[name] = len(nodes)
                    nodes.append((name, val, x, y, VIVID[ci]))

                add_n("Revenue", revenue, X1, 0.50, 0)
                add_n("Cost of Revenue", cogs, X2, 0.88, 1)
                add_n("Gross Profit", gross_profit, X2, 0.38, 2)

                # Expenses in column 3
                exp_y = 0.92
                exp_gap = 0.14
                n_exp = 0
                if rd > 0:
                    add_n("R&D", rd, X3, exp_y - n_exp * exp_gap, 3)
                    n_exp += 1
                if sga > 0:
                    add_n("SG&A", sga, X3, exp_y - n_exp * exp_gap, 4)
                    n_exp += 1
                if da > 0:
                    add_n("D&A", da, X3, exp_y - n_exp * exp_gap, 5)
                    n_exp += 1
                if other_opex > 0:
                    add_n("Other OpEx", other_opex, X3, exp_y - n_exp * exp_gap, 5)
                    n_exp += 1
                oi_y = min(exp_y - n_exp * exp_gap - 0.12, 0.35)
                add_n("Operating Income", op_income, X3, oi_y, 6)

                if interest > 0:
                    add_n("Interest Exp.", interest, X4, oi_y + 0.12, 7)
                pt_y = oi_y - 0.08
                add_n("Pretax Income", pretax, X4, pt_y, 8)

                if tax > 0:
                    add_n("Income Tax", tax, X5, pt_y + 0.10, 9)
                net_y = pt_y - 0.10
                add_n("Net Income", net_income, X5, max(net_y, 0.08), 10)

                # ── Build links: (src_idx, tgt_idx, value, color) ──
                links = []
                def lnk(s, t, v, ci):
                    si, ti = nmap.get(s, -1), nmap.get(t, -1)
                    if si >= 0 and ti >= 0 and v > 0:
                        links.append((si, ti, v, VIVID[ci]))

                lnk("Revenue", "Cost of Revenue", cogs, 1)
                lnk("Revenue", "Gross Profit", gross_profit, 2)
                if rd > 0: lnk("Gross Profit", "R&D", rd, 3)
                if sga > 0: lnk("Gross Profit", "SG&A", sga, 4)
                if da > 0: lnk("Gross Profit", "D&A", da, 5)
                if other_opex > 0: lnk("Gross Profit", "Other OpEx", other_opex, 5)
                lnk("Gross Profit", "Operating Income", op_income, 6)
                if interest > 0: lnk("Operating Income", "Interest Exp.", interest, 7)
                lnk("Operating Income", "Pretax Income", pretax, 8)
                if tax > 0: lnk("Pretax Income", "Income Tax", tax, 9)
                lnk("Pretax Income", "Net Income", net_income, 10)

                # ── Draw figure ──
                fig = plt.figure(figsize=(16, 9), facecolor="white")
                if _logo_img is not None:
                    logo_ax = fig.add_axes([0.20, 0.93, 0.03, 0.05])
                    logo_ax.imshow(_logo_img)
                    logo_ax.axis("off")
                fig.text(0.5, 0.96, f"{company} ({ticker}) \u2014 Income Statement Flow",
                         ha="center", va="top", fontsize=20, fontweight="bold",
                         color="#0f172a")

                _draw_kpi_row(fig, [
                    ("Revenue", revenue), ("Gross Profit", gross_profit),
                    ("Operating Income", op_income), ("Net Income", net_income),
                ])

                ax = fig.add_axes([0.06, 0.05, 0.88, 0.78])
                _draw_sankey(ax, nodes, links, revenue)

                fig.text(0.5, 0.01,
                         f"QuarterCharts  \u00b7  SEC EDGAR data  \u00b7  {ticker}",
                         ha="center", va="bottom", fontsize=8, color="#94a3b8")
                pdf.savefig(fig, facecolor="white", dpi=150)
                plt.close(fig)

            else:
                # ── Balance Sheet Sankey ──
                total_assets      = _safe(balance_df, "Total Assets")
                if total_assets == 0:
                    return b""

                current_assets    = _safe(balance_df, "Current Assets")
                noncurrent_assets = _safe(balance_df, "Total Non Current Assets")
                cash              = _safe(balance_df, "Cash And Cash Equivalents")
                short_invest      = _safe(balance_df, "Other Short Term Investments")
                receivables       = _safe(balance_df, "Accounts Receivable") or _safe(balance_df, "Receivables")
                inventory         = _safe(balance_df, "Inventory")
                ppe               = _safe(balance_df, "Net PPE") or _safe(balance_df, "Property Plant Equipment")
                goodwill          = _safe(balance_df, "Goodwill")
                intangibles       = _safe(balance_df, "Intangible Assets") or _safe(balance_df, "Other Intangible Assets")
                investments       = _safe(balance_df, "Investments And Advances") or _safe(balance_df, "Long Term Equity Investment")

                total_liab        = _safe(balance_df, "Total Liabilities Net Minority Interest") or _safe(balance_df, "Total Liab")
                current_liab      = _safe(balance_df, "Current Liabilities")
                noncurrent_liab   = _safe(balance_df, "Total Non Current Liabilities Net Minority Interest")
                accounts_payable  = _safe(balance_df, "Accounts Payable") or _safe(balance_df, "Payables")
                short_debt        = _safe(balance_df, "Current Debt") or _safe(balance_df, "Short Long Term Debt")
                long_debt         = _safe(balance_df, "Long Term Debt")
                equity            = _safe(balance_df, "Stockholders Equity") or _safe(balance_df, "Total Stockholders Equity")
                retained          = _safe(balance_df, "Retained Earnings")

                if noncurrent_assets == 0 and total_assets > current_assets:
                    noncurrent_assets = total_assets - current_assets
                if noncurrent_liab == 0 and total_liab > current_liab:
                    noncurrent_liab = total_liab - current_liab
                if equity == 0 and total_assets > total_liab:
                    equity = total_assets - total_liab

                C = BS_COLORS
                nodes = []
                nmap = {}
                def add_n(name, val, x, y, color):
                    nmap[name] = len(nodes)
                    nodes.append((name, val, x, y, color))

                # Column 1: Total Assets
                add_n("Total Assets", total_assets, 0.02, 0.50, C["asset"])

                # Column 2: Current / Non-Current / Liabilities / Equity
                ca_y = 0.80
                nca_y = 0.55
                tl_y = 0.30
                eq_y = 0.10
                if current_assets > 0:
                    add_n("Current Assets", current_assets, 0.22, ca_y, C["asset"])
                if noncurrent_assets > 0:
                    add_n("Non-Current Assets", noncurrent_assets, 0.22, nca_y, C["asset2"])
                if total_liab > 0:
                    add_n("Total Liabilities", total_liab, 0.22, tl_y, C["liability"])
                if equity > 0:
                    add_n("Equity", equity, 0.22, eq_y, C["equity"])

                # Column 3: sub-categories
                y_pos = 0.92
                if cash > 0:
                    add_n("Cash", cash, 0.48, y_pos, C["cash"]); y_pos -= 0.11
                if receivables > 0:
                    add_n("Receivables", receivables, 0.48, y_pos, C["asset"]); y_pos -= 0.11
                if inventory > 0:
                    add_n("Inventory", inventory, 0.48, y_pos, C["asset2"]); y_pos -= 0.11
                if ppe > 0:
                    add_n("PPE", ppe, 0.48, y_pos, C["ppe"]); y_pos -= 0.11
                if goodwill > 0:
                    add_n("Goodwill", goodwill, 0.48, y_pos, C["invest"]); y_pos -= 0.11
                if current_liab > 0:
                    add_n("Current Liab.", current_liab, 0.48, y_pos, C["payable"]); y_pos -= 0.11
                if long_debt > 0:
                    add_n("Long-Term Debt", long_debt, 0.48, y_pos, C["debt"]); y_pos -= 0.11
                if retained > 0:
                    add_n("Retained Earnings", retained, 0.48, max(y_pos, 0.05), C["retained"])

                # ── Links ──
                links = []
                def lnk(s, t, v, color):
                    si, ti = nmap.get(s, -1), nmap.get(t, -1)
                    if si >= 0 and ti >= 0 and v > 0:
                        links.append((si, ti, v, color))

                if current_assets > 0:
                    lnk("Total Assets", "Current Assets", current_assets, C["asset"])
                if noncurrent_assets > 0:
                    lnk("Total Assets", "Non-Current Assets", noncurrent_assets, C["asset2"])
                if total_liab > 0:
                    lnk("Total Assets", "Total Liabilities", total_liab, C["liability"])
                if equity > 0:
                    lnk("Total Assets", "Equity", equity, C["equity"])

                # Current asset details
                if cash > 0:
                    lnk("Current Assets", "Cash", cash, C["cash"])
                if receivables > 0:
                    lnk("Current Assets", "Receivables", receivables, C["asset"])
                if inventory > 0:
                    lnk("Current Assets", "Inventory", inventory, C["asset2"])

                # Non-current details
                if ppe > 0:
                    lnk("Non-Current Assets", "PPE", ppe, C["ppe"])
                if goodwill > 0:
                    lnk("Non-Current Assets", "Goodwill", goodwill, C["invest"])

                # Liability details
                if current_liab > 0:
                    lnk("Total Liabilities", "Current Liab.", current_liab, C["payable"])
                if long_debt > 0:
                    lnk("Total Liabilities", "Long-Term Debt", long_debt, C["debt"])

                # Equity details
                if retained > 0:
                    lnk("Equity", "Retained Earnings", retained, C["retained"])

                # ── Draw figure ──
                fig = plt.figure(figsize=(16, 9), facecolor="white")
                if _logo_img is not None:
                    logo_ax2 = fig.add_axes([0.20, 0.93, 0.03, 0.05])
                    logo_ax2.imshow(_logo_img)
                    logo_ax2.axis("off")
                fig.text(0.5, 0.96,
                         f"{company} ({ticker}) \u2014 Balance Sheet Flow",
                         ha="center", va="top", fontsize=20, fontweight="bold",
                         color="#0f172a")

                _draw_kpi_row(fig, [
                    ("Total Assets", total_assets), ("Total Liabilities", total_liab),
                    ("Equity", equity), ("Cash", cash),
                ])

                ax = fig.add_axes([0.06, 0.05, 0.88, 0.78])
                _draw_sankey(ax, nodes, links, total_assets)

                fig.text(0.5, 0.01,
                         f"QuarterCharts  \u00b7  SEC EDGAR data  \u00b7  {ticker}",
                         ha="center", va="bottom", fontsize=8, color="#94a3b8")
                pdf.savefig(fig, facecolor="white", dpi=150)
                plt.close(fig)

    except Exception:
        return b""

    return buf.getvalue()


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_sankey_data(ticker: str, quarterly: bool = False):
    """Fetch income statement & balance sheet data from SEC EDGAR for Sankey diagrams."""
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return pd.DataFrame(), pd.DataFrame(), {"shortName": ticker}
        facts = _fetch_edgar_facts(cik)
        entity_name = facts.get("entityName", ticker.upper())
        income = _edgar_build_df(facts, _XBRL_INCOME_TAGS, form_filter="10-K")
        balance = _edgar_build_df(facts, _XBRL_BALANCE_TAGS, form_filter="10-K")
        info = {"shortName": entity_name, "longName": entity_name}
        return income, balance, info
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), {"shortName": ticker}


def _build_income_sankey(income_df, info):
    """Build income statement Sankey with fixed positions & 11 vivid nodes.

    Flow: Revenue → COGS + Gross Profit → R&D + SG&A + D&A + Operating Income
          → Interest + Pretax Income → Tax + Net Income
    """
    # ── Extract values ──
    revenue       = _safe(income_df, "Total Revenue")
    cogs          = abs(_safe(income_df, "Cost Of Revenue"))
    gross_profit  = _safe(income_df, "Gross Profit")
    rd_expense    = abs(_safe(income_df, "Research And Development"))
    sga_expense   = abs(_safe(income_df, "Selling General And Administration"))
    dep_amort     = abs(_safe(income_df, "Reconciled Depreciation"))
    if dep_amort == 0:
        dep_amort = abs(_safe(income_df, "Depreciation And Amortization"))
    other_opex    = abs(_safe(income_df, "Other Operating Expense"))
    operating_inc = _safe(income_df, "Operating Income")
    interest_exp  = abs(_safe(income_df, "Interest Expense"))
    pretax_income = _safe(income_df, "Pretax Income") or _safe(income_df, "Income Before Tax")
    tax           = abs(_safe(income_df, "Tax Provision"))
    net_income    = _safe(income_df, "Net Income")

    if revenue == 0:
        return None

    # Fix derived values
    if gross_profit == 0 and revenue > 0:
        gross_profit = revenue - cogs
    if operating_inc == 0 and gross_profit > 0:
        operating_inc = gross_profit - rd_expense - sga_expense - dep_amort - other_opex
    if pretax_income == 0:
        pretax_income = operating_inc - interest_exp
    if net_income == 0:
        net_income = pretax_income - tax

    # Ensure all positive
    revenue = max(revenue, 0)
    cogs = max(cogs, 0)
    gross_profit = max(gross_profit, 0)
    rd_expense = max(rd_expense, 0)
    sga_expense = max(sga_expense, 0)
    dep_amort = max(dep_amort, 0)
    other_opex = max(other_opex, 0)
    operating_inc = max(operating_inc, 0)
    interest_exp = max(interest_exp, 0)
    pretax_income = max(pretax_income, 0)
    tax = max(tax, 0)
    net_income = max(net_income, 0)

    # ── Fixed X/Y positions for precise layout ──
    X1, X2, X3, X4, X5 = 0.02, 0.25, 0.55, 0.78, 0.99
    colors = VIVID

    nodes = []
    node_colors = []
    node_x = []
    node_y = []
    imap = {}

    def add(name, val, color_idx, x, y):
        y = round(max(0.01, min(0.99, y)), 4)
        imap[name] = len(nodes)
        nodes.append(f"{name}  {_fmt(val)}")
        node_colors.append(colors[color_idx])
        node_x.append(x)
        node_y.append(y)

    # Column 1: Revenue
    add("Revenue", revenue, 0, X1, 0.45)

    # Column 2: COGS (top) + Gross Profit (bottom)
    add("Cost of Revenue", cogs, 1, X2, 0.05)
    add("Gross Profit", gross_profit, 2, X2, 0.58)

    # Column 3: Expenses (top) + Operating Income (bottom)
    exp_y = 0.04
    exp_gap = 0.13
    n_exp = 0
    if rd_expense > 0:
        add("R&D", rd_expense, 3, X3, exp_y + n_exp * exp_gap)
        n_exp += 1
    if sga_expense > 0:
        add("SG&A", sga_expense, 4, X3, exp_y + n_exp * exp_gap)
        n_exp += 1
    if dep_amort > 0:
        add("D&A", dep_amort, 5, X3, exp_y + n_exp * exp_gap)
        n_exp += 1
    if other_opex > 0:
        add("Other OpEx", other_opex, 5, X3, exp_y + n_exp * exp_gap)
        n_exp += 1

    oi_y = max(exp_y + n_exp * exp_gap + 0.16, 0.60)
    add("Operating Income", operating_inc, 6, X3, oi_y)

    # Column 4: Interest + Pretax Income
    if interest_exp > 0:
        inter_y = max(oi_y - 0.08, 0.50)
        add("Interest Exp.", interest_exp, 7, X4, inter_y)
    pt_y = oi_y + 0.14
    add("Pretax Income", pretax_income, 8, X4, pt_y)

    # Column 5: Tax + Net Income
    tax_y = pt_y + 0.04
    net_y = pt_y + 0.14
    if tax > 0:
        add("Income Tax", tax, 9, X5, min(tax_y, 0.88))
        net_y = tax_y + 0.12
    add("Net Income", net_income, 10, X5, min(net_y, 0.97))

    # ── Links ──
    srcs, tgts, vals, lcolors = [], [], [], []

    def link(src, tgt, val, ci=0):
        s, t = imap.get(src, -1), imap.get(tgt, -1)
        if s >= 0 and t >= 0 and val > 0:
            srcs.append(s)
            tgts.append(t)
            vals.append(val)
            lcolors.append(_rgba(colors[ci]))

    link("Revenue", "Cost of Revenue", cogs, 1)
    link("Revenue", "Gross Profit", gross_profit, 2)

    if rd_expense > 0:
        link("Gross Profit", "R&D", rd_expense, 3)
    if sga_expense > 0:
        link("Gross Profit", "SG&A", sga_expense, 4)
    if dep_amort > 0:
        link("Gross Profit", "D&A", dep_amort, 5)
    if other_opex > 0:
        link("Gross Profit", "Other OpEx", other_opex, 5)
    link("Gross Profit", "Operating Income", operating_inc, 6)

    if interest_exp > 0:
        link("Operating Income", "Interest Exp.", interest_exp, 7)
    link("Operating Income", "Pretax Income", pretax_income, 8)

    if tax > 0:
        link("Pretax Income", "Income Tax", tax, 9)
    link("Pretax Income", "Net Income", net_income, 10)

    if not vals:
        return None

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        textfont=dict(
            size=13,
            family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif",
            color="#1e293b",
        ),
        node=dict(
            pad=18,
            thickness=24,
            line=dict(color="rgba(0,0,0,0)", width=0),
            label=nodes,
            color=node_colors,
            x=node_x,
            y=node_y,
            hovertemplate="<b>%{label}</b><extra></extra>",
        ),
        link=dict(
            source=srcs,
            target=tgts,
            value=vals,
            color=lcolors,
            hovertemplate="Flow: %{value:$,.0f}<extra></extra>",
        ),
    ))

    fig.update_layout(
        height=650,
        margin=dict(l=10, r=10, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif", color="#1e293b"),
    )

    return fig


def _build_balance_sheet_sankey(balance_df, info):
    """Build a balance sheet Sankey with fixed positions — no node crossing.

    Layout (4 columns, top-to-bottom order matches link order):
      Col 1: Total Assets
      Col 2: Current Assets, Non-Current Assets, Total Liabilities, Equity
      Col 3: Sub-categories (CA details, NCA details, CL, NCL, Eq details)
      Col 4: Leaf details
    """
    # ── Extract values ──
    total_assets      = _safe(balance_df, "Total Assets")
    current_assets    = _safe(balance_df, "Current Assets")
    noncurrent_assets = _safe(balance_df, "Total Non Current Assets")
    cash              = _safe(balance_df, "Cash And Cash Equivalents")
    short_invest      = _safe(balance_df, "Other Short Term Investments")
    receivables       = _safe(balance_df, "Accounts Receivable") or _safe(balance_df, "Receivables")
    inventory         = _safe(balance_df, "Inventory")
    ppe               = _safe(balance_df, "Net PPE") or _safe(balance_df, "Property Plant Equipment")
    goodwill          = _safe(balance_df, "Goodwill")
    intangibles       = _safe(balance_df, "Intangible Assets") or _safe(balance_df, "Other Intangible Assets")
    investments       = _safe(balance_df, "Investments And Advances") or _safe(balance_df, "Long Term Equity Investment")

    total_liab        = _safe(balance_df, "Total Liabilities Net Minority Interest") or _safe(balance_df, "Total Liab")
    current_liab      = _safe(balance_df, "Current Liabilities")
    noncurrent_liab   = _safe(balance_df, "Total Non Current Liabilities Net Minority Interest")
    accounts_payable  = _safe(balance_df, "Accounts Payable") or _safe(balance_df, "Payables")
    short_debt        = _safe(balance_df, "Current Debt") or _safe(balance_df, "Short Long Term Debt")
    long_debt         = _safe(balance_df, "Long Term Debt")
    deferred_rev      = _safe(balance_df, "Current Deferred Revenue")

    equity            = _safe(balance_df, "Stockholders Equity") or _safe(balance_df, "Total Stockholders Equity")
    retained          = _safe(balance_df, "Retained Earnings")

    if total_assets == 0:
        return None

    # Fix derived
    if noncurrent_assets == 0 and total_assets > 0 and current_assets > 0:
        noncurrent_assets = total_assets - current_assets
    if noncurrent_liab == 0 and total_liab > 0 and current_liab > 0:
        noncurrent_liab = total_liab - current_liab
    if equity == 0 and total_assets > 0 and total_liab > 0:
        equity = total_assets - total_liab

    C = BS_COLORS

    # ── Node builder with position tracking ──
    nodes, node_colors_list, node_x, node_y = [], [], [], []
    links_src, links_tgt, links_val, links_col = [], [], [], []
    imap = {}

    def add(name, val, color, x, y):
        y = round(max(0.01, min(0.99, y)), 4)
        x = round(max(0.01, min(0.99, x)), 4)
        imap[name] = len(nodes)
        nodes.append(f"{name}  {_fmt(val)}")
        node_colors_list.append(color)
        node_x.append(x)
        node_y.append(y)
        return imap[name]

    def link(src_name, tgt_name, val, color):
        s, t = imap.get(src_name, -1), imap.get(tgt_name, -1)
        if s >= 0 and t >= 0 and val and val > 0:
            links_src.append(s)
            links_tgt.append(t)
            links_val.append(val)
            links_col.append(_rgba(color))

    # ── X columns ──
    X1, X2, X3, X4 = 0.01, 0.25, 0.55, 0.88

    # ────────────────────────────────────────────────────────────
    # SLOT-BASED LAYOUT: enumerate ALL leaf items in strict order,
    # assign uniform Y slots, then derive parent positions from
    # children's center.  This guarantees zero crossing.
    # ────────────────────────────────────────────────────────────

    # Build ordered item groups: (group_key, parent_col2_name, items_list)
    # Each item: (name, val, color)
    ca_items = []
    if cash > 0:
        ca_items.append(("Cash", cash, C["cash"]))
    if short_invest > 0:
        ca_items.append(("ST Investments", short_invest, C["invest"]))
    if receivables > 0:
        ca_items.append(("Receivables", receivables, C["asset"]))
    if inventory > 0:
        ca_items.append(("Inventory", inventory, C["asset"]))
    other_ca = max(0, current_assets - cash - short_invest - receivables - inventory)
    if other_ca > 0:
        ca_items.append(("Other Current", other_ca, C["other"]))

    nca_items = []
    if ppe > 0:
        nca_items.append(("PPE", ppe, C["ppe"]))
    if goodwill > 0:
        nca_items.append(("Goodwill", goodwill, C["asset2"]))
    if intangibles > 0:
        nca_items.append(("Intangibles", intangibles, C["asset2"]))
    if investments > 0:
        nca_items.append(("Investments", investments, C["invest"]))
    known_nca = ppe + goodwill + intangibles + investments
    other_nca = max(0, noncurrent_assets - known_nca)
    if other_nca > 0:
        nca_items.append(("Other Non-Current", other_nca, C["other"]))

    cl_items = []
    if accounts_payable > 0:
        cl_items.append(("Accounts Payable", accounts_payable, C["payable"]))
    if short_debt > 0:
        cl_items.append(("Short-Term Debt", short_debt, C["debt"]))
    if deferred_rev > 0:
        cl_items.append(("Deferred Revenue", deferred_rev, C["liability"]))
    known_cl = accounts_payable + short_debt + deferred_rev
    other_cl_val = max(0, current_liab - known_cl)
    if other_cl_val > 0:
        cl_items.append(("Other CL", other_cl_val, C["other"]))

    ncl_items = []
    if long_debt > 0:
        ncl_items.append(("Long-Term Debt", long_debt, C["debt"]))
    other_ncl = max(0, noncurrent_liab - long_debt)
    if other_ncl > 0:
        ncl_items.append(("Other LT Liab.", other_ncl, C["other"]))

    eq_items = []
    if equity > 0 and retained and retained > 0:
        eq_items.append(("Retained Earnings", retained, C["retained"]))
        other_eq = max(0, equity - retained)
        if other_eq > 0:
            eq_items.append(("Other Equity", other_eq, C["other"]))

    # Groups in strict top-to-bottom order
    # Each group: (col2_parent, col3_parent_or_None, items, col_for_items)
    groups = []
    if ca_items:
        groups.append(("Current Assets", None, ca_items, X3))
    if nca_items:
        groups.append(("Non-Current Assets", None, nca_items, X3))
    if cl_items:
        groups.append(("Total Liabilities", "Current Liab.", cl_items, X4))
    if ncl_items:
        groups.append(("Total Liabilities", "Non-Current Liab.", ncl_items, X4))
    if eq_items:
        groups.append(("Equity", None, eq_items, X3))

    # Count total slots (leaf items) + inter-group gaps
    total_leaf_items = sum(len(items) for _, _, items, _ in groups)
    n_groups = len(groups)
    gap_slots = 2  # each gap between groups = 2 empty slots worth of space

    total_slots = total_leaf_items + gap_slots * max(n_groups - 1, 0)
    if total_slots == 0:
        total_slots = 1

    slot_height = 0.96 / total_slots  # Y range [0.02, 0.98]

    # Assign Y positions to all leaf items, record group Y ranges
    slot_idx = 0
    group_y_ranges = []  # (y_first, y_last) for each group

    for g_idx, (col2_parent, col3_parent, items, x_col) in enumerate(groups):
        y_first = 0.02 + slot_idx * slot_height
        for i, (nm, vl, cl) in enumerate(items):
            y = 0.02 + slot_idx * slot_height
            add(nm, vl, cl, x_col, y)
            slot_idx += 1
        y_last = 0.02 + (slot_idx - 1) * slot_height
        group_y_ranges.append((y_first, y_last))
        if g_idx < n_groups - 1:
            slot_idx += gap_slots  # skip gap

    # ── Place Col 3 intermediate nodes (Current Liab., Non-Current Liab.) ──
    # and Col 2 parent nodes at the center of their children
    col2_parent_ys = {}  # parent_name -> center_y

    for g_idx, (col2_parent, col3_parent, items, x_col) in enumerate(groups):
        y_first, y_last = group_y_ranges[g_idx]
        y_center = (y_first + y_last) / 2

        if col3_parent is not None:
            # This group has an intermediate node (e.g., "Current Liab.")
            # Place it at the center of its children
            if col3_parent == "Current Liab." and current_liab > 0:
                add("Current Liab.", current_liab, C["liability"], X3, y_center)
            elif col3_parent == "Non-Current Liab." and noncurrent_liab > 0:
                add("Non-Current Liab.", noncurrent_liab, C["liability"], X3, y_center)

        # Track Col 2 parent center (may span multiple groups)
        if col2_parent not in col2_parent_ys:
            col2_parent_ys[col2_parent] = [y_center]
        else:
            col2_parent_ys[col2_parent].append(y_center)

    # Place Col 2 parents at the mean center of all their groups
    for parent_name, centers in col2_parent_ys.items():
        y = sum(centers) / len(centers)
        if parent_name == "Current Assets":
            add("Current Assets", current_assets, C["asset"], X2, y)
        elif parent_name == "Non-Current Assets":
            add("Non-Current Assets", noncurrent_assets, C["asset2"], X2, y)
        elif parent_name == "Total Liabilities":
            add("Total Liabilities", total_liab, C["liability"], X2, y)
        elif parent_name == "Equity":
            add("Equity", equity, C["equity"], X2, y)

    # Place Col 1: Total Assets at the overall center
    all_col2_ys = sorted(col2_parent_ys.items(),
                         key=lambda kv: sum(kv[1]) / len(kv[1]))
    overall_y = sum(sum(v) / len(v) for _, v in all_col2_ys) / max(len(all_col2_ys), 1)
    add("Total Assets", total_assets, C["asset"], X1, overall_y)

    # ── Create ALL links in strict top-to-bottom order ──
    # Col 1 → Col 2 links (in Y order of Col 2 targets)
    col2_ordered = sorted(col2_parent_ys.keys(),
                          key=lambda k: sum(col2_parent_ys[k]) / len(col2_parent_ys[k]))
    for parent_name in col2_ordered:
        if parent_name == "Current Assets":
            link("Total Assets", "Current Assets", current_assets, C["asset"])
        elif parent_name == "Non-Current Assets":
            link("Total Assets", "Non-Current Assets", noncurrent_assets, C["asset2"])
        elif parent_name == "Total Liabilities":
            link("Total Assets", "Total Liabilities", total_liab, C["liability"])
        elif parent_name == "Equity":
            link("Total Assets", "Equity", equity, C["equity"])

    # Col 2 → Col 3/Col 4 links (per group, in order)
    for g_idx, (col2_parent, col3_parent, items, x_col) in enumerate(groups):
        if col3_parent is not None:
            # Col 2 → Col 3 intermediate
            if col3_parent == "Current Liab.":
                link("Total Liabilities", "Current Liab.", current_liab, C["liability"])
            elif col3_parent == "Non-Current Liab.":
                link("Total Liabilities", "Non-Current Liab.", noncurrent_liab, C["liability"])
            # Col 3 intermediate → Col 4 leaf items
            link_parent = col3_parent
        else:
            link_parent = col2_parent

        for nm, vl, cl in items:
            if vl and vl > 0:
                link(link_parent, nm, vl, cl)

    if not links_val:
        return None

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        textfont=dict(
            size=13,
            family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif",
            color="#1e293b",
        ),
        node=dict(
            pad=18,
            thickness=24,
            line=dict(color="rgba(0,0,0,0)", width=0),
            label=nodes,
            color=node_colors_list,
            x=node_x,
            y=node_y,
            hovertemplate="<b>%{label}</b><extra></extra>",
        ),
        link=dict(
            source=links_src,
            target=links_tgt,
            value=links_val,
            color=links_col,
            hovertemplate="Flow: %{value:$,.0f}<extra></extra>",
        ),
    ))

    fig.update_layout(
        height=700,
        margin=dict(l=10, r=10, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif", color="#1e293b"),
    )

    return fig


def render_sankey_page():
    """Render the Sankey diagram page."""
    ticker = st.session_state.get("ticker", "AAPL")

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        .sankey-header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-radius: 12px;
            padding: 24px 28px 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.06);
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
        }
        .sankey-header-left {
            flex: 1;
        }
        .sankey-title {
            font-size: 1.6rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 4px;
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sankey-company-logo {
            height: 32px;
            width: 32px;
            object-fit: contain;
            border-radius: 6px;
            background: #fff;
        }
        .sankey-subtitle {
            color: #94a3b8;
            font-size: 0.9rem;
        }
        /* ── Sankey header row: title + PDF download button ── */
        /* Target the stHorizontalBlock that contains the PDF download key */
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]),
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            padding: 8px 4px !important;
            gap: 0 !important;
            align-items: center !important;
            margin-bottom: 4px !important;
        }
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]) [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) [data-testid="stColumn"] {
            padding: 0 !important;
        }
        /* Make inner header transparent since row provides the dark bg */
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]) .sankey-header,
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) .sankey-header {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            margin-bottom: 0 !important;
        }
        /* PDF download button inside header row */
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]) [data-testid="stDownloadButton"] button,
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) [data-testid="stButton"] button {
            background: rgba(255,255,255,0.13) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.28) !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            padding: 5px 14px !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            min-height: 0 !important;
            height: auto !important;
            line-height: 1.4 !important;
            white-space: nowrap !important;
        }
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]) [data-testid="stDownloadButton"] button:hover,
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) [data-testid="stButton"] button:hover {
            background: rgba(255,255,255,0.24) !important;
            border-color: rgba(255,255,255,0.45) !important;
        }
        /* Remove extra margins inside PDF column */
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]) [data-testid="stDownloadButton"],
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) [data-testid="stButton"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        .sankey-tab-container {
            display: flex;
            gap: 0;
            margin-bottom: 1rem;
        }
        .sankey-tab {
            padding: 11px 32px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            border: 1.5px solid #e2e8f0;
            background: #f8fafc;
            color: #64748b;
            text-decoration: none;
            transition: all 0.25s ease;
            letter-spacing: -0.01em;
        }
        .sankey-tab:first-child {
            border-radius: 10px 0 0 10px;
        }
        .sankey-tab:last-child {
            border-radius: 0 10px 10px 0;
            border-left: none;
        }
        .sankey-tab.active {
            background: linear-gradient(135deg, #1e293b, #334155);
            color: #f1f5f9;
            border-color: #1e293b;
            box-shadow: 0 2px 8px rgba(30,41,59,0.25);
        }
        .sankey-tab:hover:not(.active) {
            background: #e2e8f0;
            color: #334155;
        }
        div[data-testid="metric-container"] {
            background: #1e1e2e;
            border-radius: 12px;
            padding: 14px 18px;
            border: 1px solid #2d2d42;
        }
        .sankey-legend {
            display: flex;
            gap: 28px;
            margin-top: 12px;
            padding: 12px 16px;
            background: #f8fafc;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            font-size: 0.85rem;
            color: #475569;
        }
        .sankey-legend span {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .legend-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        /* ── Sankey Responsive ── */
        @media (max-width: 768px) {
            .sankey-header {
                padding: 16px 14px 14px !important;
                flex-direction: column !important;
                gap: 8px !important;
            }
            .sankey-title {
                font-size: 1.2rem !important;
            }
            .sankey-company-logo {
                height: 26px !important;
                width: 26px !important;
            }
            .sankey-subtitle {
                font-size: 0.8rem !important;
            }
            .sankey-tab {
                padding: 9px 16px !important;
                font-size: 0.82rem !important;
            }
            .sankey-legend {
                flex-wrap: wrap !important;
                gap: 12px !important;
                padding: 10px 12px !important;
                font-size: 0.78rem !important;
            }
            div[data-testid="metric-container"] {
                padding: 10px 12px !important;
            }
            [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]),
            [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) {
                padding: 6px 4px !important;
            }
        }
        @media (max-width: 480px) {
            .sankey-header {
                padding: 12px 10px !important;
                border-radius: 8px !important;
            }
            .sankey-title {
                font-size: 1rem !important;
            }
            .sankey-tab-container {
                flex-wrap: wrap !important;
            }
            .sankey-tab {
                padding: 8px 12px !important;
                font-size: 0.78rem !important;
                flex: 1 !important;
                text-align: center !important;
            }
            .sankey-tab:first-child {
                border-radius: 8px 0 0 8px !important;
            }
            .sankey-tab:last-child {
                border-radius: 0 8px 8px 0 !important;
            }
            .sankey-legend {
                gap: 8px !important;
                font-size: 0.72rem !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # Fetch data
    using_demo = False
    with st.spinner(f"Loading {ticker} financial data..."):
        try:
            _sq = st.session_state.get("sankey_compare_quarterly", False)
            income_df, balance_df, info = _fetch_sankey_data(ticker, quarterly=_sq)
        except Exception:
            income_df, balance_df, info = pd.DataFrame(), pd.DataFrame(), {"shortName": ticker}

    # If data is empty (rate-limited), fall back to demo data
    if income_df.empty and balance_df.empty:
        income_df, balance_df, info = _get_demo_data(ticker)
        using_demo = True
        st.info(f"\ud83d\udcc8 Showing sample data for **{ticker.upper()}** \u2013 SEC EDGAR data is temporarily unavailable. Refresh in a minute for live data.")

    # --- Period comparison (from sidebar selectors) ---
    _pa = st.session_state.get("sankey_period_a", None)
    _pb = st.session_state.get("sankey_period_b", None)
    _sq2 = st.session_state.get("sankey_compare_quarterly", False)
    if _pa and _pb and _pa != _pb:
        income_df = _reorder_df_for_comparison(income_df, _pa, _pb, _sq2)
        balance_df = _reorder_df_for_comparison(balance_df, _pa, _pb, _sq2)
        _compare_label = f"vs {_pb}"
        _compare_note = f"Comparing {_pa} vs {_pb}"
    else:
        _compare_label = "YoY"
        _compare_note = None

    company_name = info.get("shortName", info.get("longName", ticker))

    # Tab selection
    sankey_view = st.session_state.get("sankey_view", "income")
    qp_view = st.query_params.get("view", "").lower()
    if qp_view in ("income", "balance"):
        sankey_view = qp_view
        st.session_state.sankey_view = sankey_view

    view_label = "Income Statement" if sankey_view == "income" else "Balance Sheet"

    # ── Header row: title (HTML) + PDF download button (st.download_button) ──
    hdr_col, pdf_col = st.columns([0.87, 0.13])

    with hdr_col:
        st.markdown(f"""
        <div class="sankey-header">
            <div class="sankey-header-left">
                <div class="sankey-title"><img src="https://financialmodelingprep.com/image-stock/{ticker.upper()}.png" class="sankey-company-logo" onerror="this.style.display='none'"> {company_name} — Sankey Diagram</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with pdf_col:
        # Pre-generate or retrieve cached PDF
        _pdf_key = f"_sankey_pdf_v3_{ticker}_{sankey_view}"
        if not st.session_state.get(_pdf_key):
            _pdf_bytes = _generate_sankey_pdf(income_df, balance_df, info, ticker, sankey_view)
            if _pdf_bytes:
                st.session_state[_pdf_key] = _pdf_bytes

        if st.session_state.get(_pdf_key):
            try:
                st.download_button(
                    label="PDF",
                    data=st.session_state[_pdf_key],
                    file_name=f"{ticker}_{sankey_view}_sankey.pdf",
                    mime="application/pdf",
                    icon=":material/download:",
                    key=f"dl_sankey_{sankey_view}",
                )
            except TypeError:
                st.download_button(
                    label="⬇ PDF",
                    data=st.session_state[_pdf_key],
                    file_name=f"{ticker}_{sankey_view}_sankey.pdf",
                    mime="application/pdf",
                    key=f"dl_sankey_{sankey_view}",
                )
        else:
            try:
                st.button("PDF", key=f"gen_pdf_sankey_{sankey_view}",
                          icon=":material/download:", disabled=True)
            except TypeError:
                st.button("PDF", key=f"gen_pdf_sankey_{sankey_view}",
                          disabled=True)

    st.markdown(f"""
    <div class="sankey-tab-container">
        <a class="sankey-tab {'active' if sankey_view == 'income' else ''}"
           href="?page=sankey&ticker={ticker}&view=income" target="_self">Income Statement</a>
        <a class="sankey-tab {'active' if sankey_view == 'balance' else ''}"
           href="?page=sankey&ticker={ticker}&view=balance" target="_self">Balance Sheet</a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div style="text-align:center;color:#888;font-size:0.85rem;margin-top:-0.5rem;margin-bottom:0.5rem">{_compare_note + " · " if _compare_note else ""}Annual financial flow visualization</div>', unsafe_allow_html=True)

    if sankey_view == "income":
        # ── Historical trend selector (popup) ──
        metric_options = list(INCOME_NODE_METRICS.keys())
        sel = st.pills("📈 Click a metric to see historical trend",
                       metric_options, key="income_metric_pill")
        if sel:
            # Track active metric in popup (allows navigation inside dialog)
            if f"popup_active_income" not in st.session_state or st.session_state.get("popup_trigger_income") != sel:
                st.session_state["popup_active_income"] = sel
                st.session_state["popup_trigger_income"] = sel
            active_metric = st.session_state["popup_active_income"]
            @st.dialog(f"{active_metric} — Historical Trend", width="large")
            def _income_popup():
                _show_metric_popup(ticker, active_metric, "income")
            _income_popup()

        # ── KPI Metric Cards ──
        revenue      = _safe(income_df, "Total Revenue")
        gross_profit = _safe(income_df, "Gross Profit")
        cogs_kpi     = abs(_safe(income_df, "Cost Of Revenue"))
        op_income    = _safe(income_df, "Operating Income")
        net_income   = _safe(income_df, "Net Income")
        rev_prev     = _safe_prev(income_df, "Total Revenue")
        gp_prev      = _safe_prev(income_df, "Gross Profit")
        oi_prev      = _safe_prev(income_df, "Operating Income")
        ni_prev      = _safe_prev(income_df, "Net Income")
        # Compute derived Gross Profit when XBRL tag is missing
        if gross_profit == 0 and revenue > 0 and cogs_kpi > 0:
            gross_profit = revenue - cogs_kpi
        if gp_prev == 0 and rev_prev > 0:
            cogs_prev = abs(_safe_prev(income_df, "Cost Of Revenue"))
            if cogs_prev > 0:
                gp_prev = rev_prev - cogs_prev

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Revenue", _fmt(revenue), _yoy_delta(revenue, rev_prev, _compare_label))
        m2.metric("Gross Profit", _fmt(gross_profit), _yoy_delta(gross_profit, gp_prev, _compare_label))
        m3.metric("Operating Income", _fmt(op_income), _yoy_delta(op_income, oi_prev, _compare_label))
        m4.metric("Net Income", _fmt(net_income), _yoy_delta(net_income, ni_prev, _compare_label))

        st.divider()

        fig = _build_income_sankey(income_df, info)
        if fig:

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtons": [["toImage"]]})

            # Bridge: click Sankey node → auto-click matching pill
            _inject_sankey_click_js(INCOME_NODE_METRICS)
        else:
            st.warning(f"No income statement data available for {ticker}.")

        st.caption(f"📊 QuarterCharts · SEC EDGAR data · {ticker}" + (f" \u00b7 {_compare_note}" if _compare_note else ""))

    elif sankey_view == "balance":
        # ── Historical trend selector (popup) ──
        metric_options = list(BALANCE_NODE_METRICS.keys())
        sel = st.pills("📈 Click a metric to see historical trend",
                       metric_options, key="balance_metric_pill")
        if sel:
            # Track active metric in popup (allows navigation inside dialog)
            if f"popup_active_balance" not in st.session_state or st.session_state.get("popup_trigger_balance") != sel:
                st.session_state["popup_active_balance"] = sel
                st.session_state["popup_trigger_balance"] = sel
            active_metric = st.session_state["popup_active_balance"]
            @st.dialog(f"{active_metric} — Historical Trend", width="large")
            def _balance_popup():
                _show_metric_popup(ticker, active_metric, "balance")
            _balance_popup()

        # ── KPI Metric Cards for Balance Sheet ──
        total_assets = _safe(balance_df, "Total Assets")
        total_liab   = _safe(balance_df, "Total Liabilities Net Minority Interest") or _safe(balance_df, "Total Liab")
        equity_val   = _safe(balance_df, "Stockholders Equity") or _safe(balance_df, "Total Stockholders Equity")
        cash_val     = _safe(balance_df, "Cash And Cash Equivalents")
        ta_prev      = _safe_prev(balance_df, "Total Assets")
        tl_prev      = _safe_prev(balance_df, "Total Liabilities Net Minority Interest") or _safe_prev(balance_df, "Total Liab")
        eq_prev      = _safe_prev(balance_df, "Stockholders Equity") or _safe_prev(balance_df, "Total Stockholders Equity")
        cash_prev    = _safe_prev(balance_df, "Cash And Cash Equivalents")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Assets", _fmt(total_assets), _yoy_delta(total_assets, ta_prev, _compare_label))
        m2.metric("Total Liabilities", _fmt(total_liab), _yoy_delta(total_liab, tl_prev, _compare_label))
        m3.metric("Equity", _fmt(equity_val), _yoy_delta(equity_val, eq_prev, _compare_label))
        m4.metric("Cash", _fmt(cash_val), _yoy_delta(cash_val, cash_prev, _compare_label))

        st.divider()

        fig = _build_balance_sheet_sankey(balance_df, info)
        if fig:

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtons": [["toImage"]]})

            # Bridge: click Sankey node → auto-click matching pill
            _inject_sankey_click_js(BALANCE_NODE_METRICS)
        else:
            st.warning(f"No balance sheet data available for {ticker}.")

        st.caption(f"📊 QuarterCharts · SEC EDGAR data · {ticker}" + (f" \u00b7 {_compare_note}" if _compare_note else ""))
