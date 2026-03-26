"""Landing / Home page for Quarter Charts."""
import streamlit as st
import streamlit.components.v1 as components


def render_home_page():
    """Full-width marketing landing page with ticker search."""

    # ── hide default Streamlit chrome ──
    st.markdown("""
    <style>
    /* hide sidebar & default header/footer on home page */
    [data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 0 !important; max-width: 100% !important; }
    footer { display: none !important; }

    /* Force dark background on entire app */
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], .main {
        background: #0B1120 !important;
    }

    /* Remove gap between components.html iframe and surrounding content */
    iframe[title="streamlit_components_v1.html"] {
        margin-top: -16px !important;
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

    /* ── HERO BOTTOM (after search bar) ── */
    .hero-bottom {
        text-align: center;
        padding: 0 24px 80px;
        background: var(--qc-bg);
    }
    .popular-tickers {
        font-size: .85rem;
        color: #64748B;
        margin-bottom: 32px;
    }
    .popular-tickers a {
        color: #3B82F6;
        text-decoration: none;
        font-weight: 600;
        transition: color .15s;
    }
    .popular-tickers a:hover {
        color: #60A5FA;
        text-decoration: underline;
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
        background: #3B82F6;
        color: #fff;
        border: none;
        box-shadow: 0 0 24px rgba(59,130,246,.35);
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
    .price-card li::before { content: "\2713 "; color: var(--qc-green); font-weight: 700; }

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

    <!-- hero top -->
    <div class="hero">
        <div class="hero-badge">&#128202; FINANCIAL DATA VISUALIZATION</div>
        <h1>Understand Any Stock<br>In Seconds</h1>
        <p class="sub">
            Interactive Sankey diagrams, quarterly income charts, and company
            profiles &mdash; all from one search. Built for investors who value
            clarity over clutter.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Ticker search bar (components.html for full JS support) ──
    components.html("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #0B1120;
            display: flex;
            justify-content: center;
            padding: 0 24px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .search-wrap {
            width: 100%;
            max-width: 520px;
        }
        form {
            display: flex;
            align-items: center;
            background: #131B2E;
            border: 1px solid #1E293B;
            border-radius: 16px;
            padding: 6px 6px 6px 16px;
            transition: border-color .25s, box-shadow .25s;
        }
        form:focus-within {
            border-color: #3B82F6;
            box-shadow: 0 0 20px rgba(59,130,246,.2);
        }
        .icon {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            margin-right: 12px;
        }
        input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: #F1F5F9;
            font-size: 1rem;
            font-family: inherit;
            padding: 10px 0;
            min-width: 0;
        }
        input::placeholder { color: #64748B; }
        button {
            flex-shrink: 0;
            background: linear-gradient(135deg, #3B82F6, #2563EB);
            color: #fff;
            border: none;
            border-radius: 12px;
            padding: 10px 24px;
            font-size: .95rem;
            font-weight: 700;
            font-family: inherit;
            cursor: pointer;
            letter-spacing: .04em;
            transition: transform .15s, box-shadow .15s;
        }
        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(59,130,246,.4);
        }
    </style>
    <div class="search-wrap">
        <form onsubmit="go(); return false;">
            <div class="icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                     stroke="#94A3B8" stroke-width="2.5" stroke-linecap="round"
                     stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
            </div>
            <input id="t" type="text"
                   placeholder="Search any ticker &#8212; AAPL, TSLA, NVDA, META ..."
                   autocomplete="off" spellcheck="false" />
            <button type="submit">GO</button>
        </form>
    </div>
    <script>
        function go() {
            var v = document.getElementById('t').value.trim().toUpperCase();
            if (v) {
                window.parent.location.href = '/?page=charts&ticker=' + encodeURIComponent(v);
            }
        }
    </script>
    """, height=60)

    # ── Rest of the page (popular tickers, CTA, features, etc.) ──
    st.markdown("""
    <div class="home-wrap">

    <div class="hero-bottom">
        <div class="popular-tickers">
            Popular:
            <a href="/?page=charts&ticker=AAPL" target="_self">AAPL</a> &middot;
            <a href="/?page=charts&ticker=TSLA" target="_self">TSLA</a> &middot;
            <a href="/?page=charts&ticker=NVDA" target="_self">NVDA</a> &middot;
            <a href="/?page=charts&ticker=MSFT" target="_self">MSFT</a> &middot;
            <a href="/?page=charts&ticker=AMZN" target="_self">AMZN</a> &middot;
            <a href="/?page=charts&ticker=GOOG" target="_self">GOOG</a> &middot;
            <a href="/?page=charts&ticker=META" target="_self">META</a>
        </div>
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
            <div class="feature-icon ic-blue">&#128256;</div>
            <h3>Sankey Diagrams</h3>
            <p>See exactly where revenue flows &mdash; from top-line sales through costs and expenses to net income &mdash; in one interactive visual.</p>
            <span class="card-link">Try NVDA Sankey &rarr;</span>
        </a>
        <a class="feature-card" href="/?page=charts&ticker=NVDA" target="_self">
            <div class="feature-icon ic-cyan">&#128200;</div>
            <h3>Income Statement Charts</h3>
            <p>Revenue, gross profit, operating &amp; net income on one chart. Toggle quarterly vs. annual, and compare across 1&ndash;10 years.</p>
            <span class="card-link">View NVDA Charts &rarr;</span>
        </a>
        <a class="feature-card" href="/?page=profile&ticker=NVDA" target="_self">
            <div class="feature-icon ic-green">&#127970;</div>
            <h3>Company Profiles</h3>
            <p>Key metrics, sector, market cap, description, and financial ratios &mdash; everything you need at a glance for any ticker.</p>
            <span class="card-link">See NVDA Profile &rarr;</span>
        </a>
        <a class="feature-card" href="/?page=earnings&ticker=NVDA" target="_self">
            <div class="feature-icon ic-purple">&#128197;</div>
            <h3>Earnings Calendar</h3>
            <p>Never miss an earnings date. Browse upcoming and past reports across the entire market in one clean calendar view.</p>
            <span class="card-link">Open Calendar &rarr;</span>
        </a>
        <a class="feature-card" href="/?page=watchlist&ticker=NVDA" target="_self">
            <div class="feature-icon ic-orange">&#128065;&#65039;</div>
            <h3>Watchlist</h3>
            <p>Save your favorite tickers and track them in one place. Instant access to charts, profiles, and Sankey diagrams.</p>
            <span class="card-link">Go to Watchlist &rarr;</span>
        </a>
        <a class="feature-card" href="/?page=charts&ticker=NVDA" target="_self">
            <div class="feature-icon ic-rose">&#128196;</div>
            <h3>PDF Export</h3>
            <p>Download publication-quality charts and reports as PDFs &mdash; perfect for presentations, research, and sharing with your team.</p>
            <span class="card-link">Export a Chart &rarr;</span>
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
            <a class="btn-primary" style="display:block;text-align:center;" href="/?page=charts&ticker=NVDA" target="_self">Get Started</a>
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
            <a class="btn-primary" style="display:block;text-align:center;" href="/?page=pricing" target="_self">Contact Us</a>
        </div>
    </div>

    <!-- cta footer -->
    <div class="cta-footer">
        <h2>Ready to See Your Stocks Differently?</h2>
        <p>Join thousands of investors using Quarter Charts to make smarter decisions.</p>
        <a class="btn-primary" href="/?page=charts&ticker=AAPL" target="_self">Try It Now &mdash; It's Free</a>
    </div>

    <div class="foot-bar">
        &copy; 2026 Quarter Charts &middot; <a href="/?page=charts&ticker=NVDA" target="_self">Charts</a> &middot; <a href="/?page=sankey&ticker=NVDA" target="_self">Sankey</a> &middot; <a href="/?page=earnings&ticker=NVDA" target="_self">Earnings</a> &middot; <a href="/?page=pricing" target="_self">Pricing</a>
    </div>

    </div>
    """, unsafe_allow_html=True)
