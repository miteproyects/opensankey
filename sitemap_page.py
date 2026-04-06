"""
Styled HTML sitemap page for QuarterCharts.
Forces dark theme via Streamlit CSS overrides + st.markdown.
"""

import streamlit as st
import streamlit.components.v1 as components


TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX",
    "GOOG", "JPM", "V", "MA", "UNH", "HD", "PG", "JNJ",
    "BAC", "DIS", "ADBE", "CRM", "PYPL", "INTC", "AMD", "ORCL",
    "CSCO", "QCOM", "AVGO", "TXN", "COST", "WMT",
]

_PAGES = [
    ("Home",              "/?page=home",               "Landing page and site overview",
     "3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z@@9 22 9 12 15 12 15 22"),
    ("Stock Charts",      "/?page=charts&ticker=AAPL",  "8+ years of quarterly and annual charts",
     "18 20 18 10@@12 20 12 4@@6 20 6 14"),
    ("Sankey Diagrams",   "/?page=sankey&ticker=AAPL",  "Income & balance sheet flow diagrams",
     "22 12h-4l-3 9L9 3l-3 9H2"),
    ("Company Profile",   "/?page=profile&ticker=AAPL", "Financials, ratios & key data",
     "20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2@@CIRCLE12,7,4"),
    ("Earnings Calendar", "/?page=earnings",            "Upcoming dates, past results, EPS",
     "RECT3,4,18,18,2,2@@16 2 16 6@@8 2 8 6@@3 10 21 10"),
    ("Watchlist",         "/?page=watchlist",            "Track favorites across all views",
     "POLY12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"),
    ("Enterprise",        "/?page=pricing",              "Auto-charted dashboards + API",
     "RECT2,7,20,14,2,2@@16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"),
    ("Privacy Policy",    "/?page=privacy",              "How we handle your data",
     "12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"),
    ("Terms of Service",  "/?page=terms",                "Usage terms and conditions",
     "14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z@@14 2 14 8 20 8@@16 13 8 13@@16 17 8 17"),
]

_TICKER_SECTIONS = [
    ("Stock Charts",     "charts",  "#3b82f6"),
    ("Sankey Diagrams",  "sankey",  "#8b5cf6"),
    ("Company Profiles", "profile", "#06b6d4"),
]


