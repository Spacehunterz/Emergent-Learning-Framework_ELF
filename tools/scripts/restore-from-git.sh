#!/bin/bash
# Emergent Learning Framework - Git-Based Point-in-Time Recovery
# Restore framework to any git commit while preserving or restoring databases

set -euo pipefail

# Configuration
FRAMEWORK_DIR="$HOME/.claude/emergent-learning"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] <commit-ref>

Restore framework files to a specific git commit.

Arguments:
  <commit-ref>         Git commit reference (hash, tag, or branch)
                       Use 'list' to show recent commits
                       Use 'HEAD~N' to go back N commits

Options:
  --keep-databases     Don't restore databases, only git-tracked files
  --restore-databases  Also restore databases to the commit's version
  --force              Skip confirmation prompts
  --dry-run            Show what would be restored without actually doing it
  --help               Show this help message

Examples:
  $0 HEAD~5                      # Restore to 5 commits ago
  $0 abc1234                     # Restore to specific commit
  $0 --keep-databases HEAD~1     # Restore files only, keep current databases
  $0 --restore-databases abc1234 # Restore everything including databases
  $0 list                        # Show recent commits

Database Restoration:
  By default, databases are NOT restored (only git-tracked files).
  Use --restore-databases to also restore database state.

  WARNING: Database restoration requires that the databases were
  committed to git at that point in history. If they weren't, only
  git-tracked files will be restored.

EOF
    exit 1
}

# Parse options
KEEP_DATABASES=true
RESTORE_DATABASES=false
FORCE=false
DRY_RUN=false
COMMIT_REF=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-databases)
            KEEP_DATABASES=true
            RESTORE_DATABASES=false
            shift
            ;;
        --restore-databases)
            KEEP_DATABASES=false
            RESTORE_DATABASES=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            COMMIT_REF="$1"
            shift
            ;;
    esac
done

# Check if framework directory exists and is a git repo
if [[ ! -d "$FRAMEWORK_DIR" ]]; then
    log_error "Framework directory not found: $FRAMEWORK_DIR"
    exit 1
fi

if [[ ! -d "$FRAMEWORK_DIR/.git" ]]; then
    log_error "Not a git repository: $FRAMEWORK_DIR"
    exit 1
fi

cd "$FRAMEWORK_DIR"

# List commits if requested
if [[ "$COMMIT_REF" == "list" ]]; then
    echo "Recent commits (most recent first):"
    echo ""
    git log --oneline --decorate --graph -20
    echo ""
    log_info "Use commit hash or relative reference (e.g., HEAD~5)"
    exit 0
fi

# Validate commit reference
if [[ -z "$COMMIT_REF" ]]; then
    log_error "No commit reference provided"
    usage
fi

# Verify commit exists
if ! git rev-parse "$COMMIT_REF" >/dev/null 2>&1; then
    log_error "Invalid commit reference: $COMMIT_REF"
    log_info "Use '$0 list' to see available commits"
    exit 1
fi

# Get full commit hash
COMMIT_HASH=$(git rev-parse "$COMMIT_REF")
COMMIT_SHORT=$(git rev-parse --short "$COMMIT_REF")

# Get commit information
COMMIT_DATE=$(git show -s --format=%ci "$COMMIT_HASH")
COMMIT_AUTHOR=$(git show -s --format=%an "$COMMIT_HASH")
COMMIT_MESSAGE=$(git show -s --format=%s "$COMMIT_HASH")

# Display commit information
echo ""
log_info "=== Target Commit Information ==="
echo "Commit: $COMMIT_SHORT ($COMMIT_HASH)"
echo "Date: $COMMIT_DATE"
echo "Author: $COMMIT_AUTHOR"
echo "Message: $COMMIT_MESSAGE"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    log_warn "You have uncommitted changes!"
    git status --short
    echo ""

    if [[ "$FORCE" != true ]]; then
        read -p "Continue anyway? This will stash your changes. (yes/no): " response
        if [[ "$response" != "yes" ]]; then
            log_info "Restore cancelled"
            exit 0
        fi
    fi

    # Stash changes
    log_info "Stashing uncommitted changes..."
    STASH_NAME="pre-restore-$(date +%Y%m%d_%H%M%S)"
    git stash push -m "$STASH_NAME"
    log_success "Changes stashed as: $STASH_NAME"
    echo "Restore with: git stash pop"
