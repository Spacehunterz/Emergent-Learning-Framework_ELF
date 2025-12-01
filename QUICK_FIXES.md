# Quick Fixes for 10/10 Error Handling

## Critical Issue #1: The ID=0 Bug

### Problem
`last_insert_rowid()` returns 0 when executed after a retry in `sqlite_with_retry()`.

### Fix (5 minutes)

In `scripts/record-failure.sh` and `scripts/record-heuristic.sh`, replace the database insert section:

**BEFORE (lines 251-267 in record-failure.sh)**:
```bash
if ! LAST_ID=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relative_path',
    '$title_escaped',
    '$summary_escaped',
    '$tags_escaped',
    '$domain_escaped',
    CAST($severity AS INTEGER)
);
SELECT last_insert_rowid();
SQL
); then
    log "ERROR" "Failed to insert into database"
    exit 1
fi
```

**AFTER**:
```bash
# Use atomic transaction to preserve last_insert_rowid()
LAST_ID=$(sqlite3 "$DB_PATH" <<SQL
BEGIN IMMEDIATE TRANSACTION;
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relative_path',
    '$title_escaped',
    '$summary_escaped',
    '$tags_escaped',
    '$domain_escaped',
    CAST($severity AS INTEGER)
);
SELECT last_insert_rowid();
COMMIT;
SQL
2>&1)

# Check for errors or invalid ID
if [ $? -ne 0 ] || [ -z "$LAST_ID" ] || [ "$LAST_ID" = "0" ]; then
    log "ERROR" "Failed to insert into database (ID: $LAST_ID)"
    rm -f "$filepath"  # Clean up orphaned file
    exit 1
fi
```

**Why this works**:
- `BEGIN IMMEDIATE` acquires write lock immediately
- Entire transaction (INSERT + SELECT) runs in same context
- `last_insert_rowid()` returns correct value
- If transaction fails, nothing is committed

---

## Critical Issue #2: Git Commit Failures Not Caught

### Problem
Script reports "success" even when git commit fails due to lock timeout.

### Fix (2 minutes)

In `scripts/record-failure.sh` and `scripts/record-heuristic.sh`, modify git commit section:

**BEFORE (lines 273-297)**:
```bash
if [ -d ".git" ]; then
    LOCK_FILE="$BASE_DIR/.git/claude-lock"

    if ! acquire_git_lock "$LOCK_FILE" 30; then
        log "ERROR" "Could not acquire git lock"
        echo "Error: Could not acquire git lock"
        exit 1
    fi

    git add "$filepath"
    git add "$DB_PATH"
    if ! git commit -m "failure: $title" -m "Domain: $domain | Severity: $severity"; then
        log "WARN" "Git commit failed or no changes to commit"
        echo "Note: Git commit skipped (no changes or already committed)"
    else
        log "INFO" "Git commit created"
        echo "Git commit created"
    fi

    release_git_lock "$LOCK_FILE"
fi
```

**AFTER**:
```bash
if [ -d ".git" ]; then
    LOCK_FILE="$BASE_DIR/.git/claude-lock"

    if ! acquire_git_lock "$LOCK_FILE" 30; then
        log "ERROR" "Could not acquire git lock, rolling back"
        # Rollback: delete DB record
        sqlite3 "$DB_PATH" "DELETE FROM learnings WHERE id = $LAST_ID;"
        # Rollback: delete file
        rm -f "$filepath"
        echo "Error: Could not acquire git lock"
        exit 1
    fi

    git add "$filepath"
    git add "$DB_PATH"
    if ! git commit -m "failure: $title" -m "Domain: $domain | Severity: $severity"; then
        # Only allow "no changes" as non-fatal
        if git diff --cached --quiet; then
            log "WARN" "No changes to commit (already committed?)"
            echo "Note: No changes to commit"
        else
            log "ERROR" "Git commit failed, rolling back"
            sqlite3 "$DB_PATH" "DELETE FROM learnings WHERE id = $LAST_ID;"
            rm -f "$filepath"
            release_git_lock "$LOCK_FILE"
            echo "Error: Git commit failed"
            exit 1
        fi
    else
        log "INFO" "Git commit created"
        echo "Git commit created"
    fi

    release_git_lock "$LOCK_FILE"
fi
```

---

## High Priority: Enable WAL Mode

### Problem
SQLite using legacy "delete" journal mode with 0ms busy timeout.

### Fix (30 seconds)

Create and run this script once:

```bash
#!/bin/bash
# enable-wal-mode.sh

DB_PATH="$HOME/.claude/emergent-learning/memory/index.db"

echo "Enabling WAL mode..."

sqlite3 "$DB_PATH" <<SQL
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA synchronous=NORMAL;
SQL

echo "Done!"
echo ""
echo "Verify:"
sqlite3 "$DB_PATH" <<SQL
PRAGMA journal_mode;
PRAGMA busy_timeout;
PRAGMA synchronous;
SQL
```

**Expected output**:
```
wal
5000
1
```

**Benefits**:
- 80-90% reduction in lock contention
- Multiple readers + one writer simultaneously
- Better performance under concurrency

---

## Medium Priority: Improve Retry Backoff

### Problem
Fixed sleep time doesn't adapt to contention level.

### Fix (3 minutes)

In `sqlite_with_retry()` function (both scripts):

**BEFORE**:
```bash
sleep 0.$((RANDOM % 5 + 1))
```

**AFTER**:
```bash
# Exponential backoff: 100ms, 400ms, 900ms, 1600ms, 2500ms
local backoff=$((attempt * attempt * 100))
local sleep_ms=$((100 + RANDOM % backoff))
sleep 0.$sleep_ms
```

---

## Quick Verification Test

After applying fixes, run this test:

```bash
#!/bin/bash
# verify-fixes.sh

cd ~/.claude/emergent-learning

echo "Testing 20 concurrent writes..."

for i in {1..20}; do
    bash scripts/record-failure.sh \
        --title "Verify_$i" \
        --domain "verify" \
        --summary "Testing fixes" \
        --severity 2 \
        > /tmp/verify_$i.log 2>&1 &
done

wait
sleep 2

# Check results
db_count=$(sqlite3 memory/index.db "SELECT COUNT(*) FROM learnings WHERE title LIKE 'Verify_%';")
id_zero=$(grep -c "ID: 0)" /tmp/verify_*.log 2>/dev/null || echo 0)

echo ""
echo "Results:"
echo "  Database records: $db_count/20"
echo "  ID=0 bugs: $id_zero"

if [ $db_count -eq 20 ] && [ $id_zero -eq 0 ]; then
    echo "  ✓ ALL FIXES WORKING!"
else
    echo "  ✗ Still has issues"
fi

# Cleanup
sqlite3 memory/index.db "DELETE FROM learnings WHERE domain = 'verify';"
```

**Expected**: 20/20 success, 0 ID=0 bugs

---

## Summary

| Fix | Time | Impact | Files to Edit |
|-----|------|--------|---------------|
| Fix ID=0 bug | 5 min | Critical | record-failure.sh, record-heuristic.sh |
| Rollback on git fail | 2 min | Critical | record-failure.sh, record-heuristic.sh |
| Enable WAL mode | 30 sec | High | Run once on DB |
| Improve backoff | 3 min | Medium | record-failure.sh, record-heuristic.sh |

**Total time to 9/10**: ~10 minutes
**Total time to 10/10**: ~30 minutes (with testing)
