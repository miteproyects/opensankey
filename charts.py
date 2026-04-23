"""
Charts module for Quarter Charts.

Creates all Plotly charts with a light finance theme.
Every function accepts a pandas DataFrame where:
    - the **index** contains period labels ("Q4 2025", "2024", …)
    - the **columns** contain metric values with the names specified below.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Colour palette (light theme)
# ---------------------------------------------------------------------------

COLORS: Dict[str, str] = {
    "blue": "#4285f4",
    "yellow": "#fbbc04",
    "red": "#ea4335",
    "green": "#34a853",
    "purple": "#9c27b0",
    "teal": "#00bcd4",
    "orange": "#ff9800",
    "pink": "#e91e63",
    "bg": "#ffffff",
    "card": "#ffffff",
    "grid": "#e9ecef",
    "text": "#212529",
    "muted": "#6c757d",
}

PALETTE: List[str] = [
    COLORS["blue"],
    COLORS["yellow"],
    COLORS["red"],
    COLORS["green"],
    COLORS["purple"],
    COLORS["teal"],
    COLORS["orange"],
    COLORS["pink"],
]


# ---------------------------------------------------------------------------
# Shared layout helper
# ---------------------------------------------------------------------------

def _layout(title: str, height: int = 420, **overrides) -> Dict[str, Any]:
    """Return the standard light-theme layout dict for a Plotly figure."""
    # Title is rendered externally via Streamlit markdown (see app.py render_charts).
    # We store the title text in layout.meta as a plain string so the renderer can
    # extract it.  title="" suppresses Plotly's built-in title.
    base = dict(
        title="",
        meta=title or "",
        template="plotly_white",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(color=COLORS["text"], family="Inter, Arial, sans-serif", size=11),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=COLORS["grid"], font_color=COLORS["text"], font_size=12),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=True,
            linewidth=1,
            linecolor=COLORS["grid"],
            tickfont=dict(size=10),
            tickangle=-45,
            automargin=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor=COLORS["grid"],
            zeroline=False,
            showline=False,
            tickfont=dict(size=10),
            automargin=True,
        ),
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10),
        ),
        autosize=True,
        height=height,
        dragmode=False,
    )
    base.update(overrides)
    return base


def _empty_fig(msg: str = "No data available") -> go.Figure:
    """Return a placeholder figure when data is missing."""
    fig = go.Figure()
    fig.add_annotation(
        text=msg,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=COLORS["muted"]),
    )
    fig.update_layout(**_layout("", height=300))
    return fig



def _x(df: pd.DataFrame) -> list:
    """Return a list of period labels from the DataFrame index."""
    return df.index.astype(str).tolist()


# ---------------------------------------------------------------------------
# Income Statement charts
# ---------------------------------------------------------------------------

def create_income_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar – auto-adapts title & legend based on available columns."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    traces: List[Tuple[str, str]] = [
        ("Revenue", COLORS["blue"]),
        ("Gross Profit", COLORS["yellow"]),
        ("Operating Income", COLORS["red"]),
        ("Net Income", COLORS["green"]),
    ]
    fig = go.Figure()
    present = []
    for col, color in traces:
        if col in df.columns and df[col].notna().any() and (df[col] != 0).any():
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
            present.append(col)
    # Build adaptive title from actually-present series
    if present:
        if len(present) <= 3:
            title = ", ".join(present)
        else:
            title = ", ".join(present[:-1]) + " and " + present[-1]
    else:
        title = "Income Statement"
    fig.update_layout(**_layout(title, barmode="group"))
    return fig


def create_margins_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart – auto-adapts title & legend based on available margin columns."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    traces = [
        ("Gross Margin %", COLORS["blue"]),
        ("Operating Margin %", COLORS["yellow"]),
        ("Net Margin %", COLORS["red"]),
    ]
    fig = go.Figure()
    present = []
    for col, color in traces:
        if col in df.columns and df[col].notna().any() and (df[col] != 0).any():
            fig.add_trace(go.Scatter(
                x=x, y=df[col], name=col, mode="lines+markers",
                line=dict(width=2.5, color=color),
                marker=dict(size=7, color=color),
            ))
            present.append(col.replace(" %", ""))
    # Build adaptive title
    if present:
        title = ", ".join(present) + " (%)"
    else:
        title = "Profit Margin (%)"
    fig.update_layout(**_layout(title))
    fig.update_yaxes(ticksuffix="%")
    # Cap y-axis when margins are extreme (e.g. -100,000% distorts the chart)
    _all_vals = []
    for col, _ in traces:
        if col in df.columns:
            _all_vals.extend(df[col].dropna().tolist())
    if _all_vals:
        _mn, _mx = min(_all_vals), max(_all_vals)
        if _mn < -500 or _mx > 500:
            _capped_min = max(_mn, -500)
            _capped_max = min(_mx, 500)
            fig.update_yaxes(range=[_capped_min - 20, _capped_max + 20])
    return fig


def create_eps_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar – Earnings Per Share (Basic & Diluted)."""
    if df.empty or ("EPS" not in df.columns and "EPS Diluted" not in df.columns):
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    if "EPS" in df.columns:
        fig.add_trace(go.Bar(x=x, y=df["EPS"], name="EPS (Basic)", marker_color=COLORS["blue"]))
    if "EPS Diluted" in df.columns:
        fig.add_trace(go.Bar(x=x, y=df["EPS Diluted"], name="EPS (Diluted)", marker_color=COLORS["yellow"]))
    fig.update_layout(**_layout("Earnings Per Share (EPS)", barmode="group"))
    fig.update_yaxes(tickprefix="$")
    return fig


