"""
NSFE – Manager Control Center (password-protected).
Main menu with: Dashboard, Security, Settings
"""

import streamlit as st
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
_PASSWORD = "nppQC091011"

# ── Phase 2 Task Data ───────────────────────────────────────────────────
STEPS = [
    {
        "num": 1,
        "title": "Authentication System (Firebase Auth)",
        "icon": "🔐",
        "color": "#10B981",
        "status": "done",
        "progress": 100,
        "substeps": [
            {"id": "1A", "name": "Firebase Project Setup", "status": "pending",
             "details": "Create Firebase project, enable Email/Password + Google SSO, add authorized domain, generate service account key"},
            {"id": "1B", "name": "Auth Backend (auth.py)", "status": "done",
             "details": "Firebase Admin SDK init, JWT verification, user creation, password reset, session management, demo mode fallback"},
            {"id": "1C", "name": "Auth UI (login_page.py)", "status": "done",
             "details": "Email/password login, Google SSO button, signup toggle, validation, Firebase REST API, error mapping"},
            {"id": "1D", "name": "Future Options", "status": "future",
             "details": "Magic link login · Phone SMS OTP · Microsoft/Apple/GitHub SSO · MFA (TOTP) · Custom JWT claims · Session cookies"},
        ],
    },
    {
        "num": 2,
        "title": "Database Layer (PostgreSQL)",
        "icon": "🗄️",
        "color": "#3B82F6",
        "status": "done",
        "progress": 100,
        "substeps": [
            {"id": "2A", "name": "Railway PostgreSQL Setup", "status": "pending",
             "details": "Create PostgreSQL database in Railway, copy DATABASE_URL, schema auto-creates on startup"},
            {"id": "2B", "name": "Database Module (database.py)", "status": "done",
             "details": "Connection pooling, users/companies/audit_log schema, CRUD operations, parameterized queries, multi-tenant isolation"},
            {"id": "2C", "name": "Future Options", "status": "future",
             "details": "Supabase · SQLAlchemy ORM · Row-Level Security · Read replicas · Alembic migrations · Redis cache · Encrypted columns"},
        ],
    },
    {
        "num": 3,
        "title": "Role-Based Access Control",
        "icon": "👥",
        "color": "#8B5CF6",
        "status": "done",
        "progress": 100,
        "substeps": [
            {"id": "3A", "name": "RBAC Module (rbac.py)", "status": "done",
             "details": "5 roles (owner→viewer), granular permissions, guard functions, role hierarchy, display helpers"},
            {"id": "3B", "name": "Future Options", "status": "future",
             "details": "ABAC · Custom roles · Temporary access · Permission delegation · IP restrictions"},
        ],
    },
    {
        "num": 4,
        "title": "Environment & Deployment",
        "icon": "🚀",
        "color": "#F59E0B",
        "status": "partial",
        "progress": 60,
        "substeps": [
            {"id": "4A", "name": "Environment Variables", "status": "pending",
             "details": "FIREBASE_CREDENTIALS, FIREBASE_CONFIG, DATABASE_URL on Railway"},
            {"id": "4B", "name": "Railway Deployment", "status": "done",
             "details": "Auto-detect requirements.txt, PostgreSQL in same project, DATABASE_URL auto-linked"},
            {"id": "4C", "name": "Future Options", "status": "future",
             "details": "Docker · Vercel/Fly.io/Render · GitHub Actions CI/CD · Staging env · Secrets Manager · Custom domain SSL"},
        ],
    },
    {
        "num": 5,
        "title": "App Integration (app.py)",
        "icon": "🔗",
        "color": "#EC4899",
        "status": "pending",
        "progress": 0,
        "substeps": [
            {"id": "5A", "name": "Wire Auth into Main App", "status": "pending",
             "details": "Import auth/db modules, init session state, update nav bar, route /login, protect pages with require_auth()"},
            {"id": "5B", "name": "Future Options", "status": "future",
             "details": "Middleware decorator · FastAPI backend · WebSocket session sync"},
        ],
    },
    {
        "num": 6,
        "title": "Payment & Billing (Stripe)",
        "icon": "💳",
        "color": "#6366F1",
        "status": "deferred",
        "progress": 0,
        "substeps": [
            {"id": "6A", "name": "Stripe Integration", "status": "deferred",
             "details": "Stripe Checkout, Customer Portal, webhooks, link to company record, plan enforcement"},
            {"id": "6B", "name": "Pricing Tiers", "status": "deferred",
             "details": "Free (1 user) · Basic ($X/mo, 5 users) · Pro ($X/mo, 25 users) · Enterprise (unlimited)"},
            {"id": "6C", "name": "Implementation Files", "status": "deferred",
             "details": "billing.py · billing_page.py · webhooks.py · DB updates · RBAC plan gating"},
            {"id": "6D", "name": "Future Options", "status": "future",
             "details": "Stripe Elements · Metered billing · Annual discount · LATAM payments (Kushki) · Invoice billing · Free trial"},
        ],
    },
    {
        "num": 7,
        "title": "Data Upload & Processing",
        "icon": "📤",
        "color": "#14B8A6",
        "status": "pending",
        "progress": 0,
        "substeps": [
            {"id": "7A", "name": "SRI Invoice Upload", "status": "pending",
             "details": "XML/CSV upload UI, SRI electronic invoice parser, RUC validation, store with company_id, audit log"},
            {"id": "7B", "name": "Financial Data Processing", "status": "pending",
             "details": "Transaction categorization, tax summaries (IVA/retenciones/ICE), aggregation, multi-format support"},
            {"id": "7C", "name": "Future Options", "status": "future",
             "details": "Direct SRI API · OCR for scanned invoices · Bank statement import · ML auto-categorization · Real-time sync · Rules engine"},
        ],
    },
    {
        "num": 8,
        "title": "Dashboard & Visualization",
        "icon": "📊",
        "color": "#F97316",
        "status": "partial",
        "progress": 40,
        "substeps": [
            {"id": "8A", "name": "Enhanced Charts", "status": "partial",
             "details": "Sankey diagrams ✓ · Stock charts ✓ · Invoice volume (TODO) · Tax dashboard (TODO) · Supplier breakdown (TODO)"},
            {"id": "8B", "name": "Future Options", "status": "future",
             "details": "Embeddable dashboards · Scheduled email reports · Custom dashboard builder · AI insights (Claude API) · Export · Comparison mode"},
        ],
    },
    {
        "num": 9,
        "title": "Security & Compliance",
        "icon": "🛡️",
        "color": "#EF4444",
        "status": "partial",
        "progress": 50,
        "substeps": [
            {"id": "9A", "name": "Implemented Measures", "status": "done",
             "details": "Firebase password storage, JWT verification, parameterized SQL, session timeout, password strength, audit log, RBAC, multi-tenant"},
            {"id": "9B", "name": "ISO 27001 / SOC 2 Roadmap", "status": "pending",
             "details": "Security policy · Risk assessment · Access control docs · Incident response · BCP · Vendor assessment · Pen testing · Training"},
            {"id": "9C", "name": "Future Options", "status": "future",
             "details": "WAF · Rate limiting · CAPTCHA · Security headers · Vulnerability scanning · Data residency · Backup testing"},
        ],
    },
    {
        "num": 10,
        "title": "Team & Admin Features",
        "icon": "⚙️",
        "color": "#78716C",
        "status": "pending",
        "progress": 0,
        "substeps": [
            {"id": "10A", "name": "Team Management UI", "status": "pending",
             "details": "Invite by email, role assignment dropdown, member list with badges, remove/deactivate, ownership transfer"},
            {"id": "10B", "name": "Admin Dashboard", "status": "pending",
             "details": "Activity overview, audit log viewer, company settings, usage statistics"},
            {"id": "10C", "name": "Future Options", "status": "future",
             "details": "SSO/SAML enterprise · API keys · White-label branding · Multi-language (ES/EN) · Notification system"},
        ],
    },
]

