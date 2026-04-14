"""
Sankey diagram page â Income Statement & Balance Sheet visualizations.
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
from auth import get_auth_params

# âââ Demo / sample data for when Yahoo Finance is rate-limited âââââââââââââ
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


# âââ Vivid 11-color palette (one per node) ââââââââââââââââââââââââââââââââ
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


# Pill label → node hex color (for hover effects)
INCOME_PILL_COLORS = {
    "Revenue": VIVID[0], "Cost of Revenue": VIVID[1], "Gross Profit": VIVID[2],
    "R&D": VIVID[3], "SG&A": VIVID[4], "D&A": VIVID[5], "Other OpEx": VIVID[5],
    "Operating Income": VIVID[6], "Interest Exp.": VIVID[7],
    "Pretax Income": VIVID[8], "Income Tax": VIVID[9], "Net Income": VIVID[10],
}
BALANCE_PILL_COLORS = {
    "Total Assets": BS_COLORS["asset"], "Current Assets": BS_COLORS["asset"],
    "Non-Current Assets": BS_COLORS["asset2"], "Cash": BS_COLORS["cash"],
    "ST Investments": BS_COLORS["invest"], "Receivables": BS_COLORS["asset"],
    "Inventory": BS_COLORS["asset"], "PPE": BS_COLORS["asset2"],
    "Goodwill": BS_COLORS["asset2"], "Intangibles": BS_COLORS["asset2"],
    "Investments": BS_COLORS["invest"], "Total Liabilities": BS_COLORS["liability"],
    "Current Liab.": BS_COLORS["liability"], "Non-Current Liab.": BS_COLORS["liability"],
    "Accounts Payable": BS_COLORS["payable"], "Short-Term Debt": BS_COLORS["debt"],
    "Deferred Revenue": BS_COLORS["liability"], "Long-Term Debt": BS_COLORS["debt"],
    "Equity": BS_COLORS["equity"], "Retained Earnings": BS_COLORS["retained"],
}


def _rgba(hex_color, alpha=0.42):
    """Convert hex to rgba string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _text_height_px(font_sz, has_row2=True):
    """Return the pixel height of a 3-row or 2-row annotation label.

    Row layout:  <b>Name</b>  <b>$Value</b>  [<span>↑+X% +$delta</span>]
    Line height ≈ font_size × 1.45 (for layout/spacing calculations).
    """
    line_h = font_sz * 1.45
    return line_h * (3 if has_row2 else 2)


def _text_height_px_visual(font_sz, has_row2=True):
    """Return the RENDERED pixel height of a Plotly HTML annotation.

    Plotly annotations with <b>, <br>, <span> tags render with significantly
    more vertical spacing than standard CSS line-height. This larger estimate
    is used only for post-layout overlap detection, NOT for chart height calc.
    """
    line_h = font_sz * 2.6
    return line_h * (3 if has_row2 else 2)


def _compute_dynamic_height(column_node_counts, font_sz, node_gap_px=10, base_height=460):
    """Compute the chart height so that the tallest column has room for all labels.

    For each column, the minimum pixel height needed is:
        n_nodes × text_height_px + (n_nodes - 1) × node_gap_px
    The chart's drawable area is  height × (dom_y1 - dom_y0) = height × 0.92.
    So chart height = max(base_height, worst_col_min_px / 0.92 + margin).
    """
    text_h = _text_height_px(font_sz, has_row2=True)  # worst case: 3-row
    needed = base_height
    for n in column_node_counts:
        if n <= 1:
            continue
        col_px = n * text_h + (n - 1) * node_gap_px
        chart_px = col_px / 0.92 + 30  # 30px for top/bottom margin
        needed = max(needed, chart_px)
    return int(min(needed, 1800))  # cap at 1800px for dense balance sheets (META etc.)


def _min_band_for_text(font_sz, chart_height, has_row2=True):
    """Convert text pixel height to paper-coordinate band height."""
    text_px = _text_height_px(font_sz, has_row2)
    dom_span = 0.92  # domain [0.04, 0.96]
    return text_px / (chart_height * dom_span)


def _fix_bar_gaps(node_x, node_y, node_val_raw, chart_height, min_gap_px=2):
    """Ensure minimum pixel gap between adjacent bar EDGES in each column.

    Plotly Sankey bar height is proportional to the node's flow value.
    This function computes bar heights, finds the gap between the bottom
    edge of each bar and the top edge of the bar below it, and pushes
    node_y positions apart if the gap is smaller than min_gap_px.

    Operates in node_y space (0=top, 1=bottom).  Mutates node_y in-place.
    """
    from collections import defaultdict

    dom_span = 0.92  # domain [0.04, 0.96]
    avail_px = chart_height * dom_span

    # Global scale: Plotly scales bars so that the densest column fits.
    # For each column, sum of values gives total flow.
    columns = defaultdict(list)
    for i in range(len(node_x)):
        col_key = round(node_x[i], 3)
        columns[col_key].append(i)

    # Find max column sum → determines the global bar-height scale
    max_col_sum = 0
    for col_idxs in columns.values():
        col_sum = sum(node_val_raw[i] for i in col_idxs)
        max_col_sum = max(max_col_sum, col_sum)

    if max_col_sum <= 0:
        return

    scale_px = avail_px / max_col_sum  # pixels per value unit

    # Convert min_gap_px to node_y units (node_y [0,1] spans avail_px)
    min_gap_ny = min_gap_px / avail_px

    # For each column, enforce minimum gap between bar edges
    for col_key, col_idxs in columns.items():
        if len(col_idxs) <= 1:
            continue

        # Sort by node_y ascending (top to bottom on screen)
        col_idxs.sort(key=lambda i: node_y[i])

        # Compute bar half-heights in node_y units
        bar_half = []
        for i in col_idxs:
            bar_h_px = node_val_raw[i] * scale_px
            bar_h_ny = bar_h_px / avail_px
            bar_half.append(bar_h_ny / 2)

        # Multiple passes to push apart
        for _pass in range(20):
            changed = False
            for j in range(len(col_idxs) - 1):
                i_upper = col_idxs[j]
                i_lower = col_idxs[j + 1]

                upper_bar_bottom = node_y[i_upper] + bar_half[j]
                lower_bar_top = node_y[i_lower] - bar_half[j + 1]

                gap = lower_bar_top - upper_bar_bottom
                if gap < min_gap_ny:
                    # Push apart symmetrically
                    push = (min_gap_ny - gap) / 2 + 0.0001
                    node_y[i_upper] = node_y[i_upper] - push
                    node_y[i_lower] = node_y[i_lower] + push
                    changed = True

            if not changed:
                break

            # Clamp to [0.01, 0.99]
            for j, i in enumerate(col_idxs):
                node_y[i] = max(0.01 + bar_half[j],
                                min(0.99 - bar_half[j], node_y[i]))


def _fix_text_gaps(node_x, node_y, node_row2, font_sz, chart_height, min_gap_px=2):
    """Ensure minimum pixel gap between adjacent TEXT label edges in each column.

    Each node's 3-row (or 2-row) annotation is centered at node_y (yanchor=middle).
    The text extends text_h/2 above and below the center.  This function checks
    if adjacent text labels overlap and pushes node_y apart if gap < min_gap_px.

    Runs AFTER _fix_bar_gaps so that bars are already separated.
    Operates in node_y space (0=top, 1=bottom).  Mutates node_y in-place.
    """
    from collections import defaultdict

    dom_span = 0.92  # domain [0.04, 0.96]
    avail_px = chart_height * dom_span

    # Rendered line height: Plotly HTML annotations with <b>, <br>, <span>
    # render taller than plain CSS line-height.  Use 2.6× font_sz to match
    # _text_height_px() which drives the height calculation — using a smaller
    # multiplier underestimates text extent and allows overlaps.
    line_h_px = font_sz * 2.6

    def _text_h_px(has_r2):
        return line_h_px * (3 if has_r2 else 2)

    # Convert min_gap_px to node_y units
    min_gap_ny = min_gap_px / avail_px

    # Group nodes by column
    columns = defaultdict(list)
    for i in range(len(node_x)):
        col_key = round(node_x[i], 3)
        columns[col_key].append(i)

    for col_key, col_idxs in columns.items():
        if len(col_idxs) <= 1:
            continue

        # Sort by node_y ascending (top to bottom on screen)
        col_idxs.sort(key=lambda i: node_y[i])

        # Compute text half-heights in node_y units
        text_half = []
        for i in col_idxs:
            th_px = _text_h_px(bool(node_row2[i]))
            text_half.append((th_px / avail_px) / 2)

        # Multiple passes to push apart
        for _pass in range(20):
            changed = False
            for j in range(len(col_idxs) - 1):
                i_upper = col_idxs[j]
                i_lower = col_idxs[j + 1]

                upper_text_bottom = node_y[i_upper] + text_half[j]
                lower_text_top = node_y[i_lower] - text_half[j + 1]

                gap = lower_text_top - upper_text_bottom
                if gap < min_gap_ny:
                    push = (min_gap_ny - gap) / 2 + 0.0001
                    node_y[i_upper] = node_y[i_upper] - push
                    node_y[i_lower] = node_y[i_lower] + push
                    changed = True

            if not changed:
                break

            # Clamp to [0.01, 0.99]
            for j, i in enumerate(col_idxs):
                node_y[i] = max(0.01 + text_half[j],
                                min(0.99 - text_half[j], node_y[i]))


def _fix_cross_column_text(node_x, node_y, node_val_raw, node_name_list,
                           node_val_str, node_row2, font_sz, chart_height,
                           thickness, min_gap_px=2):
    """Prevent horizontal text overlap between nodes in adjacent columns.

    Text labels extend to the RIGHT of each node bar.  When two nodes in
    neighbouring columns sit at similar Y positions, the left column's text
    can collide with the right column's text.

    Text width is estimated in paper-X units relative to the gap between
    adjacent columns — this is screen-size independent (no pixel-width
    assumption).  For conflicts, BOTH nodes are pushed apart symmetrically
    (upper goes up, lower goes down) by half the needed amount.

    Each node looks at both left and right neighbour columns across all
    passes, so fixing cols 2↔3 won't silently break 3↔4.

    Y shift per node is capped at max_shift_ny to keep text near its bar.
    Runs AFTER _fix_bar_gaps and _fix_text_gaps.  Mutates node_y in-place.
    """
    from collections import defaultdict

    dom_span = 0.92
    avail_px = chart_height * dom_span

    # ── Text height (Y extent) in node_y units ──────────────────────────
    line_h_px = font_sz * 2.6  # match _text_height_px() multiplier

    def _text_h_ny(has_r2):
        px = line_h_px * (3 if has_r2 else 2)
        return px / avail_px

    # ── Text width in paper-X units (screen-size independent) ───────────
    # Average character width ≈ 0.55 × font_sz.  We express the text
    # width as a fraction of 1.0 (paper-X) by dividing by an assumed
    # minimum chart width.  Using a SMALL chart width (350px ≈ mobile)
    # makes the estimate conservative: if no overlap on a 350px screen,
    # there won't be on a wider screen either.
    _min_chart_w_px = 350.0
    char_w_paper = (font_sz * 0.55) / _min_chart_w_px
    bar_offset_paper = (thickness / 2 + 1) / _min_chart_w_px

    def _text_width_paper(idx):
        """Estimate text label width in paper-X coords (mobile-safe)."""
        name_len = len(node_name_list[idx])
        val_len = len(node_val_str[idx])
        r2_len = len(node_row2[idx]) if node_row2[idx] else 0
        max_chars = max(name_len, val_len, r2_len)
        return max_chars * char_w_paper + bar_offset_paper

    # ── Build per-node data ─────────────────────────────────────────────
    n = len(node_x)
    text_half_h = [_text_h_ny(bool(node_row2[i])) / 2 for i in range(n)]
    text_w = [_text_width_paper(i) for i in range(n)]

    # Track cumulative shift per node to enforce cap
    total_shift = [0.0] * n
    max_shift_ny = 50.0 / avail_px  # 50 px max drift (was 30; more room for dense balance sheets)

    # ── Group nodes by column (sorted left to right) ────────────────────
    columns = defaultdict(list)
    for i in range(n):
        col_key = round(node_x[i], 3)
        columns[col_key].append(i)
    sorted_col_keys = sorted(columns.keys())

    min_gap_ny = min_gap_px / avail_px

    # ── Iterative global passes ─────────────────────────────────────────
    for _pass in range(15):
        any_conflict = False

        # Check every pair of adjacent columns
        for ci in range(len(sorted_col_keys) - 1):
            left_key = sorted_col_keys[ci]
            right_key = sorted_col_keys[ci + 1]

            for li in columns[left_key]:
                l_x_right = node_x[li] + text_w[li]

                for ri in columns[right_key]:
                    # X overlap: left text extends past right column start?
                    if l_x_right <= node_x[ri]:
                        continue

                    # Y overlap check
                    l_y_top = node_y[li] - text_half_h[li]
                    l_y_bot = node_y[li] + text_half_h[li]
                    r_y_top = node_y[ri] - text_half_h[ri]
                    r_y_bot = node_y[ri] + text_half_h[ri]

                    if l_y_bot <= r_y_top or r_y_bot <= l_y_top:
                        continue

                    # ── Conflict: push BOTH nodes apart symmetrically ───
                    any_conflict = True
                    y_overlap = min(l_y_bot, r_y_bot) - max(l_y_top, r_y_top)
                    needed = (y_overlap + min_gap_ny) / 2

                    # Determine who is upper vs lower
                    if node_y[li] <= node_y[ri]:
                        upper, lower = li, ri
                    else:
                        upper, lower = ri, li

                    # Push upper UP, lower DOWN — each by half
                    up_shift = min(needed, max_shift_ny - abs(total_shift[upper]))
                    dn_shift = min(needed, max_shift_ny - abs(total_shift[lower]))
                    up_shift = max(up_shift, 0)
                    dn_shift = max(dn_shift, 0)

                    node_y[upper] -= up_shift
                    node_y[lower] += dn_shift
                    total_shift[upper] -= up_shift
                    total_shift[lower] += dn_shift

                    # Clamp
                    node_y[upper] = max(0.01 + text_half_h[upper],
                                        min(0.99 - text_half_h[upper],
                                            node_y[upper]))
                    node_y[lower] = max(0.01 + text_half_h[lower],
                                        min(0.99 - text_half_h[lower],
                                            node_y[lower]))

        if not any_conflict:
            break


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
    if av >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _fmt_delta(current, previous):
    """Format the dollar difference as +$2.76B or -$2.23B."""
    if current is None or previous is None or previous == 0:
        return None
    diff = current - previous
    sign = "+" if diff >= 0 else "-"
    av = abs(diff)
    if av >= 1e12:
        return f"{sign}${av/1e12:.2f}T"
    if av >= 1e9:
        return f"{sign}${av/1e9:.2f}B"
    if av >= 1e6:
        return f"{sign}${av/1e6:.0f}M"
    if av >= 1e3:
        return f"{sign}${av/1e3:.0f}K"
    return f"{sign}${av:,.0f}"


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
    if current is None or previous is None:
        return None
    if isinstance(current, float) and (pd.isna(current) or pd.isna(previous)):
        return None
    if previous != 0:
        return ((current - previous) / abs(previous)) * 100
    return None


def _yoy_delta(current, previous, label="YoY"):
    """Format YoY as delta string for st.metric, including dollar difference."""
    pct = _yoy(current, previous)
    if pct is None:
        return None
    delta = _fmt_delta(current, previous)
    if delta:
        return f"{pct:+.1f}% {label} ({delta})"
    return f"{pct:+.1f}% {label}"


def _compute_sankey_metrics(income_df, balance_df=None):
    """Compute ALL Sankey page metrics from the final aggregated DataFrames using Pandas.

    Returns a dict with:
      - 'income': dict of {account_name: {'current': float, 'previous': float, 'pct_change': float|None, 'dollar_change': float|None}}
      - 'balance': same structure for balance sheet
      - 'kpi': list of KPI card data
      - 'df_info': debugging info about the DataFrames
    """
    result = {"income": {}, "balance": {}, "kpi": [], "df_info": {}}

    def _extract_metric(df, key):
        """Extract current (col 0) and previous (col 1) values using Pandas iloc."""
        if df is None or df.empty:
            return 0.0, 0.0
        cur = 0.0
        prev = 0.0
        for idx in df.index:
            if key.lower() in str(idx).lower():
                cur = float(df.iloc[df.index.get_loc(idx), 0]) if pd.notna(df.iloc[df.index.get_loc(idx), 0]) else 0.0
                if df.shape[1] >= 2:
                    prev = float(df.iloc[df.index.get_loc(idx), 1]) if pd.notna(df.iloc[df.index.get_loc(idx), 1]) else 0.0
                break
        return cur, prev

    def _pct_change(cur, prev):
        """Compute percentage change using Pandas-compatible math."""
        if prev and prev != 0:
            return ((cur - prev) / abs(prev)) * 100
        return None

    if income_df is not None and not income_df.empty:
        # Store DF diagnostics
        result["df_info"]["income_shape"] = income_df.shape
        result["df_info"]["income_cols"] = list(income_df.columns)

        # Extract all income statement metrics
        _keys = ["Total Revenue", "Cost Of Revenue", "Gross Profit",
                 "Research And Development", "Selling General And Administration",
                 "Reconciled Depreciation", "Other Operating Expense",
                 "Operating Income", "Interest Expense", "Pretax Income",
                 "Tax Provision", "Net Income"]
        for k in _keys:
            cur, prev = _extract_metric(income_df, k)
            pct = _pct_change(cur, prev)
            result["income"][k] = {
                "current": cur, "previous": prev,
                "pct_change": pct,
                "dollar_change": cur - prev if prev != 0 else None,
            }

        # Derive Gross Profit if missing
        rev = result["income"].get("Total Revenue", {}).get("current", 0)
        cogs = abs(result["income"].get("Cost Of Revenue", {}).get("current", 0))
        gp = result["income"].get("Gross Profit", {}).get("current", 0)
        if gp == 0 and rev > 0 and cogs > 0:
            rev_prev = result["income"]["Total Revenue"]["previous"]
            cogs_prev = abs(result["income"]["Cost Of Revenue"]["previous"])
            gp_derived = rev - cogs
            gp_prev_derived = rev_prev - cogs_prev if rev_prev > 0 and cogs_prev > 0 else 0
            result["income"]["Gross Profit"] = {
                "current": gp_derived, "previous": gp_prev_derived,
                "pct_change": _pct_change(gp_derived, gp_prev_derived),
                "dollar_change": gp_derived - gp_prev_derived if gp_prev_derived != 0 else None,
            }

        # Derive Operating Income if missing
        op_inc = result["income"].get("Operating Income", {}).get("current", 0)
        if op_inc == 0:
            _gp_c = result["income"].get("Gross Profit", {}).get("current", 0)
            if _gp_c > 0:
                _rd_c = abs(result["income"].get("Research And Development", {}).get("current", 0))
                _sg_c = abs(result["income"].get("Selling General And Administration", {}).get("current", 0))
                _da_c = abs(result["income"].get("Reconciled Depreciation", {}).get("current", 0))
                _oe_c = abs(result["income"].get("Other Operating Expense", {}).get("current", 0))
                _oi_derived = _gp_c - _rd_c - _sg_c - _da_c - _oe_c
                _gp_p = result["income"].get("Gross Profit", {}).get("previous", 0)
                _rd_p = abs(result["income"].get("Research And Development", {}).get("previous", 0))
                _sg_p = abs(result["income"].get("Selling General And Administration", {}).get("previous", 0))
                _da_p = abs(result["income"].get("Reconciled Depreciation", {}).get("previous", 0))
                _oe_p = abs(result["income"].get("Other Operating Expense", {}).get("previous", 0))
                _oi_prev = _gp_p - _rd_p - _sg_p - _da_p - _oe_p if _gp_p > 0 else 0
                result["income"]["Operating Income"] = {
                    "current": _oi_derived, "previous": _oi_prev,
                    "pct_change": _pct_change(_oi_derived, _oi_prev),
                    "dollar_change": _oi_derived - _oi_prev if _oi_prev != 0 else None,
                }

    if balance_df is not None and not balance_df.empty:
        result["df_info"]["balance_shape"] = balance_df.shape
        result["df_info"]["balance_cols"] = list(balance_df.columns)
        _bs_keys = ["Total Assets", "Total Liabilities Net Minority Interest",
                     "Total Equity Gross Minority Interest", "Stockholders Equity",
                     "Current Assets", "Current Liabilities", "Cash And Cash Equivalents",
                     "Total Debt", "Net Debt"]
        for k in _bs_keys:
            cur, prev = _extract_metric(balance_df, k)
            pct = _pct_change(cur, prev)
            result["balance"][k] = {
                "current": cur, "previous": prev,
                "pct_change": pct,
                "dollar_change": cur - prev if prev != 0 else None,
            }

    return result


def _cross_validate_metrics(metrics, raw_qtr_df, fy, qa_nums, qb_nums, fy_end):
    """Cross-validate aggregated metrics against raw quarterly data using Pandas.

    Uses the SAME _aggregate_partial_year function that produces the Sankey data
    to independently recompute from the raw quarterly DataFrame, then compares.
    """
    checks = []
    if raw_qtr_df is None or raw_qtr_df.empty:
        return checks

    # Re-aggregate using the EXACT same function that _build_partial_year_df uses
    try:
        all_series = []
        if qa_nums:
            s, _ = _aggregate_partial_year(raw_qtr_df, fy, qa_nums, fy_end, False)
            if s is not None:
                all_series.append(s)
        if qb_nums:
            s, _ = _aggregate_partial_year(raw_qtr_df, fy - 1, qb_nums, fy_end, False)
            if s is not None:
                all_series.append(s)

        if not all_series:
            # Store debug info about why no series were found
            _col_info = []
            for c in raw_qtr_df.columns[:6]:
                try:
                    ts = pd.Timestamp(c)
                    _col_info.append(f"{c} (m={ts.month},y={ts.year})")
                except Exception:
                    _col_info.append(f"{c} (unparseable)")
            checks.append({
                "check": "Column matching",
                "ok": False,
                "displayed": 0,
                "recomputed": 0,
                "diff": 0,
                "detail": f"No columns matched. qa={qa_nums} qb={qb_nums} fy={fy} fy_end={fy_end}. Cols: {_col_info}",
            })
            return checks

        recomputed_series = all_series[0]
        for s in all_series[1:]:
            recomputed_series = recomputed_series.add(s, fill_value=0)

        # Compare key metrics
        def _normalize(s):
            """Remove spaces, underscores, hyphens for fuzzy matching."""
            return s.lower().replace(" ", "").replace("_", "").replace("-", "")

        def _find_in_series(series, name):
            """Find a value in the recomputed series by normalized name."""
            _nk = _normalize(name)
            for idx in series.index:
                if _nk in _normalize(str(idx)):
                    v = series[idx]
                    if pd.notna(v):
                        return float(v)
            return 0.0

        for key in ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]:
            if key not in metrics.get("income", {}):
                continue
            displayed = metrics["income"][key]["current"]
            # Find matching index in the recomputed series
            recomputed = _find_in_series(recomputed_series, key)

            # Derive Gross Profit if not in raw XBRL data (some companies don't file it)
            if key == "Gross Profit" and recomputed == 0.0:
                _xv_rev = _find_in_series(recomputed_series, "Total Revenue")
                _xv_cogs = abs(_find_in_series(recomputed_series, "Cost Of Revenue"))
                if _xv_rev > 0 and _xv_cogs > 0:
                    recomputed = _xv_rev - _xv_cogs
            diff = abs(displayed - recomputed)
            threshold = max(abs(displayed) * 0.001, 1)  # 0.1% tolerance
            checks.append({
                "check": f"{key} (Period A)",
                "ok": diff < threshold,
                "displayed": displayed,
                "recomputed": recomputed,
                "diff": diff,
            })
    except Exception as e:
        checks.append({
            "check": "Cross-validation error",
            "ok": False,
            "displayed": 0,
            "recomputed": 0,
            "diff": 0,
            "detail": str(e),
        })

    return checks


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
    """Aggregate specific fiscal quarters of FY `fy` into a single Series.

    Args:
        qtr_df: DataFrame with quarterly data (columns = dates).
        fy: Fiscal year label (e.g. 2026).
        quarter_list: List of quarter numbers to include, e.g. [1, 2] or [1, 3, 4].
        fy_end: FY end month.
        is_balance_sheet: If True, use latest quarter's snapshot; else sum.

    Returns (Series, label_timestamp) or (None, None) if no matching columns.
    """
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
        # Use the latest quarter's snapshot (last matched column by date)
        latest_col = max(matched_cols, key=lambda c: pd.Timestamp(c))
        return qtr_df[latest_col], latest_col
    else:
        return qtr_df[matched_cols].sum(axis=1), matched_cols[-1]


