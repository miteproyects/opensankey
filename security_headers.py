"""
Security Headers Middleware for Streamlit (Tornado).

Injects security-critical HTTP response headers into every response:
- Strict-Transport-Security (HSTS) — SEC-001
- Content-Security-Policy (CSP) — SEC-002
- X-Frame-Options — SEC-005
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy
- Strips Server version header — SEC-010

Usage: Call inject_security_headers() once at app startup (before any st.* calls).
"""

import logging

logger = logging.getLogger(__name__)

# ── CSP Policy ──────────────────────────────────────────────────────────────
# Streamlit needs 'unsafe-inline' for its own scripts/styles.
# GIS (Google Identity Services) needs accounts.google.com.
# Plotly needs cdn.plot.ly.
CSP_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://cdn.plot.ly https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://accounts.google.com https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: https: blob:",
    "connect-src 'self' https://accounts.google.com https://*.googleapis.com https://*.google.com https://*.firebaseio.com wss://*.firebaseio.com https://query1.finance.yahoo.com https://query2.finance.yahoo.com https://*.yahoo.com https://securetoken.googleapis.com",
    "frame-src 'self' https://accounts.google.com",
    "frame-ancestors 'self'",
    "base-uri 'self'",
    "form-action 'self' https://accounts.google.com",
    "upgrade-insecure-requests",
])


def inject_security_headers():
    """
    Monkey-patch Tornado's RequestHandler to inject security headers
    into every HTTP response served by Streamlit.

    Must be called ONCE at startup, before Streamlit serves any requests.
    """
    try:
        from tornado.web import RequestHandler

        _original_set_default_headers = RequestHandler.set_default_headers

        def _secure_set_default_headers(self):
            _original_set_default_headers(self)

            # SEC-001: HSTS — force HTTPS for 1 year, include subdomains
            self.set_header(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload"
            )

            # SEC-002: Content Security Policy
            self.set_header("Content-Security-Policy", CSP_POLICY)

            # SEC-005: Clickjacking protection (X-Frame-Options + CSP frame-ancestors)
            # Using SAMEORIGIN (not DENY) because Streamlit uses same-origin iframes
            # for components.html() — including the Google Sign-In button
            self.set_header("X-Frame-Options", "SAMEORIGIN")

            # SEC-010: Prevent MIME-type sniffing
            self.set_header("X-Content-Type-Options", "nosniff")

            # Referrer policy — don't leak URLs to third parties
            self.set_header("Referrer-Policy", "strict-origin-when-cross-origin")

            # Permissions policy — disable unnecessary browser features
            self.set_header(
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=(), payment=()"
            )

            # Cross-Origin headers — enhance isolation
            self.set_header("Cross-Origin-Opener-Policy", "same-origin")
            self.set_header("Cross-Origin-Resource-Policy", "same-origin")

            # X-Robots-Tag — ensure search engines index the site
            self.set_header("X-Robots-Tag", "index, follow")

            # SEC-010: Remove server version info
            self.clear_header("Server")

        RequestHandler.set_default_headers = _secure_set_default_headers
        logger.info("Security headers middleware injected successfully.")
        return True

    except Exception as e:
        logger.error(f"Failed to inject security headers: {e}")
        return False


def get_https_redirect_meta():
    """
    Returns an HTML meta tag that forces HTTPS redirect on the client side.
    Useful as a backup when server-side redirect isn't possible (Railway handles this).

    SEC-001: HTTPS enforcement at the application layer.
    """
    return (
        '<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">'
    )