# ── Security Issues Data ────────────────────────────────────────────────
SECURITY_ISSUES = [
    {
        "id": "SEC-001",
        "severity": "critical",
        "title": "No HTTPS enforcement on API endpoints",
        "category": "Transport Security",
        "status": "open",
        "description": "All API endpoints should enforce HTTPS. HTTP requests must be redirected or blocked.",
        "recommendation": "Configure Railway to force HTTPS redirects. Add HSTS header with min 1 year max-age.",
        "affected": "All endpoints",
        "date_found": "2026-03-15",
    },
    {
        "id": "SEC-002",
        "severity": "critical",
        "title": "Missing Content Security Policy (CSP) header",
        "category": "HTTP Headers",
        "status": "open",
        "description": "No CSP header is set, leaving the application vulnerable to XSS and data injection attacks.",
        "recommendation": "Add strict CSP: default-src 'self'; script-src 'self' 'unsafe-inline' cdn.plot.ly; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;",
        "affected": "All pages",
        "date_found": "2026-03-15",
    },
    {
        "id": "SEC-003",
        "severity": "high",
        "title": "No rate limiting on login endpoint",
        "category": "Authentication",
        "status": "open",
        "description": "Login attempts are not rate-limited, enabling brute-force password attacks.",
        "recommendation": "Implement rate limiting: max 5 attempts per IP per minute. Use exponential backoff. Lock account after 10 consecutive failures.",
        "affected": "Login page, API auth endpoints",
        "date_found": "2026-03-15",
    },
    {
        "id": "SEC-004",
        "severity": "high",
        "title": "Session tokens not rotated after privilege change",
        "category": "Session Management",
        "status": "open",
        "description": "When a user's role changes (e.g., viewer → admin), the session token is not regenerated, creating a session fixation risk.",
        "recommendation": "Regenerate session token after any role change, password change, or privilege escalation.",
        "affected": "RBAC system, session management",
        "date_found": "2026-03-16",
    },
    {
        "id": "SEC-005",
        "severity": "high",
        "title": "No X-Frame-Options or frame-ancestors CSP",
        "category": "HTTP Headers",
        "status": "open",
        "description": "App can be embedded in iframes on malicious sites, enabling clickjacking attacks.",
        "recommendation": "Add X-Frame-Options: DENY header and frame-ancestors 'none' to CSP.",
        "affected": "All pages",
        "date_found": "2026-03-15",
    },
    {
        "id": "SEC-006",
        "severity": "medium",
        "title": "Database connection string in environment variable",
        "category": "Secrets Management",
        "status": "mitigated",
        "description": "DATABASE_URL is stored as plain text environment variable in Railway.",
        "recommendation": "This is standard for Railway. Ensure Railway dashboard access is protected with 2FA. Consider using Railway's reference variables (${{Postgres.DATABASE_URL}}) for auto-rotation.",
        "affected": "Railway deployment",
        "date_found": "2026-03-10",
    },
    {
        "id": "SEC-007",
        "severity": "medium",
        "title": "No automated vulnerability scanning",
        "category": "CI/CD Security",
        "status": "open",
        "description": "No dependency scanning (Dependabot/Snyk) or SAST tools are configured in the GitHub repository.",
        "recommendation": "Enable GitHub Dependabot alerts. Add safety or pip-audit to CI pipeline. Consider Snyk for deeper analysis.",
        "affected": "GitHub repository, dependencies",
        "date_found": "2026-03-16",
    },
    {
        "id": "SEC-008",
        "severity": "medium",
        "title": "Missing audit log for data exports",
        "category": "Data Protection",
        "status": "open",
        "description": "When users export or download financial data (CSVs, charts), no audit trail is created.",
        "recommendation": "Log all data export events with user_id, company_id, data_type, timestamp, and IP address.",
        "affected": "Charts, Sankey exports, data downloads",
        "date_found": "2026-03-17",
    },
    {
        "id": "SEC-009",
        "severity": "medium",
        "title": "No CAPTCHA on signup form",
        "category": "Bot Protection",
        "status": "open",
        "description": "Signup form has no bot protection, enabling automated account creation.",
        "recommendation": "Add reCAPTCHA v3 or hCaptcha to signup and password reset forms.",
        "affected": "Signup page, password reset",
        "date_found": "2026-03-17",
    },
    {
        "id": "SEC-010",
        "severity": "low",
        "title": "Server version exposed in response headers",
        "category": "Information Disclosure",
        "status": "open",
        "description": "Response headers reveal Streamlit and Python version info, aiding attackers in fingerprinting.",
        "recommendation": "Configure response headers to remove Server, X-Powered-By. Add custom middleware to strip version info.",
        "affected": "All HTTP responses",
        "date_found": "2026-03-18",
    },
    {
        "id": "SEC-011",
        "severity": "low",
        "title": "No backup verification process",
        "category": "Business Continuity",
        "status": "open",
        "description": "Database backups exist (Railway auto-backup) but there is no scheduled restore test.",
        "recommendation": "Schedule monthly backup restore test. Document RTO (Recovery Time Objective) and RPO (Recovery Point Objective).",
        "affected": "PostgreSQL database",
        "date_found": "2026-03-18",
    },
    {
        "id": "SEC-012",
        "severity": "info",
        "title": "2FA not enforced for admin accounts",
        "category": "Account Security",
        "status": "open",
        "description": "Platform admin accounts (Firebase, Railway, Stripe, GitHub) do not require 2FA.",
        "recommendation": "Enable 2FA on all admin accounts: Firebase Console, Railway, Stripe Dashboard, GitHub (enforce via org settings).",
        "affected": "Admin accounts on all platforms",
        "date_found": "2026-03-18",
    },
]

