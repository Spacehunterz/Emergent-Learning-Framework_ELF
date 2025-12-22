# Concurrency Quick Reference

**Agent E Improvements - Quick Reference Card**

---

## SQLite Configuration

### Check Current Settings
```bash
sqlite3 memory/index.db "PRAGMA journal_mode;"
sqlite3 memory/index.db "PRAGMA busy_timeout;"
```

### Expected Values
```
journal_mode: wal
busy_timeout: 10000 (ms)
```

---

## Using the Concurrency Library

### Import
```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/concurrency.sh"
```

### Atomic File Write
```bash
content="Your content here"
write_atomic "/path/to/file.md" "$content"
```

### Atomic File Append
```bash
append_atomic "/path/to/file.md" "New content\n"
```

### SQLite with Retry
```bash
sqlite_with_retry "$DB_PATH" "INSERT INTO table VALUES (...);"
```

### Git Locking
```bash
LOCK_FILE="$BASE_DIR/.git/claude-lock"

if acquire_git_lock "$LOCK_FILE" 10; then
    # Do git operations
    git add file.md
    git commit -m "message"
    release_git_lock "$LOCK_FILE"
else
    echo "Failed to acquire lock"
    exit 1
fi
```

### SQL Escaping
```bash
title_escaped=$(escape_sql "$user_input")
sqlite3 "$DB_PATH" "INSERT INTO table VALUES ('$title_escaped');"
```

### Input Validation
```bash
severity=$(validate_severity "$user_input")  # Returns 1-5
confidence=$(validate_confidence "$user_input")  # Returns 0.0-1.0
```

---

## Testing

### Concurrent Reads
```bash
./simple-concurrency-test.sh 30
```

### Full Stress Test
```bash
./concurrency-stress-test.sh 20 10
```

---

## Lock Behavior

### Timeouts
- **Git lock**: 10 seconds
- **SQLite busy timeout**: 10000ms (10 seconds)
- **Retry attempts**: 5 maximum

### Backoff Schedule
```
Attempt 1: 0.1-0.2s
Attempt 2: 0.2-0.4s
Attempt 3: 0.4-0.8s
Attempt 4: 0.8-1.6s
Attempt 5: 1.6-3.2s
```

### Stale Lock Detection
- Locks older than 5 minutes are considered stale
- Automatically cleaned before acquire attempts
- Handles process death (kill -9)

---

## Common Patterns

### Safe Database Insert
```bash
# Escape input
title_escaped=$(escape_sql "$title")
domain_escaped=$(escape_sql "$domain")

# Insert with retry
if ! id=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO learnings (title, domain) VALUES ('$title_escaped', '$domain_escaped');
SELECT last_insert_rowid();
SQL
); then
    echo "Failed to insert"
    exit 1
fi

echo "Inserted with ID: $id"
```

### Safe File + DB Update
```bash
# 1. Create file atomically
write_atomic "$file_path" "$content"

# 2. Insert into DB
if ! sqlite_with_retry "$DB_PATH" "INSERT ..."; then
    rm -f "$file_path"  # Rollback
    exit 1
fi

# 3. Commit to git
acquire_git_lock "$LOCK_FILE" 10
git add "$file_path" "$DB_PATH"
git commit -m "message"
release_git_lock "$LOCK_FILE"
```

---

## Troubleshooting

### Lock is Stuck
```bash
# Check for lock directories
ls -la ~/.claude/emergent-learning/.git/*.dir

# Manually clean (if confirmed stale)
rmdir ~/.claude/emergent-learning/.git/claude-lock.dir
```

### Database Locked Errors
```bash
# Check if WAL mode is enabled
sqlite3 memory/index.db "PRAGMA journal_mode;"

# If not "wal", enable it
sqlite3 memory/index.db "PRAGMA journal_mode=WAL;"
```

### Performance Issues
```bash
# Check WAL file size
ls -lh memory/index.db*

# Manual checkpoint (if WAL is large)
sqlite3 memory/index.db "PRAGMA wal_checkpoint(FULL);"
```

---

## Key Improvements Summary

| Area | Before | After | Improvement |
|------|--------|-------|-------------|
| Journal Mode | DELETE | WAL | Multi-reader concurrency |
| Busy Timeout | 0ms | 10000ms | Automatic retry |
| Lock Timeout | 30s | 10s | 3x faster |
| Retry Pattern | Linear | Exponential | No thundering herd |
| File Writes | Direct | Atomic rename | Crash-safe |
| Stale Locks | Manual | Auto-detected | Self-healing |

---

## Files Reference

- **Library**: `scripts/lib/concurrency.sh`
- **Analysis**: `CONCURRENCY_ANALYSIS.md`
- **Full Report**: `AGENT_E_CONCURRENCY_REPORT.md`
- **Test Evidence**: `AGENT_E_TEST_EVIDENCE.txt`
- **Example Script**: `scripts/record-failure-v3.sh`

---

**Last Updated**: 2025-12-01 by Agent E
