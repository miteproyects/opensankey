"""
Audit logging for security-relevant events.

SEC-008: Tracks data exports, authentication events, and admin actions.

Events are logged to Python's logging system (which Railway captures)
and optionally to the database when available.

Usage:
    from audit_log import log_event, AuditEvent
    log_event(AuditEvent.DATA_EXPORT, user_email="user@example.com",
              details={"ticker": "NVDA", "format": "csv"})
"""

import time
import json
import logging
import streamlit as st
from enum import Enum

logger = logging.getLogger("audit")


class AuditEvent(str, Enum):
    """Enumeration of auditable events."""
    # Authentication
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    SIGNUP = "auth.signup"
    PASSWORD_RESET = "auth.password_reset"
    GOOGLE_LOGIN = "auth.google_login"

    # Data access
    DATA_EXPORT = "data.export"
    CHART_DOWNLOAD = "data.chart_download"
    SANKEY_EXPORT = "data.sankey_export"
    REPORT_GENERATE = "data.report_generate"

    # Admin actions
    ROLE_CHANGE = "admin.role_change"
    USER_DISABLE = "admin.user_disable"
    SETTINGS_CHANGE = "admin.settings_change"

    # Security
    RATE_LIMIT_HIT = "security.rate_limit"
    SESSION_EXPIRED = "security.session_expired"
    INVALID_TOKEN = "security.invalid_token"


def log_event(
    event: AuditEvent,
    user_email: str | None = None,
    user_uid: str | None = None,
    details: dict | None = None,
):
    """
    Log an audit event.

    Args:
        event: The type of event (from AuditEvent enum)
        user_email: Email of the user who triggered the event
        user_uid: UID of the user (Firebase UID)
        details: Additional context (ticker, format, target_user, etc.)
    """
    # Get user info from session state if not provided
    if user_email is None:
        user_email = st.session_state.get("user_email", "anonymous")
    if user_uid is None:
        user_uid = st.session_state.get("user_uid", "unknown")

    record = {
        "timestamp": time.time(),
        "event": event.value,
        "user_email": user_email,
        "user_uid": user_uid,
        "details": details or {},
    }

    # Log to Python logger (Railway captures stdout/stderr)
    logger.info(f"AUDIT | {event.value} | user={user_email} | {json.dumps(details or {})}")

    # Future: persist to database
    _persist_to_db(record)


def _persist_to_db(record: dict):
    """
    Persist audit record to PostgreSQL (if available).
    Gracefully no-ops if database is not configured.
    """
    try:
        from database import is_db_ready
        if not is_db_ready():
            return

        import psycopg2
        import os

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return

        # Ensure audit table exists
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                event VARCHAR(100) NOT NULL,
                user_email VARCHAR(255),
                user_uid VARCHAR(128),
                details JSONB DEFAULT '{}'::jsonb
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event);
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_email);
            CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp);
        """)

        cur.execute(
            """INSERT INTO audit_log (event, user_email, user_uid, details)
               VALUES (%s, %s, %s, %s)""",
            (record["event"], record["user_email"], record["user_uid"],
             json.dumps(record["details"]))
        )
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        # Never let audit logging break the main app
        logger.debug(f"Audit DB write skipped: {e}")
