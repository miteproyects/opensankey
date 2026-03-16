"""
Open Sankey – A local financial charting app.

Run with:  streamlit run app.py
"""

import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any

from data_fetcher import (
    get_company_info,
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_analyst_forecast,
    validate_ticker,
    format_large_number,
    compute_margins,
    compute_eps,
    compute_revenue_yoy,
    compute_per_share,
    compute_qoq_revenue,
    compute_expense_ratios,
    compute_ebitda,
    compute_effective_tax_rate,
    get_revenue_by_product,
    get_revenue_by_geography,
    _opensankey_get_segments,
)
from info_data import get_company_icon
from price_api import ensure_running as _start_price_api, API_PORT as _PRICE_API_PORT
_start_price_api()  # Start background price server on port 8502

# Lazy-load page modules: only import when their page is active (saves ~2s)
# from profile_page import render_profile_page   — imported in page routing
# from earnings_page import render_earnings_page  — imported in page routing
# from watchlist_page import render_watchlist_page — imported in page routing
from charts import (
    COLORS,
    create_income_chart,
    create_margins_chart,
    create_eps_chart,
    create_revenue_yoy_chart,
    create_opex_chart,
    create_ebitda_chart,
    create_tax_chart,
    create_per_share_chart,
    create_qoq_revenue_chart,
    create_sbc_chart,
    create_shares_chart,
    create_expense_ratios_chart,
    create_effective_tax_rate_chart,
    create_cash_flow_chart,
    create_cash_position_chart,
    create_capex_chart,
    create_assets_chart,
    create_liabilities_chart,
    create_equity_debt_chart,
    create_pe_chart,
    create_market_cap_chart,
    create_analyst_forecast_chart,
    create_revenue_by_product_chart,
    create_revenue_by_geography_chart,
    create_income_breakdown_chart,
)


# ───────────────────────────────────────────────────────────────────────────
# Page config
# ───────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Open Sankey",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

# Cache version: only clear caches manually when needed (not on every new session)
# To force cache clear: bump this number AND uncomment the clear() line, then revert.
# _CACHE_VERSION = 91
# if st.session_state.get("_cache_v") != _CACHE_VERSION:
#     st.cache_data.clear()
#     st.session_state._cache_v = _CACHE_VERSION

# ───────────────────────────────────────────────────────────────────────────
# Force light mode at browser level BEFORE any content renders
# ───────────────────────────────────────────────────────────────────────────
st.markdown(
    '<meta name="color-scheme" content="light only">'
    '<style>:root{color-scheme:light only !important}'
    'html,body,.stApp{background:#fff!important;color:#212529!important}</style>',
    unsafe_allow_html=True,
)

# ───────────────────────────────────────────────────────────────────────────
# Custom CSS – light theme matching Open Sankey style
# ───────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---- Variables ---- */
:root {
    --bg: #ffffff;
    --sidebar-bg: #f8f9fa;
    --header-bg: #212529;
    --accent: #2475fc;
    --text: #212529;
    --muted: #6c757d;
    --border: #dee2e6;
    --light-border: #e9ecef;
    --green: #34a853;
    --yellow: #fbbc04;
    --red: #ea4335;
}

/* ---- Global – force white immediately to prevent dark flash on refresh ---- */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"], .main, .block-container,
[data-testid="stMainBlockContainer"] {
    background-color: #ffffff !important;
    color: #212529 !important;
}

/* Remove Streamlit header */
[data-testid="stHeader"] {
    background-color: #ffffff !important;
    display: none !important;
}

/* Sidebar – move to right side */
section[data-testid="stSidebar"] {
    background-color: var(--sidebar-bg) !important;
    border-left: 1px solid var(--border);
    border-right: none;
    order: 2 !important;
    min-width: 340px !important;
    width: 340px !important;
}
/* Make collapse button always visible — arrow flipped to >> (close right-side sidebar) */
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button {
    visibility: visible !important;
}
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button [data-testid="stIconMaterial"] {
    transform: scaleX(-1) !important;
}
[data-testid="stAppViewContainer"] {
    flex-direction: row !important;
}
[data-testid="stAppViewContainer"] > div:not([data-testid="stSidebar"]) {
    order: 1 !important;
    flex: 1 1 auto !important;
}
/* Push the collapse/expand button to the right side too */
[data-testid="stSidebarCollapsedControl"] {
    left: auto !important;
    right: 0.5rem !important;
    /* Hide Streamlit's default expand control — we use our nav-bar button */
    opacity: 0 !important;
    pointer-events: none !important;
    position: fixed !important;
    top: -9999px !important;
}
/* When sidebar is collapsed, hide the sidebar panel */
[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    background: transparent !important;
    border: none !important;
}
[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarContent"] {
    width: 0 !important;
    min-width: 0 !important;
    overflow: hidden !important;
}
/* Hide all sidebar content when collapsed */
[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarUserContent"] {
    display: none !important;
}

/* ── CSS-driven expand-button visibility (no JS needed) ────────── */
/* When sidebar is collapsed, show the nav-bar expand button via :has() */
:has([data-testid="stSidebar"][aria-expanded="false"]) .nav-expand-btn {
    display: block !important;
}
/* When sidebar is expanded, ensure the expand button hides */
:has([data-testid="stSidebar"][aria-expanded="true"]) .nav-expand-btn {
    display: none !important;
}

/* Remove default top padding */
.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 1rem !important;
}

/* ---- Nav bar (dark header) ---- */
.nav-bar {
    background: var(--header-bg);
    padding: 10px 24px;
    display: flex;
    align-items: center;
    gap: 28px;
    flex-wrap: wrap;
    margin: -0.5rem -1rem 16px -1rem;
    position: relative;
}
/* Expand-sidebar button inside nav bar */
.nav-expand-btn {
    display: none;
    margin-left: auto;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 6px;
    padding: 4px 10px;
    color: #ffffff;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.2s;
    line-height: 1;
}
.nav-expand-btn:hover {
    background: rgba(255,255,255,0.25);
}
.nav-bar a, .nav-bar .nav-link {
    color: #adb5bd;
    text-decoration: none;
    font-size: 0.9rem;
    font-weight: 400;
    transition: color 0.2s;
    cursor: pointer;
}
.nav-bar a:hover, .nav-bar a.active,
.nav-bar .nav-link:hover, .nav-bar .nav-link.active {
    color: #ffffff;
    font-weight: 700;
}
.nav-logo {
    font-size: 1.2rem;
    font-weight: 800;
    color: #ffffff !important;
    display: flex;
    align-items: center;
    gap: 8px;
    line-height: 1.1;
}

/* ---- Metric cards ---- */
.metric-row {
    display: flex;
    gap: 12px;
    margin: 10px 0 4px 0;
}
.metric-card {
    flex: 1;
    text-align: center;
    padding: 8px 4px;
}
.metric-label {
    color: var(--muted);
    font-size: 0.75rem;
    font-weight: 400;
    margin-bottom: 2px;
}
.metric-value {
    color: var(--text);
    font-size: 1.3rem;
    font-weight: 700;
}
.more-info-link {
    color: var(--accent);
    font-size: 0.8rem;
    text-decoration: none;
    cursor: pointer;
}

/* ---- Pre-style section header rows via CSS to prevent white flash on load ---- */
/* These rules ONLY apply before JS runs (no .section-row-* class yet).
   Once JS adds .section-row-expanded / .section-row-collapsed, these
   step aside and the JS-applied rules take over. */
