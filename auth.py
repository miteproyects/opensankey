"""
QuarterCharts – Authentication Module
======================================
Handles user authentication via email/password and Google Sign-In,
with automatic account linking by email address.

Architecture:
- Email/password: bcrypt hashing stored in PostgreSQL
- Google Sign-In: GIS client-side flow → ID token verified server-side
  using Google's public keys (NO client secret needed)
- Sessions: DB-backed tokens passed via URL query params to survive
  Streamlit's full page reloads on <a> tag navigation
- Account linking: same email = same account, regardless of sign-in method

Best practices (Google guidance):
- If user signs in with Google and email matches existing account → link
- If user signs up with email and later signs in with Google → link
- Users can use either method after linking
"""

import secrets
import logging
from datetime import datetime, timezone, timedelta

import streamlit as st

logger = logging.getLogger(__name__)

# ── Password hashing ─────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── Google ID Token Verification ─────────────────────────────────────────────

GOOGLE_CLIENT_ID = "61622589594-3tet7j0drvkam8js5gtisbiv8bs2hevj.apps.googleusercontent.com"


def verify_google_id_token(id_token_str: str) -> dict | None:
    """
    Verify a Google ID token using Google's public keys.
    Returns payload dict with 'sub', 'email', 'name', 'picture', etc.
    Only needs the CLIENT_ID (public) — no client secret required.
    """
    try:
        from google.oauth2 import id_token as gid_token
        from google.auth.transport import requests as google_requests

        payload = gid_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        # Verify issuer
        if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            logger.warning(f"Invalid issuer: {payload.get('iss')}")
            return None

        # Verify email is present and verified
        if not payload.get("email_verified", False):
            logger.warning("Google email not verified")
            return None

        return payload

    except Exception as e:
        logger.warning(f"Google ID token verification failed: {e}")
        return None


# ── Session Management ───────────────────────────────────────────────────────

SESSION_DURATION_DAYS = 30
_SESSION_PARAM = "_sid"


def _generate_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(48)


def create_login_session(user_id: int) -> str:
    """Create a new session, store in DB, return the token."""
    from database import create_session
    token = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)
    create_session(token, user_id, expires)
    return token


def set_session_state(user: dict, token: str):
    """Populate st.session_state with auth info."""
    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["user_email"] = user["email"]
    st.session_state["user_display_name"] = user.get("display_name", "")
    st.session_state["user_avatar"] = user.get("avatar_url", "")
    st.session_state["auth_provider"] = user.get("auth_provider", "email")
    st.session_state["session_token"] = token


def clear_session_state():
    """Remove auth info from st.session_state and delete DB session."""
    # Try to get token from session state first, fall back to URL param
    token = st.session_state.get("session_token") or st.query_params.get(_SESSION_PARAM, "")
    if token:
        try:
            from database import delete_session
            delete_session(token)
        except Exception:
            pass
    for key in ["logged_in", "user_id", "user_email", "user_display_name",
                "user_avatar", "auth_provider", "session_token"]:
        st.session_state.pop(key, None)


def get_auth_params() -> str:
    """Return URL query string fragment with session token for nav links."""
    token = st.session_state.get("session_token", "")
    if token:
        return f"&{_SESSION_PARAM}={token}"
    return ""


def restore_session():
    """
    Check URL query params for a session token and restore login state.
    Called on every page load to survive Streamlit's full page reloads.
    """
    if st.session_state.get("logged_in"):
        return  # Already logged in this Streamlit session

    token = st.query_params.get(_SESSION_PARAM, "")
    if not token:
        return

    try:
        from database import get_session as db_get_session, get_user_by_id, update_last_login
        session = db_get_session(token)
        if not session:
            return  # Expired or invalid token

        user = get_user_by_id(session["user_id"])
        if not user or not user.get("is_active"):
            return

        set_session_state(user, token)
        update_last_login(user["id"])
    except Exception as e:
        logger.warning(f"Session restore failed: {e}")


# ── Login / Register Flows ───────────────────────────────────────────────────

def login_with_email(email: str, password: str) -> tuple[bool, str]:
    """
    Authenticate with email + password.
    Returns (success, error_message).
    On success, st.session_state is populated and session token is created.
    """
    from database import get_user_by_email, update_last_login

    email = email.strip().lower()
    if not email or not password:
        return False, "Please enter your email and password."

    user = get_user_by_email(email)
    if not user:
        return False, "No account found with this email. Please sign up first."

    if not user.get("password_hash"):
        # User exists but signed up with Google only
        return False, "This account uses Google sign-in. Click 'Continue with Google' or set a password in your account settings."

    if not _verify_password(password, user["password_hash"]):
        return False, "Incorrect password. Please try again."

    if not user.get("is_active"):
        return False, "This account has been deactivated."

    # Success
    token = create_login_session(user["id"])
    set_session_state(user, token)
    update_last_login(user["id"])
    return True, ""


