"""
Login / Sign-up page for QuarterCharts.
Renders a modern auth form with email+password and Google login.
Manages session state for user authentication status.
"""
import streamlit as st
import streamlit.components.v1 as components
import requests
import json


def render_login_page():
    """Render the login / sign-up page."""

    # -- Auth mode toggle --
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    mode = st.session_state.auth_mode

    # -- Page CSS --
    st.markdown("""
    <style>
    .auth-wrapper {
        max-width: 420px;
        margin: 40px auto;
        padding: 0 16px;
    }
    .auth-title {
        text-align: center;
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 6px;
        font-family: Inter, system-ui, sans-serif;
    }
    .auth-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 0.92rem;
        margin-bottom: 28px;
        font-family: Inter, system-ui, sans-serif;
    }
    .auth-divider {
        display: flex;
        align-items: center;
        margin: 16px 0;
        font-size: 0.82rem;
        color: #94a3b8;
        font-family: Inter, system-ui, sans-serif;
    }
    .auth-divider::before, .auth-divider::after {
        content: "";
        flex: 1;
        border-bottom: 1px solid #e2e8f0;
    }
    .auth-divider::before { margin-right: 12px; }
    .auth-divider::after  { margin-left: 12px; }
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
    .auth-wrapper [data-testid="stTextInput"] input {
        border-radius: 10px;
        padding: 11px 14px;
        font-size: 0.9rem;
    }
    .auth-wrapper [data-testid="stFormSubmitButton"] button {
        border-radius: 10px;
        padding: 11px 16px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # -- Auth card --
    st.markdown('<div class="auth-wrapper">', unsafe_allow_html=True)

    if mode == "login":
        st.markdown('<div class="auth-title">Welcome back</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Sign in to your QuarterCharts account</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="auth-title">Create account</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Start analyzing financials for free</div>', unsafe_allow_html=True)

    # -- Google Sign-In (login mode only) --
    if mode == "login":
        from auth import get_firebase_config
        fb_config = get_firebase_config()
        api_key = fb_config.get("apiKey", "")
        auth_domain = fb_config.get("authDomain", "")

        if api_key and auth_domain:
            if "google_id_token" not in st.session_state:
                st.session_state.google_id_token = None

            google_html = f"""
            <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
            <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>
            <script>
            const firebaseConfig = {{
                apiKey: "{api_key}",
                authDomain: "{auth_domain}"
            }};
            if (!firebase.apps.length) firebase.initializeApp(firebaseConfig);

            function signInWithGoogle() {{
                const provider = new firebase.auth.GoogleAuthProvider();
                firebase.auth().signInWithPopup(provider)
                    .then((result) => {{
                        return result.user.getIdToken();
                    }})
                    .then((idToken) => {{
                        const url = new URL(window.parent.location.href);
                        url.searchParams.set("google_token", idToken);
                        window.parent.location.href = url.toString();
                    }})
                    .catch((error) => {{
                        document.getElementById("google-error").textContent = error.message;
                    }});
            }}
            </script>
            <button onclick="signInWithGoogle()" style="
                display:flex;align-items:center;justify-content:center;gap:10px;
                width:100%;padding:11px 16px;border-radius:10px;font-size:0.92rem;
                font-weight:600;cursor:pointer;background:#fff;border:1.5px solid #e2e8f0;
                color:#1e293b;font-family:Inter,system-ui,sans-serif;
            ">
                <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                Continue with Google
            </button>
            <div id="google-error" style="color:#ef4444;font-size:0.85rem;text-align:center;margin-top:4px;"></div>
            """
            components.html(google_html, height=70)

            # Handle Google token from URL params
            params = st.query_params
            google_token = params.get("google_token", None)
            if google_token:
                from auth import verify_id_token, set_authenticated_session
                user_data = verify_id_token(google_token)
                if user_data:
                    set_authenticated_session({
                        "success": True,
                        "uid": user_data.get("uid", ""),
                        "email": user_data.get("email", ""),
                        "name": user_data.get("name", user_data.get("email", "User")),
                    })
                    st.query_params.clear()
                    st.success("Signed in with Google! Redirecting\u2026")
                    st.rerun()
                else:
                    st.error("Google sign-in failed. Please try again.")
                    st.query_params.clear()

    # Divider
    st.markdown('<div class="auth-divider">or</div>', unsafe_allow_html=True)

    # -- Email / password form --
    with st.form("auth_form", clear_on_submit=False, border=False):
        if mode == "signup":
            name = st.text_input("Full name", placeholder="John Doe")

        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        if mode == "signup":
            confirm = st.text_input("Confirm password", type="password", placeholder="Confirm your password")

        btn_label = "Sign In" if mode == "login" else "Create Account"
        submitted = st.form_submit_button(btn_label, use_container_width=True)

    # Handle form submission
    if submitted:
        if not email or not password:
            st.error("Please fill in all fields.")
        elif mode == "signup" and password != confirm:
            st.error("Passwords don't match.")
        elif mode == "signup":
            from auth import create_user, set_authenticated_session
            result = create_user(email, password, name)
            if result.get("success"):
                set_authenticated_session(result)
                st.success("Account created! Redirecting\u2026")
                st.rerun()
            else:
                st.error(result.get("error", "Signup failed."))
        else:
            # -- Email/password login via Firebase REST API --
            from auth import get_firebase_config, set_authenticated_session, verify_id_token
            fb_config = get_firebase_config()
            api_key = fb_config.get("apiKey", "")

            if api_key:
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
                payload = {
                    "email": email,
                    "password": password,
                    "returnSecureToken": True,
                }
                try:
                    resp = requests.post(url, json=payload, timeout=10)
                    data = resp.json()
                    if resp.ok and "idToken" in data:
                        user_data = verify_id_token(data["idToken"])
                        if user_data:
                            set_authenticated_session({
                                "success": True,
                                "uid": user_data.get("uid", ""),
                                "email": user_data.get("email", email),
                                "name": user_data.get("name", email.split("@")[0]),
                            })
                            st.success("Welcome back! Redirecting\u2026")
                            st.rerun()
                        else:
                            st.error("Token verification failed.")
                    else:
                        err_msg = data.get("error", {}).get("message", "Login failed.")
                        friendly = {
                            "EMAIL_NOT_FOUND": "No account found with this email.",
                            "INVALID_PASSWORD": "Incorrect password.",
                            "USER_DISABLED": "This account has been disabled.",
                            "INVALID_LOGIN_CREDENTIALS": "Invalid email or password.",
                        }
                        st.error(friendly.get(err_msg, f"Login failed: {err_msg}"))
                except requests.exceptions.RequestException as e:
                    st.error("Connection error. Please try again.")
            else:
                from auth import demo_login
                result = demo_login(email, password)
                if result.get("success"):
                    set_authenticated_session(result)
                    st.success("Welcome back! Redirecting\u2026")
                    st.rerun()
                else:
                    st.error(result.get("error", "Login failed."))

    # Toggle login / signup
    toggle_text = "Don't have an account? <a>Sign up</a>" if mode == "login" else "Already have an account? <a>Sign in</a>"
    st.markdown(f'<div class="auth-toggle">{toggle_text}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # -- Mode toggle buttons --
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if mode == "login":
            if st.button("Switch to Sign Up", use_container_width=True, type="tertiary"):
                st.session_state.auth_mode = "signup"
                st.rerun()
        else:
            if st.button("Switch to Sign In", use_container_width=True, type="tertiary"):
                st.session_state.auth_mode = "login"
                st.rerun()
