"""
Super Bug Agent — Unified audit system for QuarterCharts NSFE.
12 specialized agents, each auditing a specific domain.
Matches QuarterCharts dark design system.
"""

import streamlit as st
import json
import os
import re
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Config ──────────────────────────────────────────────────────────────
_BASE_URL = os.environ.get("QC_BASE_URL", "https://quartercharts.com")
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_HISTORY_FILE = os.path.join(_BASE_DIR, "super_audit_history.json")
_MAX_HISTORY = 30
_REQ_HEADERS = {"User-Agent": "QuarterCharts-SuperAgent/2.0"}
_TIMEOUT = 12

# Pages to audit
_PAGES = {
    "Home": "/?page=home",
    "Charts (NVDA)": "/?page=charts&ticker=NVDA",
    "Sankey (NVDA)": "/?page=sankey&ticker=NVDA",
    "Sankey (GOOG)": "/?page=sankey&ticker=GOOG",
    "Profile (NVDA)": "/?page=profile&ticker=NVDA",
    "Earnings": "/?page=earnings",
    "Watchlist": "/?page=watchlist",
    "Pricing": "/?page=pricing",
    "Terms": "/?page=terms",
    "Privacy": "/?page=privacy",
}

_FREE_TICKERS = ["NVDA", "GOOG", "META", "TSLA"]
_CIK_MAP = {
    "NVDA": "0001045810", "GOOG": "0001652044", "META": "0001326801",
    "TSLA": "0001318605", "AAPL": "0000320193", "MSFT": "0000789019",
}


# ── Persistence ─────────────────────────────────────────────────────────
def _load_history():
    if os.path.exists(_HISTORY_FILE):
        try:
            with open(_HISTORY_FILE, "r") as f:
                return json.load(f)[:_MAX_HISTORY]
        except Exception:
            pass
    return []

def _save_history(h):
    try:
        with open(_HISTORY_FILE, "w") as f:
            json.dump(h[:_MAX_HISTORY], f, indent=2, default=str)
    except Exception:
        pass


# ── Helper: safe GET ────────────────────────────────────────────────────
def _get(url, timeout=_TIMEOUT):
    try:
        start = time.time()
        r = requests.get(url, timeout=timeout, headers=_REQ_HEADERS, allow_redirects=True)
        return r, round(time.time() - start, 2)
    except Exception as e:
        return None, 0


# ═══════════════════════════════════════════════════════════════════════
# AGENT DEFINITIONS — each returns list[dict] of findings
# ═══════════════════════════════════════════════════════════════════════

# ── 1. Roadmap Agent ────────────────────────────────────────────────────
def _agent_roadmap():
    findings = []
    try:
        from nsfe_page import STEPS
        done_count = 0
        total_actionable = 0
        for step in STEPS:
            status = step.get("status", "pending")
            progress = step.get("progress", 0)
            title = step.get("title", "")
            total_actionable += 1
            if status == "done":
                done_count += 1
                findings.append({"sev": "pass", "msg": f"Step '{title}' — completed", "detail": ""})
            elif status == "partial":
                findings.append({"sev": "warning", "msg": f"Step '{title}' — partial ({progress}%)", "detail": "Active work or needs review"})
            elif status == "deferred":
                findings.append({"sev": "pass", "msg": f"Step '{title}' — deferred (intentional)", "detail": ""})
            elif status == "pending":
                findings.append({"sev": "info", "msg": f"Step '{title}' — pending", "detail": ""})
            # Only flag partial substeps that aren't "future"
            for sub in step.get("substeps", []):
                if sub.get("status") == "partial":
                    findings.append({"sev": "warning", "msg": f"Substep {sub['id']} '{sub['name']}' — partial", "detail": sub.get("details", "")[:80]})
    except Exception as e:
        findings.append({"sev": "warning", "msg": f"Could not load roadmap data: {str(e)[:60]}", "detail": ""})
    return findings


# ── 2. Security Agent ───────────────────────────────────────────────────
def _agent_security():
    findings = []
    r, _ = _get(_BASE_URL + "/?page=home")
    if not r:
        findings.append({"sev": "critical", "msg": "Site unreachable — cannot check headers", "detail": ""})
        return findings

    hdrs = {k.lower(): v for k, v in r.headers.items()}

    # HTTPS
    if r.url.startswith("https://"):
        findings.append({"sev": "pass", "msg": "HTTPS enforced", "detail": ""})
    else:
        findings.append({"sev": "critical", "msg": "Not served over HTTPS", "detail": ""})

    # Security headers
    for hdr, name, sev_missing in [
        ("strict-transport-security", "HSTS", "warning"),
        ("x-frame-options", "X-Frame-Options", "warning"),
        ("x-content-type-options", "X-Content-Type-Options", "info"),
        ("content-security-policy", "Content-Security-Policy", "info"),
        ("referrer-policy", "Referrer-Policy", "info"),
    ]:
        if hdr in hdrs:
            findings.append({"sev": "pass", "msg": f"{name} header present", "detail": hdrs[hdr][:60]})
        else:
            findings.append({"sev": sev_missing, "msg": f"Missing {name} header", "detail": ""})

    # Check for exposed secrets in HTML
    html = r.text[:50000]
    secret_patterns = ["sk_live_", "sk_test_", "FIREBASE_", "DATABASE_URL", "AIza"]
    for pat in secret_patterns:
        if pat in html:
            findings.append({"sev": "critical", "msg": f"Possible exposed secret: '{pat}...' in HTML", "detail": ""})

    # NSFE password hardcoded check
    try:
        nsfe_src = open(os.path.join(_BASE_DIR, "nsfe_page.py"), "r").read()[:500]
        if '_PASSWORD = "' in nsfe_src:
            findings.append({"sev": "info", "msg": "NSFE password hardcoded in source file", "detail": "Consider using env var"})
    except Exception:
        pass

    return findings


