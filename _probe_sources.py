"""
Probe script — test SEC EDGAR → FMP → Finnhub → QuarterChart.com fallback chain
for 6 chart tasks across 7 tickers.

Output:
    /sessions/lucid-eloquent-euler/probe_results.json   (raw per-task results)
    /sessions/lucid-eloquent-euler/probe_results.md     (human-readable table)
    /sessions/lucid-eloquent-euler/probe.log            (stdout log, via shell)

Tasks tested (quarterly data, expect ~8+ quarters to count as complete):
  T1 Product segments            (QC chart_index 0)
  T2 Geographic segments         (QC chart_index 1)
  T3 EBITDA                      (QC chart_index 5)
  T4 Income waterfall            (QC chart_index 12)
  T5 Expense ratios              (QC chart_index 14)
  T6 Per-share (EPS/BV/Cash/FCF) (QC chart_index 13)
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")

import data_fetcher as DF  # noqa: E402
import requests as _rq  # noqa: E402

TICKERS = ["AAPL", "AMZN", "GOOG", "KO", "MSFT", "NVDA", "TSLA"]
if len(sys.argv) > 1:
    TICKERS = [t.upper() for t in sys.argv[1:]]
MIN_PERIODS = 4

OUT_JSON = "/sessions/lucid-eloquent-euler/probe_results.json"
OUT_MD = "/sessions/lucid-eloquent-euler/probe_results.md"
# Fallback to local workspace if run on Mac (the above path won't exist)
if not os.path.isdir(os.path.dirname(OUT_JSON)):
    OUT_JSON = os.path.join(os.path.expanduser("~"), "Desktop", "OpenTF", "probe_results.json")
    OUT_MD = os.path.join(os.path.expanduser("~"), "Desktop", "OpenTF", "probe_results.md")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_df(df: Optional[pd.DataFrame], min_rows: int = MIN_PERIODS) -> Tuple[bool, str]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return False, "empty/None"
    if len(df) < min_rows:
        return False, f"only {len(df)} periods (<{min_rows})"
    return True, f"{len(df)} periods, {len(df.columns)} cols"


def _ok_segments(d: Any, min_rows: int = MIN_PERIODS) -> Tuple[bool, str]:
    if d is None:
        return False, "None"
    if isinstance(d, dict):
        if not d:
            return False, "empty dict"
        nonempty = {k: v for k, v in d.items() if isinstance(v, pd.DataFrame) and not v.empty}
        if not nonempty:
            return False, "all segments empty"
        for k, v in nonempty.items():
            if len(v) < min_rows:
                return False, f"'{k}' only {len(v)} periods"
            if v.shape[1] < 2:
                return False, f"'{k}' only {v.shape[1]} segment cols"
        return True, f"{len(nonempty)} type(s), ~{max(len(v) for v in nonempty.values())} periods"
    if isinstance(d, pd.DataFrame):
        if d.empty:
            return False, "empty DF"
        if len(d) < min_rows:
            return False, f"only {len(d)} periods"
        if d.shape[1] < 2:
            return False, f"only {d.shape[1]} segment columns"
        return True, f"{len(d)} periods, {d.shape[1]} segments"
    return False, f"unexpected type {type(d).__name__}"


# ---------------------------------------------------------------------------
# Source 1 — SEC EDGAR
# ---------------------------------------------------------------------------

def fetch_sec(ticker: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": "sec"}
    try:
        out["income"] = DF._sec_get_income_statement(ticker, quarterly=True)
    except Exception as e:
        out["income_err"] = str(e); out["income"] = pd.DataFrame()
    try:
        out["balance"] = DF._sec_get_balance_sheet(ticker, quarterly=True)
    except Exception as e:
        out["balance_err"] = str(e); out["balance"] = pd.DataFrame()
    try:
        out["cashflow"] = DF._sec_get_cash_flow(ticker, quarterly=True)
    except Exception as e:
        out["cashflow_err"] = str(e); out["cashflow"] = pd.DataFrame()
    try:
        seg = DF._sec_get_segment_revenue(ticker, quarterly=True) or {}
    except Exception as e:
        seg = {}; out["seg_err"] = str(e)
    out["seg_product"] = seg.get("product") if isinstance(seg, dict) else None
    # `_sec_get_segment_revenue` returns the key as "geography" (not
    # "geographic"). Prefer the canonical key; fall back to the misspelled
    # variant only if "geography" is missing (NOT merely empty — empty
    # DataFrames are falsy, so a truthy-or would skip past them).
    if isinstance(seg, dict):
        _geo = seg.get("geography")
        out["seg_geo"] = _geo if _geo is not None else seg.get("geographic")
    else:
        out["seg_geo"] = None

    # Diluted shares from companyfacts
    try:
        facts = DF._sec_fetch_company_facts(ticker) or {}
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        out["shares_have"] = any(k in us_gaap for k in (
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingDiluted",
        ))
    except Exception as e:
        out["shares_have"] = False; out["shares_err"] = str(e)
    return out


# ---------------------------------------------------------------------------
# Source 2 — FMP
# ---------------------------------------------------------------------------

def fetch_fmp(ticker: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": "fmp"}
    if not DF._fmp_available():
        out["skip"] = "no FMP_API_KEY"
        for k in ("income", "balance", "cashflow"):
            out[k] = pd.DataFrame()
        out["seg_product"] = None; out["seg_geo"] = None; out["shares_have"] = False
        return out
    try:
        raw = DF._fetch_fmp_statement(ticker, "income-statement", limit=20, quarterly=True)
        out["income"] = DF._fmp_json_to_df(raw, DF._FMP_INCOME_MAP, quarterly=True) if raw else pd.DataFrame()
    except Exception as e:
        out["income_err"] = str(e); out["income"] = pd.DataFrame()
    try:
        raw = DF._fetch_fmp_statement(ticker, "balance-sheet-statement", limit=20, quarterly=True)
        out["balance"] = DF._fmp_json_to_df(raw, DF._FMP_BS_MAP, quarterly=True) if raw else pd.DataFrame()
    except Exception as e:
        out["balance_err"] = str(e); out["balance"] = pd.DataFrame()
    try:
        raw = DF._fetch_fmp_statement(ticker, "cash-flow-statement", limit=20, quarterly=True)
        out["cashflow"] = DF._fmp_json_to_df(raw, DF._FMP_CF_MAP, quarterly=True) if raw else pd.DataFrame()
    except Exception as e:
        out["cashflow_err"] = str(e); out["cashflow"] = pd.DataFrame()
    try:
        out["seg_product"] = DF._fmp_get_segments(ticker, "product", quarterly=True)
    except Exception as e:
        out["seg_product_err"] = str(e); out["seg_product"] = None
    try:
        out["seg_geo"] = DF._fmp_get_segments(ticker, "geographic", quarterly=True)
    except Exception as e:
        out["seg_geo_err"] = str(e); out["seg_geo"] = None
    inc = out.get("income")
    out["shares_have"] = bool(
        isinstance(inc, pd.DataFrame)
        and any("Diluted" in c and "Shares" in c for c in inc.columns)
    )
    return out


# ---------------------------------------------------------------------------
# Source 3 — Finnhub (/stock/financials-reported)
# ---------------------------------------------------------------------------

_FH_INCOME_MAP = {
    "Revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "Cost of Revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "Gross Profit": ["GrossProfit"],
    "Operating Expenses": ["OperatingExpenses"],
    "Operating Income": ["OperatingIncomeLoss"],
    "R&D": ["ResearchAndDevelopmentExpense"],
    "SG&A": ["SellingGeneralAndAdministrativeExpense"],
    "Net Income": ["NetIncomeLoss"],
    "Diluted EPS": ["EarningsPerShareDiluted"],
    "Diluted Shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}
_FH_BS_MAP = {
    "Total Assets": ["Assets"],
    "Total Liabilities": ["Liabilities"],
    "Stockholders Equity": ["StockholdersEquity",
                             "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "Cash and Cash Equivalents": ["CashAndCashEquivalentsAtCarryingValue", "Cash"],
}
_FH_CF_MAP = {
    "Operating Cash Flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "Capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "Depreciation & Amortization": ["DepreciationDepletionAndAmortization",
                                     "DepreciationAndAmortization", "Depreciation"],
}


def _finnhub_fetch(ticker: str) -> List[dict]:
    try:
        r = _rq.get(
            "https://finnhub.io/api/v1/stock/financials-reported",
            params={"symbol": ticker.upper(), "freq": "quarterly", "token": DF._finnhub_key()},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        return (r.json() or {}).get("data", []) or []
    except Exception:
        return []


def _fh_build_df(data: List[dict], section: str, field_map: Dict[str, List[str]]) -> pd.DataFrame:
    rows: Dict[str, Dict[str, float]] = {}
    for rec in data:
        q, y = rec.get("quarter"), rec.get("year")
        if not (q and y):
            continue
        try:
            q, y = int(q), int(y)
        except Exception:
            continue
        label = f"Q{q} {y}"
        report = (rec.get("report") or {}).get(section, []) or []
        row: Dict[str, float] = {}
        for item in report:
            concept = str(item.get("concept", "")).replace("us-gaap:", "").replace("us-gaap_", "")
            try:
                val = float(item.get("value"))
            except Exception:
                continue
            for out_name, cands in field_map.items():
                if concept in cands and out_name not in row:
                    row[out_name] = val
        if row:
            rows[label] = row
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(rows, orient="index")

    def _k(lbl):
        try:
            p = lbl.split()
            return (int(p[1]), int(p[0][1:]))
        except Exception:
            return (0, 0)

    df = df.reindex(sorted(df.index, key=_k))
    return df


def fetch_finnhub(ticker: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"source": "finnhub"}
    data = _finnhub_fetch(ticker)
    if not data:
        for k in ("income", "balance", "cashflow"):
            out[k] = pd.DataFrame()
        out["seg_product"] = None; out["seg_geo"] = None; out["shares_have"] = False
        out["note"] = "financials-reported returned empty (plan-gated or unavailable)"
        return out
    out["income"] = _fh_build_df(data, "ic", _FH_INCOME_MAP)
    out["balance"] = _fh_build_df(data, "bs", _FH_BS_MAP)
    out["cashflow"] = _fh_build_df(data, "cf", _FH_CF_MAP)
    out["seg_product"] = None
    out["seg_geo"] = None
    inc = out["income"]
    out["shares_have"] = isinstance(inc, pd.DataFrame) and ("Diluted Shares" in inc.columns)
    return out


# ---------------------------------------------------------------------------
# Source 4 — QuarterChart.com (task-specific chart_index)
# ---------------------------------------------------------------------------
# chart_index mapping used throughout the app:
#   0  = product segments
#   1  = geographic segments
#   5  = EBITDA
#   12 = income breakdown / waterfall
#   13 = per-share
#   14 = expense ratios

def fetch_qc_chart(ticker: str, idx: int) -> Optional[pd.DataFrame]:
    try:
        df = DF._opensankey_get_segments(ticker, idx, quarterly=True)
        return df
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Task-level completeness checks
# ---------------------------------------------------------------------------

def check_t3_ebitda(src: Dict[str, Any]) -> Tuple[bool, str]:
    """EBITDA = Operating Income + D&A from income + cashflow."""
    inc = src.get("income"); cf = src.get("cashflow")
    if not isinstance(inc, pd.DataFrame) or inc.empty:
        return False, "no income DF"
    if not isinstance(cf, pd.DataFrame) or cf.empty:
        return False, "no cashflow DF"
    op_cols = [c for c in inc.columns if "Operating Income" in c or "OperatingIncome" in c]
    if not op_cols:
        return False, "no Operating Income col in income"
    da_cols = [c for c in cf.columns if "Depreciation" in c or "D&A" in c or "Amortization" in c]
    if not da_cols:
        return False, "no D&A col in cashflow"
    overlap = set(inc.index) & set(cf.index)
    if len(overlap) < MIN_PERIODS:
        return False, f"only {len(overlap)} overlapping quarters"
    return True, f"OI+D&A, {len(overlap)} overlapping quarters"


def check_t4_waterfall(src: Dict[str, Any]) -> Tuple[bool, str]:
    inc = src.get("income")
    if not isinstance(inc, pd.DataFrame) or inc.empty:
        return False, "no income DF"
    required = {
        "Revenue": ["Total Revenue", "Revenue", "Revenues"],
        "COGS": ["Cost of Revenue", "Cost Of Revenue", "CostOfRevenue", "COGS"],
        "Gross Profit": ["Gross Profit", "GrossProfit"],
        "OpInc": ["Operating Income", "OperatingIncome", "Operating Income Loss"],
        "NetInc": ["Net Income", "NetIncome", "Net Income Loss"],
    }
    missing = [label for label, cands in required.items() if not any(c in inc.columns for c in cands)]
    if missing:
        return False, f"missing: {missing}"
    if len(inc) < MIN_PERIODS:
        return False, f"only {len(inc)} periods"
    return True, f"5 waterfall fields, {len(inc)} periods"


def check_t5_expense_ratios(src: Dict[str, Any]) -> Tuple[bool, str]:
    inc = src.get("income")
    if not isinstance(inc, pd.DataFrame) or inc.empty:
        return False, "no income DF"
    if not any(c in inc.columns for c in ["Total Revenue", "Revenue", "Revenues"]):
        return False, "no Revenue col"
    exp_cols = [c for c in inc.columns if any(k in c for k in (
        "Cost", "R&D", "Research", "SG&A", "Selling", "Operating Expenses"
    ))]
    if len(exp_cols) < 2:
        return False, f"only {len(exp_cols)} expense cols"
    if len(inc) < MIN_PERIODS:
        return False, f"only {len(inc)} periods"
    return True, f"{len(exp_cols)} expense cols, {len(inc)} periods"


def check_t6_per_share(src: Dict[str, Any]) -> Tuple[bool, str]:
    inc = src.get("income"); bs = src.get("balance")
    if not isinstance(inc, pd.DataFrame) or inc.empty:
        return False, "no income DF"
    if not src.get("shares_have"):
        return False, "no Diluted Shares"
    if not isinstance(bs, pd.DataFrame) or bs.empty:
        return False, "no balance DF (for BV/share)"
    return True, "income + shares + balance present"


# ---------------------------------------------------------------------------
# Main probe
# ---------------------------------------------------------------------------

def probe_ticker(ticker: str) -> Dict[str, Any]:
    print(f"\n=== {ticker} ===", flush=True)

    # Fetch for sources 1-3 (unified shape)
    sources: Dict[str, Dict[str, Any]] = {}
    for fn, name in [(fetch_sec, "sec"), (fetch_fmp, "fmp"), (fetch_finnhub, "finnhub")]:
        print(f"  {name}...", flush=True)
        t0 = time.time()
        try:
            sources[name] = fn(ticker)
        except Exception as e:
            sources[name] = {"source": name, "fatal": f"{e}",
                             "traceback": traceback.format_exc()[:400]}
        print(f"    {name}: {time.time()-t0:.1f}s", flush=True)
        time.sleep(0.3)

    # QC: fetch once per task's chart_index
    print(f"  qc...", flush=True)
    qc_raw = {
        "T1_product_segments": fetch_qc_chart(ticker, 0),
        "T2_geo_segments":     fetch_qc_chart(ticker, 1),
        "T3_ebitda":           fetch_qc_chart(ticker, 5),
        "T4_waterfall":        fetch_qc_chart(ticker, 12),
        "T5_expense_ratios":   fetch_qc_chart(ticker, 14),
        "T6_per_share":        fetch_qc_chart(ticker, 13),
    }

    result: Dict[str, Any] = {"ticker": ticker, "tasks": {}}

    # Checks per task for sources 1-3 (structured data)
    task_checks = [
        ("T1_product_segments", lambda s: _ok_segments(s.get("seg_product"))),
        ("T2_geo_segments",     lambda s: _ok_segments(s.get("seg_geo"))),
        ("T3_ebitda",           check_t3_ebitda),
        ("T4_waterfall",        check_t4_waterfall),
        ("T5_expense_ratios",   check_t5_expense_ratios),
        ("T6_per_share",        check_t6_per_share),
    ]

    for task_name, check_fn in task_checks:
        trail: List[dict] = []
        chosen = None

        for sname in ("sec", "fmp", "finnhub"):
            try:
                ok, reason = check_fn(sources.get(sname, {}))
            except Exception as e:
                ok, reason = False, f"check raised: {e}"
            trail.append({"source": sname, "ok": ok, "reason": reason})
            if ok and chosen is None:
                chosen = sname
                break

        if chosen is None:
            # Try QC
            qc_df = qc_raw.get(task_name)
            ok, reason = _ok_df(qc_df)
            trail.append({"source": "quarterchart", "ok": ok, "reason": reason})
            if ok:
                chosen = "quarterchart"
        else:
            trail.append({"source": "quarterchart", "ok": None, "reason": "not tried (earlier source worked)"})

        result["tasks"][task_name] = {
            "winner": chosen,
            "worked": bool(chosen),
            "trail": trail,
        }
    return result


def build_markdown(all_results: List[dict]) -> str:
    tasks = ["T1_product_segments", "T2_geo_segments", "T3_ebitda",
             "T4_waterfall", "T5_expense_ratios", "T6_per_share"]
    lines = []
    lines.append("# Source coverage probe — SEC → FMP → Finnhub → QuarterChart")
    lines.append("")
    lines.append("| Ticker | Task | Source Used | Worked | Why |")
    lines.append("|--------|------|-------------|--------|-----|")
    for r in all_results:
        t = r["ticker"]
        for task in tasks:
            td = r["tasks"].get(task, {})
            winner = td.get("winner") or "—"
            worked = "worked" if td.get("worked") else "not worked"
            trail = td.get("trail", [])
            # Explanation: if we chose a non-first source, list why each earlier source failed
            parts = []
            for entry in trail:
                if entry.get("ok") is None:  # not tried
                    continue
                if entry["ok"]:
                    parts.append(f"{entry['source']}✓ ({entry['reason']})")
                    break
                parts.append(f"{entry['source']}✗ {entry['reason']}")
            if not td.get("worked"):
                parts.append("all 4 sources failed")
            reason = " · ".join(parts)
            lines.append(f"| {t} | {task} | {winner} | {worked} | {reason} |")
    return "\n".join(lines)


def main():
    all_results = []
    for t in TICKERS:
        r = probe_ticker(t)
        all_results.append(r)
        with open(OUT_JSON, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        with open(OUT_MD, "w") as f:
            f.write(build_markdown(all_results))
    print(f"\n=== DONE — wrote {OUT_JSON} and {OUT_MD} ===", flush=True)


if __name__ == "__main__":
    main()
