# Trail Laying Debug Guide

## Debug Logging Reference

The trail laying system now includes comprehensive debug logging to stderr. This guide explains how to interpret the logs.

---

## Log Message Types

### Success Messages: `[TRAIL_DEBUG]`

These indicate normal operation:

```
[TRAIL_DEBUG] Starting trail extraction from tool output
[TRAIL_DEBUG] Output content length: 1234
[TRAIL_DEBUG] extract_file_paths: content length = 1234
[TRAIL_DEBUG] Pattern 9 (relative) matched 2 paths
[TRAIL_DEBUG] Added path: src/components/Header.tsx
[TRAIL_DEBUG] Skipped duplicate substring: components/Header.tsx
[TRAIL_DEBUG] extract_file_paths: returning 2 paths
[TRAIL_DEBUG] Extracted 2 file paths: ['src/components/Header.tsx', 'backend/main.py']
[TRAIL_DEBUG] Calling lay_trails with agent_type=researcher, description=Investigate bug
[TRAIL_DEBUG] lay_trails called with 2 paths
[TRAIL_DEBUG] Connecting to database: C:\Users\...\memory\index.db
[TRAIL_DEBUG] Outcome=success, scent=discovery, strength=1.0
[TRAIL_DEBUG] Recording trail: src/components/Header.tsx
[TRAIL_DEBUG] Recording trail: backend/main.py
[TRAIL_DEBUG] Successfully recorded 2 trails
[TRAIL_DEBUG] lay_trails returned: 2
```

### Error Messages: `[TRAIL_ERROR]`

These indicate problems that need attention:

```
[TRAIL_ERROR] Failed to lay trails: OperationalError: database is locked
[TRAIL_ERROR] Traceback: ...
```

---

## Common Scenarios

### 1. Normal Operation (No Files)

```
[TRAIL_DEBUG] Starting trail extraction from tool output
[TRAIL_DEBUG] Output content length: 45
[TRAIL_DEBUG] extract_file_paths: content length = 45
[TRAIL_DEBUG] extract_file_paths: returning 0 paths
[TRAIL_DEBUG] Extracted 0 file paths: []
[TRAIL_DEBUG] No file paths extracted, skipping trail laying
```

**Status:** Normal - task didn't involve files

### 2. Successful Trail Laying

```
[TRAIL_DEBUG] Pattern 9 (relative) matched 1 paths
[TRAIL_DEBUG] Added path: hooks/post_tool.py
[TRAIL_DEBUG] Successfully recorded 1 trails
```

**Status:** Working correctly

### 3. Database Locked Error

```
[TRAIL_ERROR] Failed to lay trails: OperationalError: database is locked
```

**Cause:** Another process has the database open
**Solution:** Increase timeout or retry
**Impact:** Trails lost for this execution (non-fatal)

### 4. Pattern Deduplication

```
[TRAIL_DEBUG] Pattern 9 (relative) matched 1 paths
[TRAIL_DEBUG] Added path: src/components/Header.tsx
[TRAIL_DEBUG] Pattern 10 (action) matched 1 paths
[TRAIL_DEBUG] Skipped duplicate substring: components/Header.tsx
```

**Status:** Working correctly - keeping longest path

### 5. No Database

```
[TRAIL_DEBUG] Database not found at C:\Users\...\memory\index.db
```

**Cause:** Database hasn't been initialized
**Solution:** Run `python ~/.claude/emergent-learning/scripts/init-db.py`
**Impact:** No trails can be recorded

---

## Pattern Types

When debugging extraction issues, check which patterns are matching:

| Pattern # | Name | Description | Example |
|-----------|------|-------------|---------|
| 0 | backtick | Backtick-quoted paths | \`app/main.py\` |
| 1 | quoted | Quote-wrapped paths | "src/file.js" |
| 2 | file_path_param | file_path parameter | file_path = "test.py" |
| 3-5 | win_* | Windows absolute paths | C:\\Users\\...\\test.py |
| 6-8 | unix_* | Unix absolute paths | /home/user/.../test.py |
| 9 | relative | Relative paths | src/components/Header.tsx |
| 10 | action | Action verbs | "edited main.py" |
| 11 | file_prefix | File: prefix | File: test.py |

---

## Troubleshooting

### Problem: No trails being laid but files are mentioned

**Check:**
1. Look for `[TRAIL_DEBUG] extract_file_paths: returning 0 paths`
2. Examine which patterns are matching
3. Add test case to `test_trail_laying.py` with your content format

**Likely cause:** File paths don't match any regex patterns

**Solution:** Add new pattern to `trail_helper.py`

### Problem: Too many duplicate trails

**Check:**
```
[TRAIL_DEBUG] Added path: file.py
[TRAIL_DEBUG] Added path: src/file.py
[TRAIL_DEBUG] Added path: app/src/file.py
```

**Likely cause:** Deduplication logic isn't catching these
**Solution:** Review substring logic in extract_file_paths()

### Problem: Database errors

**Check:**
```
[TRAIL_ERROR] Failed to lay trails: OperationalError: ...
```

**Common causes:**
- Database locked by another process
- Disk full
- Permissions issue
- Corrupted database

**Solutions:**
- Increase timeout in `lay_trails()` (currently 5.0 seconds)
- Check disk space: `df -h`
- Check permissions: `ls -la ~/.claude/emergent-learning/memory/`
- Rebuild database if corrupted

---

## Monitoring Commands

### Count trails in last hour
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db "SELECT COUNT(*) FROM trails WHERE created_at > datetime('now', '-1 hour');"
```

### Group by agent
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db "SELECT agent_id, COUNT(*) FROM trails GROUP BY agent_id ORDER BY COUNT(*) DESC;"
```

### Recent trails with details
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db "SELECT created_at, location, scent, agent_id, message FROM trails ORDER BY created_at DESC LIMIT 10;"
```

### Check for errors in logs (if logging to file)
```bash
grep '\[TRAIL_ERROR\]' ~/.claude/hooks/logs/*.log | tail -20
```

---

## Disabling Debug Logging

To reduce log noise in production, you can disable debug logging:

**Option 1:** Set environment variable (not yet implemented)
```bash
export TRAIL_DEBUG=0
```

**Option 2:** Comment out debug lines (manual)
```python
# sys.stderr.write(f"[TRAIL_DEBUG] ...")
```

**Option 3:** Add debug flag to code (recommended future improvement)
```python
DEBUG = os.getenv('TRAIL_DEBUG', '1') == '1'

if DEBUG:
    sys.stderr.write(f"[TRAIL_DEBUG] ...")
```

---

## Performance Impact

Debug logging adds minimal overhead:
- ~10-20 stderr writes per trail laying operation
- Each write: <1ms
- Total overhead: ~10-20ms per task

**Recommendation:** Keep enabled until trail laying is proven stable in production
