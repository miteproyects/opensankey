"""
Crawler-aware pre-rendering middleware for Streamlit (Tornado).

When a known search-engine crawler (Googlebot, Bingbot, etc.) requests a page,
this middleware intercepts the request and serves a fully-formed, content-rich
HTML page instead of the Streamlit SPA shell — which crawlers can't render
because it relies on WebSocket + React hydration.

Normal users get the regular Streamlit app experience (no change).

Approach:
  1. Detect crawler User-Agent in Tornado's request pipeline
  2. Parse ?page= and ?ticker= query params
  3. Serve a static, SEO-optimised HTML page with:
     - Per-page <title>, meta description, canonical URL, OG/Twitter tags
     - JSON-LD structured data (Organization, WebSite, BreadcrumbList)
     - Real text content describing the page
     - Internal links for crawl-path discovery
     - Proper heading hierarchy (h1 → h2 → h3)

Called from app.py at startup — injects into Streamlit's Tornado router
using the same technique as price_api.py.
"""

import json
import logging
import re
import time
from urllib.parse import urlencode, parse_qs, urlparse

import tornado.web

logger = logging.getLogger(__name__)

# ── Known crawler User-Agent patterns ──────────────────────────────────────
CRAWLER_RE = re.compile(
    r"Googlebot|Bingbot|Slurp|DuckDuckBot|Baiduspider|YandexBot|Sogou|Exabot|"
    r"facebot|facebookexternalhit|ia_archiver|Twitterbot|LinkedInBot|Applebot|PetalBot|"
    r"SemrushBot|AhrefsBot|MJ12bot|Screaming Frog|"
    r"Chrome-Lighthouse|Google-InspectionTool|GoogleOther",
    re.IGNORECASE,
)

SITE = "https://quartercharts.com"
SITE_NAME = "QuarterCharts"
SITE_TITLE = "QuarterCharts.com — Stock Charts, Sankey Diagrams & More"
SITE_DESC = (
    "Visualize any stock's financials with interactive Sankey diagrams, "
    "quarterly charts and company profiles. "
    "6,000+ tickers from SEC filings. Free to start."
)
OG_IMAGE = f"{SITE}/og-image.png"

# 30 popular tickers (same as sitemap.xml)
TOP_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX",
    "GOOG", "JPM", "V", "MA", "UNH", "HD", "PG", "JNJ", "BAC", "DIS",
    "ADBE", "CRM", "PYPL", "INTC", "AMD", "ORCL", "CSCO", "QCOM",
    "AVGO", "TXN", "COST", "WMT",
]

