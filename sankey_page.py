"""
Sankey diagram page – Income Statement & Balance Sheet visualizations.
Fixed-position nodes with vivid 11-color palette, KPI metric cards,
and Pretax Income waterfall matching OpenSankey deployed style.
"""
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
from io import BytesIO
import numpy as np

# Demo / sample data for when Yahoo Finance is rate-limited
def _get_demo_data(ticker: str):
    """Return hardcoded sample financial data so Sankey always renders."""
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


def _yoy_delta(current, previous):
    """Format YoY as delta string for st.metric."""
    pct = _yoy(current, previous)
    if pct is None:
        return None
    return f"{pct:+.1f}% YoY"


# ─── Node label → Yahoo Finance metric mapping ───────────────────────────
# Maps the display name in each Sankey node to the yfinance DataFrame row key.
# Used to pull historical time-series when a user clicks a node.

INCOME_NODE_METRICS = {
    "Revenue":          "Total Revenue",
    "Cost of Revenue":  "Cost Of Revenue",
    "Gross Profit":     "Gross Profit",
    "R&D":              "Research Development",
    "SG&A":             "Selling General Administrative",
    "D&A":              "Reconciled Depreciation",
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
    "Intangibles":        "Intangible Assets",
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


def _get_historical_series(df, yf_key):
    """Extract a full time-series row from a yfinance DataFrame.

    Returns a pandas Series with datetime index and float values,
    sorted chronologically (oldest first).

    Matching strategy:
    1. Exact substring match (original)
    2. All significant words (3+ chars) from yf_key appear in the index name
    This handles yfinance inconsistencies like
    "Selling General Administrative" vs "Selling General And Administrative".
    """
    if df is None or df.empty:
        return None

    # Strategy 1: exact substring match
    for idx in df.index:
        if yf_key.lower() in str(idx).lower():
            row = df.loc[idx].dropna().astype(float)
            if not row.empty:
                row.index = pd.to_datetime(row.index)
                return row.sort_index()

    # Strategy 2: all significant word-stems (first 5 chars) present
    # Handles yfinance inconsistencies like "Administrative" vs "Administration"
    key_words = [w[:5] for w in yf_key.lower().split() if len(w) >= 4]
    if key_words:
        for idx in df.index:
            idx_lower = str(idx).lower()
            if all(stem in idx_lower for stem in key_words):
                row = df.loc[idx].dropna().astype(float)
                if not row.empty:
                    row.index = pd.to_datetime(row.index)
                    return row.sort_index()

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_quarterly_data(ticker: str):
    """Fetch quarterly income & balance sheet for historical XY charts."""
    stock = yf.Ticker(ticker)
    try:
        q_income = stock.get_income_stmt(freq="quarterly")
        q_balance = stock.get_balance_sheet(freq="quarterly")
    except Exception:
        q_income = stock.quarterly_financials
        q_balance = stock.quarterly_balance_sheet
    return q_income, q_balance


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_annual_data(ticker: str):
    """Fetch annual income & balance sheet for historical XY charts."""
    stock = yf.Ticker(ticker)
    try:
        a_income = stock.get_income_stmt(freq="yearly")
        a_balance = stock.get_balance_sheet(freq="yearly")
    except Exception:
        a_income = stock.financials
        a_balance = stock.balance_sheet
    return a_income, a_balance


def _show_metric_popup(ticker, node_label, view):
    """Show a popup (dialog) with historical chart + Quarterly/Annual & period selectors."""

    # Determine which mapping to use
    metric_map = INCOME_NODE_METRICS if view == "income" else BALANCE_NODE_METRICS

    clean_label = node_label.split("<br>")[0] if "<br>" in node_label else node_label
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
                st.rerun()

    # Render period selector
    period_cols = st.columns([1, 3, 1])
    with period_cols[1]:
        pc = st.columns(4)
        for i, lbl in enumerate(["1Y", "2Y", "4Y", "MAX"]):
            if pc[i].button(lbl, key=f"{period_key}_{lbl}",
                            type="primary" if st.session_state[period_key] == lbl else "secondary",
                            use_container_width=True):
                st.session_state[period_key] = lbl
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
        hovertemplate=f"%{{x|%b %Y}}<br>${{y:.2f}}{suffix}<extra></extra>",
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

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"hist_{freq}_{period}")

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
                    // Strip value after <br>
                    var label = raw.split('<br>')[0].replace(/\\n/g, '').trim();
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
    """Generate a professional PDF with waterfall / stacked-bar chart + KPI cards.

    Income Statement  → waterfall chart showing Revenue → Net Income flow.
    Balance Sheet     → stacked horizontal bars (Assets vs Liabilities & Equity).
    Uses matplotlib only (no kaleido needed).  Returns PDF bytes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.ticker import FuncFormatter
    import numpy as np

    buf = BytesIO()
    company = info.get("shortName", info.get("longName", ticker))

    def _fmts(v):
        """Short format for labels."""
        av = abs(v)
        if av >= 1e12: return f"${v/1e12:.1f}T"
        if av >= 1e9:  return f"${v/1e9:.1f}B"
        if av >= 1e6:  return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"

    def _fmt_axis(v, _pos):
        if abs(v) >= 1e12: return f"${v/1e12:.1f}T"
        if abs(v) >= 1e9:  return f"${v/1e9:.0f}B"
        if abs(v) >= 1e6:  return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"

    def _draw_kpi_row(fig, kpis, y_bottom=0.85, height=0.07):
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
            ax_kpi.text(xc, 0.75, lbl, ha="center", va="center",
                        fontsize=10, color="#64748b")
            ax_kpi.text(xc, 0.25, _fmts(val), ha="center", va="center",
                        fontsize=16, color="#1e293b", fontweight="bold")
            if i < len(kpis) - 1:
                ax_kpi.axvline(x=i + 1, color="#e2e8f0", linewidth=1.5)

    try:
        with PdfPages(buf) as pdf:
            if view == "income":
                # ── Extract data ──
                revenue      = _safe(income_df, "Total Revenue")
                cogs         = abs(_safe(income_df, "Cost Of Revenue"))
                gross_profit = _safe(income_df, "Gross Profit") or (revenue - cogs)
                rd           = abs(_safe(income_df, "Research And Development"))
                sga          = abs(_safe(income_df, "Selling General And Administration"))
                da           = abs(_safe(income_df, "Reconciled Depreciation"))
                if da == 0:
                    da = abs(_safe(income_df, "Depreciation And Amortization"))
                op_income    = _safe(income_df, "Operating Income")
                interest     = abs(_safe(income_df, "Interest Expense"))
                pretax       = _safe(income_df, "Pretax Income") or _safe(income_df, "Income Before Tax")
                tax          = abs(_safe(income_df, "Tax Provision"))
                net_income   = _safe(income_df, "Net Income")

                if revenue == 0:
                    return b""

                # Fix derived
                if gross_profit == 0:
                    gross_profit = revenue - cogs
                if op_income == 0:
                    op_income = gross_profit - rd - sga - da
                if pretax == 0:
                    pretax = op_income - interest
                if net_income == 0:
                    net_income = pretax - tax

                # ── Build waterfall steps ──
                # (label, amount, type, color)
                steps = [("Revenue", revenue, "total", "#22c55e")]
                if cogs > 0:
                    steps.append(("COGS", -cogs, "expense", "#ef4444"))
                steps.append(("Gross Profit", gross_profit, "subtotal", "#3b82f6"))
                if sga > 0:
                    steps.append(("SG&A", -sga, "expense", "#f97316"))
                if rd > 0:
                    steps.append(("R&D", -rd, "expense", "#f59e0b"))
                if da > 0:
                    steps.append(("D&A", -da, "expense", "#a855f7"))
                steps.append(("Operating Inc.", max(op_income, 0), "subtotal", "#06b6d4"))
                if interest > 0:
                    steps.append(("Interest", -interest, "expense", "#64748b"))
                steps.append(("Pretax Income", max(pretax, 0), "subtotal", "#6366f1"))
                if tax > 0:
                    steps.append(("Tax", -tax, "expense", "#ec4899"))
                steps.append(("Net Income", max(net_income, 0), "subtotal", "#84cc16"))

                n = len(steps)
                labels  = [s[0] for s in steps]
                amounts = [s[1] for s in steps]
                types   = [s[2] for s in steps]
                colors  = [s[3] for s in steps]

                # Compute waterfall bar positions
                bottoms = []
                heights = []
                running = 0.0
                for _l, amt, typ, _c in steps:
                    if typ in ("total", "subtotal"):
                        bottoms.append(0)
                        heights.append(abs(amt))
                        running = abs(amt)
                    else:  # expense
                        new_running = running + amt
                        bottoms.append(max(new_running, 0))
                        heights.append(abs(amt))
                        running = max(new_running, 0)

                # ── Draw figure ──
                fig = plt.figure(figsize=(16, 9), facecolor="white")
                fig.text(0.5, 0.96, f"{company} ({ticker}) — Income Statement Flow",
                         ha="center", va="top", fontsize=20, fontweight="bold",
                         color="#0f172a")

                _draw_kpi_row(fig, [
                    ("Revenue", revenue), ("Gross Profit", gross_profit),
                    ("Operating Income", op_income), ("Net Income", net_income),
                ])

                ax = fig.add_axes([0.08, 0.08, 0.88, 0.72])
                x_pos = np.arange(n)
                ax.bar(x_pos, heights, bottom=bottoms, color=colors, width=0.55,
                       edgecolor="white", linewidth=1, zorder=3)

                # Connector lines between expense steps
                for i in range(n - 1):
                    if types[i + 1] == "expense":
                        y_line = bottoms[i + 1] + heights[i + 1]
                        ax.plot([x_pos[i] + 0.275, x_pos[i + 1] - 0.275],
                                [y_line, y_line],
                                color="#94a3b8", linewidth=0.8, linestyle="--",
                                zorder=2)

                # Value labels
                offset = revenue * 0.015
                for i in range(n):
                    val = abs(amounts[i])
                    y_top = bottoms[i] + heights[i] + offset
                    txt = (f"\u2212{_fmts(val)}" if types[i] == "expense"
                           else _fmts(val))
                    ax.text(x_pos[i], y_top, txt, ha="center", va="bottom",
                            fontsize=9, fontweight="bold", color="#374151")

                ax.set_xticks(x_pos)
                ax.set_xticklabels(labels, fontsize=10, fontweight="medium",
                                   color="#374151")
                ax.yaxis.set_major_formatter(FuncFormatter(_fmt_axis))
                ax.set_xlim(-0.6, n - 0.4)
                ax.set_ylim(0, revenue * 1.15)
                ax.grid(axis="y", alpha=0.12, zorder=1, color="#94a3b8")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["bottom"].set_color("#cbd5e1")
                ax.spines["left"].set_color("#cbd5e1")
                ax.tick_params(axis="y", labelsize=9, colors="#64748b")
                ax.tick_params(axis="x", length=0)

                fig.text(0.5, 0.01,
                         f"OpenSankey  \u00b7  Yahoo Finance data  \u00b7  {ticker}",
                         ha="center", va="bottom", fontsize=8, color="#94a3b8")
                pdf.savefig(fig, facecolor="white", dpi=150)
                plt.close(fig)

            else:
                # ── Balance Sheet stacked horizontal bars ──
                total_assets = _safe(balance_df, "Total Assets")
                if total_assets == 0:
                    return b""

                cash         = _safe(balance_df, "Cash And Cash Equivalents")
                receivables  = (_safe(balance_df, "Accounts Receivable")
                                or _safe(balance_df, "Receivables"))
                ppe          = (_safe(balance_df, "Net PPE")
                                or _safe(balance_df, "Property Plant Equipment"))
                goodwill     = _safe(balance_df, "Goodwill")
                short_invest = _safe(balance_df, "Other Short Term Investments")
                investments  = (_safe(balance_df, "Investments And Advances")
                                or _safe(balance_df, "Long Term Equity Investment"))
                total_liab   = (_safe(balance_df, "Total Liabilities Net Minority Interest")
                                or _safe(balance_df, "Total Liab"))
                current_liab = _safe(balance_df, "Current Liabilities")
                long_debt    = _safe(balance_df, "Long Term Debt")
                equity       = (_safe(balance_df, "Stockholders Equity")
                                or _safe(balance_df, "Total Stockholders Equity"))
                if equity == 0 and total_assets > 0 and total_liab > 0:
                    equity = total_assets - total_liab

                # Build asset & funding breakdown items
                asset_items = []
                if cash > 0:
                    asset_items.append(("Cash", cash, "#06b6d4"))
                if short_invest > 0:
                    asset_items.append(("ST Invest.", short_invest, "#a855f7"))
                if receivables > 0:
                    asset_items.append(("Receivables", receivables, "#3b82f6"))
                if ppe > 0:
                    asset_items.append(("PPE", ppe, "#8b5cf6"))
                if goodwill > 0:
                    asset_items.append(("Goodwill", goodwill, "#6366f1"))
                if investments > 0:
                    asset_items.append(("Investments", investments, "#a855f7"))
                other_a = max(0, total_assets - sum(x[1] for x in asset_items))
                if other_a > 0:
                    asset_items.append(("Other Assets", other_a, "#94a3b8"))

                fund_items = []
                if current_liab > 0:
                    fund_items.append(("Current Liab.", current_liab, "#f59e0b"))
                if long_debt > 0:
                    fund_items.append(("Long-Term Debt", long_debt, "#ef4444"))
                other_l = max(0, total_liab - current_liab - long_debt)
                if other_l > 0:
                    fund_items.append(("Other Liab.", other_l, "#f97316"))
                if equity > 0:
                    fund_items.append(("Equity", equity, "#22c55e"))

                # ── Draw figure ──
                fig = plt.figure(figsize=(16, 9), facecolor="white")
                fig.text(0.5, 0.96,
                         f"{company} ({ticker}) — Balance Sheet Breakdown",
                         ha="center", va="top", fontsize=20, fontweight="bold",
                         color="#0f172a")

                _draw_kpi_row(fig, [
                    ("Total Assets", total_assets), ("Total Liabilities", total_liab),
                    ("Equity", equity), ("Cash", cash),
                ])

                ax = fig.add_axes([0.12, 0.08, 0.82, 0.72])
                bar_h = 0.45
                rows = [
                    (asset_items, 1.0, "Assets"),
                    (fund_items, 0.3, "Liabilities\n& Equity"),
                ]
                for items, y_pos, row_lbl in rows:
                    left = 0
                    for lbl, val, clr in items:
                        ax.barh(y_pos, val, left=left, height=bar_h, color=clr,
                                edgecolor="white", linewidth=1.5, zorder=3)
                        mid = left + val / 2
                        ratio = val / total_assets
                        if ratio > 0.08:
                            ax.text(mid, y_pos, f"{lbl}\n{_fmts(val)}",
                                    ha="center", va="center",
                                    fontsize=8, fontweight="bold", color="white",
                                    zorder=4)
                        elif ratio > 0.04:
                            ax.text(mid, y_pos, _fmts(val), ha="center",
                                    va="center", fontsize=7, fontweight="bold",
                                    color="white", zorder=4)
                        left += val
                    ax.text(-total_assets * 0.01, y_pos, row_lbl, ha="right",
                            va="center", fontsize=11, fontweight="bold",
                            color="#374151")

                ax.set_xlim(0, total_assets * 1.02)
                ax.set_ylim(-0.1, 1.5)
                ax.xaxis.set_major_formatter(FuncFormatter(_fmt_axis))
                ax.set_yticks([])
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_visible(False)
                ax.spines["bottom"].set_color("#cbd5e1")
                ax.grid(axis="x", alpha=0.12, zorder=1, color="#94a3b8")
                ax.tick_params(axis="x", labelsize=9, colors="#64748b")

                fig.text(0.5, 0.01,
                         f"OpenSankey  \u00b7  Yahoo Finance data  \u00b7  {ticker}",
                         ha="center", va="bottom", fontsize=8, color="#94a3b8")
                pdf.savefig(fig, facecolor="white", dpi=150)
                plt.close(fig)

    except Exception:
        return b""

    return buf.getvalue()


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_sankey_data(ticker: str):
    """Fetch income statement, balance sheet data for Sankey diagrams."""
    try:
        stock = yf.Ticker(ticker)
        income = stock.financials
        balance = stock.balance_sheet
        info = stock.info or {}
        return income, balance, info
    except Exception as e:
        # Handle rate limit and other yfinance errors gracefully
        import time
        error_msg = str(e).lower()
        if "rate" in error_msg or "limit" in error_msg or "too many" in error_msg:
            time.sleep(2)
            try:
                stock = yf.Ticker(ticker)
                income = stock.financials
                balance = stock.balance_sheet
                info = stock.info or {}
                return income, balance, info
            except Exception:
                pass
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
        nodes.append(f"{name}<br>{_fmt(val)}")
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
        nodes.append(f"{name}<br>{_fmt(val)}")
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

        /* -- Sankey Responsive -- */
        @media (max-width: 768px) {
            .sankey-header { padding: 16px 14px 14px !important; flex-direction: column !important; gap: 8px !important; }
            .sankey-title { font-size: 1.2rem !important; }
            .sankey-subtitle { font-size: 0.8rem !important; }
            .sankey-tab { padding: 9px 16px !important; font-size: 0.82rem !important; }
            .sankey-legend { flex-wrap: wrap !important; gap: 12px !important; padding: 10px 12px !important; font-size: 0.78rem !important; }
            div[data-testid="metric-container"] { padding: 10px 12px !important; }
            [data-testid="stHorizontalBlock"]:has([class*="st-key-dl_sankey_"]),
            [data-testid="stHorizontalBlock"]:has([class*="st-key-gen_pdf_sankey_"]) { padding: 6px 4px !important; }
        }
        @media (max-width: 480px) {
            .sankey-header { padding: 12px 10px !important; border-radius: 8px !important; }
            .sankey-title { font-size: 1rem !important; }
            .sankey-tab-container { flex-wrap: wrap !important; }
            .sankey-tab { padding: 8px 12px !important; font-size: 0.78rem !important; flex: 1 !important; text-align: center !important; }
            .sankey-tab:first-child { border-radius: 8px 0 0 8px !important; }
            .sankey-tab:last-child { border-radius: 0 8px 8px 0 !important; }
            .sankey-legend { gap: 8px !important; font-size: 0.72rem !important; }
        }
    </style>
    """, unsafe_allow_html=True)

    # Fetch data
    using_demo = False
    with st.spinner(f"Loading {ticker} financial data..."):
        try:
            income_df, balance_df, info = _fetch_sankey_data(ticker)
        except Exception:
            income_df, balance_df, info = pd.DataFrame(), pd.DataFrame(), {"shortName": ticker}

    # If data is empty (rate-limited), fall back to demo data
    if income_df.empty and balance_df.empty:
        income_df, balance_df, info = _get_demo_data(ticker)
        using_demo = True
        st.info(f"Showing sample data for **{ticker.upper()}** -- Yahoo Finance is temporarily rate-limiting requests. Refresh in a minute for live data.")

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
                <div class="sankey-title">🔀 {company_name} — Sankey Diagram</div>
                <div class="sankey-subtitle">Annual financial flow visualization · Most recent fiscal year</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with pdf_col:
        # Pre-generate or retrieve cached PDF
        _pdf_key = f"_sankey_pdf_v2_{ticker}_{sankey_view}"
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

    if sankey_view == "income":
        # ── KPI Metric Cards ──
        revenue      = _safe(income_df, "Total Revenue")
        gross_profit = _safe(income_df, "Gross Profit")
        op_income    = _safe(income_df, "Operating Income")
        net_income   = _safe(income_df, "Net Income")
        rev_prev     = _safe_prev(income_df, "Total Revenue")
        gp_prev      = _safe_prev(income_df, "Gross Profit")
        oi_prev      = _safe_prev(income_df, "Operating Income")
        ni_prev      = _safe_prev(income_df, "Net Income")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Revenue", _fmt(revenue), _yoy_delta(revenue, rev_prev))
        m2.metric("Gross Profit", _fmt(gross_profit), _yoy_delta(gross_profit, gp_prev))
        m3.metric("Operating Income", _fmt(op_income), _yoy_delta(op_income, oi_prev))
        m4.metric("Net Income", _fmt(net_income), _yoy_delta(net_income, ni_prev))

        st.divider()

        fig = _build_income_sankey(income_df, info)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # ── Historical trend selector (popup) ──
            metric_options = list(INCOME_NODE_METRICS.keys())
            sel = st.pills("📈 Click a metric to see historical trend",
                           metric_options, key="income_metric_pill")
            if sel:
                @st.dialog(f"{sel} — Historical Trend", width="large")
                def _income_popup():
                    _show_metric_popup(ticker, sel, "income")
                _income_popup()

            # Bridge: click Sankey node → auto-click matching pill
            _inject_sankey_click_js(INCOME_NODE_METRICS)
        else:
            st.warning(f"No income statement data available for {ticker}.")

        st.caption(f"📊 OpenSankey · Yahoo Finance data · {ticker}")

    elif sankey_view == "balance":
        # ── KPI Metric Cards for Balance Sheet ──
        total_assets = _safe(balance_df, "Total Assets")
        total_liab   = _safe(balance_df, "Total Liabilities Net Minority Interest") or _safe(balance_df, "Total Liab")
        equity_val   = _safe(balance_df, "Stockholders Equity") or _safe(balance_df, "Total Stockholders Equity")
        cash_val     = _safe(balance_df, "Cash And Cash Equivalents")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Assets", _fmt(total_assets))
        m2.metric("Total Liabilities", _fmt(total_liab))
        m3.metric("Equity", _fmt(equity_val))
        m4.metric("Cash", _fmt(cash_val))

        st.divider()

        fig = _build_balance_sheet_sankey(balance_df, info)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # ── Historical trend selector (popup) ──
            metric_options = list(BALANCE_NODE_METRICS.keys())
            sel = st.pills("📈 Click a metric to see historical trend",
                           metric_options, key="balance_metric_pill")
            if sel:
                @st.dialog(f"{sel} — Historical Trend", width="large")
                def _balance_popup():
                    _show_metric_popup(ticker, sel, "balance")
                _balance_popup()

            # Bridge: click Sankey node → auto-click matching pill
            _inject_sankey_click_js(BALANCE_NODE_METRICS)
        else:
            st.warning(f"No balance sheet data available for {ticker}.")

        st.caption(f"📊 OpenSankey · Yahoo Finance data · {ticker}")
