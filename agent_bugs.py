"""
Agent Bugs — Automated site audit system for QuarterCharts NSFE dashboard.
Three subtabs: Manual Audit, Scan History, Live Monitor.
"""

import streamlit as st
import json
import os
import time
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Config ──────────────────────────────────────────────────────────────
_BASE_URL = "https://quartercharts.com"
_AUDIT_HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "audit_history.json"
)
_MAX_HISTORY = 50  # Keep last 50 audit runs

# ── Pages to audit ──────────────────────────────────────────────────────
_AUDIT_PAGES = {
    "Home":             "/?page=home",
    "Charts (NVDA)":    "/?page=charts&ticker=NVDA",
    "Sankey (NVDA)":    "/?page=sankey&ticker=NVDA",
    "Sankey (GOOG)":    "/?page=sankey&ticker=GOOG",
    "Profile (NVDA)":   "/?page=profile&ticker=NVDA",
    "Earnings":         "/?page=earnings",
    "Watchlist":        "/?page=watchlist",
    "Pricing":          "/?page=pricing",
    "Terms":            "/?page=terms",
    "Privacy":          "/?page=privacy",
}

_FREE_TICKERS = ["NVDA", "GOOG", "META", "TSLA"]


# ── Persistence ─────────────────────────────────────────────────────────

def _load_history() -> list:
    if os.path.exists(_AUDIT_HISTORY_FILE):
        try:
            with open(_AUDIT_HISTORY_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[:_MAX_HISTORY]
        except Exception:
            pass
    return []


def _save_history(history: list):
    try:
        with open(_AUDIT_HISTORY_FILE, "w") as f:
            json.dump(history[:_MAX_HISTORY], f, indent=2, default=str)
    except Exception:
        pass


# ── Audit Checks ────────────────────────────────────────────────────────

def _check_page_response(page_name: str, path: str) -> dict:
    """Check if a page responds and measure load time."""
    url = _BASE_URL + path
    try:
        start = time.time()
        resp = requests.get(url, timeout=15, allow_redirects=True,
                            headers={"User-Agent": "QuarterCharts-AuditBot/1.0"})
        elapsed = round(time.time() - start, 2)
        status = resp.status_code
        size_kb = round(len(resp.content) / 1024, 1)

        # Determine severity
        if status >= 500:
            severity = "critical"
            msg = f"Server error {status}"
        elif status >= 400:
            severity = "warning"
            msg = f"Client error {status}"
        elif elapsed > 8:
            severity = "critical"
            msg = f"Extremely slow: {elapsed}s"
        elif elapsed > 5:
            severity = "warning"
            msg = f"Slow load: {elapsed}s"
        elif elapsed > 3:
            severity = "info"
            msg = f"Acceptable: {elapsed}s"
        else:
            severity = "pass"
            msg = f"Fast: {elapsed}s"

        return {
            "page": page_name,
            "url": url,
            "status_code": status,
            "load_time": elapsed,
            "size_kb": size_kb,
            "severity": severity,
            "message": msg,
            "layer": "Performance",
        }
    except requests.Timeout:
        return {
            "page": page_name, "url": url, "status_code": 0,
            "load_time": 15, "size_kb": 0, "severity": "critical",
            "message": "Request timed out (>15s)", "layer": "Performance",
        }
    except Exception as e:
        return {
            "page": page_name, "url": url, "status_code": 0,
            "load_time": 0, "size_kb": 0, "severity": "critical",
            "message": f"Connection failed: {str(e)[:80]}", "layer": "Performance",
        }


def _check_seo_meta(page_name: str, path: str) -> list:
    """Check SEO meta tags on a page."""
    url = _BASE_URL + path
    findings = []
    try:
        resp = requests.get(url, timeout=12,
                            headers={"User-Agent": "QuarterCharts-AuditBot/1.0"})
        html = resp.text

        # Title tag
        if "<title>" in html.lower():
            import re
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""
            if not title or title == "Streamlit":
                findings.append({
                    "page": page_name, "severity": "warning", "layer": "SEO",
                    "message": f"Missing or default page title (got: '{title[:40]}')",
                })
            elif len(title) > 70:
                findings.append({
                    "page": page_name, "severity": "info", "layer": "SEO",
                    "message": f"Title too long ({len(title)} chars, max 60-70 recommended)",
                })
            else:
                findings.append({
                    "page": page_name, "severity": "pass", "layer": "SEO",
                    "message": f"Title OK: '{title[:50]}'",
                })
        else:
            findings.append({
                "page": page_name, "severity": "warning", "layer": "SEO",
                "message": "No <title> tag found",
            })

        # Meta description
        import re
        desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                               html, re.IGNORECASE)
        if desc_match:
            desc = desc_match.group(1)
            if len(desc) < 50:
                findings.append({
                    "page": page_name, "severity": "info", "layer": "SEO",
                    "message": f"Meta description too short ({len(desc)} chars)",
                })
            else:
                findings.append({
                    "page": page_name, "severity": "pass", "layer": "SEO",
                    "message": "Meta description present",
                })
        else:
            findings.append({
                "page": page_name, "severity": "warning", "layer": "SEO",
                "message": "Missing meta description",
            })

        # Open Graph
        og_match = re.search(r'<meta\s+property=["\']og:', html, re.IGNORECASE)
        if not og_match:
            findings.append({
                "page": page_name, "severity": "info", "layer": "SEO",
                "message": "No Open Graph tags found",
            })

        # Canonical URL
        canon_match = re.search(r'<link\s+rel=["\']canonical["\']', html, re.IGNORECASE)
        if not canon_match:
            findings.append({
                "page": page_name, "severity": "info", "layer": "SEO",
                "message": "No canonical URL tag",
            })

    except Exception as e:
        findings.append({
            "page": page_name, "severity": "warning", "layer": "SEO",
            "message": f"Could not check SEO: {str(e)[:60]}",
        })
    return findings


