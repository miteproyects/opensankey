"""
Pre-startup SEO patcher for Streamlit's index.html.

This script MUST run BEFORE `streamlit run` so that Streamlit reads the
fully-patched index.html into memory on startup.  Called from start.sh.
"""

import json
import os
import re
import sys


def patch():
    try:
        import streamlit as _st
    except ImportError:
        print("[SEO] streamlit not installed, skipping", file=sys.stderr)
        return

    idx = os.path.join(os.path.dirname(_st.__file__), "static", "index.html")
    if not os.path.isfile(idx):
        print(f"[SEO] index.html not found at {idx}", file=sys.stderr)
        return

    with open(idx, "r") as f:
        html = f.read()

    original = html  # keep a copy to detect changes

    # ── Google site verification ─────────────────────────────────────────
    tag = '<meta name="google-site-verification" content="4yRIohYFN8d_gMq4yQUG3sF9n_tbeZqKEL4pp-SlK9A" />'
    if "google-site-verification" not in html:
        html = html.replace("</head>", f"{tag}\n</head>", 1)

    # ── Robots meta ──────────────────────────────────────────────────────
    if 'name="robots"' not in html:
        html = html.replace(
            "</head>",
            '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />\n</head>',
            1,
        )

    # ── Theme color ──────────────────────────────────────────────────────
    if 'name="theme-color"' not in html:
        html = html.replace(
            "</head>",
            '<meta name="theme-color" content="#0a0a1a" />\n</head>',
            1,
        )

    # ── Favicon ─────────────────────────────────────────────────────────
    if 'rel="icon"' not in html:
        html = html.replace(
            "</head>",
            '<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png" />\n'
            '<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192x192.png" />\n'
            '<link rel="apple-touch-icon" href="/favicon-192x192.png" />\n</head>',
            1,
        )

    # ── Title ────────────────────────────────────────────────────────────
    _new_title = "QuarterCharts.com \u2014 Stock Charts, Sankey Diagrams & More"
    if _new_title not in html:
        html = re.sub(
            r"<title>[^<]*</title>",
            f"<title>{_new_title}</title>",
            html,
            count=1,
        )

    # ── Meta description ─────────────────────────────────────────────────
    _desc = (
        "Visualize any stock\u2019s financials with interactive Sankey diagrams, "
        "quarterly charts and company profiles. "
        "6,000+ tickers from SEC filings. Free to start."
    )
    if 'name="description"' not in html:
        html = html.replace(
            "</head>",
            f'<meta name="description" content="{_desc}" />\n</head>',
            1,
        )
    else:
        # Update existing description if it's the old short one
        html = re.sub(
            r'<meta name="description" content="[^"]*"',
            f'<meta name="description" content="{_desc}"',
            html,
            count=1,
        )

    # ── Canonical URL ────────────────────────────────────────────────────
    _url = "https://quartercharts.com/"
    if 'rel="canonical"' not in html:
        html = html.replace(
            "</head>",
            f'<link rel="canonical" href="{_url}" />\n</head>',
            1,
        )

    # ── Open Graph tags ──────────────────────────────────────────────────
    if 'property="og:title"' not in html:
        og_tags = (
            f'<meta property="og:title" content="{_new_title}" />\n'
            f'<meta property="og:description" content="{_desc}" />\n'
            f'<meta property="og:url" content="{_url}" />\n'
            '<meta property="og:type" content="website" />\n'
            '<meta property="og:site_name" content="QuarterCharts" />\n'
            f'<meta property="og:image" content="{_url}og-image.png" />\n'
        )
        html = html.replace("</head>", f"{og_tags}</head>", 1)

    # ── Twitter Card tags ────────────────────────────────────────────────
    if 'name="twitter:card"' not in html:
        tw_tags = (
            '<meta name="twitter:card" content="summary_large_image" />\n'
            f'<meta name="twitter:title" content="{_new_title}" />\n'
            f'<meta name="twitter:description" content="{_desc}" />\n'
            f'<meta name="twitter:image" content="{_url}og-image.png" />\n'
        )
        html = html.replace("</head>", f"{tw_tags}</head>", 1)

    # ── JSON-LD structured data ──────────────────────────────────────────
    if '"@context": "https://schema.org"' not in html:
        org_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "QuarterCharts",
                "url": _url,
                "description": _desc,
                "founder": {"@type": "Person", "name": "Sebasti\u00e1n Flores"},
                "foundingDate": "2024",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{_url}og-image.png",
                    "width": 1200,
                    "height": 630,
                },
                "sameAs": [],
            }
        )
        website_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "QuarterCharts",
                "url": _url,
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": f"{_url}?page=charts&ticker={{search_term_string}}",
                    "query-input": "required name=search_term_string",
                },
            }
        )
        app_ld = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "SoftwareApplication",
                "name": "QuarterCharts",
                "url": _url,
                "applicationCategory": "FinanceApplication",
                "operatingSystem": "Web",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                "screenshot": f"{_url}og-image.png",
                "description": _desc,
            }
        )
        nav_items = [
            {
                "@context": "https://schema.org",
                "@type": "SiteNavigationElement",
                "name": "Stock Charts \u2014 Statements + Key Metrics",
                "description": "8+ years of quarterly and annual charts.",
                "url": f"{_url}?page=charts",
            },
            {
                "@context": "https://schema.org",
                "@type": "SiteNavigationElement",
                "name": "Sankey Diagrams \u2014 Income & Balance Sheet",
                "description": "Click on Sankey nodes for account history.",
                "url": f"{_url}?page=sankey",
            },
            {
                "@context": "https://schema.org",
                "@type": "SiteNavigationElement",
                "name": "Enterprise \u2014 Automated Financial Dashboards",
                "description": "Your accounts, auto-charted. API integration included.",
                "url": f"{_url}?page=pricing",
            },
            {
                "@context": "https://schema.org",
                "@type": "SiteNavigationElement",
                "name": "Company Profile \u2014 Financials & Key Metrics",
                "description": "Explore company financials, valuation ratios, and key data points for any ticker.",
                "url": f"{_url}?page=profile",
            },
            {
                "@context": "https://schema.org",
                "@type": "SiteNavigationElement",
                "name": "Watchlist \u2014 Track Your Favorite Stocks",
                "description": "Save your favorite tickers and track them across charts, Sankeys, and earnings. Free to use.",
                "url": f"{_url}?page=watchlist",
            },
        ]
        nav_ld = "\n".join(
            f'<script type="application/ld+json">{json.dumps(item)}</script>'
            for item in nav_items
        )
        ld_block = (
            f'<script type="application/ld+json">{org_ld}</script>\n'
            f'<script type="application/ld+json">{website_ld}</script>\n'
            f'<script type="application/ld+json">{app_ld}</script>\n'
            f'{nav_ld}\n'
        )
        html = html.replace("</head>", f"{ld_block}</head>", 1)

    # ── SEO: Preload key resources to improve FCP/LCP ──────────────────
    if 'rel="preload"' not in html:
        preloads = (
            '<link rel="preload" href="/static/css/index.D5HInCXB.css" as="style">\n'
        )
        html = html.replace("</head>", f"{preloads}</head>", 1)

    # ── GA4 snippet ──────────────────────────────────────────────────────
    _ga_id = "G-69Y4ELBVWZ"
    if _ga_id not in html:
        ga_snippet = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={_ga_id}"></script>\n'
            "<script>window.dataLayer=window.dataLayer||[];"
            "function gtag(){dataLayer.push(arguments);}"
            f"gtag('js',new Date());gtag('config','{_ga_id}');</script>\n"
        )
        html = html.replace("</head>", f"{ga_snippet}</head>", 1)

    # ── Font-display: swap for Streamlit's bundled SourceSans font ──────
    # Fixes: "Ensure text remains visible during webfont load" (GTmetrix)
    if "font-display-fix" not in html:
        font_fix = (
            '<style id="font-display-fix">'
            "@font-face { font-family: 'Source Sans Pro'; font-display: swap !important; }"
            "@font-face { font-family: 'Source Sans 3'; font-display: swap !important; }"
            "</style>\n"
        )
        html = html.replace("</head>", f"{font_fix}</head>", 1)

    # ── Preconnect hints ─────────────────────────────────────────────────
    if 'rel="preconnect" href="https://www.googletagmanager.com"' not in html:
        links = (
            '<link rel="preconnect" href="https://www.googletagmanager.com">\n'
            '<link rel="preconnect" href="https://www.google-analytics.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="dns-prefetch" href="https://financialmodelingprep.com">\n'
        )
        html = html.replace("</head>", f"{links}</head>", 1)

    # ── Accessibility: ARIA landmarks + skip-nav + heading structure ─────
    # Fixes: "No heading structure", "No page regions" (WAVE alerts)
    if "a11y-landmarks" not in html:
        a11y_script = (
            '<script id="a11y-landmarks">'
            "document.addEventListener('DOMContentLoaded',function(){"
            # Skip-to-content link (visually hidden, focusable)
            "var sk=document.createElement('a');"
            "sk.href='#main-content';sk.textContent='Skip to main content';"
            "sk.className='sr-only';sk.style.cssText="
            "'position:absolute;left:-9999px;top:auto;width:1px;height:1px;"
            "overflow:hidden;z-index:10000';"
            "sk.addEventListener('focus',function(){this.style.cssText="
            "'position:fixed;top:0;left:0;background:#fff;color:#000;"
            "padding:8px 16px;z-index:10000;font-size:16px'});"
            "sk.addEventListener('blur',function(){this.style.cssText="
            "'position:absolute;left:-9999px;top:auto;width:1px;height:1px;"
            "overflow:hidden;z-index:10000'});"
            "document.body.insertBefore(sk,document.body.firstChild);"
            # Observe DOM and assign landmarks once Streamlit renders
            "var obs=new MutationObserver(function(){"
            "var main=document.querySelector('[data-testid=\"stAppViewContainer\"]');"
            "var side=document.querySelector('[data-testid=\"stSidebar\"]');"
            "if(main&&!main.hasAttribute('role')){"
            "main.setAttribute('role','main');main.id='main-content';"
            # Add visually hidden h1
            "var h1=document.createElement('h1');"
            "h1.textContent='QuarterCharts — Stock Charts, Sankey Diagrams & More';"
            "h1.style.cssText='position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden';"
            "main.insertBefore(h1,main.firstChild)}"
            "if(side&&!side.hasAttribute('role')){"
            "side.setAttribute('role','navigation');"
            "side.setAttribute('aria-label','Sidebar navigation')}"
            "});"
            "obs.observe(document.body,{childList:true,subtree:true})"
            "});"
            "</script>\n"
        )
        html = html.replace("</head>", f"{a11y_script}</head>", 1)

    # ── Noscript fallback for crawlers ───────────────────────────────────
    _noscript = (
        "<noscript>"
        '<div style="max-width:760px;margin:40px auto;font-family:sans-serif;color:#333">'
        "<h1>QuarterCharts.com &mdash; Stock Charts, Sankey Diagrams &amp; More</h1>"
        "<p>Visualize any stock's financials with interactive Sankey diagrams, "
        "quarterly charts and company profiles. 6,000+ tickers from SEC filings. "
        "Free to start.</p>"
        "<h2><a href='/?page=charts'>Stock Charts &mdash; Statements + Key Metrics</a></h2>"
        "<p>8+ years of quarterly and annual charts. Visualize income statements, balance sheets, and key financial metrics.</p>"
        "<h2><a href='/?page=sankey'>Sankey Diagrams &mdash; Income &amp; Balance Sheet</a></h2>"
        "<p>Interactive Sankey diagrams for income statements and balance sheets. Click on nodes for account history.</p>"
        "<h2><a href='/?page=pricing'>Enterprise &mdash; Automated Financial Dashboards</a></h2>"
        "<p>Your accounts, auto-charted. API integration included.</p>"
        "<h2><a href='/?page=profile'>Company Profile &mdash; Financials &amp; Key Metrics</a></h2>"
        "<p>Explore company financials, valuation ratios, and key data points for any ticker.</p>"
        "<h2><a href='/?page=watchlist'>Watchlist &mdash; Track Your Favorite Stocks</a></h2>"
        "<p>Save your favorite tickers and track them across charts, Sankeys, and earnings. Free to use.</p>"
        "<h2><a href='/?page=earnings'>Earnings Calendar</a></h2>"
        "<p>Upcoming earnings dates, past results, and EPS surprises for thousands of stocks.</p>"
        '<p><a href="/?page=privacy">Privacy Policy</a> | '
        '<a href="/?page=terms">Terms of Service</a></p>'
        "</div>"
        "</noscript>"
    )
    html = re.sub(r"<noscript>.*?</noscript>", _noscript, html, flags=re.DOTALL)

    # ── Write if changed ─────────────────────────────────────────────────
    if html != original:
        with open(idx, "w") as f:
            f.write(html)
        print(f"[SEO] Patched {idx}", file=sys.stderr, flush=True)
    else:
        print(f"[SEO] No changes needed for {idx}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    patch()