def create_revenue_yoy_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart – Revenue year-over-year growth %."""
    if df.empty or "Revenue YoY Growth %" not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=df["Revenue YoY Growth %"], name="Revenue YoY Variation",
        mode="lines+markers",
        line=dict(width=3, color=COLORS["blue"]),
        marker=dict(size=8, color=COLORS["blue"]),
    ))
    fig.update_layout(**_layout("Revenue YoY Variation (%)"))
    fig.update_yaxes(ticksuffix="%")
    return fig


def create_opex_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked bar – R&D + SGA expenses."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for col, color in [("R&D Expenses", COLORS["blue"]), ("SGA Expenses", COLORS["yellow"])]:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Operating Expenses", barmode="stack"))
    return fig


def create_ebitda_chart(df: pd.DataFrame) -> go.Figure:
    """Single bar – EBITDA."""
    if df.empty or "EBITDA" not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df["EBITDA"], name="EBITDA", marker_color=COLORS["blue"]))
    fig.update_layout(**_layout("EBITDA"))
    return fig


def create_interest_income_chart(df: pd.DataFrame) -> go.Figure:
    """Bar – Interest Expense."""
    col = "Interest Expense"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df[col], name=col, marker_color=COLORS["green"]))
    fig.update_layout(**_layout("Interest and Other Income"))
    return fig


def create_tax_chart(df: pd.DataFrame) -> go.Figure:
    """Bar – Income Tax Expense."""
    col = "Income Tax Expense"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df[col], name=col, marker_color=COLORS["red"]))
    fig.update_layout(**_layout("Income Tax Expense"))
    return fig


def create_income_breakdown_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar – Operating Income, Interest Income, Other Income/Expenses, Net Income."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    traces = [
        ("Operating Income", COLORS["blue"]),
        ("Interest Income", COLORS["yellow"]),
        ("Total Other Income Expenses Net", COLORS["red"]),
        ("Net Income", COLORS["green"]),
    ]
    fig = go.Figure()
    for col, color in traces:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Income Breakdown", barmode="group"))
    return fig


def create_per_share_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar – Revenue / Net Income / Operating CF per share."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    traces = [
        ("Revenue Per Share", COLORS["blue"]),
        ("Operating Cash Flow Per Share", COLORS["red"]),
        ("Net Income Per Share", COLORS["yellow"]),
    ]
    fig = go.Figure()
    for col, color in traces:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Per Share Metrics", barmode="group"))
    fig.update_yaxes(tickprefix="$")
    return fig


# ---------------------------------------------------------------------------
# Revenue Segmentation charts
# ---------------------------------------------------------------------------

def create_revenue_by_product_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked bar – Revenue breakdown by product/operating segment."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        fig.add_trace(go.Bar(
            x=x, y=df[col], name=col,
            marker_color=PALETTE[i % len(PALETTE)],
        ))
    fig.update_layout(**_layout("Revenue by Product", barmode="stack"))
    return fig


def create_revenue_by_geography_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked bar – Revenue breakdown by geographic region."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        fig.add_trace(go.Bar(
            x=x, y=df[col], name=col,
            marker_color=PALETTE[i % len(PALETTE)],
        ))
    fig.update_layout(**_layout("Revenue by Geography", barmode="stack"))
    return fig


# ---------------------------------------------------------------------------
# Cash Flow charts
# ---------------------------------------------------------------------------

def create_cash_flow_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar – Operating / Investing / Financing / Free cash flow."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    traces = [
        ("Operating CF", COLORS["blue"]),
        ("Investing CF", COLORS["red"]),
        ("Financing CF", COLORS["yellow"]),
        ("Free CF", COLORS["green"]),
    ]
    fig = go.Figure()
    for col, color in traces:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Cash Flows", barmode="group"))
    return fig


def create_cash_position_chart(df: pd.DataFrame) -> go.Figure:
    """Single bar – Cash and Cash Equivalents."""
    col = "Cash and Cash Equivalents"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df[col], name="Cash At End Of Period", marker_color=COLORS["blue"]))
    fig.update_layout(**_layout("Cash Position"))
    return fig


def create_capex_chart(df: pd.DataFrame) -> go.Figure:
    """Bar – Capital Expenditure."""
    col = "CapEx"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df[col].abs(), name="CapEx", marker_color=COLORS["purple"]))
    fig.update_layout(**_layout("Capital Expenditure"))
    return fig


# ---------------------------------------------------------------------------
# Balance Sheet charts
# ---------------------------------------------------------------------------

def create_assets_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked bar – Current + Non-Current Assets."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for col, color in [("Current Assets", COLORS["blue"]), ("Non-Current Assets", COLORS["yellow"])]:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Total Assets", barmode="stack"))
    return fig


def create_liabilities_chart(df: pd.DataFrame) -> go.Figure:
    """Stacked bar – Current + Non-Current Liabilities."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for col, color in [
        ("Current Liabilities", COLORS["red"]),
        ("Non-Current Liabilities", COLORS["yellow"]),
    ]:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Liabilities", barmode="stack"))
    return fig