def _check_security_headers(page_name: str, path: str) -> list:
    """Check security-related HTTP headers."""
    url = _BASE_URL + path
    findings = []
    try:
        resp = requests.get(url, timeout=10,
                            headers={"User-Agent": "QuarterCharts-AuditBot/1.0"})
        headers = {k.lower(): v for k, v in resp.headers.items()}

        # HTTPS redirect
        if resp.url.startswith("https://"):
            findings.append({
                "page": page_name, "severity": "pass", "layer": "Security",
                "message": "HTTPS enforced",
            })
        else:
            findings.append({
                "page": page_name, "severity": "critical", "layer": "Security",
                "message": "Not served over HTTPS!",
            })

        # Key security headers
        checks = {
            "x-frame-options": "X-Frame-Options",
            "x-content-type-options": "X-Content-Type-Options",
            "strict-transport-security": "HSTS",
            "content-security-policy": "Content-Security-Policy",
            "referrer-policy": "Referrer-Policy",
        }
        for hdr, name in checks.items():
            if hdr in headers:
                findings.append({
                    "page": page_name, "severity": "pass", "layer": "Security",
                    "message": f"{name} header present",
                })
            else:
                sev = "warning" if hdr in ("content-security-policy", "referrer-policy") else "info"
                findings.append({
                    "page": page_name, "severity": sev, "layer": "Security",
                    "message": f"Missing {name} header",
                })

    except Exception as e:
        findings.append({
            "page": page_name, "severity": "warning", "layer": "Security",
            "message": f"Could not check headers: {str(e)[:60]}",
        })
    return findings


def _check_api_health() -> list:
    """Check SEC EDGAR and price API availability."""
    findings = []

    # SEC EDGAR
    for ticker in _FREE_TICKERS:
        try:
            start = time.time()
            resp = requests.get(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{_ticker_to_cik_simple(ticker)}.json",
                timeout=10,
                headers={"User-Agent": "QuarterCharts contact@quartercharts.com"}
            )
            elapsed = round(time.time() - start, 2)
            if resp.status_code == 200:
                findings.append({
                    "page": f"API: SEC EDGAR ({ticker})", "severity": "pass",
                    "layer": "API Health",
                    "message": f"SEC EDGAR OK for {ticker} ({elapsed}s)",
                })
            else:
                findings.append({
                    "page": f"API: SEC EDGAR ({ticker})", "severity": "warning",
                    "layer": "API Health",
                    "message": f"SEC EDGAR returned {resp.status_code} for {ticker}",
                })
        except Exception as e:
            findings.append({
                "page": f"API: SEC EDGAR ({ticker})", "severity": "critical",
                "layer": "API Health",
                "message": f"SEC EDGAR unreachable for {ticker}: {str(e)[:50]}",
            })

    # Price API
    try:
        start = time.time()
        resp = requests.get(f"{_BASE_URL}:8502/price?ticker=NVDA", timeout=5)
        elapsed = round(time.time() - start, 2)
        if resp.status_code == 200:
            findings.append({
                "page": "API: Price Daemon", "severity": "pass",
                "layer": "API Health",
                "message": f"Price API responding ({elapsed}s)",
            })
        else:
            findings.append({
                "page": "API: Price Daemon", "severity": "warning",
                "layer": "API Health",
                "message": f"Price API returned {resp.status_code}",
            })
    except Exception:
        findings.append({
            "page": "API: Price Daemon", "severity": "info",
            "layer": "API Health",
            "message": "Price API not reachable (may be internal-only port)",
        })

    return findings


