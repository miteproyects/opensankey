"""
Styled HTML sitemap page for QuarterCharts.
Renders a visual, user-friendly sitemap with grouped sections and ticker grids.
"""

import streamlit as st


TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX",
    "GOOG", "JPM", "V", "MA", "UNH", "HD", "PG", "JNJ",
    "BAC", "DIS", "ADBE", "CRM", "PYPL", "INTC", "AMD", "ORCL",
    "CSCO", "QCOM", "AVGO", "TXN", "COST", "WMT",
]


def render_sitemap_page():
    """Render the visual sitemap page."""

    st.markdown("""
<style>
.sitemap-section {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 20px;
}
.sitemap-section h3 {
    margin: 0 0 6px 0;
    font-size: 1.15rem;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.sitemap-section .section-desc {
    color: #94a3b8;
    font-size: 0.88rem;
    margin-bottom: 18px;
}
.sitemap-section a.page-link {
    display: inline-block;
    color: #60a5fa;
    text-decoration: none;
    font-size: 0.95rem;
    padding: 4px 0;
    transition: color 0.2s;
}
.sitemap-section a.page-link:hover {
    color: #93c5fd;
    text-decoration: underline;
}
.ticker-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
    gap: 8px;
}
.ticker-chip {
    display: block;
    text-align: center;
    padding: 8px 4px;
    border-radius: 8px;
    background: rgba(96, 165, 250, 0.07);
    border: 1px solid rgba(96, 165, 250, 0.15);
    color: #93c5fd;
    text-decoration: none;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.2s ease;
}
.ticker-chip:hover {
    background: rgba(96, 165, 250, 0.18);
    border-color: rgba(96, 165, 250, 0.4);
    color: #bfdbfe;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(96, 165, 250, 0.15);
}
.sitemap-header {
    text-align: center;
    margin-bottom: 32px;
}
.sitemap-header h1 {
    font-size: 2rem;
    color: #f1f5f9;
    margin-bottom: 4px;
}
.sitemap-header p {
    color: #94a3b8;
    font-size: 0.95rem;
}
.sitemap-static-links {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
}
.static-card {
    display: block;
    padding: 16px 20px;
    border-radius: 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    text-decoration: none;
    transition: all 0.2s ease;
}
.static-card:hover {
    background: rgba(96, 165, 250, 0.08);
    border-color: rgba(96, 165, 250, 0.25);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.static-card .card-title {
    color: #e2e8f0;
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 4px;
}
.static-card .card-desc {
    color: #94a3b8;
    font-size: 0.8rem;
    line-height: 1.4;
}
.sitemap-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.06);
    margin: 8px 0 20px 0;
}
.xml-link {
    text-align: center;
    margin-top: 24px;
    padding: 16px;
    border-radius: 10px;
    background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(255,255,255,0.1);
}
.xml-link a {
    color: #64748b;
    text-decoration: none;
    font-size: 0.85rem;
}
.xml-link a:hover {
    color: #94a3b8;
}
</style>
""", unsafe_allow_html=True)

    # ── Header ──
    st.markdown("""
<div class="sitemap-header">
    <h1>Sitemap</h1>
    <p>All pages available on QuarterCharts.com</p>
</div>
""", unsafe_allow_html=True)

    # ── Static Pages ──
    st.markdown("""
<div class="sitemap-section">
    <h3>Pages</h3>
    <p class="section-desc">Main sections of QuarterCharts</p>
    <div class="sitemap-static-links">
        <a href="/?page=home" class="static-card" target="_self">
            <div class="card-title">Home</div>
            <div class="card-desc">Landing page with featured tickers and site overview</div>
        </a>
        <a href="/?page=charts&ticker=AAPL" class="static-card" target="_self">
            <div class="card-title">Stock Charts</div>
            <div class="card-desc">8+ years of quarterly and annual financial charts</div>
        </a>
        <a href="/?page=sankey&ticker=AAPL" class="static-card" target="_self">
            <div class="card-title">Sankey Diagrams</div>
            <div class="card-desc">Income statement &amp; balance sheet flow diagrams</div>
        </a>
        <a href="/?page=profile&ticker=AAPL" class="static-card" target="_self">
            <div class="card-title">Company Profile</div>
            <div class="card-desc">Financials, valuation ratios, and key data points</div>
        </a>
        <a href="/?page=earnings" class="static-card" target="_self">
            <div class="card-title">Earnings Calendar</div>
            <div class="card-desc">Upcoming earnings dates, past results, and EPS surprises</div>
        </a>
        <a href="/?page=watchlist" class="static-card" target="_self">
            <div class="card-title">Watchlist</div>
            <div class="card-desc">Track your favorite stocks across charts and Sankeys</div>
        </a>
        <a href="/?page=pricing" class="static-card" target="_self">
            <div class="card-title">Enterprise</div>
            <div class="card-desc">Automated financial dashboards with API integration</div>
        </a>
        <a href="/?page=privacy" class="static-card" target="_self">
            <div class="card-title">Privacy Policy</div>
            <div class="card-desc">How we handle your data</div>
        </a>
        <a href="/?page=terms" class="static-card" target="_self">
            <div class="card-title">Terms of Service</div>
            <div class="card-desc">Usage terms and conditions</div>
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Ticker sections ──
    _sections = [
        {
            "title": "Stock Charts by Ticker",
            "desc": "Quarterly and annual financial statement charts for popular companies",
            "page": "charts",
        },
        {
            "title": "Sankey Diagrams by Ticker",
            "desc": "Interactive income statement and balance sheet flow diagrams",
            "page": "sankey",
        },
        {
            "title": "Company Profiles by Ticker",
            "desc": "Key financial metrics, ratios, and company overviews",
            "page": "profile",
        },
    ]

    for sec in _sections:
        chips = "\n".join(
            f'        <a href="/?page={sec["page"]}&ticker={t}" class="ticker-chip" target="_self">{t}</a>'
            for t in TICKERS
        )
        st.markdown(f"""
<div class="sitemap-section">
    <h3>{sec["title"]}</h3>
    <p class="section-desc">{sec["desc"]}</p>
    <div class="ticker-grid">
{chips}
    </div>
</div>
""", unsafe_allow_html=True)

    # ── XML sitemap link ──
    st.markdown("""
<div class="xml-link">
    <a href="/sitemap.xml" target="_blank">View XML Sitemap &rarr;</a>
</div>
""", unsafe_allow_html=True)