def create_equity_debt_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar – Stockholders Equity vs Total Debt."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for col, color in [
        ("Stockholders Equity", COLORS["green"]),
        ("Total Debt", COLORS["red"]),
    ]:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Stockholders Equity vs Total Debt", barmode="group"))
    return fig


# ---------------------------------------------------------------------------
# Key Metrics charts (single-value time-series)
# ---------------------------------------------------------------------------

def create_pe_chart(df: pd.DataFrame) -> go.Figure:
    """Line – P/E Ratio over time (computed from EPS + price)."""
    col = "P/E Ratio"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Scatter(
        x=x, y=df[col], name="P/E", mode="lines+markers",
        line=dict(width=3, color=COLORS["purple"]),
        marker=dict(size=8, color=COLORS["purple"]),
    ))
    fig.update_layout(**_layout("P/E Ratio"))
    fig.update_yaxes(ticksuffix="x")
    return fig


def create_market_cap_chart(df: pd.DataFrame) -> go.Figure:
    """Bar — Market Capitalization as a time series.

    Task #36 Phase 2 upgrade: was a single-value scalar bar; now renders
    the full period-end Market Cap column (close × shares, computed in
    app.py's Key Metrics block from fetch_period_end_closes).
    """
    col = "Market Cap"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df[col], name="Market Cap",
                           marker_color=COLORS["blue"]))
    fig.update_layout(**_layout("Market Capitalization"))
    fig.update_yaxes(tickprefix="$")
    return fig


