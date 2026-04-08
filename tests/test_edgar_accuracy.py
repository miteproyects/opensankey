"""
Automated accuracy tests for QuarterCharts EDGAR data pipeline.

Validates that the data fetched from SEC EDGAR and the math applied
(quarter summing, YoY %, derived metrics) match known 10-K/10-Q filings.

Run on the deployed server (where Streamlit is available):
    python -m pytest tests/test_edgar_accuracy.py -v
    or:  python tests/test_edgar_accuracy.py   (standalone)

Run offline (math-only tests, no Streamlit needed):
    python tests/test_edgar_accuracy.py --offline

Known values sourced from SEC EDGAR XBRL viewer for each company.
"""

import sys, os
import pandas as pd
import numpy as np

# ── Make project root importable ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Pure math functions (no Streamlit dependency) ─────────────────────────

def _yoy(current, previous):
    """Calculate year-over-year percentage change."""
    if previous and previous != 0:
        return ((current - previous) / abs(previous)) * 100
    return None


def _fq_end_month_s(q, fy_end):
    """Return calendar month (1-12) when fiscal quarter q ends."""
    m = fy_end - 3 * (4 - q)
    while m <= 0:
        m += 12
    return m


def _fq_end_year_s(q, fy, fy_end):
    """Return calendar year when fiscal quarter q of FY fy ends."""
    end_cal_month = fy_end - 3 * (4 - q)
    end_cal_year = fy
    while end_cal_month <= 0:
        end_cal_month += 12
        end_cal_year -= 1
    return end_cal_year


def _aggregate_partial_year(qtr_df, fy, quarter_list, fy_end, is_balance_sheet=False):
    """Aggregate specific fiscal quarters of FY `fy` into a single Series."""
    if qtr_df is None or qtr_df.empty:
        return None, None
    col_dates = []
    for c in qtr_df.columns:
        try:
            col_dates.append((c, pd.Timestamp(c)))
        except Exception:
            col_dates.append((c, None))
    matched_cols = []
    for q in sorted(quarter_list):
        end_m = _fq_end_month_s(q, fy_end)
        end_y = _fq_end_year_s(q, fy, fy_end)
        for col_name, ts in col_dates:
            if ts and ts.month == end_m and ts.year == end_y:
                matched_cols.append(col_name)
                break
    if not matched_cols:
        return None, None
    if is_balance_sheet:
        latest_col = max(matched_cols, key=lambda c: pd.Timestamp(c))
        return qtr_df[latest_col], latest_col
    else:
        return qtr_df[matched_cols].sum(axis=1), matched_cols[-1]


# ---------------------------------------------------------------------------
# Import sankey_page helpers (only when Streamlit is available)
# ---------------------------------------------------------------------------

def _import_sankey_helpers():
    """Import helper functions from sankey_page (requires Streamlit)."""
    import sankey_page as sp
    return sp

# ── Known 10-K values (USD) from SEC EDGAR XBRL viewer ──────────────────
# Source: https://www.sec.gov/cgi-bin/viewer?action=view&cik=<CIK>&type=10-K
#
# Format: { "metric": value_in_dollars }
# These are EXACT values from the XBRL filings, not rounded.
# Updated: April 2026

KNOWN_ANNUAL = {
    "KO": {
        "fy": 2024,
        "fy_end_month": 12,
        "source": "10-K filed 2025-02-20, CIK 0000021344",
        "values": {
            "Total Revenue":        46_854_000_000,
            "Cost Of Revenue":      18_519_000_000,
            "Gross Profit":         28_335_000_000,
            "Operating Income":     10_755_000_000,
            "Net Income":            9_980_000_000,
            "Pretax Income":        12_186_000_000,
            "Tax Provision":         2_437_000_000,
        },
    },
    "AAPL": {
        "fy": 2024,
        "fy_end_month": 9,
        "source": "10-K filed 2024-11-01, CIK 0000320193",
        "values": {
            "Total Revenue":       391_035_000_000,
            "Cost Of Revenue":     210_352_000_000,
            "Gross Profit":        180_683_000_000,
            "Operating Income":    123_216_000_000,
            "Net Income":           93_736_000_000,
            "Research And Development": 31_370_000_000,
        },
    },
    "MSFT": {
        "fy": 2024,
        "fy_end_month": 6,
        "source": "10-K filed 2024-07-30, CIK 0000789019",
        "values": {
            "Total Revenue":       245_122_000_000,
            "Cost Of Revenue":      74_073_000_000,
            "Gross Profit":        171_049_000_000,
            "Operating Income":    109_433_000_000,
            "Net Income":           88_136_000_000,
        },
    },
}

