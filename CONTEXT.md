# QuarterCharts — Developer Context & Memory

> **Auto-updated** | Last modified: 2026-04-02
> This file is the living memory for AI-assisted development sessions.

---

## 1. Architecture

**Stack:** Streamlit + Plotly + Tornado + Custom HTML/CSS/JS
**Hosting:** Railway (auto-deploy from GitHub)
**Repo:** `github.com/miteproyects/opensankey`
**Port:** Streamlit on 8501, Price API on 8502

### Data Sources
| Source | Usage | Auth | Cache TTL |
|--------|-------|------|-----------|
| SEC EDGAR XBRL | Financial statements (income, balance, cash flow) | None (free) | 3600s |
| Yahoo Finance (yfinance) | Price, fundamentals, ownership, insider trades | None | 1800s |
| Finnhub API | Earnings calendar | API key (env var) | 900s |
| FMP API | Forecasts (optional) | API key (250/day free) | 3600s |
| Tornado price daemon | Real-time price polling | None | 1.5s |

### Page Routes
| Route | Page | File |
|-------|------|------|
| `/` | Home / Landing | `home_page.py` |
| `/?page=charts` | Income Statement Charts | (in `app.py` routing) |
| `/?page=sankey` | Sankey Diagrams | `sankey_page.py` |
| `/?page=profile` | Company Profile | `profile_page.py` |
| `/?page=earnings` | Earnings Calendar | `earnings_page.py` |
| `/?page=watchlist` | Saved Tickers | (in `app.py`) |
| `/?page=pricing` | Upgrade Page | `pricing_page.py` |
| `/?page=login` | Auth / Login | `login_page.py` |
| `/?page=terms` | Terms of Service | `terms_page.py` |
| `/?page=privacy` | Privacy Policy | `privacy_page.py` |
| `/?page=nsfe` | Admin Control Center | `nsfe_page.py` |

---

## 2. File Map

| File | Purpose |
|------|---------|
| `app.py` | Main entry point — routing, sidebar, navbar, footer, session mgmt |
| `home_page.py` | Landing page — hero, ticker search, feature showcase, pricing cards |
| `profile_page.py` | Company profile — fundamentals, technicals, ownership, DCF, candlestick |
| `sankey_page.py` | Sankey diagrams — income + balance sheet flows, KPI cards, metric pills |
| `earnings_page.py` | Earnings calendar — Finnhub API, week view Mon-Sun, ticker search |
| `charts.py` | Base Plotly layout + color palette for all charts |
| `data_fetcher.py` | Core data — yfinance, SEC EDGAR XBRL, FMP APIs |
| `info_data.py` | Profile data — SEC EDGAR + Yahoo for fundamentals/technicals |
| `info_charts.py` | Profile charts — ownership pie, institutional bar, insider activity |
| `price_api.py` | Tornado HTTP daemon for real-time price on port 8502 |
| `nsfe_page.py` | Admin panel — dashboard, security, settings, AI, SEO, pricing admin |
| `auth.py` | Firebase Auth — JWT, user creation, session management |
| `database.py` | PostgreSQL — connection pool, CRUD, schema, multi-tenant |
| `security_headers.py` | HTTP security headers injection |
| `stripe_checkout.py` | Stripe payment integration |
| `login_page.py` | Login/signup UI — email/password + Google SSO |
| `dashboard_page.py` | User dashboard (post-login) |

---

## 3. Design System

### Color Palette
```
Primary Blue:    #3B82F6
Dark Slate:      #1e293b / #0f172a
Text Dark:       #1e293b
Text Muted:      #64748b / #94a3b8
Background:      #ffffff
Card Border:     #e2e8f0
Card Shadow:     0 1px 4px rgba(0,0,0,0.05), 0 6px 20px rgba(0,0,0,0.04)
```

### Sankey Node Colors (VIVID palette)
```
Revenue:         #22c55e (green)
Cost of Revenue: #ef4444 (red)
Gross Profit:    #3b82f6 (blue)
R&D:             #f59e0b (amber)
SG&A:            #f97316 (orange)
D&A / Other:     #a855f7 (purple)
Operating Inc:   #06b6d4 (cyan)
Interest Exp:    #64748b (slate)
Pretax Income:   #6366f1 (indigo)
Income Tax:      #ec4899 (pink)
Net Income:      #84cc16 (lime)
```

### CSS Conventions
- Cards: `border-radius: 14-16px`, white bg, subtle shadow, hover lift
- Pills: `data-testid="stBaseButton-pills"` (NOT `stPillsButton`)
- Font: Inter via Google Fonts import
- Navbar padding: `0 14px`
- All charts: `dragmode=False`, `scrollZoom: False`
- Inject CSS via `st.markdown(unsafe_allow_html=True)`

---

## 4. Known Gotchas & Patterns

### Streamlit Quirks
- **4+ leading spaces** in f-strings render as preformatted code blocks
- **Session state after widget**: Cannot modify `st.session_state[key]` after widget renders → use two-step rerun pattern with pending/show flags
- **`st.rerun()`**: Use for two-step clear (e.g., search bar clear after search)
- **Pill selector**: Actual test ID is `stBaseButton-pills`, not `stPillsButton` or `stPills`

### Deployment
- **Git push**: Proxy at `localhost:3128` blocks HTTPS from VM — must push from local machine
- **Railway**: Auto-deploys on push to main
- **SEC EDGAR**: User-Agent header required: `"QuarterCharts contact@quartercharts.com"`

### Earnings Page
- Week starts Monday (not Sunday): `d.weekday()` where Monday=0
- Day buttons: format as "Mon 30", "Tue 31"
- Date label: "This Week: Mar 30 – Apr 05, 2026" in styled box
- Search clear: Two-step rerun using `_ec_pending_symbol` + `_ec_show_symbol`
- Results sorted: upcoming ascending, past descending by date

### Sankey Page
- Pill hover: JS-driven per-node color glow + Sankey highlight (not CSS-only)
- Click bridge: `_inject_sankey_click_js()` connects node clicks to pill buttons
- Hover bridge: `_inject_pill_hover_js()` connects pill hover to node highlighting
- CTA banner: gradient indigo background with pulse-chart SVG icon
- Compare badge: `sankey-compare-pill` class with dark gradient bg

---

## 5. Recent Changes (Changelog)

### 2026-04-02
- Pill hover: per-node color glow + Sankey node/link highlight on pill hover
- Sankey UI overhaul: shadow cards, spacing, CTA banner for metric instruction
- Header bar: vertically centered title and logo
- Pills: compact sizing (0.78rem, 4px 10px padding)

### 2026-04-01 (approx)
- Earnings page: full rebuild with Finnhub API (replaced Yahoo Finance)
- Week selector: Monday-first, styled arrow buttons, date range label
- Empty state: "No reports scheduled" with 🔕 icon
- Search bar: two-step rerun clear pattern
- Footer: Finnhub.io credit, "Built by Sebastián Flores + AI Team"
- All charts: disabled zoom/pan/box-select site-wide
- Sankey: centered tab selector, moved instruction text, added spacing
- Navbar: reduced padding to 14px
- Terms page: updated data sources to include Finnhub.io

---

## 6. Pending / Future Ideas

- [ ] Admin MD editor tab (in progress)
- [ ] User-facing AI chat for chart exploration
- [ ] Mobile responsive audit
- [ ] Cash flow Sankey diagram
- [ ] Comparison mode (two tickers side by side)
- [ ] Historical earnings accuracy tracking
- [ ] Dark mode toggle
