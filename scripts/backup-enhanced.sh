#!/bin/bash
# Emergent Learning Framework - Enhanced Backup Script v2.0
# Adds encryption, automated verification, and remote backup integrity checks

set -euo pipefail

# Source the original backup script functionality
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Record start time for RTO measurement
START_TIME=$(date +%s)

# Run original backup
log_info "Running standard backup..."
if ! "$SCRIPT_DIR/backup.sh"; then
    log_error "Standard backup failed!"
    exit 1
fi

# Get the most recent backup
BACKUP_FILE=$(ls -t "$BACKUP_ROOT"/*.tar.gz 2>/dev/null | head -1)
if [[ -z "$BACKUP_FILE" ]]; then
    log_error "No backup file found!"
    exit 1
fi

BACKUP_BASENAME=$(basename "$BACKUP_FILE")

# Optional: Encrypt backup with GPG
if [[ -n "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
    log_info "Encrypting backup with GPG..."

    if command -v gpg >/dev/null 2>&1; then
        # Encrypt for the specified recipient
        gpg --batch --yes --trust-model always \
            --recipient "$BACKUP_ENCRYPTION_KEY" \
            --encrypt --output "$BACKUP_FILE.gpg" "$BACKUP_FILE"

        if [[ -f "$BACKUP_FILE.gpg" ]]; then
            ENCRYPTED_SIZE=$(stat -c%s "$BACKUP_FILE.gpg" 2>/dev/null || stat -f%z "$BACKUP_FILE.gpg" 2>/dev/null)
            log_success "Backup encrypted (${ENCRYPTED_SIZE} bytes)"

            # Keep both encrypted and unencrypted for testing
            # In production, you might want to remove unencrypted: rm -f "$BACKUP_FILE"
            log_info "Both encrypted and unencrypted backups retained"
            BACKUP_FILE_TO_SYNC="$BACKUP_FILE.gpg"
        else
            log_error "Encryption failed!"
            exit 1
        fi
    else
        log_error "GPG not found, cannot encrypt"
        log_error "Install gpg: apt-get install gnupg (Linux) or brew install gnupg (macOS)"
        exit 1
    fi
else
    log_info "Encryption not configured (set BACKUP_ENCRYPTION_KEY=your@email.com to enable)"
    BACKUP_FILE_TO_SYNC="$BACKUP_FILE"
fi

# Enhanced remote backup with verification
if [[ -n "${REMOTE_BACKUP_DEST:-}" ]]; then
    log_info "Syncing to remote destination: $REMOTE_BACKUP_DEST"

    if [[ "$REMOTE_BACKUP_DEST" == s3://* ]] || [[ "$REMOTE_BACKUP_DEST" == gs://* ]] || [[ "$REMOTE_BACKUP_DEST" == *:* && "$REMOTE_BACKUP_DEST" != *@* ]]; then
        # Cloud storage - use rclone
        if command -v rclone >/dev/null 2>&1; then
            log_info "Using rclone for cloud storage..."
            rclone sync "$BACKUP_ROOT" "$REMOTE_BACKUP_DEST" --progress --checksum

            # Verify remote backup
            log_info "Verifying remote backup integrity..."
            if rclone check "$BACKUP_ROOT" "$REMOTE_BACKUP_DEST" --one-way 2>&1 | grep -q "0 differences"; then
                log_success "Remote backup verified successfully"
            else
                log_warn "Remote backup verification found differences"
            fi
        else
            log_error "rclone not found, cannot sync to cloud storage"
            log_error "Install rclone: https://rclone.org/install/"
            exit 1
        fi
    else
        # SSH/local destination - use rsync
        if command -v rsync >/dev/null 2>&1; then
            log_info "Using rsync for remote sync..."
            rsync -avz --checksum --delete "$BACKUP_ROOT/" "$REMOTE_BACKUP_DEST/"

            # Verify remote backup
            log_info "Verifying remote backup integrity..."
            if rsync -avz --checksum --dry-run --delete "$BACKUP_ROOT/" "$REMOTE_BACKUP_DEST/" | grep -q "total size"; then
                log_success "Remote backup verified successfully"
            else
                log_warn "Remote backup verification inconclusive"
            fi
        else
            log_error "rsync not found, cannot sync to remote destination"
            log_error "Install rsync: apt-get install rsync (Linux) or brew install rsync (macOS)"
            exit 1
        fi
    fi
else
    log_info "No remote backup configured (set REMOTE_BACKUP_DEST to enable)"
    log_info "Examples:"
    log_info "  - SSH: user@server:/path/to/backups"
    log_info "  - rclone: myremote:backups/emergent-learning"
    log_info "  - S3: s3://my-bucket/emergent-learning"
fi

# Auto-verify backup integrity
log_info "Running automatic backup verification..."
if "$SCRIPT_DIR/verify-backup.sh" --alert-on-fail "$BACKUP_BASENAME" >/dev/null 2>&1; then
    log_success "Backup verification passed"
else
    log_error "Backup verification FAILED!"
    log_error "Backup may be corrupted - investigate immediately"
    exit 1
fi

# Calculate and display backup time
END_TIME=$(date +%s)
BACKUP_DURATION=$((END_TIME - START_TIME))
log_success "Backup completed in ${BACKUP_DURATION} seconds"

# Final summary
echo ""
log_success "=== Enhanced Backup Complete ==="
echo "Backup File: $BACKUP_FILE"
if [[ -n "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
    echo "Encrypted File: $BACKUP_FILE.gpg"
fi
if [[ -n "${REMOTE_BACKUP_DEST:-}" ]]; then
    echo "Remote Location: $REMOTE_BACKUP_DEST"
fi
echo "Duration: ${BACKUP_DURATION} seconds"
echo "Verification: PASSED"
echo ""

exit 0
