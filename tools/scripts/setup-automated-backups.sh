#!/bin/bash
# Emergent Learning Framework - Automated Backup Setup
# Configures cron jobs for automated backups and verification

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_DIR="$HOME/.claude/emergent-learning"
LOG_DIR="$HOME/.claude/backups/logs"

# Create log directory
mkdir -p "$LOG_DIR"

echo "================================================"
echo "Emergent Learning Framework - Backup Automation"
echo "================================================"
echo ""

# Check if we're on Windows (Git Bash/MSYS)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    log_warn "Windows detected - cron not available"
    log_info "Setting up Task Scheduler instead..."

    # Create a wrapper script for Windows Task Scheduler
    WRAPPER_SCRIPT="$FRAMEWORK_DIR/scripts/run-backup-windows.bat"
    cat > "$WRAPPER_SCRIPT" << 'EOF'
@echo off
REM Emergent Learning Framework - Windows Backup Wrapper
REM Run this script with Windows Task Scheduler

set LOGFILE=%USERPROFILE%\.claude\backups\logs\backup-%date:~-4,4%%date:~-10,2%%date:~-7,2%.log
bash "%USERPROFILE%\.claude\emergent-learning\scripts\backup.sh" >> "%LOGFILE%" 2>&1
EOF

    log_success "Created Windows wrapper script: $WRAPPER_SCRIPT"
    echo ""
    echo "To set up automated backups on Windows:"
    echo ""
    echo "1. Open Task Scheduler (taskschd.msc)"
    echo "2. Click 'Create Basic Task'"
    echo "3. Name: 'Emergent Learning Backup'"
    echo "4. Trigger: Daily at 2:00 AM"
    echo "5. Action: Start a program"
    echo "6. Program: $WRAPPER_SCRIPT"
    echo "7. Finish and test the task"
    echo ""
    echo "For weekly verification, create another task:"
    echo ""
    echo "Create: verify-backup-windows.bat"
    echo "Content: bash ~/.claude/emergent-learning/scripts/verify-backup.sh --alert-on-fail"
    echo "Schedule: Weekly on Sunday at 3:00 AM"
    echo ""
    exit 0
fi

# Check if cron is available (Linux/macOS)
if ! command -v crontab >/dev/null 2>&1; then
    log_error "crontab not found - cannot set up automated backups"
    log_info "Install cron or use systemd timers"
    exit 1
fi

# Display current crontab
log_info "Current crontab:"
crontab -l 2>/dev/null || echo "  (empty)"
echo ""

# Ask user for confirmation
log_warn "This will add backup jobs to your crontab"
read -p "Continue? (yes/no): " response
if [[ "$response" != "yes" ]]; then
    log_info "Setup cancelled"
    exit 0
fi

# Create temporary crontab file
TEMP_CRON=$(mktemp)
trap "rm -f $TEMP_CRON" EXIT

# Export current crontab
crontab -l 2>/dev/null > "$TEMP_CRON" || echo "" > "$TEMP_CRON"

# Remove any existing emergent-learning backup jobs
sed -i.bak '/emergent-learning.*backup/d' "$TEMP_CRON" 2>/dev/null || \
    sed -i '' '/emergent-learning.*backup/d' "$TEMP_CRON" 2>/dev/null || \
    grep -v 'emergent-learning.*backup' "$TEMP_CRON" > "${TEMP_CRON}.new" && mv "${TEMP_CRON}.new" "$TEMP_CRON"

# Add new backup jobs
cat >> "$TEMP_CRON" << EOF

# Emergent Learning Framework - Automated Backups
# Added by setup-automated-backups.sh on $(date)

# Daily backup at midnight (00:00)
0 0 * * * $FRAMEWORK_DIR/scripts/backup.sh >> $LOG_DIR/backup-daily.log 2>&1

# Weekly verification on Sunday at 3 AM
0 3 * * 0 $FRAMEWORK_DIR/scripts/verify-backup.sh --alert-on-fail >> $LOG_DIR/verify-weekly.log 2>&1

# Monthly archive on 1st at 1 AM (backup.sh already handles retention)
# This is just a marker - the daily backup on the 1st will be kept as monthly
# 0 1 1 * * $FRAMEWORK_DIR/scripts/backup.sh >> $LOG_DIR/backup-monthly.log 2>&1

EOF

# Install new crontab
crontab "$TEMP_CRON"

log_success "Automated backups configured successfully!"
echo ""
log_info "Schedule:"
echo "  - Daily backup: Midnight (00:00)"
echo "  - Weekly verification: Sunday 3:00 AM"
echo "  - Monthly archives: Automatic (1st of month)"
echo ""
log_info "Logs location: $LOG_DIR"
echo "  - backup-daily.log"
echo "  - verify-weekly.log"
echo ""
log_info "To view current schedule:"
echo "  crontab -l"
echo ""
log_info "To remove automated backups:"
echo "  crontab -e"
echo "  (then delete the Emergent Learning section)"
echo ""

# Create a monitoring script
MONITOR_SCRIPT="$FRAMEWORK_DIR/scripts/check-backup-health.sh"
cat > "$MONITOR_SCRIPT" << 'EOFMONITOR'
#!/bin/bash
# Check if backups are running successfully

BACKUP_ROOT="${BACKUP_ROOT:-$HOME/.claude/backups/emergent-learning}"
LOG_DIR="$HOME/.claude/backups/logs"

echo "Backup Health Check"
echo "==================="
echo ""

# Check if backup was created today
TODAY=$(date +%Y%m%d)
if ls "$BACKUP_ROOT/${TODAY}"*.tar.gz >/dev/null 2>&1; then
    echo "✓ Backup created today: $(ls -t "$BACKUP_ROOT/${TODAY}"*.tar.gz | head -1 | xargs basename)"
else
    echo "✗ WARNING: No backup found for today ($TODAY)"
fi

# Check recent backups
echo ""
echo "Recent backups:"
ls -lht "$BACKUP_ROOT"/*.tar.gz 2>/dev/null | head -5 || echo "  No backups found"

# Check log files
echo ""
echo "Recent log entries:"
if [[ -f "$LOG_DIR/backup-daily.log" ]]; then
    echo "--- Last backup log ---"
    tail -n 10 "$LOG_DIR/backup-daily.log"
else
    echo "No daily backup log found"
fi

echo ""
EOFMONITOR

chmod +x "$MONITOR_SCRIPT"
log_success "Created monitoring script: $MONITOR_SCRIPT"
echo ""
log_info "To check backup health:"
echo "  $MONITOR_SCRIPT"
echo ""

exit 0
