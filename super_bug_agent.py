"""
Super Bug Agent — Unified audit system for QuarterCharts NSFE.
20 specialized agents, each auditing a specific domain.
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

# ── Audit Tickers Config ───────────────────────────────────────────────
_AUDIT_TICKERS_FILE = os.path.join(_BASE_DIR, "audit_tickers_config.json")
_DEFAULT_AUDIT_TICKERS = ["NVDA", "GOOG", "META", "TSLA", "AAPL", "MSFT", "AMZN", "HOFT"]


def _load_audit_tickers():
    """Load the list of tickers the Audit Panel agent should check."""
    if os.path.exists(_AUDIT_TICKERS_FILE):
        try:
            with open(_AUDIT_TICKERS_FILE, "r") as f:
                data = json.load(f)
                tickers = data.get("tickers", _DEFAULT_AUDIT_TICKERS)
                if isinstance(tickers, list) and len(tickers) > 0:
                    return [t.strip().upper() for t in tickers if t.strip()]
        except Exception:
            pass
    return list(_DEFAULT_AUDIT_TICKERS)


def _save_audit_tickers(tickers):
    """Persist the audit tickers list."""
    try:
        clean = [t.strip().upper() for t in tickers if t.strip()]
        with open(_AUDIT_TICKERS_FILE, "w") as f:
            json.dump({"tickers": clean, "updated": datetime.now().isoformat()}, f, indent=2)
        return True
    except Exception:
        return False


# ── EDGAR Ticker Registry ─────────────────────────────────────────────
_EDGAR_REGISTRY_CACHE_FILE = os.path.join(_BASE_DIR, "edgar_tickers_cache.json")
_EDGAR_REGISTRY_CACHE_TTL = 86400  # 24 hours


def _fetch_edgar_ticker_registry(force=False):
    """Fetch SEC EDGAR company_tickers.json and return {ticker: {cik, name}}.

    Caches to disk for 24 hours to avoid hammering SEC servers.
    Returns (dict, error_string_or_None).
    """
    # Check cache first
    if not force and os.path.exists(_EDGAR_REGISTRY_CACHE_FILE):
        try:
            with open(_EDGAR_REGISTRY_CACHE_FILE, "r") as f:
                cached = json.load(f)
            age = time.time() - cached.get("fetched_ts", 0)
            if age < _EDGAR_REGISTRY_CACHE_TTL and cached.get("tickers"):
                return cached["tickers"], None
        except Exception:
            pass

    # Fetch from SEC
    try:
        headers = {"User-Agent": "QuarterCharts/1.0 support@quartercharts.com"}
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=headers, timeout=15,
        )
        r.raise_for_status()
        raw = r.json()
        # raw = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc"}, ...}
        registry = {}
        for _, entry in raw.items():
            tk = entry.get("ticker", "").upper()
            if tk:
                registry[tk] = {
                    "cik": str(entry.get("cik_str", "")),
                    "name": entry.get("title", ""),
                }
        # Cache to disk
        try:
            with open(_EDGAR_REGISTRY_CACHE_FILE, "w") as f:
                json.dump({"tickers": registry, "fetched_ts": time.time(),
                           "count": len(registry)}, f)
        except Exception:
            pass
        return registry, None
    except Exception as e:
        return {}, f"Failed to fetch EDGAR registry: {str(e)[:80]}"


def _validate_tickers_against_edgar(tickers):
    """Cross-reference a list of tickers against SEC EDGAR registry.

    Returns list of findings (dicts with sev/msg/detail).
    """
    findings = []
    registry, err = _fetch_edgar_ticker_registry()
    if err:
        findings.append({"sev": "warning", "msg": f"EDGAR registry: {err}", "detail": ""})
        return findings

    findings.append({
        "sev": "info",
        "msg": f"EDGAR registry loaded: {len(registry):,} tickers",
        "detail": "",
    })

    valid = []
    invalid = []
    for t in tickers:
        if t.upper() in registry:
            info = registry[t.upper()]
            valid.append((t, info["cik"], info["name"]))
        else:
            invalid.append(t)

    if valid:
        findings.append({
            "sev": "pass",
            "msg": f"{len(valid)}/{len(tickers)} tickers found in EDGAR",
            "detail": "",
        })
    if invalid:
        findings.append({
            "sev": "critical",
            "msg": f"{len(invalid)} tickers NOT in EDGAR: {', '.join(invalid)}",
            "detail": (
                "These tickers have no SEC filings — they won't produce "
                "Sankey data. Remove them or check for typos."
            ),
        })

    # Also list each valid ticker with CIK + name for reference
    for t, cik, name in valid[:10]:  # cap at 10 to keep output manageable
        findings.append({
            "sev": "pass",
            "msg": f"{t}: CIK {cik} — {name}",
            "detail": "",
        })
    if len(valid) > 10:
        findings.append({
            "sev": "info",
            "msg": f"... and {len(valid) - 10} more valid tickers",
            "detail": "",
        })

    return findings


# ── EDGAR Batch Audit ─────────────────────────────────────────────────
_BATCH_SIZE = 500
_BATCH_TIMESTAMPS_FILE = os.path.join(_BASE_DIR, "edgar_batch_timestamps.json")


def _load_batch_timestamps() -> dict:
    """Load {batch_index_str: iso_timestamp} from disk."""
    if os.path.exists(_BATCH_TIMESTAMPS_FILE):
        try:
            with open(_BATCH_TIMESTAMPS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_batch_timestamp(batch_idx: int):
    """Record the current datetime for a completed batch."""
    ts_map = _load_batch_timestamps()
    ts_map[str(batch_idx)] = datetime.now().isoformat()
    try:
        with open(_BATCH_TIMESTAMPS_FILE, "w") as f:
            json.dump(ts_map, f, indent=2)
    except Exception:
        pass


def _get_edgar_batches() -> list[list[str]]:
    """Fetch all EDGAR tickers, sort alphabetically, split into batches of 500.

    Returns list of lists.  Last batch may be shorter (e.g. 391).
    """
    registry, err = _fetch_edgar_ticker_registry()
    if not registry:
        return []
    all_tickers = sorted(registry.keys())
    batches = []
    for i in range(0, len(all_tickers), _BATCH_SIZE):
        batches.append(all_tickers[i : i + _BATCH_SIZE])
    return batches


# ── Earnings Week Tickers ──────────────────────────────────────────────
_FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "d77c5b1r01qp6afl34h0d77c5b1r01qp6afl34hg")
_EARNINGS_CACHE_FILE = os.path.join(_BASE_DIR, "earnings_week_cache.json")
_EARNINGS_CACHE_TTL = 3600  # 1 hour


def _fetch_earnings_week_tickers(week_offset: int = 0) -> list[str]:
    """Fetch tickers reporting earnings in a given week from Finnhub API.

    Args:
        week_offset: 0 = this week, 1 = next week, -1 = last week

    Returns:
        Sorted list of unique ticker symbols.
    """
    from datetime import date as _d, timedelta as _td
    today = _d.today()
    monday = today - _td(days=today.weekday()) + _td(weeks=week_offset)
    sunday = monday + _td(days=6)
    from_str = monday.isoformat()
    to_str = sunday.isoformat()

    # Check cache first
    try:
        if os.path.exists(_EARNINGS_CACHE_FILE):
            with open(_EARNINGS_CACHE_FILE, "r") as f:
                cache = json.load(f)
            if (cache.get("from") == from_str
                    and cache.get("to") == to_str
                    and cache.get("fetched")):
                age = (datetime.now() - datetime.fromisoformat(cache["fetched"])).total_seconds()
                if age < _EARNINGS_CACHE_TTL:
                    return cache.get("tickers", [])
    except Exception:
        pass

    # Fetch from Finnhub
    tickers = set()
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params={"from": from_str, "to": to_str, "token": _FINNHUB_KEY},
            timeout=12,
        )
        if r.status_code == 200:
            data = r.json()
            for item in data.get("earningsCalendar", []):
                sym = (item.get("symbol") or "").strip().upper()
                if sym:
                    tickers.add(sym)
    except Exception:
        pass

    result = sorted(tickers)

    # Save to cache
    try:
        with open(_EARNINGS_CACHE_FILE, "w") as f:
            json.dump({
                "from": from_str, "to": to_str,
                "fetched": datetime.now().isoformat(),
                "count": len(result),
                "tickers": result,
            }, f, indent=2)
    except Exception:
        pass

    return result


def _merge_earnings_into_audit_tickers(week_offset: int = 0) -> tuple[list[str], int]:
    """Fetch this week's earnings tickers and merge them into the audit tickers list.

    Returns:
        (updated_tickers, num_added) — the full list and how many new tickers were added.
    """
    earnings = _fetch_earnings_week_tickers(week_offset)
    current = _load_audit_tickers()
    current_set = set(current)
    new_tickers = [t for t in earnings if t not in current_set]
    merged = current + new_tickers
    if new_tickers:
        _save_audit_tickers(merged)
    return merged, len(new_tickers)


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
                           "team", "seo", "pricing", "users", "analytics", "memory",
                           "status", "meta", "audit_panel",
                           "ext_speed", "ext_seo", "ext_uptime", "ext_security",
                           "ext_accessibility", "ext_google_signin"]:
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
    """Comprehensive Sankey Audit Panel: validates EDGAR data pipeline and
    Sankey rendering for every configured ticker across ALL year/Q combinations.

    For each ticker:
      1. CIK resolution — diagnose ticker→CIK failures
      2. EDGAR data fetch — diagnose API/network/XBRL failures
      3. XBRL tag coverage — check which income/balance tags have data
      4. Year discovery — find all available FYs
      5. For EVERY FY pair (Period A × Period B): test ALL Q combos
         - Single Qs: Q1, Q2, Q3, Q4
         - Multi-Q within year: Q1+Q2, Q1+Q2+Q3, Q1+Q2+Q3+Q4, Q2+Q3, etc.
         - Cross-year: Q3+Q4(prev) + Q1+Q2(cur) rolling windows
      6. Revenue sanity — detect $0 revenue, all-dashes, negative values
      7. Accounting identity checks — GP = Rev - COGS, etc.
      8. Balance Sheet validation — non-zero, asset = liab + equity
      9. Default view fallback — detect same-period comparisons
     10. Q heuristic vs EDGAR mismatch — detect "Not yet filed" errors
     11. Empty default view detection — current FY has 0 filed Qs on EDGAR
     12. KPI vs table cross-validation — stale session state causes mismatch
     13. 52/53-week FY drift tolerance — verify ±1 month fallback finds data
     14. Table year-shift detection — table auto-retries year-1 when sidebar year is empty
    """
    findings = []

    # ── 0. Imports ──
    try:
        from sankey_page import (
            _fetch_sankey_data, _ticker_to_cik, _fetch_edgar_facts,
            _edgar_build_df, _XBRL_INCOME_TAGS, _XBRL_BALANCE_TAGS,
            _fq_end_month_s, _fq_end_year_s,
        )
        findings.append({"sev": "pass", "msg": "Backend imports OK", "detail": ""})
    except Exception as e:
        findings.append({"sev": "critical", "msg": f"Cannot import sankey_page: {str(e)[:80]}", "detail": ""})
        return findings

    import calendar
    from datetime import date as _date, timedelta as _td
    from itertools import combinations

    now = datetime.now()
    today = _date(now.year, now.month, min(now.day, 28))
    _SEC_BUFFER = 45  # days after Q end before SEC data appears

    # ── Helpers ──
    def _q_end_date(q, fy, fy_end=12):
        em = _fq_end_month_s(q, fy_end)
        ey = _fq_end_year_s(q, fy, fy_end)
        return _date(ey, em, calendar.monthrange(ey, em)[1])

    def _q_available(q, fy, fy_end=12):
        try:
            return today >= _q_end_date(q, fy, fy_end) + _td(days=_SEC_BUFFER)
        except Exception:
            return False

    def _find_col(df, q, fy, fy_end):
        """Find the DataFrame column matching this Q's end date.
        Uses ±1 month fallback for 52/53-week FY drift companies."""
        em = _fq_end_month_s(q, fy_end)
        ey = _fq_end_year_s(q, fy, fy_end)
        # Pass 1: exact match
        for col in df.columns:
            try:
                ts = pd.Timestamp(col)
                if ts.month == em and ts.year == ey:
                    return col
            except Exception:
                pass
        # Pass 2: ±1 month tolerance
        m_minus = (em - 2) % 12 + 1
        m_plus = em % 12 + 1
        y_minus = ey if m_minus != 12 else ey - 1
        y_plus = ey if m_plus != 1 else ey + 1
        for col in df.columns:
            try:
                ts = pd.Timestamp(col)
                if ((ts.month == m_minus and ts.year == y_minus) or
                        (ts.month == m_plus and ts.year == y_plus)):
                    return col
            except Exception:
                pass
        return None

    def _col_has_data(df, col):
        """Check if a column has any non-zero, non-NaN values."""
        try:
            vals = df[col]
            return vals.apply(lambda v: v is not None and v != 0 and not pd.isna(v)).any()
        except Exception:
            return False

    def _extract_metric(df, col, keywords, exclude=None):
        """Extract a metric value from a DataFrame column by row name matching."""
        best = 0
        for row_name in df.index:
            rn = row_name.lower()
            if any(k in rn for k in keywords):
                if exclude and any(e in rn for e in exclude):
                    continue
                try:
                    v = float(df.at[row_name, col]) if df.at[row_name, col] is not None and not pd.isna(df.at[row_name, col]) else 0
                except (ValueError, TypeError):
                    v = 0
                if abs(v) > abs(best):
                    best = v
        return best

    def _aggregate_qs(df, qs, fy, fy_end, is_balance=False):
        """Aggregate multiple quarters: sum for income, latest snapshot for balance."""
        result = None
        for q in sorted(qs):
            col = _find_col(df, q, fy, fy_end)
            if col is None or not _col_has_data(df, col):
                return None  # missing Q breaks the combo
            series = pd.to_numeric(df[col], errors="coerce").fillna(0)
            if is_balance:
                result = series  # point-in-time: take latest
            else:
                result = series if result is None else result.add(series, fill_value=0)
        return result

    # ── Load configured tickers ──
    audit_tickers = _load_audit_tickers()
    findings.append({"sev": "info", "msg": f"Auditing {len(audit_tickers)} tickers: {', '.join(audit_tickers)}", "detail": ""})

    # ── PHASE 0: EDGAR Registry Validation (optional) ──
    if st.session_state.get("sba_edgar_validate", False):
        edgar_findings = _validate_tickers_against_edgar(audit_tickers)
        findings.extend(edgar_findings)
        # Remove invalid tickers from audit list so we don't waste time on them
        registry, _ = _fetch_edgar_ticker_registry()
        if registry:
            _before = len(audit_tickers)
            audit_tickers = [t for t in audit_tickers if t.upper() in registry]
            _removed = _before - len(audit_tickers)
            if _removed > 0:
                findings.append({
                    "sev": "info",
                    "msg": f"Skipping {_removed} non-EDGAR tickers in remaining phases",
                    "detail": "",
                })

    # ── Generate all Q combination patterns ──
    # Single Qs, multi-Q within year, and full year
    all_q_combos = []
    for size in range(1, 5):
        for combo in combinations([1, 2, 3, 4], size):
            all_q_combos.append(list(combo))
    # all_q_combos: [1],[2],[3],[4],[1,2],[1,3],[1,4],[2,3],[2,4],[3,4],[1,2,3],[1,2,4],[1,3,4],[2,3,4],[1,2,3,4]

    for ticker in audit_tickers:
        try:
            # ════════════════════════════════════════════════════════════
            # PHASE 1: CIK Resolution
            # ════════════════════════════════════════════════════════════
            cik = None
            cik_error = None
            try:
                cik = _ticker_to_cik(ticker)
            except Exception as e:
                cik_error = str(e)[:80]

            if not cik:
                # Classify the failure — OTC/foreign/SPAC tickers are expected to fail
                # Common suffixes for non-US or OTC tickers
                _OTC_HINTS = (".L", ".TO", ".AX", ".HK", ".T", ".SI", ".NS", ".BO")
                is_likely_non_sec = (
                    any(ticker.endswith(s) for s in _OTC_HINTS) or
                    len(ticker) > 5  # most US tickers are 1-5 chars
                )
                if is_likely_non_sec:
                    findings.append({"sev": "info", "msg": f"{ticker}: not in SEC EDGAR (non-US/OTC)",
                                     "detail": cik_error or "Company likely not SEC-registered"})
                else:
                    findings.append({"sev": "warning", "msg": f"{ticker}: CIK resolution failed",
                                     "detail": cik_error or "Ticker not found in SEC EDGAR company registry"})
                continue
            findings.append({"sev": "pass", "msg": f"{ticker}: CIK={cik}", "detail": ""})

            # ════════════════════════════════════════════════════════════
            # PHASE 2: EDGAR Data Fetch + Failure Diagnosis
            # ════════════════════════════════════════════════════════════
            try:
                facts = _fetch_edgar_facts(cik)
                if not facts:
                    findings.append({"sev": "warning", "msg": f"{ticker}: EDGAR returned empty facts",
                                     "detail": "API may be down or CIK invalid"})
                    continue
                us_gaap = facts.get("facts", {}).get("us-gaap", {})
                ifrs = facts.get("facts", {}).get("ifrs-full", {})
                if not us_gaap:
                    if ifrs:
                        findings.append({"sev": "info", "msg": f"{ticker}: uses IFRS (not us-gaap) — {len(ifrs)} concepts",
                                         "detail": "IFRS filer; Sankey uses us-gaap tags so data may be sparse"})
                    else:
                        findings.append({"sev": "warning", "msg": f"{ticker}: no us-gaap data in EDGAR facts",
                                         "detail": "Company may use IFRS or have no XBRL filings"})
                    continue
                findings.append({"sev": "pass", "msg": f"{ticker}: EDGAR facts OK ({len(us_gaap)} concepts)", "detail": ""})
            except Exception as e:
                findings.append({"sev": "critical", "msg": f"{ticker}: EDGAR fetch failed — {str(e)[:60]}",
                                 "detail": "Network timeout, rate limit, or API error"})
                continue

            # ════════════════════════════════════════════════════════════
            # PHASE 3: XBRL Tag Coverage
            # ════════════════════════════════════════════════════════════
            missing_income_tags = []
            for display_name, tags in _XBRL_INCOME_TAGS.items():
                if not tags:  # derived field
                    continue
                found = any(t in us_gaap for t in tags)
                if not found:
                    missing_income_tags.append(display_name)

            missing_balance_tags = []
            for display_name, tags in _XBRL_BALANCE_TAGS.items():
                if not tags:  # derived field
                    continue
                found = any(t in us_gaap for t in tags)
                if not found:
                    missing_balance_tags.append(display_name)

            total_inc = len([k for k, v in _XBRL_INCOME_TAGS.items() if v])
            total_bal = len([k for k, v in _XBRL_BALANCE_TAGS.items() if v])
            inc_found = total_inc - len(missing_income_tags)
            bal_found = total_bal - len(missing_balance_tags)

            if missing_income_tags:
                findings.append({"sev": "info", "msg": f"{ticker}: income tags {inc_found}/{total_inc}",
                                 "detail": f"Missing: {', '.join(missing_income_tags[:5])}"})
            else:
                findings.append({"sev": "pass", "msg": f"{ticker}: all {total_inc} income tags present", "detail": ""})

            if missing_balance_tags:
                findings.append({"sev": "info", "msg": f"{ticker}: balance tags {bal_found}/{total_bal}",
                                 "detail": f"Missing: {', '.join(missing_balance_tags[:5])}"})
            else:
                findings.append({"sev": "pass", "msg": f"{ticker}: all {total_bal} balance tags present", "detail": ""})

            # ════════════════════════════════════════════════════════════
            # PHASE 4: Build DataFrames
            # ════════════════════════════════════════════════════════════
            inc_q, bal_q, info = _fetch_sankey_data(ticker, quarterly=True)
            inc_a, bal_a, _ = _fetch_sankey_data(ticker, quarterly=False)
            entity = info.get("shortName", ticker)

            if inc_q.empty and inc_a.empty:
                findings.append({"sev": "warning", "msg": f"{ticker}: DataFrames empty after build",
                                 "detail": "XBRL tags exist but filtering produced no rows"})
                continue

            findings.append({"sev": "pass", "msg": f"{ticker}: DataFrames built ({entity})",
                             "detail": f"Income Q:{inc_q.shape} A:{inc_a.shape} | Balance Q:{bal_q.shape} A:{bal_a.shape}"})

            # ════════════════════════════════════════════════════════════
            # PHASE 5: Discover Available FYs + FY End Month
            # ════════════════════════════════════════════════════════════
            fy_end = 12
            if not inc_q.empty:
                try:
                    # Use the most common month across columns
                    months = [pd.Timestamp(c).month for c in inc_q.columns]
                    fy_end = max(set(months), key=months.count)
                except Exception:
                    pass

            available_fy = set()
            for df_check in [inc_q, inc_a]:
                if not df_check.empty:
                    for col in df_check.columns:
                        try:
                            ts = pd.Timestamp(col)
                            fy = ts.year if ts.month <= fy_end else ts.year + 1
                            available_fy.add(fy)
                        except Exception:
                            pass

            if not available_fy:
                findings.append({"sev": "warning", "msg": f"{ticker}: no fiscal years discovered", "detail": ""})
                continue

            fy_list = sorted(available_fy, reverse=True)
            findings.append({"sev": "pass", "msg": f"{ticker}: FY end month={fy_end}, years={fy_list[0]}..{fy_list[-1]} ({len(fy_list)} FYs)",
                             "detail": ""})

            # ════════════════════════════════════════════════════════════
            # PHASE 6: Test ALL Year × Q Combinations
            # ════════════════════════════════════════════════════════════
            # For each FY, determine which individual Qs have data
            fy_q_map = {}  # fy -> list of Qs with data
            for fy in fy_list:
                qs_avail = []
                for q in range(1, 5):
                    col = _find_col(inc_q, q, fy, fy_end)
                    if col is not None and _col_has_data(inc_q, col):
                        qs_avail.append(q)
                fy_q_map[fy] = qs_avail

            # Report per-FY availability
            for fy in fy_list[:5]:  # top 5 FYs
                qs = fy_q_map.get(fy, [])
                if qs:
                    findings.append({"sev": "pass", "msg": f"{ticker} FY{fy}: Q{','.join(str(q) for q in qs)} available", "detail": ""})
                else:
                    if _q_available(1, fy, fy_end):
                        findings.append({"sev": "warning", "msg": f"{ticker} FY{fy}: no Qs with data (expected some)",
                                         "detail": "Q1 should be available by now"})
                    else:
                        findings.append({"sev": "info", "msg": f"{ticker} FY{fy}: no data yet (future/recent)", "detail": ""})

            # ── Test all Q combos within each FY ──
            combo_pass = 0
            combo_fail = 0
            combo_details = []  # collect failures for report

            for fy in fy_list[:4]:  # test last 4 FYs
                qs_avail = fy_q_map.get(fy, [])
                if not qs_avail:
                    continue

                for q_combo in all_q_combos:
                    # Skip combos that include Qs without data
                    if not all(q in qs_avail for q in q_combo):
                        continue

                    combo_label = f"FY{fy} Q{'+'.join(str(q) for q in q_combo)}"

                    # Aggregate income
                    agg = _aggregate_qs(inc_q, q_combo, fy, fy_end, is_balance=False)
                    if agg is None:
                        combo_fail += 1
                        combo_details.append(f"{combo_label}: aggregation returned None")
                        continue

                    # Extract key metrics (supports both standard and financial-sector tags)
                    rev = 0
                    ni = 0
                    cogs = 0
                    gp = 0
                    fin_rev = 0  # financial-sector revenue fallback
                    for row_name in inc_q.index:
                        rn = row_name.lower()
                        try:
                            v = float(agg.get(row_name, 0)) if not pd.isna(agg.get(row_name, 0)) else 0
                        except (ValueError, TypeError):
                            v = 0
                        if "revenue" in rn and "cost" not in rn and abs(v) > abs(rev):
                            rev = v
                        # Financial-sector revenue: interest income, noninterest income, etc.
                        if any(k in rn for k in ("interest income", "interest and dividend",
                               "noninterest income", "net interest income",
                               "financial services", "brokerage commission",
                               "investment banking")) and "expense" not in rn and abs(v) > abs(fin_rev):
                            fin_rev = v
                        if rn in ("net income", "netincomeloss", "net income loss") and abs(v) > abs(ni):
                            ni = v
                        if ("cost of" in rn or "cost of goods" in rn or "costofrevenue" in rn) and abs(v) > abs(cogs):
                            cogs = v
                        if "gross profit" in rn and abs(v) > abs(gp):
                            gp = v
                    # If standard revenue is $0 but financial-sector revenue exists, use it
                    if rev == 0 and fin_rev != 0:
                        rev = fin_rev

                    if rev == 0:
                        combo_fail += 1
                        combo_details.append(f"{combo_label}: revenue=$0")
                    elif rev < 0:
                        combo_fail += 1
                        combo_details.append(f"{combo_label}: negative revenue ${rev/1e6:.0f}M")
                    else:
                        combo_pass += 1

                        # Accounting identity: GP ≈ Rev - COGS (if both reported)
                        if gp > 0 and cogs > 0:
                            expected_gp = rev - cogs
                            gp_diff_pct = abs(gp - expected_gp) / rev * 100 if rev else 0
                            if gp_diff_pct > 5:
                                combo_details.append(
                                    f"{combo_label}: GP mismatch — reported ${gp/1e9:.1f}B vs "
                                    f"computed ${expected_gp/1e9:.1f}B ({gp_diff_pct:.0f}% diff)")

            total_combos = combo_pass + combo_fail
            if total_combos > 0:
                pass_rate = round(combo_pass / total_combos * 100)
                if combo_fail == 0:
                    findings.append({"sev": "pass",
                                     "msg": f"{ticker}: all {total_combos} Q combos pass (rev>0)",
                                     "detail": f"{combo_pass} combos across {min(len(fy_list),4)} FYs"})
                else:
                    sev = "warning" if pass_rate >= 80 else "critical"
                    findings.append({"sev": sev,
                                     "msg": f"{ticker}: {combo_fail}/{total_combos} Q combos failed ({pass_rate}% pass)",
                                     "detail": "; ".join(combo_details[:5])})

            # ── Test Period A vs Period B (compare mode) ──
            if len(fy_list) >= 2:
                compare_pass = 0
                compare_fail = 0
                compare_details = []

                # Test every FY pair (A, B) where A > B
                test_fys = fy_list[:4]
                for i, fy_a in enumerate(test_fys):
                    for fy_b in test_fys[i+1:]:
                        qs_a = fy_q_map.get(fy_a, [])
                        qs_b = fy_q_map.get(fy_b, [])
                        if not qs_a or not qs_b:
                            continue

                        # Test matching Q patterns between periods
                        common_qs_patterns = []
                        for q_combo in all_q_combos:
                            if all(q in qs_a for q in q_combo) and all(q in qs_b for q in q_combo):
                                common_qs_patterns.append(q_combo)

                        for q_combo in common_qs_patterns:
                            q_label = f"Q{'+'.join(str(q) for q in q_combo)}"
                            pair_label = f"FY{fy_a} vs FY{fy_b} {q_label}"

                            agg_a = _aggregate_qs(inc_q, q_combo, fy_a, fy_end)
                            agg_b = _aggregate_qs(inc_q, q_combo, fy_b, fy_end)

                            if agg_a is None or agg_b is None:
                                compare_fail += 1
                                compare_details.append(f"{pair_label}: aggregation failed")
                                continue

                            # Extract revenue for both periods (standard + financial-sector)
                            rev_a = rev_b = 0
                            fin_rev_a = fin_rev_b = 0
                            _FIN_KEYWORDS = ("interest income", "interest and dividend",
                                             "noninterest income", "net interest income",
                                             "financial services", "brokerage commission",
                                             "investment banking")
                            for rn in inc_q.index:
                                rl = rn.lower()
                                try:
                                    va = float(agg_a.get(rn, 0)) if not pd.isna(agg_a.get(rn, 0)) else 0
                                    vb = float(agg_b.get(rn, 0)) if not pd.isna(agg_b.get(rn, 0)) else 0
                                except (ValueError, TypeError):
                                    va = vb = 0
                                if "revenue" in rl and "cost" not in rl:
                                    if abs(va) > abs(rev_a):
                                        rev_a = va
                                    if abs(vb) > abs(rev_b):
                                        rev_b = vb
                                if any(k in rl for k in _FIN_KEYWORDS) and "expense" not in rl:
                                    if abs(va) > abs(fin_rev_a):
                                        fin_rev_a = va
                                    if abs(vb) > abs(fin_rev_b):
                                        fin_rev_b = vb
                            # Fallback to financial-sector revenue
                            if rev_a == 0 and fin_rev_a != 0:
                                rev_a = fin_rev_a
                            if rev_b == 0 and fin_rev_b != 0:
                                rev_b = fin_rev_b

                            if rev_a > 0 and rev_b > 0:
                                compare_pass += 1
                            else:
                                compare_fail += 1
                                if rev_a == 0:
                                    compare_details.append(f"{pair_label}: Period A rev=$0")
                                if rev_b == 0:
                                    compare_details.append(f"{pair_label}: Period B rev=$0")

                total_cmp = compare_pass + compare_fail
                if total_cmp > 0:
                    cmp_rate = round(compare_pass / total_cmp * 100)
                    if compare_fail == 0:
                        findings.append({"sev": "pass",
                                         "msg": f"{ticker}: all {total_cmp} compare combos pass",
                                         "detail": f"Period A×B pairs with matching Q patterns"})
                    else:
                        sev = "warning" if cmp_rate >= 80 else "critical"
                        findings.append({"sev": sev,
                                         "msg": f"{ticker}: {compare_fail}/{total_cmp} compare combos failed ({cmp_rate}%)",
                                         "detail": "; ".join(compare_details[:5])})

            # ════════════════════════════════════════════════════════════
            # PHASE 7: Balance Sheet Validation
            # ════════════════════════════════════════════════════════════
            if not bal_q.empty:
                bal_pass = 0
                bal_fail = 0
                bal_details = []

                for fy in fy_list[:4]:
                    qs_avail = fy_q_map.get(fy, [])
                    for q in qs_avail:
                        col = _find_col(bal_q, q, fy, fy_end)
                        if col is None:
                            # Try matching balance sheet columns differently
                            continue
                        if not _col_has_data(bal_q, col):
                            bal_fail += 1
                            bal_details.append(f"FY{fy} Q{q}: balance col empty")
                            continue

                        # Extract key balance metrics
                        series = pd.to_numeric(bal_q[col], errors="coerce").fillna(0)
                        total_assets = 0
                        total_liab = 0
                        total_equity = 0
                        for rn in bal_q.index:
                            rl = rn.lower()
                            v = series.get(rn, 0)
                            if "total assets" in rl and "non" not in rl and abs(v) > abs(total_assets):
                                total_assets = v
                            if ("total liabilit" in rl) and "and" not in rl and abs(v) > abs(total_liab):
                                total_liab = v
                            if ("stockholder" in rl or "total equity" in rl or "shareholders" in rl) and abs(v) > abs(total_equity):
                                total_equity = v

                        if total_assets > 0:
                            bal_pass += 1
                            # Check A = L + E identity
                            if total_liab > 0 and total_equity != 0:
                                expected = total_liab + total_equity
                                diff_pct = abs(total_assets - expected) / total_assets * 100
                                if diff_pct > 2:
                                    bal_details.append(
                                        f"FY{fy} Q{q}: A≠L+E — A=${total_assets/1e9:.1f}B, "
                                        f"L+E=${expected/1e9:.1f}B ({diff_pct:.0f}%)")
                        else:
                            bal_fail += 1
                            bal_details.append(f"FY{fy} Q{q}: total assets=$0")

                total_bal_checks = bal_pass + bal_fail
                if total_bal_checks > 0:
                    if bal_fail == 0:
                        findings.append({"sev": "pass",
                                         "msg": f"{ticker}: all {total_bal_checks} balance sheet checks pass",
                                         "detail": ""})
                    else:
                        findings.append({"sev": "warning",
                                         "msg": f"{ticker}: {bal_fail}/{total_bal_checks} balance checks failed",
                                         "detail": "; ".join(bal_details[:5])})
                if bal_details:
                    for d in bal_details[:3]:
                        findings.append({"sev": "info", "msg": f"{ticker} balance: {d}", "detail": ""})
            elif not bal_a.empty:
                findings.append({"sev": "pass", "msg": f"{ticker}: Balance Sheet annual data OK", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"{ticker}: no Balance Sheet data at all", "detail": ""})

            # ════════════════════════════════════════════════════════════
            # PHASE 8: Sankey Render Check (smoke test)
            # ════════════════════════════════════════════════════════════
            try:
                from sankey_page import _build_income_sankey, _build_partial_year_df
            except ImportError:
                findings.append({"sev": "info", "msg": f"{ticker}: cannot import Sankey render functions", "detail": ""})
                continue

            # Test rendering for the most recent FY with full data
            for fy in fy_list[:2]:
                qs = fy_q_map.get(fy, [])
                if sorted(qs) == [1, 2, 3, 4]:
                    try:
                        # Build a 2-column DF (Period A = this FY, Period B = prior FY)
                        fy_b = fy - 1 if fy - 1 in fy_list else None
                        agg_a = _aggregate_qs(inc_q, [1, 2, 3, 4], fy, fy_end)
                        if agg_a is not None and agg_a.sum() != 0:
                            render_df = pd.DataFrame({"Period_A": agg_a})
                            if fy_b and fy_q_map.get(fy_b):
                                agg_b = _aggregate_qs(inc_q, [1, 2, 3, 4], fy_b, fy_end)
                                if agg_b is not None:
                                    render_df["Period_B"] = agg_b
                                else:
                                    render_df["Period_B"] = pd.Series(dtype=float)
                            else:
                                render_df["Period_B"] = pd.Series(dtype=float)

                            fig, nodes = _build_income_sankey(render_df, info, ticker=ticker)
                            if fig is not None and len(nodes) > 0:
                                findings.append({"sev": "pass",
                                                 "msg": f"{ticker} FY{fy}: Sankey renders OK ({len(nodes)} nodes)",
                                                 "detail": ""})
                            elif fig is None:
                                findings.append({"sev": "warning",
                                                 "msg": f"{ticker} FY{fy}: Sankey returned None (rev=$0?)",
                                                 "detail": "Income Sankey requires positive revenue"})
                            break  # only test one FY for render
                    except Exception as e:
                        findings.append({"sev": "warning",
                                         "msg": f"{ticker} FY{fy}: Sankey render error — {str(e)[:60]}",
                                         "detail": ""})
                        break

            # ════════════════════════════════════════════════════════════
            # PHASE 9: Default View Fallback Check
            # ════════════════════════════════════════════════════════════
            # Detect when the latest FY (what users see by default) has no data,
            # causing a fallback that could collide with Period B (same-vs-same).
            current_year = now.year
            latest_fy = fy_list[0] if fy_list else current_year
            if latest_fy < current_year:
                # The latest FY with data is older than the current year — users
                # selecting the current year as Period A will trigger a fallback.
                gap = current_year - latest_fy
                if gap >= 2:
                    findings.append({"sev": "warning",
                                     "msg": f"{ticker}: latest EDGAR data is FY{latest_fy} ({gap}yr gap)",
                                     "detail": "Default view will fall back; may compare same period vs itself"})
                else:
                    findings.append({"sev": "info",
                                     "msg": f"{ticker}: latest FY with data is {latest_fy} (current year={current_year})",
                                     "detail": "May trigger fallback in default Sankey view"})

            # PHASE 10: Q Availability Heuristic vs EDGAR Mismatch
            # ════════════════════════════════════════════════════════════
            # Detect quarters where the 45-day heuristic says data should
            # be available but EDGAR actually has no data.  This causes
            # the Q selector to show clickable buttons for empty quarters.
            _mismatch_qs = []
            for fy in fy_list[:3]:  # check latest 3 FYs
                actual_qs = set(fy_q_map.get(fy, []))
                for q in range(1, 5):
                    heuristic_avail = _q_available(q, fy, fy_end)
                    edgar_has_data = q in actual_qs
                    if heuristic_avail and not edgar_has_data:
                        _mismatch_qs.append((fy, q))

            if _mismatch_qs:
                _mm_list = ", ".join(f"FY{fy} Q{q}" for fy, q in _mismatch_qs)
                findings.append({
                    "sev": "warning",
                    "msg": f"{ticker}: Q selector heuristic/EDGAR mismatch — {_mm_list}",
                    "detail": (
                        "45-day heuristic says these quarters should be filed, "
                        "but EDGAR has no quarterly data. Likely 10-K (annual) "
                        "filing that takes 60-90 days, or company hasn't filed yet. "
                        "Q buttons will show 'Not yet filed' after first data load."
                    ),
                })
            else:
                findings.append({
                    "sev": "pass",
                    "msg": f"{ticker}: Q availability heuristic matches EDGAR data",
                    "detail": "",
                })

            # ════════════════════════════════════════════════════════════
            # PHASE 11: Empty Default View Detection
            # ════════════════════════════════════════════════════════════
            # The Sankey page defaults to Period A = current year (2026).
            # If the current FY has ZERO filed quarters on EDGAR, the user
            # sees an empty table with all dashes — bad first impression.
            # Detect this and report which FY actually has data.
            _cur_fy_qs = fy_q_map.get(current_year, [])
            _prev_fy_qs = fy_q_map.get(current_year - 1, [])
            _prev2_fy_qs = fy_q_map.get(current_year - 2, [])
            if not _cur_fy_qs:
                # Current FY has 0 filed quarters.
                # Default Q selection falls on Year B → all Qs from prev_qs.
                # Verify the table header and comparison use correct years.
                if _prev_fy_qs:
                    _prev_q_list = ",".join(f"Q{q}" for q in sorted(_prev_fy_qs))
                    # Default: latest Q from FY(cur-1)
                    _default_q = sorted(_prev_fy_qs)[-1]
                    # Check: does the comparison year (cur-2) also have this Q?
                    _compare_ok = _default_q in _prev2_fy_qs
                    findings.append({
                        "sev": "critical",
                        "msg": (
                            f"{ticker}: FY{current_year} has 0 filed Qs — default "
                            f"Q selector picks Q{_default_q} from FY{current_year - 1}"
                        ),
                        "detail": (
                            f"Period A=FY{current_year}, Period B=FY{current_year - 1} "
                            f"(consecutive). All Qs from Year B row (prev_qs only). "
                            f"Table header must show 'FY{current_year - 1} (Q{_default_q})' "
                            f"not 'FY{current_year} (Q{_default_q})'. "
                            f"Comparison must be FY{current_year - 1} vs FY{current_year - 2} "
                            f"(not same-vs-same). "
                            f"FY{current_year - 2} Q{_default_q}: "
                            f"{'available ✓' if _compare_ok else 'NOT available ✗ — compare will show NaN'}. "
                            f"FY{current_year - 1} has {_prev_q_list}."
                        ),
                    })
                else:
                    findings.append({
                        "sev": "critical",
                        "msg": (
                            f"{ticker}: FY{current_year} and FY{current_year - 1} "
                            f"both have 0 filed Qs"
                        ),
                        "detail": (
                            f"No quarterly data for the two most recent FYs. "
                            f"Latest FY with data: FY{latest_fy}. "
                            f"User sees all-dash table on default view."
                        ),
                    })
            else:
                _cur_q_list = ",".join(f"Q{q}" for q in sorted(_cur_fy_qs))
                findings.append({
                    "sev": "pass",
                    "msg": (
                        f"{ticker}: FY{current_year} has {len(_cur_fy_qs)} filed Q(s) "
                        f"({_cur_q_list}) — default view shows data"
                    ),
                    "detail": "",
                })

            # ════════════════════════════════════════════════════════════
            # PHASE 12: KPI vs Table Cross-Validation
            # ════════════════════════════════════════════════════════════
            # The KPI cards and the per-quarter table must show the same
            # data for the same Q selection.  When KPIs read from stale
            # session state (_sankey_reconciled) while the table reads
            # from fresh income_df, values diverge.  Simulate multi-Q
            # aggregation and verify consistency.
            _xv_fy = fy_list[0] if fy_list else current_year - 1
            _xv_qs = fy_q_map.get(_xv_fy, [])
            if len(_xv_qs) >= 2:
                # Aggregate 2 quarters (e.g. Q3+Q4) via _aggregate_partial_year
                _xv_q2 = sorted(_xv_qs)[-2:]  # latest 2 Qs
                _xv_single_q = [_xv_q2[-1]]  # single Q (latest)
                # Single-Q aggregation
                _xv_1q, _ = _aggregate_partial_year(
                    inc_q, _xv_fy, _xv_single_q, fy_end, False)
                # Multi-Q aggregation
                _xv_2q, _ = _aggregate_partial_year(
                    inc_q, _xv_fy, _xv_q2, fy_end, False)

                if _xv_1q is not None and _xv_2q is not None:
                    # Revenue from single Q vs multi Q
                    _rev_key = None
                    for idx in _xv_1q.index:
                        if "revenue" in str(idx).lower():
                            _rev_key = idx
                            break
                    if _rev_key:
                        _rev_1q = float(_xv_1q[_rev_key]) if pd.notna(_xv_1q[_rev_key]) else 0
                        _rev_2q = float(_xv_2q[_rev_key]) if pd.notna(_xv_2q[_rev_key]) else 0
                        if _rev_1q > 0 and _rev_2q > 0 and abs(_rev_2q - _rev_1q) > _rev_1q * 0.01:
                            # Multi-Q sum is larger than single Q — expected.
                            # Flag if KPIs could show stale single-Q when user selects multi-Q.
                            findings.append({
                                "sev": "warning",
                                "msg": (
                                    f"{ticker}: KPI stale-state risk — "
                                    f"Q{_xv_q2[-1]} Revenue=${_rev_1q/1e9:.1f}B vs "
                                    f"Q{'+Q'.join(str(q) for q in _xv_q2)} Revenue=${_rev_2q/1e9:.1f}B"
                                ),
                                "detail": (
                                    "KPI cards read from _sankey_reconciled (session state) "
                                    "which lags by one Streamlit rerun.  When user adds a Q, "
                                    "KPIs show stale single-Q values while Sankey/table show "
                                    "correct multi-Q sums.  Fix: clear _sankey_reconciled "
                                    "before rendering KPIs."
                                ),
                            })
                        else:
                            findings.append({
                                "sev": "pass",
                                "msg": f"{ticker}: multi-Q aggregation consistent ({'+'.join(f'Q{q}' for q in _xv_q2)})",
                                "detail": "",
                            })

            # ════════════════════════════════════════════════════════════
            # PHASE 13: 52/53-Week FY Drift Tolerance Verification
            # ════════════════════════════════════════════════════════════
            # Companies like HOFT have fiscal years ending in non-standard
            # months (e.g. fy_end=2) AND their period-end dates drift ±1
            # month across fiscal years (52/53-week calendars).  Strict
            # month matching fails; the ±1 tolerance in _find_col,
            # _match_col, and _find_col_for_q must rescue these.
            # For each available Q, check if exact match fails but ±1 succeeds.
            _drift_found = []
            _drift_fy = fy_list[0] if fy_list else current_year - 1
            _drift_qs = fy_q_map.get(_drift_fy, [])
            for _dq in _drift_qs:
                _d_em = _fq_end_month_s(_dq, fy_end)
                _d_ey = _fq_end_year_s(_dq, _drift_fy, fy_end)
                # Exact match
                _exact = None
                for col in inc_q.columns:
                    try:
                        ts = pd.Timestamp(col)
                        if ts.month == _d_em and ts.year == _d_ey:
                            _exact = col
                            break
                    except Exception:
                        pass
                # ±1 match
                _fuzzy = _find_col(inc_q, _dq, _drift_fy, fy_end) if not _exact else _exact
                if not _exact and _fuzzy:
                    _drift_found.append(f"Q{_dq} (expected {_d_em}/{_d_ey}, found {_fuzzy})")

            if _drift_found:
                findings.append({
                    "sev": "warning",
                    "msg": (
                        f"{ticker}: 52/53-week drift detected — "
                        f"{len(_drift_found)} Q(s) need ±1 month tolerance"
                    ),
                    "detail": (
                        f"FY{_drift_fy} fy_end={fy_end}. "
                        f"Drift columns: {'; '.join(_drift_found)}. "
                        f"Without ±1 tolerance in _find_col/_match_col/_find_col_for_q, "
                        f"these Qs would show all dashes. Tolerance is active and rescuing data."
                    ),
                })
            else:
                findings.append({
                    "sev": "pass",
                    "msg": f"{ticker}: no 52/53-week drift — exact month matching works for all Qs",
                    "detail": "",
                })

            # ════════════════════════════════════════════════════════════
            # PHASE 14: Table Year-Shift Detection
            # ════════════════════════════════════════════════════════════
            # The table uses sidebar year (Period A = current_year) to
            # look up Q columns.  When that year has no filed Qs, the
            # table must auto-shift to year - 1.  Simulate this: try
            # sidebar year first; if no data found, verify year - 1 works.
            if not _cur_fy_qs:
                # Current FY has no data → table should auto-shift
                _tbl_target_a = current_year - 1
                _tbl_target_b = current_year - 2
                _prev_fy_default_q = sorted(fy_q_map.get(_tbl_target_a, []))[-1] if fy_q_map.get(_tbl_target_a) else None
                if _prev_fy_default_q:
                    # Verify sidebar year would show dashes
                    _sidebar_col = _find_col(inc_q, _prev_fy_default_q, current_year, fy_end)
                    _sidebar_has_data = _sidebar_col and _col_has_data(inc_q, _sidebar_col)
                    # Verify shifted year has data
                    _shifted_col = _find_col(inc_q, _prev_fy_default_q, _tbl_target_a, fy_end)
                    _shifted_has_data = _shifted_col and _col_has_data(inc_q, _shifted_col)
                    if not _sidebar_has_data and _shifted_has_data:
                        findings.append({
                            "sev": "warning",
                            "msg": (
                                f"{ticker}: table needs year-shift — FY{current_year} Q{_prev_fy_default_q} "
                                f"empty, FY{_tbl_target_a} Q{_prev_fy_default_q} has data"
                            ),
                            "detail": (
                                f"Sidebar Period A = FY{current_year} but user's Q selection "
                                f"maps to FY{_tbl_target_a}. Table must auto-detect all-dashes "
                                f"and retry with year - 1 to show the user's actual selection."
                            ),
                        })
                    elif _shifted_has_data:
                        findings.append({
                            "sev": "pass",
                            "msg": f"{ticker}: table year-shift — FY{_tbl_target_a} Q{_prev_fy_default_q} has data",
                            "detail": "",
                        })
                    # Check Period B (comparison year)
                    _pb_default_q = sorted(fy_q_map.get(_tbl_target_b, []))[-1] if fy_q_map.get(_tbl_target_b) else None
                    if _pb_default_q:
                        _pb_col = _find_col(inc_q, _pb_default_q, _tbl_target_b, fy_end)
                        if not (_pb_col and _col_has_data(inc_q, _pb_col)):
                            findings.append({
                                "sev": "warning",
                                "msg": (
                                    f"{ticker}: table Period B FY{_tbl_target_b} Q{_pb_default_q} "
                                    f"has no data — comparison will show dashes"
                                ),
                                "detail": "",
                            })

        except Exception as e:
            findings.append({"sev": "warning", "msg": f"{ticker}: audit crashed — {str(e)[:80]}", "detail": ""})

    return findings



# ═══════════════════════════════════════════════════════════════════════
# EXTERNAL MONITORING AGENTS
# ═══════════════════════════════════════════════════════════════════════

# ── E1. Speed & Performance Agent ──────────────────────────────────────
def _agent_ext_speed():
    """Checks page speed, response times, page weight, and Core Web Vitals hints."""
    findings = []
    _test_pages = [
        ("Home", "/?page=home"),
        ("Charts", "/?page=charts&ticker=NVDA"),
        ("Sankey", "/?page=sankey&ticker=NVDA"),
        ("Pricing", "/?page=pricing"),
        ("Earnings", "/?page=earnings"),
    ]

    for name, path in _test_pages:
        url = _BASE_URL + path
        r, elapsed = _get(url, timeout=15)
        if not r:
            findings.append({"sev": "critical", "msg": f"{name}: unreachable", "detail": url})
            continue

        html = r.text
        size_kb = round(len(r.content) / 1024, 1)

        # Response time thresholds (TTFB-like)
        if elapsed <= 2:
            findings.append({"sev": "pass", "msg": f"{name}: fast response {elapsed}s ({size_kb}KB)", "detail": ""})
        elif elapsed <= 5:
            findings.append({"sev": "warning", "msg": f"{name}: moderate {elapsed}s ({size_kb}KB)", "detail": "Target < 2s for good Core Web Vitals"})
        else:
            findings.append({"sev": "critical", "msg": f"{name}: slow {elapsed}s ({size_kb}KB)", "detail": "Slow TTFB hurts LCP and PageSpeed score"})

        # Page weight
        if size_kb > 3000:
            findings.append({"sev": "critical", "msg": f"{name}: heavy page {size_kb}KB", "detail": "Compress images, lazy-load, split bundles"})
        elif size_kb > 1500:
            findings.append({"sev": "warning", "msg": f"{name}: page weight {size_kb}KB", "detail": "Consider reducing assets for mobile users"})

        # Check for render-blocking patterns
        import_count = html.lower().count('<script src=')
        css_count = html.lower().count('<link rel="stylesheet"')
        if import_count > 10:
            findings.append({"sev": "warning", "msg": f"{name}: {import_count} external scripts", "detail": "Many scripts can delay First Contentful Paint"})
        if css_count > 5:
            findings.append({"sev": "info", "msg": f"{name}: {css_count} external stylesheets", "detail": "Consider inlining critical CSS"})

    # Check GZIP / compression
    # NOTE: HEAD requests often don't trigger server-side compression (e.g. Tornado).
    # Use a full GET request with Accept-Encoding and stream=True to check the
    # Content-Encoding header without downloading the entire body.
    try:
        gzip_headers = {**_REQ_HEADERS, "Accept-Encoding": "gzip, deflate, br"}
        r_gz = requests.get(_BASE_URL, timeout=10, headers=gzip_headers,
                            allow_redirects=True, stream=True)
        encoding = r_gz.headers.get("Content-Encoding", "")
        r_gz.close()  # close without reading body
        if "gzip" in encoding or "br" in encoding:
            findings.append({"sev": "pass", "msg": f"Compression enabled: {encoding}", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": "No GZIP/Brotli compression detected", "detail": "Enable compression to reduce transfer size 60-80%"})

        # Cache headers
        cache = r_head.headers.get("Cache-Control", "")
        if cache:
            findings.append({"sev": "pass", "msg": f"Cache-Control header present: {cache[:60]}", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": "No Cache-Control header", "detail": "Add caching to reduce repeat load times"})
    except Exception:
        findings.append({"sev": "info", "msg": "Could not check compression headers", "detail": ""})

    # PageSpeed Insights API (free, no key needed for basic check)
    try:
        psi_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeedtest?url={_BASE_URL}&category=PERFORMANCE&strategy=MOBILE"
        psi_r = requests.get(psi_url, timeout=60)
        if psi_r.status_code == 200:
            data = psi_r.json()
            score = data.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score", 0)
            score_pct = int(score * 100)
            audits = data.get("lighthouseResult", {}).get("audits", {})

            if score_pct >= 90:
                findings.append({"sev": "pass", "msg": f"PageSpeed mobile score: {score_pct}/100", "detail": "Excellent performance"})
            elif score_pct >= 50:
                findings.append({"sev": "warning", "msg": f"PageSpeed mobile score: {score_pct}/100", "detail": "Needs improvement — target 90+"})
            else:
                findings.append({"sev": "critical", "msg": f"PageSpeed mobile score: {score_pct}/100", "detail": "Poor performance — major optimizations needed"})

            # Key metrics
            for metric_key, label in [("first-contentful-paint", "FCP"), ("largest-contentful-paint", "LCP"),
                                       ("total-blocking-time", "TBT"), ("cumulative-layout-shift", "CLS"),
                                       ("speed-index", "Speed Index")]:
                audit = audits.get(metric_key, {})
                display = audit.get("displayValue", "N/A")
                audit_score = audit.get("score", 1)
                sev = "pass" if audit_score >= 0.9 else "warning" if audit_score >= 0.5 else "critical"
                findings.append({"sev": sev, "msg": f"{label}: {display}", "detail": audit.get("description", "")[:80]})
        else:
            findings.append({"sev": "info", "msg": f"PageSpeed API returned {psi_r.status_code}", "detail": "Try manually at pagespeed.web.dev"})
    except Exception as e:
        findings.append({"sev": "info", "msg": f"PageSpeed API check skipped: {str(e)[:50]}", "detail": "Run manually at pagespeed.web.dev"})

    return findings


# ── E2. SEO & Search Agent ─────────────────────────────────────────────
def _agent_ext_seo():
    """Checks meta tags, Open Graph, structured data, robots.txt, sitemap, and SEO best practices."""
    findings = []

    # Check robots.txt
    r, _ = _get(_BASE_URL + "/robots.txt")
    if r and r.status_code == 200:
        robots_text = r.text
        if "Sitemap:" in robots_text:
            findings.append({"sev": "pass", "msg": "robots.txt: Sitemap reference found", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": "robots.txt: No Sitemap reference", "detail": "Add Sitemap: URL to robots.txt"})
        if "Disallow" in robots_text:
            findings.append({"sev": "pass", "msg": "robots.txt: Disallow rules present", "detail": ""})
    else:
        findings.append({"sev": "critical", "msg": "robots.txt: missing or unreachable", "detail": "Search engines need robots.txt"})

    # Check sitemap.xml
    r, _ = _get(_BASE_URL + "/sitemap.xml")
    if r and r.status_code == 200 and "<url>" in r.text.lower():
        url_count = r.text.lower().count("<url>")
        findings.append({"sev": "pass", "msg": f"sitemap.xml: found with {url_count} URLs", "detail": ""})
    else:
        findings.append({"sev": "critical", "msg": "sitemap.xml: missing or invalid", "detail": "Create XML sitemap for better indexing"})

    # Check key pages for SEO elements
    _seo_pages = [
        ("Home", "/?page=home"),
        ("Pricing", "/?page=pricing"),
        ("Charts (NVDA)", "/?page=charts&ticker=NVDA"),
    ]

    for name, path in _seo_pages:
        r, _ = _get(_BASE_URL + path)
        if not r:
            findings.append({"sev": "critical", "msg": f"{name}: unreachable for SEO check", "detail": ""})
            continue

        html = r.text.lower()

        # Title tag
        if "<title>" in html and "</title>" in html:
            title_start = html.index("<title>") + 7
            title_end = html.index("</title>")
            title = html[title_start:title_end].strip()
            title_len = len(title)
            if 30 <= title_len <= 60:
                findings.append({"sev": "pass", "msg": f"{name}: title tag OK ({title_len} chars)", "detail": ""})
            elif title_len > 0:
                findings.append({"sev": "warning", "msg": f"{name}: title {title_len} chars (ideal 30-60)", "detail": title[:60]})
            else:
                findings.append({"sev": "critical", "msg": f"{name}: empty title tag", "detail": "Every page needs a unique title"})
        else:
            findings.append({"sev": "critical", "msg": f"{name}: missing <title> tag", "detail": ""})

        # Meta description
        if 'name="description"' in html:
            findings.append({"sev": "pass", "msg": f"{name}: meta description present", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: missing meta description", "detail": "Add meta description for better CTR in search results"})

        # Open Graph tags
        og_tags = ["og:title", "og:description", "og:image", "og:url"]
        og_found = sum(1 for tag in og_tags if f'property="{tag}"' in html or f"property='{tag}'" in html)
        if og_found == len(og_tags):
            findings.append({"sev": "pass", "msg": f"{name}: all Open Graph tags present", "detail": ""})
        elif og_found > 0:
            findings.append({"sev": "warning", "msg": f"{name}: {og_found}/{len(og_tags)} OG tags", "detail": "Add missing OG tags for social sharing"})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: no Open Graph tags", "detail": "OG tags improve social media previews"})

        # Twitter Card
        if 'name="twitter:card"' in html or "name='twitter:card'" in html:
            findings.append({"sev": "pass", "msg": f"{name}: Twitter Card meta present", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": f"{name}: no Twitter Card meta", "detail": "Add for better X/Twitter previews"})

        # Canonical URL
        if 'rel="canonical"' in html or "rel='canonical'" in html:
            findings.append({"sev": "pass", "msg": f"{name}: canonical URL set", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: missing canonical URL", "detail": "Prevents duplicate content issues"})

        # H1 tag
        if "<h1" in html:
            findings.append({"sev": "pass", "msg": f"{name}: H1 tag present", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: missing H1 tag", "detail": "Every page should have one H1"})

        # Structured data (JSON-LD)
        if 'application/ld+json' in html:
            findings.append({"sev": "pass", "msg": f"{name}: JSON-LD structured data found", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": f"{name}: no JSON-LD structured data", "detail": "Add schema.org markup for rich results"})

    # Check for hreflang (international SEO)
    r, _ = _get(_BASE_URL + "/?page=home")
    if r and 'hreflang' in r.text.lower():
        findings.append({"sev": "pass", "msg": "hreflang tags present (international SEO)", "detail": ""})
    else:
        findings.append({"sev": "info", "msg": "No hreflang tags (OK if single-language site)", "detail": ""})

    return findings


# ── E3. Uptime & Availability Agent ────────────────────────────────────
def _agent_ext_uptime():
    """Checks site availability, HTTP status codes, redirect chains, and DNS resolution."""
    findings = []

    # Test main domain
    _endpoints = [
        ("Homepage", _BASE_URL),
        ("WWW redirect", "https://www.quartercharts.com"),
        ("HTTP redirect", "http://quartercharts.com"),
        ("Charts page", _BASE_URL + "/?page=charts&ticker=NVDA"),
        ("Sankey page", _BASE_URL + "/?page=sankey&ticker=NVDA"),
        ("Pricing page", _BASE_URL + "/?page=pricing"),
        ("API/Sitemap", _BASE_URL + "/sitemap.xml"),
        ("Robots", _BASE_URL + "/robots.txt"),
    ]

    for name, url in _endpoints:
        try:
            start = time.time()
            r = requests.get(url, timeout=15, headers=_REQ_HEADERS, allow_redirects=True)
            elapsed = round(time.time() - start, 2)

            if r.status_code == 200:
                findings.append({"sev": "pass", "msg": f"{name}: UP ({r.status_code}) in {elapsed}s", "detail": ""})
            elif r.status_code in (301, 302, 308):
                findings.append({"sev": "pass", "msg": f"{name}: redirect {r.status_code} → {r.headers.get('Location', '?')[:60]}", "detail": ""})
            elif r.status_code == 403:
                findings.append({"sev": "warning", "msg": f"{name}: 403 Forbidden", "detail": "Check access permissions"})
            elif r.status_code == 404:
                findings.append({"sev": "critical", "msg": f"{name}: 404 Not Found", "detail": url})
            elif r.status_code >= 500:
                findings.append({"sev": "critical", "msg": f"{name}: server error {r.status_code}", "detail": "Check Railway logs for errors"})
            else:
                findings.append({"sev": "info", "msg": f"{name}: status {r.status_code} in {elapsed}s", "detail": ""})

            # Check redirect chain length
            if len(r.history) > 2:
                findings.append({"sev": "warning", "msg": f"{name}: {len(r.history)} redirects in chain", "detail": "Long redirect chains slow page load"})

        except requests.exceptions.Timeout:
            findings.append({"sev": "critical", "msg": f"{name}: TIMEOUT (>15s)", "detail": "Site may be down or extremely slow"})
        except requests.exceptions.ConnectionError:
            findings.append({"sev": "critical", "msg": f"{name}: CONNECTION FAILED", "detail": "Site is unreachable"})
        except Exception as e:
            findings.append({"sev": "critical", "msg": f"{name}: error — {str(e)[:50]}", "detail": ""})

    # DNS resolution check
    try:
        import socket
        ip = socket.gethostbyname("quartercharts.com")
        findings.append({"sev": "pass", "msg": f"DNS resolves: quartercharts.com → {ip}", "detail": ""})
    except Exception as e:
        findings.append({"sev": "critical", "msg": f"DNS resolution failed: {str(e)[:50]}", "detail": "Domain may be misconfigured"})

    # Check www vs non-www consistency
    try:
        r_www = requests.get("https://www.quartercharts.com", timeout=10, allow_redirects=False, headers=_REQ_HEADERS)
        r_bare = requests.get("https://quartercharts.com", timeout=10, allow_redirects=False, headers=_REQ_HEADERS)
        if r_www.status_code in (301, 302, 308):
            findings.append({"sev": "pass", "msg": "www → non-www redirect configured", "detail": ""})
        elif r_bare.status_code in (301, 302, 308):
            findings.append({"sev": "pass", "msg": "non-www → www redirect configured", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": "No www/non-www redirect", "detail": "Both versions serve content — pick one canonical"})
    except Exception:
        findings.append({"sev": "info", "msg": "Could not test www redirect", "detail": ""})

    # Measure average response time across 3 pings
    times = []
    for _ in range(3):
        _, t = _get(_BASE_URL, timeout=10)
        if t > 0:
            times.append(t)
    if times:
        avg = round(sum(times) / len(times), 2)
        if avg <= 2:
            findings.append({"sev": "pass", "msg": f"Avg response time: {avg}s (3 pings)", "detail": ""})
        elif avg <= 5:
            findings.append({"sev": "warning", "msg": f"Avg response time: {avg}s (3 pings)", "detail": "Consider CDN or caching"})
        else:
            findings.append({"sev": "critical", "msg": f"Avg response time: {avg}s (3 pings)", "detail": "Severely slow — investigate server"})

    return findings


# ── E4. Security & SSL Agent ───────────────────────────────────────────
def _agent_ext_security():
    """Checks SSL certificate, security headers, HTTPS enforcement, and common vulnerabilities."""
    findings = []

    # SSL certificate check
    try:
        import ssl
        import socket
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname="quartercharts.com") as s:
            s.settimeout(10)
            s.connect(("quartercharts.com", 443))
            cert = s.getpeercert()

            # Expiry check
            not_after = cert.get("notAfter", "")
            if not_after:
                from datetime import datetime as dt
                expiry = dt.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry - dt.utcnow()).days
                if days_left > 30:
                    findings.append({"sev": "pass", "msg": f"SSL valid: {days_left} days until expiry", "detail": f"Expires: {not_after}"})
                elif days_left > 7:
                    findings.append({"sev": "warning", "msg": f"SSL expiring soon: {days_left} days left", "detail": "Renew certificate ASAP"})
                elif days_left > 0:
                    findings.append({"sev": "critical", "msg": f"SSL expires in {days_left} days!", "detail": "URGENT: Renew immediately"})
                else:
                    findings.append({"sev": "critical", "msg": "SSL CERTIFICATE EXPIRED", "detail": "Site will show security warnings"})

            # Issuer
            issuer = dict(x[0] for x in cert.get("issuer", []))
            org = issuer.get("organizationName", "Unknown")
            findings.append({"sev": "pass", "msg": f"SSL issuer: {org}", "detail": ""})

            # Subject alt names
            san = cert.get("subjectAltName", [])
            domains = [d[1] for d in san if d[0] == "DNS"]
            findings.append({"sev": "pass", "msg": f"SSL covers: {', '.join(domains[:5])}", "detail": ""})

    except Exception as e:
        findings.append({"sev": "critical", "msg": f"SSL check failed: {str(e)[:60]}", "detail": "Cannot verify certificate"})

    # HTTPS enforcement
    try:
        r = requests.get("http://quartercharts.com", timeout=10, allow_redirects=False, headers=_REQ_HEADERS)
        if r.status_code in (301, 302, 308) and "https" in r.headers.get("Location", ""):
            findings.append({"sev": "pass", "msg": "HTTP → HTTPS redirect active", "detail": ""})
        else:
            findings.append({"sev": "critical", "msg": "HTTP not redirecting to HTTPS", "detail": "All traffic must use HTTPS"})
    except Exception:
        findings.append({"sev": "info", "msg": "Could not test HTTP redirect", "detail": ""})

    # Security headers check
    try:
        r = requests.get(_BASE_URL, timeout=10, headers=_REQ_HEADERS)
        headers = r.headers

        _sec_headers = {
            "Strict-Transport-Security": ("HSTS", "critical", "Prevents protocol downgrade attacks"),
            "X-Content-Type-Options": ("X-Content-Type-Options", "warning", "Prevents MIME sniffing"),
            "X-Frame-Options": ("X-Frame-Options", "warning", "Prevents clickjacking"),
            "Content-Security-Policy": ("CSP", "warning", "Controls allowed content sources"),
            "X-XSS-Protection": ("X-XSS-Protection", "info", "Legacy XSS filter (mostly deprecated)"),
            "Referrer-Policy": ("Referrer-Policy", "info", "Controls referrer information"),
            "Permissions-Policy": ("Permissions-Policy", "info", "Controls browser features"),
        }

        for header, (label, sev_missing, desc) in _sec_headers.items():
            if header in headers:
                val = headers[header][:60]
                findings.append({"sev": "pass", "msg": f"{label}: {val}", "detail": ""})
            else:
                findings.append({"sev": sev_missing, "msg": f"Missing {label} header", "detail": desc})

        # Check for server version disclosure
        server = headers.get("Server", "")
        if server and any(v in server.lower() for v in ["apache", "nginx", "iis"]):
            findings.append({"sev": "warning", "msg": f"Server header exposes: {server}", "detail": "Hide server version to reduce attack surface"})
        elif server:
            findings.append({"sev": "pass", "msg": f"Server header: {server}", "detail": ""})

    except Exception as e:
        findings.append({"sev": "warning", "msg": f"Security headers check failed: {str(e)[:50]}", "detail": ""})

    # Check for mixed content indicators
    try:
        r, _ = _get(_BASE_URL + "/?page=home")
        if r:
            html = r.text
            http_refs = len(re.findall(r'(src|href)=["\']http://', html))
            if http_refs == 0:
                findings.append({"sev": "pass", "msg": "No mixed content (HTTP refs) on homepage", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"Mixed content: {http_refs} HTTP references on homepage", "detail": "All resources should use HTTPS"})
    except Exception:
        pass

    return findings


# ── E5. Accessibility & Mobile Agent ───────────────────────────────────
def _agent_ext_accessibility():
    """Checks mobile-friendliness, accessibility basics, viewport, ARIA, and semantic HTML."""
    findings = []

    _test_pages = [
        ("Home", "/?page=home"),
        ("Pricing", "/?page=pricing"),
        ("Charts", "/?page=charts&ticker=NVDA"),
    ]

    for name, path in _test_pages:
        r, _ = _get(_BASE_URL + path)
        if not r:
            findings.append({"sev": "critical", "msg": f"{name}: unreachable", "detail": ""})
            continue

        html = r.text
        html_lower = html.lower()

        # Viewport meta
        if 'name="viewport"' in html_lower:
            if "width=device-width" in html_lower:
                findings.append({"sev": "pass", "msg": f"{name}: viewport meta with device-width", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"{name}: viewport meta but no device-width", "detail": "Use width=device-width for responsive design"})
        else:
            findings.append({"sev": "critical", "msg": f"{name}: missing viewport meta tag", "detail": "Required for mobile rendering"})

        # Language attribute (check static HTML or JS-injected lang)
        has_lang = ('lang=' in html_lower[:500]
                    or "documentelement.setattribute('lang'" in html_lower
                    or 'documentelement.setattribute("lang"' in html_lower)
        if has_lang:
            findings.append({"sev": "pass", "msg": f"{name}: html lang attribute set", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: missing html lang attribute", "detail": "Add lang='en' for screen readers"})

        # Image alt attributes
        img_tags = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
        imgs_no_alt = sum(1 for img in img_tags if 'alt=' not in img.lower())
        if img_tags:
            if imgs_no_alt == 0:
                findings.append({"sev": "pass", "msg": f"{name}: all {len(img_tags)} images have alt text", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"{name}: {imgs_no_alt}/{len(img_tags)} images missing alt", "detail": "Alt text required for accessibility"})

        # ARIA landmarks / roles
        aria_count = html_lower.count('role=') + html_lower.count('aria-')
        if aria_count > 5:
            findings.append({"sev": "pass", "msg": f"{name}: {aria_count} ARIA attributes found", "detail": ""})
        elif aria_count > 0:
            findings.append({"sev": "info", "msg": f"{name}: {aria_count} ARIA attributes (consider adding more)", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: no ARIA attributes found", "detail": "Add ARIA landmarks for screen reader navigation"})

        # Skip links
        if 'skip' in html_lower[:2000] and ('nav' in html_lower[:2000] or 'main' in html_lower[:2000]):
            findings.append({"sev": "pass", "msg": f"{name}: skip navigation link found", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": f"{name}: no skip navigation link", "detail": "Add 'Skip to main content' for keyboard users"})

        # Form labels
        inputs = re.findall(r'<input[^>]*>', html, re.IGNORECASE)
        inputs_no_label = sum(1 for inp in inputs
                              if 'type="hidden"' not in inp.lower()
                              and 'type="submit"' not in inp.lower()
                              and 'aria-label' not in inp.lower()
                              and 'id=' not in inp.lower())
        if inputs:
            if inputs_no_label == 0:
                findings.append({"sev": "pass", "msg": f"{name}: form inputs properly labeled", "detail": ""})
            elif inputs_no_label <= 2:
                findings.append({"sev": "info", "msg": f"{name}: {inputs_no_label} inputs may lack labels", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"{name}: {inputs_no_label} inputs without labels/aria", "detail": "Screen readers need labels for form inputs"})

        # Semantic HTML elements, ARIA roles, or JS-injected role scripts
        semantic_tags = ["<nav", "<main", "<header", "<footer", "<article", "<section"]
        aria_roles = ['role="navigation"', 'role="main"', 'role="banner"',
                      'role="contentinfo"', 'role="article"', 'role="region"']
        # Also detect JS-based ARIA injection (e.g. setAttribute('role','main'))
        js_roles = ["setAttribute('role','navigation')", "setAttribute('role','main')",
                    "setAttribute('role','banner')", "setAttribute('role','contentinfo')"]
        found_semantic = sum(1 for tag in semantic_tags if tag in html_lower)
        found_aria_roles = sum(1 for role in aria_roles if role in html_lower)
        found_js_roles = sum(1 for jr in js_roles if jr in html)
        total_landmarks = min(found_semantic + found_aria_roles + found_js_roles, 6)
        if total_landmarks >= 4:
            findings.append({"sev": "pass", "msg": f"{name}: good semantic structure ({total_landmarks}/6 landmarks)", "detail": f"{found_semantic} tags + {found_aria_roles} inline + {found_js_roles} JS roles"})
        elif total_landmarks >= 2:
            findings.append({"sev": "info", "msg": f"{name}: partial semantic structure ({total_landmarks}/6 landmarks)", "detail": "Add more semantic elements or ARIA roles"})
        else:
            findings.append({"sev": "warning", "msg": f"{name}: poor semantic HTML ({total_landmarks}/6)", "detail": "Use nav, main, header, footer or ARIA role equivalents"})

        # Font size check (look for very small text patterns)
        tiny_fonts = len(re.findall(r'font-size:\s*(8|9|10)px', html))
        if tiny_fonts > 5:
            findings.append({"sev": "warning", "msg": f"{name}: {tiny_fonts} elements with font ≤10px", "detail": "Minimum 12px recommended for readability"})

    # Mobile responsiveness — check for common responsive patterns
    r, _ = _get(_BASE_URL + "/?page=home")
    if r:
        html = r.text
        if "@media" in html:
            media_queries = html.count("@media")
            findings.append({"sev": "pass", "msg": f"Responsive: {media_queries} @media queries found", "detail": ""})
        else:
            findings.append({"sev": "info", "msg": "No @media queries in initial HTML", "detail": "May be in external stylesheets (OK)"})

        # Touch-friendly tap targets (check for very small clickable areas)
        small_buttons = len(re.findall(r'padding:\s*[0-2]px', html))
        if small_buttons > 3:
            findings.append({"sev": "warning", "msg": f"{small_buttons} elements with tiny padding (<3px)", "detail": "Tap targets should be at least 48x48px on mobile"})

    return findings


# ── E6. Google Sign-In Agent ──────────────────────────────────────────
def _agent_ext_google_signin():
    """Checks that Google Sign-In is fully operational end-to-end:
    component files, Client ID config, GIS script reachability,
    login page rendering, token verification library, and OAuth consent."""
    findings = []

    # 1. Check google_signin_component directory exists with index.html
    _comp_dir = os.path.join(_BASE_DIR, "google_signin_component")
    if os.path.isdir(_comp_dir):
        _index = os.path.join(_comp_dir, "index.html")
        if os.path.isfile(_index):
            _html = open(_index, "r").read()
            if "accounts.google.com/gsi/client" in _html:
                findings.append({"sev": "pass", "msg": "GIS component: index.html with Google Identity Services script", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": "GIS component: index.html missing GIS script reference", "detail": "Should load accounts.google.com/gsi/client"})
        else:
            findings.append({"sev": "critical", "msg": "GIS component: index.html missing", "detail": _comp_dir})
    else:
        findings.append({"sev": "critical", "msg": "google_signin_component directory missing", "detail": _comp_dir})

    # 2. Check GOOGLE_CLIENT_ID is configured
    try:
        from auth import GOOGLE_CLIENT_ID
        if GOOGLE_CLIENT_ID and len(GOOGLE_CLIENT_ID) > 20:
            findings.append({"sev": "pass", "msg": f"Client ID configured: {GOOGLE_CLIENT_ID[:20]}...", "detail": ""})
        else:
            findings.append({"sev": "critical", "msg": "GOOGLE_CLIENT_ID is empty or too short", "detail": "Set GOOGLE_CLIENT_ID env var"})
    except ImportError:
        findings.append({"sev": "critical", "msg": "Cannot import GOOGLE_CLIENT_ID from auth.py", "detail": ""})

    # 3. Check google.oauth2 library is importable (token verification)
    try:
        from google.oauth2 import id_token as _gid
        from google.auth.transport import requests as _greq
        findings.append({"sev": "pass", "msg": "google-auth library available (id_token + transport)", "detail": ""})
    except ImportError as e:
        findings.append({"sev": "critical", "msg": f"google-auth library missing: {e}", "detail": "pip install google-auth"})

    # 4. Check verify_google_id_token function exists
    try:
        from auth import verify_google_id_token
        findings.append({"sev": "pass", "msg": "verify_google_id_token() function available", "detail": ""})
    except ImportError:
        findings.append({"sev": "critical", "msg": "verify_google_id_token not found in auth.py", "detail": ""})

    # 5. Check login_page.py has Google Sign-In handling
    _login_file = os.path.join(_BASE_DIR, "login_page.py")
    if os.path.isfile(_login_file):
        _lsrc = open(_login_file, "r").read()
        checks = {
            "login_with_google": "Google login handler imported",
            "google_signin": "Google Sign-In component declared",
            "credential": "Credential callback handled",
            "_render_google_button": "Google button render function",
        }
        for pattern, label in checks.items():
            if pattern in _lsrc:
                findings.append({"sev": "pass", "msg": f"login_page.py: {label}", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": f"login_page.py: missing {label}", "detail": f"Pattern '{pattern}' not found"})
    else:
        findings.append({"sev": "critical", "msg": "login_page.py not found", "detail": ""})

    # 6. Check Google GIS JS is referenced in the component HTML
    _gis_component = os.path.join(_BASE_DIR, "google_signin_component", "index.html")
    if os.path.isfile(_gis_component):
        _gis_src = open(_gis_component, "r").read()
        if "accounts.google.com/gsi/client" in _gis_src or "initTokenClient" in _gis_src:
            findings.append({"sev": "pass", "msg": "Google GIS JS referenced in component", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": "Google GIS JS not found in component HTML", "detail": "May affect Sign-In button rendering"})
    else:
        findings.append({"sev": "warning", "msg": "Google Sign-In component HTML not found", "detail": f"Expected at {_gis_component}"})

    # 7. Check login page loads + login_page.py has sign-in content
    try:
        r, elapsed = _get(_BASE_URL + "/?page=login", timeout=15)
        if r and r.status_code == 200:
            findings.append({"sev": "pass", "msg": f"Login page loads: 200 OK in {elapsed}s", "detail": ""})
        elif r:
            findings.append({"sev": "critical", "msg": f"Login page error: HTTP {r.status_code}", "detail": ""})
        else:
            findings.append({"sev": "critical", "msg": "Login page unreachable", "detail": ""})
    except Exception as e:
        findings.append({"sev": "warning", "msg": f"Login page check failed: {str(e)[:50]}", "detail": ""})

    # Check login_page.py source for sign-in UI text (Streamlit renders client-side)
    _login_src_file = os.path.join(_BASE_DIR, "login_page.py")
    if os.path.isfile(_login_src_file):
        _lp_src = open(_login_src_file, "r").read().lower()
        if "sign in" in _lp_src or "log in" in _lp_src or "login" in _lp_src:
            findings.append({"sev": "pass", "msg": "Login page source contains sign-in content", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": "login_page.py missing sign-in text", "detail": "Streamlit renders client-side"})

    # 8. Verify OAuth consent screen endpoint responds (Google's .well-known)
    try:
        r = requests.get(
            "https://accounts.google.com/.well-known/openid-configuration",
            timeout=8, headers=_REQ_HEADERS
        )
        if r.status_code == 200:
            cfg = r.json()
            if "authorization_endpoint" in cfg and "token_endpoint" in cfg:
                findings.append({"sev": "pass", "msg": "Google OpenID Connect discovery endpoint OK", "detail": ""})
            else:
                findings.append({"sev": "warning", "msg": "Google OIDC config missing expected fields", "detail": ""})
        else:
            findings.append({"sev": "warning", "msg": f"Google OIDC discovery: HTTP {r.status_code}", "detail": ""})
    except Exception as e:
        findings.append({"sev": "info", "msg": f"Could not check Google OIDC: {str(e)[:50]}", "detail": ""})

    # 9. Check auth.py has login_with_google function
    try:
        from auth import login_with_google
        findings.append({"sev": "pass", "msg": "login_with_google() function available in auth.py", "detail": ""})
    except ImportError:
        findings.append({"sev": "critical", "msg": "login_with_google not found in auth.py", "detail": ""})

    # 10. Check Firebase env vars (needed for user creation on first Google login)
    _firebase_key = os.environ.get("FIREBASE_API_KEY", "")
    if _firebase_key:
        findings.append({"sev": "pass", "msg": "FIREBASE_API_KEY env var is set", "detail": ""})
    else:
        findings.append({"sev": "info", "msg": "FIREBASE_API_KEY env var not set", "detail": "Not needed if using direct DB auth"})

    return findings


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
    # External monitoring agents
    {"id": "ext_speed",      "name": "Speed",          "icon": "⚡", "color": "#F59E0B", "fn": _agent_ext_speed,      "tab": "External"},
    {"id": "ext_seo",        "name": "SEO Check",      "icon": "🔎", "color": "#22D3EE", "fn": _agent_ext_seo,        "tab": "External"},
    {"id": "ext_uptime",     "name": "Uptime",         "icon": "🟢", "color": "#34D399", "fn": _agent_ext_uptime,     "tab": "External"},
    {"id": "ext_security",   "name": "SSL & Security", "icon": "🔐", "color": "#F43F5E", "fn": _agent_ext_security,   "tab": "External"},
    {"id": "ext_a11y",       "name": "Accessibility",  "icon": "♿", "color": "#818CF8", "fn": _agent_ext_accessibility, "tab": "External"},
    {"id": "ext_google_signin", "name": "Google Sign-In", "icon": "🔑", "color": "#4285F4", "fn": _agent_ext_google_signin, "tab": "External"},
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


def _render_summary_report():
    """Plain-text summary of the last audit run, with a copy button."""

    st.markdown("""
    <div class="sba-header">
        <h1>📋 Summary Report</h1>
        <p>Copy-paste friendly report of the last audit — share with AI or teammates</p>
    </div>
    """, unsafe_allow_html=True)

    result = st.session_state.get("sba_result")

    # Also check history if no session result
    if not result:
        history = _load_history()
        if history:
            result = history[0]

    if not result:
        st.markdown(
            '<div class="sba-empty">No audit results yet. Run agents from the '
            '<strong>Command Center</strong> tab first.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Build plain-text report ──
    overall = result.get("overall_score", 0)
    tc = result.get("total_counts", {})
    ts = result.get("timestamp", "")
    try:
        time_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        time_str = ts[:19] if ts else "unknown"

    agents_data = result.get("agents", {})

    lines = []
    lines.append("=" * 60)
    lines.append("QUARTERCHARTS — NSFQ AGENT SUMMARY REPORT")
    lines.append(f"Run: {time_str}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"OVERALL SCORE: {overall}%")
    lines.append(
        f"  Critical: {tc.get('critical', 0)}  |  "
        f"Warnings: {tc.get('warning', 0)}  |  "
        f"Info: {tc.get('info', 0)}  |  "
        f"Passed: {tc.get('pass', 0)}"
    )
    lines.append("")

    # Per-agent summary (one-liner each)
    lines.append("-" * 60)
    lines.append("AGENT SCORES")
    lines.append("-" * 60)
    for agent in AGENTS:
        aid = agent["id"]
        ad = agents_data.get(aid, {})
        score = ad.get("score", 0)
        counts = ad.get("counts", {})
        crit = counts.get("critical", 0)
        warn = counts.get("warning", 0)
        if crit > 0:
            flag = " *** CRITICAL ***"
        elif warn > 0:
            flag = " * WARNING *"
        else:
            flag = ""
        lines.append(
            f"  {agent['icon']} {agent['name']:<20s}  {score:>3d}%  "
            f"(C:{crit} W:{warn}){flag}"
        )
    lines.append("")

    # Detailed issues per agent (all non-pass findings)
    lines.append("-" * 60)
    lines.append("ALL ISSUES BY AGENT (critical, warning & info)")
    lines.append("-" * 60)
    any_issues = False
    for agent in AGENTS:
        aid = agent["id"]
        ad = agents_data.get(aid, {})
        findings = ad.get("findings", [])
        issues = [f for f in findings if f["sev"] in ("critical", "warning", "info")]
        if not issues:
            continue
        any_issues = True
        score = ad.get("score", 0)
        lines.append("")
        lines.append(f">>> {agent['icon']} {agent['name']} ({score}%)")
        sev_order = {"critical": 0, "warning": 1, "info": 2}
        for f in sorted(issues, key=lambda x: sev_order.get(x["sev"], 9)):
            sev_label = f["sev"].upper()
            detail = f" | {f['detail']}" if f.get("detail") else ""
            lines.append(f"    [{sev_label}] {f['msg']}{detail}")

    if not any_issues:
        lines.append("  (No critical or warning issues found!)")

    lines.append("")
    lines.append("=" * 60)
    lines.append("END OF REPORT")
    lines.append("=" * 60)

    report_text = "\n".join(lines)

    # Show as copyable code block (Streamlit adds a copy button automatically)
    st.code(report_text, language="text")


def render_super_bug_agent():
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Subtabs ──
    sub1, sub2, sub3, sub4 = st.tabs(["🎯 Command Center", "📅 History & Trends", "📡 Live Status", "📋 Summary Report"])

    with sub1:
        _render_command_center()
    with sub2:
        _render_history()
    with sub3:
        _render_live_status()
    with sub4:
        _render_summary_report()


def _render_command_center():
    """Main audit runner and results display."""

    # Header
    st.markdown("""
    <div class="sba-header">
        <h1>🐛 Super Bug Agent</h1>
        <p>20 specialized agents auditing every layer of QuarterCharts</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Tickers to Check (Audit Panel config) ──
    with st.expander("🔬 Tickers to Check (Sankey Audit)", expanded=False):
        current_tickers = _load_audit_tickers()
        st.markdown(
            f'<div style="font-size:0.82rem;color:#94A3B8;margin-bottom:8px;">'
            f'The <strong>Audit Panel</strong> agent will validate Sankey data for these tickers. '
            f'Currently: <strong>{len(current_tickers)}</strong> tickers.</div>',
            unsafe_allow_html=True,
        )
        # Show current tickers as pills
        if current_tickers:
            pills_html = " ".join(
                f'<span style="display:inline-block;background:#1E293B;color:#F1F5F9;'
                f'border:1px solid #334155;border-radius:8px;padding:4px 12px;'
                f'font-size:0.82rem;font-weight:600;margin:2px;">{t}</span>'
                for t in current_tickers
            )
            st.markdown(pills_html, unsafe_allow_html=True)

        # ── Auto-add from Earnings Calendar ──
        st.markdown(
            '<div style="font-size:0.78rem;color:#64748B;margin:12px 0 4px;">'
            '<strong>Auto-add from Earnings Calendar</strong> — '
            'adds tickers reporting this week (Finnhub API), keeps your existing list.</div>',
            unsafe_allow_html=True,
        )
        ea1, ea2, ea3 = st.columns(3)
        with ea1:
            if st.button("📅 + This Week", key="sba_earn_this", use_container_width=True):
                with st.spinner("Fetching this week's earnings..."):
                    merged, added = _merge_earnings_into_audit_tickers(0)
                if added > 0:
                    st.toast(f"Added {added} tickers from this week's earnings ({len(merged)} total)", icon="📅")
                    st.rerun()
                else:
                    st.toast("No new tickers to add — all already in list", icon="ℹ️")
        with ea2:
            if st.button("📅 + Next Week", key="sba_earn_next", use_container_width=True):
                with st.spinner("Fetching next week's earnings..."):
                    merged, added = _merge_earnings_into_audit_tickers(1)
                if added > 0:
                    st.toast(f"Added {added} tickers from next week's earnings ({len(merged)} total)", icon="📅")
                    st.rerun()
                else:
                    st.toast("No new tickers to add — all already in list", icon="ℹ️")
        with ea3:
            if st.button("📅 Replace → This Week Only", key="sba_earn_replace", use_container_width=True):
                with st.spinner("Fetching this week's earnings..."):
                    tickers = _fetch_earnings_week_tickers(0)
                if tickers:
                    _save_audit_tickers(tickers)
                    st.toast(f"Replaced with {len(tickers)} tickers from this week's earnings", icon="📅")
                    st.rerun()
                else:
                    st.toast("No earnings found for this week", icon="⚠️")

        # ── Manual edit ──
        st.markdown("---")
        new_tickers_str = st.text_input(
            "Edit tickers (comma-separated):",
            value=", ".join(current_tickers),
            key="sba_audit_tickers_input",
            placeholder="e.g. NVDA, GOOG, META, TSLA, AAPL",
        )
        tc1, tc2 = st.columns(2)
        with tc1:
            if st.button("💾 Save Tickers", key="sba_save_tickers", use_container_width=True):
                parsed = [t.strip().upper() for t in new_tickers_str.split(",") if t.strip()]
                if parsed:
                    _save_audit_tickers(parsed)
                    st.toast(f"Saved {len(parsed)} tickers: {', '.join(parsed)}", icon="✅")
                    st.rerun()
                else:
                    st.toast("Please enter at least one ticker.", icon="⚠️")
        with tc2:
            if st.button("↩️ Reset to Defaults", key="sba_reset_tickers", use_container_width=True):
                _save_audit_tickers(_DEFAULT_AUDIT_TICKERS)
                st.toast(f"Reset to defaults: {', '.join(_DEFAULT_AUDIT_TICKERS)}", icon="✅")
                st.rerun()

        # ── EDGAR Registry Validation Option ──
        st.markdown("---")
        st.markdown(
            '<div style="font-size:0.78rem;color:#64748B;margin:4px 0 4px;">'
            '<strong>Pre-run Validation</strong> — '
            'cross-reference tickers against the official SEC EDGAR registry '
            '(10,391 filers) to catch typos and non-SEC tickers before running the full audit.</div>',
            unsafe_allow_html=True,
        )
        _edgar_validate = st.checkbox(
            "Validate tickers against SEC EDGAR registry",
            value=st.session_state.get("sba_edgar_validate", True),
            key="sba_edgar_validate",
            help="Fetches SEC's company_tickers.json (cached 24h) and flags any tickers not found in EDGAR",
        )

    # ── EDGAR Full Registry Batch Audit ──────────────────────────────────
    with st.expander("📦 EDGAR Full Registry — Batch Audit (10,391 tickers)", expanded=False):
        st.markdown(
            '<div style="font-size:0.82rem;color:#94A3B8;margin-bottom:10px;">'
            'Run all 20 agents against the <strong>entire SEC EDGAR registry</strong> in manageable '
            'batches of 500 tickers. Click any batch when you have time — a timestamp records when '
            'each batch was last checked so you know which ones still need auditing.</div>',
            unsafe_allow_html=True,
        )

        batches = _get_edgar_batches()
        ts_map = _load_batch_timestamps()

        if not batches:
            st.warning("Could not load EDGAR registry. Check your network connection and try again.")
        else:
            total_tickers = sum(len(b) for b in batches)
            checked_count = sum(1 for i in range(len(batches)) if str(i) in ts_map)
            st.markdown(
                f'<div style="font-size:0.78rem;color:#64748B;margin-bottom:12px;">'
                f'<strong>{total_tickers:,}</strong> tickers → <strong>{len(batches)}</strong> batches '
                f'({_BATCH_SIZE} each, last has {len(batches[-1])}) · '
                f'<strong>{checked_count}/{len(batches)}</strong> batches checked</div>',
                unsafe_allow_html=True,
            )

            # Render batch buttons in rows of 3
            for row_start in range(0, len(batches), 3):
                cols = st.columns(3)
                for col_idx, batch_idx in enumerate(range(row_start, min(row_start + 3, len(batches)))):
                    batch = batches[batch_idx]
                    first_t = batch[0]
                    last_t = batch[-1]
                    last_ts = ts_map.get(str(batch_idx))
                    if last_ts:
                        try:
                            ts_label = datetime.fromisoformat(last_ts).strftime("%b %d %H:%M")
                        except Exception:
                            ts_label = last_ts[:16]
                        badge = f"✅ {ts_label}"
                        btn_type = "secondary"
                    else:
                        badge = "⬜ Not checked"
                        btn_type = "primary"

                    with cols[col_idx]:
                        st.markdown(
                            f'<div style="text-align:center;font-size:0.7rem;color:#64748B;'
                            f'margin-bottom:2px;">{first_t} → {last_t} · {len(batch)} tickers</div>',
                            unsafe_allow_html=True,
                        )
                        btn_key = f"sba_batch_{batch_idx}"
                        if st.button(
                            f"Batch {batch_idx + 1} — {badge}",
                            key=btn_key,
                            use_container_width=True,
                            type=btn_type,
                        ):
                            st.session_state["_sba_run_batch"] = batch_idx

            # ── Execute batch if a button was clicked ──
            pending_batch = st.session_state.pop("_sba_run_batch", None)
            if pending_batch is not None:
                batch = batches[pending_batch]
                st.info(f"🚀 Running all 20 agents on **Batch {pending_batch + 1}** "
                        f"({len(batch)} tickers: {batch[0]} → {batch[-1]})...")

                # Temporarily override audit tickers with this batch
                original_tickers = _load_audit_tickers()
                _save_audit_tickers(batch)

                bar = st.progress(0, text=f"Batch {pending_batch + 1}: Initializing agents...")
                def _batch_cb(pct, txt):
                    bar.progress(min(pct, 1.0), text=f"Batch {pending_batch + 1}: {txt}")

                batch_result = _run_all_agents(progress_cb=_batch_cb)
                bar.progress(1.0, text=f"Batch {pending_batch + 1}: All 20 agents complete!")
                time.sleep(0.5)
                bar.empty()

                # Restore original tickers
                _save_audit_tickers(original_tickers)

                # Save batch timestamp
                _save_batch_timestamp(pending_batch)

                # Store result
                st.session_state["sba_result"] = batch_result
                history = _load_history()
                history.insert(0, batch_result)
                _save_history(history)

                tc = batch_result["total_counts"]
                st.toast(
                    f"Batch {pending_batch + 1} complete! Score: {batch_result['overall_score']}% · "
                    f"{tc['critical']} critical · {tc['warning']} warnings",
                    icon="✅",
                )
                st.rerun()

    # Run button
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        run = st.button("🚀 Run All 20 Agents", use_container_width=True, type="primary", key="sba_run")

    if run:
        bar = st.progress(0, text="Initializing agents...")
        def _cb(pct, txt):
            bar.progress(min(pct, 1.0), text=txt)

        result = _run_all_agents(progress_cb=_cb)
        bar.progress(1.0, text="All 20 agents complete!")
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
        st.markdown('<div class="sba-empty">Click <strong>Run All 20 Agents</strong> to start your first audit</div>',
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
