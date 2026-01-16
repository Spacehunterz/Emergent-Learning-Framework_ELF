#!/bin/bash
#
# Install Ralph Loop pre-commit hook
#
# Usage:
#   bash tools/setup/install-ralph-hook.sh
#
# This installs the pre-commit hook that automatically runs Ralph loop
# on staged files before commits.
#

set -e

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
HOOK_SOURCE="$REPO_ROOT/tools/hooks/pre-commit"
HOOK_DEST="$REPO_ROOT/.git/hooks/pre-commit"

if [ ! -f "$HOOK_SOURCE" ]; then
    echo "✗ Hook source not found: $HOOK_SOURCE"
    exit 1
fi

if [ ! -d "$REPO_ROOT/.git/hooks" ]; then
    mkdir -p "$REPO_ROOT/.git/hooks"
fi

# Copy and make executable
cp "$HOOK_SOURCE" "$HOOK_DEST"
chmod +x "$HOOK_DEST"

echo "✓ Ralph Loop pre-commit hook installed"
echo ""
echo "How it works:"
echo "  1. When you run 'git commit', Ralph loop runs automatically"
echo "  2. Ralph reviews + simplifies staged code files"
echo "  3. If improvements are made, commit is blocked"
echo "  4. Stage the improvements: git add ."
echo "  5. Try committing again"
echo ""
echo "To skip Ralph:"
echo "  SKIP_RALPH_LOOP=1 git commit -m 'message'"
echo "  OR: git commit --no-verify"
echo ""
echo "To uninstall:"
echo "  rm .git/hooks/pre-commit"
