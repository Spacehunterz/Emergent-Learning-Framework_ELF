#!/bin/bash
# Start a new experiment in the Emergent Learning Framework
#
# Usage (interactive): ./start-experiment.sh
# Usage (non-interactive):
#   EXPERIMENT_NAME="name" EXPERIMENT_HYPOTHESIS="hypothesis" ./start-experiment.sh
#   Or: ./start-experiment.sh --name "name" --hypothesis "hypothesis"
#   Optional: --success-criteria "criteria" --failure-criteria "criteria"
#
# Exit codes:
#   0 - Success
#   1 - Input validation error
#   2 - Database error
#   3 - Git error
#   4 - Filesystem error
#   5 - Missing dependency
#   8 - Lock acquisition error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
EXPERIMENTS_DIR="$BASE_DIR/experiments/active"
LOGS_DIR="$BASE_DIR/logs"
SCRIPT_NAME="start-experiment"

# Setup logging before loading library
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
if ! mkdir -p "$LOGS_DIR" 2>/dev/null; then
    echo "ERROR: Cannot create logs directory: $LOGS_DIR" >&2
    exit 4
fi

# Load error handling library

# ========================================
# OBSERVABILITY INTEGRATION
# ========================================

# Source observability libraries
if [ -f "$SCRIPT_DIR/lib/logging.sh" ]; then
    source "$SCRIPT_DIR/lib/logging.sh"
    source "$SCRIPT_DIR/lib/metrics.sh" 2>/dev/null || true
    source "$SCRIPT_DIR/lib/alerts.sh" 2>/dev/null || true

    # Initialize observability
    log_init "start-experiment" "$LOGS_DIR"
    metrics_init "$DB_PATH" 2>/dev/null || true
    alerts_init "$BASE_DIR" 2>/dev/null || true

    # Generate correlation ID for this execution
    CORRELATION_ID=$(log_get_correlation_id)
    export CORRELATION_ID

    log_info "Script started" user="$(whoami)" correlation_id="$CORRELATION_ID"

    # Start performance tracking
    log_timer_start "start-experiment_total"
    OPERATION_START=$(metrics_operation_start "start-experiment" 2>/dev/null || echo "")
else
    # Fallback if libraries not found
    CORRELATION_ID="${script_name}_$(date +%s)_$$"
    OPERATION_START=""
fi

# ========================================

LIB_DIR="$SCRIPT_DIR/lib"
if [ ! -f "$LIB_DIR/error-handling.sh" ]; then
    echo "FATAL: Error handling library not found: $LIB_DIR/error-handling.sh" >&2
    exit 5
fi
source "$LIB_DIR/error-handling.sh"

# Setup error trap
setup_error_trap

log_info "Script started"

# ============================================
# Rollback on failure
# ============================================
CREATED_DIR=""
CREATED_DB_ID=""

cleanup_on_failure() {
    if [ -n "$CREATED_DIR" ] && [ -d "$CREATED_DIR" ]; then
        log_warn "Rolling back: removing directory $CREATED_DIR"
        rm -rf "$CREATED_DIR" 2>/dev/null || log_error "Failed to remove directory during rollback: $CREATED_DIR"
    fi

    if [ -n "$CREATED_DB_ID" ] && [ "$CREATED_DB_ID" != "0" ] && [ "$CREATED_DB_ID" != "" ]; then
        log_warn "Rolling back: removing DB record $CREATED_DB_ID"
        sqlite3 "$DB_PATH" "DELETE FROM experiments WHERE id=$CREATED_DB_ID" 2>/dev/null || \
            log_error "Failed to remove DB record during rollback: $CREATED_DB_ID"
    fi
}

register_cleanup cleanup_on_failure

# ============================================
# Pre-flight checks
# ============================================
preflight_check() {
    log_info "Starting pre-flight checks"

    # Check required commands
    require_command "sqlite3" "Install sqlite3: apt-get install sqlite3 or brew install sqlite"
    require_command "git" "Install git: apt-get install git or brew install git"

    # Check required files and directories
    require_file "$DB_PATH" "Database not found: $DB_PATH"

    # Database integrity check
    check_db_integrity "$DB_PATH"

    # Warn if not a git repository (non-fatal)
    if [ ! -d "$BASE_DIR/.git" ]; then
        log_warn "Not a git repository: $BASE_DIR"
        report_status "warning" "Not a git repository (commits will be skipped)"
    fi

    log_success "Pre-flight checks passed"
}

preflight_check

# Ensure experiments directory exists
safe_mkdir "$EXPERIMENTS_DIR" "Creating experiments directory"

# ============================================
# Parse arguments
# ============================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --name) name="$2"; shift 2 ;;
        --hypothesis) hypothesis="$2"; shift 2 ;;
        --success-criteria) success_criteria="$2"; shift 2 ;;
        --failure-criteria) failure_criteria="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check for environment variables
name="${name:-$EXPERIMENT_NAME}"
hypothesis="${hypothesis:-$EXPERIMENT_HYPOTHESIS}"
success_criteria="${success_criteria:-$EXPERIMENT_SUCCESS_CRITERIA}"
failure_criteria="${failure_criteria:-$EXPERIMENT_FAILURE_CRITERIA}"

