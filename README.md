# Open Sankey

A fully local, production-quality financial charting app. Built with **Streamlit**, **Plotly**, and **yfinance** — runs 100% on your Mac with no cloud hosting or paid APIs.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **Any ticker** — type any stock symbol (NVDA, AAPL, TSLA, etc.) and get instant financial charts
- **Quarterly & Annual** toggle for all financial statements
- **Timeframe selectors** — 1Y, 2Y, 4Y, MAX, or custom period range
- **Section toggles** — show/hide Income Statement, Cash Flow, Balance Sheet, Key Metrics
- **Interactive Plotly charts** — hover tooltips, zoom, pan, clickable legends
- **Analyst Forecast** section with price targets and recommendations
- **Light finance theme** with modern aesthetic
- **Share buttons** for copying links and social sharing
- **Key metrics dashboard** — Market Cap, P/E, PEG, margins, ratios
- **"More Info" panel** — detailed valuation & fundamental data
- **Multi-column layout** — switch between 1, 2, or 3 column chart views
- **Responsive design** — works on desktop and mobile
- **Data caching** — repeated views are instant (1-hour TTL)
- **Graceful error handling** — friendly messages for invalid tickers or network issues

## Charts Included

### Income Statement
1. Revenue, Gross Profit, Operating and Net Income (grouped bar)
2. Gross, Operating, and Net Profit Margin % (multi-line)
3. Earnings Per Share / EPS (line with fill)
4. Revenue YoY Variation % (line)
5. Operating Expenses — R&D + SGA (stacked bar)
6. EBITDA (bar)
7. Interest and Other Income (bar)
8. Income Tax Expense (bar)
9. Per Share Metrics (grouped bar)

### Cash Flow Statement
1. Cash Flows — Operating, Investing, Financing, Free CF (grouped bar)
2. Cash Position (bar)
3. Capital Expenditure (bar)

### Balance Sheet
1. Total Assets — Current + Non-Current (stacked bar)
2. Liabilities — Current + Non-Current (stacked bar)
3. Stockholders Equity vs Total Debt (grouped bar)

### Key Metrics
1. P/E Ratio over time (line)
2. Metric cards: Gross Margin, Operating Margin, ROE, ROA, D/E, Current Ratio, etc.

## Quick Start

### Prerequisites
- **Python 3.9+** (check: `python3 --version`)
- **pip** package manager

### Install & Run

```bash
# 1. Navigate to the project
cd ~/Desktop/OpenTF/open-sankey

# 2. (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run app.py
```

The app opens automatically at **http://localhost:8501**.

## Project Structure

```
open-sankey/
├── app.py              # Main Streamlit application (UI + layout)
├── data_fetcher.py     # Data fetching module (yfinance + caching)
├── charts.py           # Chart creation module (Plotly dark theme)
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Data Sources

- **Primary**: [Yahoo Finance](https://finance.yahoo.com) via the `yfinance` Python library
  - Company info, financial statements, balance sheets, cash flows, analyst data
  - Free, no API key required
  - Data updates in real-time during market hours

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| Charts | Plotly |
| Data | yfinance + pandas |
| Caching | `@st.cache_data(ttl=3600)` |
| Styling | Custom CSS (dark theme) |

## Customization

- **Change default ticker**: Edit `st.session_state.ticker` in `app.py`
- **Adjust cache TTL**: Change `ttl=3600` in `data_fetcher.py` decorators
- **Modify colors**: Edit the `COLORS` dict in `charts.py`
- **Add new charts**: Create a function in `charts.py`, add data mapping in `data_fetcher.py`, render in `app.py`

## License

MIT — use freely for personal or educational purposes.
