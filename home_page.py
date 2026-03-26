"""Landing / Home page for Quarter Charts."""
import streamlit as st
import streamlit.components.v1 as components


def render_home_page():
    """Full-width marketing landing page with hero ticker search."""

    # ── hide default Streamlit chrome ──
    st.markdown("""
    <style>
    /* hide sidebar & default header/footer on home page */
    [data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 0 !important; max-width: 100% !important; }
    footer { display: none !important; }

    /* dark background for entire app on home page */
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], .main {
        background: #0B1120 !important;
    }

    /* ── Home-page variables ── */
    :root {
        --qc-bg: #0B1120;
        --qc-surface: #131B2E;
        --qc-border: #1E293B;
        --qc-blue: #3B82F6;
        --qc-blue-glow: rgba(59,130,246,.35);
        --qc-cyan: #06B6D4;
        --qc-green: #10B981;
        --qc-purple: #8B5CF6;
        --qc-text: #F1F5F9;
        --qc-muted: #94A3B8;
    }

    .home-wrap * { box-sizing: border-box; margin: 0; padding: 0; }
    .home-wrap {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--qc-bg);
        color: var(--qc-text);
        overflow-x: hidden;
    }

    /* ── HERO ── */
    .hero {
        position: relative;
        text-align: center;
        padding: 100px 24px 0;
        background:
            radial-gradient(ellipse 80% 60% at 50% -10%, var(--qc-blue-glow), transparent),
            var(--qc-bg);
    }
    .hero-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 999px;
        font-size: .8rem;
        font-weight: 600;
        letter-spacing: .04em;
        background: rgba(59,130,246,.15);
        color: var(--qc-blue);
        border: 1px solid rgba(59,130,246,.3);
        margin-bottom: 28px;
    }
    .hero h1 {
        font-size: clamp(2.2rem, 5vw, 3.8rem);
        font-weight: 800;
        line-height: 1.12;
        margin-bottom: 20px;
        background: linear-gradient(135deg, #fff 30%, var(--qc-blue));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero p.sub {
        font-size: 1.15rem;
        color: var(--qc-muted);
        max-width: 620px;
        margin: 0 auto 36px;
        line-height: 1.6;
    }

    /* ── HERO TICKER SEARCH (Streamlit form override) ── */
    /* Target the form directly — no wrapper div needed */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        background: transparent !important;
    }
    [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        max-width: 520px;
        margin: 0 auto;
        background: var(--qc-surface);
        border: 1px solid var(--qc-border);
        border-radius: 16px;
        padding: 6px 6px 6px 20px;
        gap: 0 !important;
        transition: border-color .25s, box-shadow .25s;
    }
    [data-testid="stForm"] [data-testid="stHorizontalBlock"]:focus-within {
        border-color: var(--qc-blue);
        box-shadow: 0 0 24px var(--qc-blue-glow);
    }
    /* hide label */
    [data-testid="stForm"] label { display: none !important; }
    /* input field */
    [data-testid="stForm"] input[type="text"] {
        background: transparent !important;
        border: none !important;
        color: var(--qc-text) !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        padding: 12px 0 !important;
        caret-color: var(--qc-blue);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    [data-testid="stForm"] input[type="text"]::placeholder {
        color: var(--qc-muted) !important;
        opacity: 1 !important;
    }
    [data-testid="stForm"] input[type="text"]:focus {
        box-shadow: none !important;
        border: none !important;
    }
    /* GO button */
    [data-testid="stForm"] button[kind="secondaryFormSubmit"],
    [data-testid="stForm"] button[type="submit"] {
        background: linear-gradient(135deg, var(--qc-blue), #2563EB) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 32px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        letter-spacing: .04em !important;
        cursor: pointer !important;
        transition: transform .15s, box-shadow .15s !important;
        white-space: nowrap !important;
        min-width: 80px !important;
    }
    [data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover,
    [data-testid="stForm"] button[type="submit"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px var(--qc-blue-glow) !important;
    }
    /* helper text below search */
    .search-hint {
        font-size: .85rem;
        color: var(--qc-muted);
        margin-top: 14px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .search-hint a {
        color: var(--qc-blue);
        text-decoration: none;
        font-weight: 600;
        transition: color .15s;
    }
    .search-hint a:hover { color: #60A5FA; text-decoration: underline; }

    /* ── CTA BELOW SEARCH ── */
    .hero-bottom {
        background: var(--qc-bg);
        text-align: center;
        padding: 16px 24px 80px;
    }
    .hero-cta {
        display: inline-flex; gap: 14px; flex-wrap: wrap; justify-content: center;
    }
    .btn-primary, .btn-ghost {
        padding: 14px 32px;
        border-radius: 10px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        transition: all .2s;
    }
    .btn-primary {
        background: var(--qc-blue);
        color: #fff;
        border: none;
        box-shadow: 0 0 24px var(--qc-blue-glow);
    }
    .btn-primary:hover { background: #2563EB; transform: translateY(-2px); }
    .btn-ghost {
        background: transparent;
        color: var(--qc-text);
        border: 1px solid var(--qc-border);
    }
    .btn-ghost:hover { border-color: var(--qc-blue); color: var(--qc-blue); }

    /* ── METRICS STRIP ── */
    .metrics-strip {
        display: flex;
        justify-content: center;
        gap: 48px;
        padding: 40px 24px;
        border-top: 1px solid var(--qc-border);
        border-bottom: 1px solid var(--qc-border);
        flex-wrap: wrap;
    }
    .metric { text-align: center; }
    .metric .num {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, var(--qc-blue), var(--qc-cyan));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric .label { font-size: .85rem; color: var(--qc-muted); margin-top: 4px; }

    /* ── FEATURES GRID ── */
    .section-title {
        text-align: center;
        padding: 72px 24px 12px;
    }
    .section-title h2 {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .section-title p {
        color: var(--qc-muted);
        font-size: 1.05rem;
        max-width: 540px;
        margin: 0 auto;
    }
    .features {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 24px;
        max-width: 1100px;
        margin: 36px auto 0;
        padding: 0 24px 72px;
    }
    .feature-card {
        background: var(--qc-surface);
        border: 1px solid var(--qc-border);
        border-radius: 16px;
        padding: 32px 28px;
        transition: border-color .25s, transform .25s;
    }
    .feature-card:hover { border-color: var(--qc-blue); transform: translateY(-4px); }
    .feature-icon {
        width: 48px; height: 48px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.5rem;
        margin-bottom: 18px;
    }
    .feature-card h3 { font-size: 1.15rem; font-weight: 600; margin-bottom: 8px; }
    .feature-card p  { font-size: .92rem; color: var(--qc-muted); line-height: 1.55; }
    a.feature-card { text-decoration: none; color: inherit; display: block; }
    .feature-card .card-link {
        display: inline-block;
        margin-top: 14px;
        font-size: .85rem;
        font-weight: 600;
        color: var(--qc-blue);
        text-decoration: none;
        transition: gap .2s;
    }
    .feature-card:hover .card-link { letter-spacing: .02em; }

    /* icon bg colors */
    .ic-blue   { background: rgba(59,130,246,.15); }
    .ic-cyan   { background: rgba(6,182,212,.15); }
    .ic-green  { background: rgba(16,185,129,.15); }
    .ic-purple { background: rgba(139,92,246,.15); }
    .ic-orange { background: rgba(249,115,22,.15); }
    .ic-rose   { background: rgba(244,63,94,.15); }
    /* ── HOW IT WORKS ── */
    .steps {
        display: flex;
        justify-content: center;
        gap: 40px;
        max-width: 960px;
        margin: 36px auto 0;
        padding: 0 24px 72px;
        flex-wrap: wrap;
    }
    .step {
        text-align: center;
        flex: 1;
        min-width: 200px;
        max-width: 280px;
    }
    .step-num {
        width: 48px; height: 48px;
        border-radius: 50%;
        background: rgba(59,130,246,.15);
        color: var(--qc-blue);
        font-weight: 800;
        font-size: 1.2rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 16px;
    }
    .step h3 { font-size: 1.05rem; font-weight: 600; margin-bottom: 6px; }
    .step p  { font-size: .88rem; color: var(--qc-muted); line-height: 1.5; }
    .step a  { color: var(--qc-blue); text-decoration: none; font-weight: 600; }
    .step a:hover { text-decoration: underline; }

    /* ── PRICING PREVIEW ── */
    .pricing-row {
        display: flex;
        justify-content: center;
        gap: 24px;
        max-width: 960px;
        margin: 36px auto 0;
        padding: 0 24px 72px;
        flex-wrap: wrap;
    }
    .price-card {
        background: var(--qc-surface);
        border: 1px solid var(--qc-border);
        border-radius: 16px;
        padding: 32px 28px;
        text-align: center;
        flex: 1;
        min-width: 240px;
        max-width: 300px;
        transition: border-color .25s, transform .25s;
    }
    .price-card.pop { border-color: var(--qc-blue); }
    .price-card:hover { transform: translateY(-4px); }
    .price-card .tier { font-size: .85rem; color: var(--qc-muted); text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
    .price-card .amount { font-size: 2.4rem; font-weight: 800; margin: 8px 0 4px; }
    .price-card .period { font-size: .85rem; color: var(--qc-muted); margin-bottom: 16px; }
    .price-card ul { list-style: none; text-align: left; padding: 0; margin-bottom: 20px; }
    .price-card li { font-size: .88rem; color: var(--qc-muted); padding: 5px 0; }
    .price-card li::before { content: "\\2713  "; color: var(--qc-green); font-weight: 700; }

    /* ── CTA FOOTER ── */
    .cta-footer {
        text-align: center;
        padding: 72px 24px 80px;
        background:
            radial-gradient(ellipse 70% 50% at 50% 110%, var(--qc-blue-glow), transparent),
            var(--qc-bg);
    }
    .cta-footer h2 { font-size: 2rem; font-weight: 700; margin-bottom: 12px; }
    .cta-footer p  { color: var(--qc-muted); margin-bottom: 28px; font-size: 1.05rem; }

    .foot-bar {
        text-align: center;
        padding: 24px;
        border-top: 1px solid var(--qc-border);
        font-size: .82rem;
        color: var(--qc-muted);
    }
    .foot-bar a { color: var(--qc-blue); text-decoration: none; }
    </style>

    <div class="home-wrap">

    <!-- hero top: badge + headline + subtitle -->
    <div class="hero">
        <div class="hero-badge">📊 FINANCIAL DATA VISUALIZATION</div>
        <h1>Understand Any Stock<br>In Seconds</h1>
        <p class="sub">
            Interactive Sankey diagrams, quarterly income charts, and company
            profiles &mdash; all from one search. Built for investors who value
            clarity over clutter.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── TICKER SEARCH (real Streamlit form, styled to match hero) ──
    search_container = st.container()
    with search_container:
        with st.form("home_ticker_form", clear_on_submit=False, border=False):
            col_input, col_btn = st.columns([4, 1], vertical_alignment="center")
            with col_input:
                new_ticker = st.text_input(
                    "Search ticker",
                    value="",
                    placeholder="Search any ticker \u2014 AAPL, TSLA, NVDA, META ...",
                    label_visibility="collapsed",
                ).upper().strip()
            with col_btn:
                submitted = st.form_submit_button("GO")

        # quick-access links
        st.markdown(
            '<div class="search-hint">'
            'Popular: '
            '<a href="/?page=charts&ticker=AAPL" target="_self">AAPL</a> \u00b7 '
            '<a href="/?page=charts&ticker=TSLA" target="_self">TSLA</a> \u00b7 '
            '<a href="/?page=charts&ticker=NVDA" target="_self">NVDA</a> \u00b7 '
            '<a href="/?page=charts&ticker=MSFT" target="_self">MSFT</a> \u00b7 '
            '<a href="/?page=charts&ticker=AMZN" target="_self">AMZN</a> \u00b7 '
            '<a href="/?page=charts&ticker=GOOG" target="_self">GOOG</a> \u00b7 '
            '<a href="/?page=charts&ticker=META" target="_self">META</a>'
            '</div>',
            unsafe_allow_html=True,
        )

    # handle form submission
    if submitted and new_ticker:
        from data_fetcher import validate_ticker
        if validate_ticker(new_ticker):
            st.session_state.ticker = new_ticker
            st.session_state.page = "charts"
            st.query_params.update({"page": "charts", "ticker": new_ticker})
            st.rerun()
        else:
            st.markdown(
                f'<div style="text-align:center;padding:8px;color:#F87171;'
                f'font-family:Inter,sans-serif;font-size:.95rem;">'
                f'\u26a0\ufe0f  Ticker <b>{new_ticker}</b> not found. Try another symbol.'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── rest of the page (CTA buttons + everything below) ──
    st.markdown("""
    <div class="home-wrap">

    <!-- CTA buttons -->
    <div class="hero-bottom">
        <div class="hero-cta">
            <a class="btn-primary" href="/?page=charts&ticker=NVDA" target="_self">Explore Charts &mdash; Free</a>
            <a class="btn-ghost"  href="/?page=pricing" target="_self">View Pricing</a>
        </div>
    </div>

    <!-- trust strip -->
    <div class="metrics-strip">
        <div class="metric"><div class="num">6 000+</div><div class="label">Tickers Covered</div></div>
        <div class="metric"><div class="num">40+</div><div class="label">Quarters of Data</div></div>
        <div class="metric"><div class="num">Real-Time</div><div class="label">SEC Filings Sync</div></div>
        <div class="metric"><div class="num">Free</div><div class="label">To Get Started</div></div>
    </div>

    <!-- features -->
    <div class="section-title">
        <h2>Everything You Need to Analyze Stocks</h2>
        <p>Powerful tools, zero learning curve. Explore any public company in a few clicks.</p>
    </div>
    <div class="features">
        <a class="feature-card" href="/?page=sankey&ticker=NVDA" target="_self">
            <div class="feature-icon ic-blue">🔀</div>
            <h3>Sankey Diagrams</h3>
            <p>See exactly where revenue flows &mdash; from top-line sales through costs and expenses to net income.</p>
            <span class="card-link">Try NVDA Sankey →</span>
        </a>
        <a class="feature-card" href="/?page=charts&ticker=NVDA" target="_self">
            <div class="feature-icon ic-cyan">📈</div>
            <h3>Income Statement Charts</h3>
            <p>Revenue, gross profit, operating &amp; net income on one chart. Toggle quarterly vs. annual, and compare</p>
            <span class="card-link">View NVDA Charts →</span>
        </a>
        <a class="feature-card" href="/?page=profile&ticker=NVDA" target="_self">
            <div class="feature-icon ic-green">🏢</div>
            <h3>Company Profiles</h3>
            <p>Key metrics, sector, market cap, description, and financial ratios &mdash; everything you need at a glance.</p>
            <span class="card-link">See NVDA Profile →</span>
        </a>
        <a class="feature-card" href="/?page=earnings&ticker=NVDA" target="_self">
            <div class="feature-icon ic-purple">📅</div>
            <h3>Earnings Calendar</h3>
            <p>Never miss an earnings date. Browse upcoming and past reports across the entire market in one clean interface.</p>
            <span class="card-link">Open Calendar →</span>
        </a>
        <a class="feature-card" href="/?page=watchlist&ticker=NVDA" target="_self">
            <div class="feature-icon ic-orange">👁️</div>
            <h3>Watchlist</h3>
            <p>Save your favorite tickers and track them in one place. Instant access to charts, profiles, and Sankey diagrams.</p>
            <span class="card-link">Go to Watchlist →</span>
        </a>
        <a class="feature-card" href="/?page=charts&ticker=NVDA" target="_self">
            <div class="feature-icon ic-rose">📄</div>
            <h3>PDF Export</h3>
            <p>Download publication-quality charts and reports as PDFs &mdash; perfect for presentations, research, and reports.</p>
            <span class="card-link">Export a Chart →</span>
        </a>
    </div>

    <!-- how it works -->
    <div class="section-title">
        <h2>Start in Three Steps</h2>
        <p>No sign-up required for basic access.</p>
    </div>
    <div class="steps">
        <div class="step">
            <div class="step-num">1</div>
            <h3>Enter a Ticker</h3>
            <p>Type any US stock symbol &mdash; <a href="/?page=charts&ticker=AAPL" target="_self">AAPL</a>, <a href="/?page=charts&ticker=TSLA" target="_self">TSLA</a>, <a href="/?page=charts&ticker=NVDA" target="_self">NVDA</a>, or 6 000+ others.</p>
        </div>
        <div class="step">
            <div class="step-num">2</div>
            <h3>Explore Visuals</h3>
            <p>Switch between <a href="/?page=sankey&ticker=NVDA" target="_self">Sankey</a>, <a href="/?page=charts&ticker=NVDA" target="_self">charts</a>, and <a href="/?page=profile&ticker=NVDA" target="_self">profiles</a> with a single click.</p>
        </div>
        <div class="step">
            <div class="step-num">3</div>
            <h3>Export &amp; Share</h3>
            <p>Download PDFs or share links &mdash; your data, your way.</p>
        </div>
    </div>

    <!-- pricing -->
    <div class="section-title">
        <h2>Simple, Transparent Pricing</h2>
        <p>Start free. Upgrade when you're ready.</p>
    </div>
    <div class="pricing-row">
        <div class="price-card">
            <div class="tier">Free</div>
            <div class="amount">$0</div>
            <div class="period">forever</div>
            <ul>
                <li>5 ticker lookups / day</li>
                <li>Income statement charts</li>
                <li>Basic Sankey diagrams</li>
            </ul>
            <a class="btn-ghost" href="/?page=charts&ticker=NVDA" target="_self">Get Started</a>
        </div>
        <div class="price-card pop">
            <div class="tier">Pro</div>
            <div class="amount">$15</div>
            <div class="period">/ month</div>
            <ul>
                <li>Unlimited lookups</li>
                <li>Company profiles</li>
                <li>PDF exports</li>
                <li>Watchlist</li>
            </ul>
            <a class="btn-primary" style="display:block;text-align:center;" href="/?page=pricing" target="_self">Upgrade to Pro</a>
        </div>
        <div class="price-card">
            <div class="tier">Enterprise</div>
            <div class="amount">$49</div>
            <div class="period">/ month</div>
            <ul>
                <li>Everything in Pro</li>
                <li>API access</li>
                <li>Team dashboards</li>
                <li>Priority support</li>
            </ul>
            <a class="btn-ghost" href="/?page=pricing" target="_self">Contact Us</a>
        </div>
    </div>

    <!-- CTA footer -->
    <div class="cta-footer">
        <h2>Ready to See Your Stocks Differently?</h2>
        <p>Join thousands of investors using Quarter Charts to make smarter decisions.</p>
        <a class="btn-primary" href="/?page=charts&ticker=AAPL" target="_self">Try It Now &mdash; It's Free</a>
    </div>

    <div class="foot-bar">
        © 2026 Quarter Charts · <a href="/?page=charts&ticker=NVDA" target="_self">Charts</a> · <a href="/?page=sankey&ticker=NVDA" target="_self">Sankey</a> · <a href="/?page=earnings&ticker=NVDA" target="_self">Earnings</a> · <a href="/?page=pricing" target="_self">Pricing</a>
    </div>

    </div>
    """, unsafe_allow_html=True)
