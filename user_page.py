"""
User dashboard page for QuarterCharts.
Shows portfolio overview, account settings, and recent activity feed.
Accessible via /?page=user tab for development; will later sit behind login.
"""

import streamlit as st
import json
import os
from datetime import datetime, timedelta

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
    """Fetch live quote for a single ticker. Returns dict with price info."""
    try:
        import yfinance as yf
        t = yf.Ticker(sym)
        fi = t.fast_info
        price = getattr(fi, "last_price", None) or 0
        prev = getattr(fi, "previous_close", None) or price
        change = price - prev if prev else 0
        pct = (change / prev * 100) if prev else 0
        mkt_cap = getattr(fi, "market_cap", None) or 0
        return {
            "symbol": sym,
            "price": price,
            "change": change,
            "pct": pct,
            "market_cap": mkt_cap,
        }
    except Exception:
        return {"symbol": sym, "price": 0, "change": 0, "pct": 0, "market_cap": 0}


def _fmt_cap(val):
    """Format market cap into readable string."""
    if not val:
        return "—"
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


# ── Main render ──────────────────────────────────────────────────────────────

def render_user_page():
    """Render the user dashboard page."""

    # Page CSS
    st.markdown("""
    <style>
    .user-greeting {
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.3px;
        margin-bottom: 2px;
    }
    .user-greeting-sub {
        color: #6b7280;
        font-size: 14px;
        margin-bottom: 24px;
    }
    .dash-section-title {
        font-size: 18px;
        font-weight: 600;
        margin: 28px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e5e7eb;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .stat-card {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 18px 20px;
        text-align: center;
    }
    .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
    }
    .stat-label {
        font-size: 12px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }
    .stock-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        border-bottom: 1px solid #f0f0f0;
        transition: background 0.15s;
    }
    .stock-row:hover {
        background: #f8fafc;
    }
    .stock-sym {
        font-weight: 600;
        font-size: 14px;
        color: #111827;
        min-width: 60px;
    }
    .stock-price {
        font-size: 14px;
        font-weight: 500;
        color: #111827;
        min-width: 70px;
        text-align: right;
    }
    .stock-change {
        font-size: 13px;
        font-weight: 500;
        min-width: 80px;
        text-align: right;
        padding: 2px 8px;
        border-radius: 6px;
    }
    .stock-change.up { color: #16a34a; background: #f0fdf4; }
    .stock-change.down { color: #dc2626; background: #fef2f2; }
    .stock-cap {
        font-size: 12px;
        color: #9ca3af;
        min-width: 70px;
        text-align: right;
    }
    .activity-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .activity-icon {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        flex-shrink: 0;
    }
    .activity-text {
        font-size: 14px;
        color: #374151;
        line-height: 1.4;
    }
    .activity-time {
        font-size: 11px;
        color: #9ca3af;
        margin-top: 2px;
    }
    .account-field {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .account-label {
        font-size: 13px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        font-weight: 500;
    }
    .account-value {
        font-size: 14px;
        color: #111827;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Greeting ─────────────────────────────────────────────────────────
    user_name = st.session_state.get("user_name") or "Investor"
    first_name = user_name.split()[0] if user_name else "Investor"
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    st.markdown(f'<div class="user-greeting">{greeting}, {first_name}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="user-greeting-sub">Here\'s your QuarterCharts overview</div>', unsafe_allow_html=True)

    # ── Quick Stats Row ──────────────────────────────────────────────────
    watchlist = _load_watchlist_tickers()
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-value">{len(watchlist)}</div>
            <div class="stat-label">Watchlist Stocks</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="stat-card">
            <div class="stat-value">Free</div>
            <div class="stat-label">Current Plan</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        user_email = st.session_state.get("user_email") or "—"
        joined_label = "Active"
        st.markdown(f"""<div class="stat-card">
            <div class="stat-value" style="font-size:16px;">{user_email}</div>
            <div class="stat-label">Account Email</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-value" style="color:#16a34a;">{joined_label}</div>
            <div class="stat-label">Account Status</div>
        </div>""", unsafe_allow_html=True)

    # ── Two-column layout: Portfolio + Activity ──────────────────────────
    left_col, right_col = st.columns([3, 2])

    # ── LEFT: Portfolio Overview ─────────────────────────────────────────
    with left_col:
        st.markdown('<div class="dash-section-title">Portfolio Overview</div>', unsafe_allow_html=True)

        if not watchlist:
            st.info("Your watchlist is empty. Add tickers from the Watchlist page.")
        else:
            # Fetch quotes in parallel
            from concurrent.futures import ThreadPoolExecutor, as_completed
            quotes = []
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(_fetch_quote, sym): sym for sym in watchlist[:10]}
                for fut in as_completed(futures):
                    try:
                        quotes.append(fut.result())
                    except Exception:
                        pass

            # Sort by symbol
            quotes.sort(key=lambda q: watchlist.index(q["symbol"]) if q["symbol"] in watchlist else 99)

            # Header row
            st.markdown("""
            <div style="display:flex;justify-content:space-between;padding:6px 16px;font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.5px;font-weight:500;">
                <span style="min-width:60px;">Ticker</span>
                <span style="min-width:70px;text-align:right;">Price</span>
                <span style="min-width:80px;text-align:right;">Change</span>
                <span style="min-width:70px;text-align:right;">Mkt Cap</span>
            </div>""", unsafe_allow_html=True)

            # Stock rows
            rows_html = ""
            gainers = 0
            losers = 0
            for q in quotes:
                cls = "up" if q["change"] >= 0 else "down"
                sign = "+" if q["change"] >= 0 else ""
                if q["change"] >= 0:
                    gainers += 1
                else:
                    losers += 1
                rows_html += f"""
                <a href="/?page=charts&ticker={q['symbol']}" target="_self" style="text-decoration:none;color:inherit;">
                <div class="stock-row">
                    <span class="stock-sym">{q['symbol']}</span>
                    <span class="stock-price">${q['price']:.2f}</span>
                    <span class="stock-change {cls}">{sign}{q['pct']:.2f}%</span>
                    <span class="stock-cap">{_fmt_cap(q['market_cap'])}</span>
                </div>
                </a>"""

            st.markdown(rows_html, unsafe_allow_html=True)

            # Summary line
            st.markdown(f"""
            <div style="padding:12px 16px;font-size:12px;color:#6b7280;">
                Showing top {len(quotes)} of {len(watchlist)} watchlist stocks &middot;
                <span style="color:#16a34a;">{gainers} up</span> &middot;
                <span style="color:#dc2626;">{losers} down</span>
            </div>""", unsafe_allow_html=True)

    # ── RIGHT: Activity Feed ─────────────────────────────────────────────
    with right_col:
        st.markdown('<div class="dash-section-title">Recent Activity</div>', unsafe_allow_html=True)

        # Activity items (placeholder data for now — will connect to audit_log later)
        activities = [
            {"icon": "&#128200;", "bg": "#eff6ff", "text": "Viewed <b>NVDA</b> Charts", "time": "Today"},
            {"icon": "&#9734;", "bg": "#fefce8", "text": "Added <b>AVGO</b> to Watchlist", "time": "Today"},
            {"icon": "&#128200;", "bg": "#eff6ff", "text": "Viewed <b>AAPL</b> Sankey", "time": "Yesterday"},
            {"icon": "&#128197;", "bg": "#f0fdf4", "text": "Checked Earnings Calendar", "time": "Yesterday"},
            {"icon": "&#128100;", "bg": "#faf5ff", "text": "Account created", "time": "This week"},
        ]

        activity_html = ""
        for a in activities:
            activity_html += f"""
            <div class="activity-item">
                <div class="activity-icon" style="background:{a['bg']};">{a['icon']}</div>
                <div>
                    <div class="activity-text">{a['text']}</div>
                    <div class="activity-time">{a['time']}</div>
                </div>
            </div>"""

        st.markdown(activity_html, unsafe_allow_html=True)

        st.markdown("""
        <div style="padding:16px 0 0 0;font-size:12px;color:#9ca3af;text-align:center;">
            Activity tracking coming soon
        </div>""", unsafe_allow_html=True)

    # ── Account & Settings Section ───────────────────────────────────────
    st.markdown('<div class="dash-section-title">Account & Settings</div>', unsafe_allow_html=True)

    acc_left, acc_right = st.columns(2)

    with acc_left:
        st.markdown("**Profile Information**")
        user_email = st.session_state.get("user_email") or "Not set"
        user_name_full = st.session_state.get("user_name") or "Not set"
        user_role = st.session_state.get("user_role") or "Free"

        st.markdown(f"""
        <div class="account-field">
            <span class="account-label">Name</span>
            <span class="account-value">{user_name_full}</span>
        </div>
        <div class="account-field">
            <span class="account-label">Email</span>
            <span class="account-value">{user_email}</span>
        </div>
        <div class="account-field">
            <span class="account-label">Role</span>
            <span class="account-value">{user_role}</span>
        </div>
        """, unsafe_allow_html=True)

    with acc_right:
        st.markdown("**Preferences**")

        st.markdown("""
        <div class="account-field">
            <span class="account-label">Default Ticker</span>
            <span class="account-value">NVDA</span>
        </div>
        <div class="account-field">
            <span class="account-label">Default View</span>
            <span class="account-value">Quarterly</span>
        </div>
        <div class="account-field">
            <span class="account-label">Notifications</span>
            <span class="account-value">Off</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Quick Actions ────────────────────────────────────────────────────
    st.markdown('<div class="dash-section-title">Quick Actions</div>', unsafe_allow_html=True)

    qa1, qa2, qa3, qa4 = st.columns(4)
    ticker = st.session_state.get("ticker", "NVDA")

    with qa1:
        st.markdown(f"""
        <a href="/?page=charts&ticker={ticker}" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;">
                <div style="font-size:24px;">&#128200;</div>
                <div class="stat-label" style="margin-top:8px;">View Charts</div>
            </div>
        </a>""", unsafe_allow_html=True)
    with qa2:
        st.markdown("""
        <a href="/?page=earnings" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;">
                <div style="font-size:24px;">&#128197;</div>
                <div class="stat-label" style="margin-top:8px;">Earnings Calendar</div>
            </div>
        </a>""", unsafe_allow_html=True)
    with qa3:
        st.markdown("""
        <a href="/?page=watchlist" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;">
                <div style="font-size:24px;">&#9734;</div>
                <div class="stat-label" style="margin-top:8px;">My Watchlist</div>
            </div>
        </a>""", unsafe_allow_html=True)
    with qa4:
        st.markdown("""
        <a href="/?page=pricing" target="_self" style="text-decoration:none;">
            <div class="stat-card" style="cursor:pointer;">
                <div style="font-size:24px;">&#128142;</div>
                <div class="stat-label" style="margin-top:8px;">Upgrade Plan</div>
            </div>
        </a>""", unsafe_allow_html=True)

    # ── Sign Out ─────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("Sign Out", key="user_signout"):
        for key in ["logged_in", "user_uid", "user_email", "user_name",
                     "user_role", "user_company_id", "auth_token", "auth_token_time"]:
            st.session_state[key] = None
        st.session_state.logged_in = False
        st.session_state.page = "home"
        st.query_params.update({"page": "home"})
        st.rerun()
