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
else
    echo "WARNING: Could not find Streamlit index.html at $STREAMLIT_INDEX"
fi

# Start Streamlit
exec streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0
