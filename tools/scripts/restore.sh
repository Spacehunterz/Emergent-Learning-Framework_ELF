#!/bin/bash
# Emergent Learning Framework - Restore Script
# Restores framework from backup with conflict detection and verification

set -euo pipefail

# Configuration
FRAMEWORK_DIR="$HOME/.claude/emergent-learning"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/.claude/backups/emergent-learning}"

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
Usage: $0 [OPTIONS] <backup-timestamp>

Restore Emergent Learning Framework from backup.

Arguments:
  <backup-timestamp>    Timestamp of backup to restore (format: YYYYMMDD_HHMMSS)
                        Use 'latest' to restore the most recent backup
                        Use 'list' to show available backups

Options:
  --sql-only           Restore only from SQL dumps (not binary databases)
  --verify-only        Verify backup without restoring
  --force              Skip confirmation prompts
  --no-backup          Don't create safety backup before restore
  --help               Show this help message

Examples:
  $0 20231201_120000              # Restore specific backup
  $0 latest                        # Restore latest backup
  $0 list                          # List available backups
  $0 --verify-only 20231201_120000 # Verify backup integrity
  $0 --force latest                # Restore without prompts

EOF
    exit 1
}

# Parse options
SQL_ONLY=false
VERIFY_ONLY=false
FORCE=false
NO_BACKUP=false
BACKUP_TIMESTAMP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --sql-only)
            SQL_ONLY=true
            shift
            ;;
        --verify-only)
            VERIFY_ONLY=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --no-backup)
            NO_BACKUP=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            BACKUP_TIMESTAMP="$1"
            shift
            ;;
    esac
done

# Check if backup root exists
if [[ ! -d "$BACKUP_ROOT" ]]; then
    log_error "Backup directory not found: $BACKUP_ROOT"
    exit 1
fi

