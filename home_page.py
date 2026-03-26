"""Landing / Home page for Quarter Charts."""
import streamlit as st
import streamlit.components.v1 as components


def render_home_page():
    """Full-width marketing landing page with ticker search."""

    # ── hide default Streamlit chrome + force dark background ──
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
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
    components.html("""
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
        .search-bar {
            display: flex;
            align-items: center;
            max-width: 520px;
            margin: 0 auto 36px;
            background: #131B2E;
            border: 1px solid #1E293B;
            border-radius: 16px;
            padding: 6px 6px 6px 16px;
            transition: border-color .25s, box-shadow .25s;
        }
        .search-bar:focus-within {
            border-color: #3B82F6;
            box-shadow: 0 0 20px rgba(59,130,246,.2);
        }
        .search-bar .s-icon {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            margin-right: 12px;
        }
        .search-bar input {
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
        .search-bar input::placeholder { color: #64748B; }
        .search-bar button {
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
        .search-bar button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(59,130,246,.4);
        }
        .popular {
            text-align: center;
            font-size: .85rem;
            color: #64748B;
            margin-bottom: 32px;
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
            padding-bottom: 80px;
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
            border-top: 1px solid #1E293B;
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

        /* ── STEPS ── */
        .steps {
            display: flex; justify-content: center; gap: 40px;
            max-width: 960px; margin: 36px auto 0;
            padding: 0 24px 72px; flex-wrap: wrap;
        }
        .step { text-align: center; flex: 1; min-width: 200px; max-width: 280px; }
        .step-num {
            width: 48px; height: 48px; border-radius: 50%;
            background: rgba(59,130,246,.15); color: #3B82F6;
            font-weight: 800; font-size: 1.2rem;
            display: inline-flex; align-items: center; justify-content: center;
            margin-bottom: 16px;
        }
        .step h3 { font-size: 1.05rem; font-weight: 600; margin-bottom: 6px; }
        .step p  { font-size: .88rem; color: #94A3B8; line-height: 1.5; }
        .step a  { color: #3B82F6; font-weight: 600; }
        .step a:hover { text-decoration: underline; }

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
        .pcard li::before { content: "\2713  "; color: #10B981; font-weight: 700; }

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
        <div class="hero-badge">&#128202; FINANCIAL DATA VISUALIZATION</div>

        <!-- Search Bar -->
        <form class="search-bar" onsubmit="doSearch(); return false;">
            <div class="s-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                     stroke="#94A3B8" stroke-width="2.5" stroke-linecap="round"
                     stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
            </div>
            <input id="ticker" type="text"
                   placeholder="Search any ticker &#8212; AAPL, TSLA, NVDA, META ..."
                   autocomplete="off" spellcheck="false" />
            <button type="submit">GO</button>
        </form>

        <h1>Understand Any Stock<br>In Seconds</h1>
        <p class="sub">
            Interactive Sankey diagrams, quarterly income charts, and company
            profiles &#8212; all from one search. Built for investors who value
            clarity over clutter.
        </p>
        <div class="popular">
            Popular:
            <a href="/?page=charts&ticker=AAPL" target="_top">AAPL</a> &#183;
            <a href="/?page=charts&ticker=TSLA" target="_top">TSLA</a> &#183;
            <a href="/?page=charts&ticker=NVDA" target="_top">NVDA</a> &#183;
            <a href="/?page=charts&ticker=MSFT" target="_top">MSFT</a> &#183;
            <a href="/?page=charts&ticker=AMZN" target="_top">AMZN</a> &#183;
            <a href="/?page=charts&ticker=GOOG" target="_top">GOOG</a> &#183;
            <a href="/?page=charts&ticker=META" target="_top">META</a>
        </div>
        <div class="hero-cta">
            <a class="btn-primary" href="/?page=charts&ticker=NVDA" target="_top">Explore Charts &#8212; Free</a>
            <a class="btn-ghost"  href="/?page=pricing" target="_top">View Pricing</a>
        </div>
    </div>

    <!-- ═══ METRICS ═══ -->
    <div class="metrics">
        <div class="metric"><div class="num">6 000+</div><div class="lbl">Tickers Covered</div></div>
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
        <a class="fcard" href="/?page=sankey&ticker=NVDA" target="_top">
            <div class="ficon ic-blue">&#128256;</div>
            <h3>Sankey Diagrams</h3>
            <p>See exactly where revenue flows &#8212; from top-line sales through costs to net income &#8212; in one interactive visual.</p>
            <span class="clink">Try NVDA Sankey &#8594;</span>
        </a>
        <a class="fcard" href="/?page=charts&ticker=NVDA" target="_top">
            <div class="ficon ic-cyan">&#128200;</div>
            <h3>Income Statement Charts</h3>
            <p>Revenue, gross profit, operating &amp; net income on one chart. Toggle quarterly vs. annual, compare 1&#8211;10 years.</p>
            <span class="clink">View NVDA Charts &#8594;</span>
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
        <a class="fcard" href="/?page=charts&ticker=NVDA" target="_top">
            <div class="ficon ic-rose">&#128196;</div>
            <h3>PDF Export</h3>
            <p>Download publication-quality charts and reports as PDFs &#8212; perfect for presentations, research, and sharing.</p>
            <span class="clink">Export a Chart &#8594;</span>
        </a>
    </div>

    <!-- ═══ HOW IT WORKS ═══ -->
    <div class="stitle">
        <h2>Start in Three Steps</h2>
        <p>No sign-up required for basic access.</p>
    </div>
    <div class="steps">
        <div class="step">
            <div class="step-num">1</div>
            <h3>Enter a Ticker</h3>
            <p>Type any US stock symbol &#8212; <a href="/?page=charts&ticker=AAPL" target="_top">AAPL</a>, <a href="/?page=charts&ticker=TSLA" target="_top">TSLA</a>, <a href="/?page=charts&ticker=NVDA" target="_top">NVDA</a>, or 6 000+ others.</p>
        </div>
        <div class="step">
            <div class="step-num">2</div>
            <h3>Explore Visuals</h3>
            <p>Switch between <a href="/?page=sankey&ticker=NVDA" target="_top">Sankey</a>, <a href="/?page=charts&ticker=NVDA" target="_top">charts</a>, and <a href="/?page=profile&ticker=NVDA" target="_top">profiles</a> with a single click.</p>
        </div>
        <div class="step">
            <div class="step-num">3</div>
            <h3>Export &amp; Share</h3>
            <p>Download PDFs or share links &#8212; your data, your way.</p>
        </div>
    </div>

    <!-- ═══ PRICING ═══ -->
    <div class="stitle">
        <h2>Simple, Transparent Pricing</h2>
        <p>Start free. Upgrade when you're ready.</p>
    </div>
    <div class="pricing">
        <div class="pcard">
            <div class="tier">Free</div>
            <div class="amt">$0</div>
            <div class="per">forever</div>
            <ul>
                <li>5 ticker lookups / day</li>
                <li>Income statement charts</li>
                <li>Basic Sankey diagrams</li>
            </ul>
            <a class="btn-primary" style="display:block;text-align:center;" href="/?page=charts&ticker=NVDA" target="_top">Get Started</a>
        </div>
        <div class="pcard pop">
            <div class="tier">Pro</div>
            <div class="amt">$15</div>
            <div class="per">/ month</div>
            <ul>
                <li>Unlimited lookups</li>
                <li>Company profiles</li>
                <li>PDF exports</li>
                <li>Watchlist</li>
            </ul>
            <a class="btn-primary" style="display:block;text-align:center;" href="/?page=pricing" target="_top">Upgrade to Pro</a>
        </div>
        <div class="pcard">
            <div class="tier">Enterprise</div>
            <div class="amt">$49</div>
            <div class="per">/ month</div>
            <ul>
                <li>Everything in Pro</li>
                <li>API access</li>
                <li>Team dashboards</li>
                <li>Priority support</li>
            </ul>
            <a class="btn-primary" style="display:block;text-align:center;" href="/?page=pricing" target="_top">Contact Us</a>
        </div>
    </div>

    <!-- ═══ CTA FOOTER ═══ -->
    <div class="cta-foot">
        <h2>Ready to See Your Stocks Differently?</h2>
        <p>Join thousands of investors using Quarter Charts to make smarter decisions.</p>
        <a class="btn-primary" href="/?page=charts&ticker=AAPL" target="_top">Try It Now &#8212; It's Free</a>
    </div>
    <div class="foot-bar">
        &#169; 2026 Quarter Charts &#183;
        <a href="/?page=charts&ticker=NVDA" target="_top">Charts</a> &#183;
        <a href="/?page=sankey&ticker=NVDA" target="_top">Sankey</a> &#183;
        <a href="/?page=earnings&ticker=NVDA" target="_top">Earnings</a> &#183;
        <a href="/?page=pricing" target="_top">Pricing</a>
    </div>

    <script>
        function doSearch() {
            var v = document.getElementById('ticker').value.trim().toUpperCase();
            if (v) {
                window.top.location.href = '/?page=charts&ticker=' + encodeURIComponent(v);
            }
        }
    </script>
    """, height=2800, scrolling=False)
