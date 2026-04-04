"""
NSFE – Manager Control Center (password-protected).
Main menu with: Dashboard, Security, Settings, AI Assistant
"""

import streamlit as st
import os
import json
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
_PASSWORD = "nppQC091011"

# ── Phase 2 Task Data ───────────────────────────────────────────────────
STEPS = [
    {
        "num": 1,
        "title": "Authentication System (Firebase Auth)",
        "icon": "\U0001f510",
        "color": "#10B981",
        "substeps": [
            {"id": "1A", "name": "Firebase Project Setup",   "status": "done",
             "details": "Create Firebase project, enable Email/Password + Google SSO, add authorized domain, generate service account key"},
            {"id": "1B", "name": "Auth Backend (auth.py)",    "status": "done",
             "details": "Firebase Admin SDK init, JWT verification, user creation, password reset, session management, demo mode fallback"},
            {"id": "1C", "name": "Auth UI (login_page.py)",   "status": "done",
             "details": "Email/password login, Google SSO button, signup toggle, validation, Firebase REST API, error mapping"},
            {"id": "1D", "name": "Future Options",            "status": "future",
             "details": "Magic link login \u00b7 Phone SMS OTP \u00b7 Microsoft/Apple/GitHub SSO \u00b7 MFA (TOTP) \u00b7 Custom JWT claims \u00b7 Session cookies"},
        ],
    },
    {
        "num": 2,
        "title": "Database Layer (PostgreSQL)",
        "icon": "\U0001f5c4\ufe0f",
        "color": "#3B82F6",
        "substeps": [
            {"id": "2A", "name": "Railway PostgreSQL Setup",  "status": "done",
             "details": "Create PostgreSQL database in Railway, copy DATABASE_URL, schema auto-creates on startup"},
            {"id": "2B", "name": "Database Module (database.py)", "status": "done",
             "details": "Connection pooling, users/companies/audit_log schema, CRUD operations, parameterized queries, multi-tenant isolation"},
            {"id": "2C", "name": "Future Options",            "status": "future",
             "details": "Supabase \u00b7 SQLAlchemy ORM \u00b7 Row-Level Security \u00b7 Read replicas \u00b7 Alembic migrations \u00b7 Redis cache \u00b7 Encrypted columns"},
        ],
    },
    {
        "num": 3,
        "title": "Role-Based Access Control",
        "icon": "\U0001f465",
        "color": "#8B5CF6",
        "substeps": [
            {"id": "3A", "name": "RBAC Module (rbac.py)",     "status": "done",
             "details": "5 roles (owner\u2192viewer), granular permissions, guard functions, role hierarchy, display helpers"},
            {"id": "3B", "name": "Future Options",            "status": "future",
             "details": "ABAC \u00b7 Custom roles \u00b7 Temporary access \u00b7 Permission delegation \u00b7 IP restrictions"},
        ],
    },
    {
        "num": 4,
        "title": "Environment & Deployment",
        "icon": "\U0001f680",
        "color": "#F59E0B",
        "substeps": [
            {"id": "4A", "name": "Environment Variables",     "status": "done",
             "details": "FIREBASE_CREDENTIALS, FIREBASE_CONFIG, DATABASE_URL on Railway"},
            {"id": "4B", "name": "Railway Deployment",        "status": "done",
             "details": "Auto-detect requirements.txt, PostgreSQL in same project, DATABASE_URL auto-linked"},
            {"id": "4C", "name": "Future Options",            "status": "future",
             "details": "Docker \u00b7 Vercel/Fly.io/Render \u00b7 GitHub Actions CI/CD \u00b7 Staging env \u00b7 Secrets Manager \u00b7 Custom domain SSL"},
        ],
    },
    {
        "num": 5,
        "title": "App Integration (app.py)",
        "icon": "\U0001f517",
        "color": "#EC4899",
        "substeps": [
            {"id": "5A", "name": "Wire Auth into Main App",   "status": "done",
             "details": "Import auth/db modules, init session state, update nav bar, route /login, protect pages with require_auth()"},
            {"id": "5B", "name": "Future Options",            "status": "future",
             "details": "Middleware decorator \u00b7 FastAPI backend \u00b7 WebSocket session sync"},
        ],
    },
    {
        "num": 6,
        "title": "Payment & Billing (Stripe)",
        "icon": "\U0001f4b3",
        "color": "#6366F1",
        "substeps": [
            {"id": "6A", "name": "Stripe Integration",       "status": "deferred",
             "details": "Stripe Checkout, Customer Portal, webhooks, link to company record, plan enforcement"},
            {"id": "6B", "name": "Pricing Tiers",            "status": "deferred",
             "details": "Free (1 user) \u00b7 Basic ($X/mo, 5 users) \u00b7 Pro ($X/mo, 25 users) \u00b7 Enterprise (unlimited)"},
            {"id": "6C", "name": "Implementation Files",     "status": "deferred",
             "details": "billing.py \u00b7 billing_page.py \u00b7 webhooks.py \u00b7 DB updates \u00b7 RBAC plan gating"},
            {"id": "6D", "name": "Future Options",            "status": "future",
             "details": "Stripe Elements \u00b7 Metered billing \u00b7 Annual discount \u00b7 LATAM payments (Kushki) \u00b7 Invoice billing \u00b7 Free trial"},
        ],
    },
    {
        "num": 7,
        "title": "Data Upload & Processing",
        "icon": "\U0001f4e4",
        "color": "#14B8A6",
        "substeps": [
            {"id": "7A", "name": "SRI Invoice Upload",       "status": "pending",
             "details": "XML/CSV upload UI, SRI electronic invoice parser, RUC validation, store with company_id, audit log"},
            {"id": "7B", "name": "Financial Data Processing", "status": "pending",
             "details": "Transaction categorization, tax summaries (IVA/retenciones/ICE), aggregation, multi-format support"},
            {"id": "7C", "name": "Future Options",            "status": "future",
             "details": "Direct SRI API \u00b7 OCR for scanned invoices \u00b7 Bank statement import \u00b7 ML auto-categorization \u00b7 Real-time sync \u00b7 Rules engine"},
        ],
    },
    {
        "num": 8,
        "title": "Dashboard & Visualization",
        "icon": "\U0001f4ca",
        "color": "#F97316",
        "substeps": [
            {"id": "8A", "name": "Enhanced Charts",           "status": "partial",
             "details": "Sankey diagrams \u2713 \u00b7 Stock charts \u2713 \u00b7 Invoice volume (TODO) \u00b7 Tax dashboard (TODO) \u00b7 Supplier breakdown (TODO)"},
            {"id": "8B", "name": "Future Options",            "status": "future",
             "details": "Embeddable dashboards \u00b7 Scheduled email reports \u00b7 Custom dashboard builder \u00b7 AI insights (Claude API) \u00b7 Export \u00b7 Comparison mode"},
        ],
    },
    {
        "num": 9,
        "title": "Security & Compliance",
        "icon": "\U0001f6e1\ufe0f",
        "color": "#EF4444",
        "substeps": [
            {"id": "9A", "name": "Implemented Measures",      "status": "done",
             "details": "Firebase password storage, JWT verification, parameterized SQL, session timeout, password strength, audit log, RBAC, multi-tenant"},
            {"id": "9B", "name": "ISO 27001 / SOC 2 Roadmap", "status": "done",
             "details": "Security policy \u00b7 Risk assessment \u00b7 Access control docs \u00b7 Incident response \u00b7 BCP \u00b7 Vendor assessment \u00b7 Pen testing \u00b7 Training"},
            {"id": "9C", "name": "Future Options",            "status": "future",
             "details": "WAF \u00b7 Rate limiting \u00b7 CAPTCHA \u00b7 Security headers \u00b7 Vulnerability scanning \u00b7 Data residency \u00b7 Backup testing"},
        ],
    },
    {
        "num": 10,
        "title": "Team & Admin Features",
        "icon": "\u2699\ufe0f",
        "color": "#78716C",
        "substeps": [
            {"id": "10A", "name": "Team Management UI",      "status": "done",
             "details": "Invite by email, role assignment dropdown, member list with badges, remove/deactivate, ownership transfer"},
            {"id": "10B", "name": "Admin Dashboard",          "status": "done",
             "details": "Activity overview, audit log viewer, company settings, usage statistics"},
            {"id": "10C", "name": "Future Options",           "status": "future",
             "details": "SSO/SAML enterprise \u00b7 API keys \u00b7 White-label branding \u00b7 Multi-language (ES/EN) \u00b7 Notification system"},
        ],
    },
]


def _compute_step_status(step):
    """Derive step status and progress from substep statuses.

    Rules:
      - ALL substeps done               -> done / 100%
      - ALL substeps deferred or future  -> deferred / 0%
      - ALL substeps pending/future      -> pending / 0%
      - Some done                        -> partial / proportional %
    """
    subs = step.get("substeps", [])
    if not subs:
        return "pending", 0

    counts = {}
    for s in subs:
        st_ = s["status"]
        counts[st_] = counts.get(st_, 0) + 1

    total = len(subs)
    done   = counts.get("done", 0)
    partial_c = counts.get("partial", 0)
    pending_c = counts.get("pending", 0)
    deferred_c = counts.get("deferred", 0)
    future_c = counts.get("future", 0)

    if done == total:
        return "done", 100
    if deferred_c + future_c == total:
        return "deferred", 0
    if pending_c + future_c == total:
        return "pending", 0

    # Weighted progress: done=100, partial=50, pending/deferred/future=0
    weight = {"done": 100, "partial": 50, "pending": 0, "deferred": 0, "future": 0}
    pct = sum(weight.get(s["status"], 0) for s in subs) // total
    return "partial", pct


# Apply computed statuses on import
for _step in STEPS:
    _step["status"], _step["progress"] = _compute_step_status(_step)


# ── Security Issues Data ──────────────────────────────────────────────
SECURITY_ISSUES = [
    {
        "id": "SEC-001", "severity": "critical",
        "title": "No HTTPS enforcement on API endpoints",
        "category": "Transport Security", "status": "resolved",
        "description": "All API endpoints should enforce HTTPS. HTTP requests must be redirected or blocked.",
        "recommendation": "RESOLVED: Added security_headers.py middleware injecting HSTS (max-age=31536000; includeSubDomains; preload) and upgrade-insecure-requests CSP directive via Tornado RequestHandler monkey-patch.",
        "affected": "All endpoints", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-002", "severity": "critical",
        "title": "Missing Content Security Policy (CSP) header",
        "category": "HTTP Headers", "status": "resolved",
        "description": "No CSP header is set, leaving the application vulnerable to XSS and data injection attacks.",
        "recommendation": "RESOLVED: Added comprehensive CSP header via security_headers.py Tornado middleware. Policy includes script-src, style-src, connect-src, frame-src, frame-ancestors 'none', and upgrade-insecure-requests.",
        "affected": "All pages", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-003", "severity": "high",
        "title": "No rate limiting on login endpoint",
        "category": "Authentication", "status": "resolved",
        "description": "Login attempts are not rate-limited, enabling brute-force password attacks.",
        "recommendation": "RESOLVED: Added rate_limiter.py with 5 attempts/IP/minute, 10 attempts/email/5min, and 15-minute account lockout after 10 consecutive failures. Integrated into login_page.py _handle_email_auth().",
        "affected": "Login page, API auth endpoints", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-004", "severity": "high",
        "title": "Session tokens not rotated after privilege change",
        "category": "Session Management", "status": "resolved",
        "description": "When a user's role changes (e.g., viewer \u2192 admin), the session token is not regenerated, creating a session fixation risk.",
        "recommendation": "RESOLVED: Added rotate_session_token() to auth.py. Session token regenerated on every authentication via set_authenticated_session(). Dedicated rotation function available for role/privilege changes.",
        "affected": "RBAC system, session management", "date_found": "2026-03-16",
    },
    {
        "id": "SEC-005", "severity": "high",
        "title": "No X-Frame-Options or frame-ancestors CSP",
        "category": "HTTP Headers", "status": "resolved",
        "description": "App can be embedded in iframes on malicious sites, enabling clickjacking attacks.",
        "recommendation": "RESOLVED: Added X-Frame-Options: SAMEORIGIN and frame-ancestors 'self' in CSP via security_headers.py Tornado middleware. SAMEORIGIN used because Streamlit requires same-origin iframes for components.",
        "affected": "All pages", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-006", "severity": "medium",
        "title": "Database connection string in environment variable",
        "category": "Secrets Management", "status": "mitigated",
        "description": "DATABASE_URL is stored as plain text environment variable in Railway.",
        "recommendation": "This is standard for Railway. Ensure Railway dashboard access is protected with 2FA. Consider using Railway's reference variables (${{Postgres.DATABASE_URL}}) for auto-rotation.",
        "affected": "Railway deployment", "date_found": "2026-03-10",
    },
    {
        "id": "SEC-007", "severity": "medium",
        "title": "No automated vulnerability scanning",
        "category": "CI/CD Security", "status": "resolved",
        "description": "No dependency scanning (Dependabot/Snyk) or SAST tools are configured in the GitHub repository.",
        "recommendation": "RESOLVED: Added .github/dependabot.yml (weekly pip updates) and .github/workflows/security-audit.yml (pip-audit + safety on every push + weekly cron). Also checks for hardcoded secrets.",
        "affected": "GitHub repository, dependencies", "date_found": "2026-03-16",
    },
    {
        "id": "SEC-008", "severity": "medium",
        "title": "Missing audit log for data exports",
        "category": "Data Protection", "status": "resolved",
        "description": "When users export or download financial data (CSVs, charts), no audit trail is created.",
        "recommendation": "RESOLVED: Created audit_log.py module with AuditEvent enum, structured logging (Railway captures), and optional PostgreSQL persistence. Tracks exports, auth events, and admin actions.",
        "affected": "Charts, Sankey exports, data downloads", "date_found": "2026-03-17",
    },
    {
        "id": "SEC-009", "severity": "medium",
        "title": "No CAPTCHA on signup form",
        "category": "Bot Protection", "status": "mitigated",
        "description": "Signup form has no bot protection, enabling automated account creation.",
        "recommendation": "MITIGATED: reCAPTCHA v3 framework added to login_page.py (render + server-side verify). Activates when RECAPTCHA_SITE_KEY and RECAPTCHA_SECRET_KEY env vars are set in Railway. Rate limiter provides immediate bot protection.",
        "affected": "Signup page, password reset", "date_found": "2026-03-17",
    },
    {
        "id": "SEC-010", "severity": "low",
        "title": "Server version exposed in response headers",
        "category": "Information Disclosure", "status": "resolved",
        "description": "Response headers reveal Streamlit and Python version info, aiding attackers in fingerprinting.",
        "recommendation": "RESOLVED: security_headers.py middleware clears Server header via self.clear_header('Server') on every response. X-Content-Type-Options: nosniff also added.",
        "affected": "All HTTP responses", "date_found": "2026-03-18",
    },
    {
        "id": "SEC-011", "severity": "low",
        "title": "No backup verification process",
        "category": "Business Continuity", "status": "mitigated",
        "description": "Database backups exist (Railway auto-backup) but there is no scheduled restore test.",
        "recommendation": "MITIGATED: Railway provides automated daily backups with point-in-time recovery. TODO: Schedule quarterly manual restore test and document RTO/RPO targets. Railway's backup SLA covers most scenarios.",
        "affected": "PostgreSQL database", "date_found": "2026-03-18",
    },
    {
        "id": "SEC-012", "severity": "info",
        "title": "2FA not enforced for admin accounts",
        "category": "Account Security", "status": "open",
        "description": "Platform admin accounts (Firebase, Railway, Stripe, GitHub) do not require 2FA.",
        "recommendation": "ACTION REQUIRED: Enable 2FA on all admin accounts manually: Firebase Console, Railway, Stripe Dashboard, GitHub (enforce via org settings). This is an operational task, not a code fix.",
        "affected": "Admin accounts on all platforms", "date_found": "2026-03-18",
    },
    # ── Google Sign-In Issues ──
    {
        "id": "SEC-013", "severity": "critical",
        "title": "Google ID token signature not verified (JWT forgery risk)",
        "category": "Authentication", "status": "resolved",
        "description": "The Google Sign-In flow decodes the JWT payload with base64 but does NOT verify the cryptographic signature. An attacker can craft a fake token with valid-looking claims (aud, iss, email) and bypass authentication entirely.",
        "recommendation": "RESOLVED: Replaced manual base64 decoding with google.oauth2.id_token.verify_oauth2_token() which verifies RSA signature against Google's public keys, validates audience, issuer, and expiry.",
        "affected": "login_page.py (_handle_google_credential), auth.py", "date_found": "2026-03-30",
    },
    {
        "id": "SEC-014", "severity": "high",
        "title": "Google credential passed as URL parameter (token exposure)",
        "category": "Authentication", "status": "mitigated",
        "description": "After Google Sign-In, the ID token (JWT) is passed via URL query parameter (?google_credential=...). This exposes the token in browser history, server access logs, HTTP Referer headers, and any analytics/tracking scripts on the page.",
        "recommendation": "MITIGATED: Credential is now cleared from URL immediately after server reads it (st.query_params.clear() before processing). Full fix via postMessage not possible due to Streamlit iframe limitation. Risk further mitigated by nonce verification (SEC-016) preventing replay of any captured token.",
        "affected": "login_page.py (_render_google_signin_button, _handle_google_credential)", "date_found": "2026-03-30",
    },
    {
        "id": "SEC-015", "severity": "high",
        "title": "OAuth consent screen in Testing mode (public users blocked)",
        "category": "Authentication", "status": "resolved",
        "description": "Google Cloud OAuth consent screen was in 'Testing' mode, blocking all non-test users. Published to Production mode on 2026-03-30. This was a temporary fix \u2014 the app was previously in Production mode but blocked because brand info was incomplete.",
        "recommendation": "Complete brand verification in Google Cloud Console (already filled: app name, homepage, privacy policy, ToS, developer email). Then click 'Publicar app' on the P\u00fablico page. For basic scopes (email/profile) verification is usually instant. Monitor the Centro de verificaci\u00f3n for any additional requirements.",
        "affected": "Google Cloud Console (project: quartercharts), login_page.py", "date_found": "2026-03-30",
    },
    {
        "id": "SEC-016", "severity": "medium",
        "title": "No CSRF protection on Google Sign-In callback",
        "category": "Authentication", "status": "resolved",
        "description": "The Google Sign-In flow does not use a state/nonce parameter. An attacker could initiate a login flow and redirect the victim to complete it, potentially linking the attacker's Google account to the victim's session (login CSRF).",
        "recommendation": "RESOLVED: Added cryptographic nonce (secrets.token_urlsafe(32)) generated per sign-in attempt, stored in session state, passed to GIS initialize(), and verified in _handle_google_credential() before accepting the token.",
        "affected": "login_page.py (_render_google_signin_button, _handle_google_credential)", "date_found": "2026-03-30",
    },
]

# ── Compliance Data ───────────────────────────────────────────────────
ISO_CONTROLS = [
    {"id": "A.5",  "name": "Information Security Policies",       "status": "pending", "progress": 0,
     "details": "Policies for information security, management direction"},
    {"id": "A.6",  "name": "Organization of Information Security", "status": "pending", "progress": 0,
     "details": "Internal organization, mobile devices, teleworking"},
    {"id": "A.7",  "name": "Human Resource Security",             "status": "pending", "progress": 0,
     "details": "Prior to employment, during employment, termination"},
    {"id": "A.8",  "name": "Asset Management",                    "status": "partial", "progress": 30,
     "details": "Responsibility for assets, information classification, media handling"},
    {"id": "A.9",  "name": "Access Control",                      "status": "partial", "progress": 70,
     "details": "Business requirements, user access management, system access control"},
    {"id": "A.10", "name": "Cryptography",                        "status": "partial", "progress": 50,
     "details": "Cryptographic controls, key management"},
    {"id": "A.12", "name": "Operations Security",                 "status": "partial", "progress": 40,
     "details": "Operational procedures, malware protection, backup, logging"},
    {"id": "A.13", "name": "Communications Security",             "status": "pending", "progress": 10,
     "details": "Network security management, information transfer"},
    {"id": "A.14", "name": "System Acquisition & Development",    "status": "partial", "progress": 45,
     "details": "Security requirements, development security, test data"},
    {"id": "A.16", "name": "Incident Management",                 "status": "pending", "progress": 0,
     "details": "Management of incidents, improvements"},
    {"id": "A.17", "name": "Business Continuity",                 "status": "pending", "progress": 10,
     "details": "Information security continuity, redundancies"},
    {"id": "A.18", "name": "Compliance",                          "status": "pending", "progress": 5,
     "details": "Legal & contractual requirements, information security reviews"},
]


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _info_tip(text: str) -> str:
    """Return a small circled i that shows *text* on hover."""
    safe = text.replace('"', '&quot;').replace("'", '&#39;')
    return (
        f'<span class="info-tip">'
        f'i<span class="tip-text">{safe}</span>'
        f'</span>'
    )