def _build_partial_year_df(qtr_df, fy_a, fy_b, quarter_list, fy_end,
                           is_balance_sheet=False, qa_nums=None, qb_nums=None):
    """Build a 2-column DataFrame aggregating selected quarters for two FYs.

    The quarter pattern is defined by qa_nums (current-year Qs) and qb_nums
    (previous-year Qs).  Period A aggregates qa_nums from fy_a + qb_nums from
    fy_a-1.  Period B mirrors the same pattern: qa_nums from fy_b + qb_nums
    from fy_b-1.  Falls back to quarter_list for both years if qa/qb not given.

    Column 0 = Period A, Column 1 = Period B.
    """
    # Determine per-year quarter lists
    # IMPORTANT: use `is not None` — an explicit empty list [] means
    # "no sk_Ya/sk_Yb buttons selected", which is different from None
    # (meaning "use the default quarter_list").
    _cur_qs = qa_nums if qa_nums is not None else quarter_list
    _prev_qs = qb_nums if qb_nums is not None else []

    def _aggregate_multi_year(qtr_df, main_fy, cur_qs, prev_qs, fy_end, is_bs):
        """Aggregate quarters across main_fy (cur_qs) and main_fy-1 (prev_qs)."""
        all_series = []
        last_ts = None
        # Current year quarters
        if cur_qs:
            s, ts = _aggregate_partial_year(qtr_df, main_fy, cur_qs, fy_end, is_bs)
            if s is not None:
                all_series.append(s)
                last_ts = ts
        # Previous year quarters
        if prev_qs:
            s, ts = _aggregate_partial_year(qtr_df, main_fy - 1, prev_qs, fy_end, is_bs)
            if s is not None:
                all_series.append(s)
                if last_ts is None:
                    last_ts = ts
        if not all_series:
            return None, None
        if is_bs:
            # Balance sheet: use latest snapshot
            return all_series[0], last_ts
        else:
            # Income: sum all matched quarter series
            combined = all_series[0]
            for s in all_series[1:]:
                combined = combined.add(s, fill_value=0)
            return combined, last_ts

    # ── Compute aggregations for Period A and Period B ──
    #
    # Both periods use _aggregate_multi_year with the SAME cur_qs / prev_qs
    # split.  This preserves the year-spanning structure:
    #   cur_qs (sk_Ya) → main_fy,  prev_qs (sk_Yb) → main_fy - 1
    #
    # Example: Period A=2025, cur_qs=[1,2,3], prev_qs=[4]
    #   Period A: FY2025 Q1-Q3 + FY2024 Q4
    #   Period B (=2024): FY2024 Q1-Q3 + FY2023 Q4   ✓ same 12-month window
    #
    # Special case — 2026 / no-data migration: all Qs moved to sk_Yb
    #   (cur_qs=[], prev_qs=[4]).  Period B must bump main_fy by +1 so
    #   main_fy-1 lands on fy_b.  E.g. Period B=2021 → main_fy=2022 →
    #   prev_qs aggregates FY2021 Q4.
    _fy_b_eff = fy_b
    if _prev_qs and not _cur_qs:
        _fy_b_eff = fy_b + 1

    # Store effective fy_b so labels can use the correct year
    import streamlit as _st_eff
    _st_eff.session_state["_fy_b_eff"] = _fy_b_eff

    # ── Period A ──
    ser_a, ts_a = _aggregate_multi_year(qtr_df, fy_a, _cur_qs, _prev_qs, fy_end, is_balance_sheet)

    # ── Period B: same year-spanning pattern, shifted to fy_b ──
    if fy_a == _fy_b_eff:
        # Same effective year → duplicate for guaranteed 0% delta
        if ser_a is not None:
            ser_b = ser_a.copy()
            ts_b = ts_a
        else:
            ser_b, ts_b = None, None
    else:
        ser_b, ts_b = _aggregate_multi_year(qtr_df, _fy_b_eff, _cur_qs, _prev_qs, fy_end, is_balance_sheet)

    # ── NEVER return raw quarterly DF — it has many columns and _safe/_safe_prev
    # would read two DIFFERENT quarters, producing completely wrong deltas.
    # Always return a controlled 2-column (or 1-column) DataFrame.
    result = pd.DataFrame(index=qtr_df.index)
    if ser_a is not None:
        result["Period_A"] = ser_a
    else:
        # Fill with NaN so the column exists but _safe returns 0
        result["Period_A"] = np.nan
    if ser_b is not None:
        result["Period_B"] = ser_b
    else:
        result["Period_B"] = np.nan

    # Store debug info about what was matched (use different key for income vs balance)
    import streamlit as _st_debug
    _dbg_key = "_agg_debug_bs" if is_balance_sheet else "_agg_debug"
    _st_debug.session_state[_dbg_key] = {
        "fy_a": fy_a, "fy_b": fy_b,
        "cur_qs": list(_cur_qs), "prev_qs": list(_prev_qs),
        "ser_a_found": ser_a is not None,
        "ser_b_found": ser_b is not None,
        "result_shape": result.shape,
        "raw_cols": [str(c) for c in qtr_df.columns[:8]],
        "fy_end": fy_end,
        "is_bs": is_balance_sheet,
    }

    return result


def _reorder_df_for_comparison(df, period_a, period_b, quarterly=False):
    """Reorder DataFrame columns so period_a is col 0, period_b is col 1.

    When quarterly=True, period labels are fiscal quarters (e.g. "Q3 2026").
    Uses FY end month from session_state to map fiscal quarter → calendar date.
    """
    if df is None or df.empty or df.shape[1] < 2:
        return df
    cols = list(df.columns)
    col_dates = []
    for c in cols:
        try:
            col_dates.append(pd.Timestamp(c))
        except Exception:
            col_dates.append(None)

    # Get FY end month for fiscal→calendar conversion
    _fy_end = st.session_state.get("_fy_end_month", 12)

    def _fiscal_q_to_end_month_year(fq, fy):
        """Convert fiscal quarter/year to (end_month, calendar_year)."""
        end_m = (_fy_end + fq * 3) % 12
        if end_m == 0:
            end_m = 12
        # Calendar year: if end_m <= fy_end_month → same as fiscal year
        # otherwise → fiscal year - 1
        if end_m <= _fy_end:
            cal_yr = fy
        else:
            cal_yr = fy - 1
        return end_m, cal_yr

    def _find(period_str):
        if quarterly:
            parts = period_str.split()
            fq = int(parts[0][1])
            fy = int(parts[1])
            end_m, cal_yr = _fiscal_q_to_end_month_year(fq, fy)
            cq = (end_m - 1) // 3 + 1  # calendar quarter of end month
            for i, d in enumerate(col_dates):
                if d and d.year == cal_yr and ((d.month - 1) // 3 + 1) == cq:
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


# âââ SEC EDGAR data source ââââââââââââââââââââââââââââââââââââââââââââââââââ
_SEC_HEADERS = {
    "User-Agent": "QuarterCharts contact@quartercharts.com",
    "Accept-Encoding": "gzip, deflate",
}

# XBRL tag mappings: DataFrame row name â list of possible us-gaap tags (first match wins)
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
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
    ],
    "Gross Profit": [
        "GrossProfit",
        "GrossProfit",  # duplicate intentional — some filings differ in case
    ],
    "Research And Development": [
        "ResearchAndDevelopmentExpense",
        "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
    ],
    "Selling General And Administration": [
        "SellingGeneralAndAdministrativeExpense",
    ],
    # Companies like META report G&A and Selling separately; fetched as
    # individual rows so the SG&A fallback in _show_metric_popup can sum them.
    "General And Administrative Expense": [
        "GeneralAndAdministrativeExpense",
    ],
    "Selling And Marketing Expense": [
        "SellingAndMarketingExpense",
        "SellingExpense",
        "MarketingExpense",
    ],
    "Reconciled Depreciation": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
        "AmortizationOfIntangibleAssets",
    ],
    "Other Operating Expenses": [
        "OtherOperatingIncomeExpenseNet",
        "OtherCostAndExpenseOperating",
        "OtherNonoperatingIncomeExpense",
    ],
    "Operating Income": [
        "OperatingIncomeLoss",
        "IncomeLossFromOperations",
    ],
    "Interest Expense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestExpenseNonoperating",
        "InterestIncomeExpenseNonoperatingNet",
    ],
    "Pretax Income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
    ],
    "Tax Provision": [
        "IncomeTaxExpenseBenefit",
        "IncomeTaxesPaid",
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
        tag_map: Dict mapping display_name â list of XBRL tags
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
                # ââ Annual data: straightforward, one entry per year ââ
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
                # ââ Balance sheet: point-in-time values ââ
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
                # ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
                # QUARTERLY INCOME: YTD-subtraction approach
                # ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
                # SEC EDGAR 10-Q entries for income items report
                # CUMULATIVE year-to-date values:
                #   Q1 â 3-month value (individual = cumulative)
                #   Q2 â 6-month cumulative (Q1+Q2)
                #   Q3 â 9-month cumulative (Q1+Q2+Q3)
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
                # ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

                # ââ Pass 1: Collect frame-based individual quarter values ââ
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

                # ââ Pass 2: YTD subtraction for missing quarters ââ
                # Collect cumulative (max val) per end date from 10-Q
                cum_by_end = {}  # end_date â (max_val, filed, fp)
                fy_annual = {}   # end_date â (val, filed)
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

                # ââ Pass 3: Q4 = FY_annual - Q3_cumulative ââ
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
                # transitions like Revenues â RevenueFromContractâ¦)
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

    # Compute derived fields — track which rows are derived
    _derived_set = set()
    if "Total Non Current Assets" in tag_map and "Total Non Current Assets" not in df.index:
        if "Total Assets" in df.index and "Current Assets" in df.index:
            nca = df.loc["Total Assets"] - df.loc["Current Assets"]
            df.loc["Total Non Current Assets"] = nca
            _derived_set.add("Total Non Current Assets")

    if "Total Non Current Liabilities Net Minority Interest" in tag_map:
        if "Total Non Current Liabilities Net Minority Interest" not in df.index:
            if "Total Liabilities Net Minority Interest" in df.index and "Current Liabilities" in df.index:
                ncl = df.loc["Total Liabilities Net Minority Interest"] - df.loc["Current Liabilities"]
                df.loc["Total Non Current Liabilities Net Minority Interest"] = ncl
                _derived_set.add("Total Non Current Liabilities Net Minority Interest")

    df.attrs["_derived_rows"] = _derived_set
    return df


# âââ Node label â metric mapping âââââââââââââââââââââââââââââââââââââââââ
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


# ---------- Expandable node definitions ------------------------------------
# Maps Sankey node label -> list of children with XBRL tags for sub-breakdowns.
# Used to: (1) mark nodes with star, (2) fetch sub-data, (3) rebuild Sankey.

EXPANDABLE_INCOME_NODES = {
    "SG&A": {
        "children": [
            {"label": "Selling Exp.", "tags": ["SellingExpense", "SellingAndMarketingExpense"], "color_idx": 4},
            {"label": "G&A Exp.", "tags": ["GeneralAndAdministrativeExpense"], "color_idx": 4},
        ],
        "parent_metric": "Selling General And Administration",
    },
    "D&A": {
        "children": [
            {"label": "Depreciation", "tags": ["Depreciation", "DepreciationNonproduction", "DepreciationPropertyPlantAndEquipment"], "color_idx": 5},
            {"label": "Amortization", "tags": ["AmortizationOfIntangibleAssets", "Amortization", "AmortizationOfFinancingCosts"], "color_idx": 5},
        ],
        "parent_metric": "Reconciled Depreciation",
    },
}

EXPANDABLE_BALANCE_NODES = {
    "Equity": {
        "children": [
            {"label": "Common Stock + APIC", "tags": ["CommonStocksIncludingAdditionalPaidInCapital", "CommonStockValue"], "color": "#22c55e"},
            {"label": "Retained Earn.", "tags": ["RetainedEarningsAccumulatedDeficit"], "color": "#14b8a6"},
            {"label": "AOCI", "tags": ["AccumulatedOtherComprehensiveIncomeLossNetOfTax"], "color": "#64748b"},
            {"label": "Treasury Stock", "tags": ["TreasuryStockValue"], "color": "#ef4444"},
        ],
        "parent_metric": "Stockholders Equity",
    },
}


def _fetch_sub_values(ticker: str, children_config: list, form_filter: str = "10-K") -> dict:
    """Fetch sub-breakdown values from EDGAR for a list of children configs.

    Returns dict: {child_label: value} for the most recent filing period.
    """
    try:
        cik = _ticker_to_cik(ticker)
        if not cik:
            return {}
        facts = _fetch_edgar_facts(cik)
        gaap = facts.get("facts", {}).get("us-gaap", {})
    except Exception:
        return {}

    result = {}
    for child in children_config:
        label = child["label"]
        for tag in child["tags"]:
            concept = gaap.get(tag)
            if not concept:
                continue
            entries = concept.get("units", {}).get("USD", [])
            if not entries:
                continue
            best_val, best_date = None, ""
            for e in entries:
                form = e.get("form", "")
                if form_filter == "10-K" and form != "10-K":
                    continue
                if form_filter == "10-Q" and form not in ("10-Q", "10-K"):
                    continue
                end = e.get("end", "")
                val = e.get("val")
                if val is not None and end > best_date:
                    best_val = abs(float(val))
                    best_date = end
            if best_val is not None and best_val > 0:
                result[label] = best_val
                break
    return result


# âââ Node info: "What it means" + "How to read it" for Sankey popups ââââââ
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

    # ââ Inject custom CSS for the timeframe buttons ââ
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


    # ââ Frequency toggle: Quarterly / Annual ââ
    freq_key = f"tf_freq_{view}_{clean_label}"
    if freq_key not in st.session_state:
        st.session_state[freq_key] = "Quarterly"

    # ââ Period toggle: 1Y / 2Y / 4Y / MAX ââ
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

    # ââ Navigation pills inside popup ââ
    all_metrics = list(metric_map.keys())
    popup_nav_key = f"popup_nav_{view}"
    nav_sel = st.pills(
        "",
        all_metrics,
        default=clean_label,
        key=popup_nav_key,
    )
    if nav_sel and nav_sel != clean_label:
        # Use pending dialog mechanism — sets pill value BEFORE widget is
        # instantiated on the next rerun, avoiding StreamlitAPIException.
        st.session_state['_pending_dialog_metric'] = nav_sel
        st.session_state['_pending_dialog_section'] = view
        st.rerun()
    freq = st.session_state[freq_key]
    period = st.session_state[period_key]

    # ââ Fetch data based on frequency ââ
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


    # Fallback: SG&A = G&A + Selling/Marketing when combined tag is missing
    if (series is None or series.empty) and yf_key == "Selling General And Administration":
        ga = _get_historical_series(src_df, "General And Administrative Expense")
        sm = _get_historical_series(src_df, "Selling And Marketing Expense")
        if ga is not None or sm is not None:
            if ga is not None and sm is not None:
                common = ga.index.intersection(sm.index)
                if len(common) > 0:
                    series = (ga.reindex(common, fill_value=0) + sm.reindex(common, fill_value=0)).sort_index()
            elif ga is not None:
                series = ga
            else:
                series = sm


    # Fallback: Gross Profit = Revenue - Cost of Revenue
    if (series is None or series.empty) and yf_key == "Gross Profit":
        rev = _get_historical_series(src_df, "Total Revenue")
        cogs = _get_historical_series(src_df, "Cost Of Revenue")
        if rev is not None and cogs is not None:
            common = rev.index.intersection(cogs.index)
            if len(common) > 0:
                computed = rev.reindex(common) - cogs.reindex(common).abs()
                if not computed.empty and computed.sum() > 0:
                    series = computed.sort_index()

    # Fallback: Cost of Revenue = Revenue - Gross Profit
    if (series is None or series.empty) and yf_key == "Cost Of Revenue":
        rev = _get_historical_series(src_df, "Total Revenue")
        gp = _get_historical_series(src_df, "Gross Profit")
        if rev is not None and gp is not None:
            common = rev.index.intersection(gp.index)
            if len(common) > 0:
                computed = rev.reindex(common) - gp.reindex(common)
                computed = computed.clip(lower=0)
                if not computed.empty and computed.sum() > 0:
                    series = computed.sort_index()

    # ââ Fallback: compute "Other OpEx" as residual when not directly available ââ
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

    # ââ Fallback: compute "Investments" as residual when not directly available ââ
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

    # ââ Filter by period ââ
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

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "scrollZoom": False, "modeBarButtons": [["toImage"]]}, key=f"hist_{freq}_{period}")
    # ââ Node info: "What it means" + "How to read it" ââ
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



def _inject_pill_hover_js(metric_map, color_map):
    """Inject JS that:
    1. Colors each pill on hover using its Sankey node color (background + border).
    2. Highlights the matching Sankey node & links while dimming the rest.
    """
    import json as _json
    colors_js = _json.dumps(color_map)

    js = f"""
    <script>
    (function() {{
        const COLORS = {colors_js};
        const parentDoc = window.parent.document;

        function hexToRgba(hex, alpha) {{
            var r = parseInt(hex.slice(1,3), 16);
            var g = parseInt(hex.slice(3,5), 16);
            var b = parseInt(hex.slice(5,7), 16);
            return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
        }}

        function setupPillHovers() {{
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            if (!btns.length) return false;
            var bound = false;
            btns.forEach(function(btn) {{
                if (btn._pillHoverBound) return;
                btn._pillHoverBound = true;
                bound = true;
                var label = btn.textContent.trim();
                var color = COLORS[label];
                if (!color) return;

                btn.addEventListener('mouseenter', function() {{
                    btn.style.background = hexToRgba(color, 0.15);
                    btn.style.borderColor = color;
                    btn.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.4) + ', 0 0 10px 3px ' + hexToRgba(color, 0.35);
                    btn.style.color = color;
                    highlightSankey(label, color);
                }});
                btn.addEventListener('mouseleave', function() {{
                    btn.style.background = '';
                    btn.style.borderColor = '';
                    btn.style.boxShadow = '';
                    btn.style.color = '';
                    resetSankey();
                }});
            }});
            return bound;
        }}

        function highlightKpi(label, color) {{
            var metrics = parentDoc.querySelectorAll('[data-testid="stMetric"]');
            metrics.forEach(function(card) {{
                var lbl = card.querySelector('[data-testid="stMetricLabel"]');
                if (!lbl) return;
                if (lbl.textContent.trim() === label) {{
                    card.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.5) + ', 0 0 16px 4px ' + hexToRgba(color, 0.3);
                    card.style.transform = 'translateY(-2px)';
                    card.style.transition = 'box-shadow 0.25s ease, transform 0.2s ease';
                    card.style.borderRadius = '8px';
                }}
            }});
        }}

        function resetKpis() {{
            var metrics = parentDoc.querySelectorAll('[data-testid="stMetric"]');
            metrics.forEach(function(card) {{
                card.style.boxShadow = '';
                card.style.transform = '';
            }});
        }}

        function extractLabel(raw) {{
            return (raw || '').split(/  /)[0].replace(/\u2605\\s*/g, '').trim();
        }}

        function highlightSankey(pillLabel, color) {{
            var plots = parentDoc.querySelectorAll('.js-plotly-plot');
            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;

                var nodeRects = sankeyEl.querySelectorAll('.node-rect');
                var nodeLabels = sankeyEl.querySelectorAll('.node-label');
                nodeRects.forEach(function(r) {{ r.style.opacity = '0.2'; r.style.transition = 'opacity 0.25s ease'; }});
                nodeLabels.forEach(function(l) {{ l.style.opacity = '0.2'; l.style.transition = 'opacity 0.25s ease'; }});

                var links = sankeyEl.querySelectorAll('.sankey-link');
                links.forEach(function(lnk) {{ lnk.style.opacity = '0.08'; lnk.style.transition = 'opacity 0.25s ease'; }});

                /* Use customdata (actual labels) instead of SVG text (empty) */
                var matchIdx = -1;
                var cd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                for (var i = 0; i < cd.length; i++) {{
                    if (extractLabel(cd[i]) === pillLabel) {{ matchIdx = i; break; }}
                }}

                if (matchIdx >= 0 && nodeRects[matchIdx]) {{
                    nodeRects[matchIdx].style.opacity = '1';
                    nodeRects[matchIdx].style.filter = 'drop-shadow(0 0 8px ' + color + ')';
                }}
                if (matchIdx >= 0 && nodeLabels[matchIdx]) {{
                    nodeLabels[matchIdx].style.opacity = '1';
                    nodeLabels[matchIdx].style.fontWeight = '700';
                }}
                /* Bold the matching annotation text (text + all tspans) */
                var annots = plotDiv.querySelectorAll('.annotation');
                if (matchIdx >= 0 && annots[matchIdx]) {{
                    var atxt = annots[matchIdx].querySelector('text');
                    if (atxt) {{
                        atxt.setAttribute('font-weight', '700');
                        atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '700'); }});
                    }}
                }}

                if (matchIdx >= 0 && plotDiv.data[0].link) {{
                    var linkData = plotDiv.data[0].link;
                    links.forEach(function(lnk, li) {{
                        if (linkData.source[li] === matchIdx || linkData.target[li] === matchIdx) {{
                            lnk.style.opacity = '0.7';
                        }}
                    }});
                }}
            }});
            highlightKpi(pillLabel, color);
        }}

        function resetSankey() {{
            var plots = parentDoc.querySelectorAll('.js-plotly-plot');
            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;
                sankeyEl.querySelectorAll('.node-rect').forEach(function(r) {{
                    r.style.opacity = '';
                    r.style.filter = '';
                }});
                sankeyEl.querySelectorAll('.node-label').forEach(function(l) {{
                    l.style.opacity = '';
                    l.style.fontWeight = '';
                }});
                sankeyEl.querySelectorAll('.sankey-link').forEach(function(lnk) {{
                    lnk.style.opacity = '';
                }});
                /* Unbold all annotations (text + tspans) */
                plotDiv.querySelectorAll('.annotation text').forEach(function(atxt) {{
                    atxt.setAttribute('font-weight', '400');
                    atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '400'); }});
                }});
            }});
            resetKpis();
        }}

        /* Persistent: re-bind pill hovers whenever Streamlit recreates buttons
           (e.g. sidebar collapse/uncollapse triggers rerun). */
        var _deb = null;
        var obs = new MutationObserver(function() {{
            clearTimeout(_deb);
            _deb = setTimeout(function() {{ setupPillHovers(); }}, 200);
        }});
        obs.observe(parentDoc.body, {{childList: true, subtree: true}});
        setupPillHovers();
        setInterval(function() {{ setupPillHovers(); }}, 3000);
    }})();
    </script>
    """
    components.html(js, height=0)



def _inject_sankey_click_js(metric_map, section="income"):
    """Inject JS that bridges Sankey node clicks to Streamlit via query params.

    When a user clicks a Sankey node, the JS sets ?open_metric=<label>&metric_section=<section>
    in the parent URL, which triggers a Streamlit rerun that opens the dialog.
    This triggers the existing st.pills â st.dialog flow.
    """
    # Build a JS set of valid pill labels for fast lookup
    valid_labels = list(metric_map.keys())
    labels_js = ", ".join(f'"{lbl}"' for lbl in valid_labels)

    js = f"""
    <script>
    (function() {{
        const VALID = new Set([{labels_js}]);
        const SECTION = "{section}";
        const parentDoc = window.parent.document;

        /* Guard against double-fire */
        var _clickGuard = false;
        function clickPill(label) {{
            if (_clickGuard) return;
            _clickGuard = true;
            setTimeout(function() {{ _clickGuard = false; }}, 2000);
            /* Use window.parent.eval() to execute React fiber onClick in the
               parent's JS context — equivalent to running from browser console.
               This bypasses iframe sandbox navigation restrictions and properly
               triggers Streamlit server-side reruns. */
            var safeLabel = label.replace(/'/g, "\\\\'");
            window.parent.eval(
                "(function(){{" +
                "var btns=document.querySelectorAll('[data-testid=\\\"stBaseButton-pills\\\"]');" +
                "for(var i=0;i<btns.length;i++){{" +
                "  if(btns[i].textContent.trim()==='" + safeLabel + "'){{" +
                "    var fk=Object.keys(btns[i]).find(function(k){{return k.startsWith('__reactFiber')||k.startsWith('__reactInternalInstance')}});" +
                "    if(fk){{" +
                "      var f=btns[i][fk];" +
                "      while(f){{" +
                "        if(f.memoizedProps&&typeof f.memoizedProps.onClick==='function'){{" +
                "          f.memoizedProps.onClick(new MouseEvent('click',{{bubbles:true}}));" +
                "          return;" +
                "        }}" +
                "        f=f.return;" +
                "      }}" +
                "    }}" +
                "    btns[i].click();" +
                "    return;" +
                "  }}" +
                "}}" +
                "}})();"
            );
        }}

        function extractLabel(raw) {{
            return (raw || '').split(/<br>|  /)[0].replace(/\\n/g, '').replace(/\u2605\\s*/g, '').trim();
        }}

        function attach() {{
            const plots = parentDoc.querySelectorAll('.js-plotly-plot');
            if (!plots.length) return false;

            let attached = false;
            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;

                // Detect SVG rebuild
                if (plotDiv._clickBoundSankeyRef !== sankeyEl) {{
                    plotDiv._sankey_click_bound = false;
                    plotDiv._clickBoundSankeyRef = sankeyEl;
                }}
                if (plotDiv._sankey_click_bound) return;

                // Build index-to-label map from customdata (SVG labels are empty)
                var nodeLabels = sankeyEl.querySelectorAll('.node-label');
                var cd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                var idxToLabel = {{}};
                for (var ci = 0; ci < cd.length; ci++) {{
                    var txt = extractLabel(cd[ci]);
                    if (txt && VALID.has(txt)) idxToLabel[ci] = txt;
                }}

                // Make annotations clickable + hoverable (not pass-through)
                var annots = plotDiv.querySelectorAll('.annotation');
                annots.forEach(function(a, ai) {{
                    a.style.pointerEvents = 'all';
                    a.style.cursor = 'pointer';
                    a.addEventListener('click', function(e) {{
                        var label = idxToLabel[ai];
                        if (label) {{
                            clickPill(label);
                            e.stopPropagation();
                        }}
                    }});
                }});

                // Attach click handlers to SVG node rects and text labels using index
                var rects = sankeyEl.querySelectorAll('.node-rect');
                rects.forEach(function(r, ri) {{
                    r.style.cursor = 'pointer';
                    r.style.pointerEvents = 'all';
                    r.addEventListener('click', function(e) {{
                        var label = idxToLabel[ri];
                        if (label) {{
                            clickPill(label);
                            e.stopPropagation();
                        }}
                    }});
                }});
                nodeLabels.forEach(function(lbl, li) {{
                    lbl.style.cursor = 'pointer';
                    lbl.style.pointerEvents = 'all';
                    lbl.addEventListener('click', function(e) {{
                        var label = idxToLabel[li];
                        if (label) {{
                            clickPill(label);
                            e.stopPropagation();
                        }}
                    }});
                }});

                // Attach click handlers to link SVG paths
                var links = sankeyEl.querySelectorAll('.sankey-link');
                links.forEach(function(lnk, li) {{
                    lnk.style.cursor = 'pointer';
                    lnk.style.pointerEvents = 'all';
                    lnk.addEventListener('click', function(e) {{
                        if (!plotDiv.data || !plotDiv.data[0] || !plotDiv.data[0].link) return;
                        var tgtIdx = plotDiv.data[0].link.target[li];
                        var tgtLabel = idxToLabel[tgtIdx];
                        if (tgtLabel) {{
                            clickPill(tgtLabel);
                            e.stopPropagation();
                            return;
                        }}
                        var srcIdx = plotDiv.data[0].link.source[li];
                        var srcLabel = idxToLabel[srcIdx];
                        if (srcLabel) {{
                            clickPill(srcLabel);
                            e.stopPropagation();
                        }}
                    }});
                }});

                plotDiv._sankey_click_bound = true;
                attached = true;
            }});
            return attached;
        }}

        /* Persistent: re-attach after sidebar toggle rebuilds the chart */
        var _deb = null;
        var obs = new MutationObserver(function() {{
            clearTimeout(_deb);
            _deb = setTimeout(function() {{ attach(); }}, 200);
        }});
        obs.observe(parentDoc.body, {{childList: true, subtree: true}});
        attach();
        setInterval(function() {{ attach(); }}, 3000);
    }})();
    </script>
    """

    components.html(js, height=0)


