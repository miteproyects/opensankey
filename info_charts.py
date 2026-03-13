"""
Info charts module for Open Sankey.

Creates Plotly charts for company profile/info page:
- Ownership splits (pie chart)
- Institutional holdings (horizontal bar chart)
- Insider trading activity (grouped bar chart)

All charts use the same color palette and light finance theme as charts.py.
"""

from typing import Dict, Any, List
import plotly.graph_objects as go
from charts import COLORS, _layout, _empty_fig


# ---------------------------------------------------------------------------
# Ownership charts
# ---------------------------------------------------------------------------

def create_ownership_pie(
    insider_pct: float,
    institutional_pct: float,
    public_pct: float,
    company_name: str,
) -> go.Figure:
    """
    Create a pie chart showing ownership split.

    Args:
        insider_pct: Percentage of shares held by insiders
        institutional_pct: Percentage of shares held by institutions
        public_pct: Percentage of shares held by public
        company_name: Name of the company for the title

    Returns:
        go.Figure: Pie chart figure
    """
    # Validate data
    if (insider_pct is None or institutional_pct is None or
            public_pct is None or not company_name):
        return _empty_fig("No ownership data available")

    # Check if percentages sum to ~100
    total = insider_pct + institutional_pct + public_pct
    if total == 0:
        return _empty_fig("No ownership data available")

    labels = ["Institutional", "Insider", "Public"]
    # Convert to percentage if values are in decimal form (< 1.0)
    if total <= 1.1:  # Likely decimal form
        values = [institutional_pct * 100, insider_pct * 100, public_pct * 100]
    else:
        values = [institutional_pct, insider_pct, public_pct]
    colors = [COLORS["blue"], COLORS["yellow"], COLORS["green"]]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors, line=dict(color=COLORS["bg"], width=2)),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    )])

    fig.update_layout(**_layout(
        f"{company_name} Ownership Split",
        height=400,
        hovermode="closest",
        showlegend=True,
    ))

    return fig


# ---------------------------------------------------------------------------
# Institutional holdings chart
# ---------------------------------------------------------------------------

def create_institutional_bar(holders: List[Dict[str, Any]]) -> go.Figure:
    """
    Create a horizontal bar chart of top institutional holders.

    Args:
        holders: List of dicts with 'name' and 'pct_held' keys.
                 Example: [{"name": "Vanguard", "pct_held": 7.5}, ...]

    Returns:
        go.Figure: Horizontal bar chart figure
    """
    if not holders or len(holders) == 0:
        return _empty_fig("No institutional holding data available")

    # Sort by pct_held descending
    sorted_holders = sorted(holders, key=lambda x: x.get("pct_held", 0), reverse=True)

    names = [h.get("name", "Unknown") for h in sorted_holders]
    raw_pcts = [h.get("pct_held", 0) for h in sorted_holders]
    # Convert to percentage if in decimal form
    pcts = [p * 100 if p < 1.0 else p for p in raw_pcts]

    fig = go.Figure(go.Bar(
        y=names,
        x=pcts,
        orientation="h",
        marker=dict(color=COLORS["blue"]),
        text=[f"{pct:.2f}%" for pct in pcts],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:.2f}%<extra></extra>",
    ))

    fig.update_layout(**_layout(
        "Percentage Held by Institution",
        height=400,
        margin=dict(l=150, r=140, t=55, b=45),
    ))

    fig.update_xaxes(ticksuffix="%")

    return fig


# ---------------------------------------------------------------------------
# Insider trading activity chart
# ---------------------------------------------------------------------------

def create_insider_activity_chart(monthly_data: List[Dict[str, Any]]) -> go.Figure:
    """
    Create a grouped bar chart showing monthly insider buying vs selling.

    Args:
        monthly_data: List of dicts with 'month', 'bought', 'sold' keys.
                      Example: [{"month": "2024-01", "bought": 100, "sold": 50}, ...]

    Returns:
        go.Figure: Grouped bar chart figure
    """
    if not monthly_data or len(monthly_data) == 0:
        return _empty_fig("No insider trading data available")

    months = [d.get("month", "") for d in monthly_data]
    bought = [d.get("bought", 0) for d in monthly_data]
    sold = [d.get("sold", 0) for d in monthly_data]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=months,
        y=bought,
        name="Share Bought",
        marker=dict(color=COLORS["green"]),
        hovertemplate="<b>%{x}</b><br>Bought: %{y:,}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=months,
        y=sold,
        name="Share Sold",
        marker=dict(color=COLORS["red"]),
        hovertemplate="<b>%{x}</b><br>Sold: %{y:,}<extra></extra>",
    ))

    fig.update_layout(**_layout(
        "Monthly Insider Trading Activity",
        height=400,
        barmode="group",
    ))

    return fig
