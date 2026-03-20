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

import yfinance as yf
import tornado.web
import tornado.ioloop

# In-memory cache: ticker -> {price, prev_close, timestamp}
_price_cache: dict = {}
_CACHE_TTL = 1.5  # seconds â keep cache short for near real-time feel

API_PORT = 8502


class PriceTornadoHandler(tornado.web.RequestHandler):
    """Handle GET /api/price/{TICKER} requests via Tornado."""

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Content-Type", "application/json")
        self.set_header("Cache-Control", "no-cache, no-store")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def get(self, ticker):
        data = _get_price(ticker.upper())
        self.write(json.dumps(data))

    def options(self, ticker):
        self.set_status(204)
        self.finish()

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
    """Inject /api/price/{ticker} into Streamlit's Tornado server (same port).

    Falls back to a standalone server on port 8502 if injection fails.
    """
    global _server_started
    with _lock:
        if _server_started:
            return
        _server_started = True

    def _inject():
        try:
            from streamlit.web.server.server import Server
            srv = Server.get_current()
            app = getattr(srv, '_app', None)
            if app is None:
                for name in dir(srv):
                    val = getattr(srv, name, None)
                    if isinstance(val, tornado.web.Application):
                        app = val
                        break
            if app is not None:
                rule = tornado.web.url(
                    r"/api/price/([\w.]+)", PriceTornadoHandler
                )
                # Insert into existing wildcard router rules at the front
                # so it takes priority over Streamlit's catch-all
                router = getattr(app, 'wildcard_router', None)
                if router and hasattr(router, 'rules'):
                    for group in router.rules:
                        target = getattr(group, 'target', None)
                        if target and hasattr(target, 'rules'):
                            target.rules.insert(0, rule)
                            print("[price_api] Injected /api/price/ into Streamlit router")
                            return
                # Fallback: try add_handlers (works if no catch-all)
                app.add_handlers(r".*", [
                    (r"/api/price/([\w.]+)", PriceTornadoHandler),
                ])
                print("[price_api] Injected /api/price/ via add_handlers")
                return
        except Exception as e:
            print(f"[price_api] Injection failed: {e}")
        _fallback()

    def _fallback():
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from urllib.parse import urlparse

        class FallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = urlparse(self.path).path.strip("/")
                parts = path.split("/")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.end_headers()
                ticker = parts[-1].upper() if parts else ""
                data = _get_price(ticker)
                self.wfile.write(json.dumps(data).encode())

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.end_headers()

            def log_message(self, fmt, *args):
                pass

        def _run():
            try:
                server = HTTPServer(("0.0.0.0", API_PORT), FallbackHandler)
                server.serve_forever()
            except OSError:
                pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        print(f"[price_api] Fallback server on port {API_PORT}")

    try:
        tornado.ioloop.IOLoop.current().call_later(2.0, _inject)
    except Exception:
        _fallback()