def _check_accessibility_basic(page_name: str, path: str) -> list:
    """Basic accessibility checks on HTML content."""
    url = _BASE_URL + path
    findings = []
    try:
        import re
        resp = requests.get(url, timeout=12,
                            headers={"User-Agent": "QuarterCharts-AuditBot/1.0"})
        html = resp.text

        # Check for lang attribute on html tag
        if re.search(r'<html[^>]+lang=', html, re.IGNORECASE):
            findings.append({
                "page": page_name, "severity": "pass", "layer": "Accessibility",
                "message": "HTML lang attribute present",
            })
        else:
            findings.append({
                "page": page_name, "severity": "warning", "layer": "Accessibility",
                "message": "Missing lang attribute on <html> tag",
            })

        # Check for images without alt text
        imgs = re.findall(r'<img\s+[^>]*?>', html, re.IGNORECASE)
        imgs_no_alt = [i for i in imgs if 'alt=' not in i.lower()]
        if imgs_no_alt:
            findings.append({
                "page": page_name, "severity": "warning", "layer": "Accessibility",
                "message": f"{len(imgs_no_alt)} image(s) missing alt text",
            })
        elif imgs:
            findings.append({
                "page": page_name, "severity": "pass", "layer": "Accessibility",
                "message": f"All {len(imgs)} images have alt text",
            })

        # Check for skip navigation link
        if 'skip' in html.lower() and 'nav' in html.lower():
            findings.append({
                "page": page_name, "severity": "pass", "layer": "Accessibility",
                "message": "Skip navigation link detected",
            })

        # Check viewport meta tag
        if re.search(r'<meta\s+name=["\']viewport["\']', html, re.IGNORECASE):
            findings.append({
                "page": page_name, "severity": "pass", "layer": "Accessibility",
                "message": "Viewport meta tag present",
            })
        else:
            findings.append({
                "page": page_name, "severity": "info", "layer": "Accessibility",
                "message": "Missing viewport meta tag (Streamlit may handle this)",
            })

    except Exception as e:
        findings.append({
            "page": page_name, "severity": "info", "layer": "Accessibility",
            "message": f"Could not check accessibility: {str(e)[:50]}",
        })
    return findings


def _ticker_to_cik_simple(ticker: str) -> str:
    """Simple ticker to CIK mapping for common tickers."""
    _MAP = {
        "NVDA": "0001045810", "GOOG": "0001652044", "GOOGL": "0001652044",
        "META": "0001326801", "TSLA": "0001318605", "AAPL": "0000320193",
        "MSFT": "0000789019", "AMZN": "0001018724",
    }
    return _MAP.get(ticker.upper(), "")


# ── Full Audit Runner ───────────────────────────────────────────────────