def _inject_node_hover_js(metric_map, color_map):
    """Inject JS that highlights the matching pill when hovering a Sankey node.

    Uses Plotly's plotly_hover / plotly_unhover events for reliable detection.
    """
    import json as _json
    colors_js = _json.dumps(color_map)

    js = f"""
    <script>
    (function() {{
        const COLORS = {colors_js};
        const parentDoc = window.parent.document;

        function hexToRgba(hex, alpha) {{
            var r = parseInt(hex.slice(1,3), 16);
            var g = parseInt(hex.slice(3,5), 16);
            var b = parseInt(hex.slice(5,7), 16);
            return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
        }}

        function findPillByLabel(label) {{
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            for (var i = 0; i < btns.length; i++) {{
                if (btns[i].textContent.trim() === label) return btns[i];
            }}
            return null;
        }}

        function highlightPill(label, color) {{
            var btn = findPillByLabel(label);
            if (!btn) return;
            btn.style.background = hexToRgba(color, 0.15);
            btn.style.borderColor = color;
            btn.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.4) + ', 0 0 10px 3px ' + hexToRgba(color, 0.35);
            btn.style.color = color;
        }}

        function resetPills() {{
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            btns.forEach(function(btn) {{
                btn.style.background = '';
                btn.style.borderColor = '';
                btn.style.boxShadow = '';
                btn.style.color = '';
            }});
        }}

        function highlightKpi(label, color) {{
            var metrics = parentDoc.querySelectorAll('[data-testid="stMetric"]');
            metrics.forEach(function(card) {{
                var lbl = card.querySelector('[data-testid="stMetricLabel"]');
                if (!lbl) return;
                if (lbl.textContent.trim() === label) {{
                    card.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.5) + ', 0 0 16px 4px ' + hexToRgba(color, 0.3);
                    card.style.transform = 'translateY(-2px)';
                    card.style.transition = 'box-shadow 0.25s ease, transform 0.2s ease';
                    card.style.borderRadius = '8px';
                }}
            }});
        }}

        function resetKpis() {{
            var metrics = parentDoc.querySelectorAll('[data-testid="stMetric"]');
            metrics.forEach(function(card) {{
                card.style.boxShadow = '';
                card.style.transform = '';
            }});
        }}

        function highlightSankeyAndPill(nodeIdx, label, color, sankeyEl, plotDiv) {{
            highlightPill(label, color);
            highlightKpi(label, color);
            var nodeRects = sankeyEl.querySelectorAll('.node-rect');
            var nodeLabels = sankeyEl.querySelectorAll('.node-label');
            nodeRects.forEach(function(r) {{ r.style.opacity = '0.2'; r.style.transition = 'opacity 0.25s ease'; }});
            nodeLabels.forEach(function(l) {{ l.style.opacity = '0.2'; l.style.transition = 'opacity 0.25s ease'; }});
            var links = sankeyEl.querySelectorAll('.sankey-link');
            links.forEach(function(lnk) {{ lnk.style.opacity = '0.08'; lnk.style.transition = 'opacity 0.25s ease'; }});
            if (nodeRects[nodeIdx]) {{
                nodeRects[nodeIdx].style.opacity = '1';
                nodeRects[nodeIdx].style.filter = 'drop-shadow(0 0 8px ' + color + ')';
            }}
            if (nodeLabels[nodeIdx]) {{
                nodeLabels[nodeIdx].style.opacity = '1';
                nodeLabels[nodeIdx].style.fontWeight = '700';
            }}
            /* Bold the matching annotation (text + all tspans) */
            var annots = plotDiv.querySelectorAll('.annotation');
            if (annots[nodeIdx]) {{
                var atxt = annots[nodeIdx].querySelector('text');
                if (atxt) {{
                    atxt.setAttribute('font-weight', '700');
                    atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '700'); }});
                }}
            }}
            if (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].link) {{
                var linkData = plotDiv.data[0].link;
                links.forEach(function(lnk, li) {{
                    if (linkData.source[li] === nodeIdx || linkData.target[li] === nodeIdx) {{
                        lnk.style.opacity = '0.85';
                        lnk.style.filter = 'brightness(1.1)';
                    }}
                }});
            }}
        }}

        function resetSankey(sankeyEl) {{
            sankeyEl.querySelectorAll('.node-rect').forEach(function(r) {{
                r.style.opacity = ''; r.style.filter = '';
            }});
            sankeyEl.querySelectorAll('.node-label').forEach(function(l) {{
                l.style.opacity = ''; l.style.fontWeight = '';
            }});
            sankeyEl.querySelectorAll('.sankey-link').forEach(function(lnk) {{
                lnk.style.opacity = ''; lnk.style.filter = '';
            }});
            /* Unbold all annotations (text + tspans) */
            var plotDiv = sankeyEl.closest('.js-plotly-plot');
            if (plotDiv) plotDiv.querySelectorAll('.annotation text').forEach(function(atxt) {{
                atxt.setAttribute('font-weight', '400');
                atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '400'); }});
            }});
            resetKpis();
        }}

        function extractLabel(raw) {{
            return (raw || '').split(/<br>|  /)[0].replace(/\\n/g, '').replace(/\u2605\\s*/g, '').trim();
        }}

        function attach() {{
            var plots = parentDoc.querySelectorAll('.js-plotly-plot');
            if (!plots.length) return false;
            var attached = false;

            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;

                // Detect SVG rebuild: if the .sankey element changed, rebind
                if (plotDiv._boundSankeyRef !== sankeyEl) {{
                    plotDiv._nodeHoverBound2 = false;
                    plotDiv._boundSankeyRef = sankeyEl;
                }}
                if (plotDiv._nodeHoverBound2) return;

                // Build label-to-index map from customdata (SVG labels are empty)
                var cd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                var labelMap = {{}};
                for (var ci = 0; ci < cd.length; ci++) {{
                    var txt = extractLabel(cd[ci]);
                    if (txt && COLORS[txt]) labelMap[txt] = ci;
                }}

                // Use Plotly hover/unhover events (reliable for Sankey)
                plotDiv.on('plotly_hover', function(data) {{
                    if (!data || !data.points || !data.points[0]) return;
                    var pt = data.points[0];
                    // Skip link hovers — only handle node hovers
                    if (pt.hasOwnProperty('flow') || pt.hasOwnProperty('source') || pt.hasOwnProperty('target')) return;
                    var idx = pt.pointNumber;
                    if (typeof idx !== 'number') return;
                    // Get label from customdata
                    var curCd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                    var label = extractLabel(curCd[idx] || '');
                    var color = COLORS[label];
                    if (!label || !color) return;
                    // Re-query sankeyEl in case SVG was rebuilt
                    var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                    highlightSankeyAndPill(idx, label, color, currentSankey, plotDiv);
                }});

                plotDiv.on('plotly_unhover', function() {{
                    resetPills();
                    var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                    resetSankey(currentSankey);
                }});

                /* Direct mouseenter/mouseleave on node-rects for reliable bold */
                var nodeRects = sankeyEl.querySelectorAll('.node-rect');
                nodeRects.forEach(function(r, ri) {{
                    r.addEventListener('mouseenter', function() {{
                        var curCd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                        var label = extractLabel(curCd[ri] || '');
                        var color = COLORS[label];
                        if (!label || !color) return;
                        var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                        highlightSankeyAndPill(ri, label, color, currentSankey, plotDiv);
                    }});
                    r.addEventListener('mouseleave', function() {{
                        resetPills();
                        var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                        resetSankey(currentSankey);
                    }});
                }});

                /* Also hover on annotation text (3-row labels) → same glow */
                var annots = plotDiv.querySelectorAll('.annotation');
                annots.forEach(function(a, ai) {{
                    a.style.cursor = 'pointer';
                    a.addEventListener('mouseenter', function() {{
                        var curCd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                        var label = extractLabel(curCd[ai] || '');
                        var color = COLORS[label];
                        if (!label || !color) return;
                        var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                        highlightSankeyAndPill(ai, label, color, currentSankey, plotDiv);
                    }});
                    a.addEventListener('mouseleave', function() {{
                        resetPills();
                        var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                        resetSankey(currentSankey);
                    }});
                }});

                plotDiv._nodeHoverBound2 = true;
                attached = true;
            }});
            return attached;
        }}

        /* Persistent: re-attach after sidebar toggle rebuilds the chart */
        var _deb = null;
        var obs = new MutationObserver(function() {{
            clearTimeout(_deb);
            _deb = setTimeout(function() {{ attach(); }}, 200);
        }});
        obs.observe(parentDoc.body, {{childList: true, subtree: true}});
        attach();
        setInterval(function() {{ attach(); }}, 3000);
    }})();
    </script>
    """
    components.html(js, height=0)


def _inject_delta_color_js():
    """Inject JS that colors the YoY delta portion of Sankey node labels.

    Finds arrow characters (\u2191 / \u2193) in each SVG node-label text,
    then wraps the arrow + percentage + dollar delta in a colored <tspan>:
      green (#16a34a) for positive (\u2191)
      red   (#dc2626) for negative (\u2193)
    """
    js = """
    <script>
    (function() {
        const UP = '\u2191', DOWN = '\u2193';
        const GREEN = '#16a34a', RED = '#dc2626';
        const parentDoc = window.parent.document;

        function needsColorize(label) {
            /* Check if this label has unprocessed arrow chars in its raw tspans.
               Plotly can rebuild label text in-place, overwriting our colored
               tspans while keeping the same DOM node. Detect this by looking
               for arrow chars in tspans that are NOT .delta-suffix. */
            var tspans = label.querySelectorAll('tspan');
            var targets = tspans.length ? tspans : [label];
            for (var i = 0; i < targets.length; i++) {
                if (targets[i].classList && targets[i].classList.contains('delta-suffix')) continue;
                var txt = targets[i].textContent || '';
                if (txt.indexOf(UP) >= 0 || txt.indexOf(DOWN) >= 0) return true;
            }
            return false;
        }

        function colorize() {
            var labels = parentDoc.querySelectorAll('.sankey .node-label');
            if (!labels.length) return false;
            var did = false;
            labels.forEach(function(label) {
                if (!needsColorize(label)) return;
                /* Remove any stale .delta-suffix tspans from a previous run
                   (Plotly may have partially rebuilt the label). */
                label.querySelectorAll('.delta-suffix').forEach(function(ds) { ds.remove(); });
                var tspans = label.querySelectorAll('tspan');
                var targets = tspans.length ? tspans : [label];
                targets.forEach(function(el) {
                    var txt = el.textContent || '';
                    var idxUp = txt.indexOf(UP);
                    var idxDown = txt.indexOf(DOWN);
                    var idx = -1, color = '';
                    if (idxUp >= 0 && (idxDown < 0 || idxUp < idxDown)) {
                        idx = idxUp; color = GREEN;
                    } else if (idxDown >= 0) {
                        idx = idxDown; color = RED;
                    }
                    if (idx < 0) return;
                    var before = txt.substring(0, idx);
                    var after = txt.substring(idx);
                    if (/[+-]0\.0%/.test(after) || /[+-]\$0[^.]/.test(after) || /[+-]\$0$/.test(after)) {
                        color = '#64748b';
                    }
                    if (el.tagName === 'tspan') {
                        el.textContent = before;
                        var colored = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
                        colored.textContent = after;
                        colored.setAttribute('fill', color);
                        colored.setAttribute('font-weight', '400');
                        colored.classList.add('delta-suffix');
                        el.parentNode.insertBefore(colored, el.nextSibling);
                    } else {
                        el.textContent = before;
                        var colored = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
                        colored.textContent = after;
                        colored.setAttribute('fill', color);
                        colored.setAttribute('font-weight', '400');
                        colored.classList.add('delta-suffix');
                        el.appendChild(colored);
                    }
                });
                did = true;
            });
            return did;
        }

        /* Persistent observer: re-colorize whenever Plotly rebuilds the SVG
           (e.g. sidebar collapse/uncollapse triggers Streamlit rerender). */
        var _debounce = null;
        var obs = new MutationObserver(function() {
            clearTimeout(_debounce);
            _debounce = setTimeout(function() { colorize(); }, 200);
        });
        obs.observe(parentDoc.body, {childList: true, subtree: true});
        colorize();
        /* Poll frequently as fallback — catches in-place Plotly updates */
        setInterval(function() { colorize(); }, 1500);
    })();
    </script>
    """
    components.html(js, height=0)


def _inject_kpi_hover_js(kpi_labels_to_nodes, color_map, section="income"):
    """Inject JS that highlights matching Sankey node + pill when hovering a KPI metric card.

    kpi_labels_to_nodes: dict mapping KPI card label (e.g. "Revenue") to Sankey node name
    color_map: dict mapping node name to hex color
    """
    import json as _json
    map_js = _json.dumps(kpi_labels_to_nodes)
    colors_js = _json.dumps(color_map)

    js = f"""
    <script>
    (function() {{
        const KPI_MAP = {map_js};
        const COLORS = {colors_js};
        const SECTION = "{section}";
        const parentDoc = window.parent.document;

        function hexToRgba(hex, alpha) {{
            var r = parseInt(hex.slice(1,3), 16);
            var g = parseInt(hex.slice(3,5), 16);
            var b = parseInt(hex.slice(5,7), 16);
            return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
        }}

        function extractLabel(raw) {{
            return (raw || '').split(/  /)[0].replace(/\u2605\\s*/g, '').trim();
        }}

        function highlightSankey(nodeLabel, color) {{
            var plots = parentDoc.querySelectorAll('.js-plotly-plot');
            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;
                var nodeRects = sankeyEl.querySelectorAll('.node-rect');
                var nodeLabels = sankeyEl.querySelectorAll('.node-label');
                nodeRects.forEach(function(r) {{ r.style.opacity = '0.2'; r.style.transition = 'opacity 0.25s ease'; }});
                nodeLabels.forEach(function(l) {{ l.style.opacity = '0.2'; l.style.transition = 'opacity 0.25s ease'; }});
                var links = sankeyEl.querySelectorAll('.sankey-link');
                links.forEach(function(lnk) {{ lnk.style.opacity = '0.08'; lnk.style.transition = 'opacity 0.25s ease'; }});

                /* Use customdata (actual labels) instead of SVG text (empty) */
                var matchIdx = -1;
                var cd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                for (var i = 0; i < cd.length; i++) {{
                    if (extractLabel(cd[i]) === nodeLabel) {{ matchIdx = i; break; }}
                }}

                if (matchIdx >= 0 && nodeRects[matchIdx]) {{
                    nodeRects[matchIdx].style.opacity = '1';
                    nodeRects[matchIdx].style.filter = 'drop-shadow(0 0 8px ' + color + ')';
                }}
                if (matchIdx >= 0 && nodeLabels[matchIdx]) {{
                    nodeLabels[matchIdx].style.opacity = '1';
                    nodeLabels[matchIdx].style.fontWeight = '700';
                }}
                /* Bold matching annotation (text + all tspans) */
                var annots = plotDiv.querySelectorAll('.annotation');
                if (matchIdx >= 0 && annots[matchIdx]) {{
                    var atxt = annots[matchIdx].querySelector('text');
                    if (atxt) {{
                        atxt.setAttribute('font-weight', '700');
                        atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '700'); }});
                    }}
                }}
                if (matchIdx >= 0 && plotDiv.data[0].link) {{
                    var linkData = plotDiv.data[0].link;
                    links.forEach(function(lnk, li) {{
                        if (linkData.source[li] === matchIdx || linkData.target[li] === matchIdx) {{
                            lnk.style.opacity = '0.7';
                        }}
                    }});
                }}
            }});
            /* Also highlight the matching pill button */
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            btns.forEach(function(btn) {{
                if (btn.textContent.trim() === nodeLabel) {{
                    btn.style.background = hexToRgba(color, 0.15);
                    btn.style.borderColor = color;
                    btn.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.4) + ', 0 0 10px 3px ' + hexToRgba(color, 0.35);
                    btn.style.color = color;
                }}
            }});
        }}

        function resetAll() {{
            var plots = parentDoc.querySelectorAll('.js-plotly-plot');
            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;
                sankeyEl.querySelectorAll('.node-rect').forEach(function(r) {{
                    r.style.opacity = ''; r.style.filter = '';
                }});
                sankeyEl.querySelectorAll('.node-label').forEach(function(l) {{
                    l.style.opacity = ''; l.style.fontWeight = '';
                }});
                sankeyEl.querySelectorAll('.sankey-link').forEach(function(lnk) {{
                    lnk.style.opacity = '';
                }});
                /* Unbold all annotations (text + tspans) */
                plotDiv.querySelectorAll('.annotation text').forEach(function(atxt) {{
                    atxt.setAttribute('font-weight', '400');
                    atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '400'); }});
                }});
            }});
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            btns.forEach(function(btn) {{
                btn.style.background = '';
                btn.style.borderColor = '';
                btn.style.boxShadow = '';
                btn.style.color = '';
            }});
        }}

        /* Guard against double-fire */
        var _clickGuard = false;
        function clickPill(label) {{
            if (_clickGuard) return;
            _clickGuard = true;
            setTimeout(function() {{ _clickGuard = false; }}, 2000);
            /* Use window.parent.eval() to execute React fiber onClick in the
               parent's JS context — equivalent to running from browser console.
               This bypasses iframe sandbox navigation restrictions and properly
               triggers Streamlit server-side reruns. */
            var safeLabel = label.replace(/'/g, "\\\\'");
            window.parent.eval(
                "(function(){{" +
                "var btns=document.querySelectorAll('[data-testid=\\\"stBaseButton-pills\\\"]');" +
                "for(var i=0;i<btns.length;i++){{" +
                "  if(btns[i].textContent.trim()==='" + safeLabel + "'){{" +
                "    var fk=Object.keys(btns[i]).find(function(k){{return k.startsWith('__reactFiber')||k.startsWith('__reactInternalInstance')}});" +
                "    if(fk){{" +
                "      var f=btns[i][fk];" +
                "      while(f){{" +
                "        if(f.memoizedProps&&typeof f.memoizedProps.onClick==='function'){{" +
                "          f.memoizedProps.onClick(new MouseEvent('click',{{bubbles:true}}));" +
                "          return;" +
                "        }}" +
                "        f=f.return;" +
                "      }}" +
                "    }}" +
                "    btns[i].click();" +
                "    return;" +
                "  }}" +
                "}}" +
                "}})();"
            );
        }}

        function setupKpiHovers() {{
            /* Reset any stale glow/highlight from previous session */
            var metrics = parentDoc.querySelectorAll('[data-testid="stMetric"]');
            metrics.forEach(function(card) {{
                card.style.boxShadow = '';
                card.style.transform = '';
            }});
            var plots = parentDoc.querySelectorAll('.js-plotly-plot');
            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;
                sankeyEl.querySelectorAll('.node-rect').forEach(function(r) {{ r.style.opacity = ''; r.style.filter = ''; }});
                sankeyEl.querySelectorAll('.node-label').forEach(function(l) {{ l.style.opacity = ''; l.style.fontWeight = ''; }});
                sankeyEl.querySelectorAll('.sankey-link').forEach(function(lnk) {{ lnk.style.opacity = ''; lnk.style.filter = ''; }});
            }});
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            btns.forEach(function(btn) {{ btn.style.background = ''; btn.style.borderColor = ''; btn.style.boxShadow = ''; btn.style.color = ''; }});

            if (!metrics.length) return false;
            var bound = false;
            metrics.forEach(function(card) {{
                if (card._kpiHoverBound) return;
                var labelEl = card.querySelector('[data-testid="stMetricLabel"]');
                if (!labelEl) return;
                var labelText = labelEl.textContent.trim();
                var nodeLabel = KPI_MAP[labelText];
                var color = nodeLabel ? COLORS[nodeLabel] : null;
                if (!nodeLabel || !color) return;
                card._kpiHoverBound = true;
                bound = true;
                card.style.cursor = 'pointer';
                card.style.transition = 'box-shadow 0.25s ease, transform 0.2s ease';
                card.style.borderRadius = '8px';
                card.style.overflow = 'visible';
                card.style.position = 'relative';
                card.style.zIndex = '1';
                /* Fix immediate column wrapper clipping the glow — only
                   go up 3 levels to avoid breaking the page scroll container */
                var _p = card.parentElement;
                for (var _pi = 0; _pi < 3 && _p; _pi++) {{
                    _p.style.overflow = 'visible';
                    _p = _p.parentElement;
                }}
                /* Use both mouseenter and mouseover for max compatibility */
                function _doHighlight() {{
                    card.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.5) + ', 0 0 16px 4px ' + hexToRgba(color, 0.3);
                    card.style.transform = 'translateY(-2px)';
                    card.style.zIndex = '10';
                    highlightSankey(nodeLabel, color);
                }}
                function _doReset() {{
                    card.style.boxShadow = '';
                    card.style.transform = '';
                    card.style.zIndex = '1';
                    resetAll();
                }}
                card.addEventListener('mouseenter', _doHighlight);
                card.addEventListener('mouseleave', _doReset);
                card.addEventListener('click', function() {{
                    clickPill(nodeLabel);
                }});
                /* Also bind on all children so hover fires on inner text */
                card.querySelectorAll('*').forEach(function(child) {{
                    child.addEventListener('mouseenter', function(e) {{
                        e.stopPropagation();
                        _doHighlight();
                    }});
                }});
            }});
            return bound;
        }}

        var _deb = null;
        var obs = new MutationObserver(function() {{
            clearTimeout(_deb);
            _deb = setTimeout(function() {{ setupKpiHovers(); }}, 200);
        }});
        obs.observe(parentDoc.body, {{childList: true, subtree: true}});
        setupKpiHovers();
        setInterval(function() {{ setupKpiHovers(); }}, 3000);
    }})();
    </script>
    """
    components.html(js, height=0)


