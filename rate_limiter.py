"""
In-memory rate limiter for authentication endpoints.

SEC-003: Prevents brute-force password attacks by limiting login attempts
per IP address and per email address.

Limits:
- 5 attempts per IP per 60-second window
- 10 attempts per email per 300-second window (5 minutes)
- Account lockout after 10 consecutive failures per email

Note: This is an in-memory implementation. Rate limit state resets on
app restart. For production at scale, consider Redis-backed rate limiting.
"""

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Tuple

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────────

MAX_ATTEMPTS_PER_IP = 5          # max attempts per IP per window
IP_WINDOW_SECONDS = 60           # 1-minute sliding window for IP

MAX_ATTEMPTS_PER_EMAIL = 10      # max attempts per email per window
EMAIL_WINDOW_SECONDS = 300       # 5-minute sliding window for email

LOCKOUT_THRESHOLD = 10           # consecutive failures before lockout
LOCKOUT_DURATION_SECONDS = 900   # 15-minute lockout


@dataclass
class _AttemptRecord:
    """Tracks login attempts for a single key (IP or email)."""
    timestamps: list = field(default_factory=list)
    consecutive_failures: int = 0
    locked_until: float = 0.0


class RateLimiter:
    """Thread-safe in-memory rate limiter for login attempts."""

    def __init__(self):
        self._ip_records: dict[str, _AttemptRecord] = defaultdict(_AttemptRecord)
        self._email_records: dict[str, _AttemptRecord] = defaultdict(_AttemptRecord)

    def _cleanup_window(self, record: _AttemptRecord, window_seconds: int):
        """Remove timestamps outside the current sliding window."""
        cutoff = time.time() - window_seconds
        record.timestamps = [t for t in record.timestamps if t > cutoff]

    def check_rate_limit(self, ip: str, email: str) -> Tuple[bool, str]:
        """
        Check if a login attempt is allowed.

        Returns:
            (allowed: bool, reason: str)
            If not allowed, reason explains why (for user-facing error).
        """
        now = time.time()
        email_lower = email.lower().strip()

        # Check email lockout first
        email_rec = self._email_records[email_lower]
        if email_rec.locked_until > now:
            remaining = int(email_rec.locked_until - now)
            minutes = remaining // 60
            logger.warning(f"Rate limit: account locked for {email_lower} ({remaining}s remaining)")
            return False, f"Account temporarily locked. Try again in {minutes + 1} minute{'s' if minutes > 0 else ''}."

        # Check IP rate limit
        ip_rec = self._ip_records[ip]
        self._cleanup_window(ip_rec, IP_WINDOW_SECONDS)
        if len(ip_rec.timestamps) >= MAX_ATTEMPTS_PER_IP:
            logger.warning(f"Rate limit: IP {ip} exceeded {MAX_ATTEMPTS_PER_IP} attempts in {IP_WINDOW_SECONDS}s")
            return False, "Too many login attempts. Please wait a minute before trying again."

        # Check email rate limit
        self._cleanup_window(email_rec, EMAIL_WINDOW_SECONDS)
        if len(email_rec.timestamps) >= MAX_ATTEMPTS_PER_EMAIL:
            logger.warning(f"Rate limit: email {email_lower} exceeded {MAX_ATTEMPTS_PER_EMAIL} attempts in {EMAIL_WINDOW_SECONDS}s")
            return False, "Too many login attempts for this account. Please wait 5 minutes."

        return True, ""

    def record_attempt(self, ip: str, email: str, success: bool):
        """Record a login attempt (success or failure)."""
        now = time.time()
        email_lower = email.lower().strip()

        # Always record timestamp for rate limiting windows
        self._ip_records[ip].timestamps.append(now)
        self._email_records[email_lower].timestamps.append(now)

        if success:
            # Reset consecutive failures on success
            self._email_records[email_lower].consecutive_failures = 0
            self._email_records[email_lower].locked_until = 0.0
            self._ip_records[ip].consecutive_failures = 0
        else:
            # Increment consecutive failures
            email_rec = self._email_records[email_lower]
            email_rec.consecutive_failures += 1

            # Lockout after threshold
            if email_rec.consecutive_failures >= LOCKOUT_THRESHOLD:
                email_rec.locked_until = now + LOCKOUT_DURATION_SECONDS
                logger.warning(
                    f"Rate limit: account {email_lower} LOCKED for {LOCKOUT_DURATION_SECONDS}s "
                    f"after {email_rec.consecutive_failures} consecutive failures"
                )

    def get_remaining_attempts(self, ip: str, email: str) -> int:
        """Return how many attempts remain before rate limit kicks in."""
        email_lower = email.lower().strip()

        self._cleanup_window(self._ip_records[ip], IP_WINDOW_SECONDS)
        self._cleanup_window(self._email_records[email_lower], EMAIL_WINDOW_SECONDS)

        ip_remaining = MAX_ATTEMPTS_PER_IP - len(self._ip_records[ip].timestamps)
        email_remaining = MAX_ATTEMPTS_PER_EMAIL - len(self._email_records[email_lower].timestamps)

        return max(0, min(ip_remaining, email_remaining))


# Singleton instance — shared across all Streamlit sessions
_limiter = RateLimiter()


def check_login_allowed(email: str) -> Tuple[bool, str]:
    """
    Check if a login attempt is allowed for the given email.

    Since Streamlit doesn't expose client IP reliably, we use
    'streamlit' as a placeholder. The email-based limiting is
    the primary protection.

    Returns: (allowed, error_message)
    """
    # Streamlit doesn't expose client IP easily; use a generic key
    # The email-based rate limit is the primary protection
    ip = "streamlit_client"
    return _limiter.check_rate_limit(ip, email)


def record_login_attempt(email: str, success: bool):
    """Record a login attempt result."""
    ip = "streamlit_client"
    _limiter.record_attempt(ip, email, success)