[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_"]):not(.section-row-expanded):not(.section-row-collapsed) {
    background: var(--header-bg) !important;
    border-radius: 12px !important;
    border: 2px solid var(--header-bg) !important;
    padding: 0 4px !important;
    gap: 0 !important;
    align-items: center !important;
}
[class*="st-key-hdr_show_"] button:not(.section-header-expanded):not(.section-header-collapsed) {
    background: transparent !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 14px 20px !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    text-align: left !important;
    cursor: pointer !important;
    min-height: 3rem !important;
}
/* Pre-style PDF buttons before JS — only when row has no JS class yet */
[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_"]):not(.section-row-expanded):not(.section-row-collapsed) [class*="st-key-gen_pdf_"] button,
[data-testid="stHorizontalBlock"]:has([class*="st-key-hdr_show_"]):not(.section-row-expanded):not(.section-row-collapsed) [class*="st-key-dl_"] button {
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

/* ---- Section header buttons – EXPANDED (dark, like original) ---- */
.section-header-expanded {
    background: var(--header-bg) !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    padding: 14px 20px !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    border: 2px solid var(--header-bg) !important;
    text-align: left !important;
    cursor: pointer !important;
    min-height: 3rem !important;
}
.section-header-expanded:hover {
    background: #343a40 !important;
    border-color: #343a40 !important;
    color: #ffffff !important;
}
.section-header-expanded:focus {
    box-shadow: none !important;
    outline: none !important;
    color: #ffffff !important;
}

/* ---- Section header buttons – COLLAPSED (light, like original) ---- */
.section-header-collapsed {
    background: #ffffff !important;
    color: var(--text) !important;
    border-radius: 12px !important;
    padding: 14px 20px !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    border: 2px solid var(--border) !important;
    text-align: left !important;
    cursor: pointer !important;
    min-height: 3rem !important;
}
.section-header-collapsed:hover {
    background: #f8f9fa !important;
    border-color: #ced4da !important;
    color: var(--text) !important;
}
.section-header-collapsed:focus {
    box-shadow: none !important;
    outline: none !important;
    color: var(--text) !important;
}

/* ---- Section header row: header + PDF button side by side via st.columns ---- */
/* JS adds .section-row-expanded / .section-row-collapsed to the stHorizontalBlock
   that contains the header button + PDF button columns. */
.section-row-expanded {
    background: var(--header-bg) !important;
    border-radius: 12px !important;
    border: 2px solid var(--header-bg) !important;
    padding: 0 4px !important;
    gap: 0 !important;
    align-items: center !important;
}
.section-row-collapsed {
    background: #ffffff !important;
    border-radius: 12px !important;
    border: 2px solid var(--border) !important;
    padding: 0 4px !important;
    gap: 0 !important;
    align-items: center !important;
}
/* Header button inside row should be transparent (row provides background) */
.section-row-expanded .section-header-expanded,
.section-row-collapsed .section-header-collapsed {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
}
/* PDF button dark variant (inside expanded row) */
.section-row-expanded button:not(.section-header-expanded) {
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
.section-row-expanded button:not(.section-header-expanded):hover {
    background: rgba(255,255,255,0.24) !important;
    border-color: rgba(255,255,255,0.45) !important;
}
/* PDF button light variant (inside collapsed row) */
.section-row-collapsed button:not(.section-header-collapsed) {
    background: rgba(0,0,0,0.05) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
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
.section-row-collapsed button:not(.section-header-collapsed):hover {
    background: rgba(0,0,0,0.10) !important;
    border-color: #adb5bd !important;
}
/* Remove extra padding from PDF column containers */
.section-row-expanded [data-testid="stColumn"],
.section-row-collapsed [data-testid="stColumn"] {
    padding: 0 !important;
}
.section-row-expanded [data-testid="stColumn"] [data-testid="stButton"],
.section-row-collapsed [data-testid="stColumn"] [data-testid="stButton"],
.section-row-expanded [data-testid="stColumn"] [data-testid="stDownloadButton"],
.section-row-collapsed [data-testid="stColumn"] [data-testid="stDownloadButton"] {
    margin: 0 !important;
    padding: 0 !important;
}

/* ---- Info (i) icon styling ---- */
[data-testid="stPopoverButton"] {
    background: transparent !important;
    border: 1.5px solid #adb5bd !important;
    border-radius: 50% !important;
    width: 22px !important;
    height: 22px !important;
    min-height: 22px !important;
    min-width: 22px !important;
    max-width: 22px !important;
    max-height: 22px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    opacity: 0.5;
    position: relative !important;
    margin-top: 2px !important;
    overflow: hidden !important;
}
/* Hide ALL default inner content (text "i" + chevron) */
[data-testid="stPopoverButton"] > * {
    visibility: hidden !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
/* Draw the styled "i" via ::after pseudo-element */
[data-testid="stPopoverButton"]::after {
    content: "i" !important;
    font-family: Georgia, "Times New Roman", serif !important;
    font-size: 14px !important;
    font-style: italic !important;
    font-weight: 600 !important;
    color: #6c757d !important;
    line-height: 1 !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
}
[data-testid="stPopoverButton"]:hover {
    opacity: 1 !important;
    border-color: #2475fc !important;
    background: #f0f6ff !important;
}
[data-testid="stPopoverButton"]:hover::after {
    color: #2475fc !important;
}
[data-testid="stPopoverButton"]:focus {
    box-shadow: none !important;
    outline: none !important;
}
/* Popover content panel */
[data-testid="stPopoverBody"] {
    max-width: 460px !important;
    min-width: 360px !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
    padding: 4px 8px !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06) !important;
}
/* Section labels inside popover */
[data-testid="stPopoverBody"] strong {
    color: #212529 !important;
}
[data-testid="stPopoverBody"] h3 {
    font-size: 1.05rem !important;
    margin: 0 0 4px 0 !important;
    padding-bottom: 8px !important;
    border-bottom: 1.5px solid #e9ecef !important;
    color: #212529 !important;
}

/* ---- Status indicator ---- */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    margin-right: 6px;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
/* Hide the duplicate nav buttons row (navbar JS triggers them) */
.hidden-nav-row { display: none !important; }

/* ---- Compact chart spacing ---- */
.element-container:has(iframe) { margin-bottom: 0 !important; }

/* ---- Footer ---- */
.footer {
    background: var(--header-bg);
    color: #adb5bd;
    padding: 40px 24px;
    margin-top: 40px;
    margin-left: -1rem;
    margin-right: -1rem;
}
.footer h3 {
    color: #ffffff;
    font-size: 1rem;
    margin-bottom: 12px;
}
.footer p, .footer a {
    color: #adb5bd;
    font-size: 0.85rem;
    line-height: 1.7;
}
.footer a:hover {
    color: var(--accent);
}

/* ---- Hide Streamlit branding ---- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ---- Expander styling ---- */
div[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 8px;
}

/* ---- Sidebar segmented buttons ---- */
section[data-testid="stSidebar"] button[kind="secondary"] {
    border: 2px solid var(--accent) !important;
    color: var(--accent) !important;
    background: #ffffff !important;
    font-weight: 500;
    padding: 0.45rem 0.2rem !important;
    min-height: 2.5rem;
    font-size: 0.9rem;
    border-radius: 0 !important;
}
section[data-testid="stSidebar"] button[kind="primary"] {
    border: 2px solid var(--accent) !important;
    background: var(--accent) !important;
    color: #fff !important;
    font-weight: 600;
    padding: 0.45rem 0.2rem !important;
    min-height: 2.5rem;
    font-size: 0.9rem;
    border-radius: 0 !important;
}

/* Connected segmented bar (applied via JS) */
.seg-connected {
    gap: 0 !important;
    border: 2px solid var(--accent) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
.seg-connected [data-testid="stColumn"] {
    padding: 0 !important;
}
.seg-connected button {
    border: none !important;
    border-radius: 0 !important;
    border-right: 1px solid rgba(36,117,252,0.3) !important;
}
.seg-connected [data-testid="stColumn"]:last-child button {
    border-right: none !important;
}

/* Custom Timeframe expander */
section[data-testid="stSidebar"] div[data-testid="stExpander"] {
    border: 2px solid var(--accent) !important;
    border-radius: 10px !important;
}
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary p {
    color: var(--accent) !important;
    font-weight: 500;
}

/* ---- Plotly - no extra background override needed with light theme ---- */
</style>
""", unsafe_allow_html=True)

# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# Global responsive CSS â all devices / all viewports
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">', unsafe_allow_html=True)
st.markdown("""
<style>
/* ====== GLOBAL RESPONSIVE ====== */

/* Ensure smooth scrolling on iOS */
html { -webkit-overflow-scrolling: touch; }

/* Fix iOS input zoom (font-size under 16px triggers zoom) */
input, select, textarea { font-size: 16px !important; }

/* Make all Plotly charts container-width responsive */
.js-plotly-plot, .plotly { width: 100% !important; }

/* Prevent horizontal overflow globally */
.main .block-container { overflow-x: hidden; }

/* Responsive images and iframes */
img, iframe, svg, canvas { max-width: 100%; height: auto; }

/* ====== TABLET (lte 1024px) ====== */
@media (max-width: 1024px) {
    /* Collapse sidebar by default on tablet */
    section[data-testid="stSidebar"] {
        min-width: 280px !important;
        width: 280px !important;
    }
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    /* Nav bar: tighter spacing */
    .nav-bar {
        padding: 10px 16px !important;
        gap: 16px !important;
    }
    .nav-bar a, .nav-bar .nav-link {
        font-size: 0.82rem !important;
    }
    .nav-logo {
        font-size: 1rem !important;
    }
    /* Metric cards: smaller text */
    .metric-value {
        font-size: 1.1rem !important;
    }
    /* Footer: tighter */
    .footer {
        padding: 24px 16px !important;
    }
}

/* ====== MOBILE (lte 768px) ====== */
@media (max-width: 768px) {
    /* Hide sidebar completely on mobile, show expand button */
    section[data-testid="stSidebar"] {
        min-width: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
        display: none !important;
    }
    .nav-expand-btn {
        display: inline-flex !important;
    }
    /* Block container: minimal padding */
    .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
        padding-top: 0.25rem !important;
    }
    /* Nav bar: wrap and compact */
    .nav-bar {
        padding: 8px 12px !important;
        gap: 10px !important;
        margin: -0.5rem -0.4rem 10px -0.4rem !important;
    }
    .nav-bar a, .nav-bar .nav-link {
        font-size: 0.78rem !important;
    }
    .nav-logo {
        font-size: 0.95rem !important;
        gap: 5px !important;
    }
    /* Metric cards stack better */
    .metric-row {
        flex-wrap: wrap !important;
        gap: 8px !important;
    }
    .metric-card {
        flex: 1 1 45% !important;
        min-width: 120px !important;
    }
    .metric-value {
        font-size: 1rem !important;
    }
    .metric-label {
        font-size: 0.7rem !important;
    }
    /* Section headers: smaller */
    .section-header-expanded,
    .section-header-collapsed,
    [class*="st-key-hdr_show_"] button {
        padding: 10px 12px !important;
        font-size: 0.95rem !important;
        min-height: 2.4rem !important;
    }
    /* Footer: single column */
    .footer {
        padding: 20px 12px !important;
        margin-left: -0.4rem !important;
        margin-right: -0.4rem !important;
    }
    /* Streamlit columns: prevent extreme squish */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    /* Popover: fit mobile screen */
    [data-testid="stPopoverBody"] {
        max-width: 90vw !important;
        min-width: 260px !important;
    }
    /* Info banner text */
    .stAlert p {
        font-size: 0.85rem !important;
    }
}

/* ====== SMALL PHONE (lte 480px) ====== */
@media (max-width: 480px) {
    .block-container {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }
    .nav-bar {
        padding: 6px 8px !important;
        gap: 8px !important;
        margin: -0.5rem -0.25rem 8px -0.25rem !important;
    }
    .nav-bar a, .nav-bar .nav-link {
        font-size: 0.72rem !important;
    }
    .nav-logo {
        font-size: 0.85rem !important;
    }
    .metric-card {
        flex: 1 1 100% !important;
    }
    .metric-value {
        font-size: 0.9rem !important;
    }
    .section-header-expanded,
    .section-header-collapsed {
        padding: 8px 10px !important;
        font-size: 0.85rem !important;
    }
    /* PDF buttons in section headers */
    .section-row-expanded button:not(.section-header-expanded),
    .section-row-collapsed button:not(.section-header-collapsed) {
        font-size: 0.68rem !important;
        padding: 4px 8px !important;
    }
}

/* ====== TOUCH DEVICE IMPROVEMENTS ====== */
@media (hover: none) and (pointer: coarse) {
    /* Larger tap targets */
    .nav-bar a, .nav-bar .nav-link {
        padding: 6px 4px !important;
        min-height: 36px !important;
        display: inline-flex !important;
        align-items: center !important;
    }
    button {
        min-height: 44px;
    }
    /* Remove hover-only effects that don't work on touch */
    .section-header-expanded:hover,
    .section-header-collapsed:hover {
        background: inherit !important;
    }
}

/* ====== HIGH DPI / RETINA ====== */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
    /* Sharper borders on retina displays */
    .section-row-expanded,
    .section-row-collapsed {
        border-width: 1px !important;
    }
}

/* ====== LANDSCAPE PHONE ====== */
@media (max-height: 500px) and (orientation: landscape) {
    .nav-bar {
        padding: 4px 12px !important;
    }
    .block-container {
        padding-top: 0.1rem !important;
    }
}

/* ====== PRINT ====== */
@media print {
    .nav-bar, section[data-testid="stSidebar"], .nav-expand-btn { display: none !important; }
    .block-container { padding: 0 !important; }
}

/* ====== SCROLLABLE TABLES (global) ====== */
.responsive-table-wrap {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-bottom: 1rem;
}
.responsive-table-wrap table {
    min-width: 580px;
}
</style>
""", unsafe_allow_html=True)



# ───────────────────────────────────────────────────────────────────────────
# Session state defaults
# ───────────────────────────────────────────────────────────────────────────
# ---- Deferred sync: apply header-toggle flags BEFORE widgets render ----
for _sk, _ck in [("show_income", "cb_income"), ("show_cashflow", "cb_cf"),
                  ("show_balance", "cb_bs"), ("show_metrics", "cb_km")]:
    _flag = f"_sync_{_ck}"
    if _flag in st.session_state:
        st.session_state[_ck] = st.session_state[_flag]
        st.session_state[_sk] = st.session_state[_flag]
        del st.session_state[_flag]

if "ticker" not in st.session_state:
    st.session_state.ticker = "NVDA"
# Always sync page from query params (navbar uses URL navigation)
_qp_page = st.query_params.get("page", "").lower()
_qp_ticker = st.query_params.get("ticker", "").upper().strip()
if _qp_ticker:
    st.session_state.ticker = _qp_ticker
if _qp_page in ("profile", "charts", "earnings", "watchlist", "sankey", "login", "pricing"):
    st.session_state.page = _qp_page
elif "page" not in st.session_state:
    st.session_state.page = "charts"
# Always keep URL in sync so browser refresh preserves the current page
_sync_page = st.session_state.page
_sync_ticker = st.session_state.ticker
if st.query_params.get("page") != _sync_page or st.query_params.get("ticker") != _sync_ticker:
    st.query_params.update({"page": _sync_page, "ticker": _sync_ticker})
if "quarterly" not in st.session_state:
    st.session_state.quarterly = True
if "timeframe" not in st.session_state:
    st.session_state.timeframe = "2Y"
if "show_income" not in st.session_state:
    st.session_state.show_income = True
if "show_cashflow" not in st.session_state:
    st.session_state.show_cashflow = True
if "show_balance" not in st.session_state:
    st.session_state.show_balance = True
if "show_metrics" not in st.session_state:
    st.session_state.show_metrics = True
if "show_forecast" not in st.session_state:
    st.session_state.show_forecast = False
if "layout_cols" not in st.session_state:
    st.session_state.layout_cols = 1


# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────

def _trim_timeframe(df: pd.DataFrame) -> pd.DataFrame:
    """Trim DataFrame rows to match the selected timeframe."""
    tf = st.session_state.timeframe
    if df.empty or tf == "MAX":
        return df
    if tf == "CUSTOM" and "custom_n" in st.session_state:
        n = st.session_state.custom_n
        return df.tail(min(n, len(df)))
    n_map = {"1Y": 4, "2Y": 8, "4Y": 16}
    n = n_map.get(tf, len(df))
    if not st.session_state.quarterly:
        n = max(n // 4, 1)
    # Return all available data if we have less than requested
    return df.tail(min(n, len(df)))


def _trim_segment_timeframe(df: pd.DataFrame) -> pd.DataFrame:
    """Trim segment DataFrame to match the selected timeframe.

    Segment data may be annual (FY labels) even when quarterly mode is
    selected (FMP free tier only provides annual segments).  This function
    detects whether the data is annual or quarterly and trims accordingly.
    """
    tf = st.session_state.timeframe
    if df.empty or tf == "MAX":
        return df

    # Detect if this is annual data (FY labels) or quarterly (Q labels)
    is_annual = any(str(idx).startswith("FY") for idx in df.index)

    year_map = {"1Y": 1, "2Y": 2, "4Y": 4}
    quarter_map = {"1Y": 4, "2Y": 8, "4Y": 16}

    if is_annual:
        # Annual data: trim by number of years (match user selection exactly)
        n = year_map.get(tf, len(df))
    elif st.session_state.quarterly:
        n = quarter_map.get(tf, len(df))
    else:
        n = year_map.get(tf, len(df))

    if tf == "CUSTOM" and "custom_n" in st.session_state:
        n = st.session_state.custom_n
        if is_annual:
            n = max(n // 4, 2)

    return df.tail(min(n, len(df)))


def _fmt(val, pct=False, dollar=False, ratio=False) -> str:
    """Quick formatting helper for metric display."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    if pct:
        return f"{val * 100:.1f}%" if abs(val) < 10 else f"{val:.1f}%"
    if dollar:
        return f"${val:,.2f}"
    if ratio:
        return f"{val:.2f}"
    return f"{val:,.2f}"


# ───────────────────────────────────────────────────────────────────────────
# Chart info / explanations (ℹ️ icon next to each chart title)
# ───────────────────────────────────────────────────────────────────────────

CHART_INFO = {
    # ── Income Statement ──
    "Revenue, Gross Profit, Operating and Net Income": {
        "meaning": "Revenue is total sales. Gross Profit = Revenue minus cost of goods sold. "
                   "Operating Income = Gross Profit minus operating expenses (R&D, SGA). "
                   "Net Income = the bottom line after all expenses, taxes, and interest.",
        "reading": "Look for consistent growth across all four bars. A widening gap between "
                   "Revenue and Net Income may signal rising costs. All four growing together "
                   "indicates strong, efficient scaling.",
    },
    "Revenue by Product": {
        "meaning": "Breaks down total revenue by product line or business division, "
                   "showing which segments drive the most sales.",
        "reading": "Diversified revenue across segments is healthier. A single dominant segment "
                   "means high concentration risk. Watch for new segments gaining share — that's "
                   "a sign of successful expansion.",
    },
    "Revenue by Geography": {
        "meaning": "Shows revenue split by geographic region (e.g. US, Europe, Asia).",
        "reading": "Geographic diversification reduces risk from any single market. Rapid growth "
                   "in new regions signals international expansion. Decline in a region may indicate "
                   "competitive pressure or macro headwinds.",
    },
    "Gross, Operating and Net Profit Margin (%)": {
        "meaning": "Margins show profitability as a percentage of revenue. Gross Margin = "
                   "(Revenue − COGS) / Revenue. Operating Margin includes operating costs. "
                   "Net Margin is the final profit percentage after everything.",
        "reading": "Stable or expanding margins = pricing power and operational efficiency. "
                   "Declining margins could mean rising costs, competitive pressure, or heavy "
                   "investment phases. Compare to industry peers for context.",
    },
    "Earnings Per Share (EPS)": {
        "meaning": "EPS = Net Income ÷ shares outstanding. It shows how much profit is earned "
                   "per share of stock. Basic EPS uses actual shares; Diluted includes stock options.",
        "reading": "Steadily rising EPS is the single most important driver of stock price over time. "
                   "Compare Basic vs Diluted — a big gap means heavy stock-based compensation. "
                   "Declining EPS with growing revenue can indicate margin compression.",
    },
    "Revenue YoY Variation (%)": {
        "meaning": "Year-over-Year revenue growth rate. Shows how much revenue increased or "
                   "decreased compared to the same period one year earlier.",
        "reading": "Accelerating YoY growth = business is gaining momentum. Decelerating (but "
                   "still positive) growth is normal as companies get larger. Negative values "
                   "mean revenue is actually shrinking.",
    },
    "QoQ Revenue Variation (%)": {
        "meaning": "Quarter-over-Quarter revenue change. Compares each quarter to the previous one.",
        "reading": "QoQ can be volatile due to seasonality (e.g. Q4 holiday spending). "
                   "Look at the pattern across years, not individual quarters. Consistent negative "
                   "QoQ in non-seasonal quarters is a warning sign.",
    },
    "Operating Expenses": {
        "meaning": "R&D = Research & Development spending. SGA = Selling, General & Administrative "
                   "costs. Together they represent the main operating expenses.",
        "reading": "High R&D spending signals investment in future growth (common in tech). "
                   "Rising SGA may indicate scaling sales efforts. Ideally, operating expenses "
                   "should grow slower than revenue (operating leverage).",
    },
    "EBITDA": {
        "meaning": "Earnings Before Interest, Taxes, Depreciation & Amortization. A widely used "
                   "measure of operating cash profitability that strips out non-cash and financing items.",
        "reading": "Growing EBITDA shows the core business is generating more cash. Often used for "
                   "valuation (EV/EBITDA ratio). Comparing EBITDA to Net Income reveals the impact "
                   "of depreciation, interest, and taxes.",
    },
    "Interest and Other Income": {
        "meaning": "Non-operating income from interest earned on cash/investments and other "
                   "miscellaneous income sources outside the core business.",
        "reading": "Growing interest income often reflects a strong cash position. Large swings "
                   "may indicate one-time gains or losses. Compare to operating income to gauge "
                   "how much profit comes from non-core activities.",
    },
    "Income Tax Expense": {
        "meaning": "The total income tax paid or accrued by the company for the period.",
        "reading": "Rising tax expense usually means growing profits — a good sign. An unusually low "
                   "tax rate may be due to tax credits, loss carryforwards, or international structures. "
                   "Sudden jumps could indicate one-time items.",
    },
    "Income Breakdown": {
        "meaning": "A detailed decomposition of income statement line items showing how revenue "
                   "flows through to net income through various cost and expense categories.",
        "reading": "This waterfall view reveals where profit is being created and consumed. "
                   "Look for which cost buckets are growing fastest relative to revenue.",
    },
    "Per Share Metrics": {
        "meaning": "Key financial metrics divided by shares outstanding: Revenue Per Share, "
                   "Net Income Per Share, and Operating Cash Flow Per Share.",
        "reading": "These show the value each share represents. Rising per-share metrics combined "
                   "with share buybacks = double benefit for shareholders. Flat per-share metrics despite "
                   "revenue growth could mean excessive dilution.",
    },
    "Stock Based Compensation": {
        "meaning": "SBC is the cost of stock options and equity awards given to employees. "
                   "It's a non-cash expense that dilutes existing shareholders.",
        "reading": "Some SBC is normal (attracts talent), but excessive SBC eats into real returns. "
                   "Compare SBC to net income — if SBC is a large percentage, reported profits are "
                   "overstated relative to cash earnings.",
    },
    "Expense Ratios": {
        "meaning": "R&D, Capex, and SBC each expressed as a percentage of revenue. "
                   "Shows how much of every dollar of revenue goes to each expense category.",
        "reading": "Declining ratios = the company is getting more efficient as it scales. "
                   "Rising R&D ratio may be fine if it drives future growth. "
                   "SBC ratio above 10-15% is considered high by most investors.",
    },
    "Effective Tax Rate (%)": {
        "meaning": "The actual percentage of pre-tax income paid as taxes, calculated as "
                   "Tax Expense ÷ Pre-Tax Income.",
        "reading": "Most US companies have effective rates of 15-25%. Very low rates may use "
                   "international tax structures. Rising rates compress net margins. "
                   "Volatile rates often indicate one-time items or loss carryforwards.",
    },
    "Weighted Average Shares Outstanding": {
        "meaning": "The average number of shares during the period. Basic counts actual shares; "
                   "Diluted includes potential shares from options and convertibles.",
        "reading": "Declining share count = the company is buying back stock (returns value to "
                   "shareholders). Rising share count means dilution from SBC or equity raises. "
                   "A widening gap between Basic and Diluted indicates heavy option grants.",
    },
    # ── Cash Flow Statement ──
    "Cash Flows": {
        "meaning": "Operating CF = cash from core business. Investing CF = cash spent on assets "
                   "(usually negative). Financing CF = cash from debt/equity (positive) or "
                   "buybacks/dividends (negative). Free CF = Operating minus CapEx.",
        "reading": "Strong operating cash flow that exceeds net income is a quality signal. "
                   "Negative investing CF is usually good (the company is investing to grow). "
                   "Free Cash Flow is what's actually available to shareholders.",
    },
    "Cash Position": {
        "meaning": "Total cash, cash equivalents, and short-term investments on the balance sheet.",
        "reading": "A growing cash pile provides flexibility for acquisitions, buybacks, or "
                   "weathering downturns. Very high cash relative to market cap may signal "
                   "undervaluation. Low cash with high debt = financial risk.",
    },
    "Capital Expenditure": {
        "meaning": "CapEx is spending on long-term assets like property, equipment, and "
                   "infrastructure. It's an investment in future capacity.",
        "reading": "Rising CapEx often precedes revenue growth (building capacity). "
                   "Compare CapEx to depreciation: CapEx > depreciation means the company is "
                   "expanding its asset base, not just maintaining it.",
    },
    # ── Balance Sheet ──
    "Total Assets": {
        "meaning": "Everything the company owns: cash, receivables, inventory, property, "
                   "intellectual property, goodwill, and other assets.",
        "reading": "Growing total assets generally means the company is expanding. "
                   "A shift from current to non-current assets may mean long-term investment. "
                   "Compare asset growth to revenue growth for efficiency.",
    },
    "Liabilities": {
        "meaning": "Everything the company owes: accounts payable, short-term and long-term debt, "
                   "lease obligations, and other commitments.",
        "reading": "Some leverage is healthy (amplifies returns). But liabilities growing faster "
                   "than assets = deteriorating balance sheet. Watch the current vs non-current "
                   "split — high current liabilities need near-term cash to service.",
    },
    "Stockholders Equity vs Total Debt": {
        "meaning": "Equity = Assets minus Liabilities (book value owned by shareholders). "
                   "Total Debt = all interest-bearing borrowings.",
        "reading": "Equity growing while debt stays flat = strengthening balance sheet. "
                   "Debt exceeding equity (D/E > 1) increases financial risk. Some mature companies "
                   "deliberately use debt for buybacks, reducing equity while boosting EPS.",
    },
    # ── Key Metrics ──
    "P/E Ratio": {
        "meaning": "Price-to-Earnings ratio = Stock Price ÷ EPS. Shows how much investors pay "
                   "per dollar of earnings. Higher P/E = higher growth expectations.",
        "reading": "Rising P/E with stable earnings = market expects acceleration. Falling P/E "
                   "despite growing earnings = market skepticism or sector rotation. Compare to "
                   "the company's historical average and industry peers.",
    },
    "Market Capitalization": {
        "meaning": "Market Capitalization = Stock Price × Shares Outstanding. It's the total "
                   "market value of the company.",
        "reading": "Tracks the overall size and investor sentiment about the company over time. "
                   "Rising market cap with stable P/E means earnings are growing. A surge without "
                   "earnings growth suggests multiple expansion (higher expectations).",
    },
    "Analyst Price Targets": {
        "meaning": "Consensus estimates from Wall Street analysts for future price targets "
                   "(low, median, high) and buy/hold/sell recommendations.",
        "reading": "The spread between low and high targets shows uncertainty. More 'buy' "
                   "recommendations = bullish consensus. Compare current price to the median "
                   "target to see implied upside/downside.",
    },
}


def _chart_insight(fig, ticker: str) -> str:
    """Generate a brief, dynamic insight based on the chart's actual data."""
    traces = fig.data if hasattr(fig, "data") else []
    if not traces:
        return ""

    title = getattr(fig.layout, "meta", "") or ""
    insights = []

    try:
        # Get the primary (first) trace's data
        t0 = traces[0]
        y_vals = [float(v) for v in t0.y if v is not None] if hasattr(t0, "y") and t0.y is not None else []
        x_labels = [str(v) for v in t0.x] if hasattr(t0, "x") and t0.x is not None else []

        if len(y_vals) >= 2:
            first_val, last_val = y_vals[0], y_vals[-1]
            first_label = x_labels[0] if x_labels else "start"
            last_label = x_labels[-1] if x_labels else "latest"

            # Calculate overall change
            if first_val and first_val != 0:
                pct_change = ((last_val - first_val) / abs(first_val)) * 100
                direction = "increased" if pct_change > 0 else "decreased"

                # Format the values
                def _fmt_v(v):
                    av = abs(v)
                    if av >= 1e12:
                        return f"${v/1e12:.2f}T"
                    if av >= 1e9:
                        return f"${v/1e9:.1f}B"
                    if av >= 1e6:
                        return f"${v/1e6:.0f}M"
                    if av >= 1e3:
                        return f"${v/1e3:.0f}K"
                    if av < 1 and av > 0:
                        return f"{v:.1%}"
                    return f"{v:,.0f}"

                # Check if it's a percentage metric (margins, rates)
                is_pct = any(kw in title.lower() for kw in ["margin", "%", "ratio", "rate", "variation", "yoy", "qoq"])

                if is_pct:
                    insights.append(
                        f"<b>{ticker}</b>'s {t0.name or 'metric'} went from "
                        f"{first_val:.1f}% ({first_label}) to {last_val:.1f}% ({last_label})."
                    )
                else:
                    insights.append(
                        f"<b>{ticker}</b>'s {t0.name or 'metric'} {direction} by "
                        f"{abs(pct_change):.0f}% from {_fmt_v(first_val)} ({first_label}) "
                        f"to {_fmt_v(last_val)} ({last_label})."
                    )

            # Recent trend (last 3 periods)
            if len(y_vals) >= 3:
                recent = y_vals[-3:]
                if all(recent[i] < recent[i + 1] for i in range(len(recent) - 1)):
                    insights.append("📈 The recent trend shows consistent growth over the last 3 periods.")
                elif all(recent[i] > recent[i + 1] for i in range(len(recent) - 1)):
                    insights.append("📉 The recent trend shows decline over the last 3 periods.")

        # Multiple traces — compare latest values
        if len(traces) >= 2 and len(y_vals) >= 1:
            for t in traces[1:]:
                t_y = [float(v) for v in t.y if v is not None] if hasattr(t, "y") and t.y is not None else []
                if t_y and t0.name and t.name:
                    latest_ratio = last_val / t_y[-1] if t_y[-1] and t_y[-1] != 0 else None
                    if latest_ratio and latest_ratio > 1.5:
                        insights.append(
                            f"{t0.name} is currently {latest_ratio:.1f}× larger than {t.name}."
                        )

    except Exception:
        pass

    return " ".join(insights) if insights else f"Explore {ticker}'s data in the chart above."


def _render_chart(fig, key: str):
    """Render a chart title (with info ℹ️ icon) + Plotly chart below it."""
    # Extract title stored in fig.layout.meta (plain string) by charts._layout()
    chart_title = ""
    meta = getattr(fig.layout, "meta", None)
    if isinstance(meta, str) and meta:
        chart_title = meta

    _ticker = st.session_state.get("ticker", "STOCK")

    if chart_title:
        # Title row: centered title + small info icon on the right
        _tc1, _tc2 = st.columns([20, 1])
        with _tc1:
            st.markdown(
                f'<p style="text-align:center;font-weight:600;font-size:0.9rem;'
                f'margin:0 0 2px 0;color:#212529;">{chart_title}</p>',
                unsafe_allow_html=True,
            )
        with _tc2:
            info_data = CHART_INFO.get(chart_title, {})
            with st.popover("i"):
                st.markdown(f"### {chart_title}")
                # Section 1: What it means
                meaning = info_data.get("meaning", "")
                if meaning:
                    st.markdown(
                        f'<div style="margin:8px 0 12px 0;">'
                        f'<span style="color:#2475fc;font-weight:600;font-size:0.82rem;'
                        f'text-transform:uppercase;letter-spacing:0.5px;">What it means</span>'
                        f'<p style="margin:4px 0 0 0;color:#495057;font-size:0.88rem;line-height:1.55;">'
                        f'{meaning}</p></div>',
                        unsafe_allow_html=True,
                    )
                # Section 2: How to read it
                reading = info_data.get("reading", "")
                if reading:
                    st.markdown(
                        f'<div style="margin:0 0 12px 0;padding-top:8px;'
                        f'border-top:1px solid #f0f0f0;">'
                        f'<span style="color:#2475fc;font-weight:600;font-size:0.82rem;'
                        f'text-transform:uppercase;letter-spacing:0.5px;">How to read it</span>'
                        f'<p style="margin:4px 0 0 0;color:#495057;font-size:0.88rem;line-height:1.55;">'
                        f'{reading}</p></div>',
                        unsafe_allow_html=True,
                    )

    st.plotly_chart(fig, use_container_width=True, key=key, config={
        "displayModeBar": "hover",
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    })


def _share_row(chart_name: str, ticker: str):
    """Render a compact share link beneath a chart (no button, avoids layout issues)."""
    # Use markdown link styled as small text — avoids button wrapping in narrow columns
    pass  # Share functionality removed to fix layout; can be re-added via chart toolbar


def _plotly_fig_to_mpl(pfig, figsize=(10, 5)):
    """Convert a Plotly figure to a matplotlib figure for PDF export.

    Handles grouped bar charts, stacked bar charts, and line/scatter charts.
    Uses colours from the original Plotly traces.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    import numpy as np

    traces = pfig.data if hasattr(pfig, "data") else []
    if not traces:
        return None

    # Extract title
    title = ""
    meta = getattr(pfig.layout, "meta", None)
    if isinstance(meta, str) and meta:
        title = meta
    elif hasattr(pfig.layout, "title") and hasattr(pfig.layout.title, "text"):
        title = pfig.layout.title.text or ""

    fig, ax = plt.subplots(figsize=figsize)

    bar_traces = [t for t in traces if getattr(t, "type", "bar") == "bar"]
    line_traces = [t for t in traces
                   if getattr(t, "type", "") in ("scatter", "scattergl")]

    # Detect stacked mode
    barmode = getattr(pfig.layout, "barmode", None) or "group"

    if bar_traces:
        x_labels = [str(v) for v in bar_traces[0].x]
        x_pos = np.arange(len(x_labels))

        if barmode == "stack":
            bottom = np.zeros(len(x_labels))
            for t in bar_traces:
                y_vals = np.array([float(v) if v is not None else 0 for v in t.y])
                color = getattr(t.marker, "color", None) or "#4285f4"
                if isinstance(color, (list, tuple)):
                    color = color[0] if color else "#4285f4"
                ax.bar(x_pos, y_vals, 0.7, bottom=bottom,
                       label=t.name or "", color=color, edgecolor="none")
                bottom += y_vals
        else:
            n_bars = len(bar_traces)
            width = 0.8 / max(n_bars, 1)
            for idx, t in enumerate(bar_traces):
                y_vals = [float(v) if v is not None else 0 for v in t.y]
                color = getattr(t.marker, "color", None) or "#4285f4"
                if isinstance(color, (list, tuple)):
                    color = color[0] if color else "#4285f4"
                offset = (idx - (n_bars - 1) / 2) * width
                ax.bar(x_pos + offset, y_vals, width,
                       label=t.name or "", color=color, edgecolor="none")

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)

    for t in line_traces:
        x_labels = [str(v) for v in t.x]
        y_vals = [float(v) if v is not None else 0 for v in t.y]
        color = getattr(t.marker, "color", None) or "#4285f4"
        if isinstance(color, (list, tuple)):
            color = color[0] if color else "#4285f4"
        ax.plot(range(len(y_vals)), y_vals, marker="o",
                label=t.name or "", color=color, linewidth=2)
        if not bar_traces:
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)

    # Smart y-axis formatting
    def _fmt_val(v, _pos):
        if abs(v) >= 1e9:
            return f"{v / 1e9:.0f}B"
        if abs(v) >= 1e6:
            return f"{v / 1e6:.0f}M"
        if abs(v) >= 1e3:
            return f"{v / 1e3:.0f}K"
        if 0 < abs(v) < 1:
            return f"{v:.1%}"
        return f"{v:.0f}"
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_val))

    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    if any(getattr(t, "name", "") for t in traces):
        ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def _generate_section_pdf(figures: list, section_title: str, ticker: str) -> bytes:
    """Generate a multi-page PDF with matplotlib-rendered charts.

    Converts each Plotly figure to a matplotlib chart, then writes all
    charts into a single PDF.  No kaleido dependency required.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from io import BytesIO

    buf = BytesIO()
    added = 0

    with PdfPages(buf) as pdf:
        # Title page
        tfig = plt.figure(figsize=(11, 1))
        tfig.text(0.5, 0.5, f"{ticker} \u2014 {section_title}",
                  ha="center", va="center", fontsize=20, fontweight="bold")
        tfig.patch.set_facecolor("white")
        pdf.savefig(tfig, bbox_inches="tight")
        plt.close(tfig)

        for pfig, _name in figures:
            traces = pfig.data if hasattr(pfig, "data") else []
            has_data = any(
                (hasattr(t, "x") and t.x is not None and len(t.x) > 0)
                or (hasattr(t, "values") and t.values is not None
                    and len(t.values) > 0)
                for t in traces
            )
            if not has_data:
                continue
            try:
                mpl_fig = _plotly_fig_to_mpl(pfig)
                if mpl_fig:
                    pdf.savefig(mpl_fig, bbox_inches="tight", dpi=150)
                    plt.close(mpl_fig)
                    added += 1
            except Exception:
                continue

    if added == 0:
        return b""
    return buf.getvalue()


def render_charts(charts: list, section: str):
    """Render a list of (figure, name) tuples in the selected column layout.

    Skips charts that have no data (empty traces) to avoid blank placeholders
    in the grid layout.  Also stores valid figures in session state for PDF export.
    """
    # Filter out empty charts (no traces or all traces have empty x)
    valid = []
    for fig, name in charts:
        traces = fig.data if hasattr(fig, "data") else []
        has_data = any(
            (hasattr(t, "x") and t.x is not None and len(t.x) > 0)
            or (hasattr(t, "values") and t.values is not None and len(t.values) > 0)
            for t in traces
        )
        if has_data:
            valid.append((fig, name))

    # Store for PDF export
    st.session_state[f"_charts_{section}"] = valid

    # Pre-generate PDF so the download button is immediately ready (single-click)
    _section_title_map = {
        "income": "Income Statement",
        "cashflow": "Cash Flow Statement",
        "balance": "Balance Sheet",
        "keymetrics": "Key Metrics",
    }
    _pdf_state_key = f"_pdf_data_{section}"
    if valid and not st.session_state.get(_pdf_state_key):
        _tk = st.session_state.get("ticker", "STOCK")
        _sec_title = _section_title_map.get(section, section.title())
        _pdf_bytes = _generate_section_pdf(valid, _sec_title, _tk)
        if _pdf_bytes:
            st.session_state[_pdf_state_key] = _pdf_bytes
            st.session_state["_need_pdf_rerun"] = True

    n_cols = st.session_state.layout_cols
    for i in range(0, len(valid), n_cols):
        cols = st.columns(n_cols)
        for j in range(n_cols):
            idx = i + j
            if idx < len(valid):
                fig, name = valid[idx]
                with cols[j]:
                    _render_chart(fig, f"{section}_{name}_{idx}")


def _section_header(title: str, emoji: str, state_key: str, cb_key: str = "",
                    charts_key: str = "") -> bool:
    """Render a clickable section header that toggles section visibility.

    Uses st.columns to place header + PDF button side by side.
    JS PASS 1 styles the parent row with matching background.
    Returns True if the section content should be displayed.
    """
    is_open = st.session_state.get(state_key, True)
    arrow = "\u25B2" if is_open else "\u25BC"
    btn_key = f"hdr_{state_key}"
    _ticker = st.session_state.get("ticker", "STOCK")

    if charts_key:
        hdr_col, pdf_col = st.columns([0.87, 0.13])
    else:
        hdr_col = st.container()
        pdf_col = None

    with hdr_col:
        if st.button(
            f"{emoji}  {title}  {arrow}",
            key=btn_key,
            use_container_width=True,
        ):
            new_val = not is_open
            st.session_state[state_key] = new_val
            if cb_key:
                st.session_state[f"_sync_{cb_key}"] = new_val
            st.rerun()

    if pdf_col is not None:
        with pdf_col:
            _pdf_state = f"_pdf_data_{charts_key}"
            if st.session_state.get(_pdf_state):
                # PDF is pre-generated — show single-click download button
                try:
                    st.download_button(
                        label="PDF",
                        data=st.session_state[_pdf_state],
                        file_name=f"{_ticker}_{charts_key}.pdf",
                        mime="application/pdf",
                        icon=":material/download:",
                        key=f"dl_{charts_key}",
                    )
                except TypeError:
                    st.download_button(
                        label="\u2B07 PDF",
                        data=st.session_state[_pdf_state],
                        file_name=f"{_ticker}_{charts_key}.pdf",
                        mime="application/pdf",
                        key=f"dl_{charts_key}",
                    )
            else:
                # PDF not yet generated (section not expanded yet) — show
                # disabled-looking placeholder that tells user to expand first
                try:
                    st.button("PDF", key=f"gen_pdf_{charts_key}",
                              icon=":material/print:", disabled=True)
                except TypeError:
                    st.button("PDF", key=f"gen_pdf_{charts_key}",
                              disabled=True)

    return is_open


# ───────────────────────────────────────────────────────────────────────────
# Navigation bar (dark, matching original)
# ───────────────────────────────────────────────────────────────────────────

ticker = st.session_state.ticker
current_page = st.session_state.page

# Nav bar with page switching (using <a> links for reliable navigation)
st.markdown(f"""
<div class="nav-bar">
    <span class="nav-logo">📊 OPEN<br>SANKEY</span>
    <a class="nav-link {'active' if current_page == 'sankey' else ''}" href="?page=sankey&ticker={ticker}" target="_self">{ticker} Sankey</a>
    <a class="nav-link {'active' if current_page == 'charts' else ''}" href="?page=charts&ticker={ticker}" target="_self">{ticker} Charts</a>
    <a class="nav-link {'active' if current_page == 'profile' else ''}" href="?page=profile&ticker={ticker}" target="_self">{ticker} Profile</a>
    <a class="nav-link {'active' if current_page == 'earnings' else ''}" href="?page=earnings&ticker={ticker}" target="_self">Earnings Calendar</a>
    <a class="nav-link {'active' if current_page == 'watchlist' else ''}" href="?page=watchlist&ticker={ticker}" target="_self">Watchlist</a>
    <a href="?page=pricing&ticker={ticker}" target="_self" class="nav-link {'active' if current_page == 'pricing' else ''}">Pricing</a>
    <a href="?page=login&ticker={ticker}" target="_self" class="nav-link {'active' if current_page == 'login' else ''}">Sign In</a>
    <button class="nav-expand-btn" id="navExpandSidebar" title="Open sidebar">&#171;</button>
</div>
""", unsafe_allow_html=True)

# ── Sidebar expand click handler (must load with nav bar, not at page end) ──
components.html("""<script>
(function() {
    var doc = window.parent.document;
    if (!doc || !doc.body) return;
    if (doc.body._osSidebarClick) return;   // already bound
    doc.body._osSidebarClick = true;
    doc.body.addEventListener('click', function(e) {
        var btn = e.target.closest('#navExpandSidebar');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        // New Streamlit: stExpandSidebarButton
        var eb = doc.querySelector('[data-testid="stExpandSidebarButton"]');
        if (eb) { eb.click(); return; }
        // Legacy Streamlit: stSidebarCollapsedControl
        var ctrl = doc.querySelector('[data-testid="stSidebarCollapsedControl"] button');
        if (ctrl) { ctrl.click(); }
    });
})();
</script>""", height=0)

# Sync parent (Streamlit Cloud wrapper) URL with the iframe URL so that
# browser refresh preserves the current page.  The Streamlit app runs inside
# a sandboxed iframe that cannot navigate its parent via target="_top", but
# same-origin history.replaceState works.
components.html("""<script>
try {
    var top = window.parent && window.parent.parent;
    if (top && top.history) {
        var s = window.parent.location.search;
        if (top.location.search !== s) {
            top.history.replaceState({}, '', '/' + s);
        }
    }
} catch(e) {}
</script>""", height=0)

# ───────────────────────────────────────────────────────────────────────────
# Hide Streamlit's "Running..." status widget on all pages
# ───────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
    [data-testid="stStatusWidget"] { display: none !important; }
    .stSpinner { display: none !important; }
</style>""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────────────────
# Sidebar (Charts page only – Profile page has no sidebar)
# ───────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Styled GO button CSS
    st.markdown("""<style>
    /* Ticker search form */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
        color: #fff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.05em !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.45rem 1.2rem !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
        background: linear-gradient(135deg, #16213e 0%, #0f3460 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important;
    }
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:active {
        transform: translateY(0px) !important;
    }
    </style>""", unsafe_allow_html=True)

    with st.form("ticker_form", clear_on_submit=False, border=False):
        new_ticker = st.text_input(
            "Ticker",
            value=st.session_state.ticker,
            placeholder="e.g. AAPL, MSFT, TSLA",
        ).upper().strip()
        submitted = st.form_submit_button("GO →")

    if submitted and new_ticker and new_ticker != st.session_state.ticker:
        if validate_ticker(new_ticker):
            st.session_state.ticker = new_ticker
            st.query_params.update({"page": st.session_state.page, "ticker": new_ticker})
            st.rerun()
        else:
            st.error(f"'{new_ticker}' not found.")

    ticker = st.session_state.ticker

    # ---- Company header ----
    info = get_company_info(ticker)
    company_name = info.get("company_name", ticker)
    icon = get_company_icon(ticker, info.get("sector", ""), info.get("industry", ""))

    st.markdown(f"### {icon} {company_name}")

    # ---- Key metrics row ----
    mcap = info.get("market_cap_fmt", "N/A")
    pe = info.get("pe_ratio")
    peg = info.get("peg_ratio")

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-label">Market Cap</div>
            <div class="metric-value">{mcap}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">P/E</div>
            <div class="metric-value">{f'{pe:.2f}' if pe else 'N/A'}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">PEG</div>
            <div class="metric-value">{f'{peg:.2f}' if peg else 'N/A'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ---- Quarterly / Annual toggle (segmented control) ----
    period_col = st.columns(2)
    with period_col[0]:
        if st.button(
            "Quarterly",
            use_container_width=True,
            type="primary" if st.session_state.quarterly else "secondary",
        ):
            st.session_state.quarterly = True
            st.rerun()
    with period_col[1]:
        if st.button(
            "Annual",
            use_container_width=True,
            type="primary" if not st.session_state.quarterly else "secondary",
        ):
            st.session_state.quarterly = False
            st.rerun()

    # ---- Timeframe buttons (segmented control) ----
    tf_cols = st.columns(4)
    for i, tf in enumerate(["1Y", "2Y", "4Y", "MAX"]):
        with tf_cols[i]:
            if st.button(
                tf,
                use_container_width=True,
                type="primary" if st.session_state.timeframe == tf else "secondary",
                key=f"tf_{tf}",
            ):
                st.session_state.timeframe = tf
                st.rerun()

    # Custom timeframe
    with st.expander("🎯 Custom Timeframe"):
        custom_n = st.number_input(
            "Number of periods",
            min_value=1,
            max_value=40,
            value=st.session_state.get("custom_n", 5),
            key="custom_input",
        )
        if st.button("Apply", use_container_width=True, key="apply_custom"):
            st.session_state.timeframe = "CUSTOM"
            st.session_state.custom_n = custom_n
            st.rerun()

    # ---- Analyst Forecast toggle ----
    st.markdown("---")
    st.session_state.show_forecast = st.toggle(
        "📊 Analyst Forecast",
        value=st.session_state.show_forecast,
    )

    # ---- Section checkboxes ----
    st.markdown("---")
    st.session_state.show_income = st.checkbox(
        "Income Statement", value=st.session_state.show_income, key="cb_income"
    )
    st.session_state.show_cashflow = st.checkbox(
        "Cash Flow Statement", value=st.session_state.show_cashflow, key="cb_cf"
    )
    st.session_state.show_balance = st.checkbox(
        "Balance Sheet", value=st.session_state.show_balance, key="cb_bs"
    )
    st.session_state.show_metrics = st.checkbox(
        "Key Metrics", value=st.session_state.show_metrics, key="cb_km"
    )

    # ---- Layout selector ----
    st.markdown("---")
    lc = st.columns(3)
    for i, (ncols, icon) in enumerate([(1, "▬"), (2, "▦"), (3, "▩")]):
        with lc[i]:
            if st.button(
                icon,
                use_container_width=True,
                type="primary" if st.session_state.layout_cols == ncols else "secondary",
                key=f"layout_{ncols}",
            ):
                st.session_state.layout_cols = ncols
                st.rerun()

    # ---- Status ----
    st.markdown(
        '<span class="status-dot"></span> '
        '<span style="color:#34a853;font-size:0.85rem;">up to date</span>',
        unsafe_allow_html=True,
    )


# ───────────────────────────────────────────────────────────────────────────
# Page routing
# ───────────────────────────────────────────────────────────────────────────

if current_page == "profile":
    from profile_page import render_profile_page
    render_profile_page(ticker)
    st.stop()

if current_page == "earnings":
    # Hide sidebar on earnings page (it's a standalone page, not ticker-specific)
    from earnings_page import render_earnings_page
    render_earnings_page()
    st.stop()

if current_page == "login":
    from login_page import render_login_page
    render_login_page()
    st.stop()

if current_page == "pricing":
    from pricing_page import render_pricing_page
    render_pricing_page()
    st.stop()

if current_page == "sankey":
    from sankey_page import render_sankey_page
    render_sankey_page()
    st.stop()

if current_page == "watchlist":
    from watchlist_page import render_watchlist_page
    render_watchlist_page()
    st.stop()

# ───────────────────────────────────────────────────────────────────────────
# Main content area – fetch data & render charts (charts page only)
# ───────────────────────────────────────────────────────────────────────────

quarterly = st.session_state.quarterly

# Fetch all data in parallel (each is cached 1hr, but cold load benefits from concurrency)
from concurrent.futures import ThreadPoolExecutor as _TP
with _TP(max_workers=4) as _pool:
    _f_inc = _pool.submit(get_income_statement, ticker, quarterly)
    _f_bal = _pool.submit(get_balance_sheet, ticker, quarterly)
    _f_cf  = _pool.submit(get_cash_flow, ticker, quarterly)
    _f_fc  = _pool.submit(get_analyst_forecast, ticker)
income_df   = _f_inc.result()
balance_df  = _f_bal.result()
cashflow_df = _f_cf.result()
_forecast_future = _f_fc.result()  # used below

# Quality check: if quarterly CF data has sparse quarters (only Q1+Q4, missing Q2+Q3),
# try yfinance directly for better coverage
if quarterly and not cashflow_df.empty:
    _q_prefixes = set(lbl.split()[0] for lbl in cashflow_df.index if lbl.startswith("Q"))
    if len(_q_prefixes) < 4:  # Missing some quarterly prefixes
        try:
            import yfinance as _yf
            _stock = _yf.Ticker(ticker)
            _raw = getattr(_stock, "quarterly_cashflow", None)
            if _raw is not None and not _raw.empty:
                from data_fetcher import _build_period_df, _CF_MAP
                _yf_cf = _build_period_df(_raw, _CF_MAP, quarterly=True)
                if not _yf_cf.empty and len(_yf_cf) >= 4:
                    _yf_q_prefixes = set(lbl.split()[0] for lbl in _yf_cf.index if lbl.startswith("Q"))
                    if len(_yf_q_prefixes) >= len(_q_prefixes):
                        cashflow_df = _yf_cf
        except Exception:
            pass  # Keep existing CF data

forecast = _forecast_future  # already fetched in parallel above
# Apply timeframe trimming
income_df = _trim_timeframe(income_df)
balance_df = _trim_timeframe(balance_df)
cashflow_df = _trim_timeframe(cashflow_df)

# Compute derived data
margins_df = compute_margins(income_df)
eps_df = compute_eps(income_df, info)
# Use full data for YoY (needs history), then trim
yoy_df = _trim_timeframe(
    compute_revenue_yoy(get_income_statement(ticker, quarterly=quarterly))
)
shares = info.get("shares_outstanding")
per_share_df = compute_per_share(income_df, cashflow_df, shares)
qoq_df = _trim_timeframe(
    compute_qoq_revenue(get_income_statement(ticker, quarterly=quarterly))
)
expense_ratios_df = compute_expense_ratios(income_df, cashflow_df)
ebitda_df = compute_ebitda(income_df, cashflow_df)
tax_rate_df = compute_effective_tax_rate(income_df)

# Try quarterchart.com source for Expense Ratios / Per Share / EBITDA (more reliable data)
try:
    _qc_expense = _trim_timeframe(_opensankey_get_segments(ticker, 14, quarterly=quarterly))
    if not _qc_expense.empty and len(_qc_expense) >= 2:
        # Rename to match chart expectations
        _rename = {}
        for c in _qc_expense.columns:
            cl = c.lower()
            if "r&d" in cl or "research" in cl or "developement" in cl:
                _rename[c] = "R&D to Revenue"
            elif "capex" in cl:
                _rename[c] = "Capex to Revenue"
            elif "stock" in cl or "sbc" in cl:
                _rename[c] = "SBC to Revenue"
        if _rename:
            expense_ratios_df = _qc_expense.rename(columns=_rename)
except Exception:
    pass

try:
    _qc_pershare = _trim_timeframe(_opensankey_get_segments(ticker, 13, quarterly=quarterly))
    if not _qc_pershare.empty and len(_qc_pershare) >= 2:
        _rename = {}
        for c in _qc_pershare.columns:
            cl = c.lower()
            if "revenue" in cl:
                _rename[c] = "Revenue Per Share"
            elif "net income" in cl:
                _rename[c] = "Net Income Per Share"
            elif "operating" in cl or "cash flow" in cl:
                _rename[c] = "Operating Cash Flow Per Share"
        if _rename:
            per_share_df = _qc_pershare.rename(columns=_rename)
except Exception:
    pass

try:
    _qc_ebitda = _trim_timeframe(_opensankey_get_segments(ticker, 5, quarterly=quarterly))
    if not _qc_ebitda.empty and len(_qc_ebitda) >= 2:
        ebitda_df = _qc_ebitda
except Exception:
    pass

income_breakdown_df = pd.DataFrame()
try:
    _qc_incbreak = _trim_timeframe(_opensankey_get_segments(ticker, 12, quarterly=quarterly))
    if not _qc_incbreak.empty and len(_qc_incbreak) >= 2:
        income_breakdown_df = _qc_incbreak
except Exception:
    pass
# Revenue segmentation (product & geography)
product_seg_df = _trim_segment_timeframe(get_revenue_by_product(ticker, quarterly=quarterly))
geo_seg_df = _trim_segment_timeframe(get_revenue_by_geography(ticker, quarterly=quarterly))

# If no data at all
if income_df.empty and balance_df.empty and cashflow_df.empty:
    st.error(
        f"Could not load financial data for **{ticker}**. "
        "This might be due to network issues or the ticker not having "
        "financial statements available on Yahoo Finance."
    )
    st.stop()


# ───────────────────────────────────────────────────────────────────────────
# Analyst Forecast Section (only if toggle is on)
# ───────────────────────────────────────────────────────────────────────────

if st.session_state.show_forecast and forecast:
    # Analyst Forecast has no collapse – always show if toggled on
    _section_header("Analyst Forecast", "📊", "show_forecast", "")

    if st.session_state.show_forecast:
        fc_cols = st.columns(4)
        with fc_cols[0]:
            st.metric("Mean Target", f"${forecast.get('target_mean', 0):.2f}")
        with fc_cols[1]:
            st.metric("High Target", f"${forecast.get('target_high', 0):.2f}")
        with fc_cols[2]:
            st.metric("Low Target", f"${forecast.get('target_low', 0):.2f}")
        with fc_cols[3]:
            upside = forecast.get("upside_pct", 0)
            st.metric(
                "Upside",
                f"{upside:+.1f}%",
                delta=f"{upside:+.1f}%",
                delta_color="normal" if upside > 0 else "inverse",
            )

        rec = forecast.get("recommendation", "")
        n_analysts = forecast.get("num_analysts", "N/A")
        st.caption(f"Recommendation: **{rec.upper() if rec else 'N/A'}** · Analysts: **{n_analysts}**")

        _render_chart(create_analyst_forecast_chart(forecast), "analyst_chart")


# ───────────────────────────────────────────────────────────────────────────
# Income Statement Section – header ALWAYS visible
# ───────────────────────────────────────────────────────────────────────────

_section_header("Income Statement", "📊", "show_income", "cb_income", charts_key="income")

if st.session_state.show_income:
    income_charts = [
        (create_income_chart(income_df), "revenue_income"),
    ]
    # Revenue segmentation charts (FMP key required)
    if not product_seg_df.empty:
        income_charts.append((create_revenue_by_product_chart(product_seg_df), "rev_product"))
    if not geo_seg_df.empty:
        income_charts.append((create_revenue_by_geography_chart(geo_seg_df), "rev_geo"))
    if not margins_df.empty:
        income_charts.append((create_margins_chart(margins_df), "margins"))
    if not eps_df.empty:
        income_charts.append((create_eps_chart(eps_df), "eps"))
    if not yoy_df.empty:
        income_charts.append((create_revenue_yoy_chart(yoy_df), "yoy"))
    if not qoq_df.empty:
        income_charts.append((create_qoq_revenue_chart(qoq_df), "qoq"))

    income_charts.append((create_opex_chart(income_df), "opex"))
    if not ebitda_df.empty:
        income_charts.append((create_ebitda_chart(ebitda_df), "ebitda"))
    income_charts.append((create_tax_chart(income_df), "tax"))
    # Build a richer SBC df: if expense_ratios has SBC-to-Revenue, back out dollar SBC
    _sbc_df = cashflow_df
    if (not expense_ratios_df.empty and "SBC to Revenue" in expense_ratios_df.columns
            and not income_df.empty and "Revenue" in income_df.columns):
        _common = expense_ratios_df.index.intersection(income_df.index)
        if len(_common) >= 2:
            _sbc_vals = (expense_ratios_df.loc[_common, "SBC to Revenue"]
                         * income_df.loc[_common, "Revenue"])
            _sbc_df = pd.DataFrame({"Stock Based Compensation": _sbc_vals}, index=_common)
    income_charts.append((create_sbc_chart(_sbc_df), "sbc"))

    if not expense_ratios_df.empty:
        income_charts.append((create_expense_ratios_chart(expense_ratios_df), "expense_ratios"))
    if not tax_rate_df.empty:
        income_charts.append((create_effective_tax_rate_chart(tax_rate_df), "eff_tax_rate"))

    income_charts.append((create_shares_chart(income_df), "shares"))

    if not income_breakdown_df.empty:
        income_charts.append((create_income_breakdown_chart(income_breakdown_df), "income_breakdown"))

    if not per_share_df.empty:
        income_charts.append((create_per_share_chart(per_share_df), "per_share"))

    render_charts(income_charts, "income")


# ───────────────────────────────────────────────────────────────────────────
# Cash Flow Section – header ALWAYS visible
# ───────────────────────────────────────────────────────────────────────────

_section_header("Cash Flow Statement", "💰", "show_cashflow", "cb_cf", charts_key="cashflow")

if st.session_state.show_cashflow:
    render_charts([
        (create_cash_flow_chart(cashflow_df), "cash_flows"),
        (create_cash_position_chart(balance_df), "cash_pos"),
        (create_capex_chart(cashflow_df), "capex"),
    ], "cashflow")


# ───────────────────────────────────────────────────────────────────────────
# Balance Sheet Section – header ALWAYS visible
# ───────────────────────────────────────────────────────────────────────────

_section_header("Balance Sheet", "🏦", "show_balance", "cb_bs", charts_key="balance")

if st.session_state.show_balance:
    render_charts([
        (create_assets_chart(balance_df), "assets"),
        (create_liabilities_chart(balance_df), "liabilities"),
        (create_equity_debt_chart(balance_df), "equity_debt"),
    ], "balance")


# ───────────────────────────────────────────────────────────────────────────
# Key Metrics Section – header ALWAYS visible
# ───────────────────────────────────────────────────────────────────────────

_section_header("Key Metrics", "📈", "show_metrics", "cb_km", charts_key="keymetrics")

if st.session_state.show_metrics:
    km_charts = []

    # P/E Ratio over time
    if not eps_df.empty and "EPS" in eps_df.columns and info.get("current_price"):
        pe_df = pd.DataFrame(index=eps_df.index)
        price = info["current_price"]
        pe_df["P/E Ratio"] = (price / eps_df["EPS"].replace(0, np.nan)).round(2)
        pe_df = pe_df.dropna()
        if not pe_df.empty:
            km_charts.append((create_pe_chart(pe_df), "pe_ratio"))

    # Metric cards
    m1 = st.columns(4)
    with m1[0]:
        st.metric("Gross Margin", _fmt(info.get("gross_margins"), pct=True))
    with m1[1]:
        st.metric("Operating Margin", _fmt(info.get("operating_margins"), pct=True))
    with m1[2]:
        st.metric("ROE", _fmt(info.get("return_on_equity"), pct=True))
    with m1[3]:
        st.metric("ROA", _fmt(info.get("return_on_assets"), pct=True))

    m2 = st.columns(4)
    with m2[0]:
        st.metric("Debt/Equity", _fmt(info.get("debt_to_equity"), ratio=True))
    with m2[1]:
        st.metric("Current Ratio", _fmt(info.get("current_ratio"), ratio=True))
    with m2[2]:
        st.metric("Quick Ratio", _fmt(info.get("quick_ratio"), ratio=True))
    with m2[3]:
        st.metric("Revenue Growth", _fmt(info.get("revenue_growth"), pct=True))

    if km_charts:
        render_charts(km_charts, "keymetrics")




# ───────────────────────────────────────────────────────────────────────────
# Footer
# ───────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="footer">
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:30px;">
        <div>
            <h3>What is Open Sankey?</h3>
            <p>Open Sankey is a financial visualization tool that helps investors
            track and analyse company financials through interactive charts.
            This is a local clone powered by SEC EDGAR &amp; Yahoo Finance data.</p>
        </div>
        <div>
            <h3>Quick Links</h3>
            <p>
                <a href="#">Home</a><br>
                <a href="#">Earnings Calendar</a><br>
                <a href="#">Watchlist</a>
            </p>
        </div>
        <div>
            <h3>Popular Companies</h3>
            <p>AAPL &middot; MSFT &middot; GOOGL &middot; AMZN &middot; NVDA &middot; TSLA &middot; META &middot; NFLX</p>
        </div>
        <div>
            <h3>Disclaimer</h3>
            <p>This app is for educational and informational purposes only.
            Data is sourced from SEC EDGAR and Yahoo Finance and may not be 100% accurate.
            Not financial advice.</p>
        </div>
    </div>
    <hr style="border-color: #495057; margin: 20px 0;">
    <p style="text-align:center; color:#6c757d;">
        &copy; {datetime.now().year} Open Sankey &middot; Built with Streamlit &middot; Data from SEC EDGAR, FMP &amp; Yahoo Finance
    </p>
</div>
""", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────────────────
# JavaScript: Style section header buttons + connected segmented controls
# ───────────────────────────────────────────────────────────────────────────

components.html("""
<script>
(function initOpenSankey() {
    // Access the parent document (Streamlit main frame)
    var doc = window.parent.document;

    function applyStyles() {
        var main = doc.querySelector('.stMainBlockContainer') || doc.querySelector('[data-testid="stAppViewContainer"]');
        if (!main) return;

        // ---- PASS 0: Clean stale section-row-* classes from ALL blocks ----
        // Streamlit recycles DOM elements across reruns, so a block that was
        // a header row in a previous render may now hold chart content.
        var staleRows = main.querySelectorAll('.section-row-expanded, .section-row-collapsed');
        for (var sr = 0; sr < staleRows.length; sr++) {
            staleRows[sr].classList.remove('section-row-expanded', 'section-row-collapsed');
        }
        var staleBtns = main.querySelectorAll('.section-header-expanded, .section-header-collapsed');
        for (var sb = 0; sb < staleBtns.length; sb++) {
            staleBtns[sb].classList.remove('section-header-expanded', 'section-header-collapsed');
        }

        // ---- PASS 1: Style section header buttons ----
        var sectionNames = ['Income Statement', 'Cash Flow', 'Balance Sheet',
                            'Key Metrics', 'Analyst Forecast'];
        var allBtns = main.querySelectorAll('button');
        for (var i = 0; i < allBtns.length; i++) {
            var text = allBtns[i].textContent || '';
            var isSection = false;
            for (var s = 0; s < sectionNames.length; s++) {
                if (text.indexOf(sectionNames[s]) !== -1) { isSection = true; break; }
            }
            if (!isSection) continue;
            allBtns[i].classList.add(
                (text.indexOf(String.fromCharCode(0x25B2)) !== -1)
                    ? 'section-header-expanded' : 'section-header-collapsed'
            );

            // Style the parent stHorizontalBlock row (contains header + PDF columns)
            var row = allBtns[i].closest('[data-testid="stHorizontalBlock"]');
            if (row) {
                row.classList.add(
                    (text.indexOf(String.fromCharCode(0x25B2)) !== -1)
                        ? 'section-row-expanded' : 'section-row-collapsed'
                );
            }
        }

        // ---- Sidebar segmented controls ----
        var sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            var hBlocks = sidebar.querySelectorAll('[data-testid="stHorizontalBlock"]');
            for (var h = 0; h < hBlocks.length; h++) {
                var cols = hBlocks[h].querySelectorAll('[data-testid="stColumn"]');
                if (cols.length < 2) continue;
                var allBtns = true;
                for (var c = 0; c < cols.length; c++) {
                    if (!cols[c].querySelector('button')) { allBtns = false; break; }
                }
                if (allBtns) {
                    hBlocks[h].classList.add('seg-connected');
                }
            }
        }
    }

    // Apply immediately and after delays for Streamlit lazy rendering
    setTimeout(applyStyles, 300);
    setTimeout(applyStyles, 800);
    setTimeout(applyStyles, 1500);
    setTimeout(applyStyles, 3000);

    // Re-apply on DOM mutations (Streamlit re-renders)
    var observer = new MutationObserver(function() {
        setTimeout(applyStyles, 100);
    });
    observer.observe(doc.body, { childList: true, subtree: true });

    // Sidebar click handler is in a separate early-loading components.html
    // near the nav bar (not here) so it loads before the page finishes.
})();
</script>
""", height=0)

# ───────────────────────────────────────────────────────────────────────────
# Auto-rerun once after PDFs are pre-generated so download buttons appear
# ───────────────────────────────────────────────────────────────────────────
if st.session_state.pop("_need_pdf_rerun", False):
    st.rerun()