def _inject_link_hover_js(color_map):
    """Inject JS that highlights connected nodes + pill when hovering a Sankey link.

    When a user hovers a link, the two connected nodes glow, matching pills
    highlight, and the hovered link stays fully opaque while others dim.
    """
    import json as _json
    colors_js = _json.dumps(color_map)

    js = f"""
    <script>
    (function() {{
        const COLORS = {colors_js};
        const parentDoc = window.parent.document;

        function hexToRgba(hex, alpha) {{
            var r = parseInt(hex.slice(1,3), 16);
            var g = parseInt(hex.slice(3,5), 16);
            var b = parseInt(hex.slice(5,7), 16);
            return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
        }}

        function extractLabel(raw) {{
            return (raw || '').split(/<br>|  /)[0].replace(/\\n/g, '').replace(/\u2605\\s*/g, '').trim();
        }}

        function highlightLink(linkIdx, sankeyEl, plotDiv) {{
            var nodeRects = sankeyEl.querySelectorAll('.node-rect');
            var nodeLabels = sankeyEl.querySelectorAll('.node-label');
            var links = sankeyEl.querySelectorAll('.sankey-link');

            /* Dim everything first */
            nodeRects.forEach(function(r) {{ r.style.opacity = '0.2'; r.style.transition = 'opacity 0.25s ease'; }});
            nodeLabels.forEach(function(l) {{ l.style.opacity = '0.2'; l.style.transition = 'opacity 0.25s ease'; }});
            links.forEach(function(lnk) {{ lnk.style.opacity = '0.08'; lnk.style.transition = 'opacity 0.25s ease'; }});

            /* Highlight the hovered link */
            if (links[linkIdx]) links[linkIdx].style.opacity = '0.85';

            if (!plotDiv.data || !plotDiv.data[0] || !plotDiv.data[0].link) return;
            var linkData = plotDiv.data[0].link;
            var srcIdx = linkData.source[linkIdx];
            var tgtIdx = linkData.target[linkIdx];

            /* Highlight only the TARGET node */
            var cd = (plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
            var annots = plotDiv.querySelectorAll('.annotation');
            [tgtIdx].forEach(function(nIdx) {{
                if (nIdx === undefined || nIdx === null) return;
                if (nodeRects[nIdx]) {{
                    nodeRects[nIdx].style.opacity = '1';
                    var txt = extractLabel(cd[nIdx] || '');
                    var color = COLORS[txt];
                    if (color) nodeRects[nIdx].style.filter = 'drop-shadow(0 0 8px ' + color + ')';
                }}
                if (nodeLabels[nIdx]) {{
                    nodeLabels[nIdx].style.opacity = '1';
                    nodeLabels[nIdx].style.fontWeight = '700';
                }}
                /* Bold matching annotation (text + all tspans) */
                if (annots[nIdx]) {{
                    var atxt = annots[nIdx].querySelector('text');
                    if (atxt) {{
                        atxt.setAttribute('font-weight', '700');
                        atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '700'); }});
                    }}
                }}
            }});

            /* Highlight links connected to the TARGET node only */
            links.forEach(function(lnk, li) {{
                if (linkData.source[li] === tgtIdx || linkData.target[li] === tgtIdx) {{
                    lnk.style.opacity = '0.7';
                }}
            }});
            /* Keep hovered link brightest */
            if (links[linkIdx]) links[linkIdx].style.opacity = '0.85';

            /* Highlight matching pills and KPI cards for TARGET only */
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            var kpiCards = parentDoc.querySelectorAll('[data-testid="stMetric"]');
            [tgtIdx].forEach(function(nIdx) {{
                if (nIdx === undefined || nIdx === null) return;
                var txt = extractLabel(cd[nIdx] || '');
                var color = COLORS[txt];
                if (!txt || !color) return;
                btns.forEach(function(btn) {{
                    if (btn.textContent.trim() === txt) {{
                        btn.style.background = hexToRgba(color, 0.15);
                        btn.style.borderColor = color;
                        btn.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.4) + ', 0 0 10px 3px ' + hexToRgba(color, 0.35);
                        btn.style.color = color;
                    }}
                }});
                kpiCards.forEach(function(card) {{
                    var lbl = card.querySelector('[data-testid="stMetricLabel"]');
                    if (lbl && lbl.textContent.trim() === txt) {{
                        card.style.boxShadow = '0 0 0 2px ' + hexToRgba(color, 0.5) + ', 0 0 16px 4px ' + hexToRgba(color, 0.3);
                        card.style.transform = 'translateY(-2px)';
                        card.style.transition = 'box-shadow 0.25s ease, transform 0.2s ease';
                        card.style.borderRadius = '8px';
                    }}
                }});
            }});
        }}

        function resetAll(sankeyEl) {{
            sankeyEl.querySelectorAll('.node-rect').forEach(function(r) {{
                r.style.opacity = ''; r.style.filter = '';
            }});
            sankeyEl.querySelectorAll('.node-label').forEach(function(l) {{
                l.style.opacity = ''; l.style.fontWeight = '';
            }});
            sankeyEl.querySelectorAll('.sankey-link').forEach(function(lnk) {{
                lnk.style.opacity = '';
            }});
            /* Unbold all annotations (text + tspans) */
            var plotDiv = sankeyEl.closest('.js-plotly-plot');
            if (plotDiv) plotDiv.querySelectorAll('.annotation text').forEach(function(atxt) {{
                atxt.setAttribute('font-weight', '400');
                atxt.querySelectorAll('tspan').forEach(function(ts) {{ ts.setAttribute('font-weight', '400'); }});
            }});
            var btns = parentDoc.querySelectorAll('[data-testid="stBaseButton-pills"]');
            btns.forEach(function(btn) {{
                btn.style.background = '';
                btn.style.borderColor = '';
                btn.style.boxShadow = '';
                btn.style.color = '';
            }});
            var kpiCards = parentDoc.querySelectorAll('[data-testid="stMetric"]');
            kpiCards.forEach(function(card) {{
                card.style.boxShadow = '';
                card.style.transform = '';
            }});
        }}

        function attach() {{
            var plots = parentDoc.querySelectorAll('.js-plotly-plot');
            if (!plots.length) return false;
            var attached = false;
            plots.forEach(function(plotDiv) {{
                var sankeyEl = plotDiv.querySelector('.sankey');
                if (!sankeyEl) return;
                if (plotDiv._linkHoverBoundRef !== sankeyEl) {{
                    plotDiv._linkHoverBound = false;
                    plotDiv._linkHoverBoundRef = sankeyEl;
                }}
                if (plotDiv._linkHoverBound) return;

                var links = sankeyEl.querySelectorAll('.sankey-link');
                var cd = (plotDiv.data && plotDiv.data[0] && plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                links.forEach(function(lnk, li) {{
                    lnk.style.cursor = 'pointer';
                    lnk.style.pointerEvents = 'all';
                    lnk.addEventListener('mouseenter', function() {{
                        var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                        highlightLink(li, currentSankey, plotDiv);
                    }});
                    lnk.addEventListener('mouseleave', function() {{
                        var currentSankey = plotDiv.querySelector('.sankey') || sankeyEl;
                        resetAll(currentSankey);
                    }});
                    /* Click link → open Historical Trend for TARGET node */
                    lnk.addEventListener('click', function(e) {{
                        if (!plotDiv.data || !plotDiv.data[0] || !plotDiv.data[0].link) return;
                        var tgtIdx = plotDiv.data[0].link.target[li];
                        var curCd = (plotDiv.data[0].node) ? plotDiv.data[0].node.customdata : [];
                        var label = extractLabel(curCd[tgtIdx] || '');
                        if (!label) return;
                        var safeLabel = label.replace(/'/g, "\\\\'");
                        window.parent.eval(
                            "(function(){{" +
                            "var btns=document.querySelectorAll('[data-testid=\\\"stBaseButton-pills\\\"]');" +
                            "for(var i=0;i<btns.length;i++){{" +
                            "  if(btns[i].textContent.trim()==='" + safeLabel + "'){{" +
                            "    var fk=Object.keys(btns[i]).find(function(k){{return k.startsWith('__reactFiber')||k.startsWith('__reactInternalInstance')}});" +
                            "    if(fk){{" +
                            "      var f=btns[i][fk];" +
                            "      while(f){{" +
                            "        if(f.memoizedProps&&typeof f.memoizedProps.onClick==='function'){{" +
                            "          f.memoizedProps.onClick(new MouseEvent('click',{{bubbles:true}}));" +
                            "          return;" +
                            "        }}" +
                            "        f=f.return;" +
                            "      }}" +
                            "    }}" +
                            "    btns[i].click();" +
                            "    return;" +
                            "  }}" +
                            "}}" +
                            "}})();"
                        );
                        e.stopPropagation();
                    }});
                }});

                plotDiv._linkHoverBound = true;
                attached = true;
            }});
            return attached;
        }}

        var _deb = null;
        var obs = new MutationObserver(function() {{
            clearTimeout(_deb);
            _deb = setTimeout(function() {{ attach(); }}, 200);
        }});
        obs.observe(parentDoc.body, {{childList: true, subtree: true}});
        attach();
        setInterval(function() {{ attach(); }}, 3000);
    }})();
    </script>
    """
    components.html(js, height=0)


