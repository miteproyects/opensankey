#!/bin/bash
# ═══════════════════════════════════════════════════════════
# QuarterCharts — Local Development Server
# Double-click this file to start the app at localhost:8503
# (port 8501 is used by Los Barberos; 8503 is QuarterCharts local)
# ═══════════════════════════════════════════════════════════

PORT=8503

cd "$(dirname "$0")"

echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║   QuarterCharts.com — Local Server        ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "  ❌ Python 3 not found. Install it from python.org"
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

# Check Streamlit
if ! python3 -c "import streamlit" &>/dev/null; then
    echo "  📦 Installing dependencies..."
    pip3 install -r requirements.txt --break-system-packages -q
fi

# If the port is already in use, let the user know before streamlit fails noisily.
if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "  ⚠️  Port $PORT is already in use."
    echo "     Something else (maybe an old QuarterCharts process) is bound to it."
    echo "     Free it with:  lsof -iTCP:$PORT -sTCP:LISTEN -t | xargs kill"
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

echo "  🚀 Starting server..."
echo "  📍 Open: http://localhost:$PORT"
echo ""
echo "  Press Ctrl+C to stop"
echo "  ─────────────────────────────────────────────"
echo ""

# Run the same SEO patch step that start.sh does, so the local build matches prod.
python3 seo_patch.py 2>&1 || echo "  ⚠️  seo_patch.py failed (non-fatal)"

# Launch streamlit directly on $PORT. We do NOT call start.sh here because
# start.sh hardcodes --server.port=8501 for production (Railway/Procfile).
exec streamlit run app.py --server.port="$PORT" --server.address=0.0.0.0
