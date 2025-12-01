# Investigation: 20-Agent Haiku Swarm Audit

**Date**: 2025-12-01
**Agents**: 20 coordinated Haiku subagents
**Scope**: Full emergent-learning framework stress test

## Critical Findings

### RED ERRORS (Must Fix)

1. **last_insert_rowid() Bug** - Returns 0 instead of actual ID
   - Location: record-failure.sh:155, record-heuristic.sh:112
   - Cause: SELECT in separate sqlite3 connection from INSERT
   - Fix: Combine INSERT and SELECT in same connection

2. **Concurrent Write Failures** - 50% failure rate under load
   - Git index.lock contention (40% of failures)
   - SQLite database lock timeout (10% of failures)
   - Orphaned records created
   - Fix: Add flock serialization, SQLite retry logic

3. **SQL Injection in Shell Scripts** - CRITICAL security
   - Numeric fields (severity, confidence) not quoted
   - Attack: `--severity "1; DELETE FROM learnings;--"`
   - Fix: Parameterize or migrate to Python

4. **Foreign Keys Disabled** - PRAGMA foreign_keys = 0
   - Referential integrity not enforced
   - Fix: Enable in init code

### HIGH Priority Issues

5. **No Remote Backup** - Single point of failure
   - If .git deleted, total data loss
   - Fix: Push to GitHub/GitLab immediately

6. **10 Domains Out of Sync** - DB vs markdown mismatch
   - 7 orphaned markdown files (not in DB)
   - 3 DB domains missing markdown files
   - Fix: Reconciliation script needed

7. **Error Handling Score: 3-4/10**
   - Git errors suppressed with `|| echo`
   - No logging implementation
   - SQLite errors hidden

8. **Missing Indexes for Scale**
   - No index on created_at (ORDER BY slow at scale)
   - No composite index on (domain, confidence)
   - Fix: Add before 10k+ records

### PASSING Areas

- Unicode handling: 100% (20/20 tests)
- Query.py security: Parameterized queries ✓
- Database integrity: No corruption ✓
- Environment compatibility: 97% ✓
- Golden rules loading: Working ✓

## Statistics

- Total tests run: 100+
- Pass rate: ~85%
- Critical bugs: 4
- High priority: 4
- Medium issues: 15+
- Feature proposals: 5

## Recommended Actions

1. IMMEDIATE: Fix last_insert_rowid() bug (5 min)
2. IMMEDIATE: Push to remote git (7 min)
3. HIGH: Add concurrent write protection (2-4 hrs)
4. HIGH: Fix SQL injection in numeric fields (30 min)
5. MEDIUM: Enable foreign key constraints (5 min)
6. MEDIUM: Add missing indexes (15 min)
7. MEDIUM: Reconcile DB/markdown sync (1 hr)