# ============================================
# Interactive or non-interactive mode
# ============================================
if [ -n "$name" ] && [ -n "$hypothesis" ]; then
    # Non-interactive mode
    log_info "Running in non-interactive mode"

    # Validate required inputs
    validate_not_empty "$name" "experiment name"
    validate_not_empty "$hypothesis" "hypothesis"

    success_criteria="${success_criteria:-[Define success criteria]}"
    failure_criteria="${failure_criteria:-[Define failure criteria]}"

    echo "=== Start Experiment (non-interactive) ==="
else
    # Interactive mode
    log_info "Running in interactive mode"
    echo "=== Start Experiment ==="
    echo ""

    read -p "Experiment Name: " name
    validate_not_empty "$name" "experiment name"

    read -p "Hypothesis: " hypothesis
    validate_not_empty "$hypothesis" "hypothesis"

    read -p "Success Criteria: " success_criteria

    read -p "Failure Criteria: " failure_criteria
fi

log_info "Starting experiment: $name"

# ============================================
# Generate folder name and create directory
# ============================================
timestamp=$(date +%Y%m%d-%H%M%S)
folder_name=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
folder_path="$EXPERIMENTS_DIR/${timestamp}_${folder_name}"
relative_folder="experiments/active/${timestamp}_${folder_name}"

# Create experiment folder
safe_mkdir "$folder_path" "Creating experiment folder"
CREATED_DIR="$folder_path"

log_success "Created experiment directory: $folder_path"

# ============================================
# Create hypothesis.md
# ============================================
hypothesis_file="$folder_path/hypothesis.md"

if ! cat > "$hypothesis_file" <<EOF
# Experiment: $name

**Started**: $(date +%Y-%m-%d)
**Status**: Active

## Hypothesis

$hypothesis

## Success Criteria

$success_criteria

## Failure Criteria

$failure_criteria

## Variables

[What parameters are we varying?]

## Controls

[What are we keeping constant?]

## Methodology

[How will we conduct this experiment?]

## Expected Outcomes

[What do we expect to learn?]
EOF
then
    error_msg "$EXIT_FILESYSTEM_ERROR" \
        "Failed to create hypothesis file" \
        "Check write permissions for $folder_path" \
        "fatal"
    exit "$EXIT_FILESYSTEM_ERROR"
fi

report_status "success" "Created: hypothesis.md"
log_success "Created hypothesis file: $hypothesis_file"

# ============================================
# Create log.md
# ============================================
log_file="$folder_path/log.md"

if ! cat > "$log_file" <<EOF
# Experiment Log: $name

## Cycle 1

**Date**: $(date +%Y-%m-%d)
**Status**: Planned

### Try

[What did we attempt?]

### Break

[What did we observe? What broke?]

### Analysis

[What does this tell us?]

### Learning

[What heuristic or insight emerged?]

---

EOF
then
    error_msg "$EXIT_FILESYSTEM_ERROR" \
        "Failed to create log file" \
        "Check write permissions for $folder_path" \
        "fatal"
    exit "$EXIT_FILESYSTEM_ERROR"
fi

report_status "success" "Created: log.md"
log_success "Created log file: $log_file"

# ============================================
# Insert into database
# ============================================
name_escaped=$(escape_sql "$name")
hypothesis_escaped=$(escape_sql "$hypothesis")
relative_folder_escaped=$(escape_sql "$relative_folder")

experiment_id=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO experiments (name, hypothesis, status, folder_path)
VALUES (
    '$name_escaped',
    '$hypothesis_escaped',
    'active',
    '$relative_folder_escaped'
);
SELECT last_insert_rowid();
SQL
)

exit_code=$?
if [ $exit_code -ne 0 ]; then
    error_msg "$EXIT_DB_ERROR" \
        "Failed to insert experiment into database" \
        "Check database permissions and SQL syntax" \
        "fatal"
    exit "$EXIT_DB_ERROR"
fi

# Validate the returned ID
validate_db_id "$experiment_id" "experiment"

CREATED_DB_ID="$experiment_id"
report_status "success" "Database record created (ID: $experiment_id)"
log_success "Database record created (ID: $experiment_id)"

# ============================================
# Git commit with locking
# ============================================
if [ -d "$BASE_DIR/.git" ]; then
    LOCK_FILE="$BASE_DIR/.git/claude-lock"

    if ! acquire_git_lock "$LOCK_FILE" 30; then
        error_msg "$EXIT_LOCK_ERROR" \
            "Could not acquire git lock - experiment created but not committed" \
            "Manually commit changes or wait for lock to be released: $LOCK_FILE" \
            "transient"
        # Don't exit here - experiment is created, just not committed
        log_warn "Continuing without git commit"
    else
        # Add files to git
        safe_git_add "$folder_path" "Adding experiment directory"
        safe_git_add "$DB_PATH" "Adding database changes"

        # Commit
        commit_msg="experiment: Start '$name'"
        commit_desc="Hypothesis: $hypothesis"
        if safe_git_commit "$commit_msg" "$commit_desc"; then
            report_status "success" "Git commit created"
        else
            log_warn "Git commit skipped (no changes or commit failed)"
            report_status "warning" "Git commit skipped"
        fi

        release_git_lock "$LOCK_FILE"
    fi
else
    log_warn "Not a git repository. Skipping commit."
    report_status "warning" "Not a git repository (skipped commit)"
fi

# ============================================
# Success
# ============================================
log_success "Experiment started successfully: $name"
echo ""
echo "Experiment started successfully!"
echo "Folder: $folder_path"
echo "Edit hypothesis at: $hypothesis_file"
echo "Log cycles at: $log_file"
echo ""

exit "$EXIT_SUCCESS"
