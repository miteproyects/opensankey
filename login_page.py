"""
Login / Sign-up page for QuarterCharts.
Renders a modern auth form with email+password and social login buttons.
Manages session state for user authentication status.
"""
import streamlit as st


def render_login_page():
    """Render the login / sign-up page."""

    # ââ Auth mode toggle ââ
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    mode = st.session_state.auth_mode

    # ââ Page CSS ââ
    st.markdown("""
    <style>
    /* Center the auth card */
    .auth-wrapper {
        max-width: 420px;
        margin: 40px auto;
        padding: 36px 32px 28px;
        background: #fff;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    .auth-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1e293b;
        text-align: center;
        margin-bottom: 4px;
        font-family: Inter, system-ui, sans-serif;
    }
    .auth-subtitle {
        font-size: 0.9rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 24px;
        font-family: Inter, system-ui, sans-serif;
    }
    .auth-divider {
        display: flex;
        align-items: center;
        margin: 20px 0;
        color: #94a3b8;
        font-size: 0.82rem;
        font-family: Inter, system-ui, sans-serif;
    }
    .auth-divider::before, .auth-divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid #e2e8f0;
    }
    .auth-divider span {
        padding: 0 12px;
    }
    .social-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        width: 100%;
        padding: 11px 16px;
        border-radius: 10px;
        font-size: 0.92rem;
        font-weight: 600;
        font-family: Inter, system-ui, sans-serif;
        cursor: pointer;
        transition: all 0.15s ease;
        text-decoration: none;
        margin-bottom: 10px;
    }
    .social-google {
        background: #fff;
        color: #1e293b;
        border: 2px solid #e2e8f0;
    }
    .social-google:hover {
        background: #f8fafc;
        border-color: #cbd5e1;
    }
    .social-github {
        background: #24292f;
        color: #fff;
        border: 2px solid #24292f;
    }
    .social-github:hover {
        background: #1b1f23;
    }
    .auth-toggle {
        text-align: center;
        margin-top: 20px;
        font-size: 0.88rem;
        color: #64748b;
        font-family: Inter, system-ui, sans-serif;
    }
    .auth-toggle a {
        color: #3b82f6;
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
    }
    .auth-toggle a:hover {
        text-decoration: underline;
    }
    /* Style form inputs */
    .auth-wrapper [data-testid="stTextInput"] input {
        border-radius: 10px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 10px 14px !important;
        font-size: 0.92rem !important;
    }
    .auth-wrapper [data-testid="stTextInput"] input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ââ Auth card ââ
    st.markdown('<div class="auth-wrapper">', unsafe_allow_html=True)

    if mode == "login":
        st.markdown('<div class="auth-title">Welcome back</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Sign in to your QuarterCharts account</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="auth-title">Create account</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Start analyzing financials for free</div>', unsafe_allow_html=True)

    # Social login buttons
    st.markdown("""
    <button class="social-btn social-google" onclick="alert('Google login coming soon!')">
        <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
        Continue with Google
    </button>
    <button class="social-btn social-github" onclick="alert('GitHub login coming soon!')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
        Continue with GitHub
    </button>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-divider"><span>or</span></div>', unsafe_allow_html=True)

    # Email / password form
    with st.form("auth_form", clear_on_submit=False, border=False):
        if mode == "signup":
            name = st.text_input("Full name", placeholder="John Doe")

        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        if mode == "signup":
            confirm = st.text_input("Confirm password", type="password", placeholder="Confirm your password")

        btn_label = "Sign In" if mode == "login" else "Create Account"
        submitted = st.form_submit_button(btn_label, use_container_width=True, type="primary")

    if submitted:
        if not email or not password:
            st.error("Please fill in all fields.")
        elif mode == "signup" and password != confirm:
            st.error("Passwords do not match.")
        else:
            # Set logged-in state
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.session_state.user_name = name if mode == "signup" else email.split("@")[0]
            st.success("Welcome! Redirecting..." if mode == "login" else "Account created! Redirecting...")
            st.session_state.page = "charts"
            st.rerun()

    # Toggle between login and signup
    if mode == "login":
        toggle_col = st.columns([1, 2, 1])
        with toggle_col[1]:
            if st.button("Don't have an account? **Sign up**", use_container_width=True, type="tertiary"):
                st.session_state.auth_mode = "signup"
                st.rerun()
    else:
        toggle_col = st.columns([1, 2, 1])
        with toggle_col[1]:
            if st.button("Already have an account? **Sign in**", use_container_width=True, type="tertiary"):
                st.session_state.auth_mode = "login"
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
