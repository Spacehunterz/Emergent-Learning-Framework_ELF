# Concurrency Analysis - Agent E Report

**Date**: 2025-12-01
**Agent**: Opus Agent E
**Focus**: Deep concurrency testing and atomic operations

## Executive Summary

Analyzed all code in the Emergent Learning Framework for race conditions, TOCTOU vulnerabilities, and concurrency issues. Found multiple critical issues that can cause data corruption, deadlocks, and lost updates under concurrent load.

---

## TOCTOU Vulnerabilities Found

### 1. **File Existence Check Before Write** (CRITICAL)
**Location**: `record-failure.sh` lines ~180-200, `record-heuristic.sh` lines ~190-210

**Vulnerability**:
```bash
if [ ! -f "$domain_file" ]; then
    cat > "$domain_file" <<EOF
# Header...
EOF
fi
cat >> "$domain_file" <<EOF
# Append content...
EOF
```

**Race Condition**:
- Process A checks file doesn't exist
- Process B checks file doesn't exist
- Process A creates file with header
- Process B creates file with header (OVERWRITES A's work)
- Both append, but B's header clobbered A's initial content

**Impact**: Data loss, corrupted markdown files

### 2. **Database Insert + File Write** (CRITICAL)
**Location**: All record scripts

**Vulnerability**:
- Insert into DB succeeds (gets ID)
- File write fails
- DB has orphaned record
- OR: File write succeeds, DB insert fails
- File has no DB record

**Current State**: Partial rollback exists in record-failure.sh but NOT atomic

### 3. **Git Lock + SQLite Lock Ordering** (DEADLOCK RISK)
**Location**: All commit operations

**Scenario**:
- Process A: Acquires SQLite lock → tries Git lock
- Process B: Acquires Git lock → tries SQLite lock
- **DEADLOCK**

**Current State**: Lock ordering is inconsistent - SQLite lock is acquired before Git lock

### 4. **Stale Lock Files** (AVAILABILITY)
**Location**: All scripts using `acquire_git_lock()`

**Issue**:
```bash
acquire_git_lock() {
    local lock_dir="${lock_file}.dir"
    while [ $wait_time -lt $timeout ]; do
        if mkdir "$lock_dir" 2>/dev/null; then
            return 0
        fi
        sleep 1
        ((wait_time++))
    done
    return 1
}
```

**Problem**: If process dies while holding lock (crash, kill -9, power loss):
- Lock directory remains
- All future operations hang for 30s then fail
- **System requires manual intervention**

### 5. **Non-Atomic File Operations**
**Location**: All markdown file writes

**Issue**:
```bash
cat > "$filepath" <<EOF
# Large content...
EOF
```

**Problem**:
- If process killed mid-write: CORRUPTED FILE
- If disk full mid-write: TRUNCATED FILE
- Readers can see partial content

**Solution**: Write to temp file, atomic rename

---

## SQLite Concurrency Issues

### 1. **No WAL Mode** (PERFORMANCE)
**Current**: Default rollback journal mode
**Impact**:
- Only ONE writer at a time
- Readers blocked during writes
- Poor concurrency performance

**Fix**: Enable WAL (Write-Ahead Logging)
```python
cursor.execute("PRAGMA journal_mode=WAL")
```

**Benefits**:
- Multiple readers during writes
- Better crash recovery
- Significant performance improvement

### 2. **No Busy Timeout** (RELIABILITY)
**Current**: query.py has NO busy timeout
**Impact**:
- Immediate "database locked" errors
- No automatic retry at SQLite level

**Fix**:
```python
cursor.execute("PRAGMA busy_timeout=10000")  # 10 seconds
```

### 3. **Shell Script Retry Logic** (IMPROVEMENT NEEDED)
**Current**:
```bash
sqlite_with_retry() {
    local max_attempts=5
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if sqlite3 "$@" 2>/dev/null; then
            return 0
        fi
        sleep 0.$((RANDOM % 5 + 1))  # 0.1-0.5 seconds
        ((attempt++))
    done
}
```

**Issues**:
- Linear backoff (too aggressive)
- Sleep is only 0.1-0.5s (too short)
- No jitter randomization

**Fix**: Exponential backoff with jitter
```bash
sleep_time=$(awk "BEGIN {print (2^$attempt * 0.1) + (rand() * 0.1)}")
```

---

## Lock Ordering Issues

### Current Behavior:
1. **record-failure.sh**: SQLite insert → Git lock → Git commit
2. **record-heuristic.sh**: SQLite insert → Git lock → Git commit
3. **sync-db-markdown.sh**: No Git lock, direct operations

### Deadlock Scenario:
```
Process A (record-failure):
  t0: Acquire SQLite lock
  t1: Try Git lock (blocked by B)

Process B (record-heuristic):
  t0: Acquire Git lock
  t1: Try SQLite lock (blocked by A)

Result: DEADLOCK
```

### Current Mitigation:
- SQLite operations use `sqlite_with_retry()` which releases and retries
- Git lock is acquired AFTER SQLite is released
- **Still vulnerable if operations overlap**

### Recommended Fix:
**Establish strict lock ordering**:
1. Always acquire Git lock FIRST
2. Then acquire SQLite lock
3. Release in reverse order

---

## Stale Lock Detection

### Current State: NONE

### Proposed Implementation:
```bash
detect_stale_lock() {
    local lock_dir="$1"
    local max_age_seconds="${2:-300}"  # 5 minutes default

    if [ -d "$lock_dir" ]; then
        local lock_age=$(( $(date +%s) - $(stat -c %Y "$lock_dir" 2>/dev/null || stat -f %m "$lock_dir") ))
        if [ "$lock_age" -gt "$max_age_seconds" ]; then
            log "WARN" "Stale lock detected: $lock_dir (age: ${lock_age}s)"
            # Check if lock owner process exists
            # If not, clean up
            return 0
        fi
    fi
    return 1
}

acquire_git_lock() {
    local lock_file="$1"
    local lock_dir="${lock_file}.dir"

    # Check for stale lock
    if detect_stale_lock "$lock_dir" 300; then
        log "INFO" "Cleaning stale lock: $lock_dir"
        rmdir "$lock_dir" 2>/dev/null || true
    fi

    # Then acquire normally...
}
```

---

## Atomic File Operations

### Current: NON-ATOMIC
```bash
cat > "$filepath" <<EOF
Content...
EOF
```

### Recommended: ATOMIC RENAME PATTERN
```bash
write_atomic() {
    local target_file="$1"
    local content="$2"
    local temp_file="${target_file}.tmp.$$"

    # Write to temp file
    echo "$content" > "$temp_file"

    # Sync to disk
    sync "$temp_file" 2>/dev/null || true

    # Atomic rename
    mv -f "$temp_file" "$target_file"
}
```

**Benefits**:
- Readers never see partial content
- Crash-safe: either old content or new content, never corrupt
- Works across all filesystems

---

## Performance Recommendations

### 1. SQLite Configuration
```python
# In query.py _init_database():
cursor.execute("PRAGMA journal_mode=WAL")
cursor.execute("PRAGMA busy_timeout=10000")
cursor.execute("PRAGMA synchronous=NORMAL")  # WAL mode safe
cursor.execute("PRAGMA cache_size=-64000")   # 64MB cache
cursor.execute("PRAGMA temp_store=MEMORY")
```

### 2. Retry Backoff
**Exponential with Jitter**:
```bash
attempt=1
while [ $attempt -le $max_attempts ]; do
    if operation; then
        return 0
    fi
    # Exponential: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s
    # Jitter: +/- 50%
    base_sleep=$(awk "BEGIN {print 0.1 * (2^($attempt-1))}")
    jitter=$(awk "BEGIN {print rand() * $base_sleep}")
    sleep_time=$(awk "BEGIN {print $base_sleep + $jitter}")
    sleep $sleep_time
    ((attempt++))
done
```

### 3. Lock Timeouts
**Current**: 30s (too long)
**Recommended**:
- Git lock: 10s (operations are fast)
- SQLite busy_timeout: 10s (automatic)
- Script retry: 5 attempts with exponential backoff

---

## Test Strategy

### Concurrent Operations Test:
1. Spawn 20 parallel processes
2. Each records failure/heuristic
3. Verify:
   - No data loss
   - No deadlocks
   - All DB records match files
   - No corrupted markdown

### Stress Test:
1. 50 concurrent writes
2. 100 concurrent reads during writes
3. Measure:
   - Success rate
   - Average latency
   - Max latency
   - Deadlock count

### Chaos Test:
1. Random kill -9 during operations
2. Verify:
   - Stale locks cleaned
   - DB consistency maintained
   - Files not corrupted

---

## Priority Fixes

1. **CRITICAL**: Enable WAL mode + busy timeout
2. **CRITICAL**: Implement atomic file writes
3. **HIGH**: Exponential backoff with jitter
4. **HIGH**: Stale lock detection
5. **MEDIUM**: Lock ordering standardization
6. **LOW**: Performance tuning

---

## Implementation Plan

See todo list for detailed implementation steps.