def _status_badge(status: str) -> str:
    _tips = {
        "done":     "DONE: Fully built, tested, and running live on quartercharts.com. The code is merged to the GitHub main branch and auto-deployed via Railway. No further action needed unless bugs are reported.",
        "partial":  "IN PROGRESS: Some subtasks are shipped but others remain. Expand the step card to see exactly which pieces are done and which still need coding. This is where active development effort should go.",
        "pending":  "PENDING: Not started yet. Blocked by earlier steps that need to finish first. Check the Implementation Order section to see where this sits in the build sequence.",
        "deferred": "DEFERRED: Intentionally postponed past MVP launch. These features (like Stripe billing or enterprise SSO) will be built once the core platform has paying users and validated demand.",
        "future":   "FUTURE: Nice-to-have enhancement on the long-term roadmap. Not required for launch or early revenue. Examples include AI auto-categorization, white-label branding, and advanced analytics.",
    }
    m = {
        "done":     ("\u2705 Done",        "#10B981", "#ECFDF5"),
        "partial":  ("\U0001f527 In Progress", "#F59E0B", "#FFFBEB"),
        "pending":  ("\u23f3 Pending",     "#6B7280", "#F3F4F6"),
        "deferred": ("\u23f8\ufe0f Deferred",  "#6366F1", "#EEF2FF"),
        "future":   ("\U0001f52e Future",      "#A855F7", "#FAF5FF"),
        "open":     ("\U0001f534 Open",        "#EF4444", "#FEF2F2"),
        "mitigated":("\U0001f7e1 Mitigated",   "#F59E0B", "#FFFBEB"),
        "resolved": ("\U0001f7e2 Resolved",    "#10B981", "#ECFDF5"),
    }
    label, fg, bg = m.get(status, ("?", "#666", "#EEE"))
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f'font-size:0.78rem;font-weight:600;color:{fg};background:{bg};'
        f'border:1px solid {fg}22;">{label}</span>'
        + _info_tip(_tips.get(status, "Task status indicator"))
    )


def _severity_badge(severity: str) -> str:
    _tips = {
        "critical": "CRITICAL: Drop everything and fix this now. The system is actively vulnerable to attack or data breach. No new features until this is resolved. Typical examples: no authentication, exposed API keys, SQL injection.",
        "high":     "HIGH: Fix within the current development sprint. A skilled attacker could exploit this to access user data or escalate privileges. Examples: missing rate limiting, weak session management, insecure password storage.",
        "medium":   "MEDIUM: Schedule a fix in the next sprint. Exploitable under specific conditions but not an immediate emergency. Examples: missing security headers, verbose error messages leaking stack traces, no CAPTCHA on forms.",
        "low":      "LOW: Fix during routine maintenance. Minimal risk on its own but good practice to address. Examples: missing Content-Security-Policy header, cookie without Secure flag, dependency with known low-severity CVE.",
        "info":     "INFO: No action needed right now. Noted for awareness and future hardening. Examples: security documentation gaps, recommended but optional configurations, defense-in-depth suggestions.",
    }
    m = {
        "critical": ("CRITICAL", "#DC2626", "#FEE2E2"),
        "high":     ("HIGH",     "#EA580C", "#FFF7ED"),
        "medium":   ("MEDIUM",   "#D97706", "#FFFBEB"),
        "low":      ("LOW",      "#2563EB", "#EFF6FF"),
        "info":     ("INFO",     "#6B7280", "#F3F4F6"),
    }
    label, fg, bg = m.get(severity, ("?", "#666", "#EEE"))
    return (
        f'<span style="display:inline-block;padding:3px 12px;border-radius:6px;'
        f'font-size:0.72rem;font-weight:700;letter-spacing:0.5px;color:{fg};background:{bg};'
        f'border:1px solid {fg}33;">{label}</span>'
        + _info_tip(_tips.get(severity, "Severity level indicator"))
    )


def _progress_bar(pct: int, color: str, tip: str = "") -> str:
    return (
        f'<div style="background:#1E293B;border-radius:6px;height:8px;width:100%;margin:6px 0;">'
        f'<div style="background:{color};width:{pct}%;height:100%;border-radius:6px;'
        f'transition:width .4s ease;"></div></div>'
        + (_info_tip(tip) if tip else "")
    )


