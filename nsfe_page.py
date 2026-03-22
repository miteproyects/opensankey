"""
NSFE – Phase 2 Project Dashboard (password-protected).
"""

import streamlit as st
import hashlib

# ── Config ──────────────────────────────────────────────────────────────
_NSFE_HASH = "a3f7c0e6a1b3d8f2e5c9b4a7d6e1f0c3"  # md5 of the password
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


def _status_badge(status: str) -> str:
    """Return an HTML badge for task status."""
    m = {
        "done":    ("✅ Done",     "#10B981", "#ECFDF5"),
        "partial": ("🔧 In Progress", "#F59E0B", "#FFFBEB"),
        "pending": ("⏳ Pending",  "#6B7280", "#F3F4F6"),
        "deferred":("⏸️ Deferred", "#6366F1", "#EEF2FF"),
        "future":  ("🔮 Future",   "#A855F7", "#FAF5FF"),
    }
    label, fg, bg = m.get(status, ("?", "#666", "#EEE"))
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f'font-size:0.78rem;font-weight:600;color:{fg};background:{bg};'
        f'border:1px solid {fg}22;">{label}</span>'
    )


def _progress_bar(pct: int, color: str) -> str:
    """Return a small progress bar HTML string."""
    return (
        f'<div style="background:#1E293B;border-radius:6px;height:8px;width:100%;margin:6px 0;">'
        f'<div style="background:{color};width:{pct}%;height:100%;border-radius:6px;'
        f'transition:width .4s ease;"></div></div>'
    )


def render_nsfe_page():
    """Render the password-protected NSFE project dashboard."""

    # ── Inject page styles ──────────────────────────────────────────────
    st.markdown("""
    <style>
    /* hide Streamlit chrome for cleaner look */
    [data-testid="stSidebar"] { display: none !important; }
    section[data-testid="stMain"] > div { padding-top: 0 !important; }

    .nsfe-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 32px 40px;
        margin-bottom: 28px;
        text-align: center;
    }
    .nsfe-header h1 {
        color: #F8FAFC;
        font-size: 2rem;
        margin: 0 0 6px 0;
        letter-spacing: -0.5px;
    }
    .nsfe-header p {
        color: #94A3B8;
        font-size: 1rem;
        margin: 0;
    }
    .nsfe-stats {
        display: flex;
        justify-content: center;
        gap: 32px;
        margin-top: 20px;
        flex-wrap: wrap;
    }
    .nsfe-stat {
        text-align: center;
    }
    .nsfe-stat .num {
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    .nsfe-stat .lbl {
        font-size: 0.8rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .step-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 16px;
        transition: border-color 0.2s;
    }
    .step-card:hover {
        border-color: #334155;
    }
    .step-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 8px;
    }
    .step-icon {
        font-size: 1.6rem;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        flex-shrink: 0;
    }
    .step-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #F1F5F9;
        margin: 0;
    }
    .step-num {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 600;
    }
    .substep {
        background: #1E293B;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 8px 0;
    }
    .substep-name {
        font-size: 0.95rem;
        font-weight: 600;
        color: #CBD5E1;
        margin-bottom: 4px;
    }
    .substep-detail {
        font-size: 0.82rem;
        color: #64748B;
        line-height: 1.5;
    }
    .impl-order {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 14px;
        padding: 28px;
        margin-top: 24px;
    }
    .impl-order h3 {
        color: #F1F5F9;
        margin: 0 0 18px 0;
        font-size: 1.2rem;
    }
    .impl-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        border-radius: 8px;
        margin: 4px 0;
        font-size: 0.9rem;
        color: #CBD5E1;
    }
    .impl-item:nth-child(even) {
        background: #1E293B44;
    }
    .impl-done { color: #10B981; }
    .impl-pending { color: #64748B; }
    .lock-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 50vh;
    }
    .lock-icon {
        font-size: 4rem;
        margin-bottom: 16px;
    }
    .lock-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #F1F5F9;
        margin-bottom: 8px;
    }
    .lock-sub {
        font-size: 0.9rem;
        color: #64748B;
        margin-bottom: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Password Gate ───────────────────────────────────────────────────
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
        return  # stop here until authenticated

    # ── Dashboard Header ────────────────────────────────────────────────
    done_count   = sum(1 for s in STEPS if s["status"] == "done")
    partial_count = sum(1 for s in STEPS if s["status"] == "partial")
    pending_count = sum(1 for s in STEPS if s["status"] == "pending")
    deferred_count = sum(1 for s in STEPS if s["status"] == "deferred")
    overall_pct  = sum(s["progress"] for s in STEPS) // len(STEPS)

    st.markdown(f"""
    <div class="nsfe-header">
        <h1>QuarterCharts — Phase 2 Dashboard</h1>
        <p>Full implementation roadmap &nbsp;·&nbsp; 10 Steps &nbsp;·&nbsp; {overall_pct}% overall progress</p>
        <div style="max-width:400px;margin:16px auto 0;">
            {_progress_bar(overall_pct, '#3B82F6')}
        </div>
        <div class="nsfe-stats">
            <div class="nsfe-stat"><div class="num" style="color:#10B981;">{done_count}</div><div class="lbl">Completed</div></div>
            <div class="nsfe-stat"><div class="num" style="color:#F59E0B;">{partial_count}</div><div class="lbl">In Progress</div></div>
            <div class="nsfe-stat"><div class="num" style="color:#6B7280;">{pending_count}</div><div class="lbl">Pending</div></div>
            <div class="nsfe-stat"><div class="num" style="color:#6366F1;">{deferred_count}</div><div class="lbl">Deferred</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Step Cards ──────────────────────────────────────────────────────
    for step in STEPS:
        badge = _status_badge(step["status"])
        bar   = _progress_bar(step["progress"], step["color"])

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

        # Expandable substeps
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

    # ── Implementation Order ────────────────────────────────────────────
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
        cls  = "impl-done" if done else "impl-pending"
        items_html += f'<div class="impl-item"><span>{icon}</span><span class="{cls}">{i}. {text}</span></div>\n'

    st.markdown(f"""
    <div class="impl-order">
        <h3>📋 Implementation Order</h3>
        {items_html}
    </div>
    """, unsafe_allow_html=True)

    # ── Footer spacer ───────────────────────────────────────────────────
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
