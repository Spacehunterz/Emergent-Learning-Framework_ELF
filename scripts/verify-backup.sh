#!/bin/bash
# Emergent Learning Framework - Backup Verification Script
# Automated backup testing and integrity verification

set -euo pipefail

# Configuration
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
Usage: $0 [OPTIONS] [backup-timestamp]

Verify backup integrity and test restoration capability.

Arguments:
  [backup-timestamp]   Optional: Specific backup to verify
                       If omitted, verifies all backups
                       Use 'latest' to verify most recent backup

Options:
  --full-test          Perform full restore test (more thorough but slower)
  --alert-on-fail      Exit with error code if any backup fails
  --email <address>    Send email alert on failure (requires mail command)
  --help               Show this help message

Verification Levels:
  1. Basic: Check file exists and is readable
  2. Integrity: Verify checksums and archive integrity
  3. Content: Extract and verify database files
  4. Full Test: Actual restore to temporary location

Examples:
  $0                           # Verify all backups (basic)
  $0 latest                    # Verify latest backup
  $0 --full-test latest        # Full restoration test of latest
  $0 --alert-on-fail           # Verify all, exit with error if any fail

EOF
    exit 1
}

# Parse options
FULL_TEST=false
ALERT_ON_FAIL=false
EMAIL_ALERT=""
BACKUP_TIMESTAMP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --full-test)
            FULL_TEST=true
            shift
            ;;
        --alert-on-fail)
            ALERT_ON_FAIL=true
            shift
            ;;
        --email)
            EMAIL_ALERT="$2"
            shift 2
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

# Find backups to verify
BACKUPS_TO_VERIFY=()

