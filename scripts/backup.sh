#!/bin/bash
# Emergent Learning Framework - Backup Script
# Creates timestamped backups of databases and git-tracked files
# Supports local and remote backup destinations

set -euo pipefail

# Configuration
FRAMEWORK_DIR="$HOME/.claude/emergent-learning"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/.claude/backups/emergent-learning}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
RETENTION_DAILY=7
RETENTION_WEEKLY=4
RETENTION_MONTHLY=12

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

# Check if framework directory exists
if [[ ! -d "$FRAMEWORK_DIR" ]]; then
    log_error "Framework directory not found: $FRAMEWORK_DIR"
    exit 1
fi

# Create backup directory
log_info "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Change to framework directory
cd "$FRAMEWORK_DIR"

# 1. Export databases to SQL dumps
log_info "Exporting databases to SQL dumps..."

if [[ -f "memory/index.db" ]]; then
    log_info "  - Exporting index.db"
    sqlite3 memory/index.db .dump > "$BACKUP_DIR/index.sql"
    log_success "  - index.db exported ($(wc -l < "$BACKUP_DIR/index.sql") lines)"
else
    log_warn "  - index.db not found, skipping"
fi

if [[ -f "memory/vectors.db" ]]; then
    log_info "  - Exporting vectors.db"
    sqlite3 memory/vectors.db .dump > "$BACKUP_DIR/vectors.sql"
    log_success "  - vectors.db exported ($(wc -l < "$BACKUP_DIR/vectors.sql") lines)"
else
    log_warn "  - vectors.db not found, skipping"
fi

# 2. Copy binary databases (for binary-exact restoration if needed)
log_info "Copying binary database files..."
if [[ -f "memory/index.db" ]]; then
    cp memory/index.db "$BACKUP_DIR/index.db"
    log_success "  - index.db copied ($(stat -f%z "memory/index.db" 2>/dev/null || stat -c%s "memory/index.db" 2>/dev/null || echo "unknown") bytes)"
fi
if [[ -f "memory/vectors.db" ]]; then
    cp memory/vectors.db "$BACKUP_DIR/vectors.db"
    log_success "  - vectors.db copied ($(stat -f%z "memory/vectors.db" 2>/dev/null || stat -c%s "memory/vectors.db" 2>/dev/null || echo "unknown") bytes)"
fi

# 3. Export git-tracked files (excluding .git directory)
log_info "Creating git archive of tracked files..."
git archive --format=tar HEAD | tar -x -C "$BACKUP_DIR"
log_success "Git archive created"

# 4. Create metadata file
log_info "Creating backup metadata..."
cat > "$BACKUP_DIR/backup_metadata.txt" << EOF
Emergent Learning Framework Backup
===================================

Backup Date: $(date)
Backup Timestamp: $TIMESTAMP
Framework Directory: $FRAMEWORK_DIR
Git Commit: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
Git Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "N/A")

Database Export Sizes:
- index.sql: $(wc -l < "$BACKUP_DIR/index.sql" 2>/dev/null || echo "0") lines
- vectors.sql: $(wc -l < "$BACKUP_DIR/vectors.sql" 2>/dev/null || echo "0") lines

Binary Database Sizes:
- index.db: $(stat -f%z "$BACKUP_DIR/index.db" 2>/dev/null || stat -c%s "$BACKUP_DIR/index.db" 2>/dev/null || echo "N/A") bytes
- vectors.db: $(stat -f%z "$BACKUP_DIR/vectors.db" 2>/dev/null || stat -c%s "$BACKUP_DIR/vectors.db" 2>/dev/null || echo "N/A") bytes

Backup Created By: backup.sh v1.0
EOF
log_success "Metadata created"

# 5. Calculate checksums for integrity verification
log_info "Calculating checksums..."
if command -v md5sum >/dev/null 2>&1; then
    find "$BACKUP_DIR" -type f -exec md5sum {} \; > "$BACKUP_DIR/checksums.md5"
elif command -v md5 >/dev/null 2>&1; then
    find "$BACKUP_DIR" -type f -exec md5 {} \; > "$BACKUP_DIR/checksums.md5"
else
    log_warn "No md5 tool found, skipping checksums"
fi
log_success "Checksums calculated"

# 6. Compress backup
log_info "Compressing backup..."
cd "$BACKUP_ROOT"
tar -czf "${TIMESTAMP}.tar.gz" "$TIMESTAMP"
COMPRESSED_SIZE=$(stat -f%z "${TIMESTAMP}.tar.gz" 2>/dev/null || stat -c%s "${TIMESTAMP}.tar.gz" 2>/dev/null || echo "unknown")
log_success "Backup compressed: ${TIMESTAMP}.tar.gz ($COMPRESSED_SIZE bytes)"

