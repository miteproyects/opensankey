"""
User dashboard for QuarterCharts.
Shown after login — personalized overview with watchlist, quick navigation,
and ticker search.
"""
import json
import os
import streamlit as st
import logging

logger = logging.getLogger(__name__)

_WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "watchlist_data.json")


def _load_watchlist() -> list[str]:
    """Load watchlist tickers from the shared JSON file."""
    try:
        if os.path.exists(_WATCHLIST_PATH):
            with open(_WATCHLIST_PATH, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data[:10]  # Show up to 10
    except Exception:
        pass
    return []


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
    watchlist = _load_watchlist()

    # ── Welcome header ──
    greeting = display_name or (email.split("@")[0] if email else "there")
    if avatar:
        avatar_html = (
            f'<img src="{avatar}" '
            f'style="width:56px;height:56px;border-radius:50%;border:2px solid #3b82f6;'
            f'object-fit:cover;" referrerpolicy="no-referrer"/>'
        )
    else:
        initial = (display_name or email or "U")[0].upper()
        avatar_html = (
            f'<div style="width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#3b82f6,#8b5cf6);'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'color:white;font-size:24px;font-weight:700;">{initial}</div>'
        )

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:20px;margin:32px 0 4px;padding:24px 28px;
                background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
                border-radius:16px;border:1px solid #334155;">
        {avatar_html}
        <div style="flex:1;">
            <h2 style="margin:0;color:#f0f0f0;font-size:24px;font-weight:600;">
                Welcome back, {greeting}</h2>
            <p style="margin:4px 0 0;color:#94a3b8;font-size:14px;">{email}</p>
        </div>
        <a href="/?page=user&ticker={ticker}{auth_params}" target="_self"
           style="text-decoration:none;color:#94a3b8;font-size:13px;
                  padding:8px 16px;border:1px solid #334155;border-radius:8px;
                  transition:all .15s;"
           onmouseover="this.style.borderColor='#3b82f6';this.style.color='#3b82f6'"
           onmouseout="this.style.borderColor='#334155';this.style.color='#94a3b8'">
            Account Settings
        </a>
    </div>
    """, unsafe_allow_html=True)

    # ── Ticker search bar ──
    st.markdown("")
    search_col1, search_col2 = st.columns([4, 1])
    with search_col1:
        new_ticker = st.text_input(
            "Search", value=ticker, placeholder="Search any ticker — e.g. AAPL, MSFT, NVDA",
            key="dash_ticker", label_visibility="collapsed",
        )
    with search_col2:
        if st.button("Explore", use_container_width=True, type="primary", key="dash_go"):
            t = new_ticker.strip().upper()
            if t:
                # ── Ticker access gating ──
                try:
                    from database import get_user_plan_access
                    _uid = st.session_state.get("user_id") if st.session_state.get("logged_in") else None
                    _access = get_user_plan_access(_uid)
                    if _access["allowed_tickers"] is not None and t not in _access["allowed_tickers"]:
                        st.query_params.update({"page": _access["redirect_blocked"], "ticker": t})
                        st.rerun()
                except Exception:
                    pass
                st.query_params["page"] = "charts"
                st.query_params["ticker"] = t
                st.rerun()

    # ── Watchlist section ──
    if watchlist:
        st.markdown("""
        <p style="color:#94a3b8;font-size:14px;font-weight:500;margin:20px 0 10px;
                  text-transform:uppercase;letter-spacing:0.5px;">
            Your Watchlist</p>
        """, unsafe_allow_html=True)

        chips_html = ""
        for t in watchlist:
            chips_html += (
                f'<a href="/?page=charts&ticker={t}{auth_params}" target="_self" '
                f'style="display:inline-block;padding:8px 18px;margin:0 8px 8px 0;'
                f'background:#1e293b;border:1px solid #334155;border-radius:20px;'
                f'color:#e2e8f0;font-size:14px;font-weight:600;text-decoration:none;'
                f'letter-spacing:0.3px;transition:all .15s;"'
                f' onmouseover="this.style.borderColor=\'#3b82f6\';this.style.background=\'#1e3a5f\'"'
                f' onmouseout="this.style.borderColor=\'#334155\';this.style.background=\'#1e293b\'">'
                f'{t}</a>'
            )
        chips_html += (
            f'<a href="/?page=watchlist&ticker={ticker}{auth_params}" target="_self" '
            f'style="display:inline-block;padding:8px 18px;margin:0 8px 8px 0;'
            f'background:transparent;border:1px dashed #475569;border-radius:20px;'
            f'color:#64748b;font-size:14px;text-decoration:none;transition:all .15s;"'
            f' onmouseover="this.style.borderColor=\'#3b82f6\';this.style.color=\'#3b82f6\'"'
            f' onmouseout="this.style.borderColor=\'#475569\';this.style.color=\'#64748b\'">+ Manage</a>'
        )
        st.markdown(f'<div style="margin-bottom:8px;">{chips_html}</div>', unsafe_allow_html=True)

    # ── Quick-access cards ──
    st.markdown("""
    <p style="color:#94a3b8;font-size:14px;font-weight:500;margin:20px 0 10px;
              text-transform:uppercase;letter-spacing:0.5px;">
        Explore</p>
    """, unsafe_allow_html=True)

    def _card(icon, title, desc, page, extra_qs=""):
        link = f"/?page={page}&ticker={ticker}{auth_params}{extra_qs}"
        return (
            f'<a href="{link}" target="_self" style="text-decoration:none;display:block;height:100%;">'
            f'<div style="background:#1e293b;border-radius:12px;padding:20px 24px;'
            f'border:1px solid #334155;transition:all .2s;cursor:pointer;height:100%;'
            f'display:flex;flex-direction:column;gap:6px;"'
            f' onmouseover="this.style.borderColor=\'#3b82f6\';this.style.transform=\'translateY(-2px)\';'
            f'this.style.boxShadow=\'0 4px 12px rgba(59,130,246,0.15)\'"'
            f' onmouseout="this.style.borderColor=\'#334155\';this.style.transform=\'none\';'
            f'this.style.boxShadow=\'none\'">'
            f'<div style="font-size:28px;line-height:1;">{icon}</div>'
            f'<div style="color:#f0f0f0;font-size:16px;font-weight:600;margin-top:4px;">{title}</div>'
            f'<div style="color:#94a3b8;font-size:13px;line-height:1.4;">{desc}</div>'
            f'</div></a>'
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            _card("📊", "Charts", "Quarterly income, cash flow & balance sheet", "charts"),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _card("🔀", "Sankey Diagrams", "Interactive financial flow visualizations", "sankey"),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _card("📅", "Earnings Calendar", "Upcoming earnings dates & estimates", "earnings"),
            unsafe_allow_html=True,
        )

    st.markdown("")

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(
            _card("🏢", "Company Profile", "Overview, sector, market cap & more", "profile"),
            unsafe_allow_html=True,
        )
    with col5:
        st.markdown(
            _card("⭐", "Watchlist", "Manage your saved tickers", "watchlist"),
            unsafe_allow_html=True,
        )
    with col6:
        st.markdown(
            _card("📈", "NSFE Analysis", "Non-standard financial events", "nsfe"),
            unsafe_allow_html=True,
        )

    # ── Sign out ──
    st.markdown('<div style="margin-top:32px;"></div>', unsafe_allow_html=True)
    if st.button("Sign Out", key="dash_signout"):
        clear_session_state()
        st.session_state.page = "home"
        st.query_params.clear()
        st.query_params["page"] = "home"
        st.query_params["ticker"] = ticker
        st.rerun()
