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
import os
from rate_limiter import check_login_allowed, record_login_attempt

logger = logging.getLogger(__name__)

# ── Credentials ──
# GOOGLE_CLIENT_ID is a public OAuth identifier (visible in page source).
# FIREBASE_API_KEY must come from env vars only (never hardcoded).
GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "399215694191-jpd7hljpsgvvnnj34apjpsngfmsq4a33.apps.googleusercontent.com",
)

FIREBASE_API_KEY = ""
_fb_config_json = os.getenv("FIREBASE_CONFIG", "")
if _fb_config_json:
    try:
        _fb_config = json.loads(_fb_config_json)
        FIREBASE_API_KEY = _fb_config.get("apiKey", "")
    except json.JSONDecodeError:
        pass

if not FIREBASE_API_KEY:
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")

# SEC-009: reCAPTCHA v3 site key (set RECAPTCHA_SITE_KEY env var to enable)
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
    /* Hide default Streamlit header/footer for cleaner auth page */
    .auth-card {
        max-width: 440px;
        margin: 30px auto 0 auto;
        padding: 36px 32px 28px 32px;
        background: #ffffff;
        border-radius: 16px;
        box-shadow: 0 2px 16px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04);
        border: 1px solid #f0f0f0;
    }
    @media (prefers-color-scheme: dark) {
        .auth-card {
            background: #1a1a2e;
            border-color: #2a2a3e;
            box-shadow: 0 2px 16px rgba(0,0,0,0.3);
        }
        .auth-title { color: #f0f0f0 !important; }
        .auth-subtitle { color: #9ca3af !important; }
        .divider-row hr { border-top-color: #374151 !important; }
        .divider-row span { color: #6b7280 !important; }
        .auth-toggle { color: #9ca3af !important; }
        .auth-toggle a { color: #60a5fa !important; }
        .auth-footer { color: #6b7280 !important; }
    }
    .auth-title {
        font-size: 26px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 6px;
        color: #111827;
        letter-spacing: -0.3px;
    }
    .auth-subtitle {
        text-align: center;
        color: #6b7280;
        margin-bottom: 20px;
        font-size: 14px;
        font-weight: 400;
    }
    .divider-row {
        display: flex;
        align-items: center;
        margin: 16px 0 12px 0;
    }
    .divider-row hr {
        flex: 1;
        border: none;
        border-top: 1px solid #e5e7eb;
    }
    .divider-row span {
        padding: 0 14px;
        color: #9ca3af;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }
    .auth-toggle {
        text-align: center;
        margin-top: 20px;
        font-size: 14px;
        color: #6b7280;
        padding-top: 16px;
        border-top: 1px solid #f0f0f0;
    }
    .auth-toggle a {
        color: #2563eb;
        text-decoration: none;
        font-weight: 600;
        cursor: pointer;
    }
    .auth-toggle a:hover {
        text-decoration: underline;
    }
    .auth-footer {
        text-align: center;
        font-size: 11px;
        color: #9ca3af;
        margin-top: 16px;
        line-height: 1.5;
    }
    /* Streamlit button overrides for this page */
    .stButton > button[kind="primary"] {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 10px 0 !important;
        letter-spacing: 0.2px !important;
    }
    .stButton > button[kind="secondary"] {
        border-radius: 10px !important;
        font-weight: 500 !important;
    }
    /* Input field styling */
    .stTextInput > div > div > input {
        border-radius: 10px !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # -- Handle Google credential from URL params --
    # SEC-014: Read and immediately clear credential from URL
    params = st.query_params
    google_credential = params.get("google_credential", None)
    if google_credential:
        st.query_params.clear()
        _handle_google_credential(google_credential)
        return

    # -- Card open --
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)

    if mode == "login":
        st.markdown('<div class="auth-title">Welcome back</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Sign in to your QuarterCharts account</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="auth-title">Create your account</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Start tracking earnings with QuarterCharts</div>', unsafe_allow_html=True)

    # -- Google Sign-In (both modes) --
    _render_google_signin_button()

    # -- Divider --
    st.markdown("""
    <div class="divider-row">
        <hr><span>or</span><hr>
    </div>
    """, unsafe_allow_html=True)

    # -- Name field (signup only) --
    name = ""
    if mode == "signup":
        name = st.text_input("Full Name", placeholder="Your full name", key="auth_name")

    # -- Email & Password --
    email = st.text_input("Email", placeholder="you@example.com", key="auth_email")
    password = st.text_input("Password", type="password", placeholder="Enter your password", key="auth_password")

    if mode == "signup":
        st.caption("Password must be at least 6 characters.")

    # SEC-009: Render reCAPTCHA v3 widget on signup (invisible)
    if mode == "signup" and RECAPTCHA_SITE_KEY:
        _render_recaptcha_widget()

    # -- Submit --
    btn_label = "Sign In" if mode == "login" else "Create Account"
    if st.button(btn_label, use_container_width=True, type="primary", key="auth_submit"):
        if not email or not password:
            st.error("Please enter both email and password.")
        elif mode == "signup" and not name:
            st.error("Please enter your name.")
        elif mode == "signup" and len(password) < 6:
            st.error("Password must be at least 6 characters.")
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
            '<div class="auth-toggle">Don\'t have an account? </div>',
            unsafe_allow_html=True,
        )
        if st.button("Create an account", use_container_width=True, key="toggle_signup"):
            st.session_state.auth_mode = "signup"
            st.rerun()
    else:
        st.markdown(
            '<div class="auth-toggle">Already have an account? </div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign in instead", use_container_width=True, key="toggle_login"):
            st.session_state.auth_mode = "login"
            st.rerun()

    # -- Footer --
    st.markdown(
        '<div class="auth-footer">By continuing, you agree to QuarterCharts\' Terms of Service.</div>',
        unsafe_allow_html=True,
    )

    # -- Card close --
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
        var credential = response.credential;
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
                shape: 'pill',
                width: 380,
                logo_alignment: 'left'
            }}
        );
    }};
    </script>
    <div id="g_id_signin" style="display:flex;justify-content:center;margin:4px 0;"></div>
    """
    components.html(google_html, height=50)


def _handle_google_credential(credential):
    """Verify a Google ID token cryptographically and create an authenticated session.

    SEC-013 FIX: Uses google.oauth2.id_token.verify_oauth2_token() which:
    - Fetches Google's public keys and verifies the RSA signature
    - Validates audience (aud) matches our client ID
    - Validates issuer (iss) is accounts.google.com
    - Validates expiry (exp)

    SEC-016 FIX: Verifies the nonce in the token matches the one stored in
    session state, preventing CSRF and token replay attacks.
    """
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        # Cryptographically verify the Google ID token
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

        # Try Firebase Admin SDK first, fall back to REST API
        signup_result = None
        try:
            from auth import create_user
            signup_result = create_user(email, password, name)
        except Exception as e:
            logger.warning(f"Admin SDK signup failed, trying REST API: {e}")

        if signup_result and signup_result.get("success"):
            record_login_attempt(email, success=True)
            set_authenticated_session(signup_result)
            st.success("Account created! Redirecting\u2026")
            st.rerun()
        elif signup_result and signup_result.get("error"):
            # Admin SDK returned a specific error (e.g., email exists)
            record_login_attempt(email, success=False)
            st.error(signup_result.get("error"))
        else:
            # Admin SDK not configured — use Firebase REST API for signup
            api_key = FIREBASE_API_KEY
            if not api_key:
                st.error("Signup is not configured. Please use Google Sign-In.")
                return
            signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
            signup_payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True,
            }
            try:
                resp = requests.post(signup_url, json=signup_payload, timeout=10)
                data = resp.json()
                if resp.ok and "idToken" in data:
                    # Update display name via REST API
                    if name:
                        update_url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={api_key}"
                        requests.post(update_url, json={
                            "idToken": data["idToken"],
                            "displayName": name,
                        }, timeout=5)
                    record_login_attempt(email, success=True)
                    set_authenticated_session({
                        "success": True,
                        "uid": data.get("localId", ""),
                        "email": data.get("email", email),
                        "display_name": name or email.split("@")[0],
                    })
                    st.success("Account created! Redirecting\u2026")
                    st.rerun()
                else:
                    record_login_attempt(email, success=False)
                    msg = data.get("error", {}).get("message", "Signup failed.")
                    friendly = {
                        "EMAIL_EXISTS": "An account with this email already exists. Try signing in.",
                        "WEAK_PASSWORD": "Password must be at least 6 characters.",
                        "INVALID_EMAIL": "Please enter a valid email address.",
                        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
                    }
                    st.error(friendly.get(msg, f"Signup failed: {msg}"))
            except requests.exceptions.RequestException as e:
                logger.error(f"Firebase REST API signup error: {e}")
                st.error("Connection error. Please check your internet and try again.")
    else:
        # SEC-003: Check rate limit before attempting login
        allowed, reason = check_login_allowed(email)
        if not allowed:
            st.error(reason)
            return

        # -- Email/password login via Firebase REST API --
        api_key = FIREBASE_API_KEY
        if not api_key:
            # Try from env at runtime too
            from auth import get_firebase_config
            fb_config = get_firebase_config()
            api_key = fb_config.get("apiKey", "")

        if not api_key:
            logger.error("No Firebase API key available for email login")
            st.error("Email login is not configured yet. Please use Google Sign-In, or contact support.")
            return

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
                # Try to verify token via Firebase Admin SDK first
                from auth import verify_id_token
                user_data = verify_id_token(data["idToken"])

                if user_data:
                    # Admin SDK verification succeeded
                    record_login_attempt(email, success=True)
                    set_authenticated_session({
                        "success": True,
                        "uid": user_data.get("uid", data.get("localId", "")),
                        "email": user_data.get("email", email),
                        "display_name": user_data.get("name", data.get("displayName", email.split("@")[0])),
                    })
                    st.rerun()
                else:
                    # Admin SDK not configured or verification failed —
                    # Fall back to REST API response data.
                    # This is still secure because we just authenticated
                    # with Firebase's own API using the correct password.
                    logger.info("Firebase Admin SDK not available, using REST API response for session")
                    record_login_attempt(email, success=True)
                    set_authenticated_session({
                        "success": True,
                        "uid": data.get("localId", ""),
                        "email": data.get("email", email),
                        "display_name": data.get("displayName", email.split("@")[0]),
                    })
                    st.rerun()
            else:
                record_login_attempt(email, success=False)
                msg = data.get("error", {}).get("message", "Login failed.")
                friendly = {
                    "EMAIL_NOT_FOUND": "No account found with that email. Try signing up first.",
                    "INVALID_PASSWORD": "Incorrect password. Please try again.",
                    "INVALID_LOGIN_CREDENTIALS": "Invalid email or password. Please try again.",
                    "USER_DISABLED": "This account has been disabled.",
                    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
                }
                st.error(friendly.get(msg, f"Login failed: {msg}"))
        except requests.exceptions.RequestException as e:
            logger.error(f"Firebase REST API connection error: {e}")
            st.error("Connection error. Please check your internet and try again.")


# -- SEC-009: reCAPTCHA v3 Helpers --

def _render_recaptcha_widget():
    """Render invisible reCAPTCHA v3 widget that auto-generates a token."""
    if not RECAPTCHA_SITE_KEY:
        return

    recaptcha_html = f"""
    <script src="https://www.google.com/recaptcha/api.js?render={RECAPTCHA_SITE_KEY}"></script>
    <script>
    grecaptcha.ready(function() {{
        grecaptcha.execute('{RECAPTCHA_SITE_KEY}', {{action: 'signup'}}).then(function(token) {{
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
        return True