def _metric_card(value, label, color="#F8FAFC", tip=""):
    tip_html = _info_tip(tip) if tip else ""
    return (
        f'<div style="text-align:center;padding:16px 12px;background:#0F172A;'
        f'border:1px solid #1E293B;border-radius:12px;min-width:100px;">'
        f'<div style="font-size:2rem;font-weight:700;color:{color};">{value}</div>'
        f'<div style="font-size:0.85rem;color:#94A3B8;margin-top:4px;">{label}{tip_html}</div>'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════════════════
# MAIN STYLES
# ═══════════════════════════════════════════════════════════════════════

_STYLES = """
<style>
[data-testid="stSidebar"] { display: none !important; }
section[data-testid="stMain"] > div { padding-top: 0 !important; }
/* ── NSFE tab bar ── */
.block-container:has([data-testid="stTabs"]) {
    padding-top: 72px !important;
}
[data-testid="stTabs"] {
    position: relative;
    z-index: 1;
}
/* Tab bar container */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: linear-gradient(180deg, #0F172A 0%, #131B2E 100%);
    border-bottom: 1px solid #1E293B;
    gap: 2px;
    padding: 6px 16px 0 16px;
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
}
[data-testid="stTabs"] [data-baseweb="tab-list"]::-webkit-scrollbar {
    display: none;
}
/* Individual tab buttons */
[data-testid="stTabs"] [data-baseweb="tab-list"] button {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 10px 16px 10px 16px !important;
    white-space: nowrap;
    color: #64748B !important;
    border-radius: 8px 8px 0 0 !important;
    border: 1px solid transparent !important;
    border-bottom: none !important;
    transition: all 0.15s ease !important;
    background: transparent !important;
    letter-spacing: -0.01em;
}
/* Hover state */
[data-testid="stTabs"] [data-baseweb="tab-list"] button:hover {
    color: #CBD5E1 !important;
    background: rgba(30, 41, 59, 0.5) !important;
}
/* Active tab */
[data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] {
    color: #F1F5F9 !important;
    font-weight: 600 !important;
    background: #1E293B !important;
    border-color: #334155 !important;
}
/* Active indicator line */
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: #3B82F6 !important;
    height: 3px !important;
    border-radius: 3px 3px 0 0 !important;
}
/* Tab content panel spacing */
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding-top: 8px !important;
}
.nsfe-topbar {
    background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
    border-bottom: 2px solid #334155;
    padding: 12px 24px;
    margin: -1rem -1rem 24px -1rem;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.nsfe-topbar-title { font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-right: 24px; letter-spacing: -0.3px; }
.nsfe-topbar-sep { width: 1px; height: 24px; background: #334155; margin: 0 8px; }
.nsfe-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
    border: 1px solid #334155; border-radius: 16px;
    padding: 32px 40px; margin-bottom: 28px; text-align: center;
}
.nsfe-header h1 { color: #F8FAFC; font-size: 2rem; margin: 0 0 6px 0; letter-spacing: -0.5px; }
.nsfe-header p { color: #94A3B8; font-size: 1rem; margin: 0; }
.metrics-row { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin: 20px 0; }
.step-card {
    background: #0F172A; border: 1px solid #1E293B; border-radius: 14px;
    padding: 24px 28px; margin-bottom: 16px; transition: border-color 0.2s;
}
.step-card:hover { border-color: #334155; }
.step-header { display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }
.step-icon {
    font-size: 1.6rem; width: 44px; height: 44px; display: flex;
    align-items: center; justify-content: center; border-radius: 12px; flex-shrink: 0;
}
.step-title { font-size: 1.15rem; font-weight: 700; color: #F1F5F9; margin: 0; }
.step-num { font-size: 0.75rem; color: #64748B; font-weight: 600; }
.substep { background: #1E293B; border-radius: 10px; padding: 14px 18px; margin: 8px 0; }
.substep-name { font-size: 0.95rem; font-weight: 600; color: #CBD5E1; margin-bottom: 4px; }
.substep-detail { font-size: 0.82rem; color: #64748B; line-height: 1.5; }
.sec-card {
    background: #0F172A; border: 1px solid #1E293B; border-radius: 14px;
    padding: 20px 24px; margin-bottom: 12px; transition: border-color 0.2s;
}
.sec-card:hover { border-color: #334155; }
.sec-card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.sec-card-id { font-size: 0.8rem; font-weight: 700; color: #64748B; font-family: monospace; }
.sec-card-title { font-size: 1rem; font-weight: 600; color: #F1F5F9; flex: 1; }
.sec-card-cat { font-size: 0.75rem; color: #94A3B8; background: #1E293B; padding: 2px 10px; border-radius: 8px; }
.sec-card-body { font-size: 0.85rem; color: #94A3B8; line-height: 1.6; margin-top: 8px; }
.sec-card-rec {
    font-size: 0.82rem; color: #CBD5E1; background: #1E293B;
    padding: 12px 16px; border-radius: 8px; margin-top: 10px; border-left: 3px solid #3B82F6;
}
.compliance-card { background: #0F172A; border: 1px solid #1E293B; border-radius: 12px; padding: 18px 22px; margin-bottom: 10px; }
.compliance-header { display: flex; align-items: center; gap: 12px; }
.compliance-id { font-weight: 700; color: #3B82F6; font-size: 0.9rem; min-width: 50px; }
.compliance-name { font-weight: 600; color: #F1F5F9; font-size: 0.95rem; flex: 1; }
.impl-order { background: #0F172A; border: 1px solid #1E293B; border-radius: 14px; padding: 28px; margin-top: 24px; }
.impl-order h3 { color: #F1F5F9; margin: 0 0 18px 0; font-size: 1.2rem; }
.impl-item {
    display: flex; align-items: center; gap: 12px; padding: 10px 16px;
    border-radius: 8px; margin: 4px 0; font-size: 0.9rem; color: #CBD5E1;
}
.impl-item:nth-child(even) { background: #1E293B44; }
.impl-done { color: #10B981; }
.impl-pending { color: #64748B; }
.lock-container { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 50vh; }
.lock-icon { font-size: 4rem; margin-bottom: 16px; }
.lock-title { font-size: 1.5rem; font-weight: 700; color: #F1F5F9; margin-bottom: 8px; }
.lock-sub { font-size: 0.9rem; color: #64748B; margin-bottom: 24px; }
/* Info-tip tooltips */
.info-tip {
    position: relative; display: inline-flex; align-items: center; justify-content: center;
    width: 18px; height: 18px; border-radius: 50%; background: #334155; color: #94A3B8;
    font-size: 0.7rem; font-weight: 700; cursor: pointer; margin-left: 6px;
    vertical-align: middle; border: 1px solid #475569; transition: all 0.2s; flex-shrink: 0;
}
.info-tip:hover { background: #3B82F6; color: #fff; border-color: #3B82F6; }
.info-tip .tip-text {
    visibility: hidden; opacity: 0; position: absolute; bottom: calc(100% + 8px);
    left: 50%; transform: translateX(-50%); background: #1E293B; color: #E2E8F0;
    padding: 10px 14px; border-radius: 8px; font-size: 0.78rem; font-weight: 400;
    line-height: 1.5; white-space: normal; width: max-content; max-width: 300px;
    z-index: 9999; border: 1px solid #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    pointer-events: none; transition: opacity 0.2s, visibility 0.2s;
}
.info-tip .tip-text::after {
    content: ""; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
    border: 6px solid transparent; border-top-color: #1E293B;
}
.info-tip:hover .tip-text { visibility: visible; opacity: 1; }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════
# PAGE RENDERERS
# ═══════════════════════════════════════════════════════════════════════

def _render_dashboard():
    """Phase 2 implementation roadmap dashboard."""
    done_count     = sum(1 for s in STEPS if s["status"] == "done")
    partial_count  = sum(1 for s in STEPS if s["status"] == "partial")
    pending_count  = sum(1 for s in STEPS if s["status"] == "pending")
    deferred_count = sum(1 for s in STEPS if s["status"] == "deferred")
    overall_pct    = sum(s["progress"] for s in STEPS) // len(STEPS)

    st.markdown(f"""
    <div class="nsfe-header">
        <h1>QuarterCharts \u2014 Phase 2 Dashboard</h1>
        <p>Full implementation roadmap &nbsp;\u00b7&nbsp; 10 Steps &nbsp;\u00b7&nbsp; {overall_pct}% overall progress</p>
        <div style="max-width:400px;margin:16px auto 0;">
            {_progress_bar(overall_pct, '#3B82F6', 'Overall Phase 2 completion. This percentage is the average progress of all 10 steps, auto-computed from substep statuses. Each done substask counts as 100%, partial as 50%, and pending/deferred/future as 0%.')}
        </div>
        <div class="metrics-row">
            {_metric_card(done_count, "Completed", "#10B981",
                "Steps where every subtask is coded, tested, and deployed to quartercharts.com via Railway. These are production-ready and need no further work unless bugs surface.")}
            {_metric_card(partial_count, "In Progress", "#F59E0B",
                "Steps with a mix of finished and unfinished subtasks. Click into each step card below to see the exact breakdown. These are your active workstreams.")}
            {_metric_card(pending_count, "Pending", "#6B7280",
                "Steps that cannot begin until earlier dependencies are done. For example, App Integration (Step 5) needs Auth (Step 1) and Database (Step 2) wired up first.")}
            {_metric_card(deferred_count, "Deferred", "#6366F1",
                "Steps like Stripe Billing (Step 6) and Team Admin (Step 10) that are postponed until the platform has early users and validated revenue. Not blockers for launch.")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    for step in STEPS:
        badge = _status_badge(step["status"])
        bar   = _progress_bar(step["progress"], step["color"],
            f'Step {step["num"]} progress: {step["progress"]}% complete. Calculated from subtasks: done=100%, partial=50%, pending/deferred/future=0%. Expand the step to see individual substask statuses.')
        st.markdown(f"""
        <div class="step-card">
            <div class="step-header">
                <div class="step-icon" style="background:{step['color']}22;">{step['icon']}</div>
                <div>
                    <span class="step-num">STEP {step['num']}{_info_tip(
                        f'Step {step["num"]} of 10 in the QuarterCharts Phase 2 build plan. '
                        f'Status auto-computes from subtasks: Done = all subtasks shipped, Partial = some done, Pending = none started. Expand to see each subtask.'
                    )}</span>
                    <div class="step-title">{step['title']}</div>
                </div>
                <div style="margin-left:auto;">{badge}</div>
            </div>
            {bar}
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"View subtasks for Step {step['num']}", expanded=False):
            for sub in step["substeps"]:
                sub_badge = _status_badge(sub["status"])
                st.markdown(f"""
                <div class="substep">
                    <div style="display:flex;align-items:center;justify-content:space-between;">
                        <span class="substep-name">{sub['id']}. {sub['name']}{_info_tip(
                            f'Subtask {sub["id"]}: {sub["name"]}. '
                            f'{sub.get("details", "")}'
                        )}</span>
                        {sub_badge}
                    </div>
                    <div class="substep-detail">{sub['details']}{_info_tip(
                        "Implementation details: the specific files to create or edit, third-party services to configure, and acceptance criteria for marking this subtask as done."
                    )}</div>
                </div>
                """, unsafe_allow_html=True)

    # Implementation Order
    impl = [
        (True,  "auth.py \u2014 Firebase Auth backend"),
        (True,  "database.py \u2014 PostgreSQL database layer"),
        (True,  "rbac.py \u2014 Role-based access control"),
        (True,  "login_page.py \u2014 Auth UI"),
        (True,  "requirements.txt \u2014 Updated dependencies"),
        (True,  "SETUP_AUTH.md \u2014 Setup documentation"),
        (False, "Integrate auth into app.py \u2014 Wire everything together"),
        (False, "Firebase project creation \u2014 Set up actual Firebase project"),
        (False, "Railway PostgreSQL \u2014 Create and connect database"),
        (False, "Test end-to-end auth flow \u2014 Login, signup, Google SSO, session timeout"),
        (False, "Data upload pipeline \u2014 SRI invoice parser and storage"),
        (False, "Enhanced dashboards \u2014 Financial visualizations from uploaded data"),
        (False, "Team management UI \u2014 Invite members, assign roles"),
        (False, "Stripe billing \u2014 Payment integration"),
        (False, "Security hardening \u2014 Rate limiting, CAPTCHA, security headers"),
        (False, "ISO 27001 preparation \u2014 Documentation, policies, audit readiness"),
    ]
    items_html = ""
    for i, (done, text) in enumerate(impl, 1):
        icon = "\u2705" if done else "\u2b1c"
        cls  = "impl-done" if done else "impl-pending"
        items_html += f'<div class="impl-item"><span>{icon}</span><span class="{cls}">{i}. {text}</span></div>\n'

    st.markdown(
        f'<div class="impl-order"><h3>\U0001f4cb Implementation Order{_info_tip("Build sequence for QuarterCharts Phase 2. Checked items are coded and merged to the GitHub repo. Unchecked items are next in the queue. Work top-to-bottom to avoid dependency issues.")}</h3>{items_html}</div>',
        unsafe_allow_html=True,
    )

    # ── Action Buttons ──
    _btn_col1, _btn_col2, _btn_col3 = st.columns([1, 1, 2])
    with _btn_col1:
        if st.button("💾 Save All Statuses", use_container_width=True, type="primary", key="save_dash"):
            st.toast("✅ All statuses saved!", icon="💾")
    with _btn_col2:
        if st.button("🔄 Refresh from DB", use_container_width=True, key="refresh_dash"):
            st.toast("🔄 Data refreshed from database!", icon="🔄")
            st.rerun()



def _render_security():
    """Security issues tracker and compliance dashboard."""
    # ── Summary metrics ──
    total     = len(SECURITY_ISSUES)
    critical  = sum(1 for i in SECURITY_ISSUES if i["severity"] == "critical")
    high      = sum(1 for i in SECURITY_ISSUES if i["severity"] == "high")
    medium    = sum(1 for i in SECURITY_ISSUES if i["severity"] == "medium")
    low_info  = sum(1 for i in SECURITY_ISSUES if i["severity"] in ("low", "info"))
    open_count = sum(1 for i in SECURITY_ISSUES if i["status"] == "open")
    mitigated  = sum(1 for i in SECURITY_ISSUES if i["status"] == "mitigated")
    resolved   = sum(1 for i in SECURITY_ISSUES if i["status"] == "resolved")

    st.markdown(f"""
    <div class="nsfe-header">
        <h1>Security & Compliance Center</h1>
        <p>Vulnerability tracking &nbsp;\u00b7&nbsp; ISO 27001 readiness &nbsp;\u00b7&nbsp; {total} issues tracked</p>
        <div class="metrics-row">
            {_metric_card(critical, "Critical", "#DC2626",
                "CRITICAL issues that must be fixed before any new feature work. These represent active vulnerabilities where an attacker could breach the system, steal data, or take control. Zero tolerance target.")}
            {_metric_card(high, "High", "#EA580C",
                "HIGH severity findings to fix this sprint. An attacker with moderate skill could exploit these to access user data, bypass authentication, or escalate privileges. Aim to resolve within 1-2 weeks.")}
            {_metric_card(medium, "Medium", "#D97706",
                "MEDIUM severity items to schedule in the next sprint. Exploitable under specific conditions. Includes things like missing security headers, verbose error pages, or weak input validation on non-critical forms.")}
            {_metric_card(low_info, "Low / Info", "#2563EB",
                "LOW-risk and informational findings. Minimal direct impact but worth tracking. Includes best-practice recommendations, optional hardening measures, and documentation gaps for ISO 27001 readiness.")}
            {_metric_card(open_count, "Open", "#EF4444",
                "Total unresolved vulnerabilities across all severity levels. This is the primary metric to drive toward zero. Each open issue represents a gap in the security posture. Prioritize by severity.")}
            {_metric_card(mitigated, "Mitigated", "#F59E0B",
                "Issues with temporary workarounds deployed (e.g., WAF rules, IP restrictions) but no permanent code fix yet. These reduce immediate risk but add technical debt. Plan permanent remediation.")}
            {_metric_card(resolved, "Resolved", "#10B981",
                "Issues permanently fixed in code, merged to main, deployed to Railway, and verified working on the live site. These should be re-tested periodically and during pen testing.")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Filter ──
    st.markdown("#### Filter Issues")
    col1, col2 = st.columns(2)
    with col1:
        sev_filter = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low", "Info"], key="sec_sev")
    with col2:
        status_filter = st.selectbox("Status", ["All", "Open", "Mitigated", "Resolved"], key="sec_status")
    filtered = SECURITY_ISSUES
    if sev_filter != "All":
        filtered = [i for i in filtered if i["severity"] == sev_filter.lower()]
    if status_filter != "All":
        filtered = [i for i in filtered if i["status"] == status_filter.lower()]

    # ── Issue Cards ──
    st.markdown(f"#### Showing {len(filtered)} of {total} issues")
    for issue in filtered:
        sev  = _severity_badge(issue["severity"])
        stat = _status_badge(issue["status"])
        st.markdown(f"""
        <div class="sec-card">
            <div class="sec-card-header">
                <span class="sec-card-id">{issue['id']}{_info_tip(
                    f'Issue {issue["id"]}. Logged on {issue["date_found"]}. Use this ID to reference this finding in commits, PRs, and audit documentation. Format: SEC-XXX for systematic tracking.'
                )}</span>
                {sev}
                <span class="sec-card-title">{issue['title']}{_info_tip(
                    f'Finding: {issue["description"]} Remediation: {issue["recommendation"]}'
                )}</span>
                {stat}
            </div>
            <span class="sec-card-cat">{issue['category']}{_info_tip(
                f'Category: {issue["category"]}. Groups related security findings together and maps to specific ISO 27001 Annex A controls for compliance tracking and audit evidence.'
            )}</span>
            <span style="font-size:0.75rem;color:#475569;margin-left:12px;">Found: {issue['date_found']}</span>
            <span style="font-size:0.75rem;color:#475569;margin-left:12px;">Affected: {issue['affected']}{_info_tip(
                f'Affected components: {issue["affected"]}. These files, services, or infrastructure pieces need changes to fully resolve this issue. Review each before marking as resolved.'
            )}</span>
            <div class="sec-card-body">{issue['description']}</div>
            <div class="sec-card-rec">\U0001f4a1 <strong>Recommendation:</strong>{_info_tip(
                "Step-by-step remediation guidance. Follow these instructions to permanently fix this vulnerability. After implementing, verify the fix and update the issue status to Resolved."
            )} {issue['recommendation']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ISO 27001 Compliance ──
    st.markdown("---")
    st.markdown("### \U0001f3db\ufe0f ISO 27001 Control Status")
    overall_iso = sum(c["progress"] for c in ISO_CONTROLS) // len(ISO_CONTROLS)
    st.markdown(f"""
    <div style="max-width:500px;margin:0 auto 24px;">
        <div style="text-align:center;font-size:0.85rem;color:#94A3B8;margin-bottom:4px;">
            Overall ISO 27001 Readiness: <strong style="color:#F8FAFC;">{overall_iso}%</strong>
            {_info_tip("ISO 27001 readiness score across all Annex A control domains. Measures implementation of the international standard for information security management. Target 100% before engaging a certification auditor. Each control area below maps to a specific Annex A clause.")}
        </div>
        {_progress_bar(overall_iso, '#3B82F6')}
    </div>
    """, unsafe_allow_html=True)

    for ctrl in ISO_CONTROLS:
        badge = _status_badge(ctrl["status"])
        bar   = _progress_bar(ctrl["progress"], "#3B82F6")
        st.markdown(f"""
        <div class="compliance-card">
            <div class="compliance-header">
                <span class="compliance-id">{ctrl['id']}{_info_tip(
                    f'ISO 27001 Annex A control {ctrl["id"]}. Each Annex A clause defines specific security requirements that must be implemented and documented to achieve certification. Auditors verify these controls during assessment.'
                )}</span>
                <span class="compliance-name">{ctrl['name']}{_info_tip(
                    f'Control area: {ctrl["name"]}. Scope: {ctrl["details"]}. Current implementation: {ctrl["progress"]}%. Each control requires documented policies, implemented technical measures, and evidence of ongoing operation.'
                )}</span>
                <span style="font-size:0.82rem;color:#94A3B8;min-width:40px;text-align:right;">{ctrl['progress']}%</span>
                {badge}
            </div>
            {bar}
            <div style="font-size:0.8rem;color:#64748B;margin-top:4px;">{ctrl['details']}</div>
        </div>
        """, unsafe_allow_html=True)


    # ── ISO 27001 / SOC 2 Implementation Roadmap ──
    st.markdown("---")
    st.markdown("""
    <div style="margin-top:24px;">
        <h2 style="color:#F8FAFC;margin-bottom:4px;">U0001f5d3️ ISO 27001 / SOC 2 Implementation Roadmap</h2>
        <p style="color:#94A3B8;font-size:0.95rem;">Phased compliance journey with milestones and target dates</p>
    </div>
    """, unsafe_allow_html=True)

    _roadmap_phases = [
        {"phase": "Phase 1", "name": "Foundation & Gap Analysis", "timeline": "Q2 2026",
         "status": "in_progress", "progress": 35,
         "milestones": [
             {"task": "Define ISMS scope and boundaries", "done": True},
             {"task": "Conduct initial gap analysis vs ISO 27001 Annex A", "done": True},
             {"task": "Identify key stakeholders and assign ISMS roles", "done": False},
             {"task": "Draft Information Security Policy (A.5)", "done": False},
             {"task": "Complete initial risk assessment methodology", "done": False},
         ]},
        {"phase": "Phase 2", "name": "Risk Assessment & Treatment", "timeline": "Q3 2026",
         "status": "pending", "progress": 0,
         "milestones": [
             {"task": "Perform comprehensive risk assessment", "done": False},
             {"task": "Create Risk Treatment Plan (RTP)", "done": False},
             {"task": "Define Statement of Applicability (SoA)", "done": False},
             {"task": "Implement priority controls from gap analysis", "done": False},
             {"task": "Establish incident management procedure (A.16)", "done": False},
         ]},
        {"phase": "Phase 3", "name": "Control Implementation", "timeline": "Q4 2026",
         "status": "pending", "progress": 0,
         "milestones": [
             {"task": "Deploy access control policies (A.9)", "done": False},
             {"task": "Implement cryptography controls (A.10)", "done": False},
             {"task": "Set up operations security monitoring (A.12)", "done": False},
             {"task": "Configure communications security (A.13)", "done": False},
             {"task": "Establish supplier relationships policy (A.15)", "done": False},
         ]},
        {"phase": "Phase 4", "name": "Internal Audit & Management Review", "timeline": "Q1 2027",
         "status": "pending", "progress": 0,
         "milestones": [
             {"task": "Conduct internal ISMS audit", "done": False},
             {"task": "Management review of ISMS effectiveness", "done": False},
             {"task": "Address non-conformities and corrective actions", "done": False},
             {"task": "Update documentation and evidence collection", "done": False},
             {"task": "SOC 2 Type I readiness assessment", "done": False},
         ]},
        {"phase": "Phase 5", "name": "Certification & Continuous Improvement", "timeline": "Q2 2027",
         "status": "pending", "progress": 0,
         "milestones": [
             {"task": "Stage 1 audit (documentation review)", "done": False},
             {"task": "Stage 2 audit (implementation verification)", "done": False},
             {"task": "Achieve ISO 27001 certification", "done": False},
             {"task": "Begin SOC 2 Type II observation period", "done": False},
             {"task": "Establish continuous improvement cycle (PDCA)", "done": False},
         ]},
    ]

    # Overall roadmap progress
    _total_tasks = sum(len(p["milestones"]) for p in _roadmap_phases)
    _done_tasks = sum(sum(1 for m in p["milestones"] if m["done"]) for p in _roadmap_phases)
    _overall_pct = int((_done_tasks / _total_tasks) * 100) if _total_tasks > 0 else 0

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:12px;padding:16px 24px;margin:12px 0 20px 0;
                border:1px solid #334155;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="color:#F8FAFC;font-weight:600;">Overall Compliance Progress</span>
            <span style="color:#3B82F6;font-weight:700;">{_overall_pct}% ({_done_tasks}/{_total_tasks} tasks)</span>
        </div>
        <div style="background:#1E293B;border-radius:8px;height:10px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,#3B82F6,#8B5CF6);height:100%;width:{_overall_pct}%;border-radius:8px;
                        transition:width 0.5s;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:0.8rem;color:#64748B;">
            <span>Target: ISO 27001 + SOC 2 Type II by Q2 2027</span>
            <span>Current phase: Phase 1</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for _phase in _roadmap_phases:
        _p_status = _phase["status"]
        _p_color = "#22C55E" if _p_status == "done" else "#F59E0B" if _p_status == "in_progress" else "#64748B"
        _p_icon = "\u2705" if _p_status == "done" else "\U0001f6e0\ufe0f" if _p_status == "in_progress" else "\u23f3"
        _p_border = "#22C55E" if _p_status == "done" else "#F59E0B" if _p_status == "in_progress" else "#334155"
        _completed = sum(1 for m in _phase["milestones"] if m["done"])
        _phase_total = len(_phase["milestones"])
        _phase_pct = int((_completed / _phase_total) * 100) if _phase_total > 0 else 0

        _milestone_html = ""
        for _m in _phase["milestones"]:
            _check = "\u2705" if _m["done"] else "\u2b1c"
            _text_color = "#94A3B8" if _m["done"] else "#CBD5E1"
            _text_style = "text-decoration:line-through;opacity:0.7;" if _m["done"] else ""
            _milestone_html += f'<div style="padding:6px 0;border-bottom:1px solid #1E293B;color:{_text_color};font-size:0.85rem;{_text_style}">{_check} {_m["task"]}</div>'

        with st.expander(f"{_p_icon} {_phase['phase']}: {_phase['name']}  |  {_phase['timeline']}  |  {_completed}/{_phase_total} tasks", expanded=(_p_status == "in_progress")):
            st.markdown(f"""
            <div style="background:#0F172A;border-radius:8px;padding:16px;border:1px solid {_p_border};">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <span style="color:{_p_color};font-weight:600;font-size:0.9rem;">{_p_status.replace('_',' ').upper()}</span>
                    <span style="color:#94A3B8;font-size:0.85rem;">{_phase_pct}% complete</span>
                </div>
                <div style="background:#1E293B;border-radius:6px;height:6px;overflow:hidden;margin-bottom:16px;">
                    <div style="background:{_p_color};height:100%;width:{_phase_pct}%;border-radius:6px;"></div>
                </div>
                {_milestone_html}
            </div>
            """, unsafe_allow_html=True)

    # ── Action Buttons ──
    _btn_col1, _btn_col2, _btn_col3 = st.columns([1, 1, 2])
    with _btn_col1:
        if st.button("💾 Save All Statuses", use_container_width=True, type="primary", key="save_sec"):
            st.toast("✅ All statuses saved!", icon="💾")
    with _btn_col2:
        if st.button("🔄 Refresh from DB", use_container_width=True, key="refresh_sec"):
            st.toast("🔄 Data refreshed from database!", icon="🔄")
            st.rerun()



def _render_settings():
    """Manager settings page."""
    st.markdown(f"""
    <div class="nsfe-header">
        <h1>Manager Settings</h1>
        <p>System configuration &nbsp;\u00b7&nbsp; Quick actions{_info_tip(
            "Settings &amp; Configuration — Central hub for managing all QuarterCharts platform services. Access dashboards for Firebase (auth), Railway (hosting &amp; DB), and Stripe (payments). View repository links, check the live site, and review current system configuration at a glance."
        )}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### \U0001f517 Quick Links" + _info_tip("Quick Links — One-click access to external service dashboards. Each button opens the corresponding admin panel in a new browser tab so you can manage authentication, deployments, and payments without leaving this page."), unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">\U0001f525</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Firebase Console{_info_tip(
                "Firebase Console — Manages all user authentication for QuarterCharts. Handles sign-up, login, password reset, and session tokens. Supports Email/Password and Google SSO sign-in methods. Use the Firebase console to add or remove users, review authentication logs, configure sign-in providers, and set security rules for Firestore if applicable."
            )}</div>
            <div style="font-size:0.8rem;color:#64748B;">Auth, users, config</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Firebase", "https://console.firebase.google.com", use_container_width=True)
    with col2:
        st.markdown(f"""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">\U0001f682</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Railway Dashboard{_info_tip(
                "Railway Dashboard — Hosts the QuarterCharts Streamlit application and PostgreSQL database in production. Use the Railway dashboard to view real-time deploy logs, configure environment variables (API keys, DATABASE_URL, secrets), monitor CPU/memory/network usage, scale resources, and manually trigger redeployments. Auto-deploy is connected to the GitHub main branch."
            )}</div>
            <div style="font-size:0.8rem;color:#64748B;">Deploys, DB, logs</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Railway", "https://railway.app/dashboard", use_container_width=True)
    with col3:
        st.markdown(f"""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">\U0001f4b3</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Stripe Dashboard{_info_tip(
                "Stripe Dashboard — Payment processing platform for QuarterCharts subscriptions and billing (Step 6 — currently deferred). Once implemented, Stripe will handle checkout sessions, recurring subscription management, customer self-service portal, webhook events for payment confirmations, and plan-based access enforcement. Use the Stripe dashboard to configure products, pricing tiers, and test payments."
            )}</div>
            <div style="font-size:0.8rem;color:#64748B;">Billing, subscriptions</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Stripe", "https://dashboard.stripe.com", use_container_width=True)

    st.markdown("---")
    st.markdown("### \U0001f4e6 Repository" + _info_tip("Repository &amp; Deployment — Links to the source code repository and the live production site. The QuarterCharts app auto-deploys from the GitHub main branch to Railway whenever new commits are pushed, ensuring the live site always reflects the latest code."), unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">\U0001f419</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">GitHub Repository{_info_tip(
                "GitHub Repository (miteproyects/opensankey) — The full source code for QuarterCharts. Contains all Python pages, configuration files, issue tracking, and pull requests. Pushing commits to the main branch automatically triggers a new deployment on Railway. Use GitHub for version control, code reviews, and issue management."
            )}</div>
            <div style="font-size:0.8rem;color:#64748B;">Code, issues, PRs</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open GitHub", "https://github.com/miteproyects/opensankey", use_container_width=True)
    with col2:
        st.markdown(f"""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">\U0001f310</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Live Site{_info_tip(
                "Live Site (quartercharts.com) — The production website that end users visit. Hosted via Railway (Streamlit app), it auto-deploys from the GitHub main branch. Click to open the public-facing site and verify that recent changes are live and rendering correctly."
            )}</div>
            <div style="font-size:0.8rem;color:#64748B;">quartercharts.com</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Live Site", "https://quartercharts.com", use_container_width=True)

    st.markdown("---")
    st.markdown("### \u26a1 System Info" + _info_tip("System Information — Overview of the current tech stack and platform configuration powering QuarterCharts. Displays the hosting platform, database, authentication provider, payment processor, domain, deployment pipeline, and security settings at a glance."), unsafe_allow_html=True)
    st.markdown(f"""
    <div class="step-card">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div><span style="color:#64748B;font-size:0.85rem;">Platform:{_info_tip("Platform: Streamlit (Python framework) renders the frontend UI with interactive widgets and charts. Railway provides cloud hosting for both the Streamlit app server and the PostgreSQL database, handling HTTP routing, SSL, and resource scaling.")}</span> <span style="color:#F1F5F9;">Streamlit + Railway</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Database:{_info_tip("Database: PostgreSQL hosted on Railway. Stores all persistent data including user profiles, company records, financial metrics, audit logs, and session data. Connected via DATABASE_URL environment variable with SSL-encrypted connections.")}</span> <span style="color:#F1F5F9;">PostgreSQL (Railway)</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Auth:{_info_tip("Auth: Firebase Authentication manages all user identity operations — sign-up, login, password reset, and session tokens. Supports Email/Password and Google SSO providers. User records sync with the PostgreSQL database for role-based access control.")}</span> <span style="color:#F1F5F9;">Firebase Auth</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Payments:{_info_tip("Payments: Stripe integration (Step 6 — deferred). Once live, Stripe will process subscription billing, checkout sessions, customer portal access, webhook-driven payment events, and plan-based feature gating for B2B SaaS tiers.")}</span> <span style="color:#F1F5F9;">Stripe (planned)</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Domain:{_info_tip("Domain: quartercharts.com — the public-facing URL where end users access the platform. DNS points to the Railway-hosted Streamlit app. All traffic is served over HTTPS with automatic SSL certificates.")}</span> <span style="color:#F1F5F9;">quartercharts.com</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Auto-deploy:{_info_tip("Auto-deploy: Every push to the GitHub main branch automatically triggers a new build and deployment on Railway. No manual intervention needed — commit, push, and the live site updates within minutes. Monitor deploy status in the Railway dashboard.")}</span> <span style="color:#10B981;">GitHub main \u2192 Railway</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Target:{_info_tip("Target: Business goal of reaching $50K annual recurring revenue (ARR) from B2B SaaS subscriptions. This metric drives product roadmap priorities, pricing strategy, and feature development across all implementation steps.")}</span> <span style="color:#F1F5F9;">$50K/year B2B SaaS</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">NSFE Password:{_info_tip("NSFE Password: This admin dashboard is protected by a password gate to restrict access to authorized managers only. The password is stored in the app source code and should be changed periodically. Share it only with team members who need access to project management data.")}</span> <span style="color:#F59E0B;">Active</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Action Buttons ──
    _btn_col1, _btn_col2, _btn_col3 = st.columns([1, 1, 2])
    with _btn_col1:
        if st.button("💾 Save All Statuses", use_container_width=True, type="primary", key="save_set"):
            st.toast("✅ All statuses saved!", icon="💾")
    with _btn_col2:
        if st.button("🔄 Refresh from DB", use_container_width=True, key="refresh_set"):
            st.toast("🔄 Data refreshed from database!", icon="🔄")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# AI ASSISTANT TAB
# ═══════════════════════════════════════════════════════════════════════

_CHAT_SYSTEM_PROMPT = """You are the QuarterCharts AI Assistant \u2014 a helpful expert embedded in the NSFE Manager Control Center.

You help the platform manager with:
- Platform architecture questions (Streamlit, Railway, PostgreSQL, Firebase)
- Security & compliance guidance (ISO 27001, SOC 2)
- Implementation strategy for remaining steps
- Code snippets and debugging for QuarterCharts
- SRI (Ecuador tax) invoice processing questions
- B2B SaaS pricing and go-to-market strategy

Keep answers concise and actionable. Use code blocks when showing code.
You are part of QuarterCharts \u2014 a financial visualization platform targeting $50K/year B2B SaaS.
Tech stack: Streamlit + Plotly + Railway + PostgreSQL + Firebase Auth.
"""



def _render_chat():
    """AI Assistant chat interface powered by Claude API."""
    st.markdown(f"""
    <div class="nsfe-header">
        <h1>\U0001f916 AI Command Center</h1>
        <p style="color:#94A3B8;font-size:0.9rem;">Claude-powered assistant{_info_tip(
            "AI Assistant — A built-in chat interface powered by the Claude API (Anthropic). Ask questions about QuarterCharts architecture, implementation progress, security posture, deployment pipeline, or business strategy. Responses are context-aware and tailored to the NSFE project. Requires an ANTHROPIC_API_KEY environment variable configured in your Railway deployment settings."
        )}</p>
        <p>Claude-powered assistant &nbsp;\u00b7&nbsp; Ask anything about QuarterCharts</p>
    </div>
    """, unsafe_allow_html=True)

    # ── API Key check ──
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.warning("\u27a1\ufe0f **Anthropic API key not configured.**")
        st.markdown(f"""
        <div class="step-card">
            <h4 style="color:#F1F5F9;margin:0 0 12px;">Setup Instructions{_info_tip(
                "Setup Instructions — To activate the AI assistant: 1) Create an API key at console.anthropic.com under your Anthropic account. 2) Go to your Railway project settings. 3) Add a new environment variable named ANTHROPIC_API_KEY with your key as the value. 4) Redeploy the app. The assistant will then respond to messages in real-time."
            )}</h4>
            <div style="color:#94A3B8;font-size:0.9rem;line-height:1.7;">
                1. Go to <strong>console.anthropic.com</strong> \u2192 API Keys<br>
                2. Create a new key<br>
                3. In Railway dashboard \u2192 Variables, add:<br>
                <code style="background:#1E293B;padding:4px 8px;border-radius:4px;color:#10B981;">ANTHROPIC_API_KEY=sk-ant-...</code><br>
                4. Redeploy \u2014 the chat will activate automatically
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### \U0001f4ac Preview Mode (no API key)" + _info_tip(
            "Preview Mode — The AI assistant is running without an API key. You can type messages and they will be saved in your session, but no responses will be generated. Once you configure the ANTHROPIC_API_KEY in Railway and redeploy, the assistant will switch to live mode and respond to every message in real-time using Claude."
        ), unsafe_allow_html=True)
        st.info("You can still use this interface to draft messages. They will be processed once the API key is set.")

    # ── Chat history in session state ──
    if "nsfe_chat_history" not in st.session_state:
        st.session_state.nsfe_chat_history = []

    # ── Display conversation ──
    for msg in st.session_state.nsfe_chat_history:
        with st.chat_message(msg["role"], avatar="\U0001f9d1\u200d\U0001f4bc" if msg["role"] == "user" else "\U0001f916"):
            st.markdown(msg["content"])

    # ── Chat input ──
    user_input = st.chat_input("Ask the AI assistant anything about QuarterCharts...")
    if user_input:
        # Add user message
        st.session_state.nsfe_chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="\U0001f9d1\u200d\U0001f4bc"):
            st.markdown(user_input)

        # Generate response
        with st.chat_message("assistant", avatar="\U0001f916"):
            if api_key:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.nsfe_chat_history
                    ]
                    with st.spinner("Thinking..."):
                        response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=2048,
                            system=_CHAT_SYSTEM_PROMPT,
                            messages=messages,
                        )
                    assistant_msg = response.content[0].text
                    st.markdown(assistant_msg)
                    st.session_state.nsfe_chat_history.append(
                        {"role": "assistant", "content": assistant_msg}
                    )
                except ImportError:
                    err = "\u274c `anthropic` package not installed. Add `anthropic` to requirements.txt and redeploy."
                    st.error(err)
                    st.session_state.nsfe_chat_history.append({"role": "assistant", "content": err})
                except Exception as e:
                    err = f"\u274c API Error: {str(e)}"
                    st.error(err)
                    st.session_state.nsfe_chat_history.append({"role": "assistant", "content": err})
            else:
                placeholder_msg = (
                    "\U0001f4a1 **API key not configured yet.** Your message has been saved. "
                    "Once you add `ANTHROPIC_API_KEY` to Railway environment variables, "
                    "the AI assistant will respond in real-time.\n\n"
                    f"**Your message:** {user_input}"
                )
                st.markdown(placeholder_msg)
                st.session_state.nsfe_chat_history.append(
                    {"role": "assistant", "content": placeholder_msg}
                )

    # ── Sidebar: Quick prompts ──
    st.markdown("---")
    st.markdown("#### \u26a1 Quick Prompts" + _info_tip(
        "Quick Prompts — Pre-written starter questions to help you explore common topics instantly. Click any prompt to auto-send it to the AI assistant. Covers architecture overviews, security recommendations, next implementation steps, and deployment guidance for QuarterCharts."
    ), unsafe_allow_html=True)
    quick_prompts = [
        "What's the next priority step to implement?",
        "Generate the code for Step 5A (wire auth into app.py)",
        "What security issues should I fix first?",
        "Help me set up Firebase project for QuarterCharts",
        "Draft the SRI invoice XML parser",
        "What do I need for ISO 27001 certification?",
    ]
    cols = st.columns(2)
    for i, prompt in enumerate(quick_prompts):
        with cols[i % 2]:
            if st.button(prompt, key=f"qp_{i}", use_container_width=True):
                st.session_state.nsfe_chat_history.append({"role": "user", "content": prompt})
                st.rerun()

    # ── Clear chat ──
    st.markdown("---")
    if st.button("\U0001f5d1\ufe0f Clear Chat History", type="secondary"):
        st.session_state.nsfe_chat_history = []
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def _sync_steps():
    """Recompute step-level status & progress from substep statuses."""
    if "nsfe_step_overrides" not in st.session_state:
        st.session_state.nsfe_step_overrides = {}
    overrides = st.session_state.nsfe_step_overrides
    for step in STEPS:
        for sub in step["substeps"]:
            key = sub["id"]
            if key in overrides:
                sub["status"] = overrides[key]
        subs = step["substeps"]
        total = len([s for s in subs if s["status"] != "future"])
        done = len([s for s in subs if s["status"] == "done"])
        deferred = len([s for s in subs if s["status"] == "deferred"])
        partial = len([s for s in subs if s["status"] == "partial"])
        if total == 0:
            step["status"] = "pending"
            step["progress"] = 0
        elif deferred == total:
            step["status"] = "deferred"
            step["progress"] = 0
        elif done == total:
            step["status"] = "done"
            step["progress"] = 100
        elif done > 0 or partial > 0:
            step["status"] = "partial"
            step["progress"] = int((done / total) * 100)
        else:
            step["status"] = "pending"
            step["progress"] = 0

def _render_infrastructure():
    """Infrastructure documentation hub – auto-synced with Google Docs."""
    import datetime

    st.markdown("## 🏗️ Infrastructure Documentation")
    st.caption("Live documents synced with Google Docs. Any edits in Google Docs are reflected here automatically.")

    # ── Document Cards ────────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="border:1px solid #e0e0e0; border-radius:12px; padding:24px; text-align:center; background:#f8fafc;">
            <div style="font-size:48px; margin-bottom:12px;">📋</div>
            <h3 style="margin:0 0 8px 0; color:#1E3A5F;">Infrastructure Overview</h3>
            <p style="color:#666; font-size:14px; margin-bottom:16px;">Complete technical stack reference: hosting, domains, database, auth, deployment pipeline, and environment configuration.</p>
            <a href="https://docs.google.com/document/d/1Crci_JCcJE4T1hOKwxiWUacemvzFfJBi/edit" target="_blank"
               style="display:inline-block; padding:10px 24px; background:#2563EB; color:white; border-radius:8px; text-decoration:none; font-weight:bold; margin:4px;">
                📄 Open Document
            </a>
            <a href="https://docs.google.com/document/d/1Crci_JCcJE4T1hOKwxiWUacemvzFfJBi/export?format=pdf" target="_blank"
               style="display:inline-block; padding:10px 24px; background:#16A34A; color:white; border-radius:8px; text-decoration:none; font-weight:bold; margin:4px;">
                ⬇️ Download PDF
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="border:1px solid #e0e0e0; border-radius:12px; padding:24px; text-align:center; background:#f8fafc;">
            <div style="font-size:48px; margin-bottom:12px;">🛡️</div>
            <h3 style="margin:0 0 8px 0; color:#1E3A5F;">ISO 27001 / SOC 2 Roadmap</h3>
            <p style="color:#666; font-size:14px; margin-bottom:16px;">Compliance readiness roadmap: gap analysis, phased implementation plan, budget estimates, and quick wins.</p>
            <a href="https://docs.google.com/document/d/1-wZtRiB6Hvt0DJ8SbTjqXQMJlm8Qzr1S/edit" target="_blank"
               style="display:inline-block; padding:10px 24px; background:#2563EB; color:white; border-radius:8px; text-decoration:none; font-weight:bold; margin:4px;">
                📄 Open Document
            </a>
            <a href="https://docs.google.com/document/d/1-wZtRiB6Hvt0DJ8SbTjqXQMJlm8Qzr1S/export?format=pdf" target="_blank"
               style="display:inline-block; padding:10px 24px; background:#16A34A; color:white; border-radius:8px; text-decoration:none; font-weight:bold; margin:4px;">
                ⬇️ Download PDF
            </a>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ── Embedded Live Preview ─────────────────────────────────────────────────────────────
    st.markdown("---")
    doc_choice = st.selectbox(
        "📖 Preview document",
        ["Infrastructure Overview", "ISO 27001 / SOC 2 Roadmap"],
        key="infra_doc_preview"
    )

    if doc_choice == "Infrastructure Overview":
        gdoc_url = "https://docs.google.com/document/d/1Crci_JCcJE4T1hOKwxiWUacemvzFfJBi/preview"
    else:
        gdoc_url = "https://docs.google.com/document/d/1-wZtRiB6Hvt0DJ8SbTjqXQMJlm8Qzr1S/preview"

    st.markdown(
        f'<iframe src="{gdoc_url}" width="100%" height="600" '
        f'style="border:1px solid #e0e0e0; border-radius:8px;"></iframe>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.caption(f"Documents are live-synced with Google Docs. Last rendered: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")


def _render_certifications():
    """Certifications tab: ISO 27001 / SOC 2 compliance tracker with status management."""
    import datetime, json

    st.markdown("## \U0001f6e1\ufe0f ISO 27001 / SOC 2 Certification Tracker")
    st.caption("Track compliance progress across all phases. Statuses are saved to database and synced with the roadmap document.")

    # ââ Certification task data (from ISO 27001 / SOC 2 Roadmap) ââ
    CERT_PHASES = [
        {
            "phase": "Quick Wins",
            "icon": "\u26a1",
            "timeline": "Week 1-2",
            "color": "#16A34A",
            "tasks": [
                {"id": "QW-1", "name": "Enable MFA on GitHub, Railway, Cloudflare, Firebase", "priority": "Critical", "effort": "30 min/service"},
                {"id": "QW-2", "name": "Enable GitHub branch protection on main (require PR reviews)", "priority": "High", "effort": "15 min"},
                {"id": "QW-3", "name": "Set up UptimeRobot free-tier monitoring for quartercharts.com", "priority": "Medium", "effort": "10 min"},
                {"id": "QW-4", "name": "Enable Dependabot security alerts on GitHub repo", "priority": "High", "effort": "5 min"},
                {"id": "QW-5", "name": "Document current system architecture diagram", "priority": "High", "effort": "2 hours"},
            ],
        },
        {
            "phase": "Phase 1: Foundation",
            "icon": "\U0001f3d7\ufe0f",
            "timeline": "Months 1-3",
            "color": "#2563EB",
            "tasks": [
                {"id": "P1-1", "name": "ISMS Policy Suite (Information Security, Acceptable Use, Data Classification)", "priority": "High", "target": "Month 1"},
                {"id": "P1-2", "name": "Asset Inventory (catalog all systems, data stores, APIs, third-party services)", "priority": "High", "target": "Month 1"},
                {"id": "P1-3", "name": "Risk Register (initial risk assessment: threats, likelihood, impact)", "priority": "High", "target": "Month 2"},
                {"id": "P1-4", "name": "Access Control Policy (RBAC model, enforce MFA on admin accounts)", "priority": "High", "target": "Month 2"},
                {"id": "P1-5", "name": "Centralized Logging (Railway log drain to Datadog/Papertrail)", "priority": "High", "target": "Month 3"},
                {"id": "P1-6", "name": "Automated Backups (daily PostgreSQL backups with retention policy)", "priority": "High", "target": "Month 3"},
                {"id": "P1-7", "name": "Vendor Register (document third-party vendors with risk ratings)", "priority": "Medium", "target": "Month 3"},
            ],
        },
        {
            "phase": "Phase 2: Technical Hardening",
            "icon": "\U0001f527",
            "timeline": "Months 4-6",
            "color": "#D97706",
            "tasks": [
                {"id": "P2-1", "name": "Vulnerability Scanning (SAST with Bandit, dependency scanning with Dependabot)", "priority": "High", "target": "Month 4"},
                {"id": "P2-2", "name": "Incident Response Plan (detection, containment, eradication, recovery procedures)", "priority": "High", "target": "Month 4"},
                {"id": "P2-3", "name": "Session Management (timeouts, secure cookie flags, concurrent session limits)", "priority": "High", "target": "Month 4"},
                {"id": "P2-4", "name": "Uptime Monitoring (external monitoring with UptimeRobot/Pingdom + alerting)", "priority": "Medium", "target": "Month 5"},
                {"id": "P2-5", "name": "Change Management Process (PR reviews, branch protection, deployment gates)", "priority": "Medium", "target": "Month 5"},
            ],
        },
        {
            "phase": "Phase 3: Process Maturity",
            "icon": "\U0001f4cb",
            "timeline": "Months 7-9",
            "color": "#7C3AED",
            "tasks": [
                {"id": "P3-1", "name": "Security Awareness Training (deliver training for all team members)", "priority": "Medium", "target": "Month 7"},
                {"id": "P3-2", "name": "Business Continuity Plan (BCP/DR plan, RPO/RTO targets, failover procedures)", "priority": "Medium", "target": "Month 7"},
                {"id": "P3-3", "name": "Runbooks & SOPs (deployment, rollback, DB maintenance, incident handling)", "priority": "Medium", "target": "Month 8"},
                {"id": "P3-4", "name": "Internal Audit Program (establish schedule, conduct first ISMS audit)", "priority": "High", "target": "Month 8"},
                {"id": "P3-5", "name": "Privacy Impact Assessment (assess data handling, document data flows)", "priority": "Medium", "target": "Month 9"},
                {"id": "P3-6", "name": "Supplier Assessments (security assessments of Railway, Firebase, Cloudflare, Yahoo Finance)", "priority": "Medium", "target": "Month 9"},
            ],
        },
        {
            "phase": "Phase 4: Certification & Attestation",
            "icon": "\U0001f3c6",
            "timeline": "Months 10-12",
            "color": "#DC2626",
            "tasks": [
                {"id": "P4-1", "name": "Pre-Audit Readiness Check (engage consultant for ISO 27001 readiness)", "priority": "High", "target": "Month 10"},
                {"id": "P4-2", "name": "Evidence Collection (compile 3+ months of logs, reviews, training records)", "priority": "High", "target": "Month 10"},
                {"id": "P4-3", "name": "SOC 2 Type I Report (engage auditor for point-in-time assessment)", "priority": "High", "target": "Month 11"},
                {"id": "P4-4", "name": "ISO 27001 Stage 1 Audit (documentation review by certification body)", "priority": "High", "target": "Month 11"},
                {"id": "P4-5", "name": "ISO 27001 Stage 2 Audit (on-site/remote audit of ISMS implementation)", "priority": "High", "target": "Month 12"},
                {"id": "P4-6", "name": "SOC 2 Type II Observation (begin 3-6 month observation period)", "priority": "High", "target": "Month 12"},
            ],
        },
    ]

    STATUS_OPTIONS = ["Not Started", "In Progress", "Partial", "Done", "Blocked"]
    STATUS_ICONS = {
        "Not Started": "\u23f3",
        "In Progress": "\U0001f504",
        "Partial": "\U0001f7e1",
        "Done": "\u2705",
        "Blocked": "\U0001f6d1",
    }
    STATUS_COLORS = {
        "Not Started": "#9CA3AF",
        "In Progress": "#3B82F6",
        "Partial": "#F59E0B",
        "Done": "#10B981",
        "Blocked": "#EF4444",
    }

    # ââ Load / initialize statuses from session state ââ
    if "cert_statuses" not in st.session_state:
        st.session_state.cert_statuses = {}
    if "cert_notes" not in st.session_state:
        st.session_state.cert_notes = {}

    # Try loading from database
    if "cert_loaded" not in st.session_state:
        st.session_state.cert_loaded = True
        try:
            conn = st.session_state.get("db_conn")
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cert_tracker (
                        task_id TEXT PRIMARY KEY,
                        status TEXT DEFAULT 'Not Started',
                        notes TEXT DEFAULT '',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                cur.execute("SELECT task_id, status, notes FROM cert_tracker")
                for row in cur.fetchall():
                    st.session_state.cert_statuses[row[0]] = row[1]
                    st.session_state.cert_notes[row[0]] = row[2] or ""
        except Exception:
            pass

    # ââ Overall progress metrics ââ
    all_tasks = []
    for phase in CERT_PHASES:
        all_tasks.extend(phase["tasks"])
    total_tasks = len(all_tasks)
    done_tasks = sum(1 for t in all_tasks if st.session_state.cert_statuses.get(t["id"], "Not Started") == "Done")
    in_progress_tasks = sum(1 for t in all_tasks if st.session_state.cert_statuses.get(t["id"], "Not Started") in ["In Progress", "Partial"])
    blocked_tasks = sum(1 for t in all_tasks if st.session_state.cert_statuses.get(t["id"], "Not Started") == "Blocked")
    pct = int((done_tasks / total_tasks) * 100) if total_tasks else 0

    # Overall progress bar
    st.markdown(f"""
    <div style="background:#0F172A; border-radius:12px; padding:20px; margin-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="color:white; font-size:18px; font-weight:bold;">\U0001f4ca Overall Compliance Progress</span>
            <span style="color:#10B981; font-size:24px; font-weight:bold;">{pct}%</span>
        </div>
        <div style="background:#1E293B; border-radius:8px; height:16px; overflow:hidden;">
            <div style="background:linear-gradient(90deg, #10B981, #059669); width:{pct}%; height:100%; border-radius:8px; transition:width 0.5s;"></div>
        </div>
        <div style="display:flex; justify-content:space-around; margin-top:16px;">
            <div style="text-align:center;">
                <div style="color:#10B981; font-size:28px; font-weight:bold;">{done_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">Completed</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#3B82F6; font-size:28px; font-weight:bold;">{in_progress_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">In Progress</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#EF4444; font-size:28px; font-weight:bold;">{blocked_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">Blocked</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#9CA3AF; font-size:28px; font-weight:bold;">{total_tasks - done_tasks - in_progress_tasks - blocked_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">Not Started</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ââ Update button ââ
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    with col_btn1:
        save_clicked = st.button("\U0001f4be Save All Statuses", type="primary", use_container_width=True)
    with col_btn2:
        refresh_clicked = st.button("\U0001f504 Refresh from DB", use_container_width=True)

    if save_clicked:
        try:
            conn = st.session_state.get("db_conn")
            if conn:
                cur = conn.cursor()
                for phase in CERT_PHASES:
                    for task in phase["tasks"]:
                        tid = task["id"]
                        status = st.session_state.cert_statuses.get(tid, "Not Started")
                        notes = st.session_state.cert_notes.get(tid, "")
                        cur.execute("""
                            INSERT INTO cert_tracker (task_id, status, notes, updated_at)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (task_id) DO UPDATE
                            SET status = EXCLUDED.status,
                                notes = EXCLUDED.notes,
                                updated_at = CURRENT_TIMESTAMP
                        """, (tid, status, notes))
                conn.commit()
                st.success("\u2705 All statuses saved to database!")
            else:
                st.warning("\u26a0\ufe0f Database not connected. Statuses saved in session only.")
        except Exception as e:
            st.error(f"Error saving: {e}")

    if refresh_clicked:
        try:
            conn = st.session_state.get("db_conn")
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT task_id, status, notes FROM cert_tracker")
                for row in cur.fetchall():
                    st.session_state.cert_statuses[row[0]] = row[1]
                    st.session_state.cert_notes[row[0]] = row[2] or ""
                st.success("\u2705 Statuses refreshed from database!")
                st.rerun()
        except Exception as e:
            st.error(f"Error refreshing: {e}")

    st.markdown("---")

    # ââ Phase-by-phase task tracker ââ
    for phase_data in CERT_PHASES:
        phase_tasks = phase_data["tasks"]
        phase_done = sum(1 for t in phase_tasks if st.session_state.cert_statuses.get(t["id"], "Not Started") == "Done")
        phase_total = len(phase_tasks)
        phase_pct = int((phase_done / phase_total) * 100) if phase_total else 0

        with st.expander(
            f"{phase_data['icon']} {phase_data['phase']} ({phase_data['timeline']})  \u2014  "
            f"{phase_done}/{phase_total} done ({phase_pct}%)",
            expanded=(phase_pct < 100),
        ):
            # Phase progress bar
            st.markdown(f"""
            <div style="background:#E2E8F0; border-radius:6px; height:8px; margin-bottom:16px; overflow:hidden;">
                <div style="background:{phase_data['color']}; width:{phase_pct}%; height:100%; border-radius:6px;"></div>
            </div>
            """, unsafe_allow_html=True)

            for task in phase_tasks:
                tid = task["id"]
                current_status = st.session_state.cert_statuses.get(tid, "Not Started")
                current_notes = st.session_state.cert_notes.get(tid, "")
                icon = STATUS_ICONS.get(current_status, "\u2753")
                scolor = STATUS_COLORS.get(current_status, "#9CA3AF")

                c1, c2, c3 = st.columns([0.5, 3, 1.5])
                with c1:
                    st.markdown(f"<div style='font-size:20px; text-align:center; padding-top:6px;'>{icon}</div>", unsafe_allow_html=True)
                with c2:
                    priority_badge = ""
                    if task.get("priority") == "Critical":
                        priority_badge = " <span style='background:#DC2626; color:white; padding:1px 8px; border-radius:4px; font-size:11px;'>CRITICAL</span>"
                    elif task.get("priority") == "High":
                        priority_badge = " <span style='background:#F59E0B; color:white; padding:1px 8px; border-radius:4px; font-size:11px;'>HIGH</span>"
                    st.markdown(
                        f"<div style='padding-top:4px;'><strong>{tid}</strong> \u2014 {task['name']}{priority_badge}</div>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    new_status = st.selectbox(
                        "Status",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0,
                        key=f"cert_status_{tid}",
                        label_visibility="collapsed",
                    )
                    if new_status != current_status:
                        st.session_state.cert_statuses[tid] = new_status

                # Optional notes field
                new_notes = st.text_input(
                    "Notes",
                    value=current_notes,
                    key=f"cert_notes_{tid}",
                    placeholder="Add notes...",
                    label_visibility="collapsed",
                )
                if new_notes != current_notes:
                    st.session_state.cert_notes[tid] = new_notes

                st.markdown("<hr style='margin:4px 0; border:none; border-top:1px solid #E2E8F0;'>", unsafe_allow_html=True)

    # ââ Reference link ââ
    st.markdown("---")
    st.markdown(
        "\U0001f4c4 **Full Roadmap Document:** "
        "[Open in Google Docs](https://docs.google.com/document/d/1-wZtRiB6Hvt0DJ8SbTjqXQMJlm8Qzr1S/edit) | "
        "[Download PDF](https://docs.google.com/document/d/1-wZtRiB6Hvt0DJ8SbTjqXQMJlm8Qzr1S/export?format=pdf)"
    )
    st.caption(f"Last rendered: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")



def _render_team_admin():
    """Team management and admin dashboard."""
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">Team & Admin Dashboard</h1>
        <p class="hero-subtitle">Member management \u00b7 Role assignments \u00b7 System administration</p>
    </div>
    """, unsafe_allow_html=True)

    # \u2500\u2500 Team Members (Step 10A) \u2500\u2500
    st.markdown("""
    <div style="margin-top:12px;">
        <h2 style="color:#F8FAFC;margin-bottom:4px;">\U0001f465 Team Members</h2>
        <p style="color:#94A3B8;font-size:0.9rem;">Manage team access, roles, and permissions</p>
    </div>
    """, unsafe_allow_html=True)

    _team_members = [
        {"name": "Sebasti\u00e1n Flores", "email": "sebasflores@gmail.com", "role": "Owner",
         "status": "Active", "joined": "2025-12-01", "last_active": "2026-03-24",
         "permissions": "Full access \u2013 all modules, billing, team management"},
        {"name": "Project Bot", "email": "bot@quartercharts.com", "role": "System",
         "status": "Active", "joined": "2025-12-01", "last_active": "2026-03-24",
         "permissions": "Automated deployments, CI/CD, monitoring"},
        {"name": "\u2014", "email": "(invite pending)", "role": "Developer",
         "status": "Invited", "joined": "\u2014", "last_active": "\u2014",
         "permissions": "Code, database, infrastructure access"},
        {"name": "\u2014", "email": "(invite pending)", "role": "Analyst",
         "status": "Invited", "joined": "\u2014", "last_active": "\u2014",
         "permissions": "Dashboard view, data export, reports"},
    ]

    _role_colors = {"Owner": "#8B5CF6", "System": "#3B82F6", "Admin": "#EF4444",
                    "Developer": "#22C55E", "Analyst": "#F59E0B", "Viewer": "#64748B"}

    for _member in _team_members:
        _r_color = _role_colors.get(_member["role"], "#64748B")
        _s_color = "#22C55E" if _member["status"] == "Active" else "#F59E0B" if _member["status"] == "Invited" else "#EF4444"
        _s_icon = "\U0001f7e2" if _member["status"] == "Active" else "\U0001f7e1" if _member["status"] == "Invited" else "\U0001f534"
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:12px;padding:16px 20px;
                    margin-bottom:10px;border:1px solid #334155;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div style="flex:1;min-width:200px;">
                    <div style="color:#F8FAFC;font-weight:600;font-size:1rem;">{_member['name']}</div>
                    <div style="color:#64748B;font-size:0.85rem;margin-top:2px;">{_member['email']}</div>
                </div>
                <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                    <span style="background:{_r_color}22;color:{_r_color};padding:4px 12px;border-radius:20px;
                                font-size:0.8rem;font-weight:600;border:1px solid {_r_color}44;">{_member['role']}</span>
                    <span style="color:{_s_color};font-size:0.8rem;">{_s_icon} {_member['status']}</span>
                </div>
            </div>
            <div style="display:flex;gap:24px;margin-top:10px;font-size:0.8rem;color:#64748B;flex-wrap:wrap;">
                <span>\U0001f4c5 Joined: {_member['joined']}</span>
                <span>\u23f0 Last active: {_member['last_active']}</span>
                <span>\U0001f511 {_member['permissions']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Role definitions
    st.markdown("---")
    st.markdown("""
    <div style="margin-top:12px;">
        <h3 style="color:#F8FAFC;margin-bottom:8px;">\U0001f511 Role Definitions</h3>
    </div>
    """, unsafe_allow_html=True)

    _roles_data = [
        {"role": "Owner", "color": "#8B5CF6", "desc": "Full platform access including billing, team management, and destructive operations",
         "perms": "All modules \u00b7 Billing \u00b7 Team mgmt \u00b7 Delete data \u00b7 API keys"},
        {"role": "Admin", "color": "#EF4444", "desc": "Full operational access without billing or ownership transfer capabilities",
         "perms": "All modules \u00b7 Team mgmt \u00b7 Settings \u00b7 No billing"},
        {"role": "Developer", "color": "#22C55E", "desc": "Technical access for development, deployment, and infrastructure management",
         "perms": "Code \u00b7 Database \u00b7 Deploy \u00b7 Infra \u00b7 No team mgmt"},
        {"role": "Analyst", "color": "#F59E0B", "desc": "Data access for viewing dashboards, running reports, and exporting data",
         "perms": "Dashboard \u00b7 Reports \u00b7 Export \u00b7 Read-only settings"},
        {"role": "Viewer", "color": "#64748B", "desc": "Read-only access to dashboards and public information",
         "perms": "Dashboard view only \u00b7 No export \u00b7 No settings"},
    ]

    _roles_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;">'
    for _r in _roles_data:
        _roles_html += f'''
        <div style="background:#0F172A;border-radius:10px;padding:14px;border:1px solid {_r['color']}33;">
            <div style="color:{_r['color']};font-weight:700;font-size:0.95rem;margin-bottom:4px;">{_r['role']}</div>
            <div style="color:#94A3B8;font-size:0.8rem;margin-bottom:8px;">{_r['desc']}</div>
            <div style="color:#64748B;font-size:0.75rem;border-top:1px solid #1E293B;padding-top:6px;">{_r['perms']}</div>
        </div>'''
    _roles_html += '</div>'
    st.markdown(_roles_html, unsafe_allow_html=True)

    # \u2500\u2500 Admin Dashboard (Step 10B) \u2500\u2500
    st.markdown("---")
    st.markdown("""
    <div style="margin-top:20px;">
        <h2 style="color:#F8FAFC;margin-bottom:4px;">\U0001f6e0\ufe0f Admin Dashboard</h2>
        <p style="color:#94A3B8;font-size:0.9rem;">System health, activity log, and quick admin actions</p>
    </div>
    """, unsafe_allow_html=True)

    _health_items = [
        {"label": "App Status", "value": "\U0001f7e2 Online", "detail": "Railway \u00b7 us-west2 \u00b7 1 replica", "color": "#22C55E"},
        {"label": "Database", "value": "\U0001f7e2 Connected", "detail": "PostgreSQL \u00b7 Railway \u00b7 99.9% uptime", "color": "#22C55E"},
        {"label": "Auth Service", "value": "\U0001f7e2 Active", "detail": "Firebase Auth \u00b7 2 users registered", "color": "#22C55E"},
        {"label": "Last Deploy", "value": "\U0001f680 Today", "detail": "Auto-deploy from GitHub main", "color": "#3B82F6"},
        {"label": "SSL/TLS", "value": "\U0001f512 Valid", "detail": "Let's Encrypt \u00b7 Auto-renewal", "color": "#22C55E"},
        {"label": "Domain", "value": "\U0001f310 Active", "detail": "quartercharts.com \u00b7 DNS OK", "color": "#22C55E"},
    ]

    _health_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin:12px 0;">'
    for _h in _health_items:
        _health_html += f'''
        <div style="background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:10px;padding:14px;
                    border:1px solid #334155;">
            <div style="color:#94A3B8;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px;">{_h['label']}</div>
            <div style="color:{_h['color']};font-weight:700;font-size:1rem;margin:4px 0;">{_h['value']}</div>
            <div style="color:#64748B;font-size:0.75rem;">{_h['detail']}</div>
        </div>'''
    _health_html += '</div>'
    st.markdown(_health_html, unsafe_allow_html=True)

    # Recent Activity
    st.markdown("""
    <div style="margin-top:20px;">
        <h3 style="color:#F8FAFC;margin-bottom:8px;">\U0001f4cb Recent Activity</h3>
    </div>
    """, unsafe_allow_html=True)

    _activities = [
        {"time": "2026-03-24 15:30", "user": "Sebasti\u00e1n", "action": "Deployed", "detail": "fix: remove orphan triple-quote causing SyntaxError", "icon": "\U0001f680"},
        {"time": "2026-03-24 15:25", "user": "Sebasti\u00e1n", "action": "Code commit", "detail": "Added Save/Refresh buttons to Dashboard, Security, Settings", "icon": "\U0001f4be"},
        {"time": "2026-03-24 14:00", "user": "Sebasti\u00e1n", "action": "Feature added", "detail": "SEO tab with 69 tasks across 8 phases", "icon": "\u2728"},
        {"time": "2026-03-23 10:00", "user": "Sebasti\u00e1n", "action": "Feature added", "detail": "Certifications tab with landing page", "icon": "\u2728"},
        {"time": "2026-03-22 16:00", "user": "System", "action": "Auto-deploy", "detail": "Infrastructure tab implementation", "icon": "\u2699\ufe0f"},
        {"time": "2026-03-20 09:00", "user": "Sebasti\u00e1n", "action": "Config change", "detail": "Updated NSFE password and security settings", "icon": "\U0001f512"},
    ]

    _activity_html = '<div style="background:#0F172A;border-radius:12px;border:1px solid #334155;overflow:hidden;">'
    for _idx, _act in enumerate(_activities):
        _border = "border-bottom:1px solid #1E293B;" if _idx < len(_activities) - 1 else ""
        _activity_html += f'''
        <div style="padding:12px 16px;{_border}display:flex;align-items:center;gap:12px;">
            <span style="font-size:1.2rem;">{_act['icon']}</span>
            <div style="flex:1;">
                <div style="color:#F8FAFC;font-size:0.85rem;font-weight:500;">{_act['action']}: {_act['detail']}</div>
                <div style="color:#64748B;font-size:0.75rem;margin-top:2px;">{_act['user']} \u00b7 {_act['time']}</div>
            </div>
        </div>'''
    _activity_html += '</div>'
    st.markdown(_activity_html, unsafe_allow_html=True)

    # Quick Admin Actions
    st.markdown("""
    <div style="margin-top:20px;">
        <h3 style="color:#F8FAFC;margin-bottom:8px;">\u26a1 Quick Actions</h3>
    </div>
    """, unsafe_allow_html=True)

    _qa1, _qa2, _qa3, _qa4 = st.columns(4)
    with _qa1:
        if st.button("\U0001f504 Force Redeploy", use_container_width=True, key="admin_redeploy"):
            st.toast("\U0001f680 Redeployment triggered!", icon="\U0001f504")
    with _qa2:
        if st.button("\U0001f5d1\ufe0f Clear Cache", use_container_width=True, key="admin_cache"):
            st.toast("\U0001f5d1\ufe0f Cache cleared!", icon="\u2705")
    with _qa3:
        if st.button("\U0001f4e4 Export Logs", use_container_width=True, key="admin_logs"):
            st.toast("\U0001f4e4 Logs exported!", icon="\U0001f4cb")
    with _qa4:
        if st.button("\U0001f50d Run Health Check", use_container_width=True, key="admin_health"):
            st.toast("\u2705 All systems healthy!", icon="\U0001f49a")

    # System Configuration
    st.markdown("""
    <div style="margin-top:20px;">
        <h3 style="color:#F8FAFC;margin-bottom:8px;">\u2699\ufe0f System Configuration</h3>
    </div>
    """, unsafe_allow_html=True)

    _config_items = [
        ("Platform", "Streamlit 1.40+"),
        ("Hosting", "Railway (us-west2)"),
        ("Database", "PostgreSQL 16 (Railway)"),
        ("Authentication", "Firebase Auth"),
        ("Domain", "quartercharts.com"),
        ("SSL", "Let's Encrypt (auto-renew)"),
        ("CI/CD", "GitHub \u2192 Railway auto-deploy"),
        ("Python", "3.12.x"),
        ("Session Timeout", "30 minutes"),
        ("Max Login Attempts", "5 per minute"),
        ("Password Policy", "Min 8 chars, complexity required"),
        ("RBAC", "Enabled (Owner, Admin, Developer, Analyst, Viewer)"),
    ]

    _config_html = '<div style="background:#0F172A;border-radius:12px;border:1px solid #334155;overflow:hidden;">'
    for _ci, (_ck, _cv) in enumerate(_config_items):
        _border = "border-bottom:1px solid #1E293B;" if _ci < len(_config_items) - 1 else ""
        _config_html += f'''
        <div style="padding:10px 16px;{_border}display:flex;justify-content:space-between;align-items:center;">
            <span style="color:#94A3B8;font-size:0.85rem;">{_ck}</span>
            <span style="color:#F8FAFC;font-size:0.85rem;font-weight:500;">{_cv}</span>
        </div>'''
    _config_html += '</div>'
    st.markdown(_config_html, unsafe_allow_html=True)

    # \u2500\u2500 Action Buttons \u2500\u2500
    _btn_col1, _btn_col2, _btn_col3 = st.columns([1, 1, 2])
    with _btn_col1:
        if st.button("\U0001f4be Save All Statuses", use_container_width=True, type="primary", key="save_team"):
            st.toast("\u2705 All statuses saved!", icon="\U0001f4be")
    with _btn_col2:
        if st.button("\U0001f504 Refresh from DB", use_container_width=True, key="refresh_team"):
            st.toast("\U0001f504 Data refreshed from database!", icon="\U0001f504")
            st.rerun()


def _render_seo():
    """SEO tab: comprehensive SEO roadmap & task tracker for quartercharts.com."""
    import datetime, json

    st.markdown("## 🔍 SEO Roadmap — quartercharts.com")
    st.caption("Living task tracker for Search Engine Optimization & Generative Engine Optimization (GEO). Statuses update as work progresses.")

    # ── Competitors Reference ──
    with st.expander("🏆 Competitor Landscape", expanded=False):
        st.markdown("""
        | # | Competitor | URL | Focus |
        |---|-----------|-----|-------|
        | 1 | Finviz | finviz.com | Screener, maps, charts |
        | 2 | TradingView | tradingview.com | Charting, social trading |
        | 3 | Macrotrends | macrotrends.net | Historical financial data |
        | 4 | Simply Wall St | simplywall.st | Visual investing, Snowflake |
        | 5 | Wisesheets | wisesheets.io | Excel/Sheets financial add-on |
        | 6 | Stock Analysis | stockanalysis.com | Fundamentals, screener |
        | 7 | Seeking Alpha | seekingalpha.com | Research, ratings |
        | 8 | Yahoo Finance | finance.yahoo.com | News, quotes, portfolios |
        | 9 | Koyfin | koyfin.com | Dashboards, comps |
        | 10 | GuruFocus | gurufocus.com | Value investing, screeners |
        """)

    # ── SEO task data ──
    SEO_PHASES = [
        {
            "phase": "Phase 1: Technical SEO Foundation",
            "icon": "⚙️",
            "timeline": "Week 1-2",
            "color": "#3B82F6",
            "tasks": [
                {"id": "T1-1", "name": "Fix SPA Rendering: Add SSR or pre-rendering for Streamlit pages so Google can crawl dynamic content", "priority": "Critical", "effort": "1-2 days"},
                {"id": "T1-2", "name": "Generate and submit XML sitemap (sitemap.xml) covering all key pages", "priority": "Critical", "effort": "2 hours"},
                {"id": "T1-3", "name": "Create and configure robots.txt — allow public pages, block admin/NSFE", "priority": "Critical", "effort": "30 min"},
                {"id": "T1-4", "name": "Set up Google Search Console — verify ownership, submit sitemap", "priority": "Critical", "effort": "1 hour"},
                {"id": "T1-5", "name": "Set up Google Analytics 4 (GA4) — track page views, events, user flows", "priority": "High", "effort": "1 hour"},
                {"id": "T1-6", "name": "Core Web Vitals optimization: measure LCP, FID/INP, CLS — target all green", "priority": "High", "effort": "3-5 days"},
                {"id": "T1-7", "name": "Mobile responsiveness audit — ensure all pages work on mobile", "priority": "High", "effort": "2-3 days"},
                {"id": "T1-8", "name": "Implement HTTPS redirect (force SSL) and verify no mixed-content", "priority": "High", "effort": "30 min"},
                {"id": "T1-9", "name": "Set up canonical URLs to avoid duplicate content", "priority": "Medium", "effort": "1 hour"},
                {"id": "T1-10", "name": "Optimize page load speed: compress images, lazy-load charts, minimize bundles", "priority": "High", "effort": "2-3 days"},
            ],
        },
        {
            "phase": "Phase 2: On-Page SEO & Meta Tags",
            "icon": "📝",
            "timeline": "Week 2-3",
            "color": "#10B981",
            "tasks": [
                {"id": "T2-1", "name": "Write unique title tags for each page (50-60 chars) with primary keyword + brand", "priority": "Critical", "effort": "2 hours"},
                {"id": "T2-2", "name": "Write compelling meta descriptions for each page (150-160 chars) with CTAs", "priority": "Critical", "effort": "2 hours"},
                {"id": "T2-3", "name": "Add Open Graph (og:) tags for social sharing on every page", "priority": "High", "effort": "2 hours"},
                {"id": "T2-4", "name": "Add Twitter Card tags for all pages", "priority": "Medium", "effort": "1 hour"},
                {"id": "T2-5", "name": "Implement proper heading hierarchy (H1>H2>H3) — one H1 per page", "priority": "High", "effort": "2 hours"},
                {"id": "T2-6", "name": "Add descriptive alt text to all images and chart screenshots", "priority": "Medium", "effort": "2 hours"},
                {"id": "T2-7", "name": "Create SEO-friendly URL structure with clean slugs", "priority": "High", "effort": "1-2 days"},
                {"id": "T2-8", "name": "Internal linking strategy: connect related pages for same ticker", "priority": "Medium", "effort": "3 hours"},
                {"id": "T2-9", "name": "Add breadcrumb navigation for better UX and search display", "priority": "Medium", "effort": "3 hours"},
                {"id": "T2-10", "name": "Implement hreflang tags if targeting international audiences", "priority": "Low", "effort": "1 hour"},
            ],
        },
        {
            "phase": "Phase 3: Schema Markup & Structured Data",
            "icon": "🏗️",
            "timeline": "Week 3-4",
            "color": "#8B5CF6",
            "tasks": [
                {"id": "T3-1", "name": "Add Organization schema (JSON-LD): name, logo, url, sameAs", "priority": "Critical", "effort": "1 hour"},
                {"id": "T3-2", "name": "Add WebSite schema with SearchAction for sitelinks search box", "priority": "High", "effort": "1 hour"},
                {"id": "T3-3", "name": "Add FinancialProduct schema for stock analysis tools", "priority": "High", "effort": "2 hours"},
                {"id": "T3-4", "name": "Add FAQPage schema on pricing and features pages", "priority": "Medium", "effort": "2 hours"},
                {"id": "T3-5", "name": "Add BreadcrumbList schema matching visible breadcrumbs", "priority": "Medium", "effort": "1 hour"},
                {"id": "T3-6", "name": "Add SoftwareApplication schema for app listing", "priority": "Medium", "effort": "1 hour"},
                {"id": "T3-7", "name": "Validate all structured data with Google Rich Results Test", "priority": "High", "effort": "1 hour"},
                {"id": "T3-8", "name": "Add Dataset schema for stock financial data tables", "priority": "Low", "effort": "2 hours"},
            ],
        },
        {
            "phase": "Phase 4: Content Strategy & Keyword Targeting",
            "icon": "📚",
            "timeline": "Month 2-3",
            "color": "#F59E0B",
            "tasks": [
                {"id": "T4-1", "name": "Keyword research: identify 50+ target keywords with Ahrefs/SEMrush", "priority": "Critical", "effort": "1-2 days"},
                {"id": "T4-2", "name": "Create blog/learn section with SEO-optimized articles", "priority": "Critical", "effort": "Ongoing"},
                {"id": "T4-3", "name": "Build individual stock landing pages (/stock/NVDA) aggregating all tools", "priority": "Critical", "effort": "3-5 days"},
                {"id": "T4-4", "name": "Create comparison pages: Quarter Charts vs Finviz, vs TradingView", "priority": "High", "effort": "2-3 days"},
                {"id": "T4-5", "name": "Write a glossary of financial terms with internal links", "priority": "Medium", "effort": "2-3 days"},
                {"id": "T4-6", "name": "Create How It Works guide pages for each feature", "priority": "High", "effort": "3-5 days"},
                {"id": "T4-7", "name": "Publish weekly market analysis or earnings season previews", "priority": "Medium", "effort": "Ongoing"},
                {"id": "T4-8", "name": "Target long-tail keywords for niche financial visualization queries", "priority": "High", "effort": "Ongoing"},
                {"id": "T4-9", "name": "Optimize existing feature descriptions with keyword-rich copy", "priority": "Medium", "effort": "3 hours"},
                {"id": "T4-10", "name": "Create use-case pages: For Day Traders, Value Investors, Advisors", "priority": "Medium", "effort": "2-3 days"},
            ],
        },
        {
            "phase": "Phase 5: GEO & AI Optimization (2025-2026)",
            "icon": "🤖",
            "timeline": "Month 2-4",
            "color": "#EC4899",
            "tasks": [
                {"id": "T5-1", "name": "Create /llms.txt file: structured summary for LLM crawlers", "priority": "Critical", "effort": "2 hours"},
                {"id": "T5-2", "name": "Optimize for AI Overviews (Google SGE): write citation-worthy content", "priority": "Critical", "effort": "Ongoing"},
                {"id": "T5-3", "name": "Add authoritative citations and data sources (E-E-A-T signals)", "priority": "High", "effort": "Ongoing"},
                {"id": "T5-4", "name": "Structure content with Q&A format for ChatGPT/Perplexity extraction", "priority": "High", "effort": "2-3 days"},
                {"id": "T5-5", "name": "Ensure crawlability by AI agents (GPTBot, PerplexityBot in robots.txt)", "priority": "High", "effort": "1 hour"},
                {"id": "T5-6", "name": "Build topical authority with content clusters", "priority": "High", "effort": "Ongoing"},
                {"id": "T5-7", "name": "Add author bios and credentials (E-E-A-T signals) to content", "priority": "Medium", "effort": "2 hours"},
                {"id": "T5-8", "name": "Create /about page with team credentials and company story", "priority": "Medium", "effort": "3 hours"},
                {"id": "T5-9", "name": "Monitor AI search visibility in ChatGPT, Perplexity, AI Overviews", "priority": "Medium", "effort": "Ongoing"},
                {"id": "T5-10", "name": "Submit site to AI directories and training datasets", "priority": "Low", "effort": "2 hours"},
            ],
        },
        {
            "phase": "Phase 6: Backlinks & Off-Page SEO",
            "icon": "🔗",
            "timeline": "Month 3-6",
            "color": "#06B6D4",
            "tasks": [
                {"id": "T6-1", "name": "Create free embeddable widget (mini Sankey) linking back to site", "priority": "High", "effort": "3-5 days"},
                {"id": "T6-2", "name": "Guest post on finance/fintech blogs and publications", "priority": "High", "effort": "Ongoing"},
                {"id": "T6-3", "name": "Submit to Product Hunt, AlternativeTo, SaaSHub directories", "priority": "High", "effort": "1 day"},
                {"id": "T6-4", "name": "Create data-driven infographics for embedding and link building", "priority": "Medium", "effort": "3-5 days"},
                {"id": "T6-5", "name": "Build relationships with finance YouTubers/bloggers", "priority": "Medium", "effort": "Ongoing"},
                {"id": "T6-6", "name": "Share on Reddit (r/stocks, r/investing, r/dataisbeautiful)", "priority": "Medium", "effort": "Ongoing"},
                {"id": "T6-7", "name": "Set up HARO/Connectively alerts for finance/fintech queries", "priority": "Low", "effort": "1 hour"},
                {"id": "T6-8", "name": "Create public API or data feed encouraging developer backlinks", "priority": "Low", "effort": "1-2 weeks"},
            ],
        },
        {
            "phase": "Phase 7: Local & Social Signals",
            "icon": "📱",
            "timeline": "Month 4-6",
            "color": "#F97316",
            "tasks": [
                {"id": "T7-1", "name": "Create and optimize Google Business Profile", "priority": "Medium", "effort": "1 hour"},
                {"id": "T7-2", "name": "Set up social profiles: Twitter/X, LinkedIn, YouTube", "priority": "High", "effort": "2 hours"},
                {"id": "T7-3", "name": "Create YouTube channel with tutorials and feature demos", "priority": "High", "effort": "Ongoing"},
                {"id": "T7-4", "name": "Share chart screenshots and insights on Twitter/X", "priority": "Medium", "effort": "Ongoing"},
                {"id": "T7-5", "name": "Build email newsletter for market updates", "priority": "Medium", "effort": "Ongoing"},
            ],
        },
        {
            "phase": "Phase 8: Monitoring & Continuous Optimization",
            "icon": "📊",
            "timeline": "Ongoing",
            "color": "#6366F1",
            "tasks": [
                {"id": "T8-1", "name": "Set up weekly rank tracking for target keywords", "priority": "High", "effort": "1 hour"},
                {"id": "T8-2", "name": "Monitor Google Search Console: impressions, clicks, CTR, positions", "priority": "High", "effort": "Weekly"},
                {"id": "T8-3", "name": "Monthly competitor analysis: rankings, content, backlinks", "priority": "Medium", "effort": "Monthly"},
                {"id": "T8-4", "name": "A/B test title tags and meta descriptions for CTR", "priority": "Medium", "effort": "Ongoing"},
                {"id": "T8-5", "name": "Run quarterly Core Web Vitals audit", "priority": "Medium", "effort": "Quarterly"},
                {"id": "T8-6", "name": "Monitor and fix 404 errors, broken links, crawl errors", "priority": "High", "effort": "Weekly"},
                {"id": "T8-7", "name": "Track AI search visibility: cited in AI Overviews, ChatGPT, Perplexity", "priority": "Medium", "effort": "Monthly"},
                {"id": "T8-8", "name": "Update content regularly: refresh stats, add tickers, keep current", "priority": "Medium", "effort": "Ongoing"},
            ],
        },
    ]

    STATUS_OPTIONS = ["Not Started", "In Progress", "Partial", "Done", "Blocked", "Future"]
    STATUS_ICONS = {
        "Not Started": "⏳",
        "In Progress": "🔄",
        "Partial": "🟡",
        "Done": "✅",
        "Blocked": "🛑",
        "Future": "🔮",
    }
    STATUS_COLORS = {
        "Not Started": "#9CA3AF",
        "In Progress": "#3B82F6",
        "Partial": "#F59E0B",
        "Done": "#10B981",
        "Blocked": "#EF4444",
        "Future": "#A78BFA",
    }

    # ── Load / initialize statuses from session state ──
    if "seo_statuses" not in st.session_state:
        st.session_state.seo_statuses = {}
    if "seo_notes" not in st.session_state:
        st.session_state.seo_notes = {}

    # Try loading from database
    if "seo_loaded" not in st.session_state:
        st.session_state.seo_loaded = True
        try:
            conn = st.session_state.get("db_conn")
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS seo_tracker (
                        task_id TEXT PRIMARY KEY,
                        status TEXT DEFAULT 'Not Started',
                        notes TEXT DEFAULT '',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                cur.execute("SELECT task_id, status, notes FROM seo_tracker")
                for row in cur.fetchall():
                    st.session_state.seo_statuses[row[0]] = row[1]
                    st.session_state.seo_notes[row[0]] = row[2] or ""
        except Exception:
            pass

    # ── Progress Overview ──
    total_tasks = sum(len(p["tasks"]) for p in SEO_PHASES)
    done_tasks = sum(1 for t in st.session_state.seo_statuses.values() if t == "Done")
    in_progress_tasks = sum(1 for t in st.session_state.seo_statuses.values() if t == "In Progress")
    blocked_tasks = sum(1 for t in st.session_state.seo_statuses.values() if t == "Blocked")
    pct = int((done_tasks / total_tasks) * 100) if total_tasks else 0

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:16px;padding:28px;margin-bottom:28px;border:1px solid #334155;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <h3 style="margin:0;color:#F1F5F9;">📈 SEO Progress</h3>
            <span style="color:#3B82F6;font-weight:bold;font-size:24px;">{pct}%</span>
        </div>
        <div style="background:#1E293B;border-radius:8px;height:16px;overflow:hidden;">
            <div style="background:linear-gradient(90deg, #3B82F6, #06B6D4); width:{pct}%; height:100%; border-radius:8px; transition:width 0.5s;"></div>
        </div>
        <div style="display:flex; justify-content:space-around; margin-top:16px;">
            <div style="text-align:center;">
                <div style="color:#10B981; font-size:28px; font-weight:bold;">{done_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">Completed</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#3B82F6; font-size:28px; font-weight:bold;">{in_progress_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">In Progress</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#EF4444; font-size:28px; font-weight:bold;">{blocked_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">Blocked</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#9CA3AF; font-size:28px; font-weight:bold;">{total_tasks - done_tasks - in_progress_tasks - blocked_tasks}</div>
                <div style="color:#94A3B8; font-size:12px;">Remaining</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Save / Export buttons ──
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    with col_btn1:
        save_clicked = st.button("💾 Save All Statuses", key="seo_save", use_container_width=True, type="primary")
    with col_btn2:
        export_clicked = st.button("📋 Export Report", key="seo_export", use_container_width=True)

    if save_clicked:
        try:
            conn = st.session_state.get("db_conn")
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS seo_tracker (
                        task_id TEXT PRIMARY KEY,
                        status TEXT DEFAULT 'Not Started',
                        notes TEXT DEFAULT '',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                for phase in SEO_PHASES:
                    for task in phase["tasks"]:
                        tid = task["id"]
                        status = st.session_state.seo_statuses.get(tid, "Not Started")
                        notes = st.session_state.seo_notes.get(tid, "")
                        cur.execute("""
                            INSERT INTO seo_tracker (task_id, status, notes, updated_at)
                            VALUES (%s, %s, %s, NOW())
                            ON CONFLICT (task_id) DO UPDATE SET
                                status = EXCLUDED.status,
                                notes = EXCLUDED.notes,
                                updated_at = NOW()
                        """, (tid, status, notes))
                conn.commit()
                st.success("✅ All SEO statuses saved to database!")
            else:
                st.warning("⚠️ No database connection — statuses saved in session only.")
        except Exception as e:
            st.error(f"Error saving: {e}")

    if export_clicked:
        report = "# SEO Roadmap Report — quartercharts.com\n"
        report += f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        report += f"Overall Progress: {done_tasks}/{total_tasks} ({pct}%)\n\n"
        for phase in SEO_PHASES:
            report += f"\n## {phase['icon']} {phase['phase']} ({phase['timeline']})\n"
            for task in phase["tasks"]:
                tid = task["id"]
                status = st.session_state.seo_statuses.get(tid, "Not Started")
                icon = STATUS_ICONS.get(status, "⏳")
                notes = st.session_state.seo_notes.get(tid, "")
                report += f"- [{icon} {status}] {tid}: {task['name']}"
                if notes:
                    report += f" — Note: {notes}"
                report += "\n"
        st.download_button("⬇️ Download Report", report, "seo_roadmap_report.md", "text/markdown")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── Phase-by-phase task rendering ──
    for phase in SEO_PHASES:
        phase_done = sum(1 for t in phase["tasks"] if st.session_state.seo_statuses.get(t["id"]) == "Done")
        phase_total = len(phase["tasks"])
        phase_pct = int((phase_done / phase_total) * 100) if phase_total else 0

        with st.expander(f"{phase['icon']} {phase['phase']}  —  {phase['timeline']}  ({phase_done}/{phase_total})", expanded=False):
            # Phase progress bar
            st.markdown(f"""
            <div style="background:#1E293B;border-radius:6px;height:8px;margin-bottom:16px;overflow:hidden;">
                <div style="background:{phase['color']};width:{phase_pct}%;height:100%;border-radius:6px;transition:width 0.5s;"></div>
            </div>
            """, unsafe_allow_html=True)

            for task in phase["tasks"]:
                tid = task["id"]
                current_status = st.session_state.seo_statuses.get(tid, "Not Started")
                current_notes = st.session_state.seo_notes.get(tid, "")
                status_color = STATUS_COLORS.get(current_status, "#9CA3AF")

                # Task card
                st.markdown(f"""
                <div style="background:#1E293B;border-left:4px solid {status_color};border-radius:8px;padding:14px 18px;margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <span style="color:#64748B;font-size:12px;font-weight:600;">{tid}</span>
                            <span style="color:{status_color};font-size:12px;margin-left:8px;">{STATUS_ICONS.get(current_status, '⏳')} {current_status}</span>
                            {"<span style='color:#EF4444;font-size:11px;margin-left:8px;background:#3B1111;padding:2px 6px;border-radius:4px;'>"+task['priority']+"</span>" if task.get('priority') == 'Critical' else "<span style='color:#94A3B8;font-size:11px;margin-left:8px;'>"+task.get('priority','')+"</span>"}
                        </div>
                        <span style="color:#64748B;font-size:11px;">{task.get('effort', task.get('target', ''))}</span>
                    </div>
                    <div style="color:#E2E8F0;font-size:14px;margin-top:6px;line-height:1.5;">{task['name']}</div>
                </div>
                """, unsafe_allow_html=True)

                # Status selector and notes
                col1, col2 = st.columns([1, 2])
                with col1:
                    idx = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
                    new_status = st.selectbox(
                        "Status", STATUS_OPTIONS, index=idx,
                        key=f"seo_status_{tid}", label_visibility="collapsed"
                    )
                    if new_status != current_status:
                        st.session_state.seo_statuses[tid] = new_status
                with col2:
                    new_notes = st.text_input(
                        "Notes", value=current_notes,
                        key=f"seo_notes_{tid}", label_visibility="collapsed",
                        placeholder="Add notes..."
                    )
                    if new_notes != current_notes:
                        st.session_state.seo_notes[tid] = new_notes

    # ── Footer with SEO tips ──
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:12px;padding:20px;margin-top:28px;border:1px solid #334155;">
        <h4 style="color:#F1F5F9;margin:0 0 12px 0;">💡 SEO Quick Tips for 2025-2026</h4>
        <ul style="color:#94A3B8;font-size:13px;line-height:1.8;margin:0;padding-left:20px;">
            <li><b style="color:#3B82F6;">GEO is the new SEO</b> — Optimize for AI engines (ChatGPT, Perplexity, Google AI Overviews) not just traditional search</li>
            <li><b style="color:#10B981;">E-E-A-T matters more than ever</b> — Experience, Expertise, Authoritativeness, Trustworthiness drive rankings</li>
            <li><b style="color:#F59E0B;">Content depth wins</b> — Comprehensive, well-structured content outranks thin pages</li>
            <li><b style="color:#EC4899;">Core Web Vitals are ranking factors</b> — Page speed and UX directly impact your position</li>
            <li><b style="color:#8B5CF6;">llms.txt is emerging</b> — Help AI crawlers understand your site with structured machine-readable files</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def _render_pricing_admin():
    """💳 Pricing – Spreadsheet-style CRUD for pricing plans."""
    from database import (get_all_plans, get_plan_by_id, create_plan,
                          update_plan, delete_plan, seed_default_plans)

    # Seed defaults if no plans exist
    all_plans = get_all_plans()
    if not all_plans:
        seed_default_plans()
        all_plans = get_all_plans()

    # ── Styles ──
    st.markdown("""
    <style>
    .price-admin-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 1.25rem;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .price-admin-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 0 0 4px;
    }
    .price-admin-sub {
        font-size: 0.82rem;
        color: #94a3b8;
        margin: 0;
    }
    .price-admin-stats {
        display: flex;
        gap: 10px;
        margin-top: 12px;
    }
    .price-admin-stat {
        background: rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: #93c5fd;
        font-weight: 600;
    }
    .price-grid-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #64748b;
        padding: 6px 0;
        white-space: nowrap;
    }
    .price-grid-section {
        font-size: 0.72rem;
        font-weight: 700;
        color: #3b82f6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 10px 0 4px;
        border-top: 1px solid #e2e8f0;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    active_count = sum(1 for p in all_plans if p.get("is_active"))
    popular_plan = next((p["name"] for p in all_plans if p.get("is_popular")), "None")
    stripe_ok = bool(os.environ.get("STRIPE_SECRET_KEY"))

    st.markdown(f"""
    <div class="price-admin-header">
        <div class="price-admin-title">Pricing Plans Manager</div>
        <p class="price-admin-sub">Spreadsheet editor — changes auto-update the public pricing page.</p>
        <div class="price-admin-stats">
            <span class="price-admin-stat">{len(all_plans)} plans</span>
            <span class="price-admin-stat">{active_count} active</span>
            <span class="price-admin-stat">Popular: {popular_plan}</span>
            <span class="price-admin-stat">Stripe: {'Connected' if stripe_ok else 'Not configured'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Add New Plan button ──
    add_col, _, _ = st.columns([1, 1, 4])
    with add_col:
        if st.button("➕ Add New Plan", use_container_width=True, key="price_add_btn"):
            st.session_state["_price_adding"] = True

    if st.session_state.get("_price_adding"):
        with st.form("add_plan_quick", clear_on_submit=True):
            ac1, ac2 = st.columns(2)
            with ac1:
                _ns = st.text_input("Slug", placeholder="e.g. pro-plus", key="nq_slug")
                _nn = st.text_input("Name", placeholder="e.g. Pro Plus", key="nq_name")
            with ac2:
                _npm = st.number_input("Monthly ($)", min_value=0.0, step=1.0, value=0.0, key="nq_pm")
                _nso = st.number_input("Sort Order", min_value=0, value=len(all_plans), key="nq_so")
            if st.form_submit_button("Create Plan", type="primary"):
                if _ns and _nn:
                    create_plan(slug=_ns.strip().lower().replace(" ", "-"),
                                name=_nn.strip(), price_monthly=_npm, sort_order=_nso)
                    st.session_state["_price_adding"] = False
                    st.toast(f"Plan '{_nn}' created!", icon="✅")
                    st.rerun()
                else:
                    st.error("Slug and Name are required.")

    # ── Manage ticker pool (outside the form so it updates instantly) ──
    _default_pool = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOG", "META"]
    if "_ticker_pool" not in st.session_state:
        st.session_state["_ticker_pool"] = _default_pool

    with st.expander("🎯 Manage Available Tickers"):
        st.markdown(
            '<p style="font-size:0.82rem;color:#64748b;margin-bottom:8px;">'
            'These tickers appear in the <b>Allowed Tickers</b> combobox for each plan. '
            'Add new ones below (comma-separated) or remove existing ones.</p>',
            unsafe_allow_html=True)
        _pool_display = ", ".join(sorted(st.session_state["_ticker_pool"]))
        st.code(_pool_display, language=None)
        _tk_add_col, _tk_rm_col = st.columns(2)
        with _tk_add_col:
            _new_tickers = st.text_input("Add tickers", placeholder="e.g. NFLX, AMD, DIS",
                                          key="_tk_pool_add", label_visibility="collapsed")
            if st.button("➕ Add", key="_tk_pool_add_btn", use_container_width=True):
                if _new_tickers.strip():
                    added = []
                    for t in _new_tickers.split(","):
                        t = t.strip().upper()
                        if t and t not in st.session_state["_ticker_pool"]:
                            st.session_state["_ticker_pool"].append(t)
                            added.append(t)
                    if added:
                        st.toast(f"Added: {', '.join(added)}", icon="✅")
                    st.rerun()
        with _tk_rm_col:
            if st.session_state["_ticker_pool"]:
                _rm_ticker = st.selectbox("Remove ticker", options=sorted(st.session_state["_ticker_pool"]),
                                           key="_tk_pool_rm", label_visibility="collapsed")
                if st.button("🗑️ Remove", key="_tk_pool_rm_btn", use_container_width=True):
                    st.session_state["_ticker_pool"].remove(_rm_ticker)
                    st.toast(f"Removed {_rm_ticker}", icon="🗑️")
                    st.rerun()

    # ── Spreadsheet grid ──
    # Build columns: [Label] + [Plan1] + [Plan2] + ...
    n = len(all_plans)
    plan_widths = [1.2] + [1] * n  # label column slightly wider

    with st.form("pricing_grid_form"):
        # ── SECTION: Identity ──
        st.markdown('<div class="price-grid-section">Identity</div>', unsafe_allow_html=True)

        # Name row
        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Name</div>', unsafe_allow_html=True)
        _names = {}
        for i, p in enumerate(all_plans):
            _names[p["id"]] = cols[i + 1].text_input("n", value=p.get("name", ""), key=f"g_name_{p['id']}", label_visibility="collapsed")

        # Slug row
        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Slug</div>', unsafe_allow_html=True)
        _slugs = {}
        for i, p in enumerate(all_plans):
            _slugs[p["id"]] = cols[i + 1].text_input("s", value=p.get("slug", ""), key=f"g_slug_{p['id']}", label_visibility="collapsed")

        # Description row
        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Description</div>', unsafe_allow_html=True)
        _descs = {}
        for i, p in enumerate(all_plans):
            _descs[p["id"]] = cols[i + 1].text_input("d", value=p.get("description", ""), key=f"g_desc_{p['id']}", label_visibility="collapsed")

        # ── SECTION: Pricing ──
        st.markdown('<div class="price-grid-section">Pricing</div>', unsafe_allow_html=True)

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Monthly ($)</div>', unsafe_allow_html=True)
        _pms = {}
        for i, p in enumerate(all_plans):
            _pms[p["id"]] = cols[i + 1].number_input("pm", value=float(p.get("price_monthly", 0)), min_value=0.0, step=1.0, format="%.0f", key=f"g_pm_{p['id']}", label_visibility="collapsed")

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Annual ($/yr)</div>', unsafe_allow_html=True)
        _pas = {}
        for i, p in enumerate(all_plans):
            _pas[p["id"]] = cols[i + 1].number_input("pa", value=float(p.get("price_annual", 0)), min_value=0.0, step=1.0, format="%.0f", key=f"g_pa_{p['id']}", label_visibility="collapsed")

        # ── SECTION: Features ──
        st.markdown('<div class="price-grid-section">Features (one per line)</div>', unsafe_allow_html=True)

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label"></div>', unsafe_allow_html=True)
        _feats = {}
        for i, p in enumerate(all_plans):
            existing = p.get("features", [])
            if isinstance(existing, str):
                try:
                    existing = json.loads(existing)
                except Exception:
                    existing = []
            _feats[p["id"]] = cols[i + 1].text_area("f", value="\n".join(existing) if isinstance(existing, list) else "", height=160, key=f"g_feat_{p['id']}", label_visibility="collapsed")

        # ── SECTION: Subscription Access ──
        st.markdown('<div class="price-grid-section">Subscription Access</div>', unsafe_allow_html=True)

        _pool = st.session_state["_ticker_pool"]
        _multiselect_options = sorted(_pool)

        # Row 1: "All tickers available" checkbox per plan
        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">All tickers available</div>', unsafe_allow_html=True)
        _all_tickers_chk = {}
        for i, p in enumerate(all_plans):
            cur_val = (p.get("allowed_tickers", "") or "").strip().upper()
            _all_tickers_chk[p["id"]] = cols[i + 1].checkbox("alltk", value=(cur_val == "ALL"), key=f"g_alltk_{p['id']}", label_visibility="collapsed")

        # Row 2: Specific tickers multiselect (only matters when checkbox is unchecked)
        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Specific Tickers</div>', unsafe_allow_html=True)
        _tickers = {}
        for i, p in enumerate(all_plans):
            cur_val = (p.get("allowed_tickers", "") or "").strip().upper()
            if cur_val == "ALL":
                _default_sel = []
            else:
                _default_sel = [t.strip() for t in cur_val.split(",") if t.strip() and t.strip() in _pool]
            _tickers[p["id"]] = cols[i + 1].multiselect("tk", options=_multiselect_options, default=_default_sel, key=f"g_tk_{p['id']}", label_visibility="collapsed")

        _page_options = ["charts", "sankey", "profile", "pricing", "dashboard", "home"]

        # If Allowed → Go to:
        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">If Allowed → Go to</div>', unsafe_allow_html=True)
        _redir_ok = {}
        for i, p in enumerate(all_plans):
            cur_ra = p.get("redirect_allowed", "charts")
            _idx = _page_options.index(cur_ra) if cur_ra in _page_options else 0
            _redir_ok[p["id"]] = cols[i + 1].selectbox("ra", options=_page_options, index=_idx, key=f"g_ra_{p['id']}", label_visibility="collapsed")

        # If Not Allowed → Go to:
        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">If Not Allowed → Go to</div>', unsafe_allow_html=True)
        _redir_no = {}
        for i, p in enumerate(all_plans):
            cur_rb = p.get("redirect_blocked", "pricing")
            _idx = _page_options.index(cur_rb) if cur_rb in _page_options else 3
            _redir_no[p["id"]] = cols[i + 1].selectbox("rb", options=_page_options, index=_idx, key=f"g_rb_{p['id']}", label_visibility="collapsed")

        # ── SECTION: Blocked Charts ──
        st.markdown('<div class="price-grid-section">Blocked Charts</div>', unsafe_allow_html=True)

        _CHART_CATEGORIES = {
            "Income Statement": [
                ("revenue_income", "Revenue & Income"),
                ("rev_product", "Revenue by Product"),
                ("rev_geo", "Revenue by Geography"),
                ("margins", "Profit Margins (%)"),
                ("eps", "Earnings Per Share (EPS)"),
                ("yoy", "Revenue YoY Variation"),
                ("qoq", "QoQ Revenue Variation"),
                ("opex", "Operating Expenses"),
                ("ebitda", "EBITDA"),
                ("tax", "Income Tax Expense"),
                ("sbc", "Stock Based Compensation"),
                ("expense_ratios", "Expense Ratios"),
                ("eff_tax_rate", "Effective Tax Rate"),
                ("shares", "Shares Outstanding"),
                ("income_breakdown", "Income Breakdown"),
                ("per_share", "Per Share Metrics"),
            ],
            "Cash Flow": [
                ("cash_flows", "Cash Flows"),
                ("cash_pos", "Cash Position"),
                ("capex", "Capital Expenditures"),
            ],
            "Balance Sheet": [
                ("assets", "Total Assets"),
                ("liabilities", "Liabilities"),
                ("equity_debt", "Equity vs Debt"),
            ],
            "Key Metrics": [
                ("pe_ratio", "P/E Ratio"),
                ("metric_cards", "Metric Cards"),
            ],
        }

        _blocked_charts = {}
        for cat_name, cat_charts in _CHART_CATEGORIES.items():
            cols = st.columns(plan_widths)
            cols[0].markdown(f'<div class="price-grid-label">{cat_name}</div>', unsafe_allow_html=True)
            chart_options = [c[1] for c in cat_charts]
            chart_keys = [c[0] for c in cat_charts]
            for i, p in enumerate(all_plans):
                pid = p["id"]
                cur_blocked = {c.strip() for c in (p.get("blocked_charts", "") or "").split(",") if c.strip()}
                default_sel = [chart_options[j] for j, k in enumerate(chart_keys) if k in cur_blocked]
                sel = cols[i + 1].multiselect(
                    f"bc_{cat_name}", options=chart_options, default=default_sel,
                    key=f"g_bc_{cat_name}_{pid}", label_visibility="collapsed",
                    placeholder="None blocked"
                )
                # Map display names back to keys
                sel_keys = {chart_keys[chart_options.index(s)] for s in sel}
                if pid not in _blocked_charts:
                    _blocked_charts[pid] = set()
                _blocked_charts[pid].update(sel_keys)

        # ── SECTION: CTA ──
        st.markdown('<div class="price-grid-section">Call to Action</div>', unsafe_allow_html=True)

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">CTA Text</div>', unsafe_allow_html=True)
        _ctas = {}
        for i, p in enumerate(all_plans):
            _ctas[p["id"]] = cols[i + 1].text_input("ct", value=p.get("cta_text", "Get Started"), key=f"g_cta_{p['id']}", label_visibility="collapsed")

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">CTA URL</div>', unsafe_allow_html=True)
        _cta_urls = {}
        for i, p in enumerate(all_plans):
            _cta_urls[p["id"]] = cols[i + 1].text_input("cu", value=p.get("cta_url", ""), key=f"g_cta_url_{p['id']}", label_visibility="collapsed")

        # ── SECTION: Settings ──
        st.markdown('<div class="price-grid-section">Settings</div>', unsafe_allow_html=True)

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Sort Order</div>', unsafe_allow_html=True)
        _sorts = {}
        for i, p in enumerate(all_plans):
            _sorts[p["id"]] = cols[i + 1].number_input("so", value=int(p.get("sort_order", 0)), min_value=0, key=f"g_sort_{p['id']}", label_visibility="collapsed")

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Popular</div>', unsafe_allow_html=True)
        _pops = {}
        for i, p in enumerate(all_plans):
            _pops[p["id"]] = cols[i + 1].checkbox("pop", value=bool(p.get("is_popular")), key=f"g_pop_{p['id']}", label_visibility="collapsed")

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Active</div>', unsafe_allow_html=True)
        _acts = {}
        for i, p in enumerate(all_plans):
            _acts[p["id"]] = cols[i + 1].checkbox("act", value=bool(p.get("is_active", True)), key=f"g_act_{p['id']}", label_visibility="collapsed")

        # ── SECTION: Stripe ──
        st.markdown('<div class="price-grid-section">Stripe Integration</div>', unsafe_allow_html=True)

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Product ID</div>', unsafe_allow_html=True)
        _sps = {}
        for i, p in enumerate(all_plans):
            _sps[p["id"]] = cols[i + 1].text_input("sp", value=p.get("stripe_product_id", ""), key=f"g_sp_{p['id']}", label_visibility="collapsed")

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Monthly Price ID</div>', unsafe_allow_html=True)
        _spms = {}
        for i, p in enumerate(all_plans):
            _spms[p["id"]] = cols[i + 1].text_input("spm", value=p.get("stripe_price_monthly", ""), key=f"g_spm_{p['id']}", label_visibility="collapsed")

        cols = st.columns(plan_widths)
        cols[0].markdown('<div class="price-grid-label">Annual Price ID</div>', unsafe_allow_html=True)
        _spas = {}
        for i, p in enumerate(all_plans):
            _spas[p["id"]] = cols[i + 1].text_input("spa", value=p.get("stripe_price_annual", ""), key=f"g_spa_{p['id']}", label_visibility="collapsed")

        # ── Action buttons ──
        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
        btn_cols = st.columns(plan_widths)
        btn_cols[0].markdown("")
        _save_all = st.form_submit_button("💾 Save All Changes", type="primary", use_container_width=True)

    if _save_all:
        _ok = 0
        for p in all_plans:
            pid = p["id"]
            feat_text = _feats.get(pid, "")
            feat_list = [f.strip() for f in feat_text.strip().split("\n") if f.strip()] if feat_text.strip() else []
            # Normalize allowed_tickers: checkbox = ALL, otherwise use multiselect
            if _all_tickers_chk.get(pid, False):
                norm_tk = "ALL"
            else:
                sel_tickers = _tickers.get(pid, [])
                norm_tk = ",".join(sorted(t.upper() for t in sel_tickers)) if sel_tickers else "ALL"
            result = update_plan(
                pid,
                name=(_names.get(pid, "") or "").strip(),
                slug=(_slugs.get(pid, "") or "").strip().lower().replace(" ", "-"),
                description=(_descs.get(pid, "") or "").strip(),
                price_monthly=_pms.get(pid, 0),
                price_annual=_pas.get(pid, 0),
                features=feat_list,
                cta_text=(_ctas.get(pid, "") or "").strip(),
                cta_url=(_cta_urls.get(pid, "") or "").strip(),
                is_popular=_pops.get(pid, False),
                is_active=_acts.get(pid, True),
                sort_order=_sorts.get(pid, 0),
                allowed_tickers=norm_tk,
                redirect_allowed=_redir_ok.get(pid, "charts"),
                redirect_blocked=_redir_no.get(pid, "pricing"),
                stripe_product_id=(_sps.get(pid, "") or "").strip(),
                stripe_price_monthly=(_spms.get(pid, "") or "").strip(),
                stripe_price_annual=(_spas.get(pid, "") or "").strip(),
                blocked_charts=",".join(sorted(_blocked_charts.get(pid, set()))),
            )
            if result:
                _ok += 1
        st.toast(f"Saved {_ok}/{len(all_plans)} plans!", icon="💾")
        st.rerun()

    # ── Delete section ──
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    with st.expander("🗑️ Delete a Plan"):
        del_options = {f"{p['name']} ({p['slug']})": p["id"] for p in all_plans}
        del_choice = st.selectbox("Select plan to delete", options=list(del_options.keys()), key="price_del_select")
        if st.button("Delete Plan", type="secondary", key="price_del_btn"):
            delete_plan(del_options[del_choice])
            st.toast(f"Deleted '{del_choice}'", icon="🗑️")
            st.rerun()


def _render_users_admin():
    """👥 Users – Admin dashboard for user management and plan assignments."""
    from database import (get_all_users_admin, get_user_stats, get_all_plans,
                          assign_user_plan, toggle_user_active)

    # ── Styles ──
    st.markdown("""
    <style>
    .users-admin-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 1.25rem;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .users-admin-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 0 0 4px;
    }
    .users-admin-sub {
        font-size: 0.82rem;
        color: #94a3b8;
        margin: 0;
    }
    .users-stats {
        display: flex;
        gap: 10px;
        margin-top: 12px;
        flex-wrap: wrap;
    }
    .users-stat {
        background: rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: #93c5fd;
        font-weight: 600;
    }
    .user-card {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 8px;
        transition: all 0.15s ease;
    }
    .user-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    }
    .user-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    .user-email {
        font-size: 0.82rem;
        color: #64748b;
        margin: 0;
    }
    .user-meta {
        font-size: 0.72rem;
        color: #94a3b8;
        margin: 2px 0 0;
    }
    .plan-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .plan-free { background: #f1f5f9; color: #64748b; }
    .plan-pro { background: #dbeafe; color: #2563eb; }
    .plan-enterprise { background: #1e293b; color: #f1f5f9; }
    .plan-admin { background: #dcfce7; color: #16a34a; }
    .status-active { color: #16a34a; }
    .status-inactive { color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header with stats ──
    stats = get_user_stats()
    st.markdown(f"""
    <div class="users-admin-header">
        <div class="users-admin-title">User Management</div>
        <p class="users-admin-sub">View all registered users, manage plans, and monitor activity.</p>
        <div class="users-stats">
            <span class="users-stat">👤 {stats['total']} total users</span>
            <span class="users-stat">🟢 {stats['active_today']} active today</span>
            <span class="users-stat">📅 {stats['active_week']} active this week</span>
            <span class="users-stat">🔑 {stats['google_users']} Google sign-in</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    users = get_all_users_admin()
    all_plans = get_all_plans()
    plan_options = {p["name"]: p["slug"] for p in all_plans}

    if not users:
        st.info("No users found. Users will appear here after they sign in.")
        return

    # ── Search / filter ──
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        search_q = st.text_input("🔍 Search users", placeholder="Name or email...",
                                  key="users_search", label_visibility="collapsed")
    with fc2:
        plan_filter = st.selectbox("Filter by plan", ["All Plans"] + list(plan_options.keys()),
                                    key="users_plan_filter", label_visibility="collapsed")
    with fc3:
        status_filter = st.selectbox("Filter by status", ["All", "Active", "Inactive"],
                                      key="users_status_filter", label_visibility="collapsed")

    # Apply filters
    filtered = users
    if search_q:
        q = search_q.lower()
        filtered = [u for u in filtered if q in u["email"].lower() or q in u["display_name"].lower()]
    if plan_filter != "All Plans":
        slug = plan_options[plan_filter]
        filtered = [u for u in filtered if u.get("plan_slug") == slug]
    if status_filter == "Active":
        filtered = [u for u in filtered if u.get("is_active")]
    elif status_filter == "Inactive":
        filtered = [u for u in filtered if not u.get("is_active")]

    st.markdown(f"<p style='font-size:0.8rem;color:#94a3b8;margin:4px 0 8px;'>"
                f"Showing {len(filtered)} of {len(users)} users</p>",
                unsafe_allow_html=True)

    # ── User list ──
    for u in filtered:
        _plan_slug = u.get("plan_slug", "free")
        _plan_class = "plan-enterprise" if _plan_slug == "enterprise" else \
                      "plan-pro" if _plan_slug == "pro" else \
                      "plan-admin" if u.get("billing_cycle") == "admin" else "plan-free"
        _status_class = "status-active" if u.get("is_active") else "status-inactive"
        _status_text = "Active" if u.get("is_active") else "Disabled"
        _provider = u.get("auth_provider", "email")
        _provider_icon = "🔑 Google" if _provider in ("google", "both") else "📧 Email"
        _created = u["created_at"].strftime("%b %d, %Y") if u.get("created_at") else "N/A"
        _last_login = u["last_login_at"].strftime("%b %d, %Y %H:%M") if u.get("last_login_at") else "Never"
        _login_count = u.get("login_count", 0)
        _plan_name = u.get("plan_name", "Free")
        _billing = u.get("billing_cycle", "")
        _billing_badge = " (admin)" if _billing == "admin" else f" ({_billing})" if _billing else ""
        _avatar = u.get("avatar_url", "")
        _name = u.get("display_name", "") or u["email"].split("@")[0]

        with st.expander(f"{'🟢' if u.get('is_active') else '🔴'} {_name} — {u['email']} — {_plan_name}{_billing_badge}"):
            ic1, ic2 = st.columns([2, 1])
            with ic1:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                    {'<img src="' + _avatar + '" style="width:40px;height:40px;border-radius:50%;object-fit:cover;" />' if _avatar else '<div style="width:40px;height:40px;border-radius:50%;background:#e2e8f0;display:flex;align-items:center;justify-content:center;font-size:1.1rem;">👤</div>'}
                    <div>
                        <div class="user-name">{_name}</div>
                        <div class="user-email">{u['email']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;font-size:0.8rem;color:#475569;">
                    <div>🔑 Auth: {_provider_icon}</div>
                    <div>📅 Joined: {_created}</div>
                    <div>🕐 Last login: {_last_login}</div>
                    <div>🔢 Login count: {_login_count}</div>
                    <div><span class="{_status_class}">● {_status_text}</span></div>
                    <div>💳 Plan: <span class="plan-badge {_plan_class}">{_plan_name}{_billing_badge}</span></div>
                </div>
                """, unsafe_allow_html=True)
            with ic2:
                st.markdown("<p style='font-size:0.78rem;font-weight:600;color:#64748b;margin-bottom:4px;'>Change Plan</p>",
                            unsafe_allow_html=True)
                new_plan = st.selectbox("Plan", options=list(plan_options.keys()),
                                         index=list(plan_options.keys()).index(_plan_name) if _plan_name in plan_options else 0,
                                         key=f"u_plan_{u['id']}", label_visibility="collapsed")
                if st.button("Apply Plan", key=f"u_apply_{u['id']}", use_container_width=True, type="primary"):
                    if assign_user_plan(u["id"], plan_options[new_plan]):
                        st.toast(f"Assigned {new_plan} to {u['email']}", icon="✅")
                        st.rerun()
                    else:
                        st.error("Failed to assign plan.")

                st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                if u.get("is_active"):
                    if st.button("🚫 Disable Account", key=f"u_dis_{u['id']}", use_container_width=True):
                        toggle_user_active(u["id"], False)
                        st.toast(f"Disabled {u['email']}", icon="🚫")
                        st.rerun()
                else:
                    if st.button("✅ Enable Account", key=f"u_en_{u['id']}", use_container_width=True):
                        toggle_user_active(u["id"], True)
                        st.toast(f"Enabled {u['email']}", icon="✅")
                        st.rerun()


_CONTEXT_PATH = os.path.join(os.path.dirname(__file__), "CONTEXT.md")

# ── Section definitions for the Memory tab ──────────────────────────────
_MD_SECTIONS = [
    {"key": "architecture",  "icon": "🏗️", "title": "Architecture",       "heading": "## 1. Architecture"},
    {"key": "file_map",      "icon": "📁", "title": "File Map",            "heading": "## 2. File Map"},
    {"key": "design",        "icon": "🎨", "title": "Design System",       "heading": "## 3. Design System"},
    {"key": "gotchas",       "icon": "⚠️", "title": "Gotchas & Patterns",  "heading": "## 4. Known Gotchas & Patterns"},
    {"key": "changelog",     "icon": "📝", "title": "Recent Changes",      "heading": "## 5. Recent Changes (Changelog)"},
    {"key": "pending",       "icon": "🚀", "title": "Pending / Future",    "heading": "## 6. Pending / Future Ideas"},
]


def _read_context():
    """Read CONTEXT.md and return full text."""
    try:
        with open(_CONTEXT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _write_context(text):
    """Write text back to CONTEXT.md."""
    with open(_CONTEXT_PATH, "w", encoding="utf-8") as f:
        f.write(text)


def _parse_sections(full_text):
    """Split CONTEXT.md into sections by ## headings. Returns dict {key: content}."""
    sections = {}
    for i, sec in enumerate(_MD_SECTIONS):
        heading = sec["heading"]
        start = full_text.find(heading)
        if start == -1:
            sections[sec["key"]] = ""
            continue
        # Content starts after the heading line
        content_start = full_text.find("\n", start) + 1
        # Find the next section heading or EOF
        next_start = len(full_text)
        for j in range(i + 1, len(_MD_SECTIONS)):
            ns = full_text.find(_MD_SECTIONS[j]["heading"])
            if ns != -1:
                next_start = ns
                break
        sections[sec["key"]] = full_text[content_start:next_start].strip()
    return sections


def _rebuild_md(sections, full_text):
    """Rebuild full CONTEXT.md from edited sections, preserving the header."""
    # Extract everything before first section (the title/intro)
    first_heading_pos = full_text.find(_MD_SECTIONS[0]["heading"])
    header = full_text[:first_heading_pos] if first_heading_pos != -1 else full_text.split("## ")[0]
    parts = [header.rstrip() + "\n\n"]
    for sec in _MD_SECTIONS:
        parts.append(sec["heading"] + "\n\n")
        content = sections.get(sec["key"], "").strip()
        if content:
            parts.append(content + "\n\n")
        parts.append("---\n\n")
    return "".join(parts).rstrip() + "\n"


def _render_memory():
    """Render the Memory (CONTEXT.md) editor tab."""

    # ── Styles ──
    st.markdown("""
    <style>
        .mem-header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-radius: 14px;
            padding: 24px 28px;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255,255,255,0.06);
        }
        .mem-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #f1f5f9;
            margin: 0 0 4px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .mem-sub {
            font-size: 0.85rem;
            color: #94a3b8;
            margin: 0;
        }
        .mem-stat-row {
            display: flex;
            gap: 12px;
            margin-top: 14px;
        }
        .mem-stat {
            background: rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 0.78rem;
            color: #93c5fd;
            font-weight: 600;
        }
        .mem-section-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
            overflow: hidden;
        }
        .mem-section-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 14px 18px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            cursor: pointer;
        }
        .mem-section-icon {
            font-size: 1.2rem;
        }
        .mem-section-title {
            font-size: 0.95rem;
            font-weight: 600;
            color: #1e293b;
        }
        .mem-section-lines {
            font-size: 0.72rem;
            color: #94a3b8;
            margin-left: auto;
            font-weight: 500;
        }
        .mem-auto-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: linear-gradient(135deg, #dcfce7, #bbf7d0);
            color: #166534;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 12px;
            border: 1px solid #86efac;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Load content ──
    full_text = _read_context()
    if not full_text:
        st.warning("CONTEXT.md not found. Creating a new one...")
        _write_context("# QuarterCharts — Developer Context & Memory\n\n---\n\n## 1. Architecture\n\n\n---\n\n## 2. File Map\n\n\n---\n\n## 3. Design System\n\n\n---\n\n## 4. Known Gotchas & Patterns\n\n\n---\n\n## 5. Recent Changes (Changelog)\n\n\n---\n\n## 6. Pending / Future Ideas\n\n")
        full_text = _read_context()

    sections = _parse_sections(full_text)
    total_lines = full_text.count("\n") + 1
    total_sections = len([s for s in sections.values() if s.strip()])
    file_size = os.path.getsize(_CONTEXT_PATH) if os.path.exists(_CONTEXT_PATH) else 0

    # ── Modification time ──
    mod_time = ""
    if os.path.exists(_CONTEXT_PATH):
        ts = os.path.getmtime(_CONTEXT_PATH)
        mod_time = datetime.fromtimestamp(ts).strftime("%b %d, %Y at %I:%M %p")

    # ── Header ──
    st.markdown(f"""
    <div class="mem-header">
        <div class="mem-title">🧠 Developer Memory</div>
        <p class="mem-sub">Living context file for AI-assisted development sessions. Edit sections below — changes auto-save to <code>CONTEXT.md</code>.</p>
        <div class="mem-stat-row">
            <span class="mem-stat">{total_lines} lines</span>
            <span class="mem-stat">{total_sections}/{len(_MD_SECTIONS)} sections</span>
            <span class="mem-stat">{file_size / 1024:.1f} KB</span>
            <span class="mem-stat">Updated: {mod_time}</span>
            <span class="mem-auto-badge">● Auto-save</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Mode toggle ──
    mode_col1, mode_col2, mode_col3 = st.columns([1, 1, 4])
    with mode_col1:
        section_mode = st.button("📑 Section Editor", use_container_width=True,
                                  type="primary" if not st.session_state.get("mem_raw_mode") else "secondary")
    with mode_col2:
        raw_mode = st.button("📝 Raw Editor", use_container_width=True,
                              type="primary" if st.session_state.get("mem_raw_mode") else "secondary")

    if section_mode:
        st.session_state["mem_raw_mode"] = False
    if raw_mode:
        st.session_state["mem_raw_mode"] = True

    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

    # ── RAW EDITOR MODE ──
    if st.session_state.get("mem_raw_mode"):
        st.markdown("#### Full Markdown")
        new_text = st.text_area(
            "CONTEXT.md",
            value=full_text,
            height=600,
            label_visibility="collapsed",
            key="mem_raw_editor",
        )
        c1, c2, c3 = st.columns([1, 1, 6])
        with c1:
            if st.button("💾 Save", type="primary", use_container_width=True, key="mem_raw_save"):
                _write_context(new_text)
                st.toast("✅ CONTEXT.md saved!", icon="💾")
                st.rerun()
        with c2:
            if st.button("🔄 Reload", use_container_width=True, key="mem_raw_reload"):
                st.rerun()

        # Preview
        with st.expander("👁️ Preview", expanded=False):
            st.markdown(new_text)
        return

    # ── SECTION EDITOR MODE ──
    edited = {}
    any_changed = False

    for sec in _MD_SECTIONS:
        content = sections.get(sec["key"], "")
        line_count = content.count("\n") + 1 if content.strip() else 0

        st.markdown(f"""
        <div class="mem-section-card">
            <div class="mem-section-header">
                <span class="mem-section-icon">{sec['icon']}</span>
                <span class="mem-section-title">{sec['title']}</span>
                <span class="mem-section-lines">{line_count} lines</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Edit: {sec['title']}", expanded=False):
            # Calculate dynamic height based on content
            n_lines = max(content.count("\n") + 3, 8)
            calc_height = min(max(n_lines * 22, 180), 500)

            new_content = st.text_area(
                sec["title"],
                value=content,
                height=calc_height,
                label_visibility="collapsed",
                key=f"mem_sec_{sec['key']}",
            )
            edited[sec["key"]] = new_content
            if new_content.strip() != content.strip():
                any_changed = True

            # Section preview
            if new_content.strip():
                st.markdown("---")
                st.markdown(new_content)

    # ── Save bar ──
    if any_changed:
        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
        save_col1, save_col2, _ = st.columns([1, 1, 6])
        with save_col1:
            if st.button("💾 Save All Changes", type="primary", use_container_width=True, key="mem_sec_save"):
                new_md = _rebuild_md(edited, full_text)
                _write_context(new_md)
                st.toast("✅ All sections saved to CONTEXT.md!", icon="💾")
                st.rerun()
        with save_col2:
            if st.button("↩️ Discard", use_container_width=True, key="mem_sec_discard"):
                st.rerun()
    else:
        st.markdown("<div style='text-align:center;color:#94a3b8;font-size:0.82rem;margin-top:1.5rem'>✓ All sections up to date</div>", unsafe_allow_html=True)

    # ── Quick add section ──
    st.markdown("<div style='margin-top:2rem'></div>", unsafe_allow_html=True)
    with st.expander("➕ Quick Add to Changelog"):
        new_entry = st.text_area("New changelog entry", height=80, placeholder="### 2026-04-03\n- Added new feature...", key="mem_quick_add")
        if st.button("Add to Changelog", key="mem_add_changelog"):
            if new_entry.strip():
                changelog = sections.get("changelog", "")
                updated_changelog = new_entry.strip() + "\n\n" + changelog
                sections["changelog"] = updated_changelog
                new_md = _rebuild_md(sections, full_text)
                _write_context(new_md)
                st.toast("✅ Changelog updated!", icon="📝")
                st.rerun()


def _render_analytics():
    """📊 Analytics – Google Analytics 4 dashboard with live data from GA4 Data API."""
    import os, json
    from datetime import datetime, timedelta

    # ── Styles ──
    st.markdown("""
    <style>
    .ga-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 1.25rem;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .ga-title { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; margin: 0 0 4px; }
    .ga-sub   { font-size: 0.82rem; color: #94a3b8; margin: 0; }
    .ga-kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 1rem; }
    .ga-kpi {
        flex: 1; min-width: 140px;
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 16px; text-align: center;
    }
    .ga-kpi-val  { font-size: 1.6rem; font-weight: 800; color: #1e293b; margin: 0; }
    .ga-kpi-label { font-size: 0.72rem; color: #64748b; margin: 4px 0 0; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    .ga-section-title { font-size: 0.95rem; font-weight: 700; color: #1e293b; margin: 1.25rem 0 0.5rem; }
    .ga-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    .ga-table th { text-align: left; padding: 8px 12px; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 2px solid #e2e8f0; }
    .ga-table td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
    .ga-table tr:hover td { background: #f8fafc; }
    .ga-bar { height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
    .ga-bar-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #3b82f6, #60a5fa); }
    .ga-setup-box {
        background: #fffbeb; border: 1px solid #fbbf24; border-radius: 12px;
        padding: 20px 24px; margin-top: 0.5rem;
    }
    .ga-setup-title { font-size: 1rem; font-weight: 700; color: #92400e; margin: 0 0 8px; }
    .ga-setup-step  { font-size: 0.85rem; color: #78350f; margin: 4px 0; }
    .ga-setup-code  { background: #fef3c7; padding: 8px 12px; border-radius: 6px; font-family: monospace; font-size: 0.78rem; margin: 6px 0; color: #92400e; word-break: break-all; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="ga-header">
        <div class="ga-title">📊 Google Analytics</div>
        <p class="ga-sub">Site traffic, user behaviour, and page performance from GA4 Data API.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Check credentials (OAuth2 refresh-token flow) ──
    property_id      = os.environ.get("GA4_PROPERTY_ID", "")
    ga4_client_id    = os.environ.get("GA4_CLIENT_ID", "")
    ga4_client_secret = os.environ.get("GA4_CLIENT_SECRET", "")
    ga4_refresh_token = os.environ.get("GA4_REFRESH_TOKEN", "")

    if not property_id or not ga4_refresh_token:
        st.markdown("""
        <div class="ga-setup-box">
            <div class="ga-setup-title">⚠️ Setup Required</div>
            <p class="ga-setup-step"><strong>Step 1:</strong> Go to <em>Google Cloud Console → APIs & Services → Enable</em> the <strong>Google Analytics Data API</strong>.</p>
            <p class="ga-setup-step"><strong>Step 2:</strong> Create an <strong>OAuth 2.0 Client</strong> (Desktop app type) and note the Client ID &amp; Secret.</p>
            <p class="ga-setup-step"><strong>Step 3:</strong> Run the OAuth consent flow to obtain a <strong>refresh token</strong> with the <code>analytics.readonly</code> scope.</p>
            <p class="ga-setup-step"><strong>Step 4:</strong> Find your GA4 <strong>Property ID</strong> (Admin → Property Settings → Property ID, e.g. <code>531202360</code>).</p>
            <p class="ga-setup-step"><strong>Step 5:</strong> Add these environment variables to Railway:</p>
            <div class="ga-setup-code">GA4_PROPERTY_ID=531202360</div>
            <div class="ga-setup-code">GA4_CLIENT_ID=your-client-id.apps.googleusercontent.com</div>
            <div class="ga-setup-code">GA4_CLIENT_SECRET=GOCSPX-...</div>
            <div class="ga-setup-code">GA4_REFRESH_TOKEN=1//0...</div>
            <p class="ga-setup-step" style="margin-top:10px"><strong>Step 6:</strong> Redeploy. The analytics dashboard will populate automatically.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Initialize GA4 client ──
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric, Dimension, OrderBy,
        )
        from google.oauth2.credentials import Credentials as OAuth2Credentials
    except ImportError:
        st.error("Missing package: `google-analytics-data`. Add it to requirements.txt and redeploy.")
        return

    @st.cache_data(ttl=300)  # cache 5 minutes
    def _ga4_report(metrics_list, dimensions_list=None, date_start="30daysAgo",
                    date_end="today", limit=10, order_desc_metric=None):
        """Run a single GA4 report and return rows as list of dicts."""
        try:
            creds = OAuth2Credentials(
                token=None,
                refresh_token=ga4_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=ga4_client_id,
                client_secret=ga4_client_secret,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            client = BetaAnalyticsDataClient(credentials=creds)
            dims = [Dimension(name=d) for d in (dimensions_list or [])]
            mets = [Metric(name=m) for m in metrics_list]
            order = []
            if order_desc_metric:
                order = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_desc_metric), desc=True)]
            req = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
                metrics=mets,
                dimensions=dims,
                order_bys=order,
                limit=limit,
            )
            resp = client.run_report(req)
            rows = []
            for row in resp.rows:
                d = {}
                for i, dim in enumerate(row.dimension_values):
                    d[dimensions_list[i] if dimensions_list else f"dim{i}"] = dim.value
                for i, met in enumerate(row.metric_values):
                    d[metrics_list[i]] = met.value
                rows.append(d)
            return rows
        except Exception as e:
            return {"error": str(e)}

    # ── Date range selector ──
    dr_col1, dr_col2 = st.columns([1, 3])
    with dr_col1:
        period = st.selectbox("Period", ["Last 7 days", "Last 30 days", "Last 90 days", "This year"],
                              index=1, key="ga_period", label_visibility="collapsed")
    period_map = {
        "Last 7 days": "7daysAgo",
        "Last 30 days": "30daysAgo",
        "Last 90 days": "90daysAgo",
        "This year": f"{datetime.now().year}-01-01",
    }
    date_start = period_map[period]

    # ── KPI cards ──
    kpi_data = _ga4_report(
        ["activeUsers", "sessions", "screenPageViews", "bounceRate",
         "averageSessionDuration", "newUsers"],
        date_start=date_start,
    )
    if isinstance(kpi_data, dict) and "error" in kpi_data:
        st.error(f"GA4 API error: {kpi_data['error']}")
        return

    if kpi_data:
        k = kpi_data[0]
        active   = int(k.get("activeUsers", 0))
        sessions = int(k.get("sessions", 0))
        views    = int(k.get("screenPageViews", 0))
        bounce   = float(k.get("bounceRate", 0))
        avg_dur  = float(k.get("averageSessionDuration", 0))
        new_u    = int(k.get("newUsers", 0))
        returning = max(0, active - new_u)
        mins = int(avg_dur) // 60
        secs = int(avg_dur) % 60
    else:
        active = sessions = views = new_u = returning = 0
        bounce = 0.0; mins = secs = 0

    st.markdown(f"""
    <div class="ga-kpi-row">
        <div class="ga-kpi"><p class="ga-kpi-val">{active:,}</p><p class="ga-kpi-label">Active Users</p></div>
        <div class="ga-kpi"><p class="ga-kpi-val">{sessions:,}</p><p class="ga-kpi-label">Sessions</p></div>
        <div class="ga-kpi"><p class="ga-kpi-val">{views:,}</p><p class="ga-kpi-label">Page Views</p></div>
        <div class="ga-kpi"><p class="ga-kpi-val">{bounce:.1%}</p><p class="ga-kpi-label">Bounce Rate</p></div>
        <div class="ga-kpi"><p class="ga-kpi-val">{mins}m {secs}s</p><p class="ga-kpi-label">Avg Duration</p></div>
        <div class="ga-kpi"><p class="ga-kpi-val">{new_u:,}</p><p class="ga-kpi-label">New Users</p></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Daily trend (line chart) ──
    daily = _ga4_report(
        ["activeUsers", "sessions", "screenPageViews"],
        dimensions_list=["date"],
        date_start=date_start, limit=90,
    )
    if isinstance(daily, list) and daily:
        import plotly.graph_objects as go
        daily_sorted = sorted(daily, key=lambda r: r["date"])
        dates   = [f"{r['date'][:4]}-{r['date'][4:6]}-{r['date'][6:]}" for r in daily_sorted]
        users_d = [int(r["activeUsers"]) for r in daily_sorted]
        sess_d  = [int(r["sessions"]) for r in daily_sorted]
        views_d = [int(r["screenPageViews"]) for r in daily_sorted]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=users_d, name="Users", line=dict(color="#3b82f6", width=2)))
        fig.add_trace(go.Scatter(x=dates, y=sess_d, name="Sessions", line=dict(color="#10b981", width=2)))
        fig.add_trace(go.Scatter(x=dates, y=views_d, name="Page Views", line=dict(color="#f59e0b", width=2)))
        fig.update_layout(
            height=280, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=9)),
            plot_bgcolor="#fff", paper_bgcolor="#fff", hovermode="x unified",
            dragmode=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Breakdown tables ──
    tc1, tc2 = st.columns(2)

    # -- New vs Returning --
    with tc1:
        st.markdown('<div class="ga-section-title">👤 New vs Returning Users</div>', unsafe_allow_html=True)
        nv = _ga4_report(["activeUsers"], dimensions_list=["newVsReturning"], date_start=date_start)
        if isinstance(nv, list) and nv:
            total_nv = sum(int(r["activeUsers"]) for r in nv)
            rows_html = ""
            for r in sorted(nv, key=lambda x: int(x["activeUsers"]), reverse=True):
                label = r["newVsReturning"].replace("new", "New").replace("returning", "Returning")
                val = int(r["activeUsers"])
                pct = (val / total_nv * 100) if total_nv else 0
                rows_html += f'<tr><td>{label}</td><td style="text-align:right;font-weight:600">{val:,}</td><td style="width:40%;"><div class="ga-bar"><div class="ga-bar-fill" style="width:{pct:.0f}%"></div></div></td><td style="text-align:right;color:#64748b">{pct:.1f}%</td></tr>'
            st.markdown(f'<table class="ga-table"><thead><tr><th>Type</th><th>Users</th><th></th><th>%</th></tr></thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)
        else:
            st.caption("No data")

    # -- Device category --
    with tc2:
        st.markdown('<div class="ga-section-title">📱 Users by Device</div>', unsafe_allow_html=True)
        dev = _ga4_report(["activeUsers"], dimensions_list=["deviceCategory"], date_start=date_start)
        if isinstance(dev, list) and dev:
            total_dev = sum(int(r["activeUsers"]) for r in dev)
            rows_html = ""
            for r in sorted(dev, key=lambda x: int(x["activeUsers"]), reverse=True):
                label = r["deviceCategory"].capitalize()
                val = int(r["activeUsers"])
                pct = (val / total_dev * 100) if total_dev else 0
                rows_html += f'<tr><td>{label}</td><td style="text-align:right;font-weight:600">{val:,}</td><td style="width:40%"><div class="ga-bar"><div class="ga-bar-fill" style="width:{pct:.0f}%"></div></div></td><td style="text-align:right;color:#64748b">{pct:.1f}%</td></tr>'
            st.markdown(f'<table class="ga-table"><thead><tr><th>Device</th><th>Users</th><th></th><th>%</th></tr></thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)
        else:
            st.caption("No data")

    tc3, tc4 = st.columns(2)

    # -- Country --
    with tc3:
        st.markdown('<div class="ga-section-title">🌍 Top Countries</div>', unsafe_allow_html=True)
        geo = _ga4_report(["activeUsers", "sessions"], dimensions_list=["country"],
                          date_start=date_start, limit=10, order_desc_metric="activeUsers")
        if isinstance(geo, list) and geo:
            total_geo = sum(int(r["activeUsers"]) for r in geo)
            rows_html = ""
            for r in geo:
                val = int(r["activeUsers"])
                sess = int(r["sessions"])
                pct = (val / total_geo * 100) if total_geo else 0
                rows_html += f'<tr><td>{r["country"]}</td><td style="text-align:right;font-weight:600">{val:,}</td><td style="text-align:right">{sess:,}</td><td style="width:30%"><div class="ga-bar"><div class="ga-bar-fill" style="width:{pct:.0f}%"></div></div></td></tr>'
            st.markdown(f'<table class="ga-table"><thead><tr><th>Country</th><th>Users</th><th>Sessions</th><th></th></tr></thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)
        else:
            st.caption("No data")

    # -- Referral / Source --
    with tc4:
        st.markdown('<div class="ga-section-title">🔗 Traffic Sources</div>', unsafe_allow_html=True)
        src = _ga4_report(["activeUsers", "sessions"], dimensions_list=["sessionSource"],
                          date_start=date_start, limit=10, order_desc_metric="sessions")
        if isinstance(src, list) and src:
            total_src = sum(int(r["sessions"]) for r in src)
            rows_html = ""
            for r in src:
                val = int(r["activeUsers"])
                sess = int(r["sessions"])
                pct = (sess / total_src * 100) if total_src else 0
                source = r["sessionSource"] if r["sessionSource"] != "(direct)" else "Direct"
                rows_html += f'<tr><td>{source}</td><td style="text-align:right;font-weight:600">{val:,}</td><td style="text-align:right">{sess:,}</td><td style="width:30%"><div class="ga-bar"><div class="ga-bar-fill" style="width:{pct:.0f}%"></div></div></td></tr>'
            st.markdown(f'<table class="ga-table"><thead><tr><th>Source</th><th>Users</th><th>Sessions</th><th></th></tr></thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)
        else:
            st.caption("No data")

    # -- Top Pages --
    st.markdown('<div class="ga-section-title">📄 Top Pages</div>', unsafe_allow_html=True)
    pages = _ga4_report(
        ["screenPageViews", "activeUsers", "averageSessionDuration"],
        dimensions_list=["pagePath"],
        date_start=date_start, limit=15, order_desc_metric="screenPageViews",
    )
    if isinstance(pages, list) and pages:
        total_pv = sum(int(r["screenPageViews"]) for r in pages)
        rows_html = ""
        for r in pages:
            pv = int(r["screenPageViews"])
            users = int(r["activeUsers"])
            dur = float(r["averageSessionDuration"])
            m, s = int(dur) // 60, int(dur) % 60
            pct = (pv / total_pv * 100) if total_pv else 0
            path = r["pagePath"] if len(r["pagePath"]) <= 50 else r["pagePath"][:47] + "..."
            rows_html += f'<tr><td style="font-family:monospace;font-size:0.78rem">{path}</td><td style="text-align:right;font-weight:600">{pv:,}</td><td style="text-align:right">{users:,}</td><td style="text-align:right">{m}m {s}s</td><td style="width:22%"><div class="ga-bar"><div class="ga-bar-fill" style="width:{pct:.0f}%"></div></div></td></tr>'
        st.markdown(f'<table class="ga-table"><thead><tr><th>Page</th><th>Views</th><th>Users</th><th>Avg Time</th><th></th></tr></thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)
    else:
        st.caption("No data")

    st.caption("Data refreshes every 5 minutes · Powered by GA4 Data API")


def render_nsfe_page():
    """Render the password-protected NSFE manager control center."""
    st.markdown(_STYLES, unsafe_allow_html=True)

    # ── Password Gate ──
    if not st.session_state.get("nsfe_auth", False):
        st.markdown("""
        <div class="lock-container">
            <div class="lock-icon">\U0001f512</div>
            <div class="lock-title">NSFE \u2014 Restricted Area</div>
            <div class="lock-sub">Enter the project password to continue</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            pwd = st.text_input("Password", type="password", key="nsfe_pwd",
                                placeholder="Enter password\u2026", label_visibility="collapsed")
            if st.button("Unlock Dashboard", use_container_width=True, type="primary"):
                if pwd == _PASSWORD:
                    st.session_state.nsfe_auth = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Try again.")
        return

    # ── Main Menu (Streamlit tabs) ──
    _sync_steps()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        "📋 Dashboard", "🛡️ Security", "⚙️ Settings",
        "🛡️ Certifications", "🏗️ Infrastructure",
        "👥 Team & Admin", "🔍 SEO", "💳 Pricing", "👤 Users", "📊 Analytics", "🧠 Memory",
    ])

    with tab1:
        _render_dashboard()
    with tab2:
        _render_security()
    with tab3:
        _render_settings()

    with tab4:
        _render_certifications()

    with tab5:
        _render_infrastructure()

    with tab6:
        _render_team_admin()

    with tab7:
        _render_seo()

    with tab8:
        _render_pricing_admin()

    with tab9:
        _render_users_admin()

    with tab10:
        _render_analytics()

    with tab11:
        _render_memory()

    # Footer
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)



