"""
User dashboard page for QuarterCharts.
Sidebar navigation with sections: Dashboard, Portfolio, Settings.
Accessible via /?page=user tab for development; will later sit behind login.
"""

import streamlit as st
import json
import os
from datetime import datetime
from auth import get_auth_params

# ── Helpers ──────────────────────────────────────────────────────────────────

_WATCHLIST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "watchlist_data.json"
)


def _load_watchlist_tickers() -> list:
    """Load watchlist tickers from shared watchlist file."""
    if os.path.exists(_WATCHLIST_FILE):
        try:
            with open(_WATCHLIST_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[:20]
        except Exception:
            pass
    return ["NVDA", "AAPL", "GOOGL", "MSFT", "AMZN"]


def _fetch_quote(sym: str) -> dict:
    """Fetch live quote for a single ticker."""
    try:
        import yfinance as yf
        t = yf.Ticker(sym)
        fi = t.fast_info
        price = getattr(fi, "last_price", None) or 0
        prev = getattr(fi, "previous_close", None) or price
        change = price - prev if prev else 0
        pct = (change / prev * 100) if prev else 0
        mkt_cap = getattr(fi, "market_cap", None) or 0
        return {"symbol": sym, "price": price, "change": change, "pct": pct, "market_cap": mkt_cap}
    except Exception:
        return {"symbol": sym, "price": 0, "change": 0, "pct": 0, "market_cap": 0}


def _fmt_cap(val):
    """Format market cap into readable string."""
    if not val:
        return "\u2014"
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


# ── CSS ──────────────────────────────────────────────────────────────────────

_PAGE_CSS = """
<style>
/* ── Sidebar nav ─────────────────────────────────── */
.user-nav {
    padding: 12px 0;
}
.user-nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 16px;
    margin: 2px 0;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    color: #4b5563;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s ease;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
}
.user-nav-item:hover {
    background: #f3f4f6;
    color: #111827;
}
.user-nav-item.active {
    background: #eff6ff;
    color: #2563eb;
    font-weight: 600;
}
.user-nav-item .nav-icon {
    font-size: 16px;
    width: 20px;
    text-align: center;
}
.user-nav-divider {
    height: 1px;
    background: #e5e7eb;
    margin: 12px 8px;
}
.user-nav-label {
    font-size: 10px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 8px 16px 4px;
}

/* ── Page header ─────────────────────────────────── */
.page-header {
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e5e7eb;
}
.page-title {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.3px;
    margin-bottom: 4px;
}
.page-subtitle {
    font-size: 14px;
    color: #6b7280;
}

/* ── Stat cards ──────────────────────────────────── */
.stat-card {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px;
}
.stat-card-icon {
    font-size: 20px;
    margin-bottom: 8px;
}
.stat-card-value {
    font-size: 22px;
    font-weight: 700;
    color: #111827;
    line-height: 1.2;
}
.stat-card-label {
    font-size: 12px;
    color: #6b7280;
    margin-top: 4px;
    font-weight: 500;
}

/* ── Stock table ─────────────────────────────────── */
.stock-table { width: 100%; border-collapse: collapse; }
.stock-table th {
    font-size: 11px;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 2px solid #e5e7eb;
}
.stock-table th:not(:first-child) { text-align: right; }
.stock-table td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; font-size: 14px; }
.stock-table td:not(:first-child) { text-align: right; }
.stock-table tr { transition: background 0.12s; }
.stock-table tr:hover { background: #f8fafc; }
.stock-table a { color: inherit; text-decoration: none; }
.stock-sym-cell { font-weight: 600; color: #111827; }
.stock-price-cell { font-weight: 500; color: #111827; }
.badge-up { color: #16a34a; background: #f0fdf4; padding: 2px 8px; border-radius: 6px; font-size: 13px; font-weight: 500; }
.badge-down { color: #dc2626; background: #fef2f2; padding: 2px 8px; border-radius: 6px; font-size: 13px; font-weight: 500; }
.stock-cap-cell { color: #6b7280; font-size: 13px; }

/* ── Settings ────────────────────────────────────── */
.settings-section {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
}
.settings-section-title {
    font-size: 16px;
    font-weight: 600;
    color: #111827;
    margin-bottom: 4px;
}
.settings-section-desc {
    font-size: 13px;
    color: #6b7280;
    margin-bottom: 18px;
}
.settings-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 0;
    border-bottom: 1px solid #f3f4f6;
}
.settings-row:last-child { border-bottom: none; }
.settings-row-label {
    font-size: 14px;
    font-weight: 500;
    color: #374151;
}
.settings-row-value {
    font-size: 14px;
    color: #6b7280;
}
.settings-row-hint {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 2px;
}
.danger-zone {
    border-color: #fecaca;
    background: #fef2f2;
}
.danger-zone .settings-section-title { color: #dc2626; }
</style>
"""


# ── Section renderers ────────────────────────────────────────────────────────

def _render_dashboard():
    """Dashboard overview with stats, quick portfolio, and activity."""
    user_name = st.session_state.get("user_name") or "Investor"
    first_name = user_name.split()[0] if user_name else "Investor"
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")

    st.markdown(f"""<div class="page-header">
        <div class="page-title">{greeting}, {first_name}</div>
        <div class="page-subtitle">Here's your QuarterCharts overview for {datetime.now().strftime('%B %d, %Y')}</div>
    </div>""", unsafe_allow_html=True)

    # Stat cards
    watchlist = _load_watchlist_tickers()
    user_email = st.session_state.get("user_email") or "\u2014"
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-card-icon">&#128200;</div>
            <div class="stat-card-value">{len(watchlist)}</div>
            <div class="stat-card-label">Watchlist Stocks</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="stat-card">
            <div class="stat-card-icon">&#128142;</div>
            <div class="stat-card-value">Free</div>
            <div class="stat-card-label">Current Plan</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="stat-card">
            <div class="stat-card-icon">&#128197;</div>
            <div class="stat-card-value">0</div>
            <div class="stat-card-label">Earnings Alerts</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown("""<div class="stat-card">
            <div class="stat-card-icon">&#9734;</div>
            <div class="stat-card-value" style="color:#16a34a;">Active</div>
            <div class="stat-card-label">Account Status</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Portfolio snapshot
    st.markdown("**Portfolio Snapshot**")
    _render_stock_table(watchlist[:5])
    ticker = st.session_state.get("ticker", "NVDA")
    _ap = get_auth_params()
    st.markdown(f"""<div style="padding:8px 0;font-size:13px;">
        <a href="/?page=user&ticker={ticker}&section=portfolio{_ap}" target="_self" style="color:#2563eb;text-decoration:none;font-weight:500;">View full portfolio &rarr;</a>
    </div>""", unsafe_allow_html=True)

    # Quick actions
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("**Quick Actions**")
    qa1, qa2, qa3, qa4 = st.columns(4)
    ticker = st.session_state.get("ticker", "NVDA")
    with qa1:
        st.markdown(f"""<a href="/?page=charts&ticker={ticker}{_ap}" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;text-align:center;padding:16px;">
                <div style="font-size:22px;">&#128200;</div>
                <div class="stat-card-label" style="margin-top:6px;">View Charts</div>
            </div></a>""", unsafe_allow_html=True)
    with qa2:
        st.markdown(f"""<a href="/?page=earnings&ticker={ticker}{_ap}" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;text-align:center;padding:16px;">
                <div style="font-size:22px;">&#128197;</div>
                <div class="stat-card-label" style="margin-top:6px;">Earnings Calendar</div>
            </div></a>""", unsafe_allow_html=True)
    with qa3:
        st.markdown(f"""<a href="/?page=watchlist&ticker={ticker}{_ap}" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;text-align:center;padding:16px;">
                <div style="font-size:22px;">&#9734;</div>
                <div class="stat-card-label" style="margin-top:6px;">My Watchlist</div>
            </div></a>""", unsafe_allow_html=True)
    with qa4:
        st.markdown(f"""<a href="/?page=sankey&ticker={ticker}{_ap}" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;text-align:center;padding:16px;">
                <div style="font-size:22px;">&#128202;</div>
                <div class="stat-card-label" style="margin-top:6px;">Sankey Diagram</div>
            </div></a>""", unsafe_allow_html=True)


def _render_portfolio():
    """Full portfolio view with all watchlist stocks."""
    st.markdown("""<div class="page-header">
        <div class="page-title">Portfolio</div>
        <div class="page-subtitle">Live quotes for your watchlist stocks</div>
    </div>""", unsafe_allow_html=True)

    watchlist = _load_watchlist_tickers()
    if not watchlist:
        st.info("Your watchlist is empty. Add tickers from the Watchlist page.")
        return

    _render_stock_table(watchlist)

    _ap = get_auth_params()
    st.markdown(f"""<div style="padding:12px 0;font-size:13px;color:#6b7280;">
        Showing {len(watchlist)} stocks &middot;
        <a href="/?page=watchlist&ticker={st.session_state.get('ticker', 'NVDA')}{_ap}" target="_self" style="color:#2563eb;text-decoration:none;font-weight:500;">Manage watchlist &rarr;</a>
    </div>""", unsafe_allow_html=True)


def _render_settings():
    """Account settings with profile, subscription, notifications, danger zone."""
    st.markdown("""<div class="page-header">
        <div class="page-title">Settings</div>
        <div class="page-subtitle">Manage your account preferences and subscription</div>
    </div>""", unsafe_allow_html=True)

    user_email = st.session_state.get("user_email") or "Not set"
    user_name = st.session_state.get("user_name") or "Not set"
    user_role = st.session_state.get("user_role") or "Free"

    # ── Profile ──────────────────────────────────────────────────────────
    st.markdown("""<div class="settings-section">
        <div class="settings-section-title">Profile Information</div>
        <div class="settings-section-desc">Your personal details and login credentials</div>
    </div>""", unsafe_allow_html=True)

    p1, p2 = st.columns(2)
    with p1:
        new_name = st.text_input("Display Name", value=user_name if user_name != "Not set" else "", key="settings_name", placeholder="Your name")
    with p2:
        st.text_input("Email Address", value=user_email if user_email != "Not set" else "", key="settings_email", disabled=True, help="Email cannot be changed")

    if st.button("Save Profile", type="primary", key="save_profile"):
        if new_name and new_name.strip():
            st.session_state.user_name = new_name.strip()
            st.success("Profile updated.")
        else:
            st.warning("Please enter a valid name.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Subscription ─────────────────────────────────────────────────────
    st.markdown(f"""<div class="settings-section">
        <div class="settings-section-title">Subscription & Billing</div>
        <div class="settings-section-desc">Manage your plan and payment details</div>
        <div class="settings-row">
            <div>
                <div class="settings-row-label">Current Plan</div>
                <div class="settings-row-hint">Basic access to charts and earnings data</div>
            </div>
            <div class="settings-row-value" style="font-weight:600;">Free</div>
        </div>
        <div class="settings-row">
            <div>
                <div class="settings-row-label">Billing Cycle</div>
                <div class="settings-row-hint">No active subscription</div>
            </div>
            <div class="settings-row-value">\u2014</div>
        </div>
        <div class="settings-row">
            <div>
                <div class="settings-row-label">Payment Method</div>
                <div class="settings-row-hint">No payment method on file</div>
            </div>
            <div class="settings-row-value">\u2014</div>
        </div>
    </div>""", unsafe_allow_html=True)

    sub1, sub2, _ = st.columns([1, 1, 2])
    with sub1:
        if st.button("Upgrade Plan", type="primary", key="upgrade_plan", use_container_width=True):
            st.session_state.page = "pricing"
            st.query_params.update({"page": "pricing"})
            st.rerun()
    with sub2:
        st.button("Manage Billing", key="manage_billing", use_container_width=True, disabled=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Notifications ────────────────────────────────────────────────────
    st.markdown("""<div class="settings-section">
        <div class="settings-section-title">Notifications</div>
        <div class="settings-section-desc">Choose what updates you want to receive</div>
    </div>""", unsafe_allow_html=True)

    n1, n2 = st.columns(2)
    with n1:
        st.toggle("Earnings Reminders", value=False, key="notif_earnings", help="Get notified before earnings for your watchlist stocks")
        st.toggle("Weekly Portfolio Digest", value=False, key="notif_digest", help="Weekly email with your portfolio performance")
    with n2:
        st.toggle("Price Alerts", value=False, key="notif_price", help="Alert when a stock moves more than 5% in a day")
        st.toggle("Product Updates", value=True, key="notif_product", help="New features and platform updates")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Preferences ──────────────────────────────────────────────────────
    st.markdown("""<div class="settings-section">
        <div class="settings-section-title">Display Preferences</div>
        <div class="settings-section-desc">Customize how data is displayed</div>
    </div>""", unsafe_allow_html=True)

    pref1, pref2, pref3 = st.columns(3)
    with pref1:
        st.selectbox("Default Ticker", options=["NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA"],
                      index=0, key="pref_ticker")
    with pref2:
        st.selectbox("Default View", options=["Quarterly", "Annual"], index=0, key="pref_view")
    with pref3:
        st.selectbox("Default Timeframe", options=["1Y", "2Y", "3Y", "5Y", "Max"], index=1, key="pref_timeframe")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Danger Zone ──────────────────────────────────────────────────────
    st.markdown("""<div class="settings-section danger-zone">
        <div class="settings-section-title">Danger Zone</div>
        <div class="settings-section-desc">Irreversible actions that affect your account</div>
        <div class="settings-row">
            <div>
                <div class="settings-row-label">Export Your Data</div>
                <div class="settings-row-hint">Download all your watchlists and settings</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    dz1, dz2, dz3 = st.columns([1, 1, 2])
    with dz1:
        if st.button("Export Data", key="export_data", use_container_width=True):
            # Export watchlist as JSON
            watchlist = _load_watchlist_tickers()
            export = {
                "email": user_email,
                "name": user_name,
                "watchlist": watchlist,
                "exported_at": datetime.now().isoformat(),
            }
            st.download_button(
                "Download JSON",
                data=json.dumps(export, indent=2),
                file_name="quartercharts_export.json",
                mime="application/json",
                key="download_export",
            )
    with dz2:
        if st.button("Delete Account", type="primary", key="delete_account", use_container_width=True):
            st.session_state["confirm_delete"] = True

    if st.session_state.get("confirm_delete"):
        st.warning("Are you sure you want to delete your account? This action cannot be undone.")
        dc1, dc2, _ = st.columns([1, 1, 3])
        with dc1:
            if st.button("Yes, Delete My Account", type="primary", key="confirm_delete_yes"):
                # Clear session and redirect
                from auth import clear_session
                clear_session()
                st.session_state.page = "home"
                st.rerun()
        with dc2:
            if st.button("Cancel", key="confirm_delete_no"):
                st.session_state.pop("confirm_delete", None)
                st.rerun()


# ── Shared components ────────────────────────────────────────────────────────

def _render_stock_table(tickers: list):
    """Render a stock price table for the given tickers."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    quotes = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_quote, sym): sym for sym in tickers}
        for fut in as_completed(futures):
            try:
                quotes.append(fut.result())
            except Exception:
                pass

    quotes.sort(key=lambda q: tickers.index(q["symbol"]) if q["symbol"] in tickers else 99)

    _ap = get_auth_params()
    rows = ""
    for q in quotes:
        badge = "badge-up" if q["change"] >= 0 else "badge-down"
        sign = "+" if q["change"] >= 0 else ""
        rows += f"""<tr>
            <td><a href="/?page=charts&ticker={q['symbol']}{_ap}" target="_self" class="stock-sym-cell">{q['symbol']}</a></td>
            <td class="stock-price-cell">${q['price']:.2f}</td>
            <td><span class="{badge}">{sign}{q['pct']:.2f}%</span></td>
            <td class="stock-cap-cell">{_fmt_cap(q['market_cap'])}</td>
        </tr>"""

    st.markdown(f"""
    <table class="stock-table">
        <thead><tr><th>Ticker</th><th>Price</th><th>Change</th><th>Mkt Cap</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)


# ── Main render ──────────────────────────────────────────────────────────────

# Sidebar nav items: (key, icon, label)
_NAV_ITEMS = [
    ("dashboard", "&#127968;",  "Dashboard"),
    ("portfolio", "&#128200;",  "Portfolio"),
    ("settings",  "&#9881;",    "Settings"),
]


def render_user_page():
    """Render the user dashboard page with left sidebar navigation."""

    # Inject CSS
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)

    # Current section from query param or session state
    section = st.query_params.get("section", "dashboard")
    if section not in [n[0] for n in _NAV_ITEMS]:
        section = "dashboard"

    # Layout: sidebar (1) + content (4)
    nav_col, content_col = st.columns([1, 4], gap="large")

    # ── Left sidebar ─────────────────────────────────────────────────────
    with nav_col:
        # User avatar area
        user_name = st.session_state.get("user_name") or "User"
        user_email = st.session_state.get("user_email") or ""
        initials = "".join([w[0].upper() for w in user_name.split()[:2]]) if user_name else "U"

        st.markdown(f"""
        <div style="text-align:center;padding:8px 0 16px;">
            <div style="width:56px;height:56px;border-radius:50%;background:#2563eb;color:#fff;
                        font-size:20px;font-weight:600;display:flex;align-items:center;
                        justify-content:center;margin:0 auto 10px;">{initials}</div>
            <div style="font-weight:600;font-size:14px;color:#111827;">{user_name}</div>
            <div style="font-size:12px;color:#6b7280;word-break:break-all;">{user_email}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="user-nav-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="user-nav-label">Menu</div>', unsafe_allow_html=True)

        # Nav items as Streamlit buttons (ensures proper state handling)
        ticker = st.session_state.get("ticker", "NVDA")
        _ap = get_auth_params()
        nav_html = '<div class="user-nav">'
        for key, icon, label in _NAV_ITEMS:
            active = "active" if section == key else ""
            nav_html += f"""<a href="/?page=user&ticker={ticker}&section={key}{_ap}" target="_self"
                            class="user-nav-item {active}">
                            <span class="nav-icon">{icon}</span> {label}</a>"""
        nav_html += '</div>'
        st.markdown(nav_html, unsafe_allow_html=True)

        st.markdown('<div class="user-nav-divider"></div>', unsafe_allow_html=True)

        # Sign out at bottom of sidebar
        if st.button("Sign Out", key="user_signout", use_container_width=True):
            from auth import clear_session
            clear_session()
            st.session_state.page = "home"
            st.rerun()

    # ── Main content area ────────────────────────────────────────────────
    with content_col:
        if section == "dashboard":
            _render_dashboard()
        elif section == "portfolio":
            _render_portfolio()
        elif section == "settings":
            _render_settings()
        else:
            _render_dashboard()
