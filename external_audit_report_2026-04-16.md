# QuarterCharts External Monitoring Audit Report
**Date:** April 16, 2026  
**Site:** https://quartercharts.com  

---

## Summary

| Category | Tool | Score/Grade | Status |
|----------|------|-------------|--------|
| Speed & Performance | GTmetrix | Grade C (66%) | Needs improvement |
| Speed & Performance | PageSpeed Insights | Error (SPA not rendered) | Critical |
| SEO & Search | Google Search Console | 1/98 pages indexed | Critical |
| Security & SSL | Security Headers | Grade A | Good (warnings) |
| Uptime & Availability | UptimeRobot | Fixed (was misconfigured) | Monitoring |
| Accessibility | WAVE | 9.9/10 | Excellent |

---

## Critical Issues (Fix Immediately)

### 1. Only 1 page indexed by Google (SEO)
- **Source:** Google Search Console
- **Details:** Out of 98 known pages, only 1 is indexed
  - 43 pages: "Alternate page with proper canonical tag"
  - 54 pages: "Discovered - currently not indexed"
- **Impact:** Site is essentially invisible in Google Search (only 6 clicks in 3 weeks)
- **Fix:** Investigate canonical tag setup, ensure pages render for Googlebot, request re-indexing

### 2. Lighthouse / PageSpeed Insights cannot render the site
- **Source:** PageSpeed Insights (Mobile)
- **Details:** All metrics returned "Error! The page did not paint any content"
- **Impact:** If Lighthouse can't render, Googlebot may also fail — explaining the indexing problem
- **Fix:** Implement server-side rendering (SSR) or pre-rendering for Streamlit app. Consider adding a static HTML shell that loads before Streamlit hydrates.

### 3. UptimeRobot monitor was misconfigured
- **Source:** UptimeRobot
- **Details:** URL was set to "www.https://quartercharts.com/" causing DNS resolution failure
- **Status:** FIXED — URL corrected to "https://quartercharts.com/"

---

## High Priority Issues

### 4. No CDN — 41 resources served from origin
- **Source:** GTmetrix
- **Impact:** Slower load times globally, no edge caching
- **Fix:** Set up Cloudflare, AWS CloudFront, or similar CDN for static assets

### 5. LCP 3.0s (target: < 2.5s)
- **Source:** GTmetrix
- **Details:** Largest Contentful Paint element is a button. 96% of LCP time is render delay (2.9s waiting for WebSocket data)
- **Fix:** Show a static placeholder/skeleton UI before WebSocket data arrives

### 6. FCP 2.5s (target: < 1.8s)
- **Source:** GTmetrix
- **Fix:** Reduce critical request chain (currently 640ms max latency), preload key resources

### 7. Speed Index 3.9s (target: < 1.3s)
- **Source:** GTmetrix
- **Fix:** Reduce render-blocking resources, add skeleton loading states

### 8. 369KB unused JavaScript
- **Source:** GTmetrix
- **Details:**
  - `src.BnXM6qiK.js`: 206KB (157KB unused)
  - Google Tag Manager: 136KB (80KB unused)
  - `protobuf.DYxUUxb3.js`: 71KB (58KB unused)
  - `index.k-9rUdPI.js`: 73KB (44KB unused)
- **Fix:** Code-split, tree-shake, defer non-critical scripts

### 9. CSP uses unsafe-inline and unsafe-eval
- **Source:** Security Headers
- **Details:** Content-Security-Policy script-src includes 'unsafe-inline' and 'unsafe-eval'
- **Impact:** Weakens XSS protection significantly
- **Fix:** Use nonce-based CSP or hash-based CSP instead of unsafe-inline/eval

---

## Medium Priority Issues

### 10. Font-display: swap not set
- **Source:** GTmetrix
- **Details:** SourceSansVF woff2 (167KB) blocks text rendering for 922ms
- **Fix:** Add `font-display: swap` to @font-face declarations

### 11. WebSocket blocks bfcache
- **Source:** GTmetrix
- **Details:** Pages using WebSocket cannot enter back/forward cache
- **Impact:** Navigation between pages is slower
- **Fix:** Known Streamlit limitation; consider closing WebSocket on page hide

### 12. 866KB total page size
- **Source:** GTmetrix
- **Breakdown:** JS 685KB, Fonts 166KB, CSS 8.5KB, HTML 3.5KB
- **Fix:** Lazy load non-critical JS, subset fonts, enable aggressive compression

### 13. Missing Cross-Origin headers
- **Source:** Security Headers
- **Missing:**
  - Cross-Origin-Embedder-Policy
  - Cross-Origin-Opener-Policy
  - Cross-Origin-Resource-Policy
- **Fix:** Add these headers in Railway/server config

### 14. Legacy JavaScript polyfills
- **Source:** GTmetrix
- **Details:** Babel transforms (plugin-transform-classes, plugin-transform-spread) adding ~3KB unnecessary code
- **Fix:** Update build target to modern browsers, remove legacy polyfills

---

## Low Priority Issues

### 15. No heading structure (Accessibility)
- **Source:** WAVE
- **Fix:** Ensure Streamlit pages include proper H1-H6 hierarchy

### 16. No page regions/landmarks (Accessibility)
- **Source:** WAVE
- **Fix:** Add ARIA landmark roles (header, nav, main, footer)

### 17. Noscript fallback
- **Source:** WAVE
- **Details:** Shows noscript element for non-JS browsers
- **Status:** Expected for SPA — no action needed

---

## Good Results (No Action Needed)

- **TBT (Total Blocking Time):** 0ms — Excellent
- **CLS (Cumulative Layout Shift):** 0 — Excellent
- **TTFB:** 120ms — Good
- **Security Headers:** Grade A — All major headers present
- **HSTS:** Enabled with includeSubDomains and preload
- **Accessibility:** 9.9/10 — No errors, no contrast issues
- **HTML lang attribute:** Present (en)
- **HTTP/2:** Enabled
- **Gzip compression:** Enabled
- **CSS/JS minification:** Already done
- **Server header:** "railway-edge" (no sensitive info disclosed)
