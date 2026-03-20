"""
Lightweight HTTP price API for real-time price polling.

Runs as a daemon thread on port 8502 alongside Streamlit (port 8501).
Provides /price/{TICKER} endpoint returning JSON with live price data.
Uses yfinance fast_info for minimal latency.
"""

import json
import threading
import time
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import yfinance as yf

# In-memory cache: ticker -> {price, prev_close, timestamp}
_price_cache: dict = {}
_CACHE_TTL = 1.5  # seconds â keep cache short for near real-time feel

API_PORT = 8502


class PriceHandler(BaseHTTPRequestHandler):
    """Handle GET /price/{TICKER} requests."""

    def do_GET(self):
        path = urlparse(self.path).path.strip("/")
        parts = path.split("/")

        # CORS headers for cross-origin iframe requests
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()

        if len(parts) == 2 and parts[0] == "price":
            ticker = parts[1].upper()
            data = _get_price(ticker)
            self.wfile.write(json.dumps(data).encode())
        else:
            self.wfile.write(json.dumps({"error": "Use /price/{TICKER}"}).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress request logging to keep console clean."""
        pass


def _get_price(ticker: str) -> dict:
    """Get live price with short cache to avoid hammering yfinance."""
    now = time.time()
    cached = _price_cache.get(ticker)
    if cached and (now - cached["timestamp"]) < _CACHE_TTL:
        return cached["data"]

    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        price = float(fi.last_price) if fi.last_price else 0
        prev_close = float(fi.previous_close) if fi.previous_close else price

        # Extended market data
        info = t.info
        market_state = info.get("marketState", "CLOSED")
        reg_mkt_time = info.get("regularMarketTime")
        close_time_str = ""
        if reg_mkt_time:
            try:
                tz_name = info.get("exchangeTimezoneName", "US/Eastern")
                import pytz
                tz = pytz.timezone(tz_name)
                dt = datetime.datetime.fromtimestamp(reg_mkt_time, tz=tz)
                close_time_str = dt.strftime("%B %d at %I:%M:%S %p %Z")
            except Exception:
                close_time_str = ""

        # After-hours / pre-market prices
        post_price = info.get("postMarketPrice")
        post_change = info.get("postMarketChange")
        post_change_pct = info.get("postMarketChangePercent")
        post_time = info.get("postMarketTime")
        pre_price = info.get("preMarketPrice")
        pre_change = info.get("preMarketChange")
        pre_change_pct = info.get("preMarketChangePercent")
        pre_time = info.get("preMarketTime")

        ext_label = ""
        ext_price = None
        ext_change = None
        ext_change_pct = None
        ext_time_str = ""
        if market_state in ("POST", "POSTPOST") and post_price:
            ext_label = "After hours"
            ext_price = round(float(post_price), 2)
            ext_change = round(float(post_change), 2) if post_change else 0
            ext_change_pct = round(float(post_change_pct) * 100, 2) if post_change_pct else 0
            if post_time:
                try:
                    dt2 = datetime.datetime.fromtimestamp(post_time, tz)
                    ext_time_str = dt2.strftime("%I:%M:%S %p %Z")
                except Exception:
                    pass
        elif market_state in ("PRE", "PREPRE") and pre_price:
            ext_label = "Pre-market"
            ext_price = round(float(pre_price), 2)
            ext_change = round(float(pre_change), 2) if pre_change else 0
            ext_change_pct = round(float(pre_change_pct) * 100, 2) if pre_change_pct else 0
            if pre_time:
                try:
                    dt2 = datetime.datetime.fromtimestamp(pre_time, tz)
                    ext_time_str = dt2.strftime("%I:%M:%S %p %Z")
                except Exception:
                    pass

        data = {
            "price": round(price, 2),
            "prev_close": round(prev_close, 2),
            "change": round(price - prev_close, 2),
            "change_pct": round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0,
            "ticker": ticker,
            "ok": True,
            "market_state": market_state,
            "close_time": close_time_str,
            "ext_label": ext_label,
            "ext_price": ext_price,
            "ext_change": ext_change,
            "ext_change_pct": ext_change_pct,
            "ext_time": ext_time_str,
        }
    except Exception as e:
        data = {"ok": False, "error": str(e), "ticker": ticker}

    _price_cache[ticker] = {"data": data, "timestamp": now}
    return data


_server_started = False
_lock = threading.Lock()


def ensure_running():
    """Start the price API server if not already running (idempotent)."""
    global _server_started
    with _lock:
        if _server_started:
            return
        _server_started = True

    def _run():
        try:
            server = HTTPServer(("127.0.0.1", API_PORT), PriceHandler)
            server.serve_forever()
        except OSError:
            # Port already in use (another Streamlit worker) â that's fine
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