# List backups if requested
if [[ "$BACKUP_TIMESTAMP" == "list" ]]; then
    echo "Available backups:"
    echo ""
    for backup in "$BACKUP_ROOT"/*.tar.gz; do
        if [[ ! -f "$backup" ]]; then
            log_warn "No backups found"
            exit 0
        fi
        filename=$(basename "$backup" .tar.gz)
        size=$(stat -f%z "$backup" 2>/dev/null || stat -c%s "$backup" 2>/dev/null || echo "unknown")
        size_mb=$(echo "scale=2; $size / 1024 / 1024" | bc)
        backup_date=$(date -d "${filename:0:8}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -j -f "%Y%m%d_%H%M%S" "$filename" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "unknown date")
        echo "  $filename - ${size_mb}MB - $backup_date"
    done
    exit 0
fi

# Find latest backup if requested
if [[ "$BACKUP_TIMESTAMP" == "latest" ]]; then
    latest=$(ls -t "$BACKUP_ROOT"/*.tar.gz 2>/dev/null | head -1 || echo "")
    if [[ -z "$latest" ]]; then
        log_error "No backups found"
        exit 1
    fi
    BACKUP_TIMESTAMP=$(basename "$latest" .tar.gz)
    log_info "Using latest backup: $BACKUP_TIMESTAMP"
fi

# Validate backup timestamp
if [[ -z "$BACKUP_TIMESTAMP" ]]; then
    log_error "No backup timestamp provided"
    usage
fi

BACKUP_FILE="$BACKUP_ROOT/${BACKUP_TIMESTAMP}.tar.gz"

if [[ ! -f "$BACKUP_FILE" ]]; then
    log_error "Backup not found: $BACKUP_FILE"
    log_info "Use '$0 list' to see available backups"
    exit 1
fi

# Extract to temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

log_info "Extracting backup: $BACKUP_FILE"
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
EXTRACT_DIR="$TEMP_DIR/$BACKUP_TIMESTAMP"

if [[ ! -d "$EXTRACT_DIR" ]]; then
    log_error "Backup extraction failed"
    exit 1
fi

log_success "Backup extracted to temporary directory"

# Display backup metadata
if [[ -f "$EXTRACT_DIR/backup_metadata.txt" ]]; then
    echo ""
    log_info "=== Backup Metadata ==="
    cat "$EXTRACT_DIR/backup_metadata.txt"
    echo ""
fi

# Verify checksums if available
if [[ -f "$EXTRACT_DIR/checksums.md5" ]]; then
    log_info "Verifying backup integrity..."
    cd "$EXTRACT_DIR"
    if command -v md5sum >/dev/null 2>&1; then
        if md5sum -c checksums.md5 >/dev/null 2>&1; then
            log_success "Checksum verification passed"
        else
            log_error "Checksum verification failed!"
            exit 1
        fi
    elif command -v md5 >/dev/null 2>&1; then
        # macOS md5 format is different, just check files exist
        log_warn "Using macOS md5, limited verification"
        if [[ -f "$EXTRACT_DIR/index.sql" ]] || [[ -f "$EXTRACT_DIR/index.db" ]]; then
            log_success "Backup files present"
        else
            log_error "Backup files missing!"
            exit 1
        fi
    fi
fi

# If verify-only mode, exit here
if [[ "$VERIFY_ONLY" == true ]]; then
    log_success "Backup verification complete - backup is valid"
    exit 0
fi

# Check for conflicts with existing data
CONFLICTS=false
if [[ -d "$FRAMEWORK_DIR" ]]; then
    log_warn "Framework directory already exists: $FRAMEWORK_DIR"

    # Check if there are uncommitted changes
    if [[ -d "$FRAMEWORK_DIR/.git" ]]; then
        cd "$FRAMEWORK_DIR"
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            log_warn "Uncommitted changes detected in framework directory"
            CONFLICTS=true
        fi
    fi

    # Check if databases exist
    if [[ -f "$FRAMEWORK_DIR/memory/index.db" ]] || [[ -f "$FRAMEWORK_DIR/memory/vectors.db" ]]; then
        log_warn "Existing databases found"
        CONFLICTS=true
    fi
fi

# Prompt for confirmation unless --force
if [[ "$FORCE" != true ]] && [[ "$CONFLICTS" == true ]]; then
    echo ""
    log_warn "This will overwrite existing data!"
    read -p "Continue with restore? (yes/no): " response
    if [[ "$response" != "yes" ]]; then
        log_info "Restore cancelled"
        exit 0
    fi
fi

# Create safety backup of existing data
if [[ "$NO_BACKUP" != true ]] && [[ -d "$FRAMEWORK_DIR" ]]; then
    SAFETY_BACKUP="$BACKUP_ROOT/pre-restore-$(date +%Y%m%d_%H%M%S).tar.gz"
    log_info "Creating safety backup of current state: $SAFETY_BACKUP"

    cd "$HOME/.claude"
    tar -czf "$SAFETY_BACKUP" emergent-learning/
    log_success "Safety backup created"
fi

# Perform restore
log_info "Starting restore operation..."

# Ensure framework directory exists
mkdir -p "$FRAMEWORK_DIR/memory"

# Restore databases
if [[ "$SQL_ONLY" == true ]]; then
    log_info "Restoring from SQL dumps only..."

    if [[ -f "$EXTRACT_DIR/index.sql" ]]; then
        log_info "  Restoring index.db from SQL dump"
        rm -f "$FRAMEWORK_DIR/memory/index.db"
        sqlite3 "$FRAMEWORK_DIR/memory/index.db" < "$EXTRACT_DIR/index.sql"
        log_success "  index.db restored"
    fi

    if [[ -f "$EXTRACT_DIR/vectors.sql" ]]; then
        log_info "  Restoring vectors.db from SQL dump"
        rm -f "$FRAMEWORK_DIR/memory/vectors.db"
        sqlite3 "$FRAMEWORK_DIR/memory/vectors.db" < "$EXTRACT_DIR/vectors.sql"
        log_success "  vectors.db restored"
    fi
else
    log_info "Restoring from binary databases..."

    if [[ -f "$EXTRACT_DIR/index.db" ]]; then
        log_info "  Restoring index.db"
        cp "$EXTRACT_DIR/index.db" "$FRAMEWORK_DIR/memory/index.db"
        log_success "  index.db restored"
    fi

    if [[ -f "$EXTRACT_DIR/vectors.db" ]]; then
        log_info "  Restoring vectors.db"
        cp "$EXTRACT_DIR/vectors.db" "$FRAMEWORK_DIR/memory/vectors.db"
        log_success "  vectors.db restored"
    fi
fi

# Restore git-tracked files
log_info "Restoring framework files..."

# Copy all files except databases (already restored)
rsync -av --exclude='memory/index.db' --exclude='memory/vectors.db' \
    --exclude='backup_metadata.txt' --exclude='checksums.md5' \
    "$EXTRACT_DIR/" "$FRAMEWORK_DIR/"

log_success "Framework files restored"

# Verify restoration
log_info "Verifying restoration..."

VERIFICATION_FAILED=false

if [[ ! -f "$FRAMEWORK_DIR/memory/index.db" ]]; then
    log_error "index.db not found after restore"
    VERIFICATION_FAILED=true
fi

if [[ ! -f "$FRAMEWORK_DIR/memory/vectors.db" ]]; then
    log_error "vectors.db not found after restore"
    VERIFICATION_FAILED=true
fi

# Test database integrity
if command -v sqlite3 >/dev/null 2>&1; then
    if ! sqlite3 "$FRAMEWORK_DIR/memory/index.db" "PRAGMA integrity_check;" | grep -q "ok"; then
        log_error "index.db integrity check failed"
        VERIFICATION_FAILED=true
    else
        log_success "index.db integrity verified"
    fi

    if ! sqlite3 "$FRAMEWORK_DIR/memory/vectors.db" "PRAGMA integrity_check;" | grep -q "ok"; then
        log_error "vectors.db integrity check failed"
        VERIFICATION_FAILED=true
    else
        log_success "vectors.db integrity verified"
    fi
fi

if [[ "$VERIFICATION_FAILED" == true ]]; then
    log_error "Restoration verification failed!"
    if [[ -f "$SAFETY_BACKUP" ]]; then
        log_info "Safety backup available at: $SAFETY_BACKUP"
    fi
    exit 1
fi

# Final summary
echo ""
log_success "=== Restore Complete ==="
echo "Restored From: $BACKUP_FILE"
echo "Framework Directory: $FRAMEWORK_DIR"
if [[ -f "$SAFETY_BACKUP" ]]; then
    echo "Safety Backup: $SAFETY_BACKUP"
fi
echo ""
log_info "Framework successfully restored from backup: $BACKUP_TIMESTAMP"
echo ""

exit 0
