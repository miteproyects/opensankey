"""
Auto-updater: Fetches latest 10-K values from SEC EDGAR and updates
the KNOWN_ANNUAL dict in test_edgar_accuracy.py.

Run:  python tests/update_known_values.py
      python tests/update_known_values.py --tickers AAPL MSFT KO ORCL NVDA

This script:
1. Fetches CompanyFacts JSON from EDGAR for each ticker
2. Extracts the latest 10-K annual values
3. Prints the updated KNOWN_ANNUAL dict (copy-paste into test file)
4. Optionally auto-writes it into test_edgar_accuracy.py (--write flag)
"""

import json
import re
import sys
import requests
from datetime import datetime

SEC_HEADERS = {
    "User-Agent": "QuarterCharts contact@quartercharts.com",
    "Accept-Encoding": "gzip, deflate",
}

# XBRL tags to extract — same priority order as sankey_page.py
INCOME_TAGS = {
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
    "Operating Income": ["OperatingIncomeLoss"],
    "Interest Expense": [
        "InterestExpense",
        "InterestExpenseDebt",
    ],
    "Pretax Income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "Tax Provision": ["IncomeTaxExpenseBenefit"],
    "Net Income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
}

DEFAULT_TICKERS = ["KO", "AAPL", "MSFT", "ORCL", "NVDA"]


def ticker_to_cik(ticker: str) -> str:
    """Convert stock ticker to SEC CIK number."""
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=SEC_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None


def fetch_facts(cik: str) -> dict:
    """Fetch CompanyFacts JSON from EDGAR."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_fy_end_month(facts: dict) -> int:
    """Determine fiscal year end month from the most recent 10-K filing date."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    # Look at Revenues or Assets for the FY end date
    for tag in ["Revenues", "Assets", "NetIncomeLoss"]:
        concept = gaap.get(tag)
        if not concept:
            continue
        entries = concept.get("units", {}).get("USD", [])
        fy_ends = []
        for e in entries:
            if e.get("form") == "10-K" and e.get("fp") == "FY" and e.get("end"):
                try:
                    end_date = datetime.strptime(e["end"], "%Y-%m-%d")
                    fy_ends.append(end_date)
                except ValueError:
                    pass
        if fy_ends:
            latest = max(fy_ends)
            return latest.month
    return 12  # default


def extract_latest_10k(facts: dict, fy_end_month: int) -> dict:
    """Extract the latest 10-K values for all income metrics.

    Returns: {"fy": 2024, "fy_end_month": 12, "values": {"Total Revenue": 46854000000, ...}}
    """
    gaap = facts.get("facts", {}).get("us-gaap", {})
    entity_name = facts.get("entityName", "Unknown")

    # Find the most recent FY end date across all tags
    all_fy_ends = set()
    for metric, tags in INCOME_TAGS.items():
        for tag in tags:
            concept = gaap.get(tag)
            if not concept:
                continue
            for e in concept.get("units", {}).get("USD", []):
                if e.get("form") == "10-K" and e.get("fp") == "FY" and e.get("end"):
                    all_fy_ends.add(e["end"])

    if not all_fy_ends:
        return None

    latest_end = max(all_fy_ends)
    latest_date = datetime.strptime(latest_end, "%Y-%m-%d")

    # Determine FY label year
    fy_year = latest_date.year

    # Extract values for the latest FY
    values = {}
    tags_used = {}
    for metric, tags in INCOME_TAGS.items():
        for tag in tags:
            concept = gaap.get(tag)
            if not concept:
                continue
            entries = concept.get("units", {}).get("USD", [])

            # Find the entry for the latest FY end
            best_val = None
            best_filed = ""
            for e in entries:
                if (e.get("form") == "10-K" and e.get("fp") == "FY"
                        and e.get("end") == latest_end):
                    val = e.get("val")
                    filed = e.get("filed", "")
                    if val is not None and (not best_filed or filed > best_filed):
                        best_val = val
                        best_filed = filed

            if best_val is not None:
                values[metric] = int(best_val)
                tags_used[metric] = tag
                break  # Use first matching tag (priority order)

    return {
        "fy": fy_year,
        "fy_end_month": fy_end_month,
        "entity_name": entity_name,
        "filing_end": latest_end,
        "values": values,
        "tags_used": tags_used,
    }