# ── Compliance Data ─────────────────────────────────────────────────────
ISO_CONTROLS = [
    {"id": "A.5", "name": "Information Security Policies", "status": "pending", "progress": 0,
     "details": "Policies for information security, management direction"},
    {"id": "A.6", "name": "Organization of Information Security", "status": "pending", "progress": 0,
     "details": "Internal organization, mobile devices, teleworking"},
    {"id": "A.7", "name": "Human Resource Security", "status": "pending", "progress": 0,
     "details": "Prior to employment, during employment, termination"},
    {"id": "A.8", "name": "Asset Management", "status": "partial", "progress": 30,
     "details": "Responsibility for assets, information classification, media handling"},
    {"id": "A.9", "name": "Access Control", "status": "partial", "progress": 70,
     "details": "Business requirements, user access management, system access control"},
    {"id": "A.10", "name": "Cryptography", "status": "partial", "progress": 50,
     "details": "Cryptographic controls, key management"},
    {"id": "A.12", "name": "Operations Security", "status": "partial", "progress": 40,
     "details": "Operational procedures, malware protection, backup, logging"},
    {"id": "A.13", "name": "Communications Security", "status": "pending", "progress": 10,
     "details": "Network security management, information transfer"},
    {"id": "A.14", "name": "System Acquisition & Development", "status": "partial", "progress": 45,
     "details": "Security requirements, development security, test data"},
    {"id": "A.16", "name": "Incident Management", "status": "pending", "progress": 0,
     "details": "Management of incidents, improvements"},
    {"id": "A.17", "name": "Business Continuity", "status": "pending", "progress": 10,
     "details": "Information security continuity, redundancies"},
    {"id": "A.18", "name": "Compliance", "status": "pending", "progress": 5,
     "details": "Legal & contractual requirements, information security reviews"},
]


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════
def _status_badge(status: str) -> str:
    m = {
        "done":     ("✅ Done",       "#10B981", "#ECFDF5"),
        "partial":  ("🔧 In Progress","#F59E0B", "#FFFBEB"),
        "pending":  ("⏳ Pending",    "#6B7280", "#F3F4F6"),
        "deferred": ("⏸️ Deferred",   "#6366F1", "#EEF2FF"),
        "future":   ("🔮 Future",     "#A855F7", "#FAF5FF"),
        "open":     ("🔴 Open",       "#EF4444", "#FEF2F2"),
        "mitigated":("🟡 Mitigated",  "#F59E0B", "#FFFBEB"),
        "resolved": ("🟢 Resolved",   "#10B981", "#ECFDF5"),
    }
    label, fg, bg = m.get(status, ("?", "#666", "#EEE"))
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f'font-size:0.78rem;font-weight:600;color:{fg};background:{bg};'
        f'border:1px solid {fg}22;">{label}</span>'
    )