fi

# Backup current databases if not restoring them
DB_BACKUP_DIR=""
if [[ "$KEEP_DATABASES" == true ]]; then
    DB_BACKUP_DIR=$(mktemp -d)
    log_info "Backing up current databases to: $DB_BACKUP_DIR"

    if [[ -f "memory/index.db" ]]; then
        cp "memory/index.db" "$DB_BACKUP_DIR/index.db"
    fi
    if [[ -f "memory/vectors.db" ]]; then
        cp "memory/vectors.db" "$DB_BACKUP_DIR/vectors.db"
    fi
    log_success "Databases backed up"
fi

# Show what will be restored
log_info "Files that will be changed:"
git diff --name-status HEAD "$COMMIT_HASH" | head -20
echo ""

# Confirm unless --force or --dry-run
if [[ "$FORCE" != true ]] && [[ "$DRY_RUN" != true ]]; then
    read -p "Restore framework to commit $COMMIT_SHORT? (yes/no): " response
    if [[ "$response" != "yes" ]]; then
        log_info "Restore cancelled"

        # Restore databases if we backed them up
        if [[ -n "$DB_BACKUP_DIR" ]]; then
            rm -rf "$DB_BACKUP_DIR"
        fi

        exit 0
    fi
fi

# Dry run - show what would happen
if [[ "$DRY_RUN" == true ]]; then
    log_info "DRY RUN - No changes will be made"
    echo ""
    log_info "Would restore:"
    echo "  - Git-tracked files to: $COMMIT_SHORT"
    if [[ "$RESTORE_DATABASES" == true ]]; then
        echo "  - Databases to: $COMMIT_SHORT (if present in git history)"
    else
        echo "  - Databases: KEEP CURRENT (not restored)"
    fi
    exit 0
fi

# Perform restoration
log_info "Restoring framework to commit: $COMMIT_SHORT"

# Checkout the commit
git checkout "$COMMIT_HASH" .

log_success "Git files restored to commit: $COMMIT_SHORT"

# Restore databases if we backed them up
if [[ "$KEEP_DATABASES" == true ]] && [[ -n "$DB_BACKUP_DIR" ]]; then
    log_info "Restoring current databases..."

    if [[ -f "$DB_BACKUP_DIR/index.db" ]]; then
        cp "$DB_BACKUP_DIR/index.db" "memory/index.db"
    fi
    if [[ -f "$DB_BACKUP_DIR/vectors.db" ]]; then
        cp "$DB_BACKUP_DIR/vectors.db" "memory/vectors.db"
    fi

    rm -rf "$DB_BACKUP_DIR"
    log_success "Current databases preserved"
fi

# Verify restoration
log_info "Verifying restoration..."

CURRENT_COMMIT=$(git rev-parse HEAD)
if [[ "$CURRENT_COMMIT" == "$COMMIT_HASH" ]]; then
    log_warn "HEAD is now at commit: $COMMIT_SHORT (detached HEAD state)"
    log_info "To return to your branch, run: git checkout <branch-name>"
fi

# Check database integrity
if command -v sqlite3 >/dev/null 2>&1; then
    if [[ -f "memory/index.db" ]]; then
        if sqlite3 "memory/index.db" "PRAGMA integrity_check;" | grep -q "ok"; then
            log_success "index.db integrity verified"
        else
            log_error "index.db integrity check failed"
        fi
    fi

    if [[ -f "memory/vectors.db" ]]; then
        if sqlite3 "memory/vectors.db" "PRAGMA integrity_check;" | grep -q "ok"; then
            log_success "vectors.db integrity verified"
        else
            log_error "vectors.db integrity check failed"
        fi
    fi
fi

# Final summary
echo ""
log_success "=== Restore Complete ==="
echo "Restored To: $COMMIT_SHORT ($COMMIT_HASH)"
echo "Commit Date: $COMMIT_DATE"
echo "Message: $COMMIT_MESSAGE"
echo ""

if [[ "$KEEP_DATABASES" == true ]]; then
    log_info "Databases: CURRENT (not restored from git)"
else
    log_info "Databases: RESTORED from git history"
fi

echo ""
log_info "Next steps:"
echo "  1. Review the restored state"
echo "  2. To return to your branch: git checkout <branch-name>"
echo "  3. To restore stashed changes: git stash pop"
echo ""

exit 0
