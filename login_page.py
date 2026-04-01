"""
Login / Sign-up page for QuarterCharts.
Renders a modern auth form with email+password and Google Sign-In.

Google Sign-In uses the GIS (Google Identity Services) client-side flow:
- Only the public CLIENT_ID is needed (no client secret)
- Google returns a JWT ID token directly in the browser
- Server verifies the token using Google's public keys
- This bypasses Railway's env-var isolation issue entirely
"""
import os
import streamlit as st
import streamlit.components.v1 as components
import logging

logger = logging.getLogger(__name__)

# Declare the Google Sign-In component served from a real URL on the same
# origin (https://quartercharts.com). Unlike components.html() which uses
# srcdoc (null origin), this iframe gets origin = https://quartercharts.com,
# which satisfies Google's OAuth 2.0 origin validation.
_COMPONENT_DIR = os.path.join(os.path.dirname(__file__), "google_signin_component")
_google_signin = components.declare_component("google_signin", path=_COMPONENT_DIR)

GOOGLE_CLIENT_ID = "61622589594-3tet7j0drvkam8js5gtisbiv8bs2hevj.apps.googleusercontent.com"


def render_login_page():
    """Render the login / sign-up page."""

    # -- If already logged in, redirect to dashboard --
    if st.session_state.get("logged_in"):
        from auth import get_auth_params
        st.session_state.page = "dashboard"
        st.query_params["page"] = "dashboard"
        st.rerun()

    # -- Handle Google ID token callback --
    google_credential = st.query_params.get("credential", "")
    if google_credential:
        st.query_params.clear()
        from auth import login_with_google, get_auth_params
        success, error = login_with_google(google_credential)
        if success:
            st.session_state.page = "dashboard"
            _params = get_auth_params()
            st.query_params["page"] = "dashboard"
            token = st.session_state.get("session_token", "")
            if token:
                st.query_params["_sid"] = token
            st.rerun()
        else:
            st.session_state["_auth_error"] = error

    # -- Auth mode toggle --
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"
    mode = st.session_state.auth_mode

    # -- Display any error message --
    error_msg = st.session_state.pop("_auth_error", "")
    if error_msg:
        st.markdown(f"""
        <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;
                    padding:12px 16px;margin:8px auto 0;max-width:460px;
                    color:#dc2626;font-size:14px;">
            {error_msg}
        </div>""", unsafe_allow_html=True)

    # -- Page title --
    if mode == "login":
        st.markdown('<h2 style="text-align:center;margin-top:40px;color:#f0f0f0;">Welcome back</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#9ca3af;margin-top:-10px;">Sign in to your QuarterCharts account</p>', unsafe_allow_html=True)
    else:
        st.markdown('<h2 style="text-align:center;margin-top:40px;color:#f0f0f0;">Create an account</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#9ca3af;margin-top:-10px;">Get started with QuarterCharts</p>', unsafe_allow_html=True)

    # -- Google Sign-In button (GIS client-side flow) --
    # Uses Google Identity Services library to get an ID token directly
    # in the browser — no server-side client secret exchange needed.
    _render_google_button()

    # -- OR divider --
    st.markdown("""
    <div style="display:flex;align-items:center;max-width:420px;margin:24px auto;">
        <div style="flex:1;height:1px;background:#374151;"></div>
        <span style="padding:0 16px;color:#6b7280;font-size:13px;">OR</span>
        <div style="flex:1;height:1px;background:#374151;"></div>
    </div>""", unsafe_allow_html=True)

    # -- Email / Password form --
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if mode == "signup":
            display_name = st.text_input("Name", placeholder="Your name", key="reg_name")
        email = st.text_input("Email", placeholder="you@example.com", key="auth_email")
        password = st.text_input("Password", type="password",
                                 placeholder="Enter your password" if mode == "login" else "Min. 8 characters",
                                 key="auth_password")

        btn_label = "Sign In" if mode == "login" else "Create Account"
        if st.button(btn_label, use_container_width=True, type="primary"):
            from auth import login_with_email, register_with_email, get_auth_params
            if mode == "login":
                success, error = login_with_email(email, password)
            else:
                name = st.session_state.get("reg_name", "")
                success, error = register_with_email(email, password, name)

            if success:
                st.session_state.page = "dashboard"
                st.query_params["page"] = "dashboard"
                token = st.session_state.get("session_token", "")
                if token:
                    st.query_params["_sid"] = token
                st.rerun()
            else:
                st.error(error)

        # -- Toggle login / signup --
        st.markdown("<hr style='border-color:#374151;margin:24px 0 16px;'>", unsafe_allow_html=True)
        if mode == "login":
            st.markdown('<p style="text-align:center;color:#9ca3af;font-size:14px;">Don\'t have an account?</p>', unsafe_allow_html=True)
            if st.button("Create an account", use_container_width=True, key="switch_signup"):
                st.session_state.auth_mode = "signup"
                st.rerun()
        else:
            st.markdown('<p style="text-align:center;color:#9ca3af;font-size:14px;">Already have an account?</p>', unsafe_allow_html=True)
            if st.button("Sign in", use_container_width=True, key="switch_login"):
                st.session_state.auth_mode = "login"
                st.rerun()

        # -- Terms / Privacy --
        st.markdown("""
        <p style="text-align:center;color:#6b7280;font-size:11px;margin-top:16px;">
            By continuing, you agree to QuarterCharts'
            <a href="/?page=terms" target="_self" style="color:#3b82f6;">Terms of Service</a>
            and <a href="/?page=privacy" target="_self" style="color:#3b82f6;">Privacy Policy</a>.
        </p>""", unsafe_allow_html=True)


def _render_google_button():
    """Render the Google Sign-In button using a declared component.

    declare_component(path=...) serves the component HTML from a real URL on
    https://quartercharts.com (not srcdoc), so the iframe's origin is
    https://quartercharts.com — satisfying Google's OAuth 2.0 policy.

    The component's JS navigates window.parent to /?page=login&credential=...
    when the user completes Google sign-in.
    """
    _google_signin(key="google_signin_btn", height=50)