def format_known_annual(results: dict) -> str:
    """Format the results as a Python KNOWN_ANNUAL dict string."""
    lines = ["KNOWN_ANNUAL = {"]
    for ticker, data in results.items():
        if data is None:
            lines.append(f'    # "{ticker}": SKIPPED (no 10-K data found)')
            continue

        lines.append(f'    "{ticker}": {{')
        lines.append(f'        "fy": {data["fy"]},')
        lines.append(f'        "fy_end_month": {data["fy_end_month"]},')
        lines.append(f'        "source": "10-K ending {data["filing_end"]}, '
                     f'{data["entity_name"]}",')
        lines.append(f'        "values": {{')
        for metric, val in data["values"].items():
            # Format with underscores for readability
            val_str = f"{val:_}"
            tag = data["tags_used"].get(metric, "?")
            lines.append(f'            "{metric}": {val_str},  # XBRL: {tag}')
        lines.append(f'        }},')
        lines.append(f'    }},')

    lines.append("}")
    return "\n".join(lines)


def main():
    tickers = DEFAULT_TICKERS
    write_mode = False

    # Parse args
    args = sys.argv[1:]
    if "--write" in args:
        write_mode = True
        args.remove("--write")
    if "--tickers" in args:
        idx = args.index("--tickers")
        tickers = [t.upper() for t in args[idx + 1:]]
    elif args:
        tickers = [t.upper() for t in args if not t.startswith("-")]

    if not tickers:
        tickers = DEFAULT_TICKERS

    print(f"\n{'='*70}")
    print(f"  QuarterCharts — EDGAR Known Values Auto-Updater")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Tickers: {', '.join(tickers)}")
    print(f"{'='*70}\n")

    results = {}
    for ticker in tickers:
        print(f"  Fetching {ticker}...", end=" ", flush=True)
        try:
            cik = ticker_to_cik(ticker)
            if not cik:
                print(f"CIK not found!")
                results[ticker] = None
                continue

            facts = fetch_facts(cik)
            fy_end = get_fy_end_month(facts)
            data = extract_latest_10k(facts, fy_end)

            if data:
                print(f"FY{data['fy']} (ending {data['filing_end']}), "
                      f"{len(data['values'])} metrics found")
                results[ticker] = data
            else:
                print("No 10-K data found!")
                results[ticker] = None

        except Exception as e:
            print(f"ERROR: {e}")
            results[ticker] = None

    # Print formatted output
    print(f"\n{'='*70}")
    print("  Generated KNOWN_ANNUAL (copy into test_edgar_accuracy.py):")
    print(f"{'='*70}\n")
    output = format_known_annual(results)
    print(output)

    # Optionally write to file
    if write_mode:
        import os
        test_file = os.path.join(os.path.dirname(__file__), "test_edgar_accuracy.py")
        with open(test_file, "r") as f:
            content = f.read()

        # Replace KNOWN_ANNUAL block
        pattern = r"KNOWN_ANNUAL = \{.*?\n\}"
        new_content = re.sub(pattern, output, content, flags=re.DOTALL)

        if new_content != content:
            with open(test_file, "w") as f:
                f.write(new_content)
            print(f"\n  ✅ Updated {test_file}")
        else:
            print(f"\n  ⚠️ Could not find KNOWN_ANNUAL block to replace in {test_file}")

    # Summary
    print(f"\n{'='*70}")
    print(f"  Summary:")
    for ticker, data in results.items():
        if data:
            vals = data["values"]
            rev = vals.get("Total Revenue", 0)
            ni = vals.get("Net Income", 0)
            print(f"    {ticker:5s}  FY{data['fy']}  "
                  f"Rev: ${rev / 1e9:.1f}B  NI: ${ni / 1e9:.1f}B  "
                  f"({len(vals)} metrics)")
        else:
            print(f"    {ticker:5s}  ✗ No data")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
