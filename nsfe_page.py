"""
NSFE â Manager Control Center (password-protected).
Main menu with: Dashboard, Security, Settings, AI Assistant
"""

import streamlit as st
import os
import json
from datetime import datetime

# ââ Config ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
_PASSWORD = "nppQC091011"

# ââ Phase 2 Task Data âââââââââââââââââââââââââââââââââââââââââââââââââââ
STEPS = [
    {
        "num": 1,
        "title": "Authentication System (Firebase Auth)",
        "icon": "\U0001f510",
        "color": "#10B981",
        "substeps": [
            {"id": "1A", "name": "Firebase Project Setup",   "status": "pending",
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
            {"id": "2A", "name": "Railway PostgreSQL Setup",  "status": "pending",
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
            {"id": "4A", "name": "Environment Variables",     "status": "pending",
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
            {"id": "5A", "name": "Wire Auth into Main App",   "status": "pending",
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
            {"id": "9B", "name": "ISO 27001 / SOC 2 Roadmap", "status": "pending",
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
            {"id": "10A", "name": "Team Management UI",      "status": "pending",
             "details": "Invite by email, role assignment dropdown, member list with badges, remove/deactivate, ownership transfer"},
            {"id": "10B", "name": "Admin Dashboard",          "status": "pending",
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


# ââ Security Issues Data ââââââââââââââââââââââââââââââââââââââââââââââ
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

# ââ Compliance Data âââââââââââââââââââââââââââââââââââââââââââââââââââ
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


# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# HELPER FUNCTIONS
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

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
        "done":     "DONE: This task is fully completed, tested, and verified. The code is live on the website and working in production.",
        "partial":  "IN PROGRESS: Active development is underway. Some subtasks are finished but others still need work. Check subtasks for details.",
        "pending":  "PENDING: This task has not been started yet. It is planned and waiting for prerequisite steps to be completed first.",
        "deferred": "DEFERRED: Postponed to a future phase. Not needed for MVP launch but planned for later development.",
        "future":   "FUTURE: Optional enhancement planned for a later milestone. These are nice-to-have features, not required for launch.",
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
        "critical": "CRITICAL: Requires immediate action. The system is at serious risk of exploitation. Fix before any new feature work.",
        "high":     "HIGH: Should be addressed urgently within the current sprint. Significant security impact if exploited.",
        "medium":   "MEDIUM: Plan remediation for the next sprint. Moderate risk that should be tracked and scheduled.",
        "low":      "LOW: Minor issue with limited impact. Fix when convenient or during regular maintenance cycles.",
        "info":     "INFO: Informational finding for awareness. No immediate action needed but good to track for future reference.",
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


# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# MAIN STYLES
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

_STYLES = """
<style>
[data-testid="stSidebar"] { display: none !important; }
section[data-testid="stMain"] > div { padding-top: 0 !important; }
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


# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# PAGE RENDERERS
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

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
            {_progress_bar(overall_pct, '#3B82F6', 'Overall completion percentage across all 10 implementation steps. Computed automatically from substep statuses.')}
        </div>
        <div class="metrics-row">
            {_metric_card(done_count, "Completed", "#10B981",
                "Steps fully finished: all subtasks are done, code is deployed and working on quartercharts.com.")}
            {_metric_card(partial_count, "In Progress", "#F59E0B",
                "Steps with some subtasks done but others still pending. Active development is underway.")}
            {_metric_card(pending_count, "Pending", "#6B7280",
                "Steps not started yet. Waiting for prerequisite steps to be completed first.")}
            {_metric_card(deferred_count, "Deferred", "#6366F1",
                "Steps postponed to a future development phase. Not needed for MVP launch.")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    for step in STEPS:
        badge = _status_badge(step["status"])
        bar   = _progress_bar(step["progress"], step["color"],
            f'Step {step["num"]} progress: {step["progress"]}% complete. This is auto-calculated from the status of each subtask below.')
        st.markdown(f"""
        <div class="step-card">
            <div class="step-header">
                <div class="step-icon" style="background:{step['color']}22;">{step['icon']}</div>
                <div>
                    <span class="step-num">STEP {step['num']}{_info_tip(
                        f'Step {step["num"]} of 10 in the Phase 2 roadmap. '
                        f'Status is auto-computed: a step shows Done only when ALL its subtasks are done.'
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
                        "Implementation details: describes the specific work items, technologies, and deliverables for this subtask."
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
        f'<div class="impl-order"><h3>\U0001f4cb Implementation Order{_info_tip("Recommended sequence for building the platform. Checked items are already coded and in the repo. Unchecked items are next priorities.")}</h3>{items_html}</div>',
        unsafe_allow_html=True,
    )


def _render_security():
    """Security issues tracker and compliance dashboard."""
    # ââ Summary metrics ââ
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
                "Count of CRITICAL severity issues. These need immediate action before any new feature development.")}
            {_metric_card(high, "High", "#EA580C",
                "Count of HIGH severity issues. Should be resolved within the current development sprint.")}
            {_metric_card(medium, "Medium", "#D97706",
                "Count of MEDIUM severity issues. Schedule remediation in the next sprint.")}
            {_metric_card(low_info, "Low / Info", "#2563EB",
                "Count of LOW and INFO findings. Minor issues or informational notes for awareness.")}
            {_metric_card(open_count, "Open", "#EF4444",
                "Total unresolved issues still needing action. Goal: bring this to zero.")}
            {_metric_card(mitigated, "Mitigated", "#F59E0B",
                "Issues with temporary workarounds in place. Still need permanent fixes.")}
            {_metric_card(resolved, "Resolved", "#10B981",
                "Issues fully fixed, tested, and verified in production.")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ââ Filter ââ
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

    # ââ Issue Cards ââ
    st.markdown(f"#### Showing {len(filtered)} of {total} issues")
    for issue in filtered:
        sev  = _severity_badge(issue["severity"])
        stat = _status_badge(issue["status"])
        st.markdown(f"""
        <div class="sec-card">
            <div class="sec-card-header">
                <span class="sec-card-id">{issue['id']}{_info_tip(
                    f'Security issue {issue["id"]}. Unique identifier for tracking. Found on {issue["date_found"]}.'
                )}</span>
                {sev}
                <span class="sec-card-title">{issue['title']}{_info_tip(
                    f'What: {issue["description"]} How to fix: {issue["recommendation"]}'
                )}</span>
                {stat}
            </div>
            <span class="sec-card-cat">{issue['category']}{_info_tip(
                f'Security category: {issue["category"]}. Used for grouping related issues and mapping to ISO 27001 controls.'
            )}</span>
            <span style="font-size:0.75rem;color:#475569;margin-left:12px;">Found: {issue['date_found']}</span>
            <span style="font-size:0.75rem;color:#475569;margin-left:12px;">Affected: {issue['affected']}{_info_tip(
                f'Components impacted: {issue["affected"]}. These areas need attention when implementing the fix.'
            )}</span>
            <div class="sec-card-body">{issue['description']}</div>
            <div class="sec-card-rec">\U0001f4a1 <strong>Recommendation:</strong>{_info_tip(
                "Actionable recommendation from the security audit. Follow these steps to resolve or mitigate the issue."
            )} {issue['recommendation']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ââ ISO 27001 Compliance ââ
    st.markdown("---")
    st.markdown("### \U0001f3db\ufe0f ISO 27001 Control Status")
    overall_iso = sum(c["progress"] for c in ISO_CONTROLS) // len(ISO_CONTROLS)
    st.markdown(f"""
    <div style="max-width:500px;margin:0 auto 24px;">
        <div style="text-align:center;font-size:0.85rem;color:#94A3B8;margin-bottom:4px;">
            Overall ISO 27001 Readiness: <strong style="color:#F8FAFC;">{overall_iso}%</strong>
            {_info_tip("ISO 27001 readiness score. Measures how many of the required security controls have been implemented. Target: 100% for certification.")}
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
                    f'ISO 27001 Annex A control {ctrl["id"]}. This is an international standard requirement for information security management.'
                )}</span>
                <span class="compliance-name">{ctrl['name']}{_info_tip(
                    f'Control area: {ctrl["name"]}. Covers: {ctrl["details"]}. Progress: {ctrl["progress"]}%.'
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
            "Settings page: quick links to service dashboards, repository info, and system configuration. Use these to manage your platform services."
        )}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### \U0001f517 Quick Links" + _info_tip("Direct links to your key service dashboards. Click the buttons below to open each service in a new tab."), unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">\U0001f525</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Firebase Console{_info_tip(
                "Firebase: handles user authentication (login, signup, password reset). Manages Email/Password and Google SSO sign-in methods. Go here to manage users, view auth logs, and configure sign-in providers."
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
                "Railway: hosts the backend (Streamlit app) and PostgreSQL database. Go here to view deploy logs, set environment variables (API keys, DB URL), monitor resource usage, and trigger redeployments."
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
                "Stripe: payment processing for subscriptions and billing (Step 6 - currently deferred). Will handle checkout, customer portal, webhooks, and plan enforcement once implemented."
            )}</div>
            <div style="font-size:0.8rem;color:#64748B;">Billing, subscriptions</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Stripe", "https://dashboard.stripe.com", use_container_width=True)

    st.markdown("---")
    st.markdown("### \U0001f4e6 Repository" + _info_tip("Source code repository and live deployment. The app auto-deploys from the GitHub main branch to Railway."), unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">\U0001f419</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">GitHub Repository{_info_tip(
                "GitHub repo: miteproyects/opensankey. Contains all source code, issues, and pull requests. Pushing to main branch triggers auto-deploy to Railway."
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
                "The live production website at quartercharts.com. Hosted on Streamlit Cloud, auto-deploys from GitHub main branch. This is what end users see."
            )}</div>
            <div style="font-size:0.8rem;color:#64748B;">quartercharts.com</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Live Site", "https://quartercharts.com", use_container_width=True)

    st.markdown("---")
    st.markdown("### \u26a1 System Info" + _info_tip("Current platform configuration and tech stack. Shows the services and tools powering QuarterCharts."), unsafe_allow_html=True)
    st.markdown(f"""
    <div class="step-card">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div><span style="color:#64748B;font-size:0.85rem;">Platform:{_info_tip("Streamlit serves the frontend UI, Railway hosts the backend and database.")}</span> <span style="color:#F1F5F9;">Streamlit + Railway</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Database:{_info_tip("PostgreSQL hosted on Railway. Stores users, companies, audit logs. Connection via DATABASE_URL env var.")}</span> <span style="color:#F1F5F9;">PostgreSQL (Railway)</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Auth:{_info_tip("Firebase Authentication handles user login, signup, and session management. Supports Email/Password and Google SSO.")}</span> <span style="color:#F1F5F9;">Firebase Auth</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Payments:{_info_tip("Stripe integration is planned for Step 6. Will handle subscription billing, checkout, and customer portal.")}</span> <span style="color:#F1F5F9;">Stripe (planned)</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Domain:{_info_tip("The public-facing domain. Users access the platform at this URL.")}</span> <span style="color:#F1F5F9;">quartercharts.com</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Auto-deploy:{_info_tip("Every push to the main branch on GitHub automatically triggers a redeployment on Railway. No manual deploy needed.")}</span> <span style="color:#10B981;">GitHub main \u2192 Railway</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Target:{_info_tip("Business goal: reach $50K annual recurring revenue from B2B SaaS subscriptions for financial visualization tools.")}</span> <span style="color:#F1F5F9;">$50K/year B2B SaaS</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">NSFE Password:{_info_tip("This admin dashboard is protected by a password gate. Only authorized managers can access it.")}</span> <span style="color:#F59E0B;">Active</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# AI ASSISTANT TAB
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

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
            "AI chat assistant powered by the Claude API (Anthropic). Ask questions about QuarterCharts architecture, implementation, security, or strategy. Requires an ANTHROPIC_API_KEY env var set in Railway."
        )}</p>
        <p>Claude-powered assistant &nbsp;\u00b7&nbsp; Ask anything about QuarterCharts</p>
    </div>
    """, unsafe_allow_html=True)

    # ââ API Key check ââ
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.warning("\u27a1\ufe0f **Anthropic API key not configured.**")
        st.markdown(f"""
        <div class="step-card">
            <h4 style="color:#F1F5F9;margin:0 0 12px;">Setup Instructions{_info_tip(
                "To enable AI chat, you need an Anthropic API key. Create one at console.anthropic.com, then add it as an environment variable in your Railway deployment settings."
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
            "Preview mode: messages are saved locally but not sent to Claude. Once you add the API key and redeploy, the AI will respond in real-time."
        ), unsafe_allow_html=True)
        st.info("You can still use this interface to draft messages. They will be processed once the API key is set.")

    # ââ Chat history in session state ââ
    if "nsfe_chat_history" not in st.session_state:
        st.session_state.nsfe_chat_history = []

    # ââ Display conversation ââ
    for msg in st.session_state.nsfe_chat_history:
        with st.chat_message(msg["role"], avatar="\U0001f9d1\u200d\U0001f4bc" if msg["role"] == "user" else "\U0001f916"):
            st.markdown(msg["content"])

    # ââ Chat input ââ
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

    # ââ Sidebar: Quick prompts ââ
    st.markdown("---")
    st.markdown("#### \u26a1 Quick Prompts" + _info_tip(
        "Pre-written questions to quickly start a conversation with the AI assistant. Click any prompt to send it."
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

    # ââ Clear chat ââ
    st.markdown("---")
    if st.button("\U0001f5d1\ufe0f Clear Chat History", type="secondary"):
        st.session_state.nsfe_chat_history = []
        st.rerun()


# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# MAIN ENTRY POINT
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def render_nsfe_page():
    """Render the password-protected NSFE manager control center."""
    st.markdown(_STYLES, unsafe_allow_html=True)

    # ââ Password Gate ââ
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

    # ââ Main Menu (Streamlit tabs) ââ
    tab1, tab2, tab3, tab4 = st.tabs([
        "\U0001f4cb Dashboard",
        "\U0001f6e1\ufe0f Security",
        "\u2699\ufe0f Settings",
        "\U0001f916 AI Assistant",
    ])

    with tab1:
        _render_dashboard()
    with tab2:
        _render_security()
    with tab3:
        _render_settings()
    with tab4:
        _render_chat()

    # Footer
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