def _create_ratio_line(df: pd.DataFrame, col: str, title: str, color_key: str = "blue") -> go.Figure:
    """Internal — line chart with `x` suffix for valuation-ratio series."""
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Scatter(
        x=x, y=df[col], name=col, mode="lines+markers",
        line=dict(width=3, color=COLORS[color_key]),
        marker=dict(size=8, color=COLORS[color_key]),
    ))
    fig.update_layout(**_layout(title))
    fig.update_yaxes(ticksuffix="x")
    return fig


def create_ps_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Price / Sales ratio."""
    return _create_ratio_line(df, "P/S", "Price / Sales", "blue")


def create_pocf_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Price / Operating Cash Flow ratio."""
    return _create_ratio_line(df, "P/OCF", "Price / Operating CF", "green")


def create_pfcf_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Price / Free Cash Flow ratio."""
    return _create_ratio_line(df, "P/FCF", "Price / Free Cash Flow", "yellow")


def create_pb_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Price / Book ratio."""
    return _create_ratio_line(df, "P/B", "Price / Book", "purple")


def create_ptb_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Price / Tangible Book ratio."""
    return _create_ratio_line(df, "P/TB", "Price / Tangible Book", "teal")


def create_dividend_yield_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Dividend Yield % (TTM dividends / period-end price)."""
    col = "Dividend Yield %"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Scatter(
        x=x, y=df[col], name="Dividend Yield", mode="lines+markers",
        line=dict(width=3, color=COLORS["green"]),
        marker=dict(size=8, color=COLORS["green"]),
    ))
    fig.update_layout(**_layout("Dividend Yield (%)"))
    fig.update_yaxes(ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Key Metrics — Group C charts (Task #36 Phase 3)
# ---------------------------------------------------------------------------

def create_roic_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Return on Invested Capital."""
    col = "ROIC %"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Scatter(
        x=x, y=df[col], name="ROIC", mode="lines+markers",
        line=dict(width=3, color=COLORS["teal"]),
        marker=dict(size=8, color=COLORS["teal"]),
    ))
    fig.update_layout(**_layout("Return on Invested Capital (%)"))
    fig.update_yaxes(ticksuffix="%")
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(128,128,128,0.4)")
    return fig


def create_turnover_not_applicable_fig() -> go.Figure:
    """Titled placeholder for the Turnover slot when the ticker is a bank
    or insurer (Task #36 C4 sector-gating).

    `render_charts` in app.py explicitly filters out figures that have no
    data traces — an annotation-only figure would be silently dropped
    from the grid. To keep the cell visible we add a 1-point invisible
    scatter so `fig.data` passes the has-data check, and overlay a
    centered "Not applicable for this sector" message.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(size=0, color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.add_annotation(
        text="Not applicable for this sector",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=COLORS["muted"]),
    )
    fig.update_layout(**_layout("Turnover & Efficiency (days)"))
    fig.update_yaxes(visible=False, range=[-1, 1])
    fig.update_xaxes(visible=False, range=[-1, 1])
    return fig


def create_turnover_efficiency_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar — DSO / DPO / DIO turnover days.

    Caller is responsible for NOT calling this when
    ``info_data.is_turnover_applicable(sector)`` returns False — for
    banks and insurers the Turnover panel is replaced with
    ``create_turnover_not_applicable_fig()`` upstream in ``app.py``.
    """
    if df.empty:
        return _empty_fig()
    traces = [
        ("DSO", COLORS["blue"]),
        ("DPO", COLORS["yellow"]),
        ("DIO", COLORS["red"]),
    ]
    # Require at least one of the three columns to be non-empty.
    if not any(c in df.columns and df[c].notna().any() for c, _ in traces):
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for col, color in traces:
        if col in df.columns and df[col].notna().any():
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Turnover & Efficiency (days)"))
    fig.update_yaxes(ticksuffix=" d")
    fig.update_layout(barmode="group")
    return fig


# ---------------------------------------------------------------------------
# Additional Income Statement charts (15 total)
# ---------------------------------------------------------------------------

def create_qoq_revenue_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart – Quarter-over-Quarter revenue growth %."""
    if df.empty or "QoQ Revenue Growth %" not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=df["QoQ Revenue Growth %"], name="Revenue Variation",
        mode="lines+markers",
        line=dict(width=3, color=COLORS["blue"]),
        marker=dict(size=8, color=COLORS["blue"]),
    ))
    fig.update_layout(**_layout("QoQ Revenue Variation (%)"))
    fig.update_yaxes(ticksuffix="%")
    return fig


def create_sbc_chart(df: pd.DataFrame) -> go.Figure:
    """Bar – Stock Based Compensation."""
    col = "Stock Based Compensation"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df[col], name="SBC", marker_color=COLORS["purple"]))
    fig.update_layout(**_layout("Stock Based Compensation"))
    return fig