def register_with_email(email: str, password: str, display_name: str = "") -> tuple[bool, str]:
    """
    Register a new account with email + password.
    If email already exists (from Google), link the password to it.
    """
    from database import get_user_by_email, create_user_email, link_password_to_user, update_last_login

    email = email.strip().lower()
    if not email or not password:
        return False, "Please fill in all fields."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    existing = get_user_by_email(email)
    if existing:
        if existing.get("password_hash"):
            return False, "An account with this email already exists. Please sign in."
        # Google-only account → link password to it
        pw_hash = _hash_password(password)
        if link_password_to_user(existing["id"], pw_hash):
            token = create_login_session(existing["id"])
            set_session_state(existing, token)
            update_last_login(existing["id"])
            return True, ""
        return False, "Failed to link password. Please try again."

    # New user
    pw_hash = _hash_password(password)
    user = create_user_email(email, pw_hash, display_name or email.split("@")[0])
    if not user:
        return False, "Registration failed. Please try again."

    token = create_login_session(user["id"])
    set_session_state(user, token)
    return True, ""


def verify_google_access_token(access_token: str) -> dict | None:
    """
    Verify a Google access token by calling Google's tokeninfo endpoint.
    Returns a dict with 'sub', 'email', 'email_verified', etc. on success.
    """
    import requests as req
    try:
        resp = req.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f"Google userinfo request failed: {resp.status_code}")
            return None

        data = resp.json()
        email = data.get("email", "")
        if not email or not data.get("email_verified", False):
            logger.warning("Google email not present or not verified")
            return None

        # Also verify the token was issued for our client
        tokeninfo_resp = req.get(
            f"https://oauth2.googleapis.com/tokeninfo?access_token={access_token}",
            timeout=10,
        )
        if tokeninfo_resp.status_code == 200:
            ti = tokeninfo_resp.json()
            if ti.get("aud") != GOOGLE_CLIENT_ID and ti.get("azp") != GOOGLE_CLIENT_ID:
                logger.warning(f"Token not issued for our client: aud={ti.get('aud')}")
                return None

        return {
            "sub": data.get("sub"),
            "email": email.lower(),
            "name": data.get("name", email.split("@")[0]),
            "picture": data.get("picture", ""),
            "email_verified": True,
        }

    except Exception as e:
        logger.warning(f"Google access token verification failed: {e}")
        return None


def login_with_google_access_token(access_token: str) -> tuple[bool, str]:
    """
    Authenticate with a Google access token (from OAuth2 token client flow).
    Same account creation/linking logic as login_with_google.
    """
    from database import (get_user_by_google_id, get_user_by_email,
                          create_user_google, link_google_to_user, update_last_login)

    payload = verify_google_access_token(access_token)
    if not payload:
        return False, "Google sign-in failed. Could not verify token."

    google_id = payload["sub"]
    email = payload["email"]
    name = payload.get("name", email.split("@")[0])
    picture = payload.get("picture", "")

    # 1. Check if user already exists by Google ID
    user = get_user_by_google_id(google_id)
    if user:
        token = create_login_session(user["id"])
        set_session_state(user, token)
        update_last_login(user["id"])
        return True, ""

    # 2. Check if email exists → link Google
    user = get_user_by_email(email)
    if user:
        link_google_to_user(user["id"], google_id, picture)
        token = create_login_session(user["id"])
        set_session_state(user, token)
        update_last_login(user["id"])
        return True, ""

    # 3. New user → create from Google
    user = create_user_google(email, google_id, name, picture)
    if not user:
        return False, "Failed to create account. Please try again."

    token = create_login_session(user["id"])
    set_session_state(user, token)
    return True, ""


def login_with_google(id_token_str: str) -> tuple[bool, str]:
    """
    Authenticate with a Google ID token (from GIS client-side flow).
    Handles account creation and linking automatically.
    """
    from database import (get_user_by_google_id, get_user_by_email,
                          create_user_google, link_google_to_user, update_last_login)

    payload = verify_google_id_token(id_token_str)
    if not payload:
        return False, "Google sign-in failed. Invalid or expired token."

    google_id = payload["sub"]
    email = payload["email"].lower()
    name = payload.get("name", email.split("@")[0])
    picture = payload.get("picture", "")

    # 1. Check if user already exists by Google ID
    user = get_user_by_google_id(google_id)
    if user:
        token = create_login_session(user["id"])
        set_session_state(user, token)
        update_last_login(user["id"])
        return True, ""

    # 2. Check if email exists (email/password account) → link Google
    user = get_user_by_email(email)
    if user:
        link_google_to_user(user["id"], google_id, picture)
        token = create_login_session(user["id"])
        set_session_state(user, token)
        update_last_login(user["id"])
        return True, ""

    # 3. New user → create from Google
    user = create_user_google(email, google_id, name, picture)
    if not user:
        return False, "Failed to create account. Please try again."

    token = create_login_session(user["id"])
    set_session_state(user, token)
    return True, ""
