"""
Login / Sign-up page for QuarterCharts.
Renders a modern auth form with email+password and Google login.
Manages session state for user authentication status.
"""
import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import urllib.parse


# Google OAuth Client ID (from Firebase project)
GOOGLE_CLIENT_ID = "399215694191-jpd7hljpsgvvnnj34apjpsngfmsq4a33.apps.googleusercontent.com"


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
        max-width: 420px; margin: 40px auto; padding: 0 16px;
    }
    .auth-title {
        font-size: 28px; font-weight: 700; text-align: center;
        margin-bottom: 4px;
    }
    .auth-subtitle {
        text-align: center; color: #6b7280; margin-bottom: 24px;
        font-size: 15px;
    }
    .divider-row {
        display: flex; align-items: center; margin: 18px 0;
    }
    .divider-row hr {
        flex: 1; border: none; border-top: 1px solid #e5e7eb;
    }
    .divider-row span {
        padding: 0 12px; color: #9ca3af; font-size: 13px;
    }
    .toggle-text {
        text-align: center; margin-top: 18px; font-size: 14px;
    }
    .toggle-text a {
        color: #2475fc; text-decoration: none; font-weight: 600;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

    # -- Wrapper open --
    st.markdown('<div class="auth-wrapper">', unsafe_allow_html=True)

    if mode == "login":
        st.markdown('<div class="auth-title">Welcome back</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Sign in to your QuarterCharts account</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="auth-title">Create account</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Get started with QuarterCharts</div>', unsafe_allow_html=True)

    # ââ Handle Google credential from URL params ââ
    params = st.query_params
    google_credential = params.get("google_credential", None)
    if google_credential:
        _handle_google_credential(google_credential)
        return

    # Also handle legacy google_token param (from previous implementation)
    google_token = params.get("google_token", None)
    if google_token:
        from auth import verify_id_token, set_authenticated_session
        user_data = verify_id_token(google_token)
        if user_data:
            set_authenticated_session({
                "success": True,
                "uid": user_data.get("uid", ""),
                "email": user_data.get("email", ""),
                "name": user_data.get("name", ""),
            })
            st.query_params.clear()
            st.rerun()

    # -- Google Sign-In (login mode only) --
    if mode == "login":
        _render_google_signin_button()

        # -- Divider --
        st.markdown("""
        <div class="divider-row">
            <hr><span>or continue with email</span><hr>
        </div>
        """, unsafe_allow_html=True)

    # -- Name field (signup only) --
    name = ""
    if mode == "signup":
        name = st.text_input("Full Name", placeholder="Your full name")

    # -- Email & Password --
    email = st.text_input("Email", placeholder="you@example.com")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    # -- Submit --
    btn_label = "Sign In" if mode == "login" else "Create Account"
    if st.button(btn_label, use_container_width=True, type="primary"):
        if not email or not password:
            st.error("Please enter both email and password.")
        elif mode == "signup" and not name:
            st.error("Please enter your name.")
        else:
            _handle_email_auth(mode, email, password, name)

    # -- Toggle login/signup --
    if mode == "login":
        st.markdown(
            '<div class="toggle-text">Don\'t have an account? '
            '<a onclick="fetch(\'/_stcore/set_query_params?auth_mode=signup\')">Sign up</a></div>',
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Switch to Sign Up", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.rerun()
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Switch to Sign In", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()

    # -- Wrapper close --
    st.markdown('</div>', unsafe_allow_html=True)


def _render_google_signin_button():
    """Render the Google Sign-In button using Google Identity Services (GIS).

    GIS works inside iframes (unlike Firebase signInWithPopup which requires
    http/https protocol). The flow:
    1. GIS library renders its own button inside the iframe
    2. User clicks -> Google popup opens for authentication
    3. On success, callback receives a JWT credential (Google ID token)
    4. Credential is passed to Streamlit via URL parameter for server-side verification
    """
    google_html = f"""
    <script src="https://accounts.google.com/gsi/client" async></script>
    <script>
    function handleCredentialResponse(response) {{
        // response.credential is a Google ID token (JWT)
        var credential = response.credential;
        // Navigate the parent window to pass the credential back to Streamlit
        try {{
            window.parent.location.href = '/?page=login&google_credential=' + encodeURIComponent(credential);
        }} catch(e) {{
            // Fallback: try top-level navigation
            window.top.location.href = '/?page=login&google_credential=' + encodeURIComponent(credential);
        }}
    }}

    window.onload = function() {{
        google.accounts.id.initialize({{
            client_id: '{GOOGLE_CLIENT_ID}',
            callback: handleCredentialResponse,
            ux_mode: 'popup'
        }});
        google.accounts.id.renderButton(
            document.getElementById('g_id_signin'),
            {{
                theme: 'outline',
                size: 'large',
                text: 'continue_with',
                shape: 'rectangular',
                width: 380,
                logo_alignment: 'left'
            }}
        );
    }};
    </script>
    <div id="g_id_signin" style="display:flex;justify-content:center;margin:8px 0;"></div>
    """
    components.html(google_html, height=50)


def _handle_google_credential(credential):
    """Verify a Google ID token (from GIS) and create an authenticated session."""
    try:
        # Decode the JWT to extract user info without external library
        # Google ID tokens are JWTs with 3 parts: header.payload.signature
        import base64

        parts = credential.split(".")
        if len(parts) != 3:
            st.error("Invalid Google credential format.")
            st.query_params.clear()
            return

        # Decode the payload (part 2) - add padding if needed
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)  # Add padding
        decoded = base64.urlsafe_b64decode(payload)
        token_data = json.loads(decoded)

        email = token_data.get("email", "")
        name = token_data.get("name", "")
        sub = token_data.get("sub", "")  # Google user ID
        email_verified = token_data.get("email_verified", False)

        # Verify the token is for our app
        aud = token_data.get("aud", "")
        if aud != GOOGLE_CLIENT_ID:
            st.error("Google sign-in failed: token audience mismatch.")
            st.query_params.clear()
            return

        # Verify issuer
        iss = token_data.get("iss", "")
        if iss not in ("accounts.google.com", "https://accounts.google.com"):
            st.error("Google sign-in failed: invalid token issuer.")
            st.query_params.clear()
            return

        # Check expiry
        import time
        exp = token_data.get("exp", 0)
        if time.time() > exp:
            st.error("Google sign-in failed: token expired.")
            st.query_params.clear()
            return

        if not email:
            st.error("Google sign-in failed: no email in token.")
            st.query_params.clear()
            return

        # Set authenticated session
        from auth import set_authenticated_session
        set_authenticated_session({
            "success": True,
            "uid": sub,
            "email": email,
            "name": name or email.split("@")[0],
        })
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.error(f"Google sign-in failed: {e}")
        st.query_params.clear()


def _handle_email_auth(mode, email, password, name=""):
    """Handle email/password login or signup via Firebase REST API."""
    from auth import set_authenticated_session

    if mode == "signup":
        from auth import create_user
        result = create_user(email, password, name)
        if result.get("success"):
            set_authenticated_session(result)
            st.success("Account created! Redirecting\u2026")
            st.rerun()
        else:
            st.error(result.get("error", "Signup failed."))
    else:
        # -- Email/password login via Firebase REST API --
        from auth import get_firebase_config, verify_id_token
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
                        st.rerun()
                    else:
                        st.error("Login failed: could not verify token.")
                else:
                    msg = data.get("error", {}).get("message", "Login failed.")
                    friendly = {
                        "EMAIL_NOT_FOUND": "No account found with that email.",
                        "INVALID_PASSWORD": "Incorrect password.",
                        "INVALID_LOGIN_CREDENTIALS": "Invalid email or password.",
                        "USER_DISABLED": "This account has been disabled.",
                        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
                    }
                    st.error(friendly.get(msg, f"Login failed: {msg}"))
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {e}")
        else:
            st.error("Firebase not configured. Please contact support.")