if [[ -z "$BACKUP_TIMESTAMP" ]]; then
    # Verify all backups
    for backup in "$BACKUP_ROOT"/*.tar.gz; do
        if [[ -f "$backup" ]]; then
            BACKUPS_TO_VERIFY+=("$backup")
        fi
    done
elif [[ "$BACKUP_TIMESTAMP" == "latest" ]]; then
    latest=$(ls -t "$BACKUP_ROOT"/*.tar.gz 2>/dev/null | head -1 || echo "")
    if [[ -n "$latest" ]]; then
        BACKUPS_TO_VERIFY+=("$latest")
    fi
else
    backup_file="$BACKUP_ROOT/${BACKUP_TIMESTAMP}.tar.gz"
    if [[ -f "$backup_file" ]]; then
        BACKUPS_TO_VERIFY+=("$backup_file")
    else
        log_error "Backup not found: $backup_file"
        exit 1
    fi
fi

if [[ ${#BACKUPS_TO_VERIFY[@]} -eq 0 ]]; then
    log_error "No backups found to verify"
    exit 1
fi

log_info "Found ${#BACKUPS_TO_VERIFY[@]} backup(s) to verify"
echo ""

# Verification results
TOTAL_BACKUPS=0
PASSED_BACKUPS=0
FAILED_BACKUPS=0
FAILED_BACKUP_NAMES=()

# Verify each backup
for backup_file in "${BACKUPS_TO_VERIFY[@]}"; do
    ((TOTAL_BACKUPS++))

    backup_name=$(basename "$backup_file" .tar.gz)
    backup_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo "unknown")
    backup_size_mb=$(echo "scale=2; $backup_size / 1024 / 1024" | bc 2>/dev/null || echo "unknown")

    echo "============================================"
    log_info "Verifying: $backup_name (${backup_size_mb}MB)"
    echo "============================================"

    BACKUP_FAILED=false

    # Level 1: File existence and readability
    log_info "Level 1: File existence check"
    if [[ ! -r "$backup_file" ]]; then
        log_error "Backup file not readable"
        BACKUP_FAILED=true
    else
        log_success "File readable"
    fi

    # Level 2: Archive integrity
    log_info "Level 2: Archive integrity check"
    if tar -tzf "$backup_file" >/dev/null 2>&1; then
        log_success "Archive integrity verified"
    else
        log_error "Archive is corrupted or incomplete"
        BACKUP_FAILED=true
    fi

    # Level 3: Extract and verify contents
    if [[ "$BACKUP_FAILED" == false ]]; then
        log_info "Level 3: Content verification"

        TEMP_DIR=$(mktemp -d)
        trap "rm -rf $TEMP_DIR" EXIT

        if tar -xzf "$backup_file" -C "$TEMP_DIR" 2>/dev/null; then
            EXTRACT_DIR="$TEMP_DIR/$backup_name"

            # Check for essential files
            ESSENTIAL_FILES=(
                "backup_metadata.txt"
            )

            for file in "${ESSENTIAL_FILES[@]}"; do
                if [[ ! -f "$EXTRACT_DIR/$file" ]]; then
                    log_warn "Missing file: $file"
                fi
            done

            # Check for at least one database file
            if [[ -f "$EXTRACT_DIR/index.db" ]] || [[ -f "$EXTRACT_DIR/index.sql" ]]; then
                log_success "Database files present"
            else
                log_error "No database files found in backup"
                BACKUP_FAILED=true
            fi

            # Verify checksums if present
            if [[ -f "$EXTRACT_DIR/checksums.md5" ]]; then
                log_info "Verifying checksums..."
                cd "$EXTRACT_DIR"
                if command -v md5sum >/dev/null 2>&1; then
                    if md5sum -c checksums.md5 >/dev/null 2>&1; then
                        log_success "Checksum verification passed"
                    else
                        log_error "Checksum verification failed"
                        BACKUP_FAILED=true
                    fi
                elif command -v md5 >/dev/null 2>&1; then
                    log_warn "Using macOS md5, limited verification"
                fi
            else
                log_warn "No checksums available"
            fi

            # Verify database integrity if SQLite is available
            if command -v sqlite3 >/dev/null 2>&1; then
                if [[ -f "$EXTRACT_DIR/index.db" ]]; then
                    log_info "Checking index.db integrity..."
                    if sqlite3 "$EXTRACT_DIR/index.db" "PRAGMA integrity_check;" | grep -q "ok"; then
                        log_success "index.db integrity verified"
                    else
                        log_error "index.db integrity check failed"
                        BACKUP_FAILED=true
                    fi
                fi

                if [[ -f "$EXTRACT_DIR/vectors.db" ]]; then
                    log_info "Checking vectors.db integrity..."
                    if sqlite3 "$EXTRACT_DIR/vectors.db" "PRAGMA integrity_check;" | grep -q "ok"; then
                        log_success "vectors.db integrity verified"
                    else
                        log_error "vectors.db integrity check failed"
                        BACKUP_FAILED=true
                    fi
                fi
            fi

            log_success "Content verification complete"
        else
            log_error "Failed to extract backup"
            BACKUP_FAILED=true
        fi

        rm -rf "$TEMP_DIR"
    fi

    # Level 4: Full restoration test (if requested)
    if [[ "$FULL_TEST" == true ]] && [[ "$BACKUP_FAILED" == false ]]; then
        log_info "Level 4: Full restoration test"

        TEST_DIR=$(mktemp -d)
        export FRAMEWORK_DIR="$TEST_DIR/emergent-learning"

        log_info "Testing restore to: $TEST_DIR"

        # Create mock framework structure
        mkdir -p "$FRAMEWORK_DIR/memory"
        git -C "$FRAMEWORK_DIR" init >/dev/null 2>&1 || true

        # Attempt restoration
        RESTORE_SCRIPT="$(dirname "$0")/restore.sh"
        if [[ -f "$RESTORE_SCRIPT" ]]; then
            if "$RESTORE_SCRIPT" --force --no-backup "$backup_name" >/dev/null 2>&1; then
                log_success "Full restoration test passed"
            else
                log_error "Full restoration test failed"
                BACKUP_FAILED=true
            fi
        else
            log_warn "restore.sh not found, skipping full test"
        fi

        rm -rf "$TEST_DIR"
        unset FRAMEWORK_DIR
    fi

    # Record results
    echo ""
    if [[ "$BACKUP_FAILED" == false ]]; then
        log_success "Backup verification PASSED: $backup_name"
        ((PASSED_BACKUPS++))
    else
        log_error "Backup verification FAILED: $backup_name"
        ((FAILED_BACKUPS++))
        FAILED_BACKUP_NAMES+=("$backup_name")
    fi
    echo ""
done

# Final summary
echo "============================================"
echo "Verification Summary"
echo "============================================"
echo "Total Backups: $TOTAL_BACKUPS"
echo "Passed: $PASSED_BACKUPS"
echo "Failed: $FAILED_BACKUPS"

if [[ $FAILED_BACKUPS -gt 0 ]]; then
    echo ""
    log_error "Failed backups:"
    for failed in "${FAILED_BACKUP_NAMES[@]}"; do
        echo "  - $failed"
    done
fi

echo ""

# Send alert if configured
if [[ $FAILED_BACKUPS -gt 0 ]] && [[ -n "$EMAIL_ALERT" ]]; then
    if command -v mail >/dev/null 2>&1; then
        log_info "Sending email alert to: $EMAIL_ALERT"
        {
            echo "Emergent Learning Framework Backup Verification Failed"
            echo ""
            echo "Date: $(date)"
            echo "Failed Backups: $FAILED_BACKUPS / $TOTAL_BACKUPS"
            echo ""
            echo "Failed backup(s):"
            for failed in "${FAILED_BACKUP_NAMES[@]}"; do
                echo "  - $failed"
            done
        } | mail -s "Backup Verification FAILED - Action Required" "$EMAIL_ALERT"
        log_success "Alert email sent"
    else
        log_warn "mail command not found, cannot send email alert"
    fi
fi

# Exit with appropriate code
if [[ $FAILED_BACKUPS -gt 0 ]]; then
    if [[ "$ALERT_ON_FAIL" == true ]]; then
        log_error "Exiting with error code due to failed backups"
        exit 1
    else
        log_warn "Some backups failed verification"
        exit 0
    fi
else
    log_success "All backups verified successfully"
    exit 0
fi
