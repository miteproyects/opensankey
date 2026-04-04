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

def _layout(title: str, height: int = 450, **overrides) -> Dict[str, Any]:
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
            automargin=False,
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
        margin=dict(l=10, r=10, t=10, b=70),
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
    """Grouped bar – Revenue, Gross Profit, Operating Income, Net Income."""
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
    for col, color in traces:
        if col in df.columns:
            fig.add_trace(go.Bar(x=x, y=df[col], name=col, marker_color=color))
    fig.update_layout(**_layout("Revenue, Gross Profit, Operating and Net Income", barmode="group"))
    return fig


def create_margins_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart – Gross / Operating / Net margin %."""
    if df.empty:
        return _empty_fig()
    x = _x(df)
    traces = [
        ("Gross Margin %", COLORS["blue"]),
        ("Operating Margin %", COLORS["yellow"]),
        ("Net Margin %", COLORS["red"]),
    ]
    fig = go.Figure()
    for col, color in traces:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=x, y=df[col], name=col, mode="lines+markers",
                line=dict(width=2.5, color=color),
                marker=dict(size=7, color=color),
            ))
    fig.update_layout(**_layout("Gross, Operating and Net Profit Margin (%)"))
    fig.update_yaxes(ticksuffix="%")
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
    """Bar – Market Capitalisation."""
    col = "Market Cap"
    if df.empty or col not in df.columns:
        return _empty_fig()
    x = _x(df)
    fig = go.Figure(go.Bar(x=x, y=df[col], name="Market Cap", marker_color=COLORS["blue"]))
    fig.update_layout(**_layout("Market Capitalization"))
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
