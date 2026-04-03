#!/bin/sh
# Run once to install the pre-push hook that writes BUILD_TS on every push.
# Usage: ./setup-hooks.sh
# Remove old pre-commit hook if it exists
rm -f .git/hooks/pre-commit
HOOK=".git/hooks/pre-push"
cat > "$HOOK" << 'HOOK_CONTENT'
#!/bin/sh
ROOT="$(git rev-parse --show-toplevel)"
TZ='America/Guayaquil' date +"%M:%S" > "$ROOT/BUILD_TS"
cd "$ROOT"
git add BUILD_TS
git commit --amend --no-edit --no-verify --allow-empty
HOOK_CONTENT
chmod +x "$HOOK"
echo "Pre-push hook installed. BUILD_TS will auto-update on every git push."