def _generate_sankey_pdf(income_df, balance_df, info, ticker, view="income"):
    """Generate a professional PDF with actual Sankey flow diagram + KPI cards.

    Income Statement  â Sankey diagram matching the on-screen Plotly version.
    Balance Sheet     â Sankey diagram matching the on-screen Plotly version.
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
        scale = 0.85 / max(total_height, 1)  # scale factor to convert value â y height

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
                # ââ Extract data (same as _build_income_sankey) ââ
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

                # ââ Build nodes: (label, value, x, y_center, color) ââ
                # Layout: 5 columns matching the Plotly Sankey
                # Wide X spacing for PDF Sankey (matplotlib-drawn, not Plotly)
                X1, X2, X3, X4, X5 = 0.01, 0.14, 0.32, 0.52, 0.68
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

                # ââ Build links: (src_idx, tgt_idx, value, color) ââ
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

                # ââ Draw figure ââ
                fig = plt.figure(figsize=(16, 9), facecolor="white")
                if _logo_img is not None:
                    logo_ax = fig.add_axes([0.20, 0.93, 0.03, 0.05])
                    logo_ax.imshow(_logo_img)
                    logo_ax.axis("off")
                fig.text(0.5, 0.96, f"{company} ({ticker}) \u2014 Income Statement Flow",
                         ha="center", va="top", fontsize=20, fontweight="bold",
                         color="#0f172a")

                # Adaptive KPI row — only include metrics with data
                _pdf_kpis = []
                if revenue != 0:
                    _pdf_kpis.append(("Revenue", revenue))
                if gross_profit != 0:
                    _pdf_kpis.append(("Gross Profit", gross_profit))
                if op_income != 0 or not _pdf_kpis:
                    _pdf_kpis.append(("Operating Income", op_income))
                if net_income != 0 or len(_pdf_kpis) < 2:
                    _pdf_kpis.append(("Net Income", net_income))
                _draw_kpi_row(fig, _pdf_kpis)

                ax = fig.add_axes([0.06, 0.05, 0.88, 0.78])
                _draw_sankey(ax, nodes, links, revenue)

                fig.text(0.5, 0.01,
                         f"QuarterCharts  \u00b7  SEC EDGAR data  \u00b7  {ticker}",
                         ha="center", va="bottom", fontsize=8, color="#94a3b8")
                pdf.savefig(fig, facecolor="white", dpi=150)
                plt.close(fig)

            else:
                # ââ Balance Sheet Sankey ââ
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

                # ââ Links ââ
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

                # ââ Draw figure ââ
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
        if quarterly:
            income = _edgar_build_df(facts, _XBRL_INCOME_TAGS, form_filter="10-Q", quarterly_income=True)
            balance = _edgar_build_df(facts, _XBRL_BALANCE_TAGS, form_filter="10-Q", quarterly_income=False)
        else:
            income = _edgar_build_df(facts, _XBRL_INCOME_TAGS, form_filter="10-K")
            balance = _edgar_build_df(facts, _XBRL_BALANCE_TAGS, form_filter="10-K")
        info = {"shortName": entity_name, "longName": entity_name}
        return income, balance, info
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), {"shortName": ticker}


def _build_income_sankey(income_df, info, compare_label="YoY", same_period=False,
                         expanded_nodes=None, ticker=None):
    """Build income statement Sankey with fixed positions and vivid nodes.

    Flow: Revenue -> COGS + Gross Profit -> Expenses + Operating Income
          -> Interest + Pretax Income -> Tax + Net Income

    All flows are reconciled so that parent = sum of children at every level.
    expanded_nodes: set of node labels currently expanded (e.g. {"SG&A"})
    ticker: needed to fetch sub-breakdown data from EDGAR when expanding
    """
    if expanded_nodes is None:
        expanded_nodes = set()
    # Extract values
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

    # --- Previous period values for % change labels ---
    p_revenue       = _safe_prev(income_df, "Total Revenue")
    p_cogs          = abs(_safe_prev(income_df, "Cost Of Revenue"))
    p_gross_profit  = _safe_prev(income_df, "Gross Profit")
    if p_gross_profit == 0 and p_revenue > 0:
        p_gross_profit = p_revenue - p_cogs  # works for p_cogs=0 too (financial cos)
    p_rd_expense    = abs(_safe_prev(income_df, "Research And Development"))
    p_sga_expense   = abs(_safe_prev(income_df, "Selling General And Administration"))
    p_dep_amort     = abs(_safe_prev(income_df, "Reconciled Depreciation"))
    if p_dep_amort == 0:
        p_dep_amort = abs(_safe_prev(income_df, "Depreciation And Amortization"))
    p_other_opex    = abs(_safe_prev(income_df, "Other Operating Expense"))
    p_operating_inc = _safe_prev(income_df, "Operating Income")
    p_interest_exp  = abs(_safe_prev(income_df, "Interest Expense"))
    p_pretax_income = _safe_prev(income_df, "Pretax Income") or _safe_prev(income_df, "Income Before Tax")
    p_tax           = abs(_safe_prev(income_df, "Tax Provision"))
    p_net_income    = _safe_prev(income_df, "Net Income")
    # Derive missing previous-period residuals
    if p_other_opex == 0 and p_gross_profit > 0 and p_operating_inc > 0:
        p_other_opex = max(0, p_gross_profit - p_rd_expense - p_sga_expense - p_dep_amort - p_operating_inc)
    if p_operating_inc == 0 and p_gross_profit > 0:
        p_operating_inc = max(0, p_gross_profit - p_rd_expense - p_sga_expense - p_dep_amort - p_other_opex)
    if p_pretax_income == 0 and p_operating_inc > 0:
        p_pretax_income = max(0, p_operating_inc - p_interest_exp)
    # Derive previous-period other_nonop if there's a gap
    p_other_nonop = 0
    if p_operating_inc > 0 and p_pretax_income > 0:
        p_gap = p_operating_inc - p_pretax_income
        if p_gap >= 0:
            if p_interest_exp > 0 and p_gap > p_interest_exp * 1.5:
                p_other_nonop = p_gap - p_interest_exp
            elif p_interest_exp == 0:
                p_other_nonop = p_gap
    if p_net_income == 0 and p_pretax_income > 0:
        p_net_income = max(0, p_pretax_income - p_tax)

    if revenue == 0:
        return None, []

    # --- Reconcile flows top-down (parent is authoritative) ---
    # Level 1: Revenue = COGS + Gross Profit
    if gross_profit == 0 and revenue > 0:
        gross_profit = revenue - cogs
    if cogs == 0 and revenue > 0 and gross_profit > 0:
        cogs = revenue - gross_profit
    level1_sum = cogs + gross_profit
    if level1_sum != revenue and level1_sum > 0:
        cogs = round(cogs * revenue / level1_sum)
        gross_profit = revenue - cogs

    # Level 2: Gross Profit = expenses + Operating Income
    # Preserve reported OI; cap D&A first (often overlaps with COGS)
    if operating_inc == 0 and gross_profit > 0:
        operating_inc = gross_profit - rd_expense - sga_expense - dep_amort - other_opex
    if gross_profit > 0 and operating_inc > 0:
        opex_budget = gross_profit - operating_inc
        total = rd_expense + sga_expense + dep_amort + other_opex
        if total <= opex_budget:
            other_opex = opex_budget - rd_expense - sga_expense - dep_amort
        else:
            other_opex = 0
            if rd_expense + sga_expense + dep_amort <= opex_budget:
                other_opex = opex_budget - rd_expense - sga_expense - dep_amort
            elif rd_expense + sga_expense <= opex_budget:
                dep_amort = opex_budget - rd_expense - sga_expense
            elif rd_expense <= opex_budget:
                dep_amort = 0
                sga_expense = opex_budget - rd_expense
            else:
                dep_amort = 0
                sga_expense = 0
                rd_expense = opex_budget
    elif gross_profit > 0:
        known_exp = rd_expense + sga_expense + dep_amort + other_opex
        operating_inc = max(0, gross_profit - known_exp)

    # Level 3: Operating Income = Interest + Other Non-Op + Pretax Income
    other_nonop = 0
    if pretax_income == 0:
        pretax_income = operating_inc - interest_exp
    if interest_exp + pretax_income != operating_inc and operating_inc > 0:
        gap = operating_inc - pretax_income
        if gap >= 0:
            # If reported interest is small relative to gap, split into
            # Interest Exp + Other Non-Op (investment losses, insurance, etc.)
            if interest_exp > 0 and gap > interest_exp * 1.5:
                other_nonop = gap - interest_exp
            else:
                interest_exp = gap
        else:
            pretax_income = operating_inc - interest_exp

    # Level 4: Pretax Income = Tax + Net Income
    if net_income == 0:
        net_income = pretax_income - tax
    if tax + net_income != pretax_income and pretax_income > 0:
        tax_adj = pretax_income - net_income
        if tax_adj >= 0:
            tax = tax_adj
        else:
            net_income = pretax_income - tax

    # ── Handle negative OI with positive downstream values ──
    # When OI < 0 but pretax/net income > 0 (non-operating income exceeds
    # operating loss), preserve downstream values by treating the flow as:
    #   GP → [expenses eat all GP] + [OI = pretax_income + interest_exp]
    # This keeps the Sankey showing accurate Net Income.
    _orig_oi = operating_inc
    _orig_pretax = pretax_income
    _orig_net = net_income
    _orig_tax = tax

    if operating_inc < 0 and (_orig_pretax > 0 or _orig_net > 0):
        # Company has non-op income exceeding the operating loss.
        # Set OI = pretax + interest (absorb non-op gains into OI for Sankey).
        _effective_pretax = max(_orig_pretax, 0) if _orig_pretax > 0 else max(_orig_net + _orig_tax, 0)
        operating_inc = _effective_pretax + max(interest_exp, 0)
        if operating_inc <= 0:
            operating_inc = max(_orig_net, 0) + max(_orig_tax, 0) + max(interest_exp, 0)
        # Re-balance expenses to fit: expenses = GP - OI
        if gross_profit > 0 and operating_inc < gross_profit:
            opex_budget = gross_profit - operating_inc
            total = rd_expense + sga_expense + dep_amort + other_opex
            if total > 0:
                scale = opex_budget / total
                rd_expense = round(rd_expense * scale)
                sga_expense = round(sga_expense * scale)
                dep_amort = round(dep_amort * scale)
                other_opex = opex_budget - rd_expense - sga_expense - dep_amort
            else:
                other_opex = opex_budget
        pretax_income = _effective_pretax
        net_income = max(_orig_net, 0)
        tax = max(pretax_income - net_income, 0)
        other_nonop = 0

    # Ensure all positive for Sankey
    revenue = max(revenue, 0)
    cogs = max(cogs, 0)
    gross_profit = max(gross_profit, 0)
    rd_expense = max(rd_expense, 0)
    sga_expense = max(sga_expense, 0)
    dep_amort = max(dep_amort, 0)
    other_opex = max(other_opex, 0)
    operating_inc = max(operating_inc, 0)
    interest_exp = max(interest_exp, 0)
    other_nonop = max(other_nonop, 0)
    pretax_income = max(pretax_income, 0)
    tax = max(tax, 0)
    net_income = max(net_income, 0)

    # Final reconciliation after clamping to zero
    if cogs + gross_profit != revenue:
        gross_profit = revenue - cogs
        if gross_profit < 0:
            gross_profit = 0
            cogs = revenue
    total_exp = rd_expense + sga_expense + dep_amort + other_opex
    if total_exp + operating_inc != gross_profit and gross_profit > 0:
        if operating_inc > 0:
            opex_budget = gross_profit - operating_inc
            other_opex = 0
            if rd_expense + sga_expense + dep_amort <= opex_budget:
                other_opex = opex_budget - rd_expense - sga_expense - dep_amort
            elif rd_expense + sga_expense <= opex_budget:
                dep_amort = opex_budget - rd_expense - sga_expense
            elif rd_expense <= opex_budget:
                dep_amort = 0
                sga_expense = opex_budget - rd_expense
            else:
                dep_amort = 0
                sga_expense = 0
                rd_expense = opex_budget
        else:
            diff = gross_profit - total_exp - operating_inc
            if diff > 0:
                other_opex += diff
            else:
                operating_inc = 0
                other_opex = max(0, gross_profit - rd_expense - sga_expense - dep_amort)
    if interest_exp + other_nonop + pretax_income != operating_inc:
        gap = operating_inc - pretax_income
        if gap >= 0:
            if interest_exp > 0 and gap > interest_exp * 1.5:
                other_nonop = gap - interest_exp
            else:
                interest_exp = gap
                other_nonop = 0
        else:
            pretax_income = operating_inc - interest_exp - other_nonop
            if pretax_income < 0:
                pretax_income = 0
                other_nonop = 0
                interest_exp = operating_inc
    if tax + net_income != pretax_income:
        net_income = pretax_income - tax
        if net_income < 0:
            net_income = 0
            tax = pretax_income

    # ── Store reconciled Sankey values for audit panel ──
    import streamlit as _st_rec
    _st_rec.session_state["_sankey_reconciled"] = {
        "Revenue": revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "R&D": rd_expense,
        "SG&A": sga_expense,
        "D&A": dep_amort,
        "Other OpEx": other_opex,
        "Operating Income": operating_inc,
        "Interest Exp.": interest_exp,
        "Other Non-Op": other_nonop,
        "Pretax Income": pretax_income,
        "Tax": tax,
        "Net Income": net_income,
    }
    _st_rec.session_state["_sankey_reconciled_prev"] = {
        "Revenue": p_revenue,
        "COGS": p_cogs,
        "Gross Profit": p_gross_profit,
        "R&D": p_rd_expense,
        "SG&A": p_sga_expense,
        "D&A": p_dep_amort,
        "Other OpEx": p_other_opex,
        "Operating Income": p_operating_inc,
        "Interest Exp.": p_interest_exp,
        "Other Non-Op": p_other_nonop,
        "Pretax Income": p_pretax_income,
        "Tax": p_tax,
        "Net Income": p_net_income,
    }

    # Wide X spacing — text is placed via annotations (not built-in labels)
    # Col1/Col2 use 2-row labels (shorter) so can be closer together
    X1, X2, X3, X4, X5 = 0.01, 0.14, 0.32, 0.52, 0.68
    colors = VIVID
    nodes = []
    node_colors = []
    node_x = []
    node_y = []
    node_val_raw = []    # raw numeric value (for bar height calculation)
    node_name_list = []  # "Revenue" (for 3-row annotations)
    node_val_str = []    # "$68.30B" (for 3-row annotations)
    node_row2 = []       # "↑+15.2% +$68.30B" (for 3-row annotations)
    imap = {}
    def add(name, val, color_idx, x, y, prev_val=None, expandable=False):
        y = round(max(0.01, min(0.99, y)), 4)
        imap[name] = len(nodes)
        display_name = name
        pct = _yoy(val, prev_val)
        delta_str = _fmt_delta(val, prev_val) if prev_val is not None else None
        pct_suffix = ""
        if pct is not None:
            diff = val - prev_val if prev_val is not None else 0
            arrow = "\u2191" if diff >= 0 else "\u2193"
            pct_suffix = f"  {arrow}{pct:+.1f}%"
            if delta_str:
                pct_suffix += f" {delta_str}"
        elif delta_str:
            diff = val - prev_val if prev_val is not None else 0
            arrow = "\u2191" if diff >= 0 else "\u2193"
            pct_suffix = f"  {arrow}{delta_str}"
        nodes.append(f"{display_name}  {_fmt(val)}{pct_suffix}")
        node_name_list.append(display_name)
        node_val_str.append(_fmt(val))
        node_row2.append(pct_suffix.strip() if pct_suffix.strip() else "")
        node_val_raw.append(max(val, 0))
        node_colors.append(colors[color_idx])
        node_x.append(x)
        node_y.append(y)

    # ── Pre-count nodes per column to compute dynamic chart height ──────
    # Nodes in col3/col4/col5 are confined within parent sub-bands, so compute
    # "effective full-chart density" = n_items / band_fraction for each sub-band.
    _c2_n = 2 if cogs > 0 else 1
    _c3_n = sum(1 for v in [rd_expense, sga_expense, dep_amort, other_opex] if v > 0) + 1  # +OI
    _c4_n = sum(1 for v in [interest_exp, other_nonop] if v > 0) + 1  # +Pretax
    _c5_n = (1 if tax > 0 else 0) + 1  # +NI

    # Effective density accounting for sub-band confinement:
    # Col3 items live inside GP band (fraction = gross_profit / revenue)
    _gp_frac = max(gross_profit / revenue, 0.1) if revenue > 0 else 1.0
    _c3_eff = _c3_n / _gp_frac
    # Col4 items live inside OI band (fraction ≈ oi / revenue)
    _oi_val = max(operating_inc, 1)
    _oi_frac = max(_oi_val / revenue, 0.05) if revenue > 0 else 1.0
    _c4_eff = _c4_n / _oi_frac
    # Col5 items live inside Pretax band (similar fraction to OI)
    _c5_eff = _c5_n / _oi_frac

    # Compute font size early (need it for text height calc)
    _n_nodes_est = 1 + _c2_n + _c3_n + _c4_n + _c5_n
    _font_sz_est = 11 if _n_nodes_est <= 12 else (10 if _n_nodes_est <= 16 else 9)

    # Use worst effective density for chart height
    _worst_eff = max(int(c + 0.99) for c in [_c2_n, _c3_eff, _c4_eff, _c5_eff])
    _h = _compute_dynamic_height([_worst_eff], _font_sz_est)

    # Minimum band height per node (paper coords): ensures text fits
    _min_text_band = _min_band_for_text(_font_sz_est, _h, has_row2=True)

    # ── Band-confined proportional Y-positioning ────────────────────────
    # Key principle: each column's children are confined WITHIN the
    # vertical band of their parent node.  This guarantees zero crossings.
    #
    #   Revenue  occupies full [Y_MIN, Y_MAX]
    #   Col 2:   COGS + GP  split Revenue's band
    #   Col 3:   Expenses + OI  split GP's band
    #   Col 4:   IntExp + NonOp + Pretax  split OI's band
    #   Col 5:   Tax + Net Income  split Pretax's band
    #
    Y_MIN, Y_MAX = 0.04, 0.96

    def _split_band(values, band_top, band_bot):
        """Split a vertical band into sub-bands proportional to values.

        Each child's band height = max(proportional_height, _min_text_band)
        so that the 3-row text label always fits within the node's allocated slot.
        When the parent band is too small for all children at minimum text height,
        items overflow the parent band (centered) rather than compressing and overlapping.
        """
        n = len(values)
        if n == 0:
            return []
        span = band_bot - band_top
        if n == 1:
            cy = (band_top + band_bot) / 2
            return [(cy, band_top, band_bot)]
        total = sum(values)
        if total <= 0:
            step = max(span / n, _min_text_band)
            needed = step * n
            start = band_top + (span - needed) / 2
            start = max(Y_MIN, min(start, Y_MAX - needed))
            return [(round(max(Y_MIN, min(Y_MAX, start + step * (i + 0.5))), 4),
                     round(max(Y_MIN, start + step * i), 4),
                     round(min(Y_MAX, start + step * (i + 1)), 4)) for i in range(n)]

        # Compute proportional sub-bands, enforcing text-height minimum
        results = []
        cursor = band_top
        for v in values:
            raw_band = (v / total) * span
            band_h = max(raw_band, _min_text_band)
            results.append((cursor, band_h))
            cursor += band_h

        # Rescale if we overflowed
        actual_span = sum(h for _, h in results)
        if actual_span > span + 0.001:
            needed_at_min = n * _min_text_band
            if needed_at_min <= span:
                # Band can fit all items at minimum — scale only excess above minimums
                excess_total = sum(max(0, h - _min_text_band) for _, h in results)
                target_excess = span - needed_at_min
                if excess_total > 0:
                    scale = target_excess / excess_total
                    results2, cursor = [], band_top
                    for _, h in results:
                        above = max(0, h - _min_text_band)
                        h2 = _min_text_band + above * scale
                        results2.append((cursor, h2))
                        cursor += h2
                    results = results2
                else:
                    step = span / n
                    results = [(band_top + step * i, step) for i in range(n)]
            else:
                # Band too small — overflow centered, each item gets _min_text_band
                mid = (band_top + band_bot) / 2
                start = mid - needed_at_min / 2
                start = max(Y_MIN, min(start, Y_MAX - needed_at_min))
                results = [(start + _min_text_band * i, _min_text_band) for i in range(n)]

        # Build (centre, top, bot) tuples
        out = []
        for top_y, h in results:
            bot_y = top_y + h
            centre = top_y + h / 2
            out.append((round(max(Y_MIN, min(Y_MAX, centre)), 4),
                         round(max(Y_MIN, top_y), 4),
                         round(min(Y_MAX, bot_y), 4)))
        return out

    # --- Column 1: Revenue (full band) ---
    rev_band = (Y_MIN, Y_MAX)
    rev_y = (Y_MIN + Y_MAX) / 2
    add("Revenue", revenue, 0, X1, rev_y, p_revenue)

    # --- Column 2: COGS + Gross Profit (split Revenue's band) ---
    if cogs > 0:
        c2 = _split_band([cogs, gross_profit], *rev_band)
        add("Cost of Revenue", cogs, 1, X2, c2[0][0], p_cogs)
        add("Gross Profit", gross_profit, 2, X2, c2[1][0], p_gross_profit)
        gp_band = (c2[1][1], c2[1][2])  # GP's sub-band → parent for col 3
    else:
        add("Gross Profit", gross_profit, 2, X2, rev_y, p_gross_profit)
        gp_band = rev_band  # GP == Revenue, inherits full band

    # --- Fetch sub-breakdown data for ALL expandable nodes ---
    _sub_cache = {}
    if ticker:
        for exp_name, cfg in EXPANDABLE_INCOME_NODES.items():
            _sub_cache[exp_name] = _fetch_sub_values(ticker, cfg["children"])

    _can_expand = set()
    for exp_name, sub in _sub_cache.items():
        if exp_name not in EXPANDABLE_INCOME_NODES:
            continue
        n_children = sum(1 for ch in EXPANDABLE_INCOME_NODES[exp_name]["children"] if sub.get(ch["label"], 0) > 0)
        if n_children >= 2:
            _can_expand.add(exp_name)

    # --- Column 3: Expenses + Operating Income (split GP's band) ---
    _expanded_children = {}
    col3_items = []  # [(label, value, color_idx, prev_val, expandable)]

    if rd_expense > 0:
        col3_items.append(("R&D", rd_expense, 3, p_rd_expense, False))

    if sga_expense > 0:
        _sga_expandable = "SG&A" in _can_expand
        if _sga_expandable and "SG&A" in expanded_nodes:
            sub = _sub_cache["SG&A"]
            children = []
            for ch in EXPANDABLE_INCOME_NODES["SG&A"]["children"]:
                ch_val = sub.get(ch["label"], 0)
                if ch_val > 0:
                    children.append((ch["label"], ch_val, ch["color_idx"]))
            ch_sum = sum(v for _, v, _ in children)
            if ch_sum > 0 and children:
                scale = sga_expense / ch_sum
                children = [(l, round(v * scale), ci) for l, v, ci in children]
                _expanded_children["SG&A"] = children
                for ch_label, ch_val, ch_ci in children:
                    col3_items.append((ch_label, ch_val, ch_ci, None, False))
            else:
                # Fallback: no valid children → show parent node unexpanded
                col3_items.append(("SG&A", sga_expense, 4, p_sga_expense, _sga_expandable))
        else:
            col3_items.append(("SG&A", sga_expense, 4, p_sga_expense, _sga_expandable))

    if dep_amort > 0:
        _da_expandable = "D&A" in _can_expand
        if _da_expandable and "D&A" in expanded_nodes:
            sub = _sub_cache["D&A"]
            children = []
            for ch in EXPANDABLE_INCOME_NODES["D&A"]["children"]:
                ch_val = sub.get(ch["label"], 0)
                if ch_val > 0:
                    children.append((ch["label"], ch_val, ch["color_idx"]))
            ch_sum = sum(v for _, v, _ in children)
            if ch_sum > 0 and children:
                scale = dep_amort / ch_sum
                children = [(l, round(v * scale), ci) for l, v, ci in children]
                _expanded_children["D&A"] = children
                for ch_label, ch_val, ch_ci in children:
                    col3_items.append((ch_label, ch_val, ch_ci, None, False))
            else:
                # Fallback: no valid children → show parent node unexpanded
                col3_items.append(("D&A", dep_amort, 5, p_dep_amort, _da_expandable))
        else:
            col3_items.append(("D&A", dep_amort, 5, p_dep_amort, _da_expandable))

    if other_opex > 0:
        col3_items.append(("Other OpEx", other_opex, 5, p_other_opex, False))

    col3_items.append(("Operating Income", operating_inc, 6, p_operating_inc, False))

    c3_vals = [v for _, v, *_ in col3_items]
    c3 = _split_band(c3_vals, *gp_band)
    for i, (lbl, val, ci, pv, expandable) in enumerate(col3_items):
        add(lbl, val, ci, X3, c3[i][0], pv, expandable=expandable)
    oi_y = c3[-1][0]
    oi_band = (c3[-1][1], c3[-1][2])  # OI's sub-band → parent for col 4

    # --- Column 4: Interest Exp + Other Non-Op + Pretax Income (split OI's band) ---
    col4_items = []
    if interest_exp > 0:
        col4_items.append(("Interest Exp.", interest_exp, 7, p_interest_exp))
    if other_nonop > 0:
        col4_items.append(("Other Non-Op", other_nonop, 7, p_other_nonop))
    col4_items.append(("Pretax Income", pretax_income, 8, p_pretax_income))

    c4_vals = [v for _, v, *_ in col4_items]
    c4 = _split_band(c4_vals, *oi_band)
    for i, (lbl, val, ci, pv) in enumerate(col4_items):
        add(lbl, val, ci, X4, c4[i][0], pv)
    pt_y = c4[-1][0]
    pt_band = (c4[-1][1], c4[-1][2])  # Pretax's sub-band → parent for col 5

    # --- Column 5: Tax + Net Income (split Pretax's band) ---
    col5_items = []
    if tax > 0:
        col5_items.append(("Income Tax", tax, 9, p_tax))
    col5_items.append(("Net Income", net_income, 10, p_net_income))

    c5_vals = [v for _, v, *_ in col5_items]
    c5 = _split_band(c5_vals, *pt_band)
    for i, (lbl, val, ci, pv) in enumerate(col5_items):
        add(lbl, val, ci, X5, c5[i][0], pv)

    srcs, tgts, vals, lcolors = [], [], [], []

    def link(src, tgt, val, ci=0):
        s, t = imap.get(src, -1), imap.get(tgt, -1)
        if s >= 0 and t >= 0 and val > 0:
            srcs.append(s)
            tgts.append(t)
            vals.append(val)
            lcolors.append(_rgba(colors[ci]))

    if cogs > 0:
        link("Revenue", "Cost of Revenue", cogs, 1)
    link("Revenue", "Gross Profit", gross_profit, 2)
    if rd_expense > 0:
        link("Gross Profit", "R&D", rd_expense, 3)
    if sga_expense > 0:
        if "SG&A" in _expanded_children:
            for ch_label, ch_val, ch_ci in _expanded_children["SG&A"]:
                link("Gross Profit", ch_label, ch_val, ch_ci)
        else:
            link("Gross Profit", "SG&A", sga_expense, 4)
    if dep_amort > 0:
        if "D&A" in _expanded_children:
            for ch_label, ch_val, ch_ci in _expanded_children["D&A"]:
                link("Gross Profit", ch_label, ch_val, ch_ci)
        else:
            link("Gross Profit", "D&A", dep_amort, 5)
    if other_opex > 0:
        link("Gross Profit", "Other OpEx", other_opex, 5)
    link("Gross Profit", "Operating Income", operating_inc, 6)
    if interest_exp > 0:
        link("Operating Income", "Interest Exp.", interest_exp, 7)
    if other_nonop > 0:
        link("Operating Income", "Other Non-Op", other_nonop, 7)
    link("Operating Income", "Pretax Income", pretax_income, 8)
    if tax > 0:
        link("Pretax Income", "Income Tax", tax, 9)
    link("Pretax Income", "Net Income", net_income, 10)

    if not vals:
        return None, []

    _n_nodes = len(nodes)
    # Scale node padding & thickness
    _pad = max(8, min(22, int(320 / max(_n_nodes, 1))))
    _thickness = max(10, min(18, int(200 / max(_n_nodes, 1))))
    _font_sz = _font_sz_est  # use pre-computed value (same formula)

    # ── Fix gaps: bars → text → cross-column → re-fix vertical ──────────
    # Cross-column fix moves nodes vertically, which can re-introduce
    # vertical overlaps, so we re-run bar/text gap fixes afterward.
    # Use min_gap_px=6 so the bottom of each node has a visible gap to the next.
    _fix_bar_gaps(node_x, node_y, node_val_raw, _h, min_gap_px=6)
    _fix_text_gaps(node_x, node_y, node_row2, _font_sz, _h, min_gap_px=6)
    _fix_cross_column_text(node_x, node_y, node_val_raw, node_name_list,
                           node_val_str, node_row2, _font_sz, _h, _thickness,
                           min_gap_px=6)
    _fix_bar_gaps(node_x, node_y, node_val_raw, _h, min_gap_px=6)
    _fix_text_gaps(node_x, node_y, node_row2, _font_sz, _h, min_gap_px=6)

    _empty_labels = [""] * len(nodes)
    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        orientation="h",
        textfont=dict(size=1, color="rgba(0,0,0,0)"),
        node=dict(pad=_pad, thickness=_thickness, line=dict(color="rgba(0,0,0,0)", width=0),
                  label=_empty_labels, color=node_colors, x=node_x, y=node_y,
                  customdata=nodes,
                  hovertemplate="<b>%{customdata}</b><extra></extra>"),
        link=dict(source=srcs, target=tgts, value=vals, color=lcolors,
                  hovertemplate="Flow: %{value:$,.0f}<extra></extra>"),
        domain=dict(y=[0.04, 0.96]),
    ))
    # _h already computed dynamically above (before layout)
    _layout = dict(height=_h, margin=dict(l=6, r=6, t=20, b=6),
                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                   font=dict(size=_font_sz, family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif", color="#1e293b"))
    fig.update_layout(**_layout)

    # ── Annotation-based labels ──────────────────────────────────────────
    # Annotations are placed at the same node_y (already adjusted by _fix_bar_gaps)
    _dom_y0, _dom_y1 = 0.04, 0.96
    _small_sz = max(8, _font_sz - 2)
    for i in range(len(nodes)):
        x_paper = node_x[i]
        y_paper = _dom_y0 + (_dom_y1 - _dom_y0) * (1.0 - node_y[i])
        r2 = node_row2[i]
        if r2:
            # Color row 3: green for ↑, red for ↓, gray if zero/no arrow
            if "\u2191" in r2:
                _r2_color = "#16a34a"
            elif "\u2193" in r2:
                _r2_color = "#dc2626"
            else:
                _r2_color = "#64748b"
            txt = (f"{node_name_list[i]}<br>"
                   f"{node_val_str[i]}<br>"
                   f"<span style='font-size:{_small_sz}px;color:{_r2_color}'>{r2}</span>")
        else:
            txt = (f"{node_name_list[i]}<br>"
                   f"{node_val_str[i]}")
        fig.add_annotation(
            x=x_paper, y=y_paper,
            xref="paper", yref="paper",
            text=txt,
            showarrow=False,
            align="left",
            xanchor="left",
            yanchor="middle",
            xshift=_thickness // 2 + 1,
            font=dict(size=_font_sz,
                      family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif",
                      color="#1e293b"),
        )
    # Return fig + list of node names that exist in the Sankey
    _actual_nodes = [n for n in node_name_list if n in INCOME_NODE_METRICS]
    return fig, _actual_nodes


def _build_balance_sheet_sankey(balance_df, info, compare_label="YoY", same_period=False,
                                expanded_nodes=None, ticker=None):
    """Build a balance sheet Sankey with fixed positions -- no node crossing.

    All flows are reconciled so that parent = sum of children at every level.
    """
    if expanded_nodes is None:
        expanded_nodes = set()
    total_assets      = _safe(balance_df, "Total Assets")
    current_assets    = _safe(balance_df, "Current Assets")
    noncurrent_assets = _safe(balance_df, "Total Non Current Assets")
    cash              = _safe(balance_df, "Cash And Cash Equivalents")
    # Financial companies: try additional XBRL tags for cash
    if cash == 0:
        cash = (_safe(balance_df, "Cash Cash Equivalents And Federal Funds Sold")
                or _safe(balance_df, "Cash And Due From Banks")
                or _safe(balance_df, "Cash Cash Equivalents And Short Term Investments"))
    short_invest      = _safe(balance_df, "Other Short Term Investments")
    if short_invest == 0:
        short_invest = _safe(balance_df, "Available For Sale Securities")
    receivables       = _safe(balance_df, "Accounts Receivable") or _safe(balance_df, "Receivables")
    if receivables == 0:
        receivables = _safe(balance_df, "Net Loans") or _safe(balance_df, "Loans And Leases")
    inventory         = _safe(balance_df, "Inventory")
    ppe               = _safe(balance_df, "Net PPE") or _safe(balance_df, "Property Plant Equipment")
    goodwill          = _safe(balance_df, "Goodwill")
    intangibles       = _safe(balance_df, "Intangible Assets") or _safe(balance_df, "Other Intangible Assets")
    investments       = _safe(balance_df, "Investments And Advances") or _safe(balance_df, "Long Term Equity Investment")
    if investments == 0:
        investments = _safe(balance_df, "Held To Maturity Securities") or _safe(balance_df, "Trading Securities")
    total_liab        = _safe(balance_df, "Total Liabilities Net Minority Interest") or _safe(balance_df, "Total Liab")
    current_liab      = _safe(balance_df, "Current Liabilities")
    noncurrent_liab   = _safe(balance_df, "Total Non Current Liabilities Net Minority Interest")
    accounts_payable  = _safe(balance_df, "Accounts Payable") or _safe(balance_df, "Payables")
    short_debt        = _safe(balance_df, "Current Debt") or _safe(balance_df, "Short Long Term Debt")
    long_debt         = _safe(balance_df, "Long Term Debt")
    deferred_rev      = _safe(balance_df, "Current Deferred Revenue")
    # Financial companies: extract Deposits as a named liability item
    deposits          = _safe(balance_df, "Deposits") or _safe(balance_df, "Total Deposits")
    equity            = _safe(balance_df, "Stockholders Equity") or _safe(balance_df, "Total Stockholders Equity")
    retained          = _safe(balance_df, "Retained Earnings")

    # --- Previous period values for % change labels ---
    _p = lambda key: _safe_prev(balance_df, key)
    prev_map = {
        "Total Assets": _p("Total Assets"),
        "Current Assets": _p("Current Assets"),
        "Non-Current Assets": _p("Total Non Current Assets"),
        "Cash": _p("Cash And Cash Equivalents"),
        "ST Investments": _p("Other Short Term Investments"),
        "Receivables": _p("Accounts Receivable") or _p("Receivables"),
        "Inventory": _p("Inventory"),
        "Goodwill": _p("Goodwill"),
        "Intangibles": _p("Intangible Assets") or _p("Other Intangible Assets"),
        "Total Liabilities": _p("Total Liabilities Net Minority Interest") or _p("Total Liab"),
        "Current Liab.": _p("Current Liabilities"),
        "Non-Current Liab.": _p("Total Non Current Liabilities Net Minority Interest"),
        "Accounts Payable": _p("Accounts Payable") or _p("Payables"),
        "Short-Term Debt": _p("Current Debt") or _p("Short Long Term Debt"),
        "Long-Term Debt": _p("Long Term Debt"),
        "Deferred Rev.": _p("Current Deferred Revenue"),
        "Equity": _p("Stockholders Equity") or _p("Total Stockholders Equity"),
        "Retained Earnings": _p("Retained Earnings"),
        "PP&E": _p("Net PPE") or _p("Property Plant Equipment"),
        "Investments": _p("Investments And Advances") or _p("Long Term Equity Investment"),
        "Deferred Revenue": _p("Current Deferred Revenue"),
        "Deposits": _p("Deposits") or _p("Total Deposits"),
    }
    # Derive prev CA/NCA from sub-items when reported as 0 (financial companies)
    if prev_map.get("Current Assets", 0) == 0:
        _pca = sum(prev_map.get(k, 0) for k in ["Cash", "ST Investments", "Receivables", "Inventory"])
        if _pca > 0:
            prev_map["Current Assets"] = _pca
    if prev_map.get("Non-Current Assets", 0) == 0:
        _pnca = sum(prev_map.get(k, 0) for k in ["PP&E", "Goodwill", "Intangibles", "Investments"])
        if _pnca > 0:
            prev_map["Non-Current Assets"] = _pnca
    if prev_map.get("Non-Current Liab.", 0) == 0 and prev_map.get("Total Liabilities", 0) > 0:
        _pcl = prev_map.get("Current Liab.", 0)
        _pncl = prev_map["Total Liabilities"] - _pcl
        if _pncl > 0:
            prev_map["Non-Current Liab."] = _pncl
    # Compute residual "Other" prev values
    _kca = sum(prev_map.get(k, 0) for k in ["Cash", "ST Investments", "Receivables", "Inventory"])
    prev_map["Other Current"] = max(0, prev_map.get("Current Assets", 0) - _kca)
    _knca = sum(prev_map.get(k, 0) for k in ["PP&E", "Goodwill", "Intangibles", "Investments"])
    prev_map["Other Non-Current"] = max(0, prev_map.get("Non-Current Assets", 0) - _knca)
    _kcl = sum(prev_map.get(k, 0) for k in ["Accounts Payable", "Short-Term Debt", "Deferred Revenue"])
    prev_map["Other CL"] = max(0, prev_map.get("Current Liab.", 0) - _kcl)
    prev_map["Other LT Liab."] = max(0, prev_map.get("Non-Current Liab.", 0) - prev_map.get("Long-Term Debt", 0) - prev_map.get("Deposits", 0))
    prev_map["Other Equity"] = max(0, prev_map.get("Equity", 0) - prev_map.get("Retained Earnings", 0))
    prev_map["Total Equity"] = prev_map.get("Equity", 0)

    if total_assets == 0:
        return None, []

    # Reconcile: Assets = CA + NCA
    if noncurrent_assets == 0 and total_assets > 0 and current_assets > 0:
        noncurrent_assets = total_assets - current_assets
    if current_assets == 0 and total_assets > 0 and noncurrent_assets > 0:
        current_assets = total_assets - noncurrent_assets
    if current_assets + noncurrent_assets != total_assets and current_assets > 0:
        noncurrent_assets = total_assets - current_assets

    # Reconcile: Assets = Liab + Equity
    if total_liab == 0 and equity > 0:
        total_liab = total_assets - equity
    if equity == 0 and total_liab > 0:
        equity = total_assets - total_liab
    if total_liab == 0 and equity == 0:
        total_liab = current_liab + noncurrent_liab
        if total_liab > 0:
            equity = total_assets - total_liab
        else:
            equity = total_assets
    if total_liab + equity != total_assets:
        equity = total_assets - total_liab
        if equity < 0:
            equity = 0
            total_liab = total_assets

    # Reconcile: Liab = CL + NCL
    if noncurrent_liab == 0 and total_liab > 0 and current_liab > 0:
        noncurrent_liab = total_liab - current_liab
    if current_liab == 0 and total_liab > 0 and noncurrent_liab > 0:
        current_liab = total_liab - noncurrent_liab
    if current_liab + noncurrent_liab != total_liab and total_liab > 0:
        noncurrent_liab = total_liab - current_liab
        if noncurrent_liab < 0:
            noncurrent_liab = 0
            current_liab = total_liab

    C = BS_COLORS
    nodes, node_colors_list, node_x, node_y = [], [], [], []
    node_val_raw = []  # raw numeric value (for bar height calculation)
    node_name_list, node_val_str, node_row2 = [], [], []
    links_src, links_tgt, links_val, links_col = [], [], [], []
    imap = {}

    def add(name, val, color, x, y, expandable=False):
        y = round(max(0.01, min(0.99, y)), 4)
        x = round(max(0.01, min(0.99, x)), 4)
        imap[name] = len(nodes)
        display_name = name
        pv = prev_map.get(name, 0)
        pct = _yoy(val, pv)
        delta_str = _fmt_delta(val, pv)
        pct_suffix = ""
        if pct is not None:
            diff = val - pv
            arrow = "\u2191" if diff >= 0 else "\u2193"
            pct_suffix = f"  {arrow}{pct:+.1f}%"
            if delta_str:
                pct_suffix += f" {delta_str}"
        elif delta_str:
            diff = val - pv
            arrow = "\u2191" if diff >= 0 else "\u2193"
            pct_suffix = f"  {arrow}{delta_str}"
        nodes.append(f"{display_name}  {_fmt(val)}{pct_suffix}")
        node_name_list.append(display_name)
        node_val_str.append(_fmt(val))
        node_row2.append(pct_suffix.strip() if pct_suffix.strip() else "")
        node_val_raw.append(max(val, 0))
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

    ca_items = []
    if cash > 0: ca_items.append(("Cash", cash, C["cash"]))
    if short_invest > 0: ca_items.append(("ST Investments", short_invest, C["invest"]))
    if receivables > 0: ca_items.append(("Receivables", receivables, C["asset"]))
    if inventory > 0: ca_items.append(("Inventory", inventory, C["asset"]))
    known_ca = cash + short_invest + receivables + inventory
    other_ca = max(0, current_assets - known_ca)
    if other_ca > 0: ca_items.append(("Other Current", other_ca, C["other"]))

    nca_items = []
    if ppe > 0: nca_items.append(("PP&E", ppe, C["asset2"]))
    if goodwill > 0: nca_items.append(("Goodwill", goodwill, C["asset2"]))
    if intangibles > 0: nca_items.append(("Intangibles", intangibles, C["asset2"]))
    if investments > 0: nca_items.append(("Investments", investments, C["invest"]))
    known_nca = ppe + goodwill + intangibles + investments
    other_nca = max(0, noncurrent_assets - known_nca)
    if other_nca > 0: nca_items.append(("Other Non-Current", other_nca, C["other"]))

    cl_items = []
    if accounts_payable > 0: cl_items.append(("Accounts Payable", accounts_payable, C["payable"]))
    if short_debt > 0: cl_items.append(("Short-Term Debt", short_debt, C["debt"]))
    if deferred_rev > 0: cl_items.append(("Deferred Revenue", deferred_rev, C["liability"]))
    known_cl = accounts_payable + short_debt + deferred_rev
    other_cl_val = max(0, current_liab - known_cl)
    if other_cl_val > 0: cl_items.append(("Other CL", other_cl_val, C["other"]))

    ncl_items = []
    if long_debt > 0: ncl_items.append(("Long-Term Debt", long_debt, C["debt"]))
    # Financial companies: show Deposits as a named item instead of all in "Other LT Liab."
    _ncl_known = long_debt
    if deposits > 0:
        ncl_items.append(("Deposits", deposits, C["liability"]))
        _ncl_known += deposits
    other_ncl = max(0, noncurrent_liab - _ncl_known)
    if other_ncl > 0: ncl_items.append(("Other LT Liab.", other_ncl, C["other"]))

    eq_items = []
    if equity > 0:
        if "Equity" in expanded_nodes and ticker:
            # Fetch expanded sub-breakdown from EDGAR
            _eq_sub = _fetch_sub_values(ticker, EXPANDABLE_BALANCE_NODES["Equity"]["children"])
            if _eq_sub:
                _eq_children = []
                for ch in EXPANDABLE_BALANCE_NODES["Equity"]["children"]:
                    ch_val = _eq_sub.get(ch["label"], 0)
                    if ch_val > 0:
                        _eq_children.append((ch["label"], ch_val, ch.get("color", C["equity"])))
                ch_sum = sum(v for _, v, _ in _eq_children)
                if ch_sum > 0 and _eq_children:
                    scale = equity / ch_sum
                    _eq_children = [(l, round(v * scale), c) for l, v, c in _eq_children]
                    eq_items = _eq_children
                else:
                    # Fallback to default
                    if retained and retained > 0:
                        re_show = min(retained, equity)
                        eq_items.append(("Retained Earnings", re_show, C["retained"]))
                        other_eq = max(0, equity - re_show)
                        if other_eq > 0: eq_items.append(("Other Equity", other_eq, C["other"]))
                    else:
                        eq_items.append(("Total Equity", equity, C["equity"]))
            else:
                if retained and retained > 0:
                    re_show = min(retained, equity)
                    eq_items.append(("Retained Earnings", re_show, C["retained"]))
                    other_eq = max(0, equity - re_show)
                    if other_eq > 0: eq_items.append(("Other Equity", other_eq, C["other"]))
                else:
                    eq_items.append(("Total Equity", equity, C["equity"]))
        elif retained and retained > 0:
            re_show = min(retained, equity)
            eq_items.append(("Retained Earnings", re_show, C["retained"]))
            other_eq = max(0, equity - re_show)
            if other_eq > 0: eq_items.append(("Other Equity", other_eq, C["other"]))
        else:
            eq_items.append(("Total Equity", equity, C["equity"]))

    # Wide X spacing — text is placed via annotations (not built-in labels)
    # Col1/Col2 use 2-row labels (shorter) so can be closer together
    X1, X2, X3, X4 = 0.01, 0.16, 0.38, 0.62

    # ── Band-confined proportional Y-positioning (same as income Sankey) ──
    Y_MIN, Y_MAX = 0.04, 0.96

    # ── Build the LEFT side (Assets) and RIGHT side (Liab + Equity) ──
    # Column 1: Total Assets (full band)
    # Column 2: CA + NCA  (split Total Assets band) — OR — Liab + Equity
    # Column 3: sub-items of CA/NCA — OR — CL + NCL sub-items
    #
    # For the balance sheet we use a TWO-SIDED layout:
    #   Left:  Total Assets → [CA, NCA] → sub-items
    #   Right: Total Assets → [Liab, Equity] → sub-items
    #
    # But since Sankey is a single directed graph, we model it as:
    #   Col1: Total Assets
    #   Col2: CA, NCA, Liab, Equity  (intermediate nodes)
    #   Col3: sub-items of CA/NCA + CL/NCL intermediate
    #   Col4: sub-items of CL/NCL + equity sub-items

    # ── Determine which col2 nodes exist (skip $0 parents with no items) ──
    col2_items = []  # (name, value, color, children_items, col3_or_col4, expandable)

    # Assets side
    has_ca = current_assets > 0 and ca_items
    has_nca = noncurrent_assets > 0 and nca_items
    # For financial companies where CA/NCA = 0 but sub-items exist,
    # derive the parent value from sub-items
    if not has_ca and ca_items:
        current_assets = sum(v for _, v, _ in ca_items)
        if current_assets > 0:
            has_ca = True
    if not has_nca and nca_items:
        noncurrent_assets = sum(v for _, v, _ in nca_items)
        if noncurrent_assets > 0:
            has_nca = True

    if has_ca:
        col2_items.append(("Current Assets", current_assets, C["asset"], ca_items, X3, False))
    if has_nca:
        col2_items.append(("Non-Current Assets", noncurrent_assets, C["asset2"], nca_items, X3, False))

    # Liabilities side
    has_liab = total_liab > 0
    if has_liab:
        # Liab has intermediate CL/NCL nodes at col3, then sub-items at col4
        liab_children = []  # intermediate nodes for col3
        if current_liab > 0 and cl_items:
            liab_children.append(("Current Liab.", current_liab, C["liability"], cl_items))
        if noncurrent_liab > 0 and ncl_items:
            liab_children.append(("Non-Current Liab.", noncurrent_liab, C["liability"], ncl_items))
        # If no CL/NCL breakdown, put "Other LT Liab." as direct child
        if not liab_children:
            _direct_liab_items = cl_items + ncl_items
            if not _direct_liab_items:
                _direct_liab_items = [("Other LT Liab.", total_liab, C["other"])]
            col2_items.append(("Total Liabilities", total_liab, C["liability"], _direct_liab_items, X3, False))
        else:
            col2_items.append(("Total Liabilities", total_liab, C["liability"], liab_children, X3, False))

    # Equity
    if equity > 0 and eq_items:
        col2_items.append(("Equity", equity, C["equity"], eq_items, X3, True))

    if not col2_items:
        return None, []

    # ── Count nodes per sub-band for dynamic chart height ──────────────
    # Balance sheet nodes are confined within sub-bands (CA items within CA band,
    # etc.), so we compute "effective full-chart density" per sub-band:
    #   effective_n = n_items / band_fraction
    # where band_fraction = parent_value / total_assets.
    # The chart must be tall enough for the densest sub-band.
    _bs_c2_n = len(col2_items)
    _bs_total_val = sum(item[1] for item in col2_items) or 1
    _effective_counts = [_bs_c2_n]  # col2 spans full band

    for _, val, _, children, _, _ in col2_items:
        band_frac = max(val / _bs_total_val, 0.05)  # floor at 5%
        has_nested = any(len(ch) == 4 for ch in children)
        if has_nested:
            # Liabilities: intermediate CL/NCL at col3, sub-items at col4
            n_col3 = len(children)
            _effective_counts.append(n_col3 / band_frac)
            for ch in children:
                if len(ch) == 4:
                    ch_val = ch[1]
                    ch_frac = max(ch_val / _bs_total_val, 0.03)
                    _effective_counts.append(len(ch[3]) / ch_frac)
        else:
            n_children = len(children)
            _effective_counts.append(n_children / band_frac)

    _bs_n_nodes_est = 1 + sum(
        len(ch) if not any(len(c) == 4 for c in ch)
        else len(ch) + sum(len(c[3]) for c in ch if len(c) == 4)
        for _, _, _, ch, _, _ in col2_items
    ) + _bs_c2_n
    _bs_font_sz_est = 11 if _bs_n_nodes_est <= 12 else (10 if _bs_n_nodes_est <= 16 else 9)

    # Use the worst effective density (rounded up) for chart height
    _worst_effective = max(int(c + 0.99) for c in _effective_counts) if _effective_counts else 4
    _h = _compute_dynamic_height([_worst_effective], _bs_font_sz_est)
    _bs_min_text_band = _min_band_for_text(_bs_font_sz_est, _h, has_row2=True)

    def _split_band_bs(values, band_top, band_bot):
        """Split a vertical band into sub-bands proportional to values.

        Each child's band height = max(proportional_height, _bs_min_text_band)
        so that the 3-row text label always fits within the node's allocated slot.
        When the parent band is too small for all children at minimum text height,
        items overflow the parent band (centered) rather than compressing and overlapping.
        """
        n = len(values)
        if n == 0:
            return []
        span = band_bot - band_top
        if n == 1:
            cy = (band_top + band_bot) / 2
            return [(cy, band_top, band_bot)]
        total = sum(values)
        if total <= 0:
            step = max(span / n, _bs_min_text_band)
            needed = step * n
            start = band_top + (span - needed) / 2
            start = max(Y_MIN, min(start, Y_MAX - needed))
            return [(round(max(Y_MIN, min(Y_MAX, start + step * (i + 0.5))), 4),
                     round(max(Y_MIN, start + step * i), 4),
                     round(min(Y_MAX, start + step * (i + 1)), 4)) for i in range(n)]

        # Compute proportional sub-bands, enforcing text-height minimum
        results = []
        cursor = band_top
        for v in values:
            raw_band = (v / total) * span
            band_h = max(raw_band, _bs_min_text_band)
            results.append((cursor, band_h))
            cursor += band_h

        # Rescale if we overflowed
        actual_span = sum(h for _, h in results)
        if actual_span > span + 0.001:
            needed_at_min = n * _bs_min_text_band
            if needed_at_min <= span:
                # Band can fit all items at minimum — scale only excess above minimums
                excess_total = sum(max(0, h - _bs_min_text_band) for _, h in results)
                target_excess = span - needed_at_min
                if excess_total > 0:
                    scale = target_excess / excess_total
                    results2, cursor = [], band_top
                    for _, h in results:
                        above = max(0, h - _bs_min_text_band)
                        h2 = _bs_min_text_band + above * scale
                        results2.append((cursor, h2))
                        cursor += h2
                    results = results2
                else:
                    step = span / n
                    results = [(band_top + step * i, step) for i in range(n)]
            else:
                # Band too small — overflow centered, each item gets _bs_min_text_band
                mid = (band_top + band_bot) / 2
                start = mid - needed_at_min / 2
                start = max(Y_MIN, min(start, Y_MAX - needed_at_min))
                results = [(start + _bs_min_text_band * i, _bs_min_text_band) for i in range(n)]

        # Build (centre, top, bot) tuples
        out = []
        for top_y, h in results:
            bot_y = top_y + h
            centre = top_y + h / 2
            out.append((round(max(Y_MIN, min(Y_MAX, centre)), 4),
                         round(max(Y_MIN, top_y), 4),
                         round(min(Y_MAX, bot_y), 4)))
        return out

    # ── Column 1: Total Assets → full band ──
    ta_band = (Y_MIN, Y_MAX)
    ta_y = (Y_MIN + Y_MAX) / 2
    add("Total Assets", total_assets, C["asset"], X1, ta_y)

    # ── Column 2: split Total Assets band among col2 items ──
    c2_vals = [item[1] for item in col2_items]
    c2 = _split_band_bs(c2_vals, *ta_band)

    for i, (name, val, color, children, x_children, expandable) in enumerate(col2_items):
        c2_y, c2_band_top, c2_band_bot = c2[i]
        add(name, val, color, X2, c2_y, expandable=expandable)
        link("Total Assets", name, val, color)

        # ── Column 3: split this col2 node's band among its children ──
        # Check if children have nested sub-items (liabilities CL/NCL case)
        has_nested = any(len(ch) == 4 for ch in children)

        if has_nested:
            # Liabilities: children are (name, val, color, sub_items) — intermediate col3 nodes
            c3_vals = [ch[1] for ch in children]
            c3 = _split_band_bs(c3_vals, c2_band_top, c2_band_bot)
            for j, (ch_name, ch_val, ch_color, sub_items) in enumerate(children):
                c3_y, c3_band_top, c3_band_bot = c3[j]
                add(ch_name, ch_val, ch_color, X3, c3_y)
                link(name, ch_name, ch_val, ch_color)
                # Column 4: sub-items of CL/NCL
                c4_vals = [si[1] for si in sub_items]
                c4 = _split_band_bs(c4_vals, c3_band_top, c3_band_bot)
                for k, (si_name, si_val, si_color) in enumerate(sub_items):
                    add(si_name, si_val, si_color, X4, c4[k][0])
                    link(ch_name, si_name, si_val, si_color)
        else:
            # Direct children: (name, val, color)
            c3_vals = [ch[1] for ch in children]
            c3 = _split_band_bs(c3_vals, c2_band_top, c2_band_bot)
            for j, (ch_name, ch_val, ch_color) in enumerate(children):
                add(ch_name, ch_val, ch_color, x_children, c3[j][0])
                link(name, ch_name, ch_val, ch_color)

    if not links_val:
        return None, []

    _n_nodes = len(nodes)
    # Scale node padding & thickness to fit within dynamic _h height
    _pad = max(8, min(22, int(320 / max(_n_nodes, 1))))
    _thickness = max(10, min(18, int(200 / max(_n_nodes, 1))))
    _font_sz = 11 if _n_nodes <= 12 else (10 if _n_nodes <= 16 else 9)

    # ── Fix gaps: bars → text → cross-column → re-fix vertical ──────────
    # Use min_gap_px=6 so the bottom of each node has a visible gap to the
    # next node (user rule: "bottom of a node must have a gap to the next").
    _fix_bar_gaps(node_x, node_y, node_val_raw, _h, min_gap_px=6)
    _fix_text_gaps(node_x, node_y, node_row2, _font_sz, _h, min_gap_px=6)
    _fix_cross_column_text(node_x, node_y, node_val_raw, node_name_list,
                           node_val_str, node_row2, _font_sz, _h, _thickness,
                           min_gap_px=6)
    _fix_bar_gaps(node_x, node_y, node_val_raw, _h, min_gap_px=6)
    _fix_text_gaps(node_x, node_y, node_row2, _font_sz, _h, min_gap_px=6)

    # Hide built-in node labels — we use annotations instead so text
    # renders ON TOP of all nodes (separate SVG layer).
    _empty_labels = [""] * len(nodes)
    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        orientation="h",
        textfont=dict(size=1, color="rgba(0,0,0,0)"),
        node=dict(pad=_pad, thickness=_thickness, line=dict(color="rgba(0,0,0,0)", width=0),
                  label=_empty_labels, color=node_colors_list, x=node_x, y=node_y,
                  customdata=nodes,
                  hovertemplate="<b>%{customdata}</b><extra></extra>"),
        link=dict(source=links_src, target=links_tgt, value=links_val, color=links_col,
                  hovertemplate="Flow: %{value:$,.0f}<extra></extra>"),
        domain=dict(y=[0.04, 0.96]),
    ))
    # _h already computed dynamically above (via _compute_dynamic_height)
    _layout = dict(height=_h, margin=dict(l=6, r=6, t=20, b=6),
                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                   font=dict(size=_font_sz, family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif", color="#1e293b"))
    fig.update_layout(**_layout)

    # ── Annotation-based labels (render above all nodes) ──────────────
    _dom_y0, _dom_y1 = 0.04, 0.96
    _small_sz = max(8, _font_sz - 2)
    for i in range(len(nodes)):
        x_paper = node_x[i]
        y_paper = _dom_y0 + (_dom_y1 - _dom_y0) * (1.0 - node_y[i])
        r2 = node_row2[i]
        if r2:
            # Color row 3: green for ↑, red for ↓, gray if zero/no arrow
            if "\u2191" in r2:
                _r2_color = "#16a34a"
            elif "\u2193" in r2:
                _r2_color = "#dc2626"
            else:
                _r2_color = "#64748b"
            txt = (f"{node_name_list[i]}<br>"
                   f"{node_val_str[i]}<br>"
                   f"<span style='font-size:{_small_sz}px;color:{_r2_color}'>{r2}</span>")
        else:
            txt = (f"{node_name_list[i]}<br>"
                   f"{node_val_str[i]}")
        fig.add_annotation(
            x=x_paper, y=y_paper,
            xref="paper", yref="paper",
            text=txt,
            showarrow=False,
            align="left",
            xanchor="left",
            yanchor="middle",
            xshift=_thickness // 2 + 1,
            font=dict(size=_font_sz,
                      family="Inter, -apple-system, Helvetica Neue, Arial, sans-serif",
                      color="#1e293b"),
        )
    # Return fig + list of node names that exist in the Sankey
    _actual_nodes = [n for n in node_name_list if n in BALANCE_NODE_METRICS]
    return fig, _actual_nodes


def render_sankey_page():
    """Render the Sankey diagram page."""
    ticker = st.session_state.get("ticker", "AAPL")

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        .sankey-header {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        .sankey-header-left {
            flex: 1;
        }
        .sankey-title {
            font-size: 1.15rem;
            font-weight: 600;
            color: #f8fafc;
            margin-bottom: 0 !important;
            letter-spacing: -0.02em;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 10px;
        }
        .sankey-compare-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: linear-gradient(135deg, rgba(30,41,59,0.95), rgba(15,23,42,0.95));
            border: 1px solid rgba(59,130,246,0.3);
            color: #93c5fd;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.95rem;
            font-weight: 600;
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
        /* ââ Sankey header row: title + PDF download button ââ */
        /* Target the stHorizontalBlock that contains the PDF download key */
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]),
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            padding: 12px 4px !important;
            gap: 0 !important;
            align-items: center !important;
            justify-content: center !important;
            margin-top: 23px !important;
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
            margin: 0 !important;
            padding: 0 !important;
        }
        /* Kill all inner margins so title stays vertically centered */
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]) [data-testid="stColumn"] [data-testid="stMarkdownContainer"],
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) [data-testid="stColumn"] [data-testid="stMarkdownContainer"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]) [data-testid="stColumn"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) [data-testid="stColumn"] [data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
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
            margin-top: 1.5rem;
            margin-bottom: 2rem;
            justify-content: center;
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
            background: #ffffff;
            border-radius: 14px;
            padding: 18px 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);
            transition: box-shadow 0.2s ease, transform 0.2s ease;
        }
        div[data-testid="metric-container"]:hover {
            box-shadow: 0 2px 6px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06);
            transform: translateY(-1px);
        }
        /* ── Compare badge card ── */
        .sankey-compare-card {
            text-align: center;
            margin: 0.75rem auto 1.5rem;
        }
        /* ── KPI row card wrapper ── */
        .sankey-kpi-card {
            background: #ffffff;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05), 0 6px 20px rgba(0,0,0,0.04);
            padding: 24px 20px 20px;
            margin-bottom: 1.5rem;
        }
        /* ── Instruction CTA banner ── */
        .sankey-cta-banner {
            display: flex;
            align-items: center;
            gap: 12px;
            background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 50%, #dbeafe 100%);
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 14px;
            padding: 16px 22px;
            margin: 0 0 1.75rem;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1), 0 0 0 1px rgba(99, 102, 241, 0.05);
            transition: box-shadow 0.25s ease;
        }
        .sankey-cta-banner:hover {
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.18), 0 0 0 1px rgba(99, 102, 241, 0.12);
        }
        .sankey-cta-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #6366f1, #818cf8);
            border-radius: 10px;
            flex-shrink: 0;
        }
        .sankey-cta-text {
            font-size: 0.9rem;
            font-weight: 600;
            color: #312e81;
            letter-spacing: 0.01em;
        }
        .sankey-cta-sub {
            font-size: 0.76rem;
            color: #6366f1;
            font-weight: 500;
            margin-top: 2px;
        }
        /* ── Sankey container: no scroll, clip overflow ── */
        [class*="st-key-sankey_income_scroll"],
        [class*="st-key-sankey_balance_scroll"] {
            overflow: hidden;
            border-radius: 8px;
            position: relative;
            z-index: 1;
            contain: paint;
            clip-path: inset(0 0 0 0);
            -webkit-clip-path: inset(0 0 0 0);
            isolation: isolate;
        }
        [class*="st-key-sankey_income_scroll"] [data-testid="stPlotlyChart"],
        [class*="st-key-sankey_balance_scroll"] [data-testid="stPlotlyChart"] {
            overflow: hidden !important;
            margin-top: 0 !important;
        }
        [class*="st-key-sankey_income_scroll"] iframe,
        [class*="st-key-sankey_balance_scroll"] iframe {
            overflow: hidden !important;
            margin-top: 0 !important;
        }
        [class*="st-key-sankey_income_scroll"] [data-testid="stPlotlyChart"] > div,
        [class*="st-key-sankey_balance_scroll"] [data-testid="stPlotlyChart"] > div {
            overflow: hidden !important;
            margin-top: 0 !important;
        }
        [class*="st-key-sankey_income_scroll"] .js-plotly-plot,
        [class*="st-key-sankey_balance_scroll"] .js-plotly-plot {
            overflow: hidden !important;
        }
        [class*="st-key-sankey_income_scroll"] .plot-container,
        [class*="st-key-sankey_balance_scroll"] .plot-container {
            overflow: hidden !important;
        }
        [class*="st-key-sankey_income_scroll"] .svg-container,
        [class*="st-key-sankey_balance_scroll"] .svg-container {
            overflow: hidden !important;
        }

        /* ── Pills card wrapper ── */
        .sankey-pills-card {
            background: #ffffff;
            border-radius: 14px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05), 0 4px 14px rgba(0,0,0,0.03);
            padding: 16px 18px;
            margin-bottom: 1.5rem;
            position: relative;
            z-index: 10;
        }
        /* ── Sankey chart card ── */
        .sankey-chart-card {
            background: #ffffff;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05), 0 6px 20px rgba(0,0,0,0.04);
            padding: 8px 4px;
            margin-bottom: 1rem;
        }
        .sankey-legend {
            display: flex;
            gap: 28px;
            margin-top: 12px;
            padding: 12px 16px;
            background: #f8fafc;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            font-size: 0.85rem;
            color: #475569;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
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

        /* ââ Sankey Responsive ââ */
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
                padding: 12px 14px !important;
            }
            .sankey-cta-banner {
                padding: 12px 16px !important;
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
                justify-content: center !important;
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
        /* ── Metric filter pills: compact + transition (JS applies per-node colors on hover) ── */
        [data-testid="stBaseButton-pills"] {
            font-size: 0.78rem !important;
            padding: 4px 10px !important;
            transition: background 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease, color 0.25s ease, transform 0.15s ease !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Fetch data
    using_demo = False
    _match_qs = st.session_state.get("_sankey_annual_match_qs", [1, 2, 3, 4])
    _match_q = st.session_state.get("_sankey_annual_match_q", 4)  # backward compat
    _sq = st.session_state.get("sankey_compare_quarterly", False)
    _pa = st.session_state.get("sankey_period_a", None)
    _pb = st.session_state.get("sankey_period_b", None)

    # Determine if we need partial-year aggregation:
    # Full year only when all 4 Qs of current year selected AND no previous-year Qs
    _qa_qs_check = st.session_state.get("_sankey_qa_nums", [])
    _qb_qs_check = st.session_state.get("_sankey_qb_nums", [])
    _is_full_year = (sorted(_qa_qs_check) == [1, 2, 3, 4] and not _qb_qs_check)
    # Always use partial-year aggregation when quarters are selected,
    # even full-year — we need quarterly data for the audit breakdown table.
    _partial_year = (not _sq) and _pa and _pb

    with st.spinner(f"Loading {ticker} financial data..."):
        try:
            if _partial_year:
                # Fetch quarterly data to aggregate selected quarters
                income_df, balance_df, info = _fetch_sankey_data(ticker, quarterly=True)
            else:
                income_df, balance_df, info = _fetch_sankey_data(ticker, quarterly=_sq)
        except Exception:
            income_df, balance_df, info = pd.DataFrame(), pd.DataFrame(), {"shortName": ticker}

    # If data is empty (rate-limited), fall back to demo data
    if income_df.empty and balance_df.empty:
        income_df, balance_df, info = _get_demo_data(ticker)
        using_demo = True
        st.info(f"\U0001F4C8 Showing sample data for **{ticker.upper()}** \u2013 SEC EDGAR data is temporarily unavailable. Refresh in a minute for live data.")

    # --- Partial-year aggregation (Annual mode with selected quarters) ---
    _raw_qtr_income_df = None  # For audit panel: per-quarter breakdown
    _raw_qtr_balance_df = None
    if _partial_year and not using_demo:
        _fy_end = st.session_state.get("_fy_end_month", 12)
        _qa_nums_agg = st.session_state.get("_sankey_qa_nums", _match_qs)
        _qb_nums_agg = st.session_state.get("_sankey_qb_nums", [])
        try:
            _fy_a = int(_pa)
            _fy_b = int(_pb)
            # No bump needed: _aggregate_multi_year already maps
            # cur_qs (sk_Ya) → main_fy and prev_qs (sk_Yb) → main_fy-1.
            # Period A=2026 + sk_Yb_q4 → main_fy-1 = 2025 Q4 ✓
            _raw_qtr_income_df = income_df.copy() if income_df is not None else None
            _raw_qtr_balance_df = balance_df.copy() if balance_df is not None else None

            # ── Track & add derived income rows for audit panel ──
            _derived_income_rows = {}  # row_name → footnote text
            if _raw_qtr_income_df is not None and not _raw_qtr_income_df.empty:
                _ri = _raw_qtr_income_df
                # Gross Profit derivation
                if "Gross Profit" not in _ri.index:
                    if "Total Revenue" in _ri.index and "Cost Of Revenue" in _ri.index:
                        _ri.loc["Gross Profit"] = _ri.loc["Total Revenue"] - _ri.loc["Cost Of Revenue"].abs()
                        _derived_income_rows["Gross Profit"] = "Revenue − Cost of Revenue"
                # Operating Income derivation
                if "Operating Income" not in _ri.index:
                    _gp = _ri.loc["Gross Profit"] if "Gross Profit" in _ri.index else 0
                    _rd = _ri.loc["Research And Development"].abs() if "Research And Development" in _ri.index else 0
                    _sg = _ri.loc["Selling General And Administration"].abs() if "Selling General And Administration" in _ri.index else 0
                    _da = _ri.loc["Reconciled Depreciation"].abs() if "Reconciled Depreciation" in _ri.index else 0
                    _oe = _ri.loc["Other Operating Expenses"].abs() if "Other Operating Expenses" in _ri.index else 0
                    if isinstance(_gp, pd.Series):
                        _ri.loc["Operating Income"] = _gp - _rd - _sg - _da - _oe
                        _derived_income_rows["Operating Income"] = "Gross Profit − R&D − SG&A − D&A − Other OpEx"
                # Pretax Income derivation
                if "Pretax Income" not in _ri.index:
                    if "Operating Income" in _ri.index and "Interest Expense" in _ri.index:
                        _ri.loc["Pretax Income"] = _ri.loc["Operating Income"] - _ri.loc["Interest Expense"].abs()
                        _derived_income_rows["Pretax Income"] = "Operating Income − Interest Expense"
                # Net Income derivation
                if "Net Income" not in _ri.index:
                    if "Pretax Income" in _ri.index and "Tax Provision" in _ri.index:
                        _ri.loc["Net Income"] = _ri.loc["Pretax Income"] - _ri.loc["Tax Provision"].abs()
                        _derived_income_rows["Net Income"] = "Pretax Income − Tax Provision"
            st.session_state["_derived_income_rows"] = _derived_income_rows

            # ── Track derived balance sheet rows ──
            _derived_balance_rows = {}
            if _raw_qtr_balance_df is not None and not _raw_qtr_balance_df.empty:
                _bs_derived_set = getattr(_raw_qtr_balance_df, "attrs", {}).get("_derived_rows", set())
                if "Total Non Current Assets" in _bs_derived_set:
                    _derived_balance_rows["Total Non Current Assets"] = "Total Assets − Current Assets"
                if "Total Non Current Liabilities Net Minority Interest" in _bs_derived_set:
                    _derived_balance_rows["Total Non Current Liabilities Net Minority Interest"] = "Total Liabilities − Current Liabilities"
            st.session_state["_derived_balance_rows"] = _derived_balance_rows
            income_df = _build_partial_year_df(
                income_df, _fy_a, _fy_b, _match_qs, _fy_end,
                is_balance_sheet=False,
                qa_nums=_qa_nums_agg, qb_nums=_qb_nums_agg,
            )
            balance_df = _build_partial_year_df(
                balance_df, _fy_a, _fy_b, _match_qs, _fy_end,
                is_balance_sheet=True,
                qa_nums=_qa_nums_agg, qb_nums=_qb_nums_agg,
            )
        except Exception as _agg_exc:
            import traceback as _tb
            _agg_tb = _tb.format_exc()
            st.session_state["_partial_agg_error"] = f"{_agg_exc}: {_agg_tb}"
            # ── CRITICAL: do NOT silently fall back to raw quarterly data ──
            # Raw quarterly DF has many columns; _safe/_safe_prev would read
            # col 0 and col 1 (two DIFFERENT quarters), producing WRONG deltas.
            # Instead, create a proper empty 2-column DF so deltas show as N/A.
            _empty_idx = income_df.index if income_df is not None and not income_df.empty else []
            income_df = pd.DataFrame({"Period_A": pd.Series(dtype=float, index=_empty_idx),
                                       "Period_B": pd.Series(dtype=float, index=_empty_idx)})
            balance_df = pd.DataFrame({"Period_A": pd.Series(dtype=float, index=_empty_idx),
                                        "Period_B": pd.Series(dtype=float, index=_empty_idx)})

    # --- Handle missing period data after aggregation ---
    # When Period A data hasn't been filed yet (all NaN), we need to handle it
    # intelligently instead of showing $0 with -100% deltas.
    _period_a_missing = False
    _period_b_missing = False
    _swapped_periods = False
    if _partial_year and not using_demo:
        _agg_dbg = st.session_state.get("_agg_debug", {})
        _period_a_missing = not _agg_dbg.get("ser_a_found", True)
        _period_b_missing = not _agg_dbg.get("ser_b_found", True)

        # --- Helper: search backwards for closest FY with data ---
        def _find_closest_available_fy(raw_df, start_fy, quarter_list, fy_end, is_bs):
            """Try FY start_fy-1, start_fy-2, … down to start_fy-10.
            Returns (Series, timestamp, found_fy) or (None, None, None)."""
            for try_fy in range(start_fy - 1, start_fy - 11, -1):
                ser, ts = _aggregate_partial_year(raw_df, try_fy, quarter_list, fy_end, is_bs)
                if ser is not None:
                    return ser, ts, try_fy
            return None, None, None

        _MON_S = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        def _build_month_label(qs, fy, fy_end):
            """Build e.g. '(Oct 25 · Nov 25 · Dec 25)' for given quarters."""
            parts = []
            for q in sorted(qs):
                try:
                    em = _fq_end_month_s(q, fy_end)
                    ey = _fq_end_year_s(q, fy, fy_end)
                    parts.append(f"{_MON_S[em]} {ey % 100:02d}")
                except Exception:
                    pass
            return " (" + " · ".join(parts) + ")" if parts else ""

        if _period_a_missing:
            # Use whichever quarters are selected (sk_Ya or sk_Yb)
            _fb_qa = st.session_state.get("_sankey_qa_nums", [])
            _fb_qb = st.session_state.get("_sankey_qb_nums", [])
            _fb_qs = sorted(_fb_qa or _fb_qb or [1])
            _qs_tag = "+".join(f"Q{q}" for q in _fb_qs)
            _fy_end_m = st.session_state.get("_fy_end_month", 12)
            _pa_int = int(_pa) if _pa else 2026

            # Search backwards from FY(A) for closest available data
            _fb_inc_ser, _fb_inc_ts, _fb_fy_inc = None, None, None
            _fb_bal_ser, _fb_bal_ts, _fb_fy_bal = None, None, None
            if _raw_qtr_income_df is not None and not _raw_qtr_income_df.empty:
                _fb_inc_ser, _fb_inc_ts, _fb_fy_inc = _find_closest_available_fy(
                    _raw_qtr_income_df, _pa_int, _fb_qs, _fy_end_m, False)
            if _raw_qtr_balance_df is not None and not _raw_qtr_balance_df.empty:
                _fb_bal_ser, _fb_bal_ts, _fb_fy_bal = _find_closest_available_fy(
                    _raw_qtr_balance_df, _pa_int, _fb_qs, _fy_end_m, True)

            _fb_fy = _fb_fy_inc or _fb_fy_bal  # whichever was found

            if _fb_fy is not None:
                # Found closest available — replace ONLY Period A.
                # Period B keeps the user's selected comparison year.
                if _fb_inc_ser is not None:
                    _existing_b_inc = income_df["Period_B"].copy() if (income_df is not None and "Period_B" in income_df.columns) else pd.Series(dtype=float)
                    income_df = pd.DataFrame({"Period_A": _fb_inc_ser})
                    income_df["Period_B"] = _existing_b_inc
                    _swapped_periods = True
                elif income_df is not None:
                    income_df["Period_A"] = np.nan
                if _fb_bal_ser is not None:
                    _existing_b_bal = balance_df["Period_B"].copy() if (balance_df is not None and "Period_B" in balance_df.columns) else pd.Series(dtype=float)
                    balance_df = pd.DataFrame({"Period_A": _fb_bal_ser})
                    balance_df["Period_B"] = _existing_b_bal
                elif balance_df is not None:
                    balance_df["Period_A"] = np.nan
                _fb_months = _build_month_label(_fb_qs, _fb_fy, _fy_end_m)
                st.warning(f"⚠️ {_qs_tag} FY{_pa} data not yet filed in SEC EDGAR. "
                           f"Falling back to closest available: {_qs_tag} FY{_fb_fy}{_fb_months}.")
                st.session_state["_fallback_fy"] = _fb_fy
            else:
                _swapped_periods = True
                st.warning(f"⚠️ {_qs_tag} data not available for FY{_pa} in SEC EDGAR. No recent data found.")

    # --- Period comparison (from sidebar selectors) ---
    _sq2 = st.session_state.get("sankey_compare_quarterly", False)
    _same_period = False

    # Build quarter tag for comparison note
    def _build_q_tag(qs):
        qs = sorted(qs)
        if not qs:
            return ""
        elif len(qs) == 1:
            return f" (Q{qs[0]})"
        else:
            return " (" + "+".join(f"Q{q}" for q in qs) + ")"

    _q_tag = _build_q_tag(_match_qs) if not _sq2 else ""
    # Per-year quarter tags for compare note
    _qa_qs = st.session_state.get("_sankey_qa_nums", _match_qs)
    _qb_qs = st.session_state.get("_sankey_qb_nums", [])

    def _build_period_label(main_fy, cur_qs, prev_qs):
        """Build label like 'FY2026 (Q1) + FY2025 (Q2+Q3)' or 'FY2026 (Q1+Q2)'."""
        parts = []
        if cur_qs:
            parts.append(f"FY{main_fy}{_build_q_tag(cur_qs)}")
        if prev_qs:
            parts.append(f"FY{main_fy - 1}{_build_q_tag(prev_qs)}")
        return " + ".join(parts) if parts else f"FY{main_fy}"

    if _partial_year and _pa and _pb and _pa != _pb:
        _fy_a_int = int(_pa)
        _fy_b_int = int(_pb)
        _fy_b_eff_label = st.session_state.get("_fy_b_eff", _fy_b_int)
        # Both labels use the same year-spanning structure
        _label_a = _build_period_label(_fy_a_int, _qa_qs, _qb_qs) if not _sq2 else _pa
        _label_b = _build_period_label(_fy_b_eff_label, _qa_qs, _qb_qs) if not _sq2 else _pb
        if _swapped_periods:
            # Period A fell back to closest available; Period B kept as-is
            _fb_fy_used = st.session_state.get("_fallback_fy", int(_pb))
            _fb_label = _build_period_label(_fb_fy_used, _qa_qs, _qb_qs) if not _sq2 else f"FY{_fb_fy_used}"
            _compare_label = f"vs {_pb}"
            _compare_note = f"Comparing {_fb_label} vs {_label_b} (FY{_pa} not yet filed)"
        else:
            _compare_label = f"vs {_pb}"
            _compare_note = f"Comparing {_label_a} vs {_label_b}"
    elif _partial_year and _pa and _pb and _pa == _pb:
        _fy_a_int = int(_pa)
        _label_a = _build_period_label(_fy_a_int, _qa_qs, _qb_qs) if not _sq2 else _pa
        if _swapped_periods:
            _fb_fy_used = st.session_state.get("_fallback_fy", _fy_a_int)
            _fb_label = _build_period_label(_fb_fy_used, _qa_qs, _qb_qs) if not _sq2 else f"FY{_fb_fy_used}"
            _compare_label = ""
            _compare_note = f"Showing {_fb_label} — closest available ({_label_a} not yet filed)"
        else:
            _compare_label = f"vs {_pb}"
            _compare_note = f"Comparing {_label_a} vs {_label_a}"
        _same_period = True
    elif _pa and _pb and _pa != _pb:
        income_df = _reorder_df_for_comparison(income_df, _pa, _pb, _sq2)
        balance_df = _reorder_df_for_comparison(balance_df, _pa, _pb, _sq2)
        _compare_label = f"vs {_pb}"
        # Always show quarter tags in compare note (even for full year)
        _all_sel_qs = sorted(set(_qa_qs) | set(_qb_qs)) if (_qa_qs or _qb_qs) else []
        _full_q_tag = _build_q_tag(_all_sel_qs) if _all_sel_qs and not _sq2 else ""
        _compare_note = f"Comparing FY{_pa}{_full_q_tag} vs FY{_pb}{_full_q_tag}"
    elif _pa and _pb and _pa == _pb:
        _compare_label = f"vs {_pb}"
        _all_sel_qs = sorted(set(_qa_qs) | set(_qb_qs)) if (_qa_qs or _qb_qs) else []
        _full_q_tag = _build_q_tag(_all_sel_qs) if _all_sel_qs and not _sq2 else ""
        _compare_note = f"Comparing FY{_pa}{_full_q_tag} vs FY{_pb}{_full_q_tag}"
        _same_period = True
    else:
        _compare_label = "YoY"
        _compare_note = None

    company_name = info.get("shortName", info.get("longName", ticker))

    # ═══════════════════════════════════════════════════════════════════════
    # SINGLE SOURCE OF TRUTH — compute all metrics once using Pandas
    # ═══════════════════════════════════════════════════════════════════════
    _sankey_metrics = _compute_sankey_metrics(income_df, balance_df)
    st.session_state["_sankey_metrics"] = _sankey_metrics  # for audit panel

    # Cross-validate against raw quarterly data if available
    _cross_checks = []
    if _raw_qtr_income_df is not None and not _raw_qtr_income_df.empty:
        _xv_fy_end = st.session_state.get("_fy_end_month", 12)
        _xv_qa = st.session_state.get("_sankey_qa_nums", _match_qs)
        _xv_qb = st.session_state.get("_sankey_qb_nums", [])
        _xv_fy_a = int(_pa) if _pa else 0
        _cross_checks = _cross_validate_metrics(
            _sankey_metrics, _raw_qtr_income_df, _xv_fy_a, _xv_qa, _xv_qb, _xv_fy_end
        )
    st.session_state["_cross_checks"] = _cross_checks

    # Show cross-validation failures as warning (skip if periods were swapped — mismatch expected)
    _xv_fails = [c for c in _cross_checks if not c["ok"]]
    if _xv_fails and not _swapped_periods:
        _xv_parts = []
        for c in _xv_fails:
            if c.get("detail"):
                _xv_parts.append(f'{c["check"]}: {c["detail"]}')
            else:
                _xv_parts.append(f'{c["check"]}: displayed={_fmt(c["displayed"])} vs recomputed={_fmt(c["recomputed"])}')
        _xv_msg = " | ".join(_xv_parts)
        st.warning(f"⚠️ Cross-validation: {_xv_msg}")

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE DATA VALIDATION — runs automatically on every ticker load
    # ═══════════════════════════════════════════════════════════════════════
    _validation_results = []
    if income_df is not None and not income_df.empty and not using_demo:
        _v_revenue = _safe(income_df, "Total Revenue")
        _v_cogs = abs(_safe(income_df, "Cost Of Revenue"))
        _v_gp = _safe(income_df, "Gross Profit")
        _v_op_inc = _safe(income_df, "Operating Income")
        _v_pretax = _safe(income_df, "Pretax Income") or _safe(income_df, "Income Before Tax")
        _v_tax = abs(_safe(income_df, "Tax Provision"))
        _v_ni = _safe(income_df, "Net Income")

        # Check 1: Gross Profit = Revenue - COGS (if both are filed)
        if _v_revenue > 0 and _v_cogs > 0 and _v_gp != 0:
            _computed_gp = _v_revenue - _v_cogs
            _gp_diff = abs(_computed_gp - _v_gp) / _v_revenue * 100
            _validation_results.append({
                "check": "Gross Profit = Revenue − COGS",
                "ok": _gp_diff < 1,
                "detail": f"Computed ${_computed_gp:,.0f} vs Filed ${_v_gp:,.0f} (diff {_gp_diff:.1f}%)",
            })

        # Check 2: Net Income should not exceed Revenue (sanity)
        if _v_revenue > 0 and abs(_v_ni) > _v_revenue * 2:
            _validation_results.append({
                "check": "Net Income magnitude vs Revenue",
                "ok": False,
                "detail": f"NI ${_v_ni:,.0f} exceeds 2x Revenue ${_v_revenue:,.0f}",
            })

        # Check 3: Operating Margin in reasonable range
        if _v_revenue > 0:
            _v_op_margin = _v_op_inc / _v_revenue * 100
            _margin_ok = -200 < _v_op_margin < 200
            if not _margin_ok:
                _validation_results.append({
                    "check": "Operating Margin range",
                    "ok": False,
                    "detail": f"Op Margin {_v_op_margin:.1f}% is extreme",
                })

        # Check 4: Revenue should be positive (unless pre-revenue)
        if _v_revenue == 0 and _v_ni != 0:
            _validation_results.append({
                "check": "Revenue = 0 (pre-revenue company)",
                "ok": True,  # Not an error, just informational
                "detail": "Pre-revenue company — sankey requires revenue as root node",
            })

        # Check 5: Quarter sum validation (if partial year)
        if _partial_year and not _is_full_year:
            _qs_str = "+".join(f"Q{q}" for q in sorted(_match_qs))
            _validation_results.append({
                "check": f"Quarter aggregation ({_qs_str})",
                "ok": _v_revenue > 0 or _v_ni != 0,
                "detail": f"Summed {_qs_str} data: Rev ${_v_revenue:,.0f}, NI ${_v_ni:,.0f}",
            })

    # Store results for the audit panel
    st.session_state["_validation_results"] = _validation_results

    # Show warning banner if any critical check failed
    _failed_checks = [r for r in _validation_results if not r["ok"]]
    if _failed_checks:
        _warn_msg = " | ".join(f'{r["check"]}: {r["detail"]}' for r in _failed_checks)
        st.warning(f"⚠️ Data validation: {_warn_msg}")

    # Tab selection
    sankey_view = st.session_state.get("sankey_view", "income")
    qp_view = st.query_params.get("view", "").lower()
    if qp_view in ("income", "balance"):
        sankey_view = qp_view
        st.session_state.sankey_view = sankey_view

    # ── Handle URL-triggered metric dialog (KPI card / Sankey node clicks) ──
    # JS sets open_metric, metric_section, and a unique _mts nonce.
    # We use the nonce to avoid re-processing the same click on subsequent reruns
    # (params persist in URL until the next navigation).
    _qp_metric = st.query_params.get('open_metric')
    _qp_msection = st.query_params.get('metric_section')
    _qp_ts = st.query_params.get('_mts', '')
    if (_qp_metric and _qp_msection
            and _qp_ts != st.session_state.get('_metric_click_ts', '')):
        st.session_state['_pending_dialog_metric'] = _qp_metric
        st.session_state['_pending_dialog_section'] = _qp_msection
        st.session_state['_metric_click_ts'] = _qp_ts
        # Switch tab if needed
        if _qp_msection in ('income', 'balance') and sankey_view != _qp_msection:
            sankey_view = _qp_msection
            st.session_state.sankey_view = sankey_view

    view_label = "Income Statement" if sankey_view == "income" else "Balance Sheet"

    # ââ Header row: title (HTML) + PDF download button (st.download_button) ââ
    hdr_col, pdf_col = st.columns([0.87, 0.13], vertical_alignment="center")

    with hdr_col:
        st.markdown(f"""
        <div class="sankey-header">
            <div class="sankey-header-left">
                <div class="sankey-title"><img src="https://financialmodelingprep.com/image-stock/{ticker.upper()}.png" class="sankey-company-logo" onerror="this.style.display='none'"> {company_name} &mdash; Sankey Diagram</div>
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
                    label="â¬ PDF",
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

    _auth_qs = get_auth_params()  # "&_sid=..." if logged in, else ""
    st.markdown(f"""
    <div class="sankey-tab-container">
        <a class="sankey-tab {'active' if sankey_view == 'income' else ''}"
           href="?page=sankey&ticker={ticker}&view=income{_auth_qs}" target="_self">Income Statement</a>
        <a class="sankey-tab {'active' if sankey_view == 'balance' else ''}"
           href="?page=sankey&ticker={ticker}&view=balance{_auth_qs}" target="_self">Balance Sheet</a>
    </div>
    """, unsafe_allow_html=True)

    if sankey_view == "income":
        # ââ Historical trend selector (popup) ââ
        st.markdown(f'<div class="sankey-compare-card">{("<span class=sankey-compare-pill>" + _compare_note + "</span>") if _compare_note else ""}</div>', unsafe_allow_html=True)

        # ââ KPI Metric Cards ââ
        # Use Sankey reconciled values if available (handles negative OI, etc.)
        _rec = st.session_state.get('_sankey_reconciled', {})
        _rec_prev = st.session_state.get('_sankey_reconciled_prev', {})
        revenue      = _rec.get('Revenue') or _safe(income_df, 'Total Revenue')
        gross_profit = _rec.get('Gross Profit') or _safe(income_df, 'Gross Profit')
        cogs_kpi     = abs(_rec.get('COGS', 0) or _safe(income_df, 'Cost Of Revenue'))
        op_income    = _rec.get('Operating Income', _safe(income_df, 'Operating Income'))
        net_income   = _rec.get('Net Income', _safe(income_df, 'Net Income'))
        rev_prev     = _rec_prev.get('Revenue') or _safe_prev(income_df, 'Total Revenue')
        gp_prev      = _rec_prev.get('Gross Profit') or _safe_prev(income_df, 'Gross Profit')
        oi_prev      = _rec_prev.get('Operating Income', _safe_prev(income_df, 'Operating Income'))
        ni_prev      = _rec_prev.get('Net Income', _safe_prev(income_df, 'Net Income'))
        # (matches Sankey reconciliation: GP = Revenue − COGS; when COGS=0, GP = Revenue)
        if gross_profit == 0 and revenue > 0:
            gross_profit = revenue - cogs_kpi  # cogs_kpi may be 0 → GP = Revenue
        if gp_prev == 0 and rev_prev > 0:
            cogs_prev = abs(_safe_prev(income_df, "Cost Of Revenue"))
            gp_prev = rev_prev - cogs_prev  # cogs_prev may be 0 → GP_prev = Rev_prev

        # Derive Operating Income when missing (same as Sankey reconciliation)
        if op_income == 0 and gross_profit > 0:
            _rd = abs(_safe(income_df, "Research And Development"))
            _sga = abs(_safe(income_df, "Selling General And Administration"))
            _da = abs(_safe(income_df, "Reconciled Depreciation"))
            if _da == 0:
                _da = abs(_safe(income_df, "Depreciation And Amortization"))
            _oe = abs(_safe(income_df, "Other Operating Expense"))
            op_income = max(0, gross_profit - _rd - _sga - _da - _oe)
        if oi_prev == 0 and gp_prev > 0:
            _rd_p = abs(_safe_prev(income_df, "Research And Development"))
            _sga_p = abs(_safe_prev(income_df, "Selling General And Administration"))
            _da_p = abs(_safe_prev(income_df, "Reconciled Depreciation"))
            if _da_p == 0:
                _da_p = abs(_safe_prev(income_df, "Depreciation And Amortization"))
            _oe_p = abs(_safe_prev(income_df, "Other Operating Expense"))
            oi_prev = max(0, gp_prev - _rd_p - _sga_p - _da_p - _oe_p)

        # Build adaptive KPI cards — only show metrics that have data
        _kpi_items = []
        if revenue != 0:
            _kpi_items.append(("Revenue", revenue, rev_prev))
        if gross_profit != 0:
            _kpi_items.append(("Gross Profit", gross_profit, gp_prev))
        if op_income != 0:
            _kpi_items.append(("Operating Income", op_income, oi_prev))
        if net_income != 0 or op_income != 0:
            _kpi_items.append(("Net Income", net_income, ni_prev))
        # Fallback: always show at least Operating Income + Net Income
        if not _kpi_items:
            _kpi_items = [
                ("Operating Income", op_income, oi_prev),
                ("Net Income", net_income, ni_prev),
            ]
        _kpi_cols = st.columns(len(_kpi_items))
        for _ki, (_kl, _kv, _kp) in enumerate(_kpi_items):
            _kpi_cols[_ki].metric(_kl, _fmt(_kv), _yoy_delta(_kv, _kp, _compare_label))

        st.markdown('<div style="margin-top:1.5rem"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sankey-cta-banner"><div class="sankey-cta-icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></div><div><div class="sankey-cta-text">Click a Metric or Sankey Node to View Historical Trends</div></div></div>', unsafe_allow_html=True)

        # Build Sankey first to get actual node names for pills
        _sankey_result = _build_income_sankey(income_df, info, _compare_label, _same_period,
                                              ticker=ticker)
        fig, _sankey_nodes = _sankey_result if _sankey_result and _sankey_result[0] else (None, [])

        # Pills match exactly the Sankey nodes (preserving INCOME_NODE_METRICS order)
        _node_set = set(_sankey_nodes)
        metric_options = [k for k in INCOME_NODE_METRICS.keys() if k in _node_set]

        # Apply pending dialog trigger from KPI/node click
        if st.session_state.get('_pending_dialog_section') == 'income':
            _pd_m = st.session_state.pop('_pending_dialog_metric', None)
            st.session_state.pop('_pending_dialog_section', None)
            if _pd_m and _pd_m in metric_options:
                st.session_state['_income_show'] = _pd_m

        # on_change increments a counter — we detect fresh clicks by counter change
        def _on_income_pill():
            st.session_state['_income_click_count'] = st.session_state.get('_income_click_count', 0) + 1
            st.session_state['_income_click_val'] = st.session_state.get('_income_pill_wgt')

        sel = st.pills("Trends", metric_options, label_visibility="collapsed",
                       key="_income_pill_wgt", on_change=_on_income_pill)

        # Check if there's a fresh click (counter changed) or pending trigger
        _click_count = st.session_state.get('_income_click_count', 0)
        _last_count = st.session_state.get('_income_last_count', 0)
        _to_show = st.session_state.pop('_income_show', None)

        if _click_count > _last_count:
            # Fresh click detected
            st.session_state['_income_last_count'] = _click_count
            _to_show = st.session_state.pop('_income_click_val', None)

        if _to_show:
            @st.dialog(f"{_to_show} — Historical Trend", width="large")
            def _income_popup():
                _show_metric_popup(ticker, _to_show, "income")
            _income_popup()

        if fig:
            _chart_cfg = {"displayModeBar": "hover", "displaylogo": False, "scrollZoom": False, "modeBarButtons": [["toImage"]]}
            with st.container(key="sankey_income_scroll"):
                st.plotly_chart(fig, use_container_width=True, config=_chart_cfg)

            # Bridge: click Sankey node â auto-click matching pill
            _inject_sankey_click_js(INCOME_NODE_METRICS, section="income")
            _inject_pill_hover_js(INCOME_NODE_METRICS, INCOME_PILL_COLORS)
            _inject_node_hover_js(INCOME_NODE_METRICS, INCOME_PILL_COLORS)
            _inject_kpi_hover_js(
                {"Revenue": "Revenue", "Gross Profit": "Gross Profit",
                 "Operating Income": "Operating Income", "Net Income": "Net Income"},
                INCOME_PILL_COLORS, section="income")
            _inject_link_hover_js(INCOME_PILL_COLORS)
            _inject_delta_color_js()
        else:
            if revenue == 0 and (op_income != 0 or net_income != 0):
                st.info(f"Sankey diagram requires revenue data. {ticker} is a pre-revenue company — use the pill tags above to explore individual metrics.")
            else:
                st.warning(f"No income statement data available for {ticker}.")

        st.caption(f"QuarterCharts \u00b7 SEC EDGAR data \u00b7 {ticker}" + (f" \u00b7 {_compare_note}" if _compare_note else ""))

    elif sankey_view == "balance":
        st.markdown(f'<div class="sankey-compare-card">{("<span class=sankey-compare-pill>" + _compare_note + "</span>") if _compare_note else ""}</div>', unsafe_allow_html=True)

        # ââ KPI Metric Cards for Balance Sheet ââ
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

        st.markdown('<div style="margin-top:1.5rem"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sankey-cta-banner"><div class="sankey-cta-icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></div><div><div class="sankey-cta-text">Click a Metric or Sankey Node to View Historical Trends</div></div></div>', unsafe_allow_html=True)

        # Build Sankey first to get actual node names for pills
        _sankey_result = _build_balance_sheet_sankey(balance_df, info, _compare_label, _same_period,
                                                     ticker=ticker)
        fig, _sankey_nodes = _sankey_result if _sankey_result and _sankey_result[0] else (None, [])

        # Pills match exactly the Sankey nodes (preserving BALANCE_NODE_METRICS order)
        _node_set = set(_sankey_nodes)
        metric_options = [k for k in BALANCE_NODE_METRICS.keys() if k in _node_set]

        # Apply pending dialog trigger from KPI/node click
        if st.session_state.get('_pending_dialog_section') == 'balance':
            _pd_m = st.session_state.pop('_pending_dialog_metric', None)
            st.session_state.pop('_pending_dialog_section', None)
            if _pd_m and _pd_m in metric_options:
                st.session_state['_balance_show'] = _pd_m

        def _on_balance_pill():
            st.session_state['_balance_click_count'] = st.session_state.get('_balance_click_count', 0) + 1
            st.session_state['_balance_click_val'] = st.session_state.get('_balance_pill_wgt')

        sel = st.pills("Trends", metric_options, label_visibility="collapsed",
                       key="_balance_pill_wgt", on_change=_on_balance_pill)

        _click_count = st.session_state.get('_balance_click_count', 0)
        _last_count = st.session_state.get('_balance_last_count', 0)
        _to_show = st.session_state.pop('_balance_show', None)

        if _click_count > _last_count:
            st.session_state['_balance_last_count'] = _click_count
            _to_show = st.session_state.pop('_balance_click_val', None)

        if _to_show:
            @st.dialog(f"{_to_show} — Historical Trend", width="large")
            def _balance_popup():
                _show_metric_popup(ticker, _to_show, "balance")
            _balance_popup()

        if fig:
            _chart_cfg = {"displayModeBar": "hover", "displaylogo": False, "scrollZoom": False, "modeBarButtons": [["toImage"]]}
            with st.container(key="sankey_balance_scroll"):
                st.plotly_chart(fig, use_container_width=True, config=_chart_cfg)

            # Bridge: click Sankey node â auto-click matching pill
            _inject_sankey_click_js(BALANCE_NODE_METRICS, section="balance")
            _inject_pill_hover_js(BALANCE_NODE_METRICS, BALANCE_PILL_COLORS)
            _inject_node_hover_js(BALANCE_NODE_METRICS, BALANCE_PILL_COLORS)
            _inject_kpi_hover_js(
                {"Total Assets": "Total Assets", "Total Liabilities": "Total Liabilities",
                 "Equity": "Equity", "Cash": "Cash"},
                BALANCE_PILL_COLORS, section="balance")
            _inject_link_hover_js(BALANCE_PILL_COLORS)
            _inject_delta_color_js()
        else:
            st.warning(f"No balance sheet data available for {ticker}.")

        st.caption(f"QuarterCharts \u00b7 SEC EDGAR data \u00b7 {ticker}" + (f" \u00b7 {_compare_note}" if _compare_note else ""))

    # ═══════════════════════════════════════════════════════════════════════
    # AUDIT / DEBUG PANEL — "Show Source Data"
    # ═══════════════════════════════════════════════════════════════════════
    with st.expander("🔍 Show Source Data (Audit Panel)", expanded=False):
        st.markdown("""
        <style>
        .audit-header { font-size: 0.85rem; font-weight: 600; color: #495057; margin: 8px 0 4px; }
        .audit-tag { font-family: monospace; font-size: 0.78rem; color: #6c757d; background: #f8f9fa;
                     padding: 2px 6px; border-radius: 3px; }
        </style>
        """, unsafe_allow_html=True)

        _audit_fy_end = st.session_state.get("_fy_end_month", 12)
        _audit_qs = st.session_state.get("_sankey_annual_match_qs", [1, 2, 3, 4])
        _audit_sq = st.session_state.get("sankey_compare_quarterly", False)
        _MON_AUDIT = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

        # ── Section 1: Data source info ──
        st.markdown(f'<p class="audit-header">📋 Data Source</p>', unsafe_allow_html=True)
        _src_cols = st.columns(2)
        with _src_cols[0]:
            st.markdown(f"**Ticker:** {ticker.upper()}")
            st.markdown(f"**FY End Month:** {_MON_AUDIT[_audit_fy_end]} ({_audit_fy_end})")
        with _src_cols[1]:
            st.markdown(f"**Mode:** {'Quarterly' if _audit_sq else 'Annual'}")
            if not _audit_sq:
                _q_str = ", ".join(f"Q{q}" for q in sorted(_audit_qs))
                st.markdown(f"**Selected Quarters:** {_q_str}")
            st.markdown(f"**Period A:** {_pa}  |  **Period B:** {_pb}")
            # Show aggregation errors if any
            _agg_err = st.session_state.get("_partial_agg_error", None)
            if _agg_err:
                st.error(f"⚠️ Partial-year aggregation error: {_agg_err}")
            # Show DF shape for debugging
            if income_df is not None:
                st.markdown(f"**Income DF shape:** {income_df.shape}  |  **Columns:** {list(income_df.columns)[:5]}")
            # Show aggregation debug info
            _agg_dbg = st.session_state.get("_agg_debug", {})
            if _agg_dbg:
                st.markdown(f"**Aggregation Debug:**")
                st.markdown(f"- FY A={_agg_dbg.get('fy_a')} FY B={_agg_dbg.get('fy_b')} | cur_qs={_agg_dbg.get('cur_qs')} prev_qs={_agg_dbg.get('prev_qs')}")
                st.markdown(f"- **Period A found:** {_agg_dbg.get('ser_a_found')} | **Period B found:** {_agg_dbg.get('ser_b_found')}")
                st.markdown(f"- Result shape: {_agg_dbg.get('result_shape')} | FY end: {_agg_dbg.get('fy_end')}")
                _raw_cols = _agg_dbg.get('raw_cols', [])
                if _raw_cols:
                    st.markdown(f"- Raw Q DF columns (first 8): {_raw_cols}")
                # Show expected vs actual column dates for the searched quarters
                _dbg_fy_end = _agg_dbg.get('fy_end', 12)
                _dbg_fy_a = _agg_dbg.get('fy_a', 0)
                _dbg_cur_qs = _agg_dbg.get('cur_qs', [])
                if _dbg_cur_qs and _dbg_fy_a:
                    _expected = []
                    for q in _dbg_cur_qs:
                        em = _fq_end_month_s(q, _dbg_fy_end)
                        ey = _fq_end_year_s(q, _dbg_fy_a, _dbg_fy_end)
                        _expected.append(f"Q{q}→month={em},year={ey}")
                    st.markdown(f"- **Expected columns for Period A:** {_expected}")

        st.markdown("---")

        # ── Section 2: Income Statement — Per-Quarter Tables ──
        # Build two tables (Period A, Period B) with all accounts as rows,
        # each selected quarter as a column, plus a SUM column.
        _audit_fy_end_q = st.session_state.get("_fy_end_month", 12)
        _audit_qa = st.session_state.get("_sankey_qa_nums", [])
        _audit_qb = st.session_state.get("_sankey_qb_nums", [])
        _audit_pa_val = int(_pa) if _pa else 0
        _audit_pb_val = int(_pb) if _pb else 0
        _adj_audit = 1 if (not _audit_qa and _audit_qb) else 0

        # Use raw quarterly data if available; otherwise fall back to aggregated
        _src_inc = _raw_qtr_income_df if (_raw_qtr_income_df is not None and not _raw_qtr_income_df.empty) else (income_df if income_df is not None else pd.DataFrame())

        if not _src_inc.empty:
            # Pre-parse column timestamps once
            _col_ts_map = {}
            for _c in _src_inc.columns:
                try:
                    _col_ts_map[_c] = pd.Timestamp(_c)
                except Exception:
                    pass

            def _find_col_for_q(q_num, fy_val, fy_end_m):
                """Find the DataFrame column matching fiscal quarter q_num of FY fy_val."""
                em = _fq_end_month_s(q_num, fy_end_m)
                ey = _fq_end_year_s(q_num, fy_val, fy_end_m)
                for col_name, ts in _col_ts_map.items():
                    if ts.month == em and ts.year == ey:
                        return col_name
                return None

            def _build_period_table(main_fy, qa_list, qb_list, fy_end_m, src_df, period_name, derived_rows=None):
                """Build a DataFrame: rows = accounts, cols = each Q + SUM.
                derived_rows: dict of row_name → description for derived values."""
                if derived_rows is None:
                    derived_rows = {}
                # Collect (label, col_name) pairs in order
                q_cols = []
                for q in sorted(qa_list):
                    col = _find_col_for_q(q, main_fy, fy_end_m)
                    q_cols.append((f"FY{main_fy} Q{q}", col))
                for q in sorted(qb_list):
                    col = _find_col_for_q(q, main_fy - 1, fy_end_m)
                    q_cols.append((f"FY{main_fy - 1} Q{q}", col))

                if not q_cols:
                    return None, []

                result = pd.DataFrame(index=src_df.index)
                numeric_cols = []
                for label, col_name in q_cols:
                    if col_name is not None and col_name in src_df.columns:
                        result[label] = src_df[col_name]
                        numeric_cols.append(label)
                    else:
                        result[label] = float("nan")

                # SUM column (sum across all quarter columns)
                if numeric_cols:
                    result["SUM"] = result[numeric_cols].sum(axis=1)
                else:
                    result["SUM"] = float("nan")

                # Build footnote index: assign *1, *2, etc. to derived rows that appear in this table
                _footnote_map = {}  # row_name → footnote number
                _footnotes_used = []  # list of (number, row_name, description)
                _fn_counter = 1
                for row_name in result.index:
                    if row_name in derived_rows:
                        _footnote_map[row_name] = _fn_counter
                        _footnotes_used.append((_fn_counter, row_name, derived_rows[row_name]))
                        _fn_counter += 1

                # Convert to object dtype so we can store strings
                result = result.astype(object)

                # Format all numbers, appending *n for derived rows
                for col in result.columns:
                    for row_name in result.index:
                        val = result.at[row_name, col]
                        try:
                            fval = float(val)
                            if pd.notna(fval) and fval != 0:
                                formatted = f"${fval:,.0f}"
                            else:
                                formatted = "—"
                        except (ValueError, TypeError):
                            formatted = "—"
                        if row_name in _footnote_map and formatted != "—":
                            formatted = f"{formatted} *{_footnote_map[row_name]}"
                        result.at[row_name, col] = formatted

                return result, _footnotes_used

            # Period A table
            _derived_inc = st.session_state.get("_derived_income_rows", {})
            _main_fy_a = _audit_pa_val + _adj_audit
            _tbl_a, _fn_a = _build_period_table(_main_fy_a, _audit_qa, _audit_qb, _audit_fy_end_q, _src_inc, "Period A", derived_rows=_derived_inc)
            if _tbl_a is not None:
                _lbl_a = _build_period_label(_main_fy_a, _audit_qa, _audit_qb) if (_audit_qa or _audit_qb) else f"FY{_audit_pa_val}"
                st.markdown(f'<p class="audit-header">📊 Income Statement — Period A: {_lbl_a}</p>', unsafe_allow_html=True)
                st.dataframe(_tbl_a, use_container_width=True)
                if _fn_a:
                    _fn_lines_a = "  \n".join([f"\\*{n} *{row}*: derived from {desc}" for n, row, desc in _fn_a])
                    st.caption(_fn_lines_a)

            st.markdown("---")

            # Period B table
            _main_fy_b = _audit_pb_val + _adj_audit
            _tbl_b, _fn_b = _build_period_table(_main_fy_b, _audit_qa, _audit_qb, _audit_fy_end_q, _src_inc, "Period B", derived_rows=_derived_inc)
            if _tbl_b is not None:
                _lbl_b = _build_period_label(_main_fy_b, _audit_qa, _audit_qb) if (_audit_qa or _audit_qb) else f"FY{_audit_pb_val}"
                st.markdown(f'<p class="audit-header">📊 Income Statement — Period B: {_lbl_b}</p>', unsafe_allow_html=True)
                st.dataframe(_tbl_b, use_container_width=True)
                if _fn_b:
                    _fn_lines_b = "  \n".join([f"\\*{n} *{row}*: derived from {desc}" for n, row, desc in _fn_b])
                    st.caption(_fn_lines_b)
        else:
            st.info("No income data available.")

        st.markdown("---")

        # ── Section 3: Raw balance sheet data ──
        st.markdown(f'<p class="audit-header">🏦 Balance Sheet — Raw Values</p>', unsafe_allow_html=True)
        if balance_df is not None and not balance_df.empty:
            _derived_bal = st.session_state.get("_derived_balance_rows", {})
            # Assign footnote numbers to derived balance sheet rows
            _bs_fn_map = {}
            _bs_footnotes = []
            _bs_fn_ctr = 1
            _disp_balance = balance_df.copy()
            for row_name in _disp_balance.index:
                if row_name in _derived_bal:
                    _bs_fn_map[row_name] = _bs_fn_ctr
                    _bs_footnotes.append((_bs_fn_ctr, row_name, _derived_bal[row_name]))
                    _bs_fn_ctr += 1
            _disp_balance.columns = [str(c) for c in _disp_balance.columns]
            _disp_balance = _disp_balance.astype(object)
            for col in _disp_balance.columns:
                for row_name in _disp_balance.index:
                    val = _disp_balance.at[row_name, col]
                    try:
                        fval = float(val)
                        if pd.notna(fval) and fval != 0:
                            formatted = f"${fval:,.0f}"
                        else:
                            formatted = "—"
                    except (ValueError, TypeError):
                        formatted = "—"
                    if row_name in _bs_fn_map and formatted != "—":
                        formatted = f"{formatted} *{_bs_fn_map[row_name]}"
                    _disp_balance.at[row_name, col] = formatted
            st.dataframe(_disp_balance, use_container_width=True)
            if _bs_footnotes:
                _bs_fn_lines = "  \n".join([f"\\*{n} *{row}*: derived from {desc}" for n, row, desc in _bs_footnotes])
                st.caption(_bs_fn_lines)
        else:
            st.info("No balance sheet data available.")

        st.markdown("---")

        # ── Section 4: Live Validation Results ──
        st.markdown(f'<p class="audit-header">✅ Live Validation (runs automatically on every ticker)</p>', unsafe_allow_html=True)
        _vr = st.session_state.get("_validation_results", [])
        if _vr:
            _check_rows = []
            for r in _vr:
                _check_rows.append({
                    "Status": "✅" if r["ok"] else "⚠️",
                    "Check": r["check"],
                    "Detail": r["detail"],
                })
            st.dataframe(pd.DataFrame(_check_rows), use_container_width=True, hide_index=True)
        else:
            st.success("All automatic checks passed — no issues detected.")

        # ── Section 5: Cross-Validation (Pandas recomputed vs displayed) ──
        st.markdown("---")
        st.markdown(f'<p class="audit-header">🔬 Cross-Validation: Raw Q Sum vs Aggregated (Pandas)</p>', unsafe_allow_html=True)
        _xv = st.session_state.get("_cross_checks", [])
        if _xv:
            _xv_rows = []
            for c in _xv:
                _xv_rows.append({
                    "Status": "✅" if c["ok"] else "❌",
                    "Metric": c["check"],
                    "Displayed (Sankey)": f"${c['displayed']:,.0f}" if c['displayed'] else "—",
                    "Recomputed (Pandas)": f"${c['recomputed']:,.0f}" if c['recomputed'] else "—",
                    "Difference": f"${c['diff']:,.0f}" if c['diff'] else "$0",
                })
            st.dataframe(pd.DataFrame(_xv_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Cross-validation not available (raw quarterly data needed)")

        # ── Section 6: Sankey Flow Reconciliation ──
        st.markdown("---")
        st.markdown(f'<p class="audit-header">⚖️ Sankey Flow Reconciliation (Values & Percentages)</p>', unsafe_allow_html=True)
        _sr = st.session_state.get("_sankey_reconciled", {})
        _sr_prev = st.session_state.get("_sankey_reconciled_prev", {})
        if _sr and _sr.get("Revenue", 0) > 0:
            def _fmt_v(v):
                if v is None or v == 0:
                    return "—"
                if abs(v) >= 1e9:
                    return f"${v/1e9:,.2f}B"
                if abs(v) >= 1e6:
                    return f"${v/1e6:,.0f}M"
                return f"${v:,.0f}"

            def _pct_of(part, whole):
                if whole and whole != 0:
                    return f"{(part / whole) * 100:.1f}%"
                return "—"

            def _yoy_pct(cur, prev):
                if prev and prev != 0:
                    return f"{((cur - prev) / abs(prev)) * 100:+.1f}%"
                return "N/A"

            _rev = _sr.get("Revenue", 0)
            _cogs = _sr.get("COGS", 0)
            _gp = _sr.get("Gross Profit", 0)
            _rd = _sr.get("R&D", 0)
            _sga = _sr.get("SG&A", 0)
            _da = _sr.get("D&A", 0)
            _oox = _sr.get("Other OpEx", 0)
            _oi = _sr.get("Operating Income", 0)
            _int = _sr.get("Interest Exp.", 0)
            _pt = _sr.get("Pretax Income", 0)
            _tx = _sr.get("Tax", 0)
            _ni = _sr.get("Net Income", 0)

            # Level checks
            _l1_sum = _cogs + _gp
            _l2_sum = _rd + _sga + _da + _oox + _oi
            _l3_sum = _int + _pt
            _l4_sum = _tx + _ni

            _l1_ok = abs(_l1_sum - _rev) < 1
            _l2_ok = abs(_l2_sum - _gp) < 1
            _l3_ok = abs(_l3_sum - _oi) < 1
            _l4_ok = abs(_l4_sum - _pt) < 1

            _flow_rows = [
                {"Level": "1", "Check": "Revenue = COGS + Gross Profit",
                 "Left Side": _fmt_v(_rev), "Right Side": f"{_fmt_v(_cogs)} + {_fmt_v(_gp)} = {_fmt_v(_l1_sum)}",
                 "Diff": _fmt_v(_rev - _l1_sum), "Status": "✅" if _l1_ok else "❌"},
                {"Level": "2", "Check": "Gross Profit = R&D + SG&A + D&A + Other + OpInc",
                 "Left Side": _fmt_v(_gp), "Right Side": f"{_fmt_v(_rd)}+{_fmt_v(_sga)}+{_fmt_v(_da)}+{_fmt_v(_oox)}+{_fmt_v(_oi)} = {_fmt_v(_l2_sum)}",
                 "Diff": _fmt_v(_gp - _l2_sum), "Status": "✅" if _l2_ok else "❌"},
                {"Level": "3", "Check": "Operating Income = Interest + Pretax",
                 "Left Side": _fmt_v(_oi), "Right Side": f"{_fmt_v(_int)} + {_fmt_v(_pt)} = {_fmt_v(_l3_sum)}",
                 "Diff": _fmt_v(_oi - _l3_sum), "Status": "✅" if _l3_ok else "❌"},
                {"Level": "4", "Check": "Pretax Income = Tax + Net Income",
                 "Left Side": _fmt_v(_pt), "Right Side": f"{_fmt_v(_tx)} + {_fmt_v(_ni)} = {_fmt_v(_l4_sum)}",
                 "Diff": _fmt_v(_pt - _l4_sum), "Status": "✅" if _l4_ok else "❌"},
            ]
            st.dataframe(pd.DataFrame(_flow_rows), use_container_width=True, hide_index=True)

            # ── Percentage breakdown table ──
            st.markdown(f'<p class="audit-header" style="font-size:1rem;margin-top:12px;">📐 Margins & YoY Changes</p>', unsafe_allow_html=True)
            _pct_rows = [
                {"Metric": "Revenue", "Value": _fmt_v(_rev), "% of Revenue": "100.0%",
                 "Previous": _fmt_v(_sr_prev.get("Revenue", 0)), "YoY %": _yoy_pct(_rev, _sr_prev.get("Revenue", 0))},
                {"Metric": "COGS", "Value": _fmt_v(_cogs), "% of Revenue": _pct_of(_cogs, _rev),
                 "Previous": _fmt_v(_sr_prev.get("COGS", 0)), "YoY %": _yoy_pct(_cogs, _sr_prev.get("COGS", 0))},
                {"Metric": "Gross Profit", "Value": _fmt_v(_gp), "% of Revenue": _pct_of(_gp, _rev),
                 "Previous": _fmt_v(_sr_prev.get("Gross Profit", 0)), "YoY %": _yoy_pct(_gp, _sr_prev.get("Gross Profit", 0))},
                {"Metric": "R&D", "Value": _fmt_v(_rd), "% of Revenue": _pct_of(_rd, _rev),
                 "Previous": _fmt_v(_sr_prev.get("R&D", 0)), "YoY %": _yoy_pct(_rd, _sr_prev.get("R&D", 0))},
                {"Metric": "SG&A", "Value": _fmt_v(_sga), "% of Revenue": _pct_of(_sga, _rev),
                 "Previous": _fmt_v(_sr_prev.get("SG&A", 0)), "YoY %": _yoy_pct(_sga, _sr_prev.get("SG&A", 0))},
                {"Metric": "D&A", "Value": _fmt_v(_da), "% of Revenue": _pct_of(_da, _rev),
                 "Previous": _fmt_v(_sr_prev.get("D&A", 0)), "YoY %": _yoy_pct(_da, _sr_prev.get("D&A", 0))},
                {"Metric": "Other OpEx", "Value": _fmt_v(_oox), "% of Revenue": _pct_of(_oox, _rev),
                 "Previous": _fmt_v(_sr_prev.get("Other OpEx", 0)), "YoY %": _yoy_pct(_oox, _sr_prev.get("Other OpEx", 0))},
                {"Metric": "Operating Income", "Value": _fmt_v(_oi), "% of Revenue": _pct_of(_oi, _rev),
                 "Previous": _fmt_v(_sr_prev.get("Operating Income", 0)), "YoY %": _yoy_pct(_oi, _sr_prev.get("Operating Income", 0))},
                {"Metric": "Interest Exp.", "Value": _fmt_v(_int), "% of Revenue": _pct_of(_int, _rev),
                 "Previous": _fmt_v(_sr_prev.get("Interest Exp.", 0)), "YoY %": _yoy_pct(_int, _sr_prev.get("Interest Exp.", 0))},
                {"Metric": "Pretax Income", "Value": _fmt_v(_pt), "% of Revenue": _pct_of(_pt, _rev),
                 "Previous": _fmt_v(_sr_prev.get("Pretax Income", 0)), "YoY %": _yoy_pct(_pt, _sr_prev.get("Pretax Income", 0))},
                {"Metric": "Tax", "Value": _fmt_v(_tx), "% of Revenue": _pct_of(_tx, _rev),
                 "Previous": _fmt_v(_sr_prev.get("Tax", 0)), "YoY %": _yoy_pct(_tx, _sr_prev.get("Tax", 0))},
                {"Metric": "Net Income", "Value": _fmt_v(_ni), "% of Revenue": _pct_of(_ni, _rev),
                 "Previous": _fmt_v(_sr_prev.get("Net Income", 0)), "YoY %": _yoy_pct(_ni, _sr_prev.get("Net Income", 0))},
            ]
            st.dataframe(pd.DataFrame(_pct_rows), use_container_width=True, hide_index=True)

            # ── Margin verification (recomputed vs displayed) ──
            st.markdown(f'<p class="audit-header" style="font-size:1rem;margin-top:12px;">🧮 Margin Cross-Check (Value ÷ Revenue)</p>', unsafe_allow_html=True)
            _margin_checks = []
            _margin_items = [
                ("Gross Margin", _gp, _rev),
                ("Operating Margin", _oi, _rev),
                ("Pretax Margin", _pt, _rev),
                ("Net Margin", _ni, _rev),
                ("COGS %", _cogs, _rev),
                ("R&D %", _rd, _rev),
                ("SG&A %", _sga, _rev),
            ]
            for name, numerator, denominator in _margin_items:
                calc_pct = (numerator / denominator * 100) if denominator > 0 else 0
                prev_num = _sr_prev.get(name.replace(" Margin", "").replace(" %", ""), 0)
                prev_rev = _sr_prev.get("Revenue", 0)
                # Map name back to _sr_prev keys
                _key_map = {"Gross Margin": "Gross Profit", "Operating Margin": "Operating Income",
                            "Pretax Margin": "Pretax Income", "Net Margin": "Net Income",
                            "COGS %": "COGS", "R&D %": "R&D", "SG&A %": "SG&A"}
                prev_num = _sr_prev.get(_key_map.get(name, ""), 0)
                prev_pct = (prev_num / prev_rev * 100) if prev_rev > 0 else 0
                change = calc_pct - prev_pct
                _margin_checks.append({
                    "Margin": name,
                    "Current": f"{calc_pct:.1f}%",
                    "Previous": f"{prev_pct:.1f}%",
                    "Change (pp)": f"{change:+.1f}pp",
                })
            st.dataframe(pd.DataFrame(_margin_checks), use_container_width=True, hide_index=True)
        else:
            st.info("Sankey reconciliation data not available.")

        # ── Section 7: Sankey Metrics (Single Source of Truth) ──
        st.markdown("---")
        st.markdown(f'<p class="audit-header">📊 Pandas Metrics (Single Source of Truth)</p>', unsafe_allow_html=True)
        _sm = st.session_state.get("_sankey_metrics", {})
        if _sm.get("df_info"):
            st.markdown(f"**DataFrame Info:** {_sm['df_info']}")
        if _sm.get("income"):
            _m_rows = []
            for k, v in _sm["income"].items():
                _m_rows.append({
                    "Account": k,
                    "Current (Period A)": f"${v['current']:,.0f}" if v['current'] else "—",
                    "Previous (Period B)": f"${v['previous']:,.0f}" if v['previous'] else "—",
                    "% Change": f"{v['pct_change']:+.1f}%" if v['pct_change'] is not None else "N/A",
                    "$ Change": f"${v['dollar_change']:,.0f}" if v['dollar_change'] is not None else "N/A",
                })
            st.dataframe(pd.DataFrame(_m_rows), use_container_width=True, hide_index=True)

        # ── Section 7: XBRL tags used ──
        st.markdown("---")
        st.markdown(f'<p class="audit-header">🏷️ XBRL Tags Reference</p>', unsafe_allow_html=True)
        _tag_data = []
        for display_name, tags in _XBRL_INCOME_TAGS.items():
            _tag_data.append({
                "Metric": display_name,
                "XBRL Tags (priority order)": " → ".join(tags) if tags else "Derived",
            })
        st.dataframe(pd.DataFrame(_tag_data), use_container_width=True, hide_index=True)
""""""
