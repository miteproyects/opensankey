#!/bin/bash
# ═══════════════════════════════════════════════════════════
# QuarterCharts — Local Development Server
# Double-click this file to start the app at localhost:8501
# ═══════════════════════════════════════════════════════════

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

echo "  🚀 Starting server..."
echo "  📍 Open: http://localhost:8501"
echo ""
echo "  Press Ctrl+C to stop"
echo "  ─────────────────────────────────────────────"
echo ""

# Run the same start.sh used in production
bash start.sh
