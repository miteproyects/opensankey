"""
Profile page rendering module for Quarter Charts.

Exports a single function `render_profile_page(ticker: str)` that renders
the complete company profile/info page using Streamlit.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from info_data import (
    get_company_description,
    get_fundamentals,
    get_technicals,
    get_dcf_data,
    get_ownership_data,
    get_insider_trades,
    calculate_dcf,
    get_score,
    get_company_icon,
)
from info_charts import (
    create_ownership_pie,
    create_institutional_bar,
    create_insider_activity_chart,
)
from charts import COLORS


# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────


def _fmt_currency(val: Optional[float]) -> str:
    """Format a number as currency."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    try:
        val = float(val)
        if val >= 1e12:
            return f"${val / 1e12:.2f}T"
        elif val >= 1e9:
            return f"${val / 1e9:.2f}B"
        elif val >= 1e6:
            return f"${val / 1e6:.2f}M"
        elif val >= 1e3:
            return f"${val / 1e3:.2f}K"
        else:
            return f"${val:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _fmt_pct(val: Optional[float], decimals: int = 2) -> str:
    """Format a number as percentage."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    try:
        return f"{float(val) * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def _color_for_value(val: Optional[float], is_growth: bool = False) -> str:
    """Return color (green/red/blue) based on value polarity."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return COLORS.get("blue", "#2475fc")

    try:
        val = float(val)
        if is_growth:
            return COLORS.get("green", "#34a853") if val >= 0 else COLORS.get("red", "#ea4335")
        else:
            return COLORS.get("green", "#34a853") if val > 0 else COLORS.get("red", "#ea4335")
    except (ValueError, TypeError):
        return COLORS.get("blue", "#2475fc")


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_candlestick_data(ticker: str, period: str = "3mo") -> Optional[pd.DataFrame]:
    """Fetch OHLCV candlestick data from Yahoo Finance."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period)
        if hist is not None and not hist.empty:
            hist = hist.reset_index()
            return hist
    except Exception as e:
        print(f"[profile] _fetch_candlestick_data({ticker}): {e}")
    return None


def _fetch_candlestick_chart(ticker: str, period: str = "3mo") -> Optional[go.Figure]:
    """Build a TradingView-style candlestick + volume chart from cached data.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol.
    period : str
        yfinance period string (1d, 5d, 1mo, 3mo, 6mo, ytd, 1y, 5y, max).
    """
    hist = _fetch_candlestick_data(ticker, period)
    if hist is None:
        return None

    try:
        # Normalize date column name (can be "Date" or "Datetime")
        date_col = "Datetime" if "Datetime" in hist.columns else "Date"

        # Build subplots: candlestick on top (80%), volume on bottom (20%)
        from plotly.subplots import make_subplots
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.78, 0.22],
        )

        # Candlestick trace
        fig.add_trace(go.Candlestick(
            x=hist[date_col],
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            increasing_line_color="#26a69a",   # green
            decreasing_line_color="#ef5350",   # red
            increasing_fillcolor="#26a69a",
            decreasing_fillcolor="#ef5350",
            name="Price",
            showlegend=False,
        ), row=1, col=1)

        # Volume bars colored by direction
        colors = [
            "rgba(38, 166, 154, 0.5)" if c >= o else "rgba(239, 83, 80, 0.5)"
            for o, c in zip(hist["Open"], hist["Close"])
        ]
        fig.add_trace(go.Bar(
            x=hist[date_col],
            y=hist["Volume"],
            marker_color=colors,
            name="Volume",
            showlegend=False,
        ), row=2, col=1)

        # Get latest price info for header
        latest = hist.iloc[-1]
        prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else latest["Open"]
        change = latest["Close"] - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        change_color = "#26a69a" if change >= 0 else "#ef5350"
        sign = "+" if change >= 0 else ""

        title_text = (
            f"<b>{ticker}</b>  "
            f"O <span style='color:#999'>{latest['Open']:.2f}</span>  "
            f"H <span style='color:#999'>{latest['High']:.2f}</span>  "
            f"L <span style='color:#999'>{latest['Low']:.2f}</span>  "
            f"C <span style='color:{change_color}'>{latest['Close']:.2f}</span>  "
            f"<span style='color:{change_color}'>{sign}{change:.2f} ({sign}{change_pct:.2f}%)</span>"
        )

        fig.update_layout(
            title=dict(text=title_text, font=dict(size=13), x=0.01, y=0.98),
            template="plotly_white",
            height=500,
            hovermode="x unified",
            margin=dict(l=60, r=60, t=45, b=30),
            font=dict(family="Inter, sans-serif", size=11, color="#212529"),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            xaxis_rangeslider_visible=False,
            xaxis2=dict(showgrid=False),
            yaxis=dict(
                showgrid=True, gridwidth=1, gridcolor="#f0f0f0",
                side="right", title="",
            ),
            yaxis2=dict(
                showgrid=False, side="right", title="",
            ),
            dragmode="pan",
        )

        # Remove weekend gaps for daily/weekly data
        if period in ("1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y"):
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

        return fig
    except Exception as exc:
        print(f"[profile_page] _fetch_candlestick_chart({ticker}): {exc}")
        return None


# ───────────────────────────────────────────────────────────────────────────
# Main render function
# ───────────────────────────────────────────────────────────────────────────


def render_profile_page(ticker: str) -> None:
    """Render the complete company profile page.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol (e.g., "NVDA", "AAPL").
    """
    ticker = ticker.upper().strip()

    # -- Profile-specific responsive CSS --
    st.markdown("""<style>
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"]:has([class*="st-key-period_"]) { flex-wrap: wrap !important; gap: 4px !important; }
        [data-testid="stHorizontalBlock"]:has([class*="st-key-period_"]) [data-testid="stColumn"] { flex: 0 0 30% !important; max-width: 30% !important; }
        table { font-size: 0.82rem !important; }
        td, th { padding: 6px 4px !important; }
    }
    @media (max-width: 480px) {
        [data-testid="stHorizontalBlock"]:has([class*="st-key-period_"]) [data-testid="stColumn"] { flex: 0 0 30% !important; }
    }
    </style>""", unsafe_allow_html=True)
    st.markdown('<style>.stForm { margin-top: 2px !important; }</style>', unsafe_allow_html=True)

    # Fetch all data in PARALLEL (EDGAR for financials, YF for market data)
    with ThreadPoolExecutor(max_workers=10) as pool:
        fut_company   = pool.submit(get_company_description, ticker)
        fut_fund      = pool.submit(get_fundamentals, ticker)
        fut_tech      = pool.submit(get_technicals, ticker)
        fut_dcf       = pool.submit(get_dcf_data, ticker)
        fut_own       = pool.submit(get_ownership_data, ticker)
        fut_insider   = pool.submit(get_insider_trades, ticker)
        fut_score     = pool.submit(get_score, ticker)
        fut_candle    = pool.submit(_fetch_candlestick_data, ticker, "3mo")

    company_data   = fut_company.result()
    fundamentals   = fut_fund.result()
    technicals     = fut_tech.result()
    dcf_data       = fut_dcf.result()
    ownership_data = fut_own.result()
    insider_trades = fut_insider.result()
    score          = fut_score.result()
    candle_data    = fut_candle.result()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Company Header
    # ─────────────────────────────────────────────────────────────────────────

    name = company_data.get("name", ticker)
    current_price = company_data.get("price")
    market_cap = company_data.get("market_cap")

    # Calculate fair value from DCF
    fair_value = None
    upside_pct = None
    if dcf_data and current_price:
        # Calculate DCF with default growth rates for the header
        _fcf = dcf_data.get("current_fcf", 0)
        _gr = dcf_data.get("fcf_growth_rates", [0.08]*5)
        _tg = dcf_data.get("terminal_growth_rate", 0.04)
        _dr = dcf_data.get("discount_rate", 0.08)
        _so = dcf_data.get("shares_outstanding", 1)
        _nd = dcf_data.get("net_debt", 0)
        if _fcf and _dr > _tg > 0:
            dcf_result = calculate_dcf(
                fcf=_fcf, growth_rates=_gr,
                terminal_growth=_tg, discount_rate=_dr,
                shares_outstanding=_so, net_debt=_nd,
            )
            if dcf_result and dcf_result > 0:
                fair_value = dcf_result
                upside_pct = ((fair_value - current_price) / current_price) * 100

    # Header layout: name+ticker | price | fair value+upside | score badge
    col1, col2, col3, col4 = st.columns([1.8, 1.8, 1.8, 1.2])

    with col1:
        logo_src = f"https://financialmodelingprep.com/image-stock/{ticker.upper()}.png"
        st.markdown(f'<div style="display:flex;flex-direction:column;align-items:center;gap:4px;"><img src="{logo_src}" style="width:80px;height:80px;border-radius:10px;object-fit:contain;background:#fff;padding:4px;box-shadow:0 1px 4px rgba(0,0,0,0.08);" onerror="this.style.display=\'none\'" alt="{ticker} logo"/><span style="font-size:1.4rem;font-weight:600;line-height:1.2;text-align:center;">{name} ({ticker})</span></div>', unsafe_allow_html=True)

    with col2:
        if current_price:
            st.markdown(f"""
            <div id="qc-price-container" data-ticker="{ticker}" data-prev-price="{current_price:.2f}" style="
                background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,250,252,0.9));
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 16px;
                padding: 14px 16px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
                backdrop-filter: blur(8px);
                transition: box-shadow 0.3s ease;
                overflow: hidden;
            ">
                <div style="font-size: 0.7rem; font-weight: 500; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">Live Price</div>
                <div id="qc-price-value" style="font-size: clamp(1.5rem, 3.5vw, 2rem); font-weight: 800; color: #0f172a; line-height: 1.1; letter-spacing: -0.02em; white-space: nowrap;">${current_price:.2f}</div>
                <div id="qc-change" style="font-size: 0.9rem; font-weight: 600; margin-top: 6px;"></div>
                <div id="qc-close-time" style="font-size: 0.65rem; color: #94a3b8; margin-top: 3px;"></div>
                <div id="qc-afterhours" style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.06); display: none;">
                    <div style="display: flex; align-items: baseline; gap: 8px;">
                        <div id="qc-ext-price" style="font-size: 1.1rem; font-weight: 700; color: #0f172a;"></div>
                        <div id="qc-ext-change" style="font-size: 0.8rem; font-weight: 600; white-space: nowrap;"></div>
                    </div>
                    <div id="qc-ext-time" style="font-size: 0.65rem; color: #94a3b8; margin-top: 2px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,250,252,0.9));
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 16px;
                padding: 18px 22px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.06);
                overflow: hidden;
            ">
                <div style="font-size: 0.7rem; font-weight: 500; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em;">Price</div>
                <div style="font-size: clamp(1.5rem, 3.5vw, 2rem); font-weight: 800; color: #0f172a; margin-top: 4px;">N/A</div>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        if fair_value and upside_pct is not None:
            upside_color = "#10b981" if upside_pct >= 0 else "#ef4444"
            arrow = "&#9650;" if upside_pct >= 0 else "&#9660;"
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,250,252,0.9));
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 16px;
                padding: 14px 16px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
                backdrop-filter: blur(8px);
                text-align: center;
                overflow: hidden;
            ">
                <div style="font-size: 0.7rem; font-weight: 500; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">Fair Value (DCF)</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">${fair_value:.2f}</div>
                <div style="
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    margin-top: 8px;
                    padding: 4px 12px;
                    border-radius: 20px;
                    background: {upside_color}15;
                    font-size: 0.85rem;
                    font-weight: 700;
                    color: {upside_color};
                ">
                    <span>{arrow}</span>
                    <span>{upside_pct:+.1f}% upside</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(248,250,252,0.9));
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 16px;
                padding: 18px 22px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.06);
                text-align: center;
                overflow: hidden;
            ">
                <div style="font-size: 0.7rem; font-weight: 500; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em;">Fair Value</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #0f172a; margin-top: 4px;">N/A</div>
            </div>
            """, unsafe_allow_html=True)

    with col4:
        # Score badge with SVG ring
        score_color = "#10b981" if score >= 70 else ("#f59e0b" if score >= 40 else "#ef4444")
        score_label = "Excellent" if score >= 70 else ("Good" if score >= 40 else "Low")
        score_bg = "#ecfdf5" if score >= 70 else ("#fffbeb" if score >= 40 else "#fef2f2")
        dash = score * 2.827
        st.markdown(f"""
        <style>
            @keyframes qc-score-fill {{ from {{ stroke-dasharray: 0 283; }} to {{ stroke-dasharray: {dash:.1f} 283; }} }}
            .qc-score-ring {{ animation: qc-score-fill 1.2s ease-out forwards; }}
            .qc-score-wrap:hover {{ transform: scale(1.05); }}
        </style>
        <a href="#score-section" title="{score_label} Score" style="text-decoration: none; display: block;">
        <div class="qc-score-wrap" style="
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            transition: transform 0.25s ease;
        ">
            <div style="position: relative; width: 100px; height: 100px;">
                <svg viewBox="0 0 100 100" style="transform: rotate(-90deg); width: 100%; height: 100%;">
                    <circle cx="50" cy="50" r="45" fill="{score_bg}" stroke="rgba(0,0,0,0.06)" stroke-width="6"/>
                    <circle class="qc-score-ring" cx="50" cy="50" r="45" fill="none" stroke="{score_color}" stroke-width="6" stroke-linecap="round" stroke-dasharray="0 283"/>
                </svg>
                <div style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    text-align: center;
                ">
                    <div style="font-size: 1.8rem; font-weight: 800; color: #0f172a; line-height: 1;">{score}</div>
                    <div style="font-size: 0.6rem; font-weight: 500; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">score</div>
                </div>
            </div>
            <div style="
                font-size: 0.7rem;
                font-weight: 600;
                color: {score_color};
                padding: 2px 10px;
                border-radius: 12px;
                background: {score_bg};
            ">{score_label}</div>
        </div>
        </a>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Candlestick Chart (TradingView-style)
    # ─────────────────────────────────────────────────────────────────────────

    # Period selector row
    period_labels = ["1D", "5D", "1M", "3M", "6M", "YTD", "1Y", "5Y", "All"]
    period_values = ["1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "5y", "max"]

    # Use session state for selected period
    if "chart_period" not in st.session_state:
        st.session_state.chart_period = "3mo"

    period_cols = st.columns(len(period_labels))
    for i, (label, value) in enumerate(zip(period_labels, period_values)):
        with period_cols[i]:
            is_selected = st.session_state.chart_period == value
            if st.button(
                label, key=f"period_{value}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.chart_period = value
                st.rerun()

    # Render the candlestick chart
    candle_fig = _fetch_candlestick_chart(ticker, st.session_state.chart_period)
    if candle_fig:
        st.plotly_chart(candle_fig, use_container_width=True, config={
            "displayModeBar": "hover",
            "displaylogo": False,
            "modeBarButtons": [["toImage"]],
        })
    else:
        st.info(f"Could not fetch stock price data for {ticker}.")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Description / Shares Tabs
    # ─────────────────────────────────────────────────────────────────────────

    desc_tab, shares_tab = st.tabs(["Description", "Shares"])

    with desc_tab:
        # Company description
        description = company_data.get("description", "")
        if description:
            with st.expander("Company Description", expanded=False):
                st.write(description)

        # Company info table (2-column layout)
        col_l, col_r = st.columns(2)

        company_info = {
            "Market Cap": _fmt_currency(market_cap),
            "Exchange": company_data.get("exchange", "N/A"),
            "Sector": company_data.get("sector", "N/A"),
            "Industry": company_data.get("industry", "N/A"),
            "Country": company_data.get("country", "N/A"),
            "CEO": company_data.get("ceo", "N/A"),
            "IPO Date": company_data.get("ipo_date", "N/A"),
            "CAGR": f"{company_data.get('cagr'):.2f}%" if company_data.get('cagr') else "N/A",
            "Employees": f"{company_data.get('employees'):,}" if company_data.get('employees') else "N/A",
            "Website": company_data.get("website", "N/A"),
            "Div. Yield": _fmt_pct(company_data.get("div_yield")),
            "Payout Ratio": _fmt_pct(company_data.get("payout_ratio")),
        }

        items = list(company_info.items())
        mid = len(items) // 2

        with col_l:
            for label, value in items[:mid]:
                st.markdown(f"**{label}:** {value}")

        with col_r:
            for label, value in items[mid:]:
                st.markdown(f"**{label}:** {value}")

    with shares_tab:
        st.markdown("#### Share Price History")
        st.caption("Use the candlestick chart above with period selectors to explore price data.")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Fundamentals / Technicals Tabs
    # ─────────────────────────────────────────────────────────────────────────

    fund_tab, tech_tab = st.tabs(["Fundamentals", "Technicals"])

    with fund_tab:
        # Fundamentals grid: label-left / value-right in table rows
        if fundamentals and len(fundamentals) > 0:
            # Build HTML table with 4 columns, each cell = label left + value right
            html_rows = ""
            for row_idx, row in enumerate(fundamentals):
                cells = ""
                for label, value, color in row:
                    # Map color names to hex
                    color_map = {"green": "#34a853", "red": "#ea4335", "blue": "#333"}
                    hex_color = color_map.get(color, color if color.startswith("#") else "#333")
                    cells += f"""
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.82rem; color: #555; font-weight: 500;">{label}</span>
                            <span style="font-size: 0.88rem; font-weight: 700; color: {hex_color};">{value}</span>
                        </div>
                    </td>"""
                html_rows += f"<tr>{cells}</tr>"

            st.markdown(f"""
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">
                {html_rows}
            </table>
            """, unsafe_allow_html=True)
        else:
            st.info("No fundamental metrics available.")

    with tech_tab:
        # Technicals grid: same label-left / value-right table design
        if technicals and len(technicals) > 0:
            html_rows = ""
            for row_idx, row in enumerate(technicals):
                cells = ""
                for label, value, color in row:
                    color_map = {"green": "#34a853", "red": "#ea4335", "blue": "#333"}
                    hex_color = color_map.get(color, color if color.startswith("#") else "#333")
                    cells += f"""
                    <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.82rem; color: #555; font-weight: 500;">{label}</span>
                            <span style="font-size: 0.88rem; font-weight: 700; color: {hex_color};">{value}</span>
                        </div>
                    </td>"""
                html_rows += f"<tr>{cells}</tr>"

            st.markdown(f"""
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">
                {html_rows}
            </table>
            """, unsafe_allow_html=True)
        else:
            st.info("No technical metrics available.")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. DCF Calculator / Score Tabs
    # ─────────────────────────────────────────────────────────────────────────

    dcf_tab, score_tab = st.tabs(["DCF Calculator", "Score"])

    with dcf_tab:
        st.markdown("""
        <h3 style="text-align: center; font-weight: 700; margin-bottom: 20px;">
            Discounted Cash Flow Calculator
        </h3>
        """, unsafe_allow_html=True)

        if dcf_data:
            # Get DCF inputs
            current_fcf = dcf_data.get("current_fcf", 0)
            growth_rates_default = dcf_data.get("fcf_growth_rates", [0.08]*5)
            terminal_growth = dcf_data.get("terminal_growth_rate", 0.04)
            discount_rate = dcf_data.get("discount_rate", 0.08)
            wacc_val = dcf_data.get("wacc", 0.10)
            shares_outstanding = dcf_data.get("shares_outstanding", 1)
            net_debt = dcf_data.get("net_debt", 0)

            # 6-year projection: table layout
            # All fields are plain text inputs (no stepper buttons) — matching original
            import datetime as _dt
            base_year = _dt.datetime.now().year
            num_years = 6

            # Pad growth rates to 6 years
            while len(growth_rates_default) < num_years:
                growth_rates_default.append(growth_rates_default[-1] if growth_rates_default else 0.05)

            def _fmt_fcf(v):
                """Format FCF with space separators."""
                return f"{int(round(v)):,}".replace(",", " ")

            def _parse_fcf(s):
                """Parse FCF from text input, handling spaces/commas."""
                try:
                    return float(s.replace(" ", "").replace(",", ""))
                except (ValueError, TypeError):
                    return 0

            def _parse_float(s, default=0.0):
                """Parse a float from text input."""
                try:
                    return float(s)
                except (ValueError, TypeError):
                    return default

            # ── Year header row ──
            year_cols = st.columns([1.2] + [1]*num_years)
            with year_cols[0]:
                st.markdown("**Year**")
            for i in range(num_years):
                with year_cols[i+1]:
                    st.markdown(f"**{base_year + i}**")

            # ── FCF Growth (%) row — plain text inputs, first year blank ──
            growth_cols = st.columns([1.2] + [1]*num_years)
            with growth_cols[0]:
                st.markdown("**FCF Growth (%)**")
            growth_rates = [0]  # placeholder for base year
            with growth_cols[1]:
                st.markdown("")  # First year = base, no growth
            for i in range(1, num_years):
                with growth_cols[i+1]:
                    default_pct = round(growth_rates_default[i-1] * 100, 2) if (i-1) < len(growth_rates_default) else 5.0
                    val_str = st.text_input(
                        f"G{base_year+i}",
                        value=f"{default_pct:.2f}",
                        label_visibility="collapsed",
                        key=f"dcf_g_{base_year+i}",
                    )
                    growth_rates.append(_parse_float(val_str) / 100)

            # ── FCF row — editable text inputs (matching original) ──
            fcf_cols = st.columns([1.2] + [1]*num_years)
            with fcf_cols[0]:
                st.markdown("**FCF**")

            # Calculate default projected FCFs
            default_fcfs = [current_fcf]
            proj = current_fcf
            for i in range(1, num_years):
                proj = proj * (1 + growth_rates[i])
                default_fcfs.append(proj)

            # Render editable FCF inputs
            fcf_values = []
            for i in range(num_years):
                with fcf_cols[i+1]:
                    fcf_str = st.text_input(
                        f"FCF{base_year+i}",
                        value=_fmt_fcf(default_fcfs[i]),
                        label_visibility="collapsed",
                        key=f"dcf_fcf_{base_year+i}",
                    )
                    fcf_values.append(_parse_fcf(fcf_str))

            st.markdown("")  # spacer

            # ── Bottom parameters: Long Term Growth Rate | Discount Rate | WACC | Equity Value ──
            param_cols = st.columns([1.2, 1.2, 1, 2])

            with param_cols[0]:
                st.markdown("**Long Term Growth Rate**")
                term_str = st.text_input(
                    "LT Growth",
                    value=str(round(terminal_growth * 100, 1)),
                    label_visibility="collapsed",
                    key="dcf_ltgr",
                )
                term_growth_final = _parse_float(term_str, 4.0) / 100

            with param_cols[1]:
                st.markdown("""<div style="background: #222; color: #fff; padding: 4px 8px; font-weight: 700;
                    text-align: center; border-radius: 4px;">Discount Rate</div>""", unsafe_allow_html=True)
                dr_str = st.text_input(
                    "DR",
                    value=str(round(discount_rate * 100, 1)),
                    label_visibility="collapsed",
                    key="dcf_dr",
                )
                discount_final = _parse_float(dr_str, 8.0) / 100

            with param_cols[2]:
                st.markdown("""<div style="background: #e0e0e0; padding: 4px 8px; font-weight: 600;
                    text-align: center; border-radius: 4px;">WACC</div>""", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; font-size: 1.1rem; padding-top: 8px;'>{wacc_val * 100:.1f}</div>", unsafe_allow_html=True)

            with param_cols[3]:
                # Calculate final DCF using the user-editable FCF values
                equity_per_share = None
                if discount_final > term_growth_final > 0 and fcf_values:
                    # Use growth_rates[1:] for the DCF model
                    equity_per_share = calculate_dcf(
                        fcf=current_fcf,
                        growth_rates=growth_rates[1:],
                        terminal_growth=term_growth_final,
                        discount_rate=discount_final,
                        shares_outstanding=shares_outstanding,
                        net_debt=net_debt,
                    )

                if equity_per_share and equity_per_share > 0:
                    st.markdown(f"""
                    <div style="text-align: right;">
                        <div style="font-size: 0.85rem; font-style: italic; font-weight: 600; color: #555;">
                            Equity Value Per Share
                        </div>
                        <div style="font-size: 2rem; font-weight: 700; color: #212529;">
                            $ {equity_per_share:,.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="text-align: right;">
                        <div style="font-size: 0.85rem; font-style: italic; font-weight: 600; color: #555;">
                            Equity Value Per Share
                        </div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #999;">N/A</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("DCF data not available for this ticker.")

    with score_tab:
        # Anchor for scroll-to from header badge
        st.markdown('<div id="score-section"></div>', unsafe_allow_html=True)

        # Re-compute score with breakdown using SEC EDGAR data
        from info_data import (
            _ticker_to_cik, _fetch_edgar_facts, _get_xbrl_value,
            _get_xbrl_two_years,
            _XBRL_INCOME_TAGS, _XBRL_BALANCE_TAGS, _XBRL_CASHFLOW_TAGS,
        )

        def _score_tiered(val, tiers):
            """Score a value against descending thresholds: [(threshold, pts), ...]."""
            if val is None:
                return 0
            for threshold, pts in tiers:
                if val >= threshold:
                    return pts
            return 0

        try:
            cik = _ticker_to_cik(ticker)
            facts = _fetch_edgar_facts(cik) if cik else None
            if not facts:
                raise ValueError("No EDGAR data")

            # ── Fetch raw EDGAR values ──
            rev = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Total Revenue"])
            gp = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Gross Profit"])
            cogs = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Cost Of Revenue"])
            if not gp and rev and cogs:
                gp = rev - cogs
            oi = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Operating Income"])
            ni = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Net Income"])
            interest = _get_xbrl_value(facts, _XBRL_INCOME_TAGS["Interest Expense"])

            ta = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Total Assets"])
            ca = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Assets"])
            cash_val = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Cash And Cash Equivalents"])
            inv = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Inventory"])
            ar = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Accounts Receivable"])
            cl = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Liabilities"])
            ltd = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Long Term Debt"])
            cur_debt = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Current Debt"])
            teq = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Stockholders Equity"])
            tl = _get_xbrl_value(facts, _XBRL_BALANCE_TAGS["Total Liabilities"])
            td = (ltd or 0) + (cur_debt or 0)

            ocf = _get_xbrl_value(facts, _XBRL_CASHFLOW_TAGS["Operating Cash Flow"])

            # Growth data (two years)
            ni_cur, ni_prev = _get_xbrl_two_years(facts, _XBRL_INCOME_TAGS["Net Income"])
            eps_cur, eps_prev = _get_xbrl_two_years(facts, _XBRL_INCOME_TAGS["EPS"], unit="USD/shares")

            # ── Profitability ──
            gm_pct = (gp / rev * 100) if rev and gp else 0
            pm_pct = (ni / rev * 100) if rev and ni else 0
            roe_pct = (ni / teq * 100) if teq and ni and teq != 0 else 0
            roa_pct = (ni / ta * 100) if ta and ni and ta != 0 else 0
            gm_s = _score_tiered(gm_pct, [(60,5),(40,4),(20,3),(10,2),(0.01,1)])
            pm_s = _score_tiered(pm_pct, [(20,5),(10,4),(5,3),(0.01,2)])
            roe_s = _score_tiered(roe_pct, [(25,5),(15,4),(10,3),(5,2),(0.01,1)])
            roa_s = _score_tiered(roa_pct, [(15,5),(10,4),(5,3),(2,2),(0.01,1)])
            prof_total = gm_s + pm_s + roe_s + roa_s

            # ── Liquidity ──
            cr = (ca / cl) if ca and cl and cl > 0 else None
            qr = ((ca - (inv or 0)) / cl) if ca and cl and cl > 0 else None
            cashr = (cash_val / cl) if cash_val is not None and cl and cl > 0 else None
            ocfr = (ocf / cl) if ocf is not None and cl and cl > 0 else None
            cr_s = _score_tiered(cr, [(3,5),(2,4),(1.5,3),(1,2),(0.5,1)])
            qr_s = _score_tiered(qr, [(2,5),(1.5,4),(1,3),(0.5,2),(0.2,1)])
            cashr_s = _score_tiered(cashr, [(1,5),(0.5,4),(0.3,3),(0.15,2),(0.05,1)])
            ocfr_s = _score_tiered(ocfr, [(1.5,5),(1,4),(0.5,3),(0.2,2),(0.05,1)])
            liq_total = cr_s + qr_s + cashr_s + ocfr_s

            # ── Leverage ──
            de_ratio = (td / teq) if teq and teq != 0 else None
            int_cov = abs(oi / interest) if oi and interest and abs(interest) > 0 else None
            da = (td / ta) if ta and ta > 0 else None
            ldc = (ltd / (ltd + teq)) if ltd is not None and teq is not None and (ltd + teq) > 0 else None
            # Altman Z (uses market cap from YF + EDGAR balance sheet)
            wc = (ca - cl) if ca is not None and cl is not None else None
            from info_data import _yf_info as _yf_info_fn
            _yf_data = _yf_info_fn(ticker)
            mc = _yf_data.get("marketCap")
            re_val_xbrl = _get_xbrl_value(facts, ["RetainedEarningsAccumulatedDeficit"], form_type="10-K")
            az = None
            if ta and ta > 0 and all(v is not None for v in [wc, re_val_xbrl, oi, mc, tl, rev]):
                az = 1.2*(wc/ta) + 1.4*(re_val_xbrl/ta) + 3.3*(oi/ta) + 0.6*(mc/tl if tl and tl > 0 else 0) + 1.0*(rev/ta)

            de_s = 0
            if de_ratio is not None:
                if de_ratio <= 0.1: de_s = 5
                elif de_ratio <= 0.3: de_s = 4
                elif de_ratio <= 0.5: de_s = 3
                elif de_ratio <= 1.0: de_s = 2
                elif de_ratio <= 2.0: de_s = 1
            ic_s = _score_tiered(int_cov, [(10,5),(5,4),(3,3),(1.5,2),(1,1)])
            da_s = 0
            if da is not None:
                if da <= 0.1: da_s = 5
                elif da <= 0.2: da_s = 4
                elif da <= 0.3: da_s = 3
                elif da <= 0.5: da_s = 2
                elif da <= 0.7: da_s = 1
            ldc_s = 0
            if ldc is not None:
                if ldc <= 0.1: ldc_s = 5
                elif ldc <= 0.2: ldc_s = 4
                elif ldc <= 0.3: ldc_s = 3
                elif ldc <= 0.5: ldc_s = 2
                elif ldc <= 0.7: ldc_s = 1
            az_s = _score_tiered(az, [(3,5),(2.5,4),(1.8,3),(1.2,2),(0.5,1)])
            lev_total = de_s + ic_s + da_s + ldc_s + az_s

            # ── Efficiency ──
            at = (rev / ta) if rev and ta and ta > 0 else None
            invt = (cogs / inv) if cogs and inv and inv > 0 else None
            rt = (rev / ar) if rev and ar and ar > 0 else None
            at_s = _score_tiered(at, [(2,5),(1.5,4),(1,3),(0.5,2),(0.2,1)])
            it_s = _score_tiered(invt, [(8,5),(5,4),(4,3),(2,2),(1,1)])
            rt_s = _score_tiered(rt, [(8,5),(5,4),(4,3),(2,2),(1,1)])
            eff_total = at_s + it_s + rt_s

            # ── Growth (EDGAR EPS + YF price CAGR) ──
            epsg_pct = None
            if eps_cur is not None and eps_prev is not None and eps_prev != 0:
                epsg_pct = ((eps_cur / eps_prev) - 1) * 100
            elif ni_cur is not None and ni_prev is not None and ni_prev != 0:
                epsg_pct = ((ni_cur / ni_prev) - 1) * 100
            # Also try YF earningsGrowth as fallback
            if epsg_pct is None:
                _eg = _yf_data.get("earningsGrowth")
                if _eg is not None:
                    epsg_pct = _eg * 100 if abs(_eg) < 10 else _eg
            cagr_v = None
            try:
                import yfinance as yf
                h5 = yf.Ticker(ticker).history(period="5y", interval="1mo")
                if h5 is not None and len(h5) >= 12:
                    cagr_v = (pow(float(h5["Close"].iloc[-1]) / float(h5["Close"].iloc[0]),
                                  1 / (len(h5) / 12)) - 1) * 100
            except Exception:
                pass
            epsg_s = _score_tiered(epsg_pct, [(30,5),(15,4),(5,3),(0.01,2)])
            cagr_s = _score_tiered(cagr_v, [(25,5),(15,4),(8,3),(3,2),(0.01,1)])
            gro_total = epsg_s + cagr_s

            # ── Valuation (from Yahoo Finance) ──
            pe = _yf_data.get("trailingPE")
            pb = _yf_data.get("priceToBook")
            pe_s = 0
            if pe and pe > 0:
                if pe <= 10: pe_s = 5
                elif pe <= 15: pe_s = 4
                elif pe <= 20: pe_s = 3
                elif pe <= 30: pe_s = 2
                elif pe <= 50: pe_s = 1
            pb_s = 0
            if pb and pb > 0:
                if pb <= 1: pb_s = 5
                elif pb <= 2: pb_s = 4
                elif pb <= 3: pb_s = 3
                elif pb <= 5: pb_s = 2
                elif pb <= 10: pb_s = 1
            val_total = pe_s + pb_s

        except Exception:
            prof_total = liq_total = lev_total = eff_total = gro_total = val_total = 0
            gm_s = pm_s = roe_s = roa_s = 0
            cr_s = qr_s = cashr_s = ocfr_s = 0
            de_s = ic_s = da_s = ldc_s = az_s = 0
            at_s = it_s = rt_s = 0
            epsg_s = cagr_s = pe_s = pb_s = 0

        score_color = "#34a853" if score >= 70 else ("#fbbc04" if score >= 40 else "#ea4335")
        total_score = prof_total + liq_total + lev_total + eff_total + gro_total + val_total

        # Build the score table layout
        def _cat_bar(label, pts, max_pts, color):
            return f'<div style="background:{color}; color:white; font-weight:700; padding:6px 12px; font-size:0.9rem;">{label} {pts} / {max_pts}</div>'

        def _row(items):
            """items: list of (label, score_str) tuples, 4 per row"""
            cols = ""
            for lbl, val in items:
                cols += f'<td style="padding:6px 12px; font-size:0.85rem;">{lbl}</td><td style="padding:6px 12px; font-weight:700; font-size:0.85rem;">{val}</td>'
            return f"<tr>{cols}</tr>"

        green = "#34a853"
        orange = "#fbbc04"
        red = "#ea4335"

        prof_color = green if prof_total >= 15 else (orange if prof_total >= 10 else red)
        liq_color = green if liq_total >= 15 else (orange if liq_total >= 10 else red)
        lev_color = green if lev_total >= 20 else (orange if lev_total >= 12 else red)
        eff_color = orange if eff_total >= 8 else (red if eff_total < 5 else orange)
        gro_color = green if gro_total >= 8 else (orange if gro_total >= 5 else red)
        val_color = green if val_total >= 7 else (orange if val_total >= 4 else red)

        score_html = f"""
        <table style="width:100%; border-collapse:collapse; margin-top:10px;">
        <tr><td colspan="4" style="padding:0;">{_cat_bar("Profitability", prof_total, 20, prof_color)}</td>
            <td colspan="4" style="padding:0;">{_cat_bar("Liquidity", liq_total, 20, liq_color)}</td></tr>
        {_row([("Gross Margin", f"{gm_s} / 5"), ("Profit Margin", f"{pm_s} / 5"),
               ("Current Ratio", f"{cr_s} / 5"), ("Quick Ratio", f"{qr_s} / 5")])}
        {_row([("ROE", f"{roe_s} / 5"), ("ROA", f"{roa_s} / 5"),
               ("Cash Ratio", f"{cashr_s} / 5"), ("Op. Cash Flow Ratio", f"{ocfr_s} / 5")])}

        <tr><td colspan="4" style="padding:0;">{_cat_bar("Leverage", lev_total, 25, lev_color)}</td>
            <td colspan="4" style="padding:0;">{_cat_bar("Efficiency", eff_total, 15, eff_color)}</td></tr>
        {_row([("Debt to Equity", f"{de_s} / 5"), ("Interest Coverage", f"{ic_s} / 5"),
               ("Asset Turn. Ratio", f"{at_s} / 5"), ("Inventory Turn. Ratio", f"{it_s} / 5")])}
        {_row([("Debt to Asset", f"{da_s} / 5"), ("Lt Debt to Cap.", f"{ldc_s} / 5"),
               ("Receivables Turn. Ratio", f"{rt_s} / 5"), ("", "")])}
        {_row([("Altman Z Score", f"{az_s} / 5"), ("", ""), ("", ""), ("", "")])}

        <tr><td colspan="4" style="padding:0;">{_cat_bar("Growth", gro_total, 10, gro_color)}</td>
            <td colspan="4" style="padding:0;">{_cat_bar("Valuation", val_total, 10, val_color)}</td></tr>
        {_row([("EPS Growth (1Y)", f"{epsg_s} / 5"), ("CAGR", f"{cagr_s} / 5"),
               ("P/E Ratio", f"{pe_s} / 5"), ("P/B Ratio", f"{pb_s} / 5")])}

        <tr><td colspan="8" style="padding:0;">
            <div style="background:{score_color}; color:white; font-weight:700; padding:10px 12px; font-size:1.1rem; text-align:right;">
                Total Score : {total_score} / 100
            </div>
        </td></tr>
        </table>
        """
        st.markdown(score_html, unsafe_allow_html=True)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Company Ownership Section
    # ─────────────────────────────────────────────────────────────────────────

    if ownership_data:
        st.markdown("### 🏢 Company Ownership")

        own_col_left, own_col_right = st.columns(2)

        with own_col_left:
            # Ownership pie chart
            pie_fig = create_ownership_pie(
                insider_pct=ownership_data.get("insider_pct", 0),
                institutional_pct=ownership_data.get("institutional_pct", 0),
                public_pct=ownership_data.get("public_pct", 0),
                company_name=name,
            )
            st.plotly_chart(pie_fig, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtons": [["toImage"]]})

        with own_col_right:
            # Institutional holders
            institutional_holders = ownership_data.get("institutional_holders", [])
            if institutional_holders:
                bar_fig = create_institutional_bar(institutional_holders)
                st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtons": [["toImage"]]})
            else:
                st.info("No institutional holding data available.")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Insider Activity Section
    # ─────────────────────────────────────────────────────────────────────────

    if insider_trades:
        st.markdown("### 👥 Insider Activity")

        insider_col_left, insider_col_right = st.columns(2)

        with insider_col_left:
            # Monthly insider activity chart
            monthly_data = insider_trades.get("monthly_activity", [])
            if monthly_data:
                activity_fig = create_insider_activity_chart(monthly_data)
                st.plotly_chart(activity_fig, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False, "modeBarButtons": [["toImage"]]})
            else:
                st.info("No monthly insider activity data available.")

        with insider_col_right:
            # Last 10 insiders' trades table
            recent_trades = insider_trades.get("recent_trades", [])
            if recent_trades:
                trades_df = pd.DataFrame(recent_trades[:10])
                st.markdown("#### Last 10 Insiders' Trades")
                st.dataframe(
                    trades_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "insider_name": "Insider",
                        "relation": "Relation",
                        "transaction_date": "Date",
                        "transaction_type": "Type",
                        "shares": "Shares",
                        "price": "Price",
                    }
                )
            else:
                st.info("No recent insider trades available.")

    # ─────────────────────────────────────────────────────────────────────────
    # Live Price Polling with Green/Red Flash (Yahoo Finance style)
    # Uses local price API (port 8502) to avoid CORS issues.
    # ─────────────────────────────────────────────────────────────────────────
    import streamlit.components.v1 as components
    _live_price_js = f"""
    <script>
    (function() {{
        const TICKER = "{ticker}";
        const YF_URL = "https://api.allorigins.win/raw?url=" + encodeURIComponent(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + TICKER + "?range=1d&interval=1m&includePrePost=true"
        );
        const POLL_MS = 5000;
        let prevPrice = null;
        const GREEN = "#00C805";
        const RED   = "#FF3300";
        const GREEN_BG = "rgba(0, 200, 5, 0.25)";
        const RED_BG   = "rgba(255, 51, 0, 0.25)";

        function doc() {{
            try {{ return window.parent.document; }} catch(e) {{ return null; }}
        }}

        function flash(el, dir) {{
            if (!el) return;
            el.style.backgroundColor = dir > 0 ? GREEN_BG : RED_BG;
            setTimeout(() => el.style.backgroundColor = "transparent", 600);
        }}

        function changeBadge(chg, pct) {{
            const s = chg >= 0 ? "+" : "";
            const c = chg >= 0 ? GREEN : RED;
            return '<span style="color:' + c + ';font-weight:600;">'
                 + s + chg.toFixed(2) + ' (' + s + pct.toFixed(2) + '%)</span>';
        }}

        function updateOHLC(d, price, chg, pct) {{
            const titles = d.querySelectorAll('.gtitle');
            for (let i = 0; i < titles.length; i++) {{
                const txt = titles[i].textContent;
                if (txt.includes('C ')) {{
                    const svg = titles[i].closest('svg');
                    if (!svg) continue;
                    const spans = svg.querySelectorAll('text');
                    const sgn = chg >= 0 ? "+" : "";
                    const col = chg >= 0 ? GREEN : RED;
                    for (let j = 0; j < spans.length; j++) {{
                        if (spans[j].textContent.trim().startsWith('C ')) {{
                            const parts = spans[j].textContent.split('C ');
                            if (parts.length > 1) {{
                                spans[j].textContent = parts[0] + 'C ' + price.toFixed(2);
                                spans[j].style.fill = col;
                            }}
                        }}
                        if (/^[+\\-]\\d/.test(spans[j].textContent.trim())) {{
                            spans[j].textContent = sgn + chg.toFixed(2) + ' (' + sgn + pct.toFixed(2) + '%)';
                            spans[j].style.fill = col;
                        }}
                    }}
                }}
            }}
        }}

        function poll() {{
            const dd = doc();
            if (!dd) return;
            fetch(YF_URL)
              .then(r => r.json())
              .then(data => {{
                const res = data.chart.result[0];
                const meta = res.meta;
                const ts = res.timestamp || [];
                const closes = res.indicators.quote[0].close || [];
                const regEnd = meta.currentTradingPeriod.regular.end;
                const regStart = meta.currentTradingPeriod.regular.start;
                const postEnd = meta.currentTradingPeriod.post.end;
                const preStart = meta.currentTradingPeriod.pre.start;
                const now = Math.floor(Date.now() / 1000);

                const regPrice = meta.regularMarketPrice;
                const prevClose = meta.chartPreviousClose;
                const chg = regPrice - prevClose;
                const pct = (chg / prevClose) * 100;
                const isUp = chg >= 0;
                const col = isUp ? GREEN : RED;
                const sign = isUp ? "+" : "";

                // Update main price
                const priceEl = dd.getElementById("qc-price-value");
                const changeEl = dd.getElementById("qc-change");
                const closeTimeEl = dd.getElementById("qc-close-time");

                if (priceEl) {{
                    const oldP = parseFloat(priceEl.textContent.replace('$',''));
                    priceEl.textContent = "$" + regPrice.toFixed(2);
                    if (prevPrice !== null && regPrice !== oldP) flash(priceEl, regPrice - oldP);
                    prevPrice = regPrice;
                }}

                if (changeEl) {{
                    changeEl.innerHTML = changeBadge(chg, pct);
                }}

                // Determine market state and show close time
                let marketLabel = "";
                const regTime = new Date(meta.regularMarketTime * 1000);
                if (now >= regStart && now <= regEnd) {{
                    marketLabel = "";
                }} else {{
                    const opts = {{ month:'short', day:'numeric', hour:'numeric', minute:'2-digit', hour12:true }};
                    marketLabel = "At close: " + regTime.toLocaleString('en-US', opts) + " EDT";
                }}
                if (closeTimeEl) closeTimeEl.textContent = marketLabel;

                // Update OHLC bar on chart
                updateOHLC(dd, regPrice, chg, pct);

                // Extended hours (after-hours / pre-market)
                const ahDiv = dd.getElementById("qc-afterhours");
                if (ahDiv && (now > regEnd || now < regStart)) {{
                    // Find the latest non-null close from data points
                    let lastExtPrice = null;
                    for (let i = ts.length - 1; i >= 0; i--) {{
                        if (closes[i] != null && ts[i] > regEnd) {{
                            lastExtPrice = closes[i];
                            break;
                        }}
                    }}
                    if (lastExtPrice === null) {{
                        // Try pre-market
                        for (let i = ts.length - 1; i >= 0; i--) {{
                            if (closes[i] != null && ts[i] < regStart) {{
                                lastExtPrice = closes[i];
                                break;
                            }}
                        }}
                    }}

                    if (lastExtPrice !== null && lastExtPrice !== regPrice) {{
                        ahDiv.style.display = "block";
                        const extChg = lastExtPrice - regPrice;
                        const extPct = (extChg / regPrice) * 100;
                        const extUp = extChg >= 0;
                        const extCol = extUp ? GREEN : RED;
                        const extSign = extUp ? "+" : "";
                        const extLabel = now > regEnd ? "After hours" : "Pre-market";

                        const extPriceEl = dd.getElementById("qc-ext-price");
                        const extChangeEl = dd.getElementById("qc-ext-change");
                        const extTimeEl = dd.getElementById("qc-ext-time");

                        if (extPriceEl) extPriceEl.textContent = "$" + lastExtPrice.toFixed(2);
                        if (extChangeEl) {{
                            extChangeEl.innerHTML = '<span style="color:' + extCol + ';font-weight:600;">' + extSign + extChg.toFixed(2) + ' (' + extSign + extPct.toFixed(2) + '%)</span>';
                        }}
                        if (extTimeEl) {{
                            const lastTs = new Date(ts[ts.length-1] * 1000);
                            const tOpts = {{ hour:'numeric', minute:'2-digit', hour12:true }};
                            extTimeEl.textContent = extLabel + ": " + lastTs.toLocaleString('en-US', tOpts) + " EDT";
                        }}
                    }} else {{
                        ahDiv.style.display = "none";
                    }}
                }} else if (ahDiv) {{
                    ahDiv.style.display = "none";
                }}
              }})
              .catch(e => console.log("[QC price] error:", e));
        }}

        setInterval(poll, POLL_MS);
        setTimeout(poll, 500);
    }})();
    </script>
    """
    components.html(_live_price_js, height=0, width=0)
    components.html(_live_price_js, height=0, width=0)
