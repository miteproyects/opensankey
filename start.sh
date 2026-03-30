#!/bin/bash
# Inject Google site verification meta tag into Streamlit's index.html <head>
STREAMLIT_INDEX=$(python3 -c "import streamlit, os; print(os.path.join(os.path.dirname(streamlit.__file__), 'static', 'index.html'))")

if [ -f "$STREAMLIT_INDEX" ]; then
    # Only patch if not already patched
    if ! grep -q "google-site-verification" "$STREAMLIT_INDEX"; then
        sed -i 's|<head>|<head><meta name="google-site-verification" content="4yRIohYFN8d_gMq4yQUG3sF9n_tbeZqKEL4pp-SlK9A" />|' "$STREAMLIT_INDEX"
        echo "Patched Streamlit index.html with Google site verification meta tag"
    else
        echo "Streamlit index.html already has Google site verification meta tag"
    fi

    # Patch <title> to match OAuth app name
    if grep -q "<title>Streamlit</title>" "$STREAMLIT_INDEX"; then
        sed -i 's|<title>Streamlit</title>|<title>QuarterCharts — Financial Data Visualization</title>|' "$STREAMLIT_INDEX"
        echo "Patched Streamlit title to QuarterCharts"
    fi

    # Add meta description for Google verification crawlers
    if ! grep -q "meta name=\"description\"" "$STREAMLIT_INDEX"; then
        sed -i 's|</head>|<meta name="description" content="QuarterCharts is a financial data visualization platform that turns SEC filings into interactive Sankey diagrams, quarterly income charts, and company profiles." /></head>|' "$STREAMLIT_INDEX"
        echo "Added meta description"
    fi

    # Add noscript block with privacy link and app description for crawlers
    if ! grep -q "quartercharts-seo" "$STREAMLIT_INDEX"; then
        sed -i 's|<noscript>You need to enable JavaScript to run this app.</noscript>|<noscript><div id="quartercharts-seo"><h1>QuarterCharts</h1><p>QuarterCharts is a financial data visualization platform that turns SEC filings into interactive Sankey diagrams, quarterly income charts, and company profiles.</p><a href="https://quartercharts.com/?page=privacy">Privacy Policy</a> | <a href="https://quartercharts.com/?page=terms">Terms of Service</a></div>You need to enable JavaScript to run this app.</noscript>|' "$STREAMLIT_INDEX"
        echo "Added noscript SEO block with privacy link"
    fi
else
    echo "WARNING: Could not find Streamlit index.html at $STREAMLIT_INDEX"
fi

# Start Streamlit
exec streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0