# ── Per-page SEO metadata ──────────────────────────────────────────────────
PAGE_META = {
    "home": {
        "title": SITE_TITLE,
        "desc": SITE_DESC,
        "h1": "QuarterCharts — Stock Charts, Sankey Diagrams & More",
        "content": (
            "QuarterCharts helps you visualize any public company's financials "
            "with interactive Sankey diagrams, quarterly and annual charts, "
            "and detailed company profiles. Built from SEC filings covering "
            "6,000+ tickers. Free to start — no credit card required."
        ),
    },
    "charts": {
        "title": "Stock Charts — Quarterly & Annual Financial Statements | QuarterCharts",
        "desc": "Interactive quarterly and annual charts for income statements, balance sheets, cash flow, and key financial metrics. 8+ years of data from SEC filings.",
        "h1": "Stock Charts — Statements & Key Metrics",
        "content": (
            "Explore 8+ years of quarterly and annual financial charts. "
            "Visualize income statements, balance sheets, cash flow statements, "
            "and key financial metrics for 6,000+ publicly traded companies. "
            "Data sourced directly from SEC filings."
        ),
    },
    "sankey": {
        "title": "Sankey Diagrams — Income Statement & Balance Sheet Flows | QuarterCharts",
        "desc": "Interactive Sankey diagrams showing how revenue flows through expenses to net income, and how assets relate to liabilities. Click nodes for account history.",
        "h1": "Sankey Diagrams — Income & Balance Sheet",
        "content": (
            "Visualize financial flows with interactive Sankey diagrams. "
            "See how revenue flows through cost of goods, operating expenses, "
            "interest, and taxes to net income. Explore balance sheet structure "
            "showing assets, liabilities, and equity. Click any node to see "
            "its historical trend."
        ),
    },
    "profile": {
        "title": "Company Profile — Financials & Key Metrics | QuarterCharts",
        "desc": "Comprehensive company profiles with financials, valuation ratios, key data points, and analyst estimates for any publicly traded stock.",
        "h1": "Company Profile — Financials & Key Metrics",
        "content": (
            "Explore comprehensive company profiles including financial "
            "summaries, valuation ratios (P/E, P/S, P/B, EV/EBITDA), "
            "growth metrics, profitability margins, and key data points. "
            "Data updated regularly from SEC filings and market sources."
        ),
    },
    "earnings": {
        "title": "Earnings Calendar — Upcoming Dates & EPS Surprises | QuarterCharts",
        "desc": "Upcoming earnings dates, past results, and EPS surprises for thousands of publicly traded stocks.",
        "h1": "Earnings Calendar",
        "content": (
            "Track upcoming earnings dates, past results, and EPS surprises. "
            "See which companies are reporting this week, compare actual vs. "
            "estimated earnings, and discover earnings beats and misses "
            "across thousands of publicly traded companies."
        ),
    },
    "watchlist": {
        "title": "Watchlist — Track Your Favorite Stocks | QuarterCharts",
        "desc": "Save your favorite tickers and track them across charts, Sankeys, and earnings. Free to use.",
        "h1": "Watchlist — Track Your Favorite Stocks",
        "content": (
            "Build and manage your personal stock watchlist. "
            "Save your favorite tickers and quickly access their charts, "
            "Sankey diagrams, and earnings data. Free to use — just sign in "
            "with your Google account."
        ),
    },
    "pricing": {
        "title": "Enterprise — Automated Financial Dashboards | QuarterCharts",
        "desc": "Automated financial dashboards for your business. API integration, custom branding, and team collaboration. Contact us for pricing.",
        "h1": "Enterprise — Automated Financial Dashboards",
        "content": (
            "QuarterCharts Enterprise provides automated financial dashboards "
            "for your organization. Features include API integration, custom "
            "branding, team collaboration, and automated report generation. "
            "Contact our team to learn more about enterprise pricing."
        ),
    },
    "login": {
        "title": "Sign In | QuarterCharts",
        "desc": "Sign in to QuarterCharts with your Google account to access your watchlist, saved charts, and personalized features.",
        "h1": "Sign In to QuarterCharts",
        "content": (
            "Sign in with your Google account to access your personal watchlist, "
            "saved charts, and premium features. New users can create a free "
            "account in seconds."
        ),
    },
    "privacy": {
        "title": "Privacy Policy | QuarterCharts",
        "desc": "QuarterCharts privacy policy — how we collect, use, and protect your data.",
        "h1": "Privacy Policy",
        "content": (
            "This privacy policy describes how QuarterCharts collects, uses, "
            "and protects your personal information when you use our services."
        ),
    },
    "terms": {
        "title": "Terms of Service | QuarterCharts",
        "desc": "QuarterCharts terms of service — usage terms and conditions.",
        "h1": "Terms of Service",
        "content": (
            "These terms of service govern your use of QuarterCharts. "
            "By using our platform, you agree to these terms."
        ),
    },
}


def _ticker_meta(page: str, ticker: str) -> dict:
    """Generate per-ticker SEO metadata."""
    t = ticker.upper()
    if page == "charts":
        return {
            "title": f"{t} Stock Charts — Quarterly & Annual Financials | QuarterCharts",
            "desc": (
                f"Interactive financial charts for {t}. Visualize {t}'s income statement, "
                f"balance sheet, cash flow, and key metrics. 8+ years of quarterly and annual data."
            ),
            "h1": f"{t} — Stock Charts & Financial Statements",
            "content": (
                f"Explore {t}'s financial data with interactive charts. "
                f"View quarterly and annual income statements, balance sheets, "
                f"cash flow statements, and key financial metrics including "
                f"revenue, net income, EPS, margins, and growth rates. "
                f"Data sourced from SEC filings, updated regularly."
            ),
        }
    elif page == "sankey":
        return {
            "title": f"{t} Sankey Diagram — Financial Flows Visualized | QuarterCharts",
            "desc": (
                f"Interactive Sankey diagram for {t}. See how {t}'s revenue flows to net income "
                f"and how assets relate to liabilities. Click nodes for historical trends."
            ),
            "h1": f"{t} — Sankey Diagram",
            "content": (
                f"Visualize {t}'s financial flows with an interactive Sankey diagram. "
                f"Trace how revenue flows through COGS, operating expenses, interest, "
                f"and taxes to net income. Explore {t}'s balance sheet showing the "
                f"relationship between assets, liabilities, and shareholders' equity. "
                f"Click any node to view its historical trend."
            ),
        }
    elif page == "profile":
        return {
            "title": f"{t} Company Profile — Financials & Valuation | QuarterCharts",
            "desc": (
                f"Comprehensive {t} company profile with financials, valuation ratios, "
                f"analyst estimates, and key metrics."
            ),
            "h1": f"{t} — Company Profile",
            "content": (
                f"Explore {t}'s comprehensive company profile including financial "
                f"summaries, valuation ratios (P/E, P/S, P/B, EV/EBITDA), "
                f"profitability margins, growth metrics, dividend data, and "
                f"analyst estimates. Updated regularly from SEC filings."
            ),
        }
    return PAGE_META.get(page, PAGE_META["home"])


