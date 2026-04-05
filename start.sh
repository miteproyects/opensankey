#!/bin/bash
echo "[start.sh] pwd=$(pwd)"
echo "[start.sh] ls seo_patch.py:"
ls -la seo_patch.py 2>&1 || echo "[start.sh] seo_patch.py NOT FOUND"

# ── SEO: Patch Streamlit's index.html BEFORE Streamlit starts ────────────
# This ensures Streamlit reads the fully-patched file into memory on boot.
echo "[start.sh] Running seo_patch.py..."
python3 seo_patch.py 2>&1 || echo "[start.sh] seo_patch.py FAILED with $?"
echo "[start.sh] seo_patch.py done"

# ── Copy static SEO files into Streamlit's static dir ────────────────────
python3 -c "
import os, shutil, streamlit as st
static = os.path.join(os.path.dirname(st.__file__), 'static')
app_dir = os.path.dirname(os.path.abspath('app.py'))
for f in ('robots.txt', 'sitemap.xml', 'llms.txt', 'og-image.png', 'favicon.ico', 'favicon-48x48.png', 'favicon-192x192.png'):
    src = os.path.join(app_dir, f)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(static, f))
        print(f'[SEO] Copied {f} to static/', flush=True)
"

# ── Start Streamlit ──────────────────────────────────────────────────────
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0