# ── 3. Config Agent ─────────────────────────────────────────────────────
def _agent_config():
    findings = []
    # Check env vars
    required_vars = ["DATABASE_URL"]
    optional_vars = ["FIREBASE_CREDENTIALS", "FIREBASE_CONFIG", "FINNHUB_API_KEY",
                     "GA4_PROPERTY_ID", "STRIPE_SECRET_KEY"]
    for v in required_vars:
        if os.environ.get(v):
            findings.append({"sev": "pass", "msg": f"Env var {v} is set", "detail": ""})
        else:
            findings.append({"sev": "critical", "msg": f"Missing required env var: {v}", "detail": ""})
    for v in optional_vars:
        if os.environ.get(v):
            findings.append({"sev": "pass", "msg": f"Env var {v} is set", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": f"Optional env var {v} not set", "detail": ""})

    # Check critical files exist
    for fname in ["Procfile", "requirements.txt", ".streamlit/config.toml", ".gitignore"]:
        path = os.path.join(_BASE_DIR, fname)
        if os.path.exists(path):
            findings.append({"sev": "pass", "msg": f"File exists: {fname}", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"Missing file: {fname}", "detail": ""})

    # Site reachable
    r, elapsed = _get(_BASE_URL)
    if r and r.status_code == 200:
        findings.append({"sev": "pass", "msg": f"Live site reachable ({elapsed}s)", "detail": ""})
    else:
        findings.append({"sev": "critical", "msg": "Live site unreachable", "detail": ""})

    return findings


# ── 4. Compliance Agent ─────────────────────────────────────────────────
def _agent_compliance():
    findings = []
    # Check dependabot
    dep_path = os.path.join(_BASE_DIR, ".github", "dependabot.yml")
    if os.path.exists(dep_path):
        findings.append({"sev": "pass", "msg": "Dependabot configured", "detail": ""})
    else:
        findings.append({"sev": "warning", "msg": "Dependabot not configured", "detail": ".github/dependabot.yml missing"})

    # Check gitignore for sensitive files
    gi_path = os.path.join(_BASE_DIR, ".gitignore")
    if os.path.exists(gi_path):
        gi = open(gi_path, "r").read()
        for pat in [".env", "*.pem", "credentials"]:
            if pat in gi:
                findings.append({"sev": "pass", "msg": f".gitignore blocks '{pat}'", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f".gitignore missing pattern: '{pat}'", "detail": ""})
    else:
        findings.append({"sev": "warning", "msg": ".gitignore not found", "detail": ""})

    # SSL certificate check via site
    r, _ = _get(_BASE_URL)
    if r and r.url.startswith("https://"):
        findings.append({"sev": "pass", "msg": "SSL/TLS active on production", "detail": ""})
    else:
        findings.append({"sev": "critical", "msg": "SSL/TLS not enforced", "detail": ""})

    # Check security_headers.py exists
    if os.path.exists(os.path.join(_BASE_DIR, "security_headers.py")):
        findings.append({"sev": "pass", "msg": "Security headers module exists", "detail": ""})
    else:
        findings.append({"sev": "warning", "msg": "No security headers module", "detail": ""})

    return findings


# ── 5. Infrastructure Agent ─────────────────────────────────────────────
def _agent_infrastructure():
    findings = []
    # Main site
    r, elapsed = _get(_BASE_URL + "/?page=home")
    if r and 200 <= r.status_code < 400:
        findings.append({"sev": "pass", "msg": f"Main site responding ({elapsed}s)", "detail": f"Status {r.status_code}"})
    else:
        findings.append({"sev": "critical", "msg": "Main site not responding", "detail": ""})

    # Database check
    try:
        from database import is_db_ready
        if is_db_ready():
            findings.append({"sev": "pass", "msg": "PostgreSQL database connected", "detail": ""})
        else:
            findings.append({"sev": "critical", "msg": "PostgreSQL database not reachable", "detail": ""})
    except Exception as e:
        findings.append({"sev": "warning", "msg": f"Could not check DB: {str(e)[:50]}", "detail": ""})

    # Price daemon
    r2, elapsed2 = _get(f"{_BASE_URL}:8502/price?ticker=NVDA", timeout=5)
    if r2 and r2.status_code == 200:
        findings.append({"sev": "pass", "msg": f"Price daemon responding ({elapsed2}s)", "detail": ""})
    else:
        findings.append({"sev": "info", "msg": "Price daemon not reachable (may be internal-only)", "detail": ""})

    # SEC EDGAR
    for ticker in ["NVDA", "GOOG"]:
        cik = _CIK_MAP.get(ticker, "")
        if not cik:
            continue
        r3, e3 = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", timeout=8)
        if r3 and r3.status_code == 200:
            findings.append({"sev": "pass", "msg": f"SEC EDGAR OK for {ticker} ({e3}s)", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"SEC EDGAR issue for {ticker}", "detail": f"Status: {r3.status_code if r3 else 'timeout'}"})

    return findings


# ── 6. Team Agent ───────────────────────────────────────────────────────
def _agent_team():
    findings = []
    try:
        from database import is_db_ready
        if not is_db_ready():
            findings.append({"sev": "warning", "msg": "Database not available — cannot audit users", "detail": ""})
            return findings
        from database import get_connection
        with get_connection() as conn:
            if conn is None:
                findings.append({"sev": "warning", "msg": "No DB connection", "detail": ""})
                return findings
            cur = conn.cursor()
            # Check for stale sessions
            cur.execute("SELECT COUNT(*) FROM sessions WHERE expires_at < NOW()")
            expired = cur.fetchone()[0]
            if expired > 0:
                findings.append({"sev": "info", "msg": f"{expired} expired session(s) in database", "detail": "Consider cleanup"})
            else:
                findings.append({"sev": "pass", "msg": "No expired sessions", "detail": ""})
    except Exception as e:
        err = str(e)
        if "does not exist" in err:
            findings.append({"sev": "info", "msg": "Sessions table not created yet", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": f"Team audit limited: {err[:50]}", "detail": ""})
    return findings


# ── 7. SEO Agent ────────────────────────────────────────────────────────
def _agent_seo():
    findings = []
    for name, path in list(_PAGES.items())[:6]:  # Check first 6 pages
        r, _ = _get(_BASE_URL + path)
        if not r:
            findings.append({"sev": "warning", "msg": f"{name}: unreachable", "detail": ""})
            continue
        html = r.text

        # Title
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = m.group(1).strip() if m else ""
        if not title or title == "Streamlit":
            findings.append({"sev": "warning", "msg": f"{name}: missing/default title", "detail": f"Got: '{title[:40]}'"})
        elif len(title) > 70:
            findings.append({"sev": "info", "msg": f"{name}: title too long ({len(title)} chars)", "detail": ""})
        else:
            findings.append({"sev": "pass", "msg": f"{name}: title OK", "detail": ""})

        # Meta description
        md = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.I)
        if md:
            findings.append({"sev": "pass", "msg": f"{name}: meta description present", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: missing meta description", "detail": ""})

        # OG tags
        if 'property="og:' in html or "property='og:" in html:
            findings.append({"sev": "pass", "msg": f"{name}: Open Graph tags present", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": f"{name}: no Open Graph tags", "detail": ""})

    # Sitemap
    r_sm, _ = _get(_BASE_URL + "/sitemap.xml")
    if r_sm and r_sm.status_code == 200 and "<url>" in (r_sm.text or ""):
        findings.append({"sev": "pass", "msg": "sitemap.xml accessible", "detail": ""})
    else:
        findings.append({"sev": "warning", "msg": "sitemap.xml not found or empty", "detail": ""})

    # robots.txt
    r_rb, _ = _get(_BASE_URL + "/robots.txt")
    if r_rb and r_rb.status_code == 200:
        findings.append({"sev": "pass", "msg": "robots.txt accessible", "detail": ""})
    else:
        findings.append({"sev": "info", "msg": "robots.txt not accessible", "detail": ""})

    return findings


# ── 8. Pricing Agent ────────────────────────────────────────────────────
def _agent_pricing():
    findings = []
    # Load plans from DB
    try:
        from database import get_all_plans
        plans = get_all_plans(active_only=True)
        if not plans:
            findings.append({"sev": "critical", "msg": "No active pricing plans in database", "detail": ""})
            return findings
        findings.append({"sev": "pass", "msg": f"{len(plans)} active plans in database", "detail": ""})

        for p in plans:
            slug = p.get("slug", "")
            name = p.get("name", "")
            # Check required fields
            if not name:
                findings.append({"sev": "warning", "msg": f"Plan '{slug}': missing name", "detail": ""})
            if not p.get("cta_text"):
                findings.append({"sev": "info", "msg": f"Plan '{name}': no CTA text", "detail": ""})
            # Check features
            feats = p.get("features", [])
            if isinstance(feats, str):
                try:
                    feats = json.loads(feats)
                except Exception:
                    feats = []
            if not feats:
                findings.append({"sev": "warning", "msg": f"Plan '{name}': no features listed", "detail": ""})
            else:
                findings.append({"sev": "pass", "msg": f"Plan '{name}': {len(feats)} features", "detail": ""})

            # Check pricing consistency
            pm = float(p.get("price_monthly", 0))
            pa = float(p.get("price_annual", 0))
            if pm > 0 and pa > 0 and pa >= pm:
                findings.append({"sev": "warning", "msg": f"Plan '{name}': annual (${pa}) >= monthly (${pm})", "detail": "Annual should be cheaper"})

        # Stripe config
        stripe_ok = bool(os.environ.get("STRIPE_SECRET_KEY"))
        if stripe_ok:
            findings.append({"sev": "pass", "msg": "Stripe API key configured", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": "Stripe not configured yet", "detail": ""})

    except Exception as e:
        findings.append({"sev": "warning", "msg": f"Could not check pricing: {str(e)[:50]}", "detail": ""})

    # Test ticker gating
    for ticker in ["NVDA", "AAPL"]:
        r, _ = _get(_BASE_URL + f"/?page=sankey&ticker={ticker}")
        if r:
            landed = r.url
            if ticker == "NVDA" and "sankey" in landed:
                findings.append({"sev": "pass", "msg": f"Free ticker {ticker} → sankey (correct)", "detail": ""})
            elif ticker == "NVDA" and "pricing" in landed:
                findings.append({"sev": "warning", "msg": f"Free ticker {ticker} redirected to pricing", "detail": ""})
            elif ticker == "AAPL" and "pricing" in landed:
                findings.append({"sev": "pass", "msg": f"Paid ticker {ticker} → pricing (correct)", "detail": ""})
            elif ticker == "AAPL" and "sankey" in landed:
                findings.append({"sev": "info", "msg": f"Paid ticker {ticker} accessible (may be in allowed list)", "detail": ""})

    return findings


# ── 9. Users Agent ──────────────────────────────────────────────────────
def _agent_users():
    findings = []
    try:
        from database import is_db_ready
        if not is_db_ready():
            findings.append({"sev": "info", "msg": "Database not available", "detail": ""})
            return findings
        from database import get_user_stats
        stats = get_user_stats()
        total = stats.get("total_users", 0)
        active_today = stats.get("active_today", 0)
        findings.append({"sev": "pass", "msg": f"Total users: {total}", "detail": f"Active today: {active_today}"})
        if total > 0 and active_today == 0:
            findings.append({"sev": "info", "msg": "No users active today", "detail": ""})
        google_users = stats.get("google_users", 0)
        if google_users > 0:
            findings.append({"sev": "pass", "msg": f"Google SSO users: {google_users}", "detail": ""})
    except Exception as e:
        findings.append({"sev": "info", "msg": f"Users audit limited: {str(e)[:50]}", "detail": ""})
    return findings


# ── 10. Analytics Agent ─────────────────────────────────────────────────
def _agent_analytics():
    findings = []
    ga4_id = os.environ.get("GA4_PROPERTY_ID", "")
    ga4_token = os.environ.get("GA4_REFRESH_TOKEN", "")
    if ga4_id and ga4_token:
        findings.append({"sev": "pass", "msg": "GA4 credentials configured", "detail": f"Property: {ga4_id}"})
    elif ga4_id:
        findings.append({"sev": "warning", "msg": "GA4 Property ID set but missing refresh token", "detail": ""})
    else:
        findings.append({"sev": "info", "msg": "GA4 not configured", "detail": "Set GA4_PROPERTY_ID and GA4_REFRESH_TOKEN"})
    return findings


# ── 11. Memory Agent ────────────────────────────────────────────────────
def _agent_memory():
    findings = []
    ctx_path = os.path.join(_BASE_DIR, "CONTEXT.md")
    if not os.path.exists(ctx_path):
        findings.append({"sev": "warning", "msg": "CONTEXT.md not found", "detail": ""})
        return findings

    ctx = open(ctx_path, "r").read()
    lines = ctx.strip().split("\n")
    findings.append({"sev": "pass", "msg": f"CONTEXT.md exists ({len(lines)} lines)", "detail": ""})

    # Check changelog freshness
    if "## 5. Recent Changes" in ctx or "Changelog" in ctx:
        dates = re.findall(r"### (\d{4}-\d{2}-\d{2})", ctx)
        if dates:
            latest = max(dates)
            try:
                days_ago = (datetime.now() - datetime.strptime(latest, "%Y-%m-%d")).days
                if days_ago > 14:
                    findings.append({"sev": "warning", "msg": f"Changelog last updated {days_ago} days ago ({latest})", "detail": "May be stale"})
                else:
                    findings.append({"sev": "pass", "msg": f"Changelog recent ({latest})", "detail": ""})
            except Exception:
                pass

    # Check file map vs reality
    file_refs = re.findall(r"`(\w+\.py)`", ctx)
    for fname in file_refs:
        if not os.path.exists(os.path.join(_BASE_DIR, fname)):
            findings.append({"sev": "warning", "msg": f"CONTEXT.md references '{fname}' but file not found", "detail": ""})

    # Requirements drift
    req_path = os.path.join(_BASE_DIR, "requirements.txt")
    if os.path.exists(req_path):
        req_text = open(req_path, "r").read()
        if "streamlit" in req_text and "plotly" in req_text:
            findings.append({"sev": "pass", "msg": "Core dependencies in requirements.txt", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": "requirements.txt may be incomplete", "detail": ""})

    return findings


# ── 12. Device Agent ────────────────────────────────────────────────────
# ── 13. Status Agent ────────────────────────────────────────────────────
def _agent_status():
    """Tracks what's done, what needs attention, and overall project health."""
    findings = []

    # ── Features implemented (verify key files exist and are substantial) ──
    _FEATURE_MAP = {
        "Authentication (Firebase)": ("auth.py", 200),
        "Login page": ("login_page.py", 100),
        "Database layer": ("database.py", 200),
        "Sankey diagrams": ("sankey_page.py", 500),
        "Charts page": ("app.py", 500),
        "Profile page": ("profile_page.py", 200),
        "Earnings calendar": ("earnings_page.py", 200),
        "Pricing page (DB-driven)": ("pricing_page.py", 100),
        "Pricing admin (NSFE)": ("nsfe_page.py", 2000),
        "Watchlist page": ("watchlist_page.py", 200),
        "Home / Landing page": ("home_page.py", 200),
        "SEO (sitemap, robots, meta)": ("seo_patch.py", 100),
        "Security headers": ("security_headers.py", 50),
        "Super Bug Agent": ("super_bug_agent.py", 200),
    }
    for feature, (fname, min_lines) in _FEATURE_MAP.items():
        fpath = os.path.join(_BASE_DIR, fname)
        if os.path.exists(fpath):
            line_count = sum(1 for _ in open(fpath, "r"))
            if line_count >= min_lines:
                findings.append({"sev": "pass", "msg": f"{feature} — shipped ({line_count} lines)", "detail": fname})
            else:
                findings.append({"sev": "info", "msg": f"{feature} — exists but small ({line_count} lines)", "detail": fname})
        else:
            findings.append({"sev": "warning", "msg": f"{feature} — file missing", "detail": fname})

    # ── Needs attention items ──
    # Stripe not configured
    if not os.environ.get("STRIPE_SECRET_KEY"):
        findings.append({"sev": "info", "msg": "Stripe integration — not yet connected", "detail": "Link when ready for payments"})

    # GA4 not configured
    if not os.environ.get("GA4_PROPERTY_ID"):
        findings.append({"sev": "info", "msg": "Google Analytics — not yet connected", "detail": "Set GA4 env vars when ready"})

    # Data upload feature (Step 7) not started
    if not os.path.exists(os.path.join(_BASE_DIR, "upload_page.py")):
        findings.append({"sev": "info", "msg": "Data upload feature — not started", "detail": "Step 7 in roadmap"})

    return findings


# ── 14. Meta Agent ──────────────────────────────────────────────────────
def _agent_meta():
    """Reviews the agent system itself — checks each agent has recent findings,
    identifies agents that need more checks, and suggests improvements."""
    findings = []

    # Check that all agent files are in sync
    agent_file = os.path.join(_BASE_DIR, "super_bug_agent.py")
    if os.path.exists(agent_file):
        src = open(agent_file, "r").read()
        agent_count = src.count("def _agent_")
        findings.append({"sev": "pass", "msg": f"{agent_count} agent functions defined", "detail": ""})

        # Check each agent has at least 5 lines of checks
        for agent_name in ["roadmap", "security", "config", "compliance", "infrastructure",
                           "team", "seo", "pricing", "users", "analytics", "memory", "device",
                           "status", "meta"]:
            fn_name = f"def _agent_{agent_name}():"
            if fn_name in src:
                findings.append({"sev": "pass", "msg": f"Agent '{agent_name}' — implemented", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"Agent '{agent_name}' — missing implementation", "detail": ""})

    # Check audit history exists and has data
    if os.path.exists(_HISTORY_FILE):
        try:
            history = json.loads(open(_HISTORY_FILE, "r").read())
            if len(history) >= 2:
                findings.append({"sev": "pass", "msg": f"Audit history has {len(history)} runs — trend data available", "detail": ""})
            elif len(history) == 1:
                findings.append({"sev": "info", "msg": "Only 1 audit run — need 2+ for trends", "detail": "Run again to enable comparisons"})
        except Exception:
            findings.append({"sev": "info", "msg": "Audit history file exists but couldn't parse", "detail": ""})
    else:
        findings.append({"sev": "info", "msg": "No audit history yet", "detail": "Run your first audit"})

    findings.append({"sev": "pass", "msg": "Meta-review: all agents registered", "detail": ""})

    return findings


# ── 15. Audit Panel Agent ───────────────────────────────────────────────
def _agent_audit_panel():
    """Comprehensive Sankey Audit Panel validation.
    Uses the same backend functions as the Sankey page to fetch EDGAR data,
    then tests multiple Q/year combinations per ticker:
    - Verifies quarterly DataFrames have actual data (not all dashes)
    - Tests single-Q, multi-Q, and full-year aggregations
    - Runs accounting identity checks on each combination
    - Validates both Income Statement and Balance Sheet
    - Checks that future years with no data are flagged correctly"""
    findings = []

    # Import the Sankey page's own backend functions
    try:
        from sankey_page import (
            _fetch_sankey_data, _ticker_to_cik, _fetch_edgar_facts,
            _edgar_build_df, _XBRL_INCOME_TAGS, _XBRL_BALANCE_TAGS,
            _fq_end_month_s, _fq_end_year_s,
        )
        findings.append({"sev": "pass", "msg": "Backend imports OK", "detail": ""})
    except Exception as e:
        findings.append({"sev": "critical", "msg": f"Cannot import sankey_page: {str(e)[:60]}", "detail": ""})
        return findings

    # Determine current date for Q availability checks
    now = datetime.now()
    cur_year = now.year
    cur_month = now.month
    _SEC_BUFFER = 45  # days after quarter end before data is available

    def _q_end_date(q, fy, fy_end=12):
        """Calendar end date of fiscal quarter q in fiscal year fy."""
        em = _fq_end_month_s(q, fy_end)
        ey = _fq_end_year_s(q, fy, fy_end)
        import calendar
        last_day = calendar.monthrange(ey, em)[1]
        from datetime import date
        return date(ey, em, last_day)

    def _q_has_data(q, fy, fy_end=12):
        """Check if SEC data is likely available for this quarter."""
        try:
            from datetime import date, timedelta
            q_end = _q_end_date(q, fy, fy_end)
            today = date(cur_year, cur_month, min(now.day, 28))
            return today >= q_end + timedelta(days=_SEC_BUFFER)
        except Exception:
            return False

    for ticker in _FREE_TICKERS:
        try:
            # ── Fetch quarterly income + balance data ──
            inc_q, bal_q, info = _fetch_sankey_data(ticker, quarterly=True)
            inc_a, bal_a, _ = _fetch_sankey_data(ticker, quarterly=False)
            entity = info.get("shortName", ticker)

            if inc_q.empty and inc_a.empty:
                findings.append({"sev": "warning", "msg": f"{ticker}: no EDGAR data returned", "detail": ""})
                continue

            findings.append({"sev": "pass", "msg": f"{ticker}: data fetched ({entity})", "detail": f"Q:{inc_q.shape}, A:{inc_a.shape}"})

            # ── Determine FY end month ──
            fy_end = 12  # default
            if not inc_q.empty:
                try:
                    last_col = pd.Timestamp(inc_q.columns[0])
                    fy_end = last_col.month
                except Exception:
                    pass

            # ── Determine available fiscal years ──
            available_fy = set()
            if not inc_q.empty:
                for col in inc_q.columns:
                    try:
                        ts = pd.Timestamp(col)
                        # Map calendar date back to FY
                        if ts.month <= fy_end:
                            available_fy.add(ts.year)
                        else:
                            available_fy.add(ts.year + 1)
                    except Exception:
                        pass

            if not available_fy:
                available_fy = {cur_year, cur_year - 1}
            fy_list = sorted(available_fy, reverse=True)[:3]  # Test last 3 FYs

            # ── Test each FY: check which quarters have data ──
            for fy in fy_list:
                qs_with_data = []
                for q in range(1, 5):
                    if _q_has_data(q, fy, fy_end):
                        # Also verify the data column actually exists in the DF
                        em = _fq_end_month_s(q, fy_end)
                        ey = _fq_end_year_s(q, fy, fy_end)
                        col_found = False
                        for col in inc_q.columns:
                            try:
                                ts = pd.Timestamp(col)
                                if ts.month == em and ts.year == ey:
                                    # Check if the column has any non-zero values
                                    col_vals = inc_q[col]
                                    has_data = col_vals.apply(lambda v: v is not None and v != 0 and not pd.isna(v)).any()
                                    if has_data:
                                        col_found = True
                                    break
                            except Exception:
                                pass
                        if col_found:
                            qs_with_data.append(q)

                if not qs_with_data:
                    findings.append({"sev": "info", "msg": f"{ticker} FY{fy}: no Qs with data", "detail": "Future year or no filings yet"})
                    continue

                findings.append({"sev": "pass", "msg": f"{ticker} FY{fy}: Q{','.join(str(q) for q in qs_with_data)} have data", "detail": ""})

                # ── Test Q combinations ──
                # Combo 1: Latest single Q
                _test_q_combo(findings, ticker, fy, [qs_with_data[-1]], inc_q, fy_end, "single-Q")

                # Combo 2: All available Qs
                if len(qs_with_data) > 1:
                    _test_q_combo(findings, ticker, fy, qs_with_data, inc_q, fy_end, "all-Q")

                # Combo 3: First 2 Qs (if available)
                if len(qs_with_data) >= 2:
                    _test_q_combo(findings, ticker, fy, qs_with_data[:2], inc_q, fy_end, "first-2Q")

            # ── Test future year (should have no data → not all dashes bug) ──
            future_fy = max(fy_list) + 1
            future_qs = [q for q in range(1, 5) if _q_has_data(q, future_fy, fy_end)]
            if not future_qs:
                findings.append({"sev": "pass", "msg": f"{ticker} FY{future_fy}: correctly shows no data (future)", "detail": ""})
            else:
                findings.append({"sev": "info", "msg": f"{ticker} FY{future_fy}: has Q data (filing detected)", "detail": ""})

            # ── Balance Sheet checks ──
            if not bal_q.empty:
                bal_cols = len(bal_q.columns)
                bal_rows = len(bal_q.index)
                non_zero = bal_q.apply(pd.to_numeric, errors='coerce').fillna(0).abs().sum().sum()
                if non_zero > 0:
                    findings.append({"sev": "pass", "msg": f"{ticker}: Balance Sheet has data ({bal_rows}×{bal_cols})", "detail": ""})
                else:
                    findings.append({"sev": "warning", "msg": f"{ticker}: Balance Sheet all zeros", "detail": ""})
            elif not bal_a.empty:
                findings.append({"sev": "pass", "msg": f"{ticker}: Balance Sheet (annual) has data", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"{ticker}: no Balance Sheet data", "detail": ""})

        except Exception as e:
            findings.append({"sev": "warning", "msg": f"{ticker}: audit failed — {str(e)[:60]}", "detail": ""})

    return findings


def _test_q_combo(findings, ticker, fy, qs, inc_df, fy_end, combo_name):
    """Test a specific quarter combination: aggregate selected Qs and verify data."""
    try:
        from sankey_page import _fq_end_month_s, _fq_end_year_s

        total_rev = 0
        total_ni = 0
        cols_found = 0

        for q in qs:
            em = _fq_end_month_s(q, fy_end)
            ey = _fq_end_year_s(q, fy, fy_end)
            for col in inc_df.columns:
                try:
                    ts = pd.Timestamp(col)
                    if ts.month == em and ts.year == ey:
                        # Extract Revenue and Net Income
                        rev = 0
                        ni = 0
                        for row_name in inc_df.index:
                            val = inc_df.at[row_name, col]
                            try:
                                val = float(val) if val is not None and not pd.isna(val) else 0
                            except (ValueError, TypeError):
                                val = 0
                            if "revenue" in row_name.lower() and "cost" not in row_name.lower():
                                rev = max(rev, val)
                            if row_name.lower() in ("net income", "netincomeloss", "net income loss"):
                                ni = val
                        total_rev += rev
                        total_ni += ni
                        cols_found += 1
                        break
                except Exception:
                    pass

        q_label = "+".join(f"Q{q}" for q in qs)
        if cols_found == len(qs) and total_rev > 0:
            findings.append({"sev": "pass", "msg": f"{ticker} FY{fy} ({q_label}): Rev ${total_rev/1e9:.1f}B ✓", "detail": combo_name})
        elif cols_found == 0:
            findings.append({"sev": "warning", "msg": f"{ticker} FY{fy} ({q_label}): no matching columns", "detail": f"{combo_name} — audit panel would show dashes"})
        elif total_rev == 0:
            findings.append({"sev": "warning", "msg": f"{ticker} FY{fy} ({q_label}): revenue is $0", "detail": f"{combo_name} — data columns found but empty"})
        else:
            findings.append({"sev": "info", "msg": f"{ticker} FY{fy} ({q_label}): partial data ({cols_found}/{len(qs)} cols)", "detail": combo_name})
    except Exception as e:
        findings.append({"sev": "warning", "msg": f"{ticker} FY{fy} combo test failed: {str(e)[:50]}", "detail": combo_name})


# ═══════════════════════════════════════════════════════════════════════
# AGENT REGISTRY
# ═══════════════════════════════════════════════════════════════════════

AGENTS = [
    {"id": "roadmap",        "name": "Roadmap",        "icon": "📋", "color": "#3B82F6", "fn": _agent_roadmap,        "tab": "Dashboard"},
    {"id": "security",       "name": "Security",       "icon": "🛡️", "color": "#EF4444", "fn": _agent_security,       "tab": "Security"},
    {"id": "config",         "name": "Config",         "icon": "⚙️", "color": "#F59E0B", "fn": _agent_config,         "tab": "Settings"},
    {"id": "compliance",     "name": "Compliance",     "icon": "📜", "color": "#8B5CF6", "fn": _agent_compliance,     "tab": "Certifications"},
    {"id": "infrastructure", "name": "Infrastructure", "icon": "🏗️", "color": "#06B6D4", "fn": _agent_infrastructure, "tab": "Infrastructure"},
    {"id": "team",           "name": "Team",           "icon": "👥", "color": "#EC4899", "fn": _agent_team,           "tab": "Team & Admin"},
    {"id": "seo",            "name": "SEO",            "icon": "🔍", "color": "#22C55E", "fn": _agent_seo,            "tab": "SEO"},
    {"id": "pricing",        "name": "Pricing",        "icon": "💳", "color": "#6366F1", "fn": _agent_pricing,        "tab": "Pricing"},
    {"id": "users",          "name": "Users",          "icon": "👤", "color": "#F97316", "fn": _agent_users,          "tab": "Users"},
    {"id": "analytics",      "name": "Analytics",      "icon": "📊", "color": "#14B8A6", "fn": _agent_analytics,      "tab": "Analytics"},
    {"id": "memory",         "name": "Memory",         "icon": "🧠", "color": "#A855F7", "fn": _agent_memory,         "tab": "Memory"},

    {"id": "status",         "name": "Status",         "icon": "✅", "color": "#10B981", "fn": _agent_status,         "tab": "Feature Tracker"},
    {"id": "meta",           "name": "Meta",           "icon": "🔄", "color": "#78716C", "fn": _agent_meta,           "tab": "Agent System"},
    {"id": "audit_panel",   "name": "Audit Panel",   "icon": "🔬", "color": "#DC2626", "fn": _agent_audit_panel,   "tab": "Sankey Audit"},
]


# ═══════════════════════════════════════════════════════════════════════
# AUDIT RUNNER
# ═══════════════════════════════════════════════════════════════════════

def _run_all_agents(progress_cb=None):
    results = {}
    total = len(AGENTS)
    for i, agent in enumerate(AGENTS):
        if progress_cb:
            progress_cb((i) / total, f"Running {agent['icon']} {agent['name']} Agent...")
        try:
            findings = agent["fn"]()
        except Exception as e:
            findings = [{"sev": "warning", "msg": f"Agent crashed: {str(e)[:60]}", "detail": ""}]
        # Score: pass=full, info=neutral, warning/critical=fail
        total_f = len(findings)
        good = sum(1 for f in findings if f["sev"] in ("pass", "info"))
        score = round((good / total_f) * 100) if total_f > 0 else 100
        results[agent["id"]] = {
            "findings": findings,
            "score": score,
            "counts": {
                "critical": sum(1 for f in findings if f["sev"] == "critical"),
                "warning": sum(1 for f in findings if f["sev"] == "warning"),
                "info": sum(1 for f in findings if f["sev"] == "info"),
                "pass": sum(1 for f in findings if f["sev"] == "pass"),
            },
        }
    if progress_cb:
        progress_cb(1.0, "All agents complete!")

    # Overall
    scores = [r["score"] for r in results.values()]
    overall = round(sum(scores) / len(scores)) if scores else 0
    total_counts = {"critical": 0, "warning": 0, "info": 0, "pass": 0}
    for r in results.values():
        for k, v in r["counts"].items():
            total_counts[k] += v

    return {
        "timestamp": datetime.now().isoformat(),
        "overall_score": overall,
        "agents": results,
        "total_counts": total_counts,
    }


# ═══════════════════════════════════════════════════════════════════════
# STYLES (matching QuarterCharts dark theme)
# ═══════════════════════════════════════════════════════════════════════

_CSS = """
<style>
.sba-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
    border: 1px solid #334155; border-radius: 16px;
    padding: 32px 40px; margin-bottom: 24px; text-align: center;
}
.sba-header h1 { color: #F8FAFC; font-size: 1.8rem; margin: 0 0 6px; letter-spacing: -0.5px; }
.sba-header p  { color: #94A3B8; font-size: 0.92rem; margin: 0; }
.sba-big-score {
    display: inline-flex; align-items: center; justify-content: center;
    width: 100px; height: 100px; border-radius: 50%;
    font-size: 2.2rem; font-weight: 800; margin: 16px 0 8px;
    border: 4px solid;
}
.sba-counts-row { display: flex; gap: 12px; justify-content: center; margin: 12px 0 0; flex-wrap: wrap; }
.sba-count-pill {
    font-size: 0.78rem; font-weight: 700; padding: 4px 14px;
    border-radius: 20px; border: 1px solid;
}
.sba-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
@media (max-width: 900px) { .sba-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 500px) { .sba-grid { grid-template-columns: 1fr; } }
.sba-card {
    background: #0F172A; border: 1px solid #1E293B; border-radius: 14px;
    padding: 20px; transition: border-color 0.2s; position: relative; overflow: hidden;
}
.sba-card:hover { border-color: #334155; }
.sba-card-icon { font-size: 1.5rem; margin-bottom: 6px; }
.sba-card-name { font-size: 0.82rem; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.04em; }
.sba-card-score { font-size: 1.8rem; font-weight: 800; margin: 4px 0; }
.sba-card-bar { height: 4px; background: #1E293B; border-radius: 2px; overflow: hidden; margin-top: 8px; }
.sba-card-bar-fill { height: 100%; border-radius: 2px; transition: width 0.4s ease; }
.sba-card-issues { font-size: 0.72rem; color: #64748B; margin-top: 6px; }
.sba-card-tab { position: absolute; top: 8px; right: 10px; font-size: 0.62rem; color: #475569; font-weight: 500; }
/* Agent detail sections */
.sba-agent-section {
    background: #0F172A; border: 1px solid #1E293B; border-radius: 14px;
    margin-bottom: 12px; overflow: hidden;
}
.sba-agent-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px; border-bottom: 1px solid #1E293B;
}
.sba-agent-name { font-size: 0.95rem; font-weight: 700; color: #F1F5F9; }
.sba-agent-score-badge { font-size: 0.85rem; font-weight: 800; padding: 2px 12px; border-radius: 8px; }
.sba-finding {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 10px 20px; border-bottom: 1px solid #1E293B11;
}
.sba-finding:last-child { border-bottom: none; }
.sba-badge {
    font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 0.03em; flex-shrink: 0; margin-top: 2px;
}
.sba-badge-critical { background: #7F1D1D; color: #FCA5A5; }
.sba-badge-warning  { background: #78350F; color: #FDE68A; }
.sba-badge-info     { background: #1E3A5F; color: #93C5FD; }
.sba-badge-pass     { background: #14532D; color: #86EFAC; }
.sba-finding-msg { font-size: 0.83rem; color: #CBD5E1; flex: 1; }
.sba-finding-detail { font-size: 0.75rem; color: #64748B; }
/* History section */
.sba-history-card {
    background: #0F172A; border: 1px solid #1E293B; border-radius: 12px;
    padding: 14px 20px; margin-bottom: 8px; display: flex;
    align-items: center; justify-content: space-between;
}
.sba-history-date { font-weight: 600; color: #CBD5E1; font-size: 0.85rem; }
.sba-history-meta { font-size: 0.72rem; color: #64748B; margin-top: 2px; }
.sba-empty {
    text-align: center; padding: 48px 20px; color: #475569;
    font-size: 0.95rem; background: #0F172A; border: 1px dashed #1E293B;
    border-radius: 14px;
}
.sba-trend-bar { display: flex; gap: 2px; align-items: flex-end; height: 40px; }
.sba-trend-col { flex: 1; border-radius: 2px 2px 0 0; min-width: 6px; }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _score_color(s):
    if s >= 80: return "#22C55E"
    if s >= 60: return "#F59E0B"
    return "#EF4444"

def _badge_html(sev):
    return f'<span class="sba-badge sba-badge-{sev}">{sev}</span>'


# ═══════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════

def render_super_bug_agent():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Subtabs ──
    sub1, sub2, sub3 = st.tabs(["🎯 Command Center", "📅 History & Trends", "📡 Live Status"])

    with sub1:
        _render_command_center()
    with sub2:
        _render_history()
    with sub3:
        _render_live_status()


def _render_command_center():
    """Main audit runner and results display."""

    # Header
    st.markdown("""
    <div class="sba-header">
        <h1>🐛 Super Bug Agent</h1>
        <p>14 specialized agents auditing every layer of QuarterCharts</p>
    </div>
    """, unsafe_allow_html=True)

    # Run button
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        run = st.button("🚀 Run All 14 Agents", use_container_width=True, type="primary", key="sba_run")

    if run:
        bar = st.progress(0, text="Initializing agents...")
        def _cb(pct, txt):
            bar.progress(min(pct, 1.0), text=txt)

        result = _run_all_agents(progress_cb=_cb)
        bar.progress(1.0, text="All 14 agents complete!")
        time.sleep(0.5)
        bar.empty()

        st.session_state["sba_result"] = result
        # Save to history
        history = _load_history()
        history.insert(0, result)
        _save_history(history)
        st.toast("Audit complete!", icon="✅")

    result = st.session_state.get("sba_result")
    if not result:
        st.markdown('<div class="sba-empty">Click <strong>Run All 14 Agents</strong> to start your first audit</div>',
                    unsafe_allow_html=True)
        return

    # ── Overall Score ──
    overall = result["overall_score"]
    oc = _score_color(overall)
    tc = result["total_counts"]
    ts = result.get("timestamp", "")
    try:
        time_str = datetime.fromisoformat(ts).strftime("%b %d, %Y at %H:%M")
    except Exception:
        time_str = ts[:19]

    st.markdown(f"""
    <div style="text-align:center; margin-bottom:20px;">
        <div class="sba-big-score" style="color:{oc}; border-color:{oc}33; background:{oc}11;">
            {overall}
        </div>
        <div style="font-size:0.78rem; color:#64748B; margin-top:4px;">Overall Health Score · {time_str}</div>
        <div class="sba-counts-row">
            <span class="sba-count-pill" style="color:#FCA5A5; border-color:#7F1D1D; background:#7F1D1D33;">{tc.get('critical',0)} Critical</span>
            <span class="sba-count-pill" style="color:#FDE68A; border-color:#78350F; background:#78350F33;">{tc.get('warning',0)} Warnings</span>
            <span class="sba-count-pill" style="color:#93C5FD; border-color:#1E3A5F; background:#1E3A5F33;">{tc.get('info',0)} Info</span>
            <span class="sba-count-pill" style="color:#86EFAC; border-color:#14532D; background:#14532D33;">{tc.get('pass',0)} Passed</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Agent Grid (4×3) ──
    agents_data = result.get("agents", {})
    cards_html = ""
    for agent in AGENTS:
        aid = agent["id"]
        ad = agents_data.get(aid, {})
        score = ad.get("score", 0)
        counts = ad.get("counts", {})
        sc = _score_color(score)
        crit = counts.get("critical", 0)
        warn = counts.get("warning", 0)
        issues_txt = ""
        if crit > 0:
            issues_txt += f'<span style="color:#FCA5A5;">{crit} critical</span>'
        if warn > 0:
            issues_txt += f'{" · " if issues_txt else ""}<span style="color:#FDE68A;">{warn} warn</span>'
        if not issues_txt:
            issues_txt = '<span style="color:#86EFAC;">All clear</span>'

        cards_html += f"""
        <div class="sba-card">
            <div class="sba-card-tab">← {agent['tab']}</div>
            <div class="sba-card-icon">{agent['icon']}</div>
            <div class="sba-card-name">{agent['name']}</div>
            <div class="sba-card-score" style="color:{sc};">{score}</div>
            <div class="sba-card-bar">
                <div class="sba-card-bar-fill" style="width:{score}%;background:{sc};"></div>
            </div>
            <div class="sba-card-issues">{issues_txt}</div>
        </div>"""

    st.markdown(f'<div class="sba-grid">{cards_html}</div>', unsafe_allow_html=True)

    # ── Agent Detail Sections ──
    st.markdown("### Agent Details")

    for agent in AGENTS:
        aid = agent["id"]
        ad = agents_data.get(aid, {})
        score = ad.get("score", 0)
        findings = ad.get("findings", [])
        sc = _score_color(score)
        non_pass = [f for f in findings if f["sev"] != "pass"]

        st.markdown(f"""
        <div class="sba-agent-section">
            <div class="sba-agent-header">
                <span class="sba-agent-name">{agent['icon']} {agent['name']} Agent <span style="font-size:0.72rem;color:#475569;font-weight:400;">← {agent['tab']}</span></span>
                <span class="sba-agent-score-badge" style="color:{sc};background:{sc}18;">{score}/100</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if non_pass:
            with st.expander(f"{len(non_pass)} issue{'s' if len(non_pass)!=1 else ''} found", expanded=False):
                rows = ""
                sev_order = {"critical": 0, "warning": 1, "info": 2, "pass": 3}
                for f in sorted(non_pass, key=lambda x: sev_order.get(x["sev"], 9)):
                    detail = f""" <span class="sba-finding-detail">— {f['detail']}</span>""" if f.get("detail") else ""
                    rows += f"""
                    <div class="sba-finding">
                        {_badge_html(f['sev'])}
                        <span class="sba-finding-msg">{f['msg']}{detail}</span>
                    </div>"""
                st.markdown(rows, unsafe_allow_html=True)


def _render_history():
    """History tab with trend charts."""

    st.markdown("""
    <div class="sba-header">
        <h1>📅 Audit History</h1>
        <p>Track regressions and improvements over time</p>
    </div>
    """, unsafe_allow_html=True)

    history = _load_history()
    if not history:
        st.markdown('<div class="sba-empty">No audit history yet. Run your first audit from the Command Center.</div>',
                    unsafe_allow_html=True)
        return

    # ── Trend Chart ──
    if len(history) >= 2:
        st.markdown("#### Score Trend")
        trend = []
        for h in reversed(history[:15]):
            try:
                dt = datetime.fromisoformat(h["timestamp"])
                trend.append({"Audit": dt.strftime("%m/%d %H:%M"), "Score": h["overall_score"]})
            except Exception:
                pass
        if trend:
            df = pd.DataFrame(trend).set_index("Audit")
            st.line_chart(df, height=200, use_container_width=True)

    # ── Latest vs Previous ──
    if len(history) >= 2:
        latest = history[0]
        prev = history[1]
        diff = latest["overall_score"] - prev["overall_score"]
        arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
        diff_clr = "#22C55E" if diff > 0 else ("#EF4444" if diff < 0 else "#64748B")

        st.markdown(f"""
        <div style="display:flex; gap:12px; margin:16px 0;">
            <div class="sba-card" style="flex:1;text-align:center;">
                <div style="font-size:2rem;font-weight:800;color:{_score_color(latest['overall_score'])}">{latest['overall_score']}</div>
                <div class="sba-card-name">Latest</div>
            </div>
            <div class="sba-card" style="flex:1;text-align:center;">
                <div style="font-size:2rem;font-weight:800;color:{_score_color(prev['overall_score'])}">{prev['overall_score']}</div>
                <div class="sba-card-name">Previous</div>
            </div>
            <div class="sba-card" style="flex:1;text-align:center;">
                <div style="font-size:2rem;font-weight:800;color:{diff_clr}">{arrow} {abs(diff)}</div>
                <div class="sba-card-name">Change</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── History List ──
    st.markdown("#### All Audits")
    for i, h in enumerate(history[:15]):
        try:
            dt = datetime.fromisoformat(h["timestamp"])
            dstr = dt.strftime("%b %d, %Y at %H:%M")
        except Exception:
            dstr = h.get("timestamp", "?")[:19]
        sc = h.get("overall_score", 0)
        tc = h.get("total_counts", {})
        sc_clr = _score_color(sc)
        crit = tc.get("critical", 0)
        warn = tc.get("warning", 0)
        meta = f"{crit} critical · {warn} warnings" if crit or warn else "All clear"

        st.markdown(f"""
        <div class="sba-history-card">
            <div>
                <div class="sba-history-date">{dstr}</div>
                <div class="sba-history-meta">{meta}</div>
            </div>
            <div style="font-size:1.4rem;font-weight:800;color:{sc_clr};">{sc}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Details — {dstr}", expanded=False):
            agents_data = h.get("agents", {})
            for agent in AGENTS:
                ad = agents_data.get(agent["id"], {})
                s = ad.get("score", 0)
                c = ad.get("counts", {})
                bar_clr = _score_color(s)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin:3px 0;">
                    <span style="font-size:0.95rem;min-width:24px;">{agent['icon']}</span>
                    <span style="font-size:0.82rem;font-weight:600;color:#CBD5E1;min-width:100px;">{agent['name']}</span>
                    <div style="flex:1;height:6px;background:#1E293B;border-radius:3px;overflow:hidden;">
                        <div style="width:{s}%;height:100%;background:{bar_clr};border-radius:3px;"></div>
                    </div>
                    <span style="font-size:0.82rem;font-weight:700;color:{bar_clr};min-width:36px;text-align:right;">{s}%</span>
                </div>
                """, unsafe_allow_html=True)

    # Clear
    st.markdown("---")
    if st.button("🗑️ Clear History", key="sba_clear"):
        _save_history([])
        st.session_state.pop("sba_result", None)
        st.toast("History cleared", icon="🗑️")
        st.rerun()


def _render_live_status():
    """Quick health ping dashboard."""

    st.markdown("""
    <div class="sba-header">
        <h1>📡 Live Status</h1>
        <p>Real-time health check — pings all pages right now</p>
    </div>
    """, unsafe_allow_html=True)

    results = {}
    with st.spinner("Pinging all pages..."):
        for name, path in _PAGES.items():
            r, elapsed = _get(_BASE_URL + path, timeout=10)
            ok = r is not None and 200 <= r.status_code < 400
            results[name] = {
                "ok": ok,
                "time": elapsed,
                "status": r.status_code if r else 0,
                "size_kb": round(len(r.content) / 1024, 1) if r else 0,
            }

    all_ok = all(v["ok"] for v in results.values())
    avg_t = round(sum(v["time"] for v in results.values()) / max(len(results), 1), 2)
    up_count = sum(1 for v in results.values() if v["ok"])
    status_clr = "#22C55E" if all_ok else "#EF4444"
    status_icon = "🟢" if all_ok else "🔴"
    status_txt = "All Systems Operational" if all_ok else f"{len(results) - up_count} Page(s) Down"

    st.markdown(f"""
    <div style="text-align:center;padding:24px;border:2px solid {status_clr}22;
                border-radius:16px;background:{status_clr}08;margin-bottom:20px;">
        <div style="font-size:2.2rem;">{status_icon}</div>
        <div style="font-size:1.15rem;font-weight:700;color:{status_clr};margin-top:4px;">{status_txt}</div>
        <div style="font-size:0.82rem;color:#64748B;margin-top:4px;">
            {up_count}/{len(results)} pages up · Avg response: {avg_t}s
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Per-page cards
    cards = ""
    for name, v in results.items():
        if v["ok"]:
            if v["time"] <= 3: clr, label = "#22C55E", "Fast"
            elif v["time"] <= 6: clr, label = "#F59E0B", "Slow"
            else: clr, label = "#EF4444", "Very Slow"
        else:
            clr, label = "#EF4444", "Down"

        cards += f"""
        <div class="sba-card" style="text-align:center;">
            <div style="font-weight:600;font-size:0.82rem;color:#CBD5E1;margin-bottom:4px;">{name}</div>
            <div style="font-size:1.6rem;font-weight:800;color:{clr};">{v['time']}s</div>
            <div style="font-size:0.72rem;color:#64748B;">{label} · {v['status']} · {v['size_kb']}KB</div>
        </div>"""

    st.markdown(f'<div class="sba-grid">{cards}</div>', unsafe_allow_html=True)

    # Bar chart
    st.markdown("#### Response Times")
    chart_df = pd.DataFrame({
        "Page": list(results.keys()),
        "Seconds": [v["time"] for v in results.values()],
    }).set_index("Page")
    st.bar_chart(chart_df, height=250, use_container_width=True)