def _canonical(page: str, ticker: str = "") -> str:
    """Build canonical URL for a page."""
    params = {"page": page}
    if ticker:
        params["ticker"] = ticker.upper()
    return f"{SITE}/?{urlencode(params)}"


def _build_nav_links() -> str:
    """Generate internal navigation links for crawler discovery."""
    links = [
        ("Home", f"{SITE}/"),
        ("Stock Charts", f"{SITE}/?page=charts"),
        ("Sankey Diagrams", f"{SITE}/?page=sankey"),
        ("Company Profiles", f"{SITE}/?page=profile"),
        ("Earnings Calendar", f"{SITE}/?page=earnings"),
        ("Watchlist", f"{SITE}/?page=watchlist"),
        ("Enterprise Pricing", f"{SITE}/?page=pricing"),
    ]
    items = " | ".join(f'<a href="{url}">{label}</a>' for label, url in links)
    return f'<nav aria-label="Main navigation"><p>{items}</p></nav>'


def _build_ticker_links(current_page: str) -> str:
    """Generate links to all 30 top tickers for the current page type."""
    links = []
    for t in TOP_TICKERS:
        url = f"{SITE}/?page={current_page}&ticker={t}"
        links.append(f'<a href="{url}">{t}</a>')
    return (
        f'<section aria-label="Popular tickers">'
        f'<h2>Popular Tickers</h2>'
        f'<p>{" · ".join(links)}</p>'
        f'</section>'
    )


def _build_cross_links(ticker: str) -> str:
    """For a ticker page, link to the same ticker on other page types."""
    t = ticker.upper()
    links = [
        (f"{t} Charts", f"{SITE}/?page=charts&ticker={t}"),
        (f"{t} Sankey", f"{SITE}/?page=sankey&ticker={t}"),
        (f"{t} Profile", f"{SITE}/?page=profile&ticker={t}"),
    ]
    items = " | ".join(f'<a href="{url}">{label}</a>' for label, url in links)
    return f'<section aria-label="Related pages"><h2>Also see</h2><p>{items}</p></section>'


def _breadcrumb_ld(page: str, ticker: str = "") -> str:
    """Generate BreadcrumbList JSON-LD."""
    items = [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
    ]
    page_names = {
        "charts": "Stock Charts", "sankey": "Sankey Diagrams",
        "profile": "Company Profile", "earnings": "Earnings Calendar",
        "watchlist": "Watchlist", "pricing": "Enterprise",
        "login": "Sign In", "privacy": "Privacy Policy", "terms": "Terms of Service",
    }
    if page in page_names:
        items.append({
            "@type": "ListItem",
            "position": 2,
            "name": page_names[page],
            "item": f"{SITE}/?page={page}",
        })
    if ticker:
        items.append({
            "@type": "ListItem",
            "position": 3,
            "name": ticker.upper(),
            "item": _canonical(page, ticker),
        })

    ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }
    return f'<script type="application/ld+json">{json.dumps(ld)}</script>'


def _org_ld() -> str:
    ld = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME,
        "url": SITE,
        "description": SITE_DESC,
        "logo": {"@type": "ImageObject", "url": OG_IMAGE, "width": 1200, "height": 630},
    }
    return f'<script type="application/ld+json">{json.dumps(ld)}</script>'


