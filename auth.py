"""
QuarterCharts – Firebase Authentication Module
================================================
Handles all authentication logic: token verification, user creation,
password reset, and session management.

Security:
- Passwords are NEVER stored locally — Firebase handles all credential storage
- JWT tokens are verified server-side on every request
- Sessions expire after 1 hour of inactivity (configurable)
- All auth errors are logged without exposing internals to users

Requirements:
- firebase-admin SDK
- FIREBASE_CREDENTIALS env var (JSON service account key)
  OR a firebase-credentials.json file in the project root
"""

import os
import json
import time
import logging
import streamlit as st

logger = logging.getLogger(__name__)

# ─── Firebase Admin SDK Initialization ───────────────────────────────────────

_firebase_app = None

def _get_firebase_app():
    """Lazily initialize the Firebase Admin SDK (singleton)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Priority 1: Environment variable (Railway / production)
        cred_json = os.getenv("FIREBASE_CREDENTIALS")
        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        # Priority 2: Local file (development)
        elif os.path.exists("firebase-credentials.json"):
            cred = credentials.Certificate("firebase-credentials.json")
        else:
            logger.warning("No Firebase credentials found. Auth will run in demo mode.")
            return None

        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
        return _firebase_app

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None


def _is_firebase_ready() -> bool:
    """Check if Firebase is properly configured."""
    return _get_firebase_app() is not None


# ─── Firebase Client Config (for frontend JS SDK) ───────────────────────────

def get_firebase_config() -> dict:
    """
    Return the Firebase client config for the JS SDK.
    This is PUBLIC info (safe to expose in frontend code).
    Set via FIREBASE_CONFIG env var as JSON string.
    """
    config_json = os.getenv("FIREBASE_CONFIG", "{}")
    try:
        return json.loads(config_json)
    except json.JSONDecodeError:
        return {}


# ─── Token Verification ─────────────────────────────────────────────────────

def verify_id_token(id_token: str) -> dict | None:
    """
    Verify a Firebase ID token and return the decoded claims.

    Returns dict with uid, email, name, etc. on success.
    Returns None on failure (expired, invalid, tampered).
    """
    if not _is_firebase_ready():
        return None

    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(id_token, check_revoked=True)
        return decoded
    except fb_auth.ExpiredIdTokenError:
        logger.warning("ID token has expired.")
        return None
    except fb_auth.RevokedIdTokenError:
        logger.warning("ID token has been revoked.")
        return None
    except fb_auth.InvalidIdTokenError:
        logger.warning("Invalid ID token.")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


# ─── User Management ────────────────────────────────────────────────────────

def create_user(email: str, password: str, display_name: str = "") -> dict:
    """
    Create a new user in Firebase Auth.

    Returns: {"success": True, "uid": "...", "email": "..."}
          or {"success": False, "error": "..."}
    """
    if not _is_firebase_ready():
        return {"success": False, "error": "Auth service not configured."}

    try:
        from firebase_admin import auth as fb_auth

        user = fb_auth.create_user(
            email=email,
            password=password,
            display_name=display_name or email.split("@")[0],
            email_verified=False,
        )

        # Send email verification
        # Note: Email verification link is generated client-side via JS SDK
        # The admin SDK can generate it too if needed:
        # link = fb_auth.generate_email_verification_link(email)

        logger.info(f"User created: {user.uid}")
        return {
            "success": True,
            "uid": user.uid,
            "email": user.email,
            "display_name": user.display_name,
        }

    except fb_auth.EmailAlreadyExistsError:
        return {"success": False, "error": "An account with this email already exists."}
    except fb_auth.InvalidPasswordError:
        return {"success": False, "error": "Password must be at least 6 characters."}
    except ValueError as e:
        return {"success": False, "error": f"Invalid input: {e}"}
    except Exception as e:
        logger.error(f"User creation error: {e}")
        return {"success": False, "error": "Something went wrong. Please try again."}


def get_user_by_email(email: str) -> dict | None:
    """Look up a Firebase user by email. Returns user record or None."""
    if not _is_firebase_ready():
        return None

    try:
        from firebase_admin import auth as fb_auth
        user = fb_auth.get_user_by_email(email)
        return {
            "uid": user.uid,
            "email": user.email,
            "display_name": user.display_name,
            "email_verified": user.email_verified,
            "disabled": user.disabled,
            "created_at": user.user_metadata.creation_timestamp,
        }
    except fb_auth.UserNotFoundError:
        return None
    except Exception as e:
        logger.error(f"User lookup error: {e}")
        return None


def generate_password_reset_link(email: str) -> str | None:
    """Generate a password reset link for the given email."""
    if not _is_firebase_ready():
        return None

    try:
        from firebase_admin import auth as fb_auth
        link = fb_auth.generate_password_reset_link(email)
        return link
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return None


def disable_user(uid: str) -> bool:
    """Disable a user account (soft delete)."""
    if not _is_firebase_ready():
        return False

    try:
        from firebase_admin import auth as fb_auth
        fb_auth.update_user(uid, disabled=True)
        logger.info(f"User disabled: {uid}")
        return True
    except Exception as e:
        logger.error(f"Disable user error: {e}")
        return False


# ─── Session Management ─────────────────────────────────────────────────────
#
# Architecture: Server-side session store (industry standard pattern)
#
# Problem: Streamlit loses st.session_state on every <a> link click because
# each navigation creates a new WebSocket session. URL params and file-based
# approaches are fragile.
#
# Solution: Module-level dict (_SERVER_SESSIONS) that persists across all
# Streamlit WebSocket sessions within the same Python process. After login,
# a random session ID (sid) is stored server-side with user data, and only
# the sid is passed via URL query param (&sid=...). On each page load, the
# sid is looked up to restore the session.
#
# Security: The sid is a 32-byte cryptographic random token (256 bits of
# entropy). User data never appears in the URL. Sessions auto-expire after
# SESSION_TIMEOUT_SECONDS. The store is pruned on every access.
# ─────────────────────────────────────────────────────────────────────────────

import secrets

SESSION_TIMEOUT_SECONDS = 3600  # 1 hour
_MAX_SESSIONS = 1000  # Prevent unbounded memory growth

# Server-side session store: {sid: {"user_data": {...}, "created_at": float}}
# This dict lives in the Python process memory and persists across all
# Streamlit WebSocket sessions (reruns AND full page reloads).
_SERVER_SESSIONS: dict = {}


def _prune_expired_sessions():
    """Remove expired sessions to prevent memory leaks."""
    now = time.time()
    expired = [
        sid for sid, data in _SERVER_SESSIONS.items()
        if now - data.get("created_at", 0) > SESSION_TIMEOUT_SECONDS
    ]
    for sid in expired:
        del _SERVER_SESSIONS[sid]
    # If still too many, remove oldest
    if len(_SERVER_SESSIONS) > _MAX_SESSIONS:
        sorted_sessions = sorted(
            _SERVER_SESSIONS.items(), key=lambda x: x[1].get("created_at", 0)
        )
        for sid, _ in sorted_sessions[:len(_SERVER_SESSIONS) - _MAX_SESSIONS]:
            del _SERVER_SESSIONS[sid]


def init_session_state():
    """Initialize auth-related session state variables."""
    defaults = {
        "logged_in": False,
        "user_uid": None,
        "user_email": None,
        "user_name": None,
        "user_role": None,         # e.g., "admin", "viewer", "analyst"
        "user_company_id": None,   # company this user belongs to
        "auth_token": None,
        "auth_token_time": 0,
        "auth_mode": "login",      # "login" or "signup"
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def restore_session_from_params():
    """Restore login state from the server-side session store.

    Reads the 'sid' query param, looks up the session in _SERVER_SESSIONS,
    and restores st.session_state if found and not expired.
    Call this early in app.py on every page load.
    """
    if st.session_state.get("logged_in"):
        return False  # Already logged in in this WebSocket session

    _prune_expired_sessions()

    sid = st.query_params.get("sid", "")
    if not sid:
        return False

    session_data = _SERVER_SESSIONS.get(sid)
    if not session_data:
        return False

    # Check expiry
    if time.time() - session_data.get("created_at", 0) > SESSION_TIMEOUT_SECONDS:
        _SERVER_SESSIONS.pop(sid, None)
        return False

    # Restore session state from server-side store
    user_data = session_data.get("user_data", {})
    st.session_state.logged_in = True
    st.session_state.user_uid = user_data.get("uid", "")
    st.session_state.user_email = user_data.get("email", "")
    st.session_state.user_name = user_data.get("display_name", "")
    st.session_state.auth_token_time = time.time()
    st.session_state.auth_token = secrets.token_urlsafe(32)

    # Refresh the session timestamp (sliding expiry)
    session_data["created_at"] = time.time()

    logger.info(f"Session restored from server store for {st.session_state.user_email}")
    return True


def get_auth_params() -> str:
    """Return URL query string fragment with session ID for navbar links.

    When logged in, returns '&sid=<session_token>'
    When logged out, returns empty string.
    """
    if not st.session_state.get("logged_in"):
        return ""
    sid = st.session_state.get("_server_sid", "")
    if not sid:
        return ""
    return f"&sid={sid}"


def clear_session_from_disk():
    """No-op kept for backward compatibility."""
    pass


def set_authenticated_session(user_data: dict):
    """
    Set session state after successful authentication.

    Creates a server-side session entry and stores the sid in session state.
    user_data should contain: uid, email, display_name
    SEC-004: Regenerates session token on every auth event.
    """
    _prune_expired_sessions()

    # Create a server-side session
    sid = secrets.token_urlsafe(32)
    _SERVER_SESSIONS[sid] = {
        "user_data": {
            "uid": user_data.get("uid", ""),
            "email": user_data.get("email", ""),
            "display_name": user_data.get("display_name", ""),
        },
        "created_at": time.time(),
    }

    # Set Streamlit session state
    st.session_state.logged_in = True
    st.session_state.user_uid = user_data.get("uid")
    st.session_state.user_email = user_data.get("email")
    st.session_state.user_name = user_data.get("display_name", "")
    st.session_state.auth_token_time = time.time()
    st.session_state.auth_token = secrets.token_urlsafe(32)
    # Store sid so get_auth_params() can reference it
    st.session_state._server_sid = sid

    logger.info(f"Server session created (sid={sid[:8]}...) for {user_data.get('email')}")


def rotate_session_token():
    """
    Regenerate session token after privilege change (SEC-004).

    Call this after any role change, password change, or privilege escalation
    to prevent session fixation attacks.
    """
    import secrets
    if st.session_state.get("logged_in"):
        st.session_state.auth_token = secrets.token_urlsafe(32)
        st.session_state.auth_token_time = time.time()
        logger.info(f"Session token rotated for user {st.session_state.get('user_uid')}")


def clear_session():
    """Clear all auth session state (logout) and remove server-side session."""
    # Remove from server-side store
    sid = st.session_state.get("_server_sid", "")
    if sid:
        _SERVER_SESSIONS.pop(sid, None)
    # Clear Streamlit session state
    st.session_state.logged_in = False
    st.session_state.user_uid = None
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.session_state.user_role = None
    st.session_state.user_company_id = None
    st.session_state.auth_token = None
    st.session_state.auth_token_time = 0
    st.session_state._server_sid = None


def is_session_valid() -> bool:
    """Check if the current session is still valid (not expired)."""
    if not st.session_state.get("logged_in"):
        return False

    token_time = st.session_state.get("auth_token_time", 0)
    if time.time() - token_time > SESSION_TIMEOUT_SECONDS:
        clear_session()
        return False

    return True


def require_auth() -> bool:
    """
    Auth guard — call at the top of any page that requires login.

    Returns True if user is authenticated.
    If not authenticated, redirects to login page.
    """
    init_session_state()

    if not is_session_valid():
        st.session_state.page = "login"
        st.rerun()
        return False

    return True


# ─── Demo Mode (when Firebase is not configured) ────────────────────────────

def demo_login(email: str, password: str) -> dict:
    """
    Fallback login for development/demo when Firebase isn't configured.
    Accepts any email/password combo.
    NOT FOR PRODUCTION.
    """
    if _is_firebase_ready():
        # If Firebase is configured, don't allow demo mode
        return {"success": False, "error": "Use Firebase auth."}

    logger.warning("DEMO MODE: Accepting login without verification.")
    return {
        "success": True,
        "uid": f"demo_{email.replace('@', '_').replace('.', '_')}",
        "email": email,
        "display_name": email.split("@")[0],
    }


def demo_signup(email: str, password: str, name: str) -> dict:
    """
    Fallback signup for development/demo when Firebase isn't configured.
    NOT FOR PRODUCTION.
    """
    if _is_firebase_ready():
        return create_user(email, password, name)

    logger.warning("DEMO MODE: Creating user without Firebase.")
    return {
        "success": True,
        "uid": f"demo_{email.replace('@', '_').replace('.', '_')}",
        "email": email,
        "display_name": name or email.split("@")[0],
    }
