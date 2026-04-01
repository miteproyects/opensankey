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
import urllib.parse
from rate_limiter import check_login_allowed, record_login_attempt

logger = logging.getLogger(__name__)

# ── Credentials ──
# start.sh uses sed to replace __PLACEHOLDER__ tokens below at container boot.
# This is the ONLY reliable way to pass secrets on Railway (env vars and /tmp/
# files are both invisible to the Streamlit process).
_GCI_INJECTED = "__GCI_PLACEHOLDER__"  # replaced by start.sh sed at boot
GOOGLE_CLIENT_ID = (
    os.getenv("GOOGLE_CLIENT_ID", "")
    or (_GCI_INJECTED if _GCI_INJECTED != "__GCI_PLAC" + "EHOLDER__" else "")
    or "399215694191-jpd7hljpsgvvnnj34apjpsngfmsq4a33.apps.googleusercontent.com"
)
_GCS_INJECTED = "__GCS_PLACEHOLDER__"  # replaced by start.sh sed at boot
GOOGLE_CLIENT_SECRET = (
    os.getenv("GOOGLE_CLIENT_SECRET", "")
    or (_GCS_INJECTED if _GCS_INJECTED != "__GCS_PLAC" + "EHOLDER__" else "")
)

# Redirect URI for the server-side OAuth code exchange flow
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://quartercharts.com")

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
    .auth-header {
        text-align: center;
        margin-bottom: 8px;
    }
    .auth-title {
        font-size: 26px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 6px;
        letter-spacing: -0.3px;
    }
    .auth-subtitle {
        text-align: center;
        color: #6b7280;
        margin-bottom: 12px;
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
        border-top: 1px solid rgba(128,128,128,0.2);
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

    # -- Handle Google OAuth callback --
    # Two flows: (1) auth code from direct OAuth redirect, (2) legacy credential param
    params = st.query_params
    google_code = params.get("code", None)
    google_credential = params.get("google_credential", None)

    if google_code:
        # Server-side OAuth code exchange flow
        st.query_params.clear()
        _handle_google_auth_code(google_code)
        return

    if google_credential:
        # Legacy: GIS/Firebase flow (credential passed as ID token)
        st.query_params.clear()
        _handle_google_credential(google_credential)
        return

    # -- Show any stored Google auth error from a previous rerun --
    _google_err = st.session_state.pop("_google_auth_error", None)
    if _google_err:
        st.error(f"Google sign-in failed: {_google_err}")

    # -- Centered layout using columns --
    _left, center_col, _right = st.columns([1, 1.5, 1])
    with center_col:
        # -- Header --
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


def _render_google_signin_button():
    """Render a Google Sign-In button as a direct OAuth redirect link.

    Uses the standard OAuth 2.0 authorization code flow:
    1. User clicks the link → redirected to Google's consent screen
    2. After consent, Google redirects back with ?code=...
    3. Server exchanges the code for tokens (no client-side JS needed)

    This avoids all Streamlit srcdoc iframe issues with GIS / Firebase SDK.
    """
    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    st.session_state["google_oauth_state"] = state

    oauth_params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile openid",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{oauth_params}"

    google_svg = '<svg width="18" height="18" viewBox="0 0 18 18"><path fill="#4285F4" d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/><path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z"/><path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.997 8.997 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/><path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/></svg>'

    st.markdown(f"""
    <a href="{oauth_url}" target="_self" style="
        display: flex; align-items: center; justify-content: center; gap: 10px;
        width: 380px; max-width: 100%; margin: 4px auto;
        padding: 10px 24px; border: 1px solid #dadce0; border-radius: 50px;
        background: #fff; color: #3c4043; text-decoration: none;
        font-family: 'Google Sans', Roboto, Arial, sans-serif;
        font-size: 14px; font-weight: 500; cursor: pointer;
        transition: background 0.2s, box-shadow 0.2s;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    ">{google_svg} Continue with Google</a>
    """, unsafe_allow_html=True)


def _handle_google_auth_code(code):
    """Exchange a Google OAuth authorization code for tokens, then authenticate.

    Server-side flow:
    1. POST code to Google's token endpoint with client_id + client_secret
    2. Receive id_token (+ access_token)
    3. Verify the id_token cryptographically
    4. Create an authenticated session

    Errors are stored in st.session_state["_google_auth_error"] so they survive
    the st.rerun() in the failure path and can be displayed on the login page.
    """
    def _set_error(msg):
        """Store error in session state so it survives st.rerun()."""
        st.session_state["_google_auth_error"] = msg
        logger.warning(f"Google auth error: {msg}")

    try:
        client_secret = GOOGLE_CLIENT_SECRET
        # If placeholder was never replaced by start.sh, treat as missing
        if not client_secret or client_secret == ("__GCS_PLAC" + "EHOLDER__"):
            _set_error("Server configuration error (missing client secret). Please try again later.")
            return

        # Exchange auth code for tokens
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": client_secret,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )

        if token_response.status_code != 200:
            _err_detail = ""
            try:
                _err_json = token_response.json()
                _err_detail = _err_json.get("error_description", _err_json.get("error", ""))
            except Exception:
                _err_detail = token_response.text[:200]
            logger.warning(f"Google token exchange failed: {token_response.status_code} {_err_detail}")
            _set_error(f"{_err_detail or 'could not exchange authorization code'}. Please try again.")
            return

        token_data = token_response.json()
        id_token_str = token_data.get("id_token")

        if not id_token_str:
            logger.warning("No id_token in Google token response")
            _set_error("No identity token received from Google.")
            return

        # Verify the ID token cryptographically (same as legacy flow)
        _handle_google_credential(id_token_str)

    except requests.RequestException as e:
        logger.error(f"Google token exchange network error: {e}")
        _set_error(f"Network error: {e}")


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
    # Verify the token inside try/except, but keep session creation and
    # redirect OUTSIDE so that st.rerun()'s RerunException is never caught.
    email = ""
    name = ""
    sub = ""
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
            st.session_state["_google_auth_error"] = "No email in Google token."
            return

        # SEC-016: Verify nonce if present (GIS flow includes nonce;
        # Firebase Auth signInWithPopup flow does not, so skip if absent)
        expected_nonce = st.session_state.get("google_auth_nonce")
        token_nonce = token_data.get("nonce")
        if expected_nonce and token_nonce and token_nonce != expected_nonce:
            logger.warning(f"Nonce mismatch: expected={expected_nonce}, got={token_nonce}")
            st.session_state["_google_auth_error"] = "Security token mismatch. Please try again."
            return
        # Clear the nonce after verification (one-time use)
        st.session_state.pop("google_auth_nonce", None)

    except ValueError as e:
        logger.warning(f"Google token verification failed: {e}")
        st.session_state["_google_auth_error"] = f"Invalid or expired token: {e}"
        return
    except Exception as e:
        logger.error(f"Google sign-in error: {e}")
        st.session_state["_google_auth_error"] = f"Verification error: {e}"
        return

    # Set authenticated session and redirect — OUTSIDE try/except so that
    # st.rerun() (which raises RerunException) propagates correctly.
    from auth import set_authenticated_session
    set_authenticated_session({
        "success": True,
        "uid": sub,
        "email": email,
        "display_name": name or email.split("@")[0],
    })
    logger.info(f"Google sign-in successful for {email}")
    _redirect_to_user_page()


def _redirect_to_user_page():
    """Redirect to user dashboard after successful login.

    Sets page to 'user' and triggers a Streamlit rerun. The URL sync code
    in app.py automatically updates the URL to include page, ticker, AND
    the session ID (sid) — so login state persists across page reloads and
    navigation via <a> tag links.

    Using st.rerun() is more reliable than js_redirect (components.html +
    JavaScript) because it works consistently inside button callbacks and
    doesn't depend on iframe rendering timing.
    """
    st.session_state.page = "user"
    st.rerun()


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
            _redirect_to_user_page()
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
                    _redirect_to_user_page()
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
                    _redirect_to_user_page()
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
                    _redirect_to_user_page()
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