def _run_full_audit(layers: list[str] = None, progress_callback=None) -> dict:
    """Run a comprehensive site audit across all selected layers.
    Returns a dict with findings, scores, and metadata."""

    if layers is None:
        layers = ["Performance", "SEO", "Security", "API Health", "Accessibility"]

    all_findings = []
    total_steps = 0
    if "Performance" in layers:
        total_steps += len(_AUDIT_PAGES)
    if "SEO" in layers:
        total_steps += len(_AUDIT_PAGES)
    if "Security" in layers:
        total_steps += 1  # Only need to check once
    if "API Health" in layers:
        total_steps += 1
    if "Accessibility" in layers:
        total_steps += len(_AUDIT_PAGES)

    current_step = 0

    # ── Performance: page response times ──
    if "Performance" in layers:
        for name, path in _AUDIT_PAGES.items():
            result = _check_page_response(name, path)
            all_findings.append(result)
            current_step += 1
            if progress_callback:
                progress_callback(current_step / max(total_steps, 1),
                                  f"Performance: {name}")

    # ── SEO: meta tags ──
    if "SEO" in layers:
        for name, path in _AUDIT_PAGES.items():
            seo_results = _check_seo_meta(name, path)
            all_findings.extend(seo_results)
            current_step += 1
            if progress_callback:
                progress_callback(current_step / max(total_steps, 1),
                                  f"SEO: {name}")

    # ── Security: headers (check home page only, headers are global) ──
    if "Security" in layers:
        sec_results = _check_security_headers("Home", "/?page=home")
        all_findings.extend(sec_results)
        current_step += 1
        if progress_callback:
            progress_callback(current_step / max(total_steps, 1),
                              "Security headers")

    # ── API Health ──
    if "API Health" in layers:
        api_results = _check_api_health()
        all_findings.extend(api_results)
        current_step += 1
        if progress_callback:
            progress_callback(current_step / max(total_steps, 1),
                              "API health checks")

    # ── Accessibility ──
    if "Accessibility" in layers:
        for name, path in _AUDIT_PAGES.items():
            a11y_results = _check_accessibility_basic(name, path)
            all_findings.extend(a11y_results)
            current_step += 1
            if progress_callback:
                progress_callback(current_step / max(total_steps, 1),
                                  f"Accessibility: {name}")

    # ── Calculate scores per layer ──
    scores = {}
    for layer in layers:
        layer_findings = [f for f in all_findings if f.get("layer") == layer]
        if not layer_findings:
            scores[layer] = 100
            continue
        total = len(layer_findings)
        passed = sum(1 for f in layer_findings if f["severity"] == "pass")
        scores[layer] = round((passed / total) * 100) if total > 0 else 100

    overall = round(sum(scores.values()) / len(scores)) if scores else 0

    # Severity counts
    counts = {"critical": 0, "warning": 0, "info": 0, "pass": 0}
    for f in all_findings:
        sev = f.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1

    audit_result = {
        "timestamp": datetime.now().isoformat(),
        "layers": layers,
        "overall_score": overall,
        "scores": scores,
        "counts": counts,
        "findings": all_findings,
        "pages_checked": len(_AUDIT_PAGES),
        "total_findings": len(all_findings),
    }

    return audit_result


# ── CSS Styles ──────────────────────────────────────────────────────────

_AGENT_BUGS_STYLES = """
<style>
.ab-header {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 14px; padding: 20px 24px; margin-bottom: 1.25rem;
    border: 1px solid rgba(255,255,255,0.06);
}
.ab-title { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; margin: 0 0 4px; }
.ab-sub   { font-size: 0.82rem; color: #94a3b8; margin: 0; }
.ab-score-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 1rem 0; }
.ab-score-card {
    flex: 1; min-width: 120px;
    background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 16px; text-align: center;
}
.ab-score-val { font-size: 1.8rem; font-weight: 800; margin: 0; }
.ab-score-label { font-size: 0.72rem; color: #64748b; margin: 4px 0 0;
    text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
.ab-badge-critical { background: #fef2f2; color: #dc2626; font-size: 0.72rem;
    font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid #fecaca; }
.ab-badge-warning { background: #fffbeb; color: #d97706; font-size: 0.72rem;
    font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid #fde68a; }
.ab-badge-info { background: #eff6ff; color: #2563eb; font-size: 0.72rem;
    font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid #bfdbfe; }
.ab-badge-pass { background: #f0fdf4; color: #16a34a; font-size: 0.72rem;
    font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid #bbf7d0; }
.ab-finding-row {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; border-bottom: 1px solid #f1f5f9;
}
.ab-finding-row:hover { background: #f8fafc; }
.ab-finding-page { font-weight: 600; color: #1e293b; font-size: 0.85rem; min-width: 130px; }
.ab-finding-msg  { color: #475569; font-size: 0.83rem; flex: 1; }
.ab-finding-layer { color: #94a3b8; font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; min-width: 80px; text-align: right; }
.ab-history-card {
    border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px;
    background: #fff; margin-bottom: 10px; cursor: pointer;
    transition: box-shadow 0.15s;
}
.ab-history-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.ab-history-date { font-weight: 600; color: #1e293b; font-size: 0.9rem; }
.ab-history-meta { font-size: 0.78rem; color: #94a3b8; margin-top: 2px; }
.ab-monitor-card {
    border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;
    background: #fff; text-align: center;
}
.ab-monitor-val { font-size: 2.2rem; font-weight: 800; margin: 0; }
.ab-monitor-label { font-size: 0.78rem; color: #64748b; margin: 6px 0 0;
    text-transform: uppercase; font-weight: 600; }
.ab-monitor-trend { font-size: 0.78rem; margin-top: 4px; }
.ab-progress-bar {
    height: 8px; background: #e2e8f0; border-radius: 4px;
    overflow: hidden; margin: 8px 0;
}
.ab-progress-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.ab-layer-section {
    border: 1px solid #e2e8f0; border-radius: 12px;
    margin-bottom: 12px; overflow: hidden;
}
.ab-layer-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
}
.ab-layer-name { font-weight: 700; font-size: 0.9rem; color: #1e293b; }
.ab-layer-score { font-weight: 800; font-size: 0.9rem; }
.ab-empty { text-align: center; padding: 40px 20px; color: #94a3b8; font-size: 0.9rem; }
</style>
"""