def _severity_badge(severity: str) -> str:
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
    )


def _progress_bar(pct: int, color: str) -> str:
    return (
        f'<div style="background:#1E293B;border-radius:6px;height:8px;width:100%;margin:6px 0;">'
        f'<div style="background:{color};width:{pct}%;height:100%;border-radius:6px;'
        f'transition:width .4s ease;"></div></div>'
    )


def _metric_card(value, label, color="#F8FAFC"):
    return (
        f'<div style="text-align:center;padding:16px 12px;background:#0F172A;'
        f'border:1px solid #1E293B;border-radius:12px;min-width:100px;">'
        f'<div style="font-size:2rem;font-weight:700;color:{color};">{value}</div>'
        f'<div style="font-size:0.75rem;color:#64748B;text-transform:uppercase;'
        f'letter-spacing:1px;margin-top:4px;">{label}</div></div>'
    )


# ═══════════════════════════════════════════════════════════════════════
# MAIN STYLES
# ═══════════════════════════════════════════════════════════════════════
_STYLES = """
<style>
[data-testid="stSidebar"] { display: none !important; }
section[data-testid="stMain"] > div { padding-top: 0 !important; }

.nsfe-topbar {
    background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
    border-bottom: 2px solid #334155;
    padding: 12px 24px;
    margin: -1rem -1rem 24px -1rem;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.nsfe-topbar-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #F8FAFC;
    margin-right: 24px;
    letter-spacing: -0.3px;
}
.nsfe-topbar-sep {
    width: 1px;
    height: 24px;
    background: #334155;
    margin: 0 8px;
}

.nsfe-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 28px;
    text-align: center;
}
.nsfe-header h1 { color: #F8FAFC; font-size: 2rem; margin: 0 0 6px 0; letter-spacing: -0.5px; }
.nsfe-header p { color: #94A3B8; font-size: 1rem; margin: 0; }

.metrics-row {
    display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin: 20px 0;
}

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

.substep {
    background: #1E293B; border-radius: 10px; padding: 14px 18px; margin: 8px 0;
}
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
    font-size: 0.82rem; color: #CBD5E1; background: #1E293B; padding: 12px 16px;
    border-radius: 8px; margin-top: 10px; border-left: 3px solid #3B82F6;
}

.compliance-card {
    background: #0F172A; border: 1px solid #1E293B; border-radius: 12px;
    padding: 18px 22px; margin-bottom: 10px;
}
.compliance-header { display: flex; align-items: center; gap: 12px; }
.compliance-id { font-weight: 700; color: #3B82F6; font-size: 0.9rem; min-width: 50px; }
.compliance-name { font-weight: 600; color: #F1F5F9; font-size: 0.95rem; flex: 1; }

.impl-order {
    background: #0F172A; border: 1px solid #1E293B; border-radius: 14px;
    padding: 28px; margin-top: 24px;
}
.impl-order h3 { color: #F1F5F9; margin: 0 0 18px 0; font-size: 1.2rem; }
.impl-item {
    display: flex; align-items: center; gap: 12px; padding: 10px 16px;
    border-radius: 8px; margin: 4px 0; font-size: 0.9rem; color: #CBD5E1;
}
.impl-item:nth-child(even) { background: #1E293B44; }
.impl-done { color: #10B981; }
.impl-pending { color: #64748B; }

.lock-container {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 50vh;
}
.lock-icon { font-size: 4rem; margin-bottom: 16px; }
.lock-title { font-size: 1.5rem; font-weight: 700; color: #F1F5F9; margin-bottom: 8px; }
.lock-sub { font-size: 0.9rem; color: #64748B; margin-bottom: 24px; }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════
# PAGE RENDERERS
# ═══════════════════════════════════════════════════════════════════════

def _render_dashboard():
    """Phase 2 implementation roadmap dashboard."""
    done_count = sum(1 for s in STEPS if s["status"] == "done")
    partial_count = sum(1 for s in STEPS if s["status"] == "partial")
    pending_count = sum(1 for s in STEPS if s["status"] == "pending")
    deferred_count = sum(1 for s in STEPS if s["status"] == "deferred")
    overall_pct = sum(s["progress"] for s in STEPS) // len(STEPS)

    st.markdown(f"""
    <div class="nsfe-header">
        <h1>QuarterCharts — Phase 2 Dashboard</h1>
        <p>Full implementation roadmap &nbsp;·&nbsp; 10 Steps &nbsp;·&nbsp; {overall_pct}% overall progress</p>
        <div style="max-width:400px;margin:16px auto 0;">
            {_progress_bar(overall_pct, '#3B82F6')}
        </div>
        <div class="metrics-row">
            {_metric_card(done_count, "Completed", "#10B981")}
            {_metric_card(partial_count, "In Progress", "#F59E0B")}
            {_metric_card(pending_count, "Pending", "#6B7280")}
            {_metric_card(deferred_count, "Deferred", "#6366F1")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    for step in STEPS:
        badge = _status_badge(step["status"])
        bar = _progress_bar(step["progress"], step["color"])
        st.markdown(f"""
        <div class="step-card">
            <div class="step-header">
                <div class="step-icon" style="background:{step['color']}22;">{step['icon']}</div>
                <div>
                    <span class="step-num">STEP {step['num']}</span>
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
                        <span class="substep-name">{sub['id']}. {sub['name']}</span>
                        {sub_badge}
                    </div>
                    <div class="substep-detail">{sub['details']}</div>
                </div>
                """, unsafe_allow_html=True)

    # Implementation Order
    impl = [
        (True,  "auth.py — Firebase Auth backend"),
        (True,  "database.py — PostgreSQL database layer"),
        (True,  "rbac.py — Role-based access control"),
        (True,  "login_page.py — Auth UI"),
        (True,  "requirements.txt — Updated dependencies"),
        (True,  "SETUP_AUTH.md — Setup documentation"),
        (False, "Integrate auth into app.py — Wire everything together"),
        (False, "Firebase project creation — Set up actual Firebase project"),
        (False, "Railway PostgreSQL — Create and connect database"),
        (False, "Test end-to-end auth flow — Login, signup, Google SSO, session timeout"),
        (False, "Data upload pipeline — SRI invoice parser and storage"),
        (False, "Enhanced dashboards — Financial visualizations from uploaded data"),
        (False, "Team management UI — Invite members, assign roles"),
        (False, "Stripe billing — Payment integration"),
        (False, "Security hardening — Rate limiting, CAPTCHA, security headers"),
        (False, "ISO 27001 preparation — Documentation, policies, audit readiness"),
    ]
    items_html = ""
    for i, (done, text) in enumerate(impl, 1):
        icon = "✅" if done else "⬜"
        cls = "impl-done" if done else "impl-pending"
        items_html += f'<div class="impl-item"><span>{icon}</span><span class="{cls}">{i}. {text}</span></div>\n'

    st.markdown(f"""
    <div class="impl-order">
        <h3>📋 Implementation Order</h3>
        {items_html}
    </div>
    """, unsafe_allow_html=True)


def _render_security():
    """Security issues tracker and compliance dashboard."""

    # ── Summary metrics ──
    total = len(SECURITY_ISSUES)
    critical = sum(1 for i in SECURITY_ISSUES if i["severity"] == "critical")
    high = sum(1 for i in SECURITY_ISSUES if i["severity"] == "high")
    medium = sum(1 for i in SECURITY_ISSUES if i["severity"] == "medium")
    low_info = sum(1 for i in SECURITY_ISSUES if i["severity"] in ("low", "info"))
    open_count = sum(1 for i in SECURITY_ISSUES if i["status"] == "open")
    mitigated = sum(1 for i in SECURITY_ISSUES if i["status"] == "mitigated")
    resolved = sum(1 for i in SECURITY_ISSUES if i["status"] == "resolved")

    st.markdown(f"""
    <div class="nsfe-header">
        <h1>Security & Compliance Center</h1>
        <p>Vulnerability tracking &nbsp;·&nbsp; ISO 27001 readiness &nbsp;·&nbsp; {total} issues tracked</p>
        <div class="metrics-row">
            {_metric_card(critical, "Critical", "#DC2626")}
            {_metric_card(high, "High", "#EA580C")}
            {_metric_card(medium, "Medium", "#D97706")}
            {_metric_card(low_info, "Low / Info", "#2563EB")}
            {_metric_card(open_count, "Open", "#EF4444")}
            {_metric_card(mitigated, "Mitigated", "#F59E0B")}
            {_metric_card(resolved, "Resolved", "#10B981")}
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
        sev = _severity_badge(issue["severity"])
        stat = _status_badge(issue["status"])
        st.markdown(f"""
        <div class="sec-card">
            <div class="sec-card-header">
                <span class="sec-card-id">{issue['id']}</span>
                {sev}
                <span class="sec-card-title">{issue['title']}</span>
                {stat}
            </div>
            <span class="sec-card-cat">{issue['category']}</span>
            <span style="font-size:0.75rem;color:#475569;margin-left:12px;">Found: {issue['date_found']}</span>
            <span style="font-size:0.75rem;color:#475569;margin-left:12px;">Affected: {issue['affected']}</span>
            <div class="sec-card-body">{issue['description']}</div>
            <div class="sec-card-rec">💡 <strong>Recommendation:</strong> {issue['recommendation']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ISO 27001 Compliance ──
    st.markdown("---")
    st.markdown("### 🏛️ ISO 27001 Control Status")
    overall_iso = sum(c["progress"] for c in ISO_CONTROLS) // len(ISO_CONTROLS)
    st.markdown(f"""
    <div style="max-width:500px;margin:0 auto 24px;">
        <div style="text-align:center;font-size:0.85rem;color:#94A3B8;margin-bottom:4px;">
            Overall ISO 27001 Readiness: <strong style="color:#F8FAFC;">{overall_iso}%</strong>
        </div>
        {_progress_bar(overall_iso, '#3B82F6')}
    </div>
    """, unsafe_allow_html=True)

    for ctrl in ISO_CONTROLS:
        badge = _status_badge(ctrl["status"])
        bar = _progress_bar(ctrl["progress"], "#3B82F6")
        st.markdown(f"""
        <div class="compliance-card">
            <div class="compliance-header">
                <span class="compliance-id">{ctrl['id']}</span>
                <span class="compliance-name">{ctrl['name']}</span>
                <span style="font-size:0.82rem;color:#94A3B8;min-width:40px;text-align:right;">{ctrl['progress']}%</span>
                {badge}
            </div>
            {bar}
            <div style="font-size:0.8rem;color:#64748B;margin-top:4px;">{ctrl['details']}</div>
        </div>
        """, unsafe_allow_html=True)


def _render_settings():
    """Manager settings page."""
    st.markdown("""
    <div class="nsfe-header">
        <h1>Manager Settings</h1>
        <p>System configuration &nbsp;·&nbsp; Quick actions</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔗 Quick Links")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">🔥</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Firebase Console</div>
            <div style="font-size:0.8rem;color:#64748B;">Auth, users, config</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Firebase", "https://console.firebase.google.com", use_container_width=True)
    with col2:
        st.markdown("""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">🚂</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Railway Dashboard</div>
            <div style="font-size:0.8rem;color:#64748B;">Deploys, DB, logs</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Railway", "https://railway.app/dashboard", use_container_width=True)
    with col3:
        st.markdown("""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">💳</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Stripe Dashboard</div>
            <div style="font-size:0.8rem;color:#64748B;">Billing, subscriptions</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Stripe", "https://dashboard.stripe.com", use_container_width=True)

    st.markdown("---")
    st.markdown("### 📦 Repository")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">🐙</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">GitHub Repository</div>
            <div style="font-size:0.8rem;color:#64748B;">Code, issues, PRs</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open GitHub", "https://github.com/miteproyects/opensankey", use_container_width=True)
    with col2:
        st.markdown("""
        <div class="step-card" style="text-align:center;padding:20px;">
            <div style="font-size:2rem;margin-bottom:8px;">🌐</div>
            <div style="font-weight:700;color:#F1F5F9;margin-bottom:4px;">Live Site</div>
            <div style="font-size:0.8rem;color:#64748B;">quartercharts.com</div>
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Live Site", "https://quartercharts.com", use_container_width=True)

    st.markdown("---")
    st.markdown("### ⚡ System Info")
    st.markdown(f"""
    <div class="step-card">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div><span style="color:#64748B;font-size:0.85rem;">Platform:</span> <span style="color:#F1F5F9;">Streamlit + Railway</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Database:</span> <span style="color:#F1F5F9;">PostgreSQL (Railway)</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Auth:</span> <span style="color:#F1F5F9;">Firebase Auth</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Payments:</span> <span style="color:#F1F5F9;">Stripe (planned)</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Domain:</span> <span style="color:#F1F5F9;">quartercharts.com</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Auto-deploy:</span> <span style="color:#10B981;">GitHub main → Railway</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">Target:</span> <span style="color:#F1F5F9;">$50K/year B2B SaaS</span></div>
            <div><span style="color:#64748B;font-size:0.85rem;">NSFE Password:</span> <span style="color:#F59E0B;">Active</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════
def render_nsfe_page():
    """Render the password-protected NSFE manager control center."""

    st.markdown(_STYLES, unsafe_allow_html=True)

    # ── Password Gate ──
    if not st.session_state.get("nsfe_auth", False):
        st.markdown("""
        <div class="lock-container">
            <div class="lock-icon">🔒</div>
            <div class="lock-title">NSFE — Restricted Area</div>
            <div class="lock-sub">Enter the project password to continue</div>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            pwd = st.text_input("Password", type="password", key="nsfe_pwd",
                                placeholder="Enter password…",
                                label_visibility="collapsed")
            if st.button("Unlock Dashboard", use_container_width=True, type="primary"):
                if pwd == _PASSWORD:
                    st.session_state.nsfe_auth = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Try again.")
        return

    # ── Main Menu (Streamlit tabs) ──
    tab1, tab2, tab3 = st.tabs([
        "📋 Dashboard",
        "🛡️ Security",
        "⚙️ Settings",
    ])

    with tab1:
        _render_dashboard()

    with tab2:
        _render_security()

    with tab3:
        _render_settings()

    # Footer
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
