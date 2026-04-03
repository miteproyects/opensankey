#!/bin/sh
# Run once to install the pre-commit hook that writes BUILD_TS on every commit.
# Usage: ./setup-hooks.sh
HOOK=".git/hooks/pre-commit"
cat > "$HOOK" << 'HOOK_CONTENT'
#!/bin/sh
TZ='America/Guayaquil' date +"%M:%S" > "$(git rev-parse --show-toplevel)/BUILD_TS"
git add "$(git rev-parse --show-toplevel)/BUILD_TS"
HOOK_CONTENT
chmod +x "$HOOK"
echo "Pre-commit hook installed. BUILD_TS will auto-update on every commit."
