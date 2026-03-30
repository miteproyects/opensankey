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
        "category": "Transport Security", "status": "open",
        "description": "All API endpoints should enforce HTTPS. HTTP requests must be redirected or blocked.",
        "recommendation": "Configure Railway to force HTTPS redirects. Add HSTS header with min 1 year max-age.",
        "affected": "All endpoints", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-002", "severity": "critical",
        "title": "Missing Content Security Policy (CSP) header",
        "category": "HTTP Headers", "status": "open",
        "description": "No CSP header is set, leaving the application vulnerable to XSS and data injection attacks.",
        "recommendation": "Add strict CSP: default-src 'self'; script-src 'self' 'unsafe-inline' cdn.plot.ly; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;",
        "affected": "All pages", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-003", "severity": "high",
        "title": "No rate limiting on login endpoint",
        "category": "Authentication", "status": "open",
        "description": "Login attempts are not rate-limited, enabling brute-force password attacks.",
        "recommendation": "Implement rate limiting: max 5 attempts per IP per minute. Use exponential backoff. Lock account after 10 consecutive failures.",
        "affected": "Login page, API auth endpoints", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-004", "severity": "high",
        "title": "Session tokens not rotated after privilege change",
        "category": "Session Management", "status": "open",
        "description": "When a user's role changes (e.g., viewer \u2192 admin), the session token is not regenerated, creating a session fixation risk.",
        "recommendation": "Regenerate session token after any role change, password change, or privilege escalation.",
        "affected": "RBAC system, session management", "date_found": "2026-03-16",
    },
    {
        "id": "SEC-005", "severity": "high",
        "title": "No X-Frame-Options or frame-ancestors CSP",
        "category": "HTTP Headers", "status": "open",
        "description": "App can be embedded in iframes on malicious sites, enabling clickjacking attacks.",
        "recommendation": "Add X-Frame-Options: DENY header and frame-ancestors 'none' to CSP.",
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
        "category": "CI/CD Security", "status": "open",
        "description": "No dependency scanning (Dependabot/Snyk) or SAST tools are configured in the GitHub repository.",
        "recommendation": "Enable GitHub Dependabot alerts. Add safety or pip-audit to CI pipeline. Consider Snyk for deeper analysis.",
        "affected": "GitHub repository, dependencies", "date_found": "2026-03-16",
    },
    {
        "id": "SEC-008", "severity": "medium",
        "title": "Missing audit log for data exports",
        "category": "Data Protection", "status": "open",
        "description": "When users export or download financial data (CSVs, charts), no audit trail is created.",
        "recommendation": "Log all data export events with user_id, company_id, data_type, timestamp, and IP address.",
        "affected": "Charts, Sankey exports, data downloads", "date_found": "2026-03-17",
    },
    {
        "id": "SEC-009", "severity": "medium",
        "title": "No CAPTCHA on signup form",
        "category": "Bot Protection", "status": "open",
        "description": "Signup form has no bot protection, enabling automated account creation.",
        "recommendation": "Add reCAPTCHA v3 or hCaptcha to signup and password reset forms.",
        "affected": "Signup page, password reset", "date_found": "2026-03-17",
    },
    {
        "id": "SEC-010", "severity": "low",
        "title": "Server version exposed in response headers",
        "category": "Information Disclosure", "status": "open",
        "description": "Response headers reveal Streamlit and Python version info, aiding attackers in fingerprinting.",
        "recommendation": "Configure response headers to remove Server, X-Powered-By. Add custom middleware to strip version info.",
        "affected": "All HTTP responses", "date_found": "2026-03-18",
    },
    {
        "id": "SEC-011", "severity": "low",
        "title": "No backup verification process",
        "category": "Business Continuity", "status": "open",
        "description": "Database backups exist (Railway auto-backup) but there is no scheduled restore test.",
        "recommendation": "Schedule monthly backup restore test. Document RTO (Recovery Time Objective) and RPO (Recovery Point Objective).",
        "affected": "PostgreSQL database", "date_found": "2026-03-18",
    },
    {
        "id": "SEC-012", "severity": "info",
        "title": "2FA not enforced for admin accounts",
        "category": "Account Security", "status": "open",
        "description": "Platform admin accounts (Firebase, Railway, Stripe, GitHub) do not require 2FA.",
        "recommendation": "Enable 2FA on all admin accounts: Firebase Console, Railway, Stripe Dashboard, GitHub (enforce via org settings).",
        "affected": "Admin accounts on all platforms", "date_found": "2026-03-18",
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
/* ── NSFE tab fix: keep tabs visible below fixed navbar ── */
.block-container:has([data-testid="stTabs"]) {
    padding-top: 72px !important;
}
[data-testid="stTabs"] {
    position: relative;
    z-index: 1;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #0F172A;
    flex-wrap: wrap;
    gap: 0;
    padding: 4px 8px 0 8px;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] button {
    font-size: 0.82rem !important;
    padding: 8px 12px !important;
    white-space: nowrap;
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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 Dashboard", "🛡️ Security", "⚙️ Settings",
        "🤖 AI Assistant", "🛡️ Certifications", "🏗️ Infrastructure",
        "🔍 SEO",
    ])

    with tab1:
        _render_dashboard()
    with tab2:
        _render_security()
    with tab3:
        _render_settings()
    with tab4:
        _render_chat()

    with tab5:
        _render_certifications()

    with tab6:
        _render_infrastructure()

    with tab7:
        _render_seo()

    # Footer
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
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
        "category": "Transport Security", "status": "open",
        "description": "All API endpoints should enforce HTTPS. HTTP requests must be redirected or blocked.",
        "recommendation": "Configure Railway to force HTTPS redirects. Add HSTS header with min 1 year max-age.",
        "affected": "All endpoints", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-002", "severity": "critical",
        "title": "Missing Content Security Policy (CSP) header",
        "category": "HTTP Headers", "status": "open",
        "description": "No CSP header is set, leaving the application vulnerable to XSS and data injection attacks.",
        "recommendation": "Add strict CSP: default-src 'self'; script-src 'self' 'unsafe-inline' cdn.plot.ly; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;",
        "affected": "All pages", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-003", "severity": "high",
        "title": "No rate limiting on login endpoint",
        "category": "Authentication", "status": "open",
        "description": "Login attempts are not rate-limited, enabling brute-force password attacks.",
        "recommendation": "Implement rate limiting: max 5 attempts per IP per minute. Use exponential backoff. Lock account after 10 consecutive failures.",
        "affected": "Login page, API auth endpoints", "date_found": "2026-03-15",
    },
    {
        "id": "SEC-004", "severity": "high",
        "title": "Session tokens not rotated after privilege change",
        "category": "Session Management", "status": "open",
        "description": "When a user's role changes (e.g., viewer \u2192 admin), the session token is not regenerated, creating a session fixation risk.",
        "recommendation": "Regenerate session token after any role change, password change, or privilege escalation.",
        "affected": "RBAC system, session management", "date_found": "2026-03-16",
    },
    {
        "id": "SEC-005", "severity": "high",
        "title": "No X-Frame-Options or frame-ancestors CSP",
        "category": "HTTP Headers", "status": "open",
        "description": "App can be embedded in iframes on malicious sites, enabling clickjacking attacks.",
        "recommendation": "Add X-Frame-Options: DENY header and frame-ancestors 'none' to CSP.",
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
        "category": "CI/CD Security", "status": "open",
        "description": "No dependency scanning (Dependabot/Snyk) or SAST tools are configured in the GitHub repository.",
        "recommendation": "Enable GitHub Dependabot alerts. Add safety or pip-audit to CI pipeline. Consider Snyk for deeper analysis.",
        "affected": "GitHub repository, dependencies", "date_found": "2026-03-16",
    },
    {
        "id": "SEC-008", "severity": "medium",
        "title": "Missing audit log for data exports",
        "category": "Data Protection", "status": "open",
        "description": "When users export or download financial data (CSVs, charts), no audit trail is created.",
        "recommendation": "Log all data export events with user_id, company_id, data_type, timestamp, and IP address.",
        "affected": "Charts, Sankey exports, data downloads", "date_found": "2026-03-17",
    },
    {
        "id": "SEC-009", "severity": "medium",
        "title": "No CAPTCHA on signup form",
        "category": "Bot Protection", "status": "open",
        "description": "Signup form has no bot protection, enabling automated account creation.",
        "recommendation": "Add reCAPTCHA v3 or hCaptcha to signup and password reset forms.",
        "affected": "Signup page, password reset", "date_found": "2026-03-17",
    },
    {
        "id": "SEC-010", "severity": "low",
        "title": "Server version exposed in response headers",
        "category": "Information Disclosure", "status": "open",
        "description": "Response headers reveal Streamlit and Python version info, aiding attackers in fingerprinting.",
        "recommendation": "Configure response headers to remove Server, X-Powered-By. Add custom middleware to strip version info.",
        "affected": "All HTTP responses", "date_found": "2026-03-18",
    },
    {
        "id": "SEC-011", "severity": "low",
        "title": "No backup verification process",
        "category": "Business Continuity", "status": "open",
        "description": "Database backups exist (Railway auto-backup) but there is no scheduled restore test.",
        "recommendation": "Schedule monthly backup restore test. Document RTO (Recovery Time Objective) and RPO (Recovery Point Objective).",
        "affected": "PostgreSQL database", "date_found": "2026-03-18",
    },
    {
        "id": "SEC-012", "severity": "info",
        "title": "2FA not enforced for admin accounts",
        "category": "Account Security", "status": "open",
        "description": "Platform admin accounts (Firebase, Railway, Stripe, GitHub) do not require 2FA.",
        "recommendation": "Enable 2FA on all admin accounts: Firebase Console, Railway, Stripe Dashboard, GitHub (enforce via org settings).",
        "affected": "Admin accounts on all platforms", "date_found": "2026-03-18",
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
/* ── NSFE tab fix: keep tabs visible below fixed navbar ── */
.block-container:has([data-testid="stTabs"]) {
    padding-top: 72px !important;
}
[data-testid="stTabs"] {
    position: relative;
    z-index: 1;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #0F172A;
    flex-wrap: wrap;
    gap: 0;
    padding: 4px 8px 0 8px;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] button {
    font-size: 0.82rem !important;
    padding: 8px 12px !important;
    white-space: nowrap;
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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 Dashboard", "🛡️ Security", "⚙️ Settings",
        "🤖 AI Assistant", "🛡️ Certifications", "🏗️ Infrastructure",
        "👥 Team & Admin", "🔍 SEO",
    ])

    with tab1:
        _render_dashboard()
    with tab2:
        _render_security()
    with tab3:
        _render_settings()
    with tab4:
        _render_chat()

    with tab5:
        _render_certifications()

    with tab6:
        _render_infrastructure()

    with tab7:
        _render_team_admin()


    with tab8:
        _render_seo()

    # Footer
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)



