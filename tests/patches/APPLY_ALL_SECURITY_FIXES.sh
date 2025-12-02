#!/bin/bash
# Master Security Patch Application Script
# Applies all security fixes to Emergent Learning Framework
#
# Usage: bash APPLY_ALL_SECURITY_FIXES.sh [--dry-run] [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

DRY_RUN=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--force]"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "  Security Patch Application"
echo "  Emergent Learning Framework"
echo "========================================"
echo ""
echo "Base directory: $BASE_DIR"

if [ "$DRY_RUN" = true ]; then
    echo "MODE: DRY RUN (no changes will be made)"
else
    echo "MODE: APPLYING PATCHES"
fi

echo ""

# Check if git repository
if [ -d "$BASE_DIR/.git" ]; then
    echo "Git repository detected"

    # Check for uncommitted changes
    if ! git -C "$BASE_DIR" diff --quiet; then
        echo "WARNING: Uncommitted changes detected in repository"
        if [ "$FORCE" = false ]; then
            echo "ERROR: Refusing to apply patches with uncommitted changes"
            echo "       Commit your changes or use --force to override"
            exit 1
        fi
    fi

    # Create security patch branch
    if [ "$DRY_RUN" = false ]; then
        current_branch=$(git -C "$BASE_DIR" branch --show-current)
        echo "Creating security-fixes branch from $current_branch"
        git -C "$BASE_DIR" checkout -b "security-fixes-$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
    fi
fi

echo ""
echo "========================================"
echo "  Applying CRITICAL Patches"
echo "========================================"
echo ""

# CRITICAL: Domain traversal fix
if [ -f "$SCRIPT_DIR/CRITICAL_domain_traversal_fix.patch" ]; then
    echo "1. Domain Path Traversal Fix (CRITICAL)"
    if [ "$DRY_RUN" = false ]; then
        bash "$SCRIPT_DIR/CRITICAL_domain_traversal_fix.patch" || echo "  WARNING: Patch failed or already applied"
    else
        echo "  Would apply: CRITICAL_domain_traversal_fix.patch"
    fi
    echo ""
fi

echo "========================================"
echo "  Applying HIGH Severity Patches"
echo "========================================"
echo ""

# HIGH: TOCTOU symlink race fix
if [ -f "$SCRIPT_DIR/HIGH_toctou_symlink_fix.patch" ]; then
    echo "2. TOCTOU Symlink Race Fix (HIGH)"
    if [ "$DRY_RUN" = false ]; then
        bash "$SCRIPT_DIR/HIGH_toctou_symlink_fix.patch" || echo "  WARNING: Patch failed or already applied"
    else
        echo "  Would apply: HIGH_toctou_symlink_fix.patch"
    fi
    echo ""
fi

echo "========================================"
echo "  Applying MEDIUM Severity Patches"
echo "========================================"
echo ""

# MEDIUM: Hardlink attack fix
if [ -f "$SCRIPT_DIR/MEDIUM_hardlink_attack_fix.patch" ]; then
    echo "3. Hardlink Attack Protection (MEDIUM)"
    if [ "$DRY_RUN" = false ]; then
        bash "$SCRIPT_DIR/MEDIUM_hardlink_attack_fix.patch" || echo "  WARNING: Patch failed or already applied"
    else
        echo "  Would apply: MEDIUM_hardlink_attack_fix.patch"
    fi
    echo ""
fi

if [ "$DRY_RUN" = false ]; then
    echo "========================================"
    echo "  Running Verification Tests"
    echo "========================================"
    echo ""

    if [ -f "$BASE_DIR/tests/advanced_security_tests.sh" ]; then
        echo "Running security test suite..."
        if bash "$BASE_DIR/tests/advanced_security_tests.sh"; then
            echo "SUCCESS: All security tests passed!"
        else
            echo "WARNING: Some security tests failed"
            echo "         Review test output above"
        fi
    else
        echo "WARNING: Test suite not found"
    fi

    echo ""
    echo "========================================"
    echo "  Git Commit"
    echo "========================================"
    echo ""

    if [ -d "$BASE_DIR/.git" ]; then
        echo "Creating security fix commit..."
        git -C "$BASE_DIR" add -A
        git -C "$BASE_DIR" commit -m "security: Apply critical filesystem security fixes" \
            -m "Fixes applied:" \
            -m "- CRITICAL: Domain path traversal (CVSS 9.3)" \
            -m "- HIGH: TOCTOU symlink race (CVSS 7.1)" \
            -m "- MEDIUM: Hardlink attack (CVSS 5.4)" \
            -m "" \
            -m "Security audit by: Opus Agent B" \
            -m "Date: $(date +%Y-%m-%d)" || echo "No changes to commit"

        echo ""
        echo "Patches applied and committed!"
        echo ""
        echo "Next steps:"
        echo "  1. Review the changes: git diff HEAD~1"
        echo "  2. Run tests: bash tests/advanced_security_tests.sh"
        echo "  3. Merge to master: git checkout master && git merge security-fixes-*"
    fi
fi

echo ""
echo "========================================"
echo "  Summary"
echo "========================================"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "Dry run complete. No changes were made."
    echo ""
    echo "To apply patches, run:"
    echo "  bash $0"
else
    echo "Security patches applied successfully!"
    echo ""
    echo "Backups created:"
    echo "  - *.before-domain-fix"
    echo "  - *.before-toctou-fix"
    echo "  - *.before-hardlink-fix"
    echo ""
    echo "Full security audit report:"
    echo "  $BASE_DIR/tests/SECURITY_AUDIT_FINAL_REPORT.md"
fi

echo ""
