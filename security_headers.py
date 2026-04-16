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

            # Cross-Origin headers — enhance isolation while allowing
            # Google Sign-In popup flow (accounts.google.com popup must be
            # able to communicate back to the opener window via callback).
            # "same-origin-allow-popups" keeps isolation for same-origin
            # navigations but lets OAuth popups work correctly.
            self.set_header("Cross-Origin-Opener-Policy", "same-origin-allow-popups")
            self.set_header("Cross-Origin-Resource-Policy", "cross-origin")

            # X-Robots-Tag — ensure search engines index the site
            self.set_header("X-Robots-Tag", "index, follow")

            # ── Cache-Control for static assets ──────────────────────────
            # Long cache for immutable static files (CSS/JS/fonts have hashed
            # filenames in Streamlit).  Short cache for HTML.
            req_path = self.request.path
            if req_path.startswith("/static/") or req_path.endswith((".js", ".css", ".woff2", ".woff", ".ttf", ".png", ".ico", ".svg")):
                self.set_header(
                    "Cache-Control",
                    "public, max-age=31536000, immutable"
                )
            elif req_path in ("/robots.txt", "/sitemap.xml", "/og-image.png"):
                self.set_header("Cache-Control", "public, max-age=86400")

            # SEC-010: Remove server version info
            self.clear_header("Server")

        RequestHandler.set_default_headers = _secure_set_default_headers
        logger.info("Security headers middleware injected successfully.")
        return True

    except Exception as e:
        logger.error(f"Failed to inject security headers: {e}")
        return False


def inject_gzip_compression():
    """
    Enable GZip compression for Tornado responses.

    Monkey-patches Tornado's Application to add GZipContentEncoding transform,
    reducing transfer sizes by 60-80% for text-based content (HTML, CSS, JS).

    PERF-001: Fixes "No GZIP/Brotli compression detected" warning.
    """
    try:
        from tornado.web import Application, GZipContentEncoding

        _original_init = Application.__init__

        def _gzip_init(self, *args, **kwargs):
            _original_init(self, *args, **kwargs)
            # Add GZip transform if not already present
            has_gzip = any(
                t == GZipContentEncoding or
                (isinstance(t, type) and issubclass(t, GZipContentEncoding))
                for t in self.transforms
            )
            if not has_gzip:
                self.transforms.append(GZipContentEncoding)
                logger.info("GZip compression transform added to Tornado.")

        Application.__init__ = _gzip_init
        logger.info("GZip compression injection ready.")
        return True

    except Exception as e:
        logger.error(f"Failed to inject GZip compression: {e}")
        return False


def inject_www_redirect():
    """
    Redirect www.quartercharts.com → quartercharts.com (or vice versa).

    Ensures a single canonical host to avoid duplicate content and satisfy
    uptime monitoring checks.  Railway handles HTTPS, but not www normalization.

    UPTIME-001: Fixes "No www/non-www redirect" warning.
    """
    try:
        from tornado.web import RequestHandler

        _original_prepare = getattr(RequestHandler, '_original_prepare_for_redirect', None)
        if _original_prepare is not None:
            return True  # Already injected

        _base_prepare = RequestHandler.prepare

        def _redirect_prepare(self):
            host = self.request.host.split(":")[0]  # strip port
            if host.startswith("www."):
                # 301 permanent redirect from www → non-www
                target = self.request.full_url().replace(
                    "://www.", "://", 1
                )
                self.redirect(target, permanent=True)
                return
            return _base_prepare(self)

        RequestHandler._original_prepare_for_redirect = _base_prepare
        RequestHandler.prepare = _redirect_prepare
        logger.info("www → non-www redirect middleware injected.")
        return True

    except Exception as e:
        logger.error(f"Failed to inject www redirect: {e}")
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
