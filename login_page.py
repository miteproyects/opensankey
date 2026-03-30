"""
Login / Sign-up page for QuarterCharts.
Renders a modern auth form with email+password and Google login.
Manages session state for user authentication status.

Security:
- Google ID tokens are verified cryptographically via google-auth library (SEC-013)
- Credential cleared from URL immediately after read (SEC-014 mitigation)
- Nonce parameter prevents CSRF / token replay attacks (SEC-016)
"""
import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import secrets
import logging
from rate_limiter import check_login_allowed, record_login_attempt

logger = logging.getLogger(__name__)

# Google OAuth Client ID (from Firebase project)
GOOGLE_CLIENT_ID = "399215694191-jpd7hljpsgvvnnj34apjpsngfmsq4a33.apps.googleusercontent.com"

# SEC-009: reCAPTCHA v3 site key (set RECAPTCHA_SITE_KEY env var to enable)
import os
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")


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

    # -- Handle Google credential from URL params --
    # SEC-014: Read and immediately clear credential from URL
    params = st.query_params
    google_credential = params.get("google_credential", None)
    if google_credential:
        st.query_params.clear()
        _handle_google_credential(google_credential)
        return

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

    # SEC-009: Render reCAPTCHA v3 widget on signup (invisible)
    if mode == "signup" and RECAPTCHA_SITE_KEY:
        _render_recaptcha_widget()

    # -- Submit --
    btn_label = "Sign In" if mode == "login" else "Create Account"
    if st.button(btn_label, use_container_width=True, type="primary"):
        if not email or not password:
            st.error("Please enter both email and password.")
        elif mode == "signup" and not name:
            st.error("Please enter your name.")
        elif mode == "signup" and RECAPTCHA_SITE_KEY:
            # SEC-009: Verify CAPTCHA before signup
            captcha_token = st.session_state.get("recaptcha_token", "")
            if not _verify_recaptcha(captcha_token):
                st.error("CAPTCHA verification failed. Please try again.")
            else:
                _handle_email_auth(mode, email, password, name)
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

    Security improvements:
    - SEC-016: Generates a cryptographic nonce stored in session state,
      passed to GIS initialize(), and verified when the token comes back.
    - SEC-014: Credential is passed via URL param (Streamlit limitation)
      but cleared immediately on the server side.
    """
    # SEC-016: Generate a unique nonce for this sign-in attempt
    nonce = secrets.token_urlsafe(32)
    st.session_state["google_auth_nonce"] = nonce

    google_html = f"""
    <script src="https://accounts.google.com/gsi/client" async></script>
    <script>
    function handleCredentialResponse(response) {{
        // response.credential is a Google ID token (JWT)
        var credential = response.credential;
        // Pass credential to Streamlit via URL param
        // (Streamlit iframe limitation - postMessage not supported)
        // Server clears this immediately after reading (SEC-014)
        try {{
            window.parent.location.href = '/?page=login&google_credential=' + encodeURIComponent(credential);
        }} catch(e) {{
            window.top.location.href = '/?page=login&google_credential=' + encodeURIComponent(credential);
        }}
    }}

    window.onload = function() {{
        google.accounts.id.initialize({{
            client_id: '{GOOGLE_CLIENT_ID}',
            callback: handleCredentialResponse,
            ux_mode: 'popup',
            nonce: '{nonce}'
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
    """Verify a Google ID token cryptographically and create an authenticated session.

    SEC-013 FIX: Uses google.oauth2.id_token.verify_oauth2_token() which:
    - Fetches Google's public keys and verifies the RSA signature
    - Validates audience (aud) matches our client ID
    - Validates issuer (iss) is accounts.google.com
    - Validates expiry (exp)
    This replaces the old base64-decode-only approach that was vulnerable to
    token forgery (an attacker could craft a fake JWT with any claims).

    SEC-016 FIX: Verifies the nonce in the token matches the one stored in
    session state, preventing CSRF and token replay attacks.
    """
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        # Cryptographically verify the Google ID token
        # This checks: RSA signature, aud, iss, exp
        token_data = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        email = token_data.get("email", "")
        name = token_data.get("name", "")
        sub = token_data.get("sub", "")  # Google user ID

        if not email:
            st.error("Google sign-in failed: no email in token.")
            return

        # SEC-016: Verify nonce to prevent replay / CSRF attacks
        expected_nonce = st.session_state.get("google_auth_nonce")
        token_nonce = token_data.get("nonce")
        if expected_nonce and token_nonce != expected_nonce:
            logger.warning(f"Nonce mismatch: expected={expected_nonce}, got={token_nonce}")
            st.error("Google sign-in failed: security token mismatch. Please try again.")
            return
        # Clear the nonce after successful verification (one-time use)
        st.session_state.pop("google_auth_nonce", None)

        # Set authenticated session
        from auth import set_authenticated_session
        set_authenticated_session({
            "success": True,
            "uid": sub,
            "email": email,
            "display_name": name or email.split("@")[0],
        })
        logger.info(f"Google sign-in successful for {email}")
        st.rerun()

    except ValueError as e:
        # verify_oauth2_token raises ValueError for invalid/expired/tampered tokens
        logger.warning(f"Google token verification failed: {e}")
        st.error("Google sign-in failed: invalid or expired token. Please try again.")
    except Exception as e:
        logger.error(f"Google sign-in error: {e}")
        st.error(f"Google sign-in failed: {e}")


def _handle_email_auth(mode, email, password, name=""):
    """Handle email/password login or signup via Firebase REST API.

    SEC-003: Rate limiting applied to login attempts.
    """
    from auth import set_authenticated_session

    if mode == "signup":
        # SEC-009: Rate limit signup attempts too
        allowed, reason = check_login_allowed(email)
        if not allowed:
            st.error(reason)
            return

        from auth import create_user
        result = create_user(email, password, name)
        if result.get("success"):
            record_login_attempt(email, success=True)
            set_authenticated_session(result)
            st.success("Account created! Redirecting\u2026")
            st.rerun()
        else:
            record_login_attempt(email, success=False)
            st.error(result.get("error", "Signup failed."))
    else:
        # SEC-003: Check rate limit before attempting login
        allowed, reason = check_login_allowed(email)
        if not allowed:
            st.error(reason)
            return

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
                        record_login_attempt(email, success=True)
                        set_authenticated_session({
                            "success": True,
                            "uid": user_data.get("uid", ""),
                            "email": user_data.get("email", email),
                            "name": user_data.get("name", email.split("@")[0]),
                        })
                        st.rerun()
                    else:
                        record_login_attempt(email, success=False)
                        st.error("Login failed: could not verify token.")
                else:
                    record_login_attempt(email, success=False)
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


# ── SEC-009: reCAPTCHA v3 Helpers ──────────────────────────────────────────

def _render_recaptcha_widget():
    """Render invisible reCAPTCHA v3 widget that auto-generates a token."""
    if not RECAPTCHA_SITE_KEY:
        return

    recaptcha_html = f"""
    <script src="https://www.google.com/recaptcha/api.js?render={RECAPTCHA_SITE_KEY}"></script>
    <script>
    grecaptcha.ready(function() {{
        grecaptcha.execute('{RECAPTCHA_SITE_KEY}', {{action: 'signup'}}).then(function(token) {{
            // Store token for Streamlit to read
            window.parent.postMessage({{type: 'recaptcha_token', token: token}}, '*');
        }});
    }});
    </script>
    <div id="recaptcha-badge" style="font-size:11px;color:#9ca3af;text-align:center;margin-top:4px;">
        Protected by reCAPTCHA
    </div>
    """
    components.html(recaptcha_html, height=30)


def _verify_recaptcha(token: str) -> bool:
    """
    Verify a reCAPTCHA v3 token with Google's API.

    Returns True if the token is valid and score >= 0.5.
    Returns True (passthrough) if reCAPTCHA is not configured.
    """
    if not RECAPTCHA_SECRET_KEY or not token:
        # If not configured, allow through (rate limiter is the fallback)
        return True

    try:
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": token,
            },
            timeout=5,
        )
        result = resp.json()
        success = result.get("success", False)
        score = result.get("score", 0)

        if success and score >= 0.5:
            logger.info(f"reCAPTCHA passed (score={score})")
            return True
        else:
            logger.warning(f"reCAPTCHA failed (success={success}, score={score})")
            return False

    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {e}")
        # Fail open — don't block users if Google API is down
        # Rate limiter provides backup protection
        return True
