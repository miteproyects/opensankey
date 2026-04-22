"""
User dashboard page for QuarterCharts.
Shows profile info, account settings, and sign-out.
"""
import streamlit as st
import logging

logger = logging.getLogger(__name__)


def render_user_page():
    """Render the user dashboard."""
    from auth import get_auth_params, clear_session_state

    # Require login
    if not st.session_state.get("logged_in"):
        st.session_state.page = "login"
        st.query_params["page"] = "login"
        st.rerun()

    ticker = st.session_state.get("ticker", "NVDA")
    email = st.session_state.get("user_email", "")
    display_name = st.session_state.get("user_display_name", "")
    avatar = st.session_state.get("user_avatar", "")
    provider = st.session_state.get("auth_provider", "email")

    # ── Header ──
    st.markdown('<h2 style="color:#f0f0f0;margin-top:20px;">My Account</h2>', unsafe_allow_html=True)

    # ── Profile card ──
    avatar_html = ""
    if avatar:
        avatar_html = f'<img src="{avatar}" style="width:64px;height:64px;border-radius:50%;border:2px solid #3b82f6;" referrerpolicy="no-referrer"/>'
    else:
        initial = (display_name or email or "U")[0].upper()
        avatar_html = f"""
        <div style="width:64px;height:64px;border-radius:50%;background:#3b82f6;
                    display:flex;align-items:center;justify-content:center;
                    color:white;font-size:28px;font-weight:700;">{initial}</div>"""

    provider_badge = {
        "email": "Email",
        "google": "Google",
        "both": "Email + Google",
    }.get(provider, provider)

    st.markdown(f"""
    <div style="background:#1e293b;border-radius:12px;padding:24px;margin:16px 0;
                display:flex;align-items:center;gap:20px;">
        {avatar_html}
        <div>
            <div style="color:#f0f0f0;font-size:20px;font-weight:600;">{display_name or 'User'}</div>
            <div style="color:#9ca3af;font-size:14px;">{email}</div>
            <div style="color:#6b7280;font-size:12px;margin-top:4px;">
                Sign-in method: <span style="color:#3b82f6;">{provider_badge}</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Settings sections ──
    st.markdown("---")

    # Display name
    st.markdown("#### Profile Settings")
    new_name = st.text_input("Display Name", value=display_name, key="edit_name")
    if st.button("Update Name", key="btn_update_name"):
        if new_name.strip() and new_name.strip() != display_name:
            from database import update_user_display_name
            user_id = st.session_state.get("user_id")
            if update_user_display_name(user_id, new_name.strip()):
                st.session_state["user_display_name"] = new_name.strip()
                st.success("Name updated.")
                st.rerun()
            else:
                st.error("Failed to update name.")

    # Change password (only if user has email auth)
    if provider in ("email", "both"):
        st.markdown("---")
        st.markdown("#### Change Password")
        new_pw = st.text_input("New Password", type="password", placeholder="Min. 8 characters", key="new_pw")
        confirm_pw = st.text_input("Confirm Password", type="password", key="confirm_pw")
        if st.button("Update Password", key="btn_update_pw"):
            if not new_pw or len(new_pw) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_pw != confirm_pw:
                st.error("Passwords don't match.")
            else:
                from auth import _hash_password
                from database import update_user_password
                user_id = st.session_state.get("user_id")
                if update_user_password(user_id, _hash_password(new_pw)):
                    st.success("Password updated.")
                else:
                    st.error("Failed to update password.")

    # Set password (for Google-only users)
    if provider == "google":
        st.markdown("---")
        st.markdown("#### Set a Password")
        st.markdown('<p style="color:#9ca3af;font-size:14px;">Add email/password sign-in to your Google-linked account.</p>', unsafe_allow_html=True)
        set_pw = st.text_input("Password", type="password", placeholder="Min. 8 characters", key="set_pw")
        set_confirm = st.text_input("Confirm Password", type="password", key="set_confirm")
        if st.button("Set Password", key="btn_set_pw"):
            if not set_pw or len(set_pw) < 8:
                st.error("Password must be at least 8 characters.")
            elif set_pw != set_confirm:
                st.error("Passwords don't match.")
            else:
                from auth import _hash_password
                from database import link_password_to_user
                user_id = st.session_state.get("user_id")
                if link_password_to_user(user_id, _hash_password(set_pw)):
                    st.session_state["auth_provider"] = "both"
                    st.success("Password set. You can now sign in with email + password too.")
                    st.rerun()
                else:
                    st.error("Failed to set password.")

    # ── Sign Out ──
    st.markdown("---")
    st.markdown("")
    if st.button("Sign Out", type="primary", width="stretch", key="btn_signout"):
        clear_session_state()
        st.session_state.page = "home"
        st.query_params.clear()
        st.query_params["page"] = "home"
        st.query_params["ticker"] = ticker
        st.rerun()