def create_shares_chart(df: pd.DataFrame) -> go.Figure:
    """Grouped bar – Weighted Average Shares Outstanding (Basic & Diluted)."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    for col, color in [
        ("Basic Average Shares", COLORS["blue"]),
        ("Diluted Average Shares", COLORS["yellow"]),
    ]:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Weighted Average Shares Outstanding", barmode="group"))
    return fig


def create_expense_ratios_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart – R&D/Revenue, Capex/Revenue, SBC/Revenue expense ratios."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    traces = [
        ("R&D to Revenue", COLORS["blue"]),
        ("Capex to Revenue", COLORS["yellow"]),
        ("SBC to Revenue", COLORS["red"]),
    ]
    fig = go.Figure()
    for col, color in traces:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=x, y=df[col], name=col, mode="lines+markers",
                line=dict(width=2.5, color=color),
                marker=dict(size=7, color=color),
            ))
    fig.update_layout(**_layout("Expense Ratios"))
    return fig


def create_effective_tax_rate_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart – Effective Tax Rate %."""
    col = "Effective Tax Rate %"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=df[col], name="Effective Tax Rate",
        mode="lines+markers",
        line=dict(width=3, color=COLORS["red"]),
        marker=dict(size=8, color=COLORS["red"]),
    ))
    fig.update_layout(**_layout("Effective Tax Rate (%)"))
    fig.update_yaxes(ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Analyst Forecast chart
# ---------------------------------------------------------------------------

def create_analyst_forecast_chart(forecast: Dict[str, Any]) -> go.Figure:
    """Create a visual representation of analyst price targets."""
    if not forecast or "target_mean" not in forecast:
        return _empty_fig("No analyst forecast data available")

    current = forecast.get("current_price", 0)
    mean = forecast.get("target_mean", 0)
    high = forecast.get("target_high", 0)
    low = forecast.get("target_low", 0)

    fig = go.Figure()

    # Range bar
    fig.add_trace(go.Bar(
        x=["Price Target"],
        y=[high - low],
        base=[low],
        name="Target Range",
        marker_color="rgba(66,133,244,0.3)",
        width=0.4,
    ))

    # Current price line
    fig.add_hline(y=current, line_dash="dash", line_color=COLORS["yellow"],
                  annotation_text=f"Current: ${current:.2f}")

    # Mean target
    fig.add_hline(y=mean, line_dash="dot", line_color=COLORS["green"],
                  annotation_text=f"Mean Target: ${mean:.2f}")

    fig.update_layout(**_layout("Analyst Price Targets", height=350))
    fig.update_yaxes(tickprefix="$")
    return fig


# ---------------------------------------------------------------------------
# Key Metrics — Group A charts (Task #36 Phase 1)
# ---------------------------------------------------------------------------
# All six charts below consume the DataFrame produced by
# ``info_data.compute_key_metrics_group_a``. Each picks its own column
# out of that wide frame and renders a bar or line in the standard
# _layout(). Colors reuse the existing ``COLORS`` palette to stay visually
# consistent with the income/cashflow/balance chart groups.

def create_shares_variation_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart — Shares YoY % + (optional) Net Buyback Yield TTM %.

    Two series, same axis. Phase 1 renders just the blue ``Shares YoY %``
    line. Phase 2 (Task #36 Commit 3) also passes a
    ``Net Buyback Yield TTM %`` column — we trace that in yellow when
    present, skip when absent. Same pattern as ``create_margins_chart``.
    """
    if df.empty:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure()
    traces = [
        ("Shares YoY %", COLORS["blue"]),
        ("Net Buyback Yield TTM %", COLORS["yellow"]),
    ]
    any_present = False
    for col, color in traces:
        if col in df.columns and df[col].notna().any():
            fig.add_trace(go.Scatter(
                x=x, y=df[col], name=col, mode="lines+markers",
                line=dict(width=2.5, color=color),
                marker=dict(size=7, color=color),
            ))
            any_present = True
    if not any_present:
        return _empty_fig()
    fig.update_layout(**_layout("Shares Variation (%)"))
    fig.update_yaxes(ticksuffix="%")
    # Zero-line reference makes dilution vs buyback visually obvious.
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(128,128,128,0.4)")
    return fig


def create_bvps_chart(df: pd.DataFrame) -> go.Figure:
    """Bar — Book Value Per Share."""
    col = "BVPS"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(
        x=x, y=df[col], name=col, marker_color=COLORS["blue"],
    ))
    fig.update_layout(**_layout("Book Value Per Share"))
    fig.update_yaxes(tickprefix="$")
    return fig


def create_cash_per_share_chart(df: pd.DataFrame) -> go.Figure:
    """Bar — Cash & Equivalents Per Share."""
    col = "Cash/Share"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(
        x=x, y=df[col], name=col, marker_color=COLORS["green"],
    ))
    fig.update_layout(**_layout("Cash Per Share"))
    fig.update_yaxes(tickprefix="$")
    return fig


def create_fcf_per_share_chart(df: pd.DataFrame) -> go.Figure:
    """Bar — Free Cash Flow Per Share."""
    col = "FCF/Share"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(
        x=x, y=df[col], name=col, marker_color=COLORS["yellow"],
    ))
    fig.update_layout(**_layout("Free Cash Flow Per Share"))
    fig.update_yaxes(tickprefix="$")
    return fig


def create_roe_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Return on Equity as a time series."""
    col = "ROE %"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Scatter(
        x=x, y=df[col], name="ROE", mode="lines+markers",
        line=dict(width=3, color=COLORS["purple"]),
        marker=dict(size=8, color=COLORS["purple"]),
    ))
    fig.update_layout(**_layout("Return on Equity (%)"))
    fig.update_yaxes(ticksuffix="%")
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(128,128,128,0.4)")
    return fig


def create_graham_chart(df: pd.DataFrame) -> go.Figure:
    """Line — Graham Number = √(22.5 × EPS × BVPS), intrinsic-value anchor."""
    col = "Graham Number"
    if df.empty or col not in df.columns or not df[col].notna().any():
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Scatter(
        x=x, y=df[col], name="Graham #", mode="lines+markers",
        line=dict(width=3, color=COLORS["orange"]),
        marker=dict(size=8, color=COLORS["orange"]),
    ))
    fig.update_layout(**_layout("Graham Number"))
    fig.update_yaxes(tickprefix="$")
    return fig