def render_sitemap_page():
    """Render the visual sitemap page with dark styling."""

    # ── Force dark background on Streamlit containers ──
    st.markdown("""<style>
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"],
    .main .block-container,
    section.main,
    .stApp {
        background-color: #0a0a1a !important;
    }
    [data-testid="stAppViewContainer"] > div,
    .main .block-container {
        background-color: #0a0a1a !important;
    }
    </style>""", unsafe_allow_html=True)

    # ── Header ──
    st.markdown("""
<div style="text-align:center; padding:30px 0 40px;">
    <span style="display:inline-block; padding:5px 16px; border-radius:20px;
        background:rgba(59,130,246,0.12); border:1px solid rgba(59,130,246,0.25);
        color:#60a5fa; font-size:0.72rem; font-weight:600; letter-spacing:1.5px;
        text-transform:uppercase; margin-bottom:16px;">SITEMAP</span>
    <h1 style="font-size:2.4rem; font-weight:700; color:#fff; margin:12px 0 8px;
        letter-spacing:-0.5px;">All Pages</h1>
    <p style="color:#64748b; font-size:1rem; margin:0;">
        Browse everything on QuarterCharts.com</p>
</div>
""", unsafe_allow_html=True)

    # ── Page cards ──
    st.markdown("""
<p style="font-size:0.7rem; font-weight:600; letter-spacing:2px;
    text-transform:uppercase; color:#475569; margin-bottom:16px; padding-left:4px;">
    MAIN PAGES</p>
""", unsafe_allow_html=True)

    cards_html = ""
    for name, href, desc, _ in _PAGES:
        cards_html += f'''
<a href="{href}" target="_self" style="
    display:flex; align-items:center; gap:14px; padding:18px 20px;
    border-radius:12px; background:rgba(255,255,255,0.035);
    border:1px solid rgba(255,255,255,0.07); text-decoration:none;
    transition:all 0.25s ease; cursor:pointer;
" onmouseover="
    this.style.background='rgba(59,130,246,0.08)';
    this.style.borderColor='rgba(59,130,246,0.25)';
    this.style.transform='translateY(-2px)';
    this.style.boxShadow='0 8px 24px rgba(0,0,0,0.3)';
" onmouseout="
    this.style.background='rgba(255,255,255,0.035)';
    this.style.borderColor='rgba(255,255,255,0.07)';
    this.style.transform='none';
    this.style.boxShadow='none';
">
    <div style="flex-shrink:0; width:42px; height:42px; border-radius:10px;
        background:rgba(59,130,246,0.1); display:flex; align-items:center;
        justify-content:center; color:#60a5fa; font-size:1.2rem;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round"><circle cx="12" cy="12" r="1"/></svg>
    </div>
    <div style="flex:1; min-width:0;">
        <div style="font-weight:600; font-size:0.92rem; color:#e2e8f0;
            margin-bottom:3px;">{name}</div>
        <div style="font-size:0.78rem; color:#64748b; line-height:1.3;">{desc}</div>
    </div>
    <div style="flex-shrink:0; color:#334155;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
    </div>
</a>'''

    st.markdown(f"""
<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));
    gap:10px; margin-bottom:48px;">
{cards_html}
</div>
""", unsafe_allow_html=True)

    # ── Ticker sections ──
    st.markdown("""
<p style="font-size:0.7rem; font-weight:600; letter-spacing:2px;
    text-transform:uppercase; color:#475569; margin-bottom:16px; padding-left:4px;">
    BROWSE BY TICKER</p>
""", unsafe_allow_html=True)

    for sec_name, sec_page, sec_color in _TICKER_SECTIONS:
        chips = ""
        for t in TICKERS:
            chips += f'''<a href="/?page={sec_page}&ticker={t}" target="_self" style="
                display:block; text-align:center; padding:10px 6px; border-radius:8px;
                background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06);
                color:#94a3b8; text-decoration:none; font-size:0.82rem; font-weight:600;
                letter-spacing:0.5px; transition:all 0.2s ease;
            " onmouseover="
                this.style.background='{sec_color}22';
                this.style.borderColor='{sec_color}55';
                this.style.color='#fff';
                this.style.transform='translateY(-1px)';
                this.style.boxShadow='0 3px 10px {sec_color}33';
            " onmouseout="
                this.style.background='rgba(255,255,255,0.03)';
                this.style.borderColor='rgba(255,255,255,0.06)';
                this.style.color='#94a3b8';
                this.style.transform='none';
                this.style.boxShadow='none';
            ">{t}</a>\n'''

        st.markdown(f"""
<div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05);
    border-radius:14px; padding:24px 28px; margin-bottom:14px;">
    <div style="display:flex; align-items:flex-start; gap:12px; margin-bottom:18px;">
        <div style="width:10px; height:10px; border-radius:50%;
            background:{sec_color}; margin-top:5px; flex-shrink:0;"></div>
        <div>
            <div style="font-size:1rem; font-weight:600; color:#e2e8f0;
                margin-bottom:2px;">{sec_name}</div>
            <div style="font-size:0.8rem; color:#64748b;">30 popular tickers</div>
        </div>
    </div>
    <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(80px, 1fr));
        gap:6px;">
    {chips}
    </div>
</div>
""", unsafe_allow_html=True)

    # ── XML footer ──
    st.markdown(f"""
<div style="text-align:center; margin-top:40px; padding:24px;
    border-top:1px solid rgba(255,255,255,0.05);">
    <a href="/sitemap.xml" target="_blank" style="color:#475569;
        text-decoration:none; font-size:0.82rem;">View XML Sitemap &rarr;</a>
    <div style="margin-top:8px; font-size:0.72rem; color:#334155;">
        {7 + len(TICKERS) * 3} indexed URLs</div>
</div>
""", unsafe_allow_html=True)
