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

    # ── Apple touch icon ─────────────────────────────────────────────────
    if "apple-touch-icon" not in html:
        html = html.replace(
            "</head>",
            '<link rel="apple-touch-icon" href="/og-image.png" />\n</head>',
            1,
        )

    # ── Title ────────────────────────────────────────────────────────────
    _new_title = "QuarterCharts.com \u2014 Stock Charts, Sankey Diagrams, Earnings Calendar & More"
    if _new_title not in html:
        html = re.sub(
            r"<title>[^<]*</title>",
            f"<title>{_new_title}</title>",
            html,
            count=1,
        )

    # ── Meta description ─────────────────────────────────────────────────
    _desc = (
        "Visualize any stock's financials with interactive Sankey diagrams, "
        "quarterly income charts, and company profiles.  Access to "
        "6,000+ tickers from SEC filings."
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
        ld_block = (
            f'<script type="application/ld+json">{org_ld}</script>\n'
            f'<script type="application/ld+json">{website_ld}</script>\n'
            f'<script type="application/ld+json">{app_ld}</script>\n'
        )
        html = html.replace("</head>", f"{ld_block}</head>", 1)

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

    # ── Preconnect hints ─────────────────────────────────────────────────
    if 'rel="preconnect" href="https://www.googletagmanager.com"' not in html:
        links = (
            '<link rel="preconnect" href="https://www.googletagmanager.com">\n'
            '<link rel="preconnect" href="https://www.google-analytics.com">\n'
            '<link rel="dns-prefetch" href="https://financialmodelingprep.com">\n'
        )
        html = html.replace("</head>", f"{links}</head>", 1)

    # ── Noscript fallback for crawlers ───────────────────────────────────
    _noscript = (
        "<noscript>"
        '<div style="max-width:760px;margin:40px auto;font-family:sans-serif;color:#333">'
        "<h1>QuarterCharts &mdash; Financial Data Visualization</h1>"
        "<p>QuarterCharts is a free financial data visualization platform that turns "
        "SEC filings into interactive Sankey diagrams, quarterly income charts, "
        "and company profiles &mdash; all from one search. Covering 6,000+ tickers "
        "for investors who value clarity over clutter.</p>"
        "<ul>"
        '<li><a href="/?page=charts&ticker=AAPL">AAPL Financial Charts</a></li>'
        '<li><a href="/?page=sankey&ticker=AAPL">AAPL Sankey Diagram</a></li>'
        '<li><a href="/?page=earnings">Earnings Calendar</a></li>'
        '<li><a href="/?page=pricing">Pricing Plans</a></li>'
        "</ul>"
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