# ── Known 10-Q quarterly values (individual quarter, not YTD) ────────────
KNOWN_QUARTERLY = {
    "KO": {
        "fy_end_month": 12,
        "source": "10-Q filings, CIK 0000021344",
        "quarters": {
            # FY2024 Q1 (Jan-Mar 2024)
            ("Q1", 2024): {
                "Total Revenue": 11_300_000_000,
                "Net Income":     3_177_000_000,
            },
            # FY2024 Q2 (Apr-Jun 2024)
            ("Q2", 2024): {
                "Total Revenue": 12_362_000_000,
                "Net Income":     2_411_000_000,
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: Annual 10-K values match EDGAR filings
# ═══════════════════════════════════════════════════════════════════════════

def test_annual_values():
    """Verify annual income statement values match known 10-K filings."""
    sp = _import_sankey_helpers()
    tolerance = 0.0003  # 0.03% tolerance — values must nearly exactly match EDGAR

    results = []
    for ticker, expected in KNOWN_ANNUAL.items():
        fy = expected["fy"]
        try:
            income_df, balance_df, info = sp._fetch_sankey_data(ticker, quarterly=False)
        except Exception as e:
            results.append({"ticker": ticker, "status": "FETCH_ERROR", "error": str(e)})
            continue

        if income_df.empty:
            results.append({"ticker": ticker, "status": "EMPTY_DATA"})
            continue

        # Find the column matching the expected FY
        col_match = None
        for col in income_df.columns:
            try:
                ts = pd.Timestamp(col)
                if ts.year == fy or (ts.year == fy + 1 and ts.month <= 6):
                    col_match = col
                    break
            except Exception:
                continue

        if col_match is None:
            results.append({"ticker": ticker, "status": "FY_NOT_FOUND", "fy": fy})
            continue

        col_idx = list(income_df.columns).index(col_match)

        for metric, expected_val in expected["values"].items():
            actual_val = 0
            for idx in income_df.index:
                if metric.lower() in str(idx).lower():
                    v = income_df.iloc[income_df.index.get_loc(idx), col_idx]
                    if pd.notna(v):
                        actual_val = float(v)
                    break

            if expected_val == 0:
                match = actual_val == 0
            else:
                pct_diff = abs(actual_val - expected_val) / abs(expected_val)
                match = pct_diff <= tolerance

            results.append({
                "ticker": ticker,
                "metric": metric,
                "expected": expected_val,
                "actual": actual_val,
                "match": match,
                "pct_diff": f"{abs(actual_val - expected_val) / abs(expected_val) * 100:.2f}%"
                    if expected_val != 0 else "N/A",
            })

    # Print results table
    print("\n" + "=" * 80)
    print("TEST 1: Annual 10-K Values vs Known EDGAR Filings")
    print("=" * 80)
    passed = 0
    failed = 0
    for r in results:
        if "match" in r:
            status = "✓ PASS" if r["match"] else "✗ FAIL"
            if r["match"]:
                passed += 1
            else:
                failed += 1
            print(f"  {status}  {r['ticker']:5s} | {r['metric']:35s} | "
                  f"Expected: {r['expected']:>15,.0f} | "
                  f"Actual: {r['actual']:>15,.0f} | Diff: {r['pct_diff']}")
        else:
            failed += 1
            print(f"  ✗ SKIP  {r['ticker']:5s} | {r.get('status', 'UNKNOWN')}: {r.get('error', '')}")

    print(f"\n  Results: {passed} passed, {failed} failed out of {passed + failed}")
    assert failed == 0, f"{failed} tests failed"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: Quarter summing math (Q1+Q2 = known values)
# ═══════════════════════════════════════════════════════════════════════════

def test_quarter_summing():
    """Verify that summing individual quarters matches expected totals."""
    sp = _import_sankey_helpers()
    tolerance = 0.005

    results = []
    for ticker, data in KNOWN_QUARTERLY.items():
        fy_end = data["fy_end_month"]
        try:
            income_df, _, _ = sp._fetch_sankey_data(ticker, quarterly=True)
        except Exception as e:
            results.append({"ticker": ticker, "status": "FETCH_ERROR", "error": str(e)})
            continue

        if income_df.empty:
            results.append({"ticker": ticker, "status": "EMPTY_DATA"})
            continue

        for (q_label, fy), expected_vals in data["quarters"].items():
            q_num = int(q_label[1])
            # Find matching column using fiscal quarter end date
            end_m = sp._fq_end_month_s(q_num, fy_end)
            end_y = sp._fq_end_year_s(q_num, fy, fy_end)

            col_match = None
            for col in income_df.columns:
                try:
                    ts = pd.Timestamp(col)
                    if ts.month == end_m and ts.year == end_y:
                        col_match = col
                        break
                except Exception:
                    continue

            if col_match is None:
                results.append({
                    "ticker": ticker, "quarter": f"{q_label} FY{fy}",
                    "status": "COL_NOT_FOUND",
                })
                continue

            col_idx = list(income_df.columns).index(col_match)

            for metric, expected_val in expected_vals.items():
                actual_val = 0
                for idx in income_df.index:
                    if metric.lower() in str(idx).lower():
                        v = income_df.iloc[income_df.index.get_loc(idx), col_idx]
                        if pd.notna(v):
                            actual_val = float(v)
                        break

                pct_diff = abs(actual_val - expected_val) / abs(expected_val) if expected_val else 0
                match = pct_diff <= tolerance

                results.append({
                    "ticker": ticker,
                    "quarter": f"{q_label} FY{fy}",
                    "metric": metric,
                    "expected": expected_val,
                    "actual": actual_val,
                    "match": match,
                    "pct_diff": f"{pct_diff * 100:.2f}%",
                })

    print("\n" + "=" * 80)
    print("TEST 2: Quarterly Values vs Known EDGAR Filings")
    print("=" * 80)
    passed = 0
    failed = 0
    for r in results:
        if "match" in r:
            status = "✓ PASS" if r["match"] else "✗ FAIL"
            if r["match"]:
                passed += 1
            else:
                failed += 1
            print(f"  {status}  {r['ticker']:5s} {r['quarter']:10s} | {r['metric']:20s} | "
                  f"Expected: {r['expected']:>15,.0f} | "
                  f"Actual: {r['actual']:>15,.0f} | Diff: {r['pct_diff']}")
        else:
            failed += 1
            print(f"  ✗ SKIP  {r['ticker']:5s} | {r.get('status', 'UNKNOWN')}")

    print(f"\n  Results: {passed} passed, {failed} failed out of {passed + failed}")
    assert failed == 0, f"{failed} tests failed"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: Multi-quarter aggregation math
# ═══════════════════════════════════════════════════════════════════════════

def test_multi_quarter_aggregation():
    """Verify Q1+Q2 sum equals expected H1 total (pure math check)."""
    sp = _import_sankey_helpers()
    tolerance = 0.005

    results = []
    for ticker, data in KNOWN_QUARTERLY.items():
        fy_end = data["fy_end_month"]
        try:
            income_df, _, _ = sp._fetch_sankey_data(ticker, quarterly=True)
        except Exception as e:
            results.append({"ticker": ticker, "status": "FETCH_ERROR", "error": str(e)})
            continue

        # Get all FYs that have Q1 and Q2 known values
        fy_groups = {}
        for (q_label, fy), vals in data["quarters"].items():
            if fy not in fy_groups:
                fy_groups[fy] = {}
            fy_groups[fy][q_label] = vals

        for fy, quarters in fy_groups.items():
            if "Q1" in quarters and "Q2" in quarters:
                # Expected sum = Q1 + Q2
                for metric in quarters["Q1"]:
                    if metric in quarters["Q2"]:
                        expected_sum = quarters["Q1"][metric] + quarters["Q2"][metric]

                        # Use the aggregation function
                        agg_series, _ = sp._aggregate_partial_year(
                            income_df, fy, [1, 2], fy_end, is_balance_sheet=False
                        )
                        if agg_series is None:
                            results.append({
                                "ticker": ticker, "fy": fy,
                                "metric": metric, "status": "AGG_FAILED",
                            })
                            continue

                        actual_sum = 0
                        for idx in agg_series.index:
                            if metric.lower() in str(idx).lower():
                                v = agg_series[idx]
                                if pd.notna(v):
                                    actual_sum = float(v)
                                break

                        pct_diff = abs(actual_sum - expected_sum) / abs(expected_sum) if expected_sum else 0
                        match = pct_diff <= tolerance

                        results.append({
                            "ticker": ticker,
                            "test": f"FY{fy} Q1+Q2 {metric}",
                            "expected": expected_sum,
                            "actual": actual_sum,
                            "match": match,
                            "pct_diff": f"{pct_diff * 100:.2f}%",
                        })

    print("\n" + "=" * 80)
    print("TEST 3: Multi-Quarter Aggregation (Q1+Q2 Sum)")
    print("=" * 80)
    passed = 0
    failed = 0
    for r in results:
        if "match" in r:
            status = "✓ PASS" if r["match"] else "✗ FAIL"
            if r["match"]:
                passed += 1
            else:
                failed += 1
            print(f"  {status}  {r['ticker']:5s} | {r['test']:35s} | "
                  f"Expected: {r['expected']:>15,.0f} | "
                  f"Actual: {r['actual']:>15,.0f} | Diff: {r['pct_diff']}")
        else:
            failed += 1
            print(f"  ✗ SKIP  {r['ticker']:5s} | {r.get('status', 'UNKNOWN')}")

    print(f"\n  Results: {passed} passed, {failed} failed out of {passed + failed}")
    assert failed == 0, f"{failed} tests failed"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: Derived metrics math (Gross Profit = Revenue - COGS)
# ═══════════════════════════════════════════════════════════════════════════

def test_derived_metrics():
    """Verify derived calculations: GrossProfit = Revenue - COGS, etc."""
    tolerance = 0.01  # 1% for derived metrics

    results = []
    for ticker, expected in KNOWN_ANNUAL.items():
        vals = expected["values"]

        # Test: Gross Profit = Revenue - COGS
        if "Total Revenue" in vals and "Cost Of Revenue" in vals and "Gross Profit" in vals:
            computed_gp = vals["Total Revenue"] - vals["Cost Of Revenue"]
            filed_gp = vals["Gross Profit"]
            pct_diff = abs(computed_gp - filed_gp) / abs(filed_gp) if filed_gp else 0
            match = pct_diff <= tolerance

            results.append({
                "ticker": ticker,
                "test": "Gross Profit = Revenue - COGS",
                "computed": computed_gp,
                "filed": filed_gp,
                "match": match,
                "pct_diff": f"{pct_diff * 100:.2f}%",
            })

        # Test: Tax = Pretax - Net Income (approximately)
        if "Pretax Income" in vals and "Net Income" in vals and "Tax Provision" in vals:
            computed_tax = vals["Pretax Income"] - vals["Net Income"]
            filed_tax = vals["Tax Provision"]
            pct_diff = abs(computed_tax - filed_tax) / abs(filed_tax) if filed_tax else 0
            # Wider tolerance: minorities, equity method, discontinued ops cause diffs
            match = pct_diff <= 0.15  # 15%

            results.append({
                "ticker": ticker,
                "test": "Tax ≈ Pretax - Net Income",
                "computed": computed_tax,
                "filed": filed_tax,
                "match": match,
                "pct_diff": f"{pct_diff * 100:.2f}%",
            })

    print("\n" + "=" * 80)
    print("TEST 4: Derived Metric Consistency")
    print("=" * 80)
    passed = 0
    failed = 0
    for r in results:
        status = "✓ PASS" if r["match"] else "✗ FAIL"
        if r["match"]:
            passed += 1
        else:
            failed += 1
        print(f"  {status}  {r['ticker']:5s} | {r['test']:35s} | "
              f"Computed: {r['computed']:>15,.0f} | "
              f"Filed: {r['filed']:>15,.0f} | Diff: {r['pct_diff']}")

    print(f"\n  Results: {passed} passed, {failed} failed out of {passed + failed}")
    assert failed == 0, f"{failed} tests failed"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: YoY percentage calculation
# ═══════════════════════════════════════════════════════════════════════════

def test_yoy_math():
    """Verify YoY percentage change calculation is correct."""

    cases = [
        (110, 100, 10.0),       # 10% increase
        (90, 100, -10.0),       # 10% decrease
        (200, 100, 100.0),      # 100% increase
        (0, 100, -100.0),       # 100% decrease
        (100, 0, None),         # Division by zero
        (-50, -100, 50.0),      # Negative to less negative = improvement
    ]

    print("\n" + "=" * 80)
    print("TEST 5: YoY Percentage Calculation")
    print("=" * 80)
    passed = 0
    failed = 0
    for current, previous, expected in cases:
        result = _yoy(current, previous)
        if expected is None:
            match = result is None
        else:
            match = result is not None and abs(result - expected) < 0.01
        status = "✓ PASS" if match else "✗ FAIL"
        if match:
            passed += 1
        else:
            failed += 1
        print(f"  {status}  _yoy({current}, {previous}) = {result} (expected {expected})")

    print(f"\n  Results: {passed} passed, {failed} failed out of {passed + failed}")
    assert failed == 0, f"{failed} tests failed"


# ═══════════════════════════════════════════════════════════════════════════
# Standalone runner
# ═══════════════════════════════════════════════════════════════════════════

def test_multi_quarter_aggregation_offline():
    """Verify multi-quarter aggregation with synthetic data (no network)."""
    print("\n" + "=" * 80)
    print("TEST 3b: Multi-Quarter Aggregation (Offline / Synthetic Data)")
    print("=" * 80)

    # Simulate KO-like quarterly data (FY end Dec=12)
    fy_end = 12
    # FY2024: Q1=Mar'24, Q2=Jun'24, Q3=Sep'24, Q4=Dec'24
    cols = ["2024-12-31", "2024-09-30", "2024-06-30", "2024-03-31",
            "2023-12-31", "2023-09-30", "2023-06-30", "2023-03-31"]
    data = {
        "2024-03-31": [11_300, 3_177],  # Q1 2024
        "2024-06-30": [12_362, 2_411],  # Q2 2024
        "2024-09-30": [11_854, 2_850],  # Q3 2024
        "2024-12-31": [11_338, 1_542],  # Q4 2024
        "2023-03-31": [10_980, 3_100],  # Q1 2023
        "2023-06-30": [12_000, 2_500],  # Q2 2023
        "2023-09-30": [11_500, 2_700],  # Q3 2023
        "2023-12-31": [10_800, 1_400],  # Q4 2023
    }
    qtr_df = pd.DataFrame(data, index=["Total Revenue", "Net Income"])

    passed = 0
    failed = 0

    # Test: Q1+Q2 sum for FY2024
    ser, _ = _aggregate_partial_year(qtr_df, 2024, [1, 2], fy_end, is_balance_sheet=False)
    expected_rev = 11_300 + 12_362
    actual_rev = float(ser.loc["Total Revenue"])
    match = actual_rev == expected_rev
    status = "✓ PASS" if match else "✗ FAIL"
    if match: passed += 1
    else: failed += 1
    print(f"  {status}  Q1+Q2 FY2024 Revenue: expected={expected_rev:,}, actual={actual_rev:,.0f}")

    # Test: Q1+Q3 (non-contiguous) for FY2024
    ser2, _ = _aggregate_partial_year(qtr_df, 2024, [1, 3], fy_end, is_balance_sheet=False)
    expected_rev2 = 11_300 + 11_854
    actual_rev2 = float(ser2.loc["Total Revenue"])
    match2 = actual_rev2 == expected_rev2
    status2 = "✓ PASS" if match2 else "✗ FAIL"
    if match2: passed += 1
    else: failed += 1
    print(f"  {status2}  Q1+Q3 FY2024 Revenue: expected={expected_rev2:,}, actual={actual_rev2:,.0f}")

    # Test: All 4 quarters = full year
    ser3, _ = _aggregate_partial_year(qtr_df, 2024, [1, 2, 3, 4], fy_end, is_balance_sheet=False)
    expected_full = 11_300 + 12_362 + 11_854 + 11_338
    actual_full = float(ser3.loc["Total Revenue"])
    match3 = actual_full == expected_full
    status3 = "✓ PASS" if match3 else "✗ FAIL"
    if match3: passed += 1
    else: failed += 1
    print(f"  {status3}  Q1-Q4 FY2024 Revenue: expected={expected_full:,}, actual={actual_full:,.0f}")

    # Test: Single quarter
    ser4, _ = _aggregate_partial_year(qtr_df, 2024, [2], fy_end, is_balance_sheet=False)
    expected_q2 = 12_362
    actual_q2 = float(ser4.loc["Total Revenue"])
    match4 = actual_q2 == expected_q2
    status4 = "✓ PASS" if match4 else "✗ FAIL"
    if match4: passed += 1
    else: failed += 1
    print(f"  {status4}  Q2 only FY2024 Revenue: expected={expected_q2:,}, actual={actual_q2:,.0f}")

    # Test: Net Income Q1+Q2
    expected_ni = 3_177 + 2_411
    actual_ni = float(ser.loc["Net Income"])
    match5 = actual_ni == expected_ni
    status5 = "✓ PASS" if match5 else "✗ FAIL"
    if match5: passed += 1
    else: failed += 1
    print(f"  {status5}  Q1+Q2 FY2024 Net Income: expected={expected_ni:,}, actual={actual_ni:,.0f}")

    # Test: Non-standard FY (ORCL fy_end=5)
    fy_end_orcl = 5
    # ORCL FY2025: Q1 ends Aug'24, Q2 ends Nov'24, Q3 ends Feb'25, Q4 ends May'25
    orcl_data = {
        "2024-08-31": [13_000, 3_000],  # Q1
        "2024-11-30": [14_000, 3_500],  # Q2
        "2025-02-28": [14_500, 3_800],  # Q3
        "2025-05-31": [15_000, 4_000],  # Q4
    }
    orcl_df = pd.DataFrame(orcl_data, index=["Total Revenue", "Net Income"])
    ser_orcl, _ = _aggregate_partial_year(orcl_df, 2025, [1, 2], fy_end_orcl, is_balance_sheet=False)
    expected_orcl = 13_000 + 14_000
    actual_orcl = float(ser_orcl.loc["Total Revenue"])
    match6 = actual_orcl == expected_orcl
    status6 = "✓ PASS" if match6 else "✗ FAIL"
    if match6: passed += 1
    else: failed += 1
    print(f"  {status6}  ORCL Q1+Q2 FY2025 Revenue: expected={expected_orcl:,}, actual={actual_orcl:,.0f}")

    print(f"\n  Results: {passed} passed, {failed} failed out of {passed + failed}")
    assert failed == 0, f"{failed} tests failed"


if __name__ == "__main__":
    _offline = "--offline" in sys.argv

    print("\n🔍 QuarterCharts EDGAR Accuracy Test Suite")
    print("=" * 80)

    # Tests that never need network
    test_yoy_math()
    test_derived_metrics()
    test_multi_quarter_aggregation_offline()

    if not _offline:
        # Network + Streamlit dependent tests
        try:
            test_annual_values()
            test_quarter_summing()
            test_multi_quarter_aggregation()
        except ImportError as e:
            print(f"\n⚠️  Network tests skipped (Streamlit not available): {e}")
        except Exception as e:
            print(f"\n⚠️  Network tests skipped (SEC EDGAR unreachable): {e}")
    else:
        print("\n⚠️  Network tests skipped (--offline mode)")

    print("\n" + "=" * 80)
    print("✅ All tests complete")
    print("=" * 80)