# 7. Verify compressed backup
log_info "Verifying compressed backup..."
if tar -tzf "${TIMESTAMP}.tar.gz" >/dev/null 2>&1; then
    log_success "Backup integrity verified"
else
    log_error "Backup verification failed!"
    exit 1
fi

# 8. Remove uncompressed backup directory
log_info "Cleaning up uncompressed backup..."
rm -rf "$TIMESTAMP"
log_success "Cleanup complete"

# 9. Rotate old backups
log_info "Rotating old backups..."

# Helper function to get backup age in days
backup_age_days() {
    local backup_date=$1
    local current_date=$(date +%s)
    local backup_timestamp=$(date -d "${backup_date:0:8}" +%s 2>/dev/null || date -j -f "%Y%m%d" "${backup_date:0:8}" +%s 2>/dev/null)
    echo $(( (current_date - backup_timestamp) / 86400 ))
}

# Keep daily backups for last 7 days
# Keep weekly backups (Sunday) for last 4 weeks
# Keep monthly backups (1st of month) for last 12 months
# Delete everything else

if [[ -d "$BACKUP_ROOT" ]]; then
    for backup in "$BACKUP_ROOT"/*.tar.gz; do
        if [[ ! -f "$backup" ]]; then
            continue
        fi

        filename=$(basename "$backup" .tar.gz)
        backup_date=${filename:0:8}

        # Calculate age
        age=$(backup_age_days "$backup_date")

        # Extract day of week and day of month
        day_of_week=$(date -d "$backup_date" +%u 2>/dev/null || date -j -f "%Y%m%d" "$backup_date" +%u 2>/dev/null)
        day_of_month=$(date -d "$backup_date" +%d 2>/dev/null || date -j -f "%Y%m%d" "$backup_date" +%d 2>/dev/null)

        keep=false
        reason=""

        # Keep if less than 7 days old (daily)
        if [[ $age -lt $RETENTION_DAILY ]]; then
            keep=true
            reason="daily (${age}d old)"
        # Keep if Sunday and less than 28 days old (weekly)
        elif [[ $day_of_week -eq 7 ]] && [[ $age -lt $((RETENTION_WEEKLY * 7)) ]]; then
            keep=true
            reason="weekly (${age}d old)"
        # Keep if 1st of month and less than 365 days old (monthly)
        elif [[ $day_of_month -eq 01 ]] && [[ $age -lt $((RETENTION_MONTHLY * 30)) ]]; then
            keep=true
            reason="monthly (${age}d old)"
        fi

        if [[ "$keep" == true ]]; then
            log_info "  Keeping $filename ($reason)"
        else
            log_warn "  Deleting $filename (${age}d old)"
            rm -f "$backup"
        fi
    done
fi

log_success "Backup rotation complete"

# 10. Remote backup (if configured)
if [[ -n "${REMOTE_BACKUP_DEST:-}" ]]; then
    log_info "Syncing to remote destination: $REMOTE_BACKUP_DEST"

    if command -v rsync >/dev/null 2>&1; then
        rsync -avz --delete "$BACKUP_ROOT/" "$REMOTE_BACKUP_DEST/"
        log_success "Remote sync complete (rsync)"
    elif command -v rclone >/dev/null 2>&1; then
        rclone sync "$BACKUP_ROOT" "$REMOTE_BACKUP_DEST"
        log_success "Remote sync complete (rclone)"
    else
        log_warn "No rsync or rclone found, skipping remote backup"
        log_warn "Install rsync or rclone and set REMOTE_BACKUP_DEST to enable remote backups"
    fi
else
    log_info "No remote backup configured (set REMOTE_BACKUP_DEST to enable)"
fi

# Final summary
echo ""
log_success "=== Backup Complete ==="
echo "Backup Location: $BACKUP_ROOT/${TIMESTAMP}.tar.gz"
echo "Backup Size: $COMPRESSED_SIZE bytes"
echo "Retention Policy:"
echo "  - Daily backups: Last $RETENTION_DAILY days"
echo "  - Weekly backups: Last $RETENTION_WEEKLY weeks"
echo "  - Monthly backups: Last $RETENTION_MONTHLY months"
echo ""
log_info "To restore from this backup, run:"
echo "  ./scripts/restore.sh $TIMESTAMP"
echo ""

exit 0