def _severity_badge(severity: str) -> str:
    return f'<span class="ab-badge-{severity}">{severity.upper()}</span>'


def _score_color(score: int) -> str:
    if score >= 80:
        return "#16a34a"
    elif score >= 60:
        return "#d97706"
    else:
        return "#dc2626"


# ── Render Functions ────────────────────────────────────────────────────

def _render_manual_audit():
    """Subtab 1: Manual Trigger + Report."""

    st.markdown("""
    <div class="ab-header">
        <div class="ab-title">🔍 Manual Site Audit</div>
        <p class="ab-sub">Run a comprehensive audit of quartercharts.com across all layers.
        Click the button below to start — takes ~30-60 seconds.</p>
    </div>
    """, unsafe_allow_html=True)

    # Layer selection
    all_layers = ["Performance", "SEO", "Security", "API Health", "Accessibility"]
    selected_layers = st.pills("Audit layers", all_layers, default=all_layers,
                               selection_mode="multi", key="ab_layers")
    if not selected_layers:
        selected_layers = all_layers

    # Run button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run_clicked = st.button("🚀 Run Full Audit", use_container_width=True,
                                type="primary", key="ab_run_audit")

    # Show last audit results if stored in session
    if run_clicked:
        progress_bar = st.progress(0, text="Starting audit...")
        status_text = st.empty()

        def _update_progress(pct, text):
            progress_bar.progress(min(pct, 1.0), text=f"Checking: {text}")

        result = _run_full_audit(layers=list(selected_layers),
                                 progress_callback=_update_progress)

        progress_bar.progress(1.0, text="Audit complete!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

        # Store in session and save to history
        st.session_state["ab_last_audit"] = result
        history = _load_history()
        history.insert(0, result)
        _save_history(history)

        st.toast("Audit complete!", icon="✅")

    # Display results
    result = st.session_state.get("ab_last_audit")
    if not result:
        st.markdown('<div class="ab-empty">No audit results yet. Click <strong>Run Full Audit</strong> to start.</div>',
                    unsafe_allow_html=True)
        return

    # ── Score cards ──
    overall = result["overall_score"]
    counts = result["counts"]
    ts = result["timestamp"]
    try:
        dt = datetime.fromisoformat(ts)
        time_str = dt.strftime("%b %d, %Y at %H:%M")
    except Exception:
        time_str = ts[:19]

    st.markdown(f"""
    <div style="text-align:center; margin: 0.5rem 0 0.25rem;">
        <span style="font-size:0.78rem; color:#94a3b8;">Last run: {time_str}</span>
    </div>
    """, unsafe_allow_html=True)

    score_cards = ""
    score_cards += f'''<div class="ab-score-card">
        <div class="ab-score-val" style="color:{_score_color(overall)}">{overall}</div>
        <div class="ab-score-label">Overall Score</div></div>'''
    score_cards += f'''<div class="ab-score-card">
        <div class="ab-score-val" style="color:#dc2626">{counts.get("critical", 0)}</div>
        <div class="ab-score-label">Critical</div></div>'''
    score_cards += f'''<div class="ab-score-card">
        <div class="ab-score-val" style="color:#d97706">{counts.get("warning", 0)}</div>
        <div class="ab-score-label">Warnings</div></div>'''
    score_cards += f'''<div class="ab-score-card">
        <div class="ab-score-val" style="color:#2563eb">{counts.get("info", 0)}</div>
        <div class="ab-score-label">Info</div></div>'''
    score_cards += f'''<div class="ab-score-card">
        <div class="ab-score-val" style="color:#16a34a">{counts.get("pass", 0)}</div>
        <div class="ab-score-label">Passed</div></div>'''

    st.markdown(f'<div class="ab-score-row">{score_cards}</div>', unsafe_allow_html=True)

    # ── Findings by layer ──
    findings = result.get("findings", [])
    scores = result.get("scores", {})

    for layer in result.get("layers", []):
        layer_findings = [f for f in findings if f.get("layer") == layer]
        layer_score = scores.get(layer, 0)
        score_clr = _score_color(layer_score)

        non_pass = [f for f in layer_findings if f["severity"] != "pass"]
        passed = [f for f in layer_findings if f["severity"] == "pass"]

        # Layer section header
        icon_map = {"Performance": "⚡", "SEO": "🔍", "Security": "🛡️",
                    "API Health": "🔌", "Accessibility": "♿"}
        icon = icon_map.get(layer, "📋")

        bar_color = score_clr
        st.markdown(f"""
        <div class="ab-layer-section">
            <div class="ab-layer-header">
                <span class="ab-layer-name">{icon} {layer}</span>
                <span class="ab-layer-score" style="color:{score_clr}">{layer_score}/100</span>
            </div>
            <div class="ab-progress-bar" style="margin:0;">
                <div class="ab-progress-fill" style="width:{layer_score}%;background:{bar_color};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Show non-pass findings in expander
        if non_pass:
            with st.expander(f"Issues ({len(non_pass)})", expanded=len(non_pass) <= 8):
                rows = ""
                for f in sorted(non_pass, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)):
                    rows += f"""
                    <div class="ab-finding-row">
                        {_severity_badge(f['severity'])}
                        <span class="ab-finding-page">{f.get('page', '—')}</span>
                        <span class="ab-finding-msg">{f.get('message', '')}</span>
                    </div>"""
                st.markdown(rows, unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="padding:8px 16px; font-size:0.83rem; color:#16a34a;">All checks passed</div>',
                        unsafe_allow_html=True)


def _render_scan_history():
    """Subtab 2: Auto-Scan + History."""

    st.markdown("""
    <div class="ab-header">
        <div class="ab-title">📅 Scan History</div>
        <p class="ab-sub">View past audit results and track regressions over time.
        Each manual or scheduled audit is stored here automatically.</p>
    </div>
    """, unsafe_allow_html=True)

    history = _load_history()

    if not history:
        st.markdown('<div class="ab-empty">No audit history yet. Run your first audit from the Manual Audit tab.</div>',
                    unsafe_allow_html=True)
        return

    # ── Trend line (overall scores over time) ──
    st.markdown("### Score Trend")
    if len(history) >= 2:
        import pandas as pd
        trend_data = []
        for h in reversed(history[:20]):  # Last 20, oldest first
            try:
                dt = datetime.fromisoformat(h["timestamp"])
                trend_data.append({
                    "Date": dt.strftime("%m/%d %H:%M"),
                    "Overall": h.get("overall_score", 0),
                })
            except Exception:
                pass

        if trend_data:
            df = pd.DataFrame(trend_data)
            st.line_chart(df.set_index("Date"), use_container_width=True, height=200)
    else:
        st.caption("Run at least 2 audits to see the trend chart.")

    # ── Comparison: latest vs previous ──
    if len(history) >= 2:
        latest = history[0]
        previous = history[1]
        diff = latest.get("overall_score", 0) - previous.get("overall_score", 0)
        diff_color = "#16a34a" if diff >= 0 else "#dc2626"
        diff_arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
        diff_text = f"{diff_arrow} {abs(diff)} pts" if diff != 0 else "No change"

        st.markdown(f"""
        <div style="display:flex; gap:16px; margin: 0.75rem 0 1rem;">
            <div class="ab-score-card" style="flex:1;">
                <div class="ab-score-val" style="color:{_score_color(latest.get('overall_score', 0))}">{latest.get('overall_score', 0)}</div>
                <div class="ab-score-label">Latest Score</div>
            </div>
            <div class="ab-score-card" style="flex:1;">
                <div class="ab-score-val" style="color:{_score_color(previous.get('overall_score', 0))}">{previous.get('overall_score', 0)}</div>
                <div class="ab-score-label">Previous Score</div>
            </div>
            <div class="ab-score-card" style="flex:1;">
                <div class="ab-score-val" style="color:{diff_color}">{diff_text}</div>
                <div class="ab-score-label">Change</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── History list ──
    st.markdown("### All Audits")
    for i, h in enumerate(history[:20]):
        try:
            dt = datetime.fromisoformat(h["timestamp"])
            date_str = dt.strftime("%b %d, %Y at %H:%M")
        except Exception:
            date_str = h.get("timestamp", "Unknown")[:19]

        overall = h.get("overall_score", 0)
        counts = h.get("counts", {})
        critical = counts.get("critical", 0)
        warnings = counts.get("warning", 0)
        layers = ", ".join(h.get("layers", []))

        score_clr = _score_color(overall)
        warning_tag = f' · <span style="color:#dc2626;">{critical} critical</span>' if critical > 0 else ""

        st.markdown(f"""
        <div class="ab-history-card">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div>
                    <div class="ab-history-date">{date_str}</div>
                    <div class="ab-history-meta">{layers}{warning_tag}</div>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:1.4rem; font-weight:800; color:{score_clr};">{overall}</span>
                    <div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">score</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Details — {date_str}", expanded=False):
            # Show scores per layer
            layer_scores = h.get("scores", {})
            for layer, score in layer_scores.items():
                bar_clr = _score_color(score)
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px; margin:4px 0;">
                    <span style="font-size:0.83rem; font-weight:600; min-width:110px;">{layer}</span>
                    <div class="ab-progress-bar" style="flex:1;">
                        <div class="ab-progress-fill" style="width:{score}%;background:{bar_clr};"></div>
                    </div>
                    <span style="font-size:0.83rem; font-weight:700; color:{bar_clr}; min-width:40px; text-align:right;">{score}%</span>
                </div>
                """, unsafe_allow_html=True)

            # Show non-pass findings
            findings = [f for f in h.get("findings", []) if f.get("severity") != "pass"]
            if findings:
                rows = ""
                for f in sorted(findings, key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)):
                    rows += f"""
                    <div class="ab-finding-row">
                        {_severity_badge(f['severity'])}
                        <span class="ab-finding-page">{f.get('page', '—')}</span>
                        <span class="ab-finding-msg">{f.get('message', '')}</span>
                    </div>"""
                st.markdown(rows, unsafe_allow_html=True)
            else:
                st.success("All checks passed in this audit.")

    # ── Clear history ──
    st.markdown("---")
    if st.button("🗑️ Clear Audit History", key="ab_clear_history"):
        _save_history([])
        st.session_state.pop("ab_last_audit", None)
        st.toast("Audit history cleared.", icon="🗑️")
        st.rerun()


def _render_live_monitor():
    """Subtab 3: Live Monitoring Dashboard."""

    st.markdown("""
    <div class="ab-header">
        <div class="ab-title">📡 Live Monitor</div>
        <p class="ab-sub">Real-time health dashboard for quartercharts.com.
        Shows current status, uptime, and response times with auto-refresh.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Quick health check (lightweight, just pings key pages) ──
    auto_refresh = st.toggle("Auto-refresh (every 60s)", value=False, key="ab_auto_refresh")

    if auto_refresh:
        st.caption("Dashboard refreshes automatically. Toggle off to stop.")

    # Run lightweight health check
    st.markdown("### Current Status")

    # Quick ping key pages
    _MONITOR_PAGES = {
        "Home":     "/?page=home",
        "Sankey":   "/?page=sankey&ticker=NVDA",
        "Charts":   "/?page=charts&ticker=NVDA",
        "Profile":  "/?page=profile&ticker=NVDA",
        "Earnings": "/?page=earnings",
        "Pricing":  "/?page=pricing",
    }

    results = {}
    with st.spinner("Checking site health..."):
        for name, path in _MONITOR_PAGES.items():
            url = _BASE_URL + path
            try:
                start = time.time()
                resp = requests.get(url, timeout=10,
                                    headers={"User-Agent": "QuarterCharts-Monitor/1.0"})
                elapsed = round(time.time() - start, 2)
                results[name] = {
                    "status": resp.status_code,
                    "time": elapsed,
                    "ok": 200 <= resp.status_code < 400,
                    "size_kb": round(len(resp.content) / 1024, 1),
                }
            except Exception:
                results[name] = {"status": 0, "time": 0, "ok": False, "size_kb": 0}

    # ── Status overview cards ──
    all_ok = all(r["ok"] for r in results.values())
    avg_time = round(sum(r["time"] for r in results.values()) / max(len(results), 1), 2)
    pages_up = sum(1 for r in results.values() if r["ok"])

    status_color = "#16a34a" if all_ok else "#dc2626"
    status_text = "All Systems Operational" if all_ok else f"{len(results) - pages_up} Page(s) Down"
    status_icon = "🟢" if all_ok else "🔴"

    st.markdown(f"""
    <div style="text-align:center; padding:20px; border:2px solid {status_color}22;
                border-radius:14px; background:{status_color}08; margin-bottom:1rem;">
        <div style="font-size:2rem;">{status_icon}</div>
        <div style="font-size:1.2rem; font-weight:700; color:{status_color}; margin-top:4px;">
            {status_text}
        </div>
        <div style="font-size:0.82rem; color:#64748b; margin-top:4px;">
            {pages_up}/{len(results)} pages responding · Avg response: {avg_time}s
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Per-page status cards ──
    cols_per_row = 3
    page_names = list(results.keys())
    for i in range(0, len(page_names), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(page_names):
                break
            name = page_names[idx]
            r = results[name]
            with col:
                if r["ok"]:
                    if r["time"] <= 3:
                        card_clr = "#16a34a"
                        label = "Fast"
                    elif r["time"] <= 5:
                        card_clr = "#d97706"
                        label = "Slow"
                    else:
                        card_clr = "#dc2626"
                        label = "Very Slow"
                else:
                    card_clr = "#dc2626"
                    label = "Down"

                st.markdown(f"""
                <div class="ab-monitor-card">
                    <div style="font-weight:600; font-size:0.85rem; color:#1e293b; margin-bottom:6px;">{name}</div>
                    <div class="ab-monitor-val" style="color:{card_clr}">{r['time']}s</div>
                    <div class="ab-monitor-label">{label} · {r['status']} · {r['size_kb']}KB</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Response time bar chart ──
    st.markdown("### Response Times")
    import pandas as pd
    chart_data = pd.DataFrame({
        "Page": list(results.keys()),
        "Load Time (s)": [r["time"] for r in results.values()],
    }).set_index("Page")
    st.bar_chart(chart_data, use_container_width=True, height=250)

    # ── Historical trend (from audit history) ──
    st.markdown("### Health Trend (from audits)")
    history = _load_history()
    if len(history) >= 2:
        trend_data = []
        for h in reversed(history[:15]):
            try:
                dt = datetime.fromisoformat(h["timestamp"])
                entry = {"Date": dt.strftime("%m/%d")}
                for layer, score in h.get("scores", {}).items():
                    entry[layer] = score
                trend_data.append(entry)
            except Exception:
                pass
        if trend_data:
            df = pd.DataFrame(trend_data).set_index("Date")
            st.line_chart(df, use_container_width=True, height=250)
    else:
        st.caption("Run at least 2 audits to see historical trends here.")

    # ── External tools links ──
    st.markdown("### Quick External Tools")
    _ext_cols = st.columns(4)
    _ext_tools = [
        ("⚡ PageSpeed", "https://pagespeed.web.dev/analysis?url=https://quartercharts.com"),
        ("📱 Mobile Test", "https://search.google.com/test/mobile-friendly?url=https://quartercharts.com"),
        ("🔒 SSL Check", "https://www.sslshopper.com/ssl-checker.html#hostname=quartercharts.com"),
        ("🌐 Uptime", "https://uptimerobot.com"),
    ]
    for k, (label, url) in enumerate(_ext_tools):
        with _ext_cols[k]:
            st.markdown(f"""
            <a href="{url}" target="_blank"
               style="display:block; text-align:center; padding:12px; border:1px solid #e2e8f0;
                      border-radius:10px; text-decoration:none; color:#1e293b; background:#fff;
                      box-shadow:0 1px 3px rgba(0,0,0,0.04); font-size:13px; font-weight:500;">
                {label}
            </a>
            """, unsafe_allow_html=True)

    # Auto-refresh trigger
    if auto_refresh:
        time.sleep(0.5)
        st.markdown(f"""
        <script>
        setTimeout(function() {{
            // Trigger Streamlit rerun by simulating a widget change
            window.parent.postMessage({{type: 'streamlit:rerun'}}, '*');
        }}, 60000);
        </script>
        """, unsafe_allow_html=True)


# ── Main Entry Point ────────────────────────────────────────────────────

def render_agent_bugs():
    """Main renderer for the Agent Bugs tab in NSFE."""
    st.markdown(_AGENT_BUGS_STYLES, unsafe_allow_html=True)

    # 3 subtabs
    sub1, sub2, sub3 = st.tabs([
        "🔍 Manual Audit",
        "📅 Scan History",
        "📡 Live Monitor",
    ])

    with sub1:
        _render_manual_audit()
    with sub2:
        _render_scan_history()
    with sub3:
        _render_live_monitor()
