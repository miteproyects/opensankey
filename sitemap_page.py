"""
Styled HTML sitemap page for QuarterCharts.
Renders via components.html for full dark-theme control.
"""

import streamlit as st
import streamlit.components.v1 as components


TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX",
    "GOOG", "JPM", "V", "MA", "UNH", "HD", "PG", "JNJ",
    "BAC", "DIS", "ADBE", "CRM", "PYPL", "INTC", "AMD", "ORCL",
    "CSCO", "QCOM", "AVGO", "TXN", "COST", "WMT",
]

_ICONS = {
    "Home": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "Stock Charts": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "Sankey Diagrams": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "Company Profile": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "Earnings Calendar": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    "Watchlist": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "Enterprise": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>',
    "Privacy Policy": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "Terms of Service": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
}

_PAGES = [
    ("Home",              "/?page=home",               "Landing page and site overview"),
    ("Stock Charts",      "/?page=charts&ticker=AAPL",  "8+ years of quarterly and annual charts"),
    ("Sankey Diagrams",   "/?page=sankey&ticker=AAPL",  "Income & balance sheet flow diagrams"),
    ("Company Profile",   "/?page=profile&ticker=AAPL", "Financials, ratios, and key data"),
    ("Earnings Calendar", "/?page=earnings",            "Upcoming dates, past results, EPS"),
    ("Watchlist",         "/?page=watchlist",            "Track favorites across all views"),
    ("Enterprise",        "/?page=pricing",              "Auto-charted dashboards + API"),
    ("Privacy Policy",    "/?page=privacy",              "How we handle your data"),
    ("Terms of Service",  "/?page=terms",                "Usage terms and conditions"),
]

_TICKER_SECTIONS = [
    ("Stock Charts",     "charts",  "#3b82f6", "Quarterly & annual financial statement charts"),
    ("Sankey Diagrams",  "sankey",  "#8b5cf6", "Interactive income & balance sheet flows"),
    ("Company Profiles", "profile", "#06b6d4", "Key metrics, ratios, and overviews"),
]


def render_sitemap_page():
    """Render the visual sitemap page."""

    # Build page cards HTML
    page_cards = ""
    for name, href, desc in _PAGES:
        icon = _ICONS.get(name, "")
        page_cards += f'''
        <a href="{href}" class="card" target="_top">
            <div class="card-icon">{icon}</div>
            <div class="card-body">
                <div class="card-title">{name}</div>
                <div class="card-desc">{desc}</div>
            </div>
            <div class="card-arrow">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>
        </a>'''

    # Build ticker sections HTML
    ticker_sections = ""
    for sec_name, sec_page, sec_color, sec_desc in _TICKER_SECTIONS:
        chips = ""
        for t in TICKERS:
            chips += f'<a href="/?page={sec_page}&ticker={t}" class="chip" target="_top" style="--chip-color:{sec_color}">{t}</a>\n'
        ticker_sections += f'''
        <div class="ticker-section">
            <div class="ts-header">
                <div class="ts-dot" style="background:{sec_color}"></div>
                <div>
                    <h3>{sec_name}</h3>
                    <p class="ts-desc">{sec_desc}</p>
                </div>
            </div>
            <div class="chip-grid">{chips}</div>
        </div>'''

    html = f'''
<!DOCTYPE html>
<html>
<head>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0a0a1a;
    color: #e2e8f0;
    padding: 40px 32px 60px;
    -webkit-font-smoothing: antialiased;
  }}

  /* ── Header ── */
  .header {{
    text-align: center;
    margin-bottom: 48px;
  }}
  .header .badge {{
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.25);
    color: #60a5fa;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 16px;
  }}
  .header h1 {{
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}
  .header p {{
    color: #64748b;
    font-size: 0.95rem;
  }}

  /* ── Section labels ── */
  .section-label {{
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #475569;
    margin-bottom: 16px;
    padding-left: 4px;
  }}

  /* ── Page cards ── */
  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 10px;
    margin-bottom: 48px;
  }}
  .card {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 18px;
    border-radius: 12px;
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    text-decoration: none;
    transition: all 0.25s ease;
    cursor: pointer;
  }}
  .card:hover {{
    background: rgba(59,130,246,0.06);
    border-color: rgba(59,130,246,0.2);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }}
  .card-icon {{
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: rgba(59,130,246,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #60a5fa;
  }}
  .card:hover .card-icon {{
    background: rgba(59,130,246,0.18);
  }}
  .card-body {{ flex: 1; min-width: 0; }}
  .card-title {{
    font-weight: 600;
    font-size: 0.9rem;
    color: #e2e8f0;
    margin-bottom: 2px;
  }}
  .card-desc {{
    font-size: 0.78rem;
    color: #64748b;
    line-height: 1.3;
  }}
  .card-arrow {{
    flex-shrink: 0;
    color: #334155;
    transition: color 0.2s, transform 0.2s;
  }}
  .card:hover .card-arrow {{
    color: #60a5fa;
    transform: translateX(3px);
  }}

  /* ── Ticker sections ── */
  .ticker-section {{
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 16px;
  }}
  .ts-header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 18px;
  }}
  .ts-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
  }}
  .ts-header h3 {{
    font-size: 1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 2px;
  }}
  .ts-desc {{
    font-size: 0.8rem;
    color: #64748b;
  }}

  /* ── Ticker chips ── */
  .chip-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 6px;
  }}
  .chip {{
    display: block;
    text-align: center;
    padding: 9px 6px;
    border-radius: 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    color: #94a3b8;
    text-decoration: none;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.2s ease;
  }}
  .chip:hover {{
    background: color-mix(in srgb, var(--chip-color) 15%, transparent);
    border-color: color-mix(in srgb, var(--chip-color) 35%, transparent);
    color: #fff;
    transform: translateY(-1px);
    box-shadow: 0 3px 10px color-mix(in srgb, var(--chip-color) 20%, transparent);
  }}

  /* ── XML footer ── */
  .xml-footer {{
    text-align: center;
    margin-top: 40px;
    padding: 20px;
    border-top: 1px solid rgba(255,255,255,0.05);
  }}
  .xml-footer a {{
    color: #475569;
    text-decoration: none;
    font-size: 0.8rem;
    transition: color 0.2s;
  }}
  .xml-footer a:hover {{ color: #94a3b8; }}
  .xml-footer .count {{
    display: inline-block;
    margin-top: 8px;
    font-size: 0.72rem;
    color: #334155;
  }}
</style>
</head>
<body>

<div class="header">
    <div class="badge">Sitemap</div>
    <h1>All Pages</h1>
    <p>Browse everything available on QuarterCharts.com</p>
</div>

<div class="section-label">Main Pages</div>
<div class="cards-grid">
{page_cards}
</div>

<div class="section-label">Browse by Ticker</div>
{ticker_sections}

<div class="xml-footer">
    <a href="/sitemap.xml" target="_blank">View XML Sitemap &rarr;</a>
    <div class="count">{7 + len(TICKERS) * 3} indexed URLs</div>
</div>

</body>
</html>
'''

    components.html(html, height=1800, scrolling=True)
