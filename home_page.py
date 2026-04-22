"""Landing / Home page for Quarter Charts."""
import streamlit as st
import streamlit.components.v1 as components


def _get_allowed_tickers_json():
    """Return JSON array of allowed tickers for the current user, or null if ALL.
    Returns: (allowed_json, redirect_blocked_json, redirect_allowed_json)
    """
    import json
    try:
        from database import get_user_plan_access
        _uid = st.session_state.get("user_id") if st.session_state.get("logged_in") else None
        access = get_user_plan_access(_uid)
        allowed = access["allowed_tickers"]
        redirect = access.get("redirect_blocked", "pricing")
        redir_ok = access.get("redirect_allowed", "charts")
        if allowed is None:
            return "null", json.dumps(redirect), json.dumps(redir_ok)
        return json.dumps(sorted(allowed)), json.dumps(redirect), json.dumps(redir_ok)
    except Exception:
        return "null", '"pricing"', '"charts"'


def render_home_page():
    """Full-width marketing landing page with ticker search."""

    # ── hide default Streamlit chrome + force dark background ──
    st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 0 !important; max-width: 100% !important; }
    footer { display: none !important; }
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], .main {
        background: #0B1120 !important;
    }
    /* Eliminate Streamlit default gaps around the iframe */
    [data-testid="stVerticalBlockBorderWrapper"] {
        gap: 0 !important;
    }
    .stElementContainer {
        margin: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── ENTIRE home page as a single components.html block ──
    # This guarantees: no Streamlit style interference, JS works,
    # and the whole page is one seamless visual.
    _allowed_json, _redir_json, _redir_ok_json = _get_allowed_tickers_json()
    # Placeholder tickers = admin-managed ticker pool from DB
    import json as _json
    from database import get_ticker_pool
    _ticker_pool = _json.dumps(get_ticker_pool())

    # ── Load pricing plans from DB (single source of truth with pricing_page.py) ──
    try:
        from database import get_all_plans
        _hp_plans = [p for p in get_all_plans(active_only=True) if p.get("slug") != "no-login"]
    except Exception:
        _hp_plans = []

    def _hp_pricing_card(plan):
        """Build a single .pcard block matching homepage styling, fed from DB."""
        feats = plan.get("features", [])
        if isinstance(feats, str):
            try:
                feats = _json.loads(feats)
            except Exception:
                feats = []
        slug = plan.get("slug", "")
        name = plan.get("name", "Plan")
        try:
            price_monthly = float(plan.get("price_monthly", 0) or 0)
        except Exception:
            price_monthly = 0.0
        is_popular = bool(plan.get("is_popular", False))
        cta_text = plan.get("cta_text", "Get Started")
        cta_url = plan.get("cta_url", "") or "/?page=pricing"
        if cta_url.startswith("?"):
            cta_url = "/" + cta_url
        # Price display
        if slug == "enterprise":
            amt_html = ('<div class="amt" style="font-size:2rem;">Custom</div>'
                        '<div class="per">contact us</div>')
        elif price_monthly <= 0:
            amt_html = '<div class="amt">$0</div><div class="per">forever</div>'
        else:
            amt_html = (f'<div class="amt">${price_monthly:.0f}</div>'
                        '<div class="per">/ month</div>')
        # Auto-prepend "Tickers available: …" for plans with a limited pool.
        # Mirrors pricing_page.py: plans with allowed_tickers != "ALL" (and not
        # empty) pull the live admin-managed list via get_ticker_pool(), so the
        # NSFQ "🎯 Manage Available Tickers" tab is the single source of truth.
        _tk_html = ""
        _allowed_tk = (plan.get("allowed_tickers", "") or "").strip().upper()
        if _allowed_tk and _allowed_tk != "ALL":
            try:
                from database import get_ticker_pool as _gtp
                _pool = _gtp()
            except Exception:
                _pool = [t.strip() for t in _allowed_tk.split(",") if t.strip()]
            if _pool:
                if len(_pool) > 1:
                    _tk_line = (f"Tickers available: {', '.join(_pool[:-1])} "
                                f"&amp; {_pool[-1]}")
                else:
                    _tk_line = f"Tickers available: {_pool[0]}"
                _tk_html = f"<li>{_tk_line}</li>"

        items = _tk_html + "".join(f"<li>{f}</li>" for f in feats)
        pop_class = " pop" if is_popular else ""
        return (
            f'<div class="pcard{pop_class}">'
            f'<div class="tier">{name}</div>'
            f'{amt_html}'
            f'<ul>{items}</ul>'
            f'<a class="btn-primary" style="display:block;text-align:center;" '
            f'href="{cta_url}" target="_top">{cta_text}</a>'
            '</div>'
        )

    if _hp_plans:
        _pricing_cards_html = "".join(_hp_pricing_card(p) for p in _hp_plans)
    else:
        _pricing_cards_html = (
            '<div class="pcard"><div class="tier">Pricing</div>'
            '<div class="amt">&mdash;</div><div class="per">unavailable</div>'
            '<a class="btn-primary" style="display:block;text-align:center;" '
            'href="/?page=pricing" target="_top">View Pricing</a></div>'
        )

    components.html(f"""
    <script>var __ALLOWED_TICKERS = {_allowed_json}; var __REDIR_PAGE = {_redir_json}; var __REDIR_ALLOWED = {_redir_ok_json}; var __TICKER_POOL = {_ticker_pool};</script>"""
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0B1120;
            color: #F1F5F9;
            overflow-x: hidden;
        }
        a { text-decoration: none; }

        /* ── HERO ── */
        .hero {
            text-align: center;
            padding: 80px 24px 0;
            background:
                radial-gradient(ellipse 80% 60% at 50% -10%, rgba(59,130,246,.35), transparent),
                #0B1120;
        }
        .hero-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 999px;
            font-size: .8rem;
            font-weight: 600;
            letter-spacing: .04em;
            background: rgba(59,130,246,.15);
            color: #3B82F6;
            border: 1px solid rgba(59,130,246,.3);
            margin-bottom: 28px;
        }
        .hero h1 {
            font-size: clamp(2.2rem, 5vw, 3.8rem);
            font-weight: 800;
            line-height: 1.12;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #fff 30%, #3B82F6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero .sub {
            font-size: 1.15rem;
            color: #94A3B8;
            max-width: 620px;
            margin: 0 auto 36px;
            line-height: 1.6;
        }

        /* ── SEARCH BAR ── */
        @keyframes borderGlow {
            0%, 100% { border-color: #3B82F6; box-shadow: 0 0 20px rgba(59,130,246,.15), inset 0 0 20px rgba(59,130,246,.03); }
            50% { border-color: #818CF8; box-shadow: 0 0 28px rgba(129,140,248,.2), inset 0 0 20px rgba(129,140,248,.04); }
        }
        @keyframes pulseIcon {
            0%, 100% { opacity: .6; }
            50% { opacity: 1; }
        }
        .search-wrap {
            max-width: 580px;
            margin: 0 auto 20px;
            text-align: center;
        }
        .search-bar {
            display: flex;
            align-items: center;
            max-width: 580px;
            margin: 0 auto;
            background: linear-gradient(135deg, #0F172A 0%, #131B2E 100%);
            border: 1.5px solid #3B82F6;
            border-radius: 18px;
            padding: 8px 8px 8px 20px;
            animation: borderGlow 3s ease-in-out infinite;
            position: relative;
        }
        .search-bar:focus-within {
            border-color: #60A5FA;
            box-shadow: 0 0 30px rgba(96,165,250,.3), inset 0 0 20px rgba(59,130,246,.05);
            animation: none;
        }
        .search-bar .s-icon {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            margin-right: 14px;
            animation: pulseIcon 2.5s ease-in-out infinite;
        }
        .search-bar:focus-within .s-icon { animation: none; opacity: 1; }
        .search-bar input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: #FFFFFF;
            font-size: 1.08rem;
            font-family: inherit;
            padding: 12px 0;
            min-width: 0;
            font-weight: 500;
        }
        .search-bar input::placeholder { color: #64748B; transition: color .2s; }
        .search-bar:focus-within input::placeholder { color: #94A3B8; }
        .search-bar button {
            flex-shrink: 0;
            background: linear-gradient(135deg, #3B82F6, #2563EB);
            color: #fff;
            border: none;
            border-radius: 14px;
            padding: 12px 28px;
            font-size: 1rem;
            font-weight: 700;
            font-family: inherit;
            cursor: pointer;
            letter-spacing: .04em;
            transition: transform .15s, box-shadow .15s, background .2s;
        }
        .search-bar button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 24px rgba(59,130,246,.45);
            background: linear-gradient(135deg, #60A5FA, #3B82F6);
        }
        }
        .popular {
            text-align: center;
            font-size: .85rem;
            color: #64748B;
            margin-top: 4px;
            margin-bottom: 0;
            padding-bottom: 60px;
        }
        .popular a {
            color: #3B82F6;
            font-weight: 600;
            transition: color .15s;
        }
        .popular a:hover { color: #60A5FA; text-decoration: underline; }

        /* ── CTA BUTTONS ── */
        .hero-cta {
            display: flex; gap: 14px; justify-content: center;
            flex-wrap: wrap;
            padding-bottom: 0;
        }
        .btn-primary, .btn-ghost {
            padding: 14px 32px;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all .2s;
            display: inline-block;
        }
        .btn-primary {
            background: #3B82F6;
            color: #fff;
            border: none;
            box-shadow: 0 0 24px rgba(59,130,246,.35);
        }
        .btn-primary:hover { background: #2563EB; transform: translateY(-2px); }
        .btn-ghost {
            background: transparent;
            color: #F1F5F9;
            border: 1px solid #1E293B;
        }
        .btn-ghost:hover { border-color: #3B82F6; color: #3B82F6; }

        /* ── METRICS ── */
        .metrics {
            display: flex; justify-content: center; gap: 48px;
            padding: 40px 24px; flex-wrap: wrap;
            border-bottom: 1px solid #1E293B;
        }
        .metric { text-align: center; }
        .metric .num {
            font-size: 2rem; font-weight: 800;
            background: linear-gradient(135deg, #3B82F6, #06B6D4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric .lbl { font-size: .85rem; color: #94A3B8; margin-top: 4px; }

        /* ── SECTION TITLES ── */
        .stitle { text-align: center; padding: 72px 24px 12px; }
        .stitle h2 { font-size: 2rem; font-weight: 700; margin-bottom: 10px; }
        .stitle p  { color: #94A3B8; font-size: 1.05rem; max-width: 540px; margin: 0 auto; }

        /* ── FEATURES ── */
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px; max-width: 1100px;
            margin: 36px auto 0; padding: 0 24px 72px;
        }
        .fcard {
            background: #131B2E; border: 1px solid #1E293B;
            border-radius: 16px; padding: 32px 28px;
            transition: border-color .25s, transform .25s;
            display: block; color: inherit; text-decoration: none;
        }
        .fcard:hover { border-color: #3B82F6; transform: translateY(-4px); }
        .fcard .ficon {
            width: 48px; height: 48px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.5rem; margin-bottom: 18px;
        }
        .fcard h3 { font-size: 1.15rem; font-weight: 600; margin-bottom: 8px; }
        .fcard p  { font-size: .92rem; color: #94A3B8; line-height: 1.55; }
        .fcard .clink {
            display: inline-block; margin-top: 14px; font-size: .85rem;
            font-weight: 600; color: #3B82F6;
        }
        .ic-blue   { background: rgba(59,130,246,.15); }
        .ic-cyan   { background: rgba(6,182,212,.15); }
        .ic-green  { background: rgba(16,185,129,.15); }
        .ic-purple { background: rgba(139,92,246,.15); }
        .ic-orange { background: rgba(249,115,22,.15); }
        .ic-rose   { background: rgba(244,63,94,.15); }

        /* ── PRICING ── */
        .pricing {
            display: flex; justify-content: center; gap: 24px;
            max-width: 960px; margin: 36px auto 0;
            padding: 0 24px 72px; flex-wrap: wrap;
        }
        .pcard {
            background: #131B2E; border: 1px solid #1E293B;
            border-radius: 16px; padding: 32px 28px;
            text-align: center; flex: 1;
            min-width: 240px; max-width: 300px;
            transition: border-color .25s, transform .25s;
        }
        .pcard.pop { border-color: #3B82F6; }
        .pcard:hover { transform: translateY(-4px); }
        .pcard .tier { font-size: .85rem; color: #94A3B8; text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
        .pcard .amt  { font-size: 2.4rem; font-weight: 800; margin: 8px 0 4px; }
        .pcard .per  { font-size: .85rem; color: #94A3B8; margin-bottom: 16px; }
        .pcard ul { list-style: none; text-align: left; padding: 0; margin-bottom: 20px; }
        .pcard li { font-size: .88rem; color: #94A3B8; padding: 5px 0; }
        .pcard li::before { content: "\\2713  "; color: #10B981; font-weight: 700; }

        /* ── CTA FOOTER ── */
        .cta-foot {
            text-align: center; padding: 72px 24px 80px;
            background: radial-gradient(ellipse 70% 50% at 50% 110%, rgba(59,130,246,.35), transparent), #0B1120;
        }
        .cta-foot h2 { font-size: 2rem; font-weight: 700; margin-bottom: 12px; }
        .cta-foot p  { color: #94A3B8; margin-bottom: 28px; font-size: 1.05rem; }

        .foot-bar {
            text-align: center; padding: 24px;
            border-top: 1px solid #1E293B;
            font-size: .82rem; color: #94A3B8;
        }
        .foot-bar a { color: #3B82F6; }
    </style>

    <!-- ═══ HERO ═══ -->
    <div class="hero">
        <div class="hero-badge">&#128202; QUARTERCHARTS &mdash; FINANCIAL DATA VISUALIZATION</div>

        <!-- Search Bar -->
        <div class="search-wrap">
            <form class="search-bar" onsubmit="goSearch(); return false;">
                <div class="s-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                         stroke="#60A5FA" stroke-width="2.5" stroke-linecap="round"
                         stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"/>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                </div>
                <input id="ticker" type="text"
                       placeholder="Try AAPL, BRK.B, TSLA, KO ..."
                       autocomplete="off" spellcheck="false" required />
                <button type="submit">GO</button>
            </form>
        </div>

        <h1>Understand Any Stock<br>In Seconds</h1>
        <p class="sub">
            <strong>QuarterCharts</strong> is a financial data visualization platform
            that turns SEC filings into interactive Sankey diagrams, quarterly income
            charts, and company profiles &#8212; all from one search. Built for
            investors who value clarity over clutter.
        </p>
        <div class="hero-cta">
            <a class="btn-primary" href="/?page=charts&ticker=NVDA" target="_top">Explore Charts &#8212; Free</a>
            <a class="btn-ghost"  href="/?page=pricing" target="_top">View Pricing</a>
        </div>
        <div style="height:0.5px;background:rgba(255,255,255,0.07);max-width:480px;margin:6px auto 0;border-radius:1px;"></div>
        <div class="popular" style="margin-top:4px;" id="popular-tickers"></div>
        <script>
        (function(){
            var el = document.getElementById('popular-tickers');
            var tickers = __TICKER_POOL;
            var destPage = 'sankey';
            var html = 'Popular tickers:&nbsp; ';
            for (var i = 0; i < tickers.length; i++) {
                if (i > 0) html += ' \u00b7 ';
                html += '<a href="#" data-ticker="' + tickers[i] + '" class="popular-link">' + tickers[i] + '</a>';
            }
            el.innerHTML = html;
            /* Delegated click: iframe sandbox blocks target="_top" on some
               browsers, so navigate the parent window explicitly (same trick
               goSearch() uses). */
            el.addEventListener('click', function(ev){
                var a = ev.target.closest('a.popular-link');
                if (!a) return;
                ev.preventDefault();
                var t = a.getAttribute('data-ticker');
                if (!t) return;
                var url = '/?page=' + destPage + '&ticker=' + encodeURIComponent(t);
                try {
                    var link = window.parent.document.createElement('a');
                    link.href = url;
                    link.style.display = 'none';
                    window.parent.document.body.appendChild(link);
                    link.click();
                    link.remove();
                } catch(e) {
                    window.top.location.href = url;
                }
            });
        })();
        </script>
    </div>

    <!-- ═══ METRICS ═══ -->
    <div class="metrics">
        <div class="metric"><div class="num">10 000+</div><div class="lbl">Tickers Covered</div></div>
        <div class="metric"><div class="num">40+</div><div class="lbl">Quarters of Data</div></div>
        <div class="metric"><div class="num">Real-Time</div><div class="lbl">SEC Filings Sync</div></div>
        <div class="metric"><div class="num">Free</div><div class="lbl">To Get Started</div></div>
    </div>

    <!-- ═══ FEATURES ═══ -->
    <div class="stitle">
        <h2>Everything You Need to Analyze Stocks</h2>
        <p>Powerful tools, zero learning curve. Explore any public company in a few clicks.</p>
    </div>
    <div class="features">
        <a class="fcard" href="/?page=charts&ticker=NVDA" target="_top">
            <div class="ficon ic-cyan">&#128200;</div>
            <h3>Income Statement Charts</h3>
            <p>Revenue, gross profit, operating &amp; net income on one chart. Toggle quarterly vs. annual, compare 1&#8211;10 years.</p>
            <span class="clink">View NVDA Charts &#8594;</span>
        </a>
        <a class="fcard" href="/?page=sankey&ticker=NVDA&view=balance" target="_top">
            <div class="ficon ic-blue">&#128256;</div>
            <h3>Balance Sheet Sankey</h3>
            <p>Assets, liabilities &amp; equity on one flow diagram. Toggle quarterly vs. annual, compare point-in-time snapshots.</p>
            <span class="clink">View NVDA Balance &#8594;</span>
        </a>
        <a class="fcard" href="/?page=profile&ticker=NVDA" target="_top">
            <div class="ficon ic-green">&#127970;</div>
            <h3>Company Profiles</h3>
            <p>Key metrics, sector, market cap, description, and financial ratios &#8212; everything at a glance for any ticker.</p>
            <span class="clink">See NVDA Profile &#8594;</span>
        </a>
        <a class="fcard" href="/?page=earnings&ticker=NVDA" target="_top">
            <div class="ficon ic-purple">&#128197;</div>
            <h3>Earnings Calendar</h3>
            <p>Never miss an earnings date. Browse upcoming and past reports across the entire market in one clean view.</p>
            <span class="clink">Open Calendar &#8594;</span>
        </a>
        <a class="fcard" href="/?page=watchlist&ticker=NVDA" target="_top">
            <div class="ficon ic-orange">&#128065;&#65039;</div>
            <h3>Watchlist</h3>
            <p>Save your favorite tickers and track them in one place. Instant access to charts, profiles, and Sankey diagrams.</p>
            <span class="clink">Go to Watchlist &#8594;</span>
        </a>
        <a class="fcard" href="/?page=pricing" target="_top">
            <div class="ficon ic-rose">&#128176;</div>
            <h3>Pricing</h3>
            <p>Simple, transparent plans &#8212; start free, upgrade when you need more tickers, unlimited lookups, or team dashboards.</p>
            <span class="clink">View Pricing &#8594;</span>
        </a>
    </div>

    <!-- ═══ PRICING ═══ -->
    <div class="stitle">
        <h2>Simple, Transparent Pricing</h2>
        <p>Start free. Upgrade when you're ready.</p>
    </div>
    <div class="pricing">
    """
    f"""{_pricing_cards_html}"""
    """
    </div>

    <!-- ═══ CTA FOOTER ═══ -->
    <div class="cta-foot">
        <h2>Ready to See Your Stocks Differently?</h2>
        <p>Join thousands of investors using QuarterCharts to make smarter decisions.</p>
        <a class="btn-primary" href="/?page=sankey&ticker=AAPL" target="_top">Try It Now &#8212; It's Free</a>
    </div>
    <!-- footer rendered globally by app.py -->

    <script>
    function goSearch() {
        var v = document.getElementById('ticker').value.trim().toUpperCase();
        if (!v) return;
        // Ticker access gating
        // Always go to sankey page; blocked tickers redirect via pricing
        if (__ALLOWED_TICKERS !== null && __ALLOWED_TICKERS.indexOf(v) === -1) {
            var url = '/?page=' + encodeURIComponent(__REDIR_PAGE) + '&ticker=' + encodeURIComponent(v);
        } else {
            var url = '/?page=sankey&ticker=' + encodeURIComponent(v);
        }
        try {
            var a = window.parent.document.createElement('a');
            a.href = url;
            a.style.display = 'none';
            window.parent.document.body.appendChild(a);
            a.click();
            a.remove();
        } catch(e) {
            window.open(url, '_blank');
        }
    }

    /* ── Rotating placeholder ── */
    (function() {
        var tickers = __TICKER_POOL;
        var idx = 0;
        var inp = document.getElementById('ticker');
        function rotatePlaceholder() {
            if (document.activeElement === inp || inp.value.length > 0) return;
            idx = (idx + 1) % tickers.length;
            inp.placeholder = 'Try ' + tickers[idx] + ' ...';
        }
        setInterval(rotatePlaceholder, 2200);

        /* Auto-uppercase as user types */
        inp.addEventListener('input', function() {
            var pos = this.selectionStart;
            this.value = this.value.toUpperCase();
            this.setSelectionRange(pos, pos);
        });
    })();

    /* ── Delegated click for feature cards and pricing CTAs ──
       Streamlit's iframe sandbox can block target="_top" on <a> clicks,
       so intercept them and navigate the parent window explicitly
       (same trick used by goSearch() and the popular tickers strip). */
    (function() {
        function parentNavigate(url) {
            try {
                var a = window.parent.document.createElement('a');
                a.href = url;
                a.style.display = 'none';
                window.parent.document.body.appendChild(a);
                a.click();
                a.remove();
            } catch (e) {
                try { window.top.location.href = url; }
                catch (e2) { window.location.href = url; }
            }
        }
        document.addEventListener('click', function(ev) {
            var a = ev.target.closest('a');
            if (!a) return;
            var href = a.getAttribute('href');
            if (!href || href.charAt(0) === '#') return;
            /* Only hijack in-app navigations (relative/same-origin URLs) */
            var isInApp = href.charAt(0) === '/' || href.charAt(0) === '?';
            if (!isInApp) return;
            ev.preventDefault();
            parentNavigate(href);
        });
    })();
    </script>
    """, height=2340, scrolling=False)