def render_prerender_html(page: str, ticker: str = "") -> str:
    """Build a complete HTML page for crawlers."""
    if ticker and page in ("charts", "sankey", "profile"):
        meta = _ticker_meta(page, ticker)
    else:
        meta = PAGE_META.get(page, PAGE_META["home"])

    canonical = _canonical(page, ticker) if page != "home" else SITE + "/"
    title = meta["title"]
    desc = meta["desc"]
    h1 = meta["h1"]
    content = meta["content"]

    nav = _build_nav_links()
    ticker_links = ""
    cross_links = ""

    if page in ("charts", "sankey", "profile"):
        ticker_links = _build_ticker_links(page)
        if ticker:
            cross_links = _build_cross_links(ticker)

    breadcrumb = _breadcrumb_ld(page, ticker)
    org = _org_ld()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:image" content="{OG_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{OG_IMAGE}">
<meta name="google-site-verification" content="4yRIohYFN8d_gMq4yQUG3sF9n_tbeZqKEL4pp-SlK9A">
<meta name="theme-color" content="#0a0a1a">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png">
<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192x192.png">
<link rel="apple-touch-icon" href="/favicon-192x192.png">
{breadcrumb}
{org}
<style>
body {{ font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, sans-serif;
       max-width: 960px; margin: 0 auto; padding: 24px; color: #333; line-height: 1.6; }}
h1 {{ color: #0a0a1a; font-size: 2em; margin-bottom: 0.5em; }}
h2 {{ color: #1a1a3a; font-size: 1.4em; margin-top: 1.5em; }}
a {{ color: #1a73e8; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
nav p {{ font-size: 0.95em; }}
footer {{ margin-top: 3em; padding-top: 1em; border-top: 1px solid #eee; font-size: 0.85em; color: #666; }}
</style>
</head>
<body>
<header>
{nav}
</header>
<main role="main" id="main-content">
<h1>{h1}</h1>
<p>{content}</p>
{cross_links}
{ticker_links}
</main>
<footer>
<p>&copy; 2024-2026 {SITE_NAME}. All rights reserved.</p>
<p><a href="{SITE}/?page=privacy">Privacy Policy</a> | <a href="{SITE}/?page=terms">Terms of Service</a></p>
<p><a href="{SITE}/sitemap.xml">Sitemap</a></p>
</footer>
</body>
</html>"""
    return html


# ── In-memory HTML cache for faster responses ─────────────────────────────
_html_cache: dict = {}
_CACHE_TTL = 3600  # 1 hour

_VALID_PAGES = {
    "home", "charts", "sankey", "profile", "earnings",
    "watchlist", "pricing", "login", "privacy", "terms",
}


def _get_cached_html(page: str, ticker: str) -> str:
    """Return pre-rendered HTML, using a 1-hour memory cache."""
    cache_key = f"{page}:{ticker}"
    now = time.time()
    cached = _html_cache.get(cache_key)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return cached["html"]
    html = render_prerender_html(page, ticker)
    _html_cache[cache_key] = {"html": html, "ts": now}
    return html


def inject_crawler_prerender():
    """
    Monkey-patch Tornado's RequestHandler.prepare() to intercept crawler
    requests and serve pre-rendered HTML BEFORE Streamlit processes them.

    Uses the same monkey-patching approach as security_headers.py
    (set_default_headers), which is proven to work with Streamlit.

    Must be called ONCE at startup. Works even before Streamlit starts
    serving — the monkey-patch is applied globally.
    """
    try:
        from tornado.web import RequestHandler

        _original_prepare = RequestHandler.prepare

        def _crawler_aware_prepare(self):
            """Intercept crawler requests and serve pre-rendered HTML."""
            ua = self.request.headers.get("User-Agent", "")

            # Only intercept root page requests (not /static/*, /_stcore/*, /api/*, etc.)
            path = self.request.path
            if path in ("/", "") and CRAWLER_RE.search(ua):
                # Parse query params
                page = self.get_argument("page", "home").lower()
                ticker = self.get_argument("ticker", "").upper()

                if page not in _VALID_PAGES:
                    page = "home"

                html = _get_cached_html(page, ticker)

                self.set_status(200)
                self.set_header("Content-Type", "text/html; charset=utf-8")
                self.set_header("X-Robots-Tag", "index, follow")
                self.set_header("Cache-Control", "public, max-age=3600, s-maxage=86400")
                self.set_header("Vary", "User-Agent")
                self.write(html)
                self.finish()
                logger.info(
                    f"[prerender] Served: page={page} ticker={ticker} "
                    f"ua={ua[:50]}"
                )
                return  # Skip normal Streamlit processing

            # Not a crawler or not a root request — proceed normally
            return _original_prepare(self)

        RequestHandler.prepare = _crawler_aware_prepare
        logger.info("[prerender] Crawler-aware prepare() injected successfully.")
        print("[prerender] Crawler pre-render handler active", flush=True)
        return True

    except Exception as e:
        logger.error(f"[prerender] Injection failed: {e}")
        print(f"[prerender] ERROR: {e}", flush=True)
        return False
