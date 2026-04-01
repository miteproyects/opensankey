"""
User dashboard for QuarterCharts.
Shown after login — quick overview with links to explore data.
"""
import streamlit as st
import logging

logger = logging.getLogger(__name__)


def render_dashboard_page():
    """Render the post-login user dashboard."""
    from auth import get_auth_params, clear_session_state

    # Require login
    if not st.session_state.get("logged_in"):
        st.session_state.page = "login"
        st.query_params["page"] = "login"
        st.rerun()

    ticker = st.query_params.get("ticker", st.session_state.get("ticker", "AAPL"))
    email = st.session_state.get("user_email", "")
    display_name = st.session_state.get("user_display_name", "")
    avatar = st.session_state.get("user_avatar", "")
    auth_params = get_auth_params()

    # ── Welcome header ──
    greeting = display_name or email.split("@")[0] if email else "there"
    if avatar:
        avatar_html = (
            f'<img src="{avatar}" '
            f'style="width:48px;height:48px;border-radius:50%;border:2px solid #3b82f6;vertical-align:middle;" '
            f'referrerpolicy="no-referrer"/>'
        )
    else:
        initial = (display_name or email or "U")[0].upper()
        avatar_html = (
            f'<div style="width:48px;height:48px;border-radius:50%;background:#3b82f6;'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'color:white;font-size:22px;font-weight:700;vertical-align:middle;">{initial}</div>'
        )

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:16px;margin:28px 0 8px;">'
        f'{avatar_html}'
        f'<div>'
        f'<h2 style="margin:0;color:#f0f0f0;">Welcome back, {greeting}</h2>'
        f'<p style="margin:2px 0 0;color:#9ca3af;font-size:14px;">{email}</p>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("")  # spacer

    # ── Quick-access cards ──
    st.markdown(
        '<p style="color:#9ca3af;font-size:15px;margin-bottom:12px;">'
        'Jump into your financial data:</p>',
        unsafe_allow_html=True,
    )

    def _card(icon, title, desc, page, extra_qs=""):
        link = f"/?page={page}&ticker={ticker}{auth_params}{extra_qs}"
        return (
            f'<a href="{link}" target="_self" style="text-decoration:none;">'
            f'<div style="background:#1e293b;border-radius:12px;padding:20px;'
            f'transition:background .15s;cursor:pointer;height:100%;"'
            f' onmouseover="this.style.background=\'#293548\'"'
            f' onmouseout="this.style.background=\'#1e293b\'">'
            f'<div style="font-size:28px;margin-bottom:8px;">{icon}</div>'
            f'<div style="color:#f0f0f0;font-size:16px;font-weight:600;">{title}</div>'
            f'<div style="color:#9ca3af;font-size:13px;margin-top:4px;">{desc}</div>'
            f'</div></a>'
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            _card("📊", "Charts", "Quarterly income, cash flow &amp; balance sheet", "charts"),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _card("🔀", "Sankey", "Interactive financial flow diagrams", "sankey"),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _card("📅", "Earnings Calendar", "Upcoming earnings dates &amp; estimates", "earnings"),
            unsafe_allow_html=True,
        )

    st.markdown("")  # spacer

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(
            _card("🏢", "Company Profile", "Overview, sector, market cap &amp; more", "profile"),
            unsafe_allow_html=True,
        )
    with col5:
        st.markdown(
            _card("⭐", "Watchlist", "Your saved tickers", "watchlist"),
            unsafe_allow_html=True,
        )
    with col6:
        st.markdown(
            _card("⚙️", "Account Settings", "Profile, password &amp; preferences", "user"),
            unsafe_allow_html=True,
        )

    # ── Quick ticker search ──
    st.markdown("---")
    st.markdown(
        '<p style="color:#9ca3af;font-size:15px;">Search a ticker to get started:</p>',
        unsafe_allow_html=True,
    )
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        new_ticker = st.text_input(
            "Ticker", value=ticker, placeholder="e.g. AAPL, MSFT, NVDA",
            key="dash_ticker", label_visibility="collapsed",
        )
    with search_col2:
        if st.button("Explore", use_container_width=True, type="primary", key="dash_go"):
            t = new_ticker.strip().upper()
            if t:
                st.query_params["page"] = "charts"
                st.query_params["ticker"] = t
                st.rerun()

    # ── Sign out ──
    st.markdown("---")
    if st.button("Sign Out", key="dash_signout"):
        clear_session_state()
        st.session_state.page = "home"
        st.query_params.clear()
        st.query_params["page"] = "home"
        st.query_params["ticker"] = ticker
        st.rerun()
