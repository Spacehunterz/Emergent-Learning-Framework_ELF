# Disaster Recovery Guide

**Emergent Learning Framework**

This document provides step-by-step procedures for recovering from various failure scenarios.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Backup Strategy](#backup-strategy)
3. [Recovery Scenarios](#recovery-scenarios)
4. [Tools Reference](#tools-reference)
5. [Testing & Verification](#testing--verification)
6. [Escalation](#escalation)

---

## Quick Reference

### Emergency Recovery Commands

```bash
# List available backups
~/.claude/emergent-learning/scripts/restore.sh list

# Restore latest backup
~/.claude/emergent-learning/scripts/restore.sh latest

# Restore specific backup
~/.claude/emergent-learning/scripts/restore.sh YYYYMMDD_HHMMSS

# Restore to git commit
~/.claude/emergent-learning/scripts/restore-from-git.sh HEAD~5

# Verify backups
~/.claude/emergent-learning/scripts/verify-backup.sh
```

### Backup Schedule

- **Daily**: Automated backups (keep last 7 days)
- **Weekly**: Sunday backups (keep last 4 weeks)
- **Monthly**: 1st of month backups (keep last 12 months)

### Critical Files

```
~/.claude/emergent-learning/
├── memory/
│   ├── index.db           # Main knowledge database
│   └── vectors.db         # Vector embeddings
├── scripts/
│   ├── backup.sh          # Create backups
│   ├── restore.sh         # Restore from backup
│   ├── restore-from-git.sh # Git-based recovery
│   └── verify-backup.sh   # Verify backup integrity
└── DISASTER_RECOVERY.md   # This document
```

---

## Backup Strategy

### Automated Backups

Set up automated daily backups with cron:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * ~/.claude/emergent-learning/scripts/backup.sh >> ~/.claude/backups/backup.log 2>&1

# Add weekly verification on Sundays at 3 AM
0 3 * * 0 ~/.claude/emergent-learning/scripts/verify-backup.sh --alert-on-fail
```

### Manual Backup

```bash
cd ~/.claude/emergent-learning
./scripts/backup.sh
```

### Remote Backup

Configure remote backup destination:

```bash
# Using rsync
export REMOTE_BACKUP_DEST="user@backup-server:/backups/emergent-learning"
./scripts/backup.sh

# Using rclone (cloud storage)
export REMOTE_BACKUP_DEST="remote:emergent-learning-backups"
./scripts/backup.sh
```

### Backup Contents

Each backup includes:
- **SQL dumps** of both databases (human-readable, cross-platform)
- **Binary database files** (exact copies for fast restoration)
- **All git-tracked files** (scripts, documentation, markdown files)
- **Metadata** (timestamp, git commit, file sizes)
- **Checksums** (MD5 hashes for integrity verification)

---

## Recovery Scenarios

### Scenario 1: Corrupted Database

**Symptoms:**
- SQLite errors when querying
- "database disk image is malformed"
- Application crashes

**Recovery Steps:**

1. **Verify the corruption:**
   ```bash
   cd ~/.claude/emergent-learning
   sqlite3 memory/index.db "PRAGMA integrity_check;"
   sqlite3 memory/vectors.db "PRAGMA integrity_check;"
   ```

2. **List available backups:**
   ```bash
   ./scripts/restore.sh list
   ```

3. **Restore from latest backup:**
   ```bash
   ./scripts/restore.sh latest
   ```

4. **Verify restoration:**
   ```bash
   sqlite3 memory/index.db "PRAGMA integrity_check;"
   sqlite3 memory/vectors.db "PRAGMA integrity_check;"
   ```

**Recovery Time:** 2-5 minutes

**Data Loss:** Last changes since most recent backup (max 24 hours if daily backups)

---

### Scenario 2: Accidental File Deletion

**Symptoms:**
- Missing scripts, markdown files, or configuration
- Git-tracked files deleted

**Recovery Steps:**

1. **If files are git-tracked:**
   ```bash
   cd ~/.claude/emergent-learning

   # Check what was deleted
   git status

   # Restore specific file
   git checkout HEAD -- path/to/file

   # Or restore all deleted files
   git checkout HEAD -- .
   ```

2. **If entire directory deleted:**
   ```bash
   ./scripts/restore.sh latest
   ```

3. **Verify restoration:**
   ```bash
   git status
   ls -la memory/
   ```

**Recovery Time:** 1-2 minutes (git) or 2-5 minutes (full restore)

**Data Loss:** None if using git, or last backup interval if using full restore

---

### Scenario 3: Bad Update/Configuration Change

**Symptoms:**
- System not working after recent changes
- Need to roll back to previous state

**Recovery Steps:**

1. **Check recent commits:**
   ```bash
   cd ~/.claude/emergent-learning
   ./scripts/restore-from-git.sh list
   ```

2. **Restore to previous commit (files only, keep current databases):**
   ```bash
   ./scripts/restore-from-git.sh --keep-databases HEAD~1
   ```

3. **If databases also need rollback:**
   ```bash
   ./scripts/restore-from-git.sh --restore-databases abc1234
   ```

   **Note:** Database restore from git only works if databases were committed to git at that point.

4. **Test the restored state**

5. **If satisfied, commit the rollback:**
   ```bash
   git add .
   git commit -m "Rollback to working state"
   ```

**Recovery Time:** 1-3 minutes

**Data Loss:** Changes made since target commit

---

### Scenario 4: Complete System Loss

**Symptoms:**
- Entire framework directory deleted
- Hard drive failure
- System reinstall

**Recovery Steps:**

1. **Clone or recreate framework:**
   ```bash
   mkdir -p ~/.claude
   cd ~/.claude
   git clone <repository-url> emergent-learning
   # OR if no git remote:
   mkdir emergent-learning
   ```

2. **Restore from backup:**
   ```bash
   cd emergent-learning
   ./scripts/restore.sh latest
   ```

3. **Verify restoration:**
   ```bash
   ./scripts/verify-backup.sh latest
   ```

4. **Test framework functionality:**
   ```bash
   python query/query.py --context
   ```

**Recovery Time:** 5-15 minutes (depending on backup size)

**Data Loss:** Last changes since most recent backup

---

### Scenario 5: Backup Corruption

**Symptoms:**
- Backup verification fails
- Cannot extract backup
- Checksum mismatch

**Recovery Steps:**

1. **Verify all backups:**
   ```bash
   ./scripts/verify-backup.sh
   ```

2. **Find the most recent valid backup:**
   ```bash
   ./scripts/verify-backup.sh --alert-on-fail
   ```

3. **Restore from the most recent valid backup:**
   ```bash
   ./scripts/restore.sh <valid-backup-timestamp>
   ```

4. **Investigate backup failure:**
   - Check disk space
   - Check backup logs
   - Verify backup script permissions
   - Test backup process manually

**Recovery Time:** Variable (depends on finding valid backup)

**Data Loss:** Depends on age of valid backup

**Prevention:** Regular backup verification with `verify-backup.sh`

---

### Scenario 6: Data Inconsistency

**Symptoms:**
- Databases out of sync
- Markdown files don't match database
- Query results inconsistent

**Recovery Steps:**

1. **Sync databases with markdown files:**
   ```bash
   cd ~/.claude/emergent-learning
   ./scripts/sync-db-markdown.sh
   ```

2. **If sync fails, restore from backup:**
   ```bash
   ./scripts/restore.sh latest
   ```

3. **Verify consistency:**
   ```bash
   python query/query.py --context
   # Check if results match expected state
   ```

**Recovery Time:** 2-5 minutes

**Data Loss:** Depends on severity; sync may preserve data, full restore loses changes since backup

---

### Scenario 7: Partial Corruption (Database Recoverable)

**Symptoms:**
- Some database queries work, others fail
- Database partially readable

**Recovery Steps:**

1. **Export what you can:**
   ```bash
   cd ~/.claude/emergent-learning
   sqlite3 memory/index.db .dump > manual_export.sql
   ```

2. **Create new database from export:**
   ```bash
   mv memory/index.db memory/index.db.corrupted
   sqlite3 memory/index.db < manual_export.sql
   ```

3. **Verify new database:**
   ```bash
   sqlite3 memory/index.db "PRAGMA integrity_check;"
   ```

4. **If export fails, restore from backup:**
   ```bash
   ./scripts/restore.sh latest
   ```

**Recovery Time:** 3-10 minutes

**Data Loss:** Corrupted records only (if export works), or last backup interval (if full restore needed)

---

### Scenario 8: Wrong Restore (Restore Undo)

**Symptoms:**
- Restored wrong backup
- Need to undo restoration

**Recovery Steps:**

1. **Check for safety backup:**
   ```bash
   ls -lah ~/.claude/backups/emergent-learning/pre-restore-*.tar.gz
   ```

2. **Restore from safety backup:**
   ```bash
   # Find the safety backup created just before wrong restore
   ./scripts/restore.sh pre-restore-YYYYMMDD_HHMMSS
   ```

3. **If no safety backup exists:**
   ```bash
   # Restore from a backup before the wrong restore
   ./scripts/restore.sh list
   # Choose appropriate backup
   ./scripts/restore.sh <correct-timestamp>
   ```

**Recovery Time:** 2-5 minutes

**Data Loss:** Depends on which backup you restore

**Note:** Safety backups are created automatically unless `--no-backup` flag is used

---

## Tools Reference

### backup.sh

**Purpose:** Create timestamped backups with automatic rotation

**Usage:**
```bash
./scripts/backup.sh
```

**Environment Variables:**
- `BACKUP_ROOT`: Backup destination (default: `~/.claude/backups/emergent-learning`)
- `REMOTE_BACKUP_DEST`: Remote backup location (optional)

**Features:**
- SQL dumps (cross-platform, human-readable)
- Binary database copies (fast restoration)
- Git archive of tracked files
- Checksums for verification
- Automatic compression
- Backup rotation (7 daily, 4 weekly, 12 monthly)
- Remote sync support (rsync/rclone)

---

### restore.sh

**Purpose:** Restore framework from backup

**Usage:**
```bash
./scripts/restore.sh [OPTIONS] <backup-timestamp>
```

**Options:**
- `--sql-only`: Restore from SQL dumps only
- `--verify-only`: Verify backup without restoring
- `--force`: Skip confirmation prompts
- `--no-backup`: Don't create safety backup

**Special Arguments:**
- `latest`: Restore most recent backup
- `list`: Show available backups

**Examples:**
```bash
./scripts/restore.sh latest
./scripts/restore.sh 20231201_120000
./scripts/restore.sh --verify-only latest
./scripts/restore.sh --force 20231201_120000
```

**Safety Features:**
- Creates pre-restore safety backup
- Verifies backup integrity before restore
- Confirms before overwriting data
- Checks database integrity after restore

---

### restore-from-git.sh

**Purpose:** Point-in-time recovery using git history

**Usage:**
```bash
./scripts/restore-from-git.sh [OPTIONS] <commit-ref>
```

**Options:**
- `--keep-databases`: Don't restore databases (default)
- `--restore-databases`: Also restore database state
- `--force`: Skip confirmation prompts
- `--dry-run`: Show what would be restored

**Special Arguments:**
- `list`: Show recent commits
- `HEAD~N`: Go back N commits
- `<hash>`: Specific commit hash

**Examples:**
```bash
./scripts/restore-from-git.sh list
./scripts/restore-from-git.sh HEAD~5
./scripts/restore-from-git.sh --restore-databases abc1234
./scripts/restore-from-git.sh --dry-run HEAD~1
```

**Important:**
- By default, only git-tracked files are restored
- Databases are NOT restored unless `--restore-databases` is used
- Database restore from git requires databases were committed
- Stashes uncommitted changes before restore

---

### verify-backup.sh

**Purpose:** Verify backup integrity and test restoration

**Usage:**
```bash
./scripts/verify-backup.sh [OPTIONS] [backup-timestamp]
```

**Options:**
- `--full-test`: Perform actual restore test
- `--alert-on-fail`: Exit with error if any backup fails
- `--email <address>`: Send email alert on failure

**Special Arguments:**
- `latest`: Verify most recent backup
- (no argument): Verify all backups

**Examples:**
```bash
./scripts/verify-backup.sh
./scripts/verify-backup.sh latest
./scripts/verify-backup.sh --full-test latest
./scripts/verify-backup.sh --alert-on-fail --email admin@example.com
```

**Verification Levels:**
1. File existence and readability
2. Archive integrity
3. Content extraction and checksums
4. Database integrity checks
5. Full restoration test (optional)

---

## Testing & Verification

### Regular Testing Schedule

**Monthly:**
- Full backup verification: `./scripts/verify-backup.sh --full-test latest`
- Test restoration to temporary location
- Document any issues

**Quarterly:**
- Complete disaster recovery drill
- Test restoration on clean system
- Verify all documentation is current
- Update runbooks if needed

**After System Changes:**
- Create backup before changes
- Verify backup after changes
- Test restore process if major changes

### Test Restoration

Test restoration without affecting production:

```bash
# Create test environment
export BACKUP_ROOT=~/.claude/backups/emergent-learning
export FRAMEWORK_DIR=/tmp/test-restore

# Create test structure
mkdir -p "$FRAMEWORK_DIR/memory"
cd "$FRAMEWORK_DIR"
git init

# Test restore
~/.claude/emergent-learning/scripts/restore.sh --force latest

# Verify
sqlite3 memory/index.db "PRAGMA integrity_check;"
python query/query.py --context

# Cleanup
rm -rf /tmp/test-restore
unset FRAMEWORK_DIR
```

### Backup Health Monitoring

Add to monitoring system:

```bash
# Daily backup success check
if [ ! -f ~/.claude/backups/emergent-learning/$(date +%Y%m%d)*.tar.gz ]; then
    echo "ERROR: No backup created today"
    # Send alert
fi

# Weekly verification
0 3 * * 0 ~/.claude/emergent-learning/scripts/verify-backup.sh --alert-on-fail --email admin@example.com
```

---

## Escalation

### When to Escalate

Escalate to system administrator or data recovery specialist when:

1. **All backups are corrupted**
   - No valid backup can be found
   - Need professional data recovery

2. **Hardware failure**
   - Disk failure during recovery
   - System unable to boot

3. **Data loss exceeds acceptable threshold**
   - More than 1 week of data would be lost
   - Critical learnings or experiments affected

4. **Recovery procedures fail**
   - Scripts fail with unknown errors
   - Database restoration doesn't complete
   - Data inconsistencies persist

### Escalation Contacts

```
Primary: System Administrator
  - Email: admin@example.com
  - Phone: +1-xxx-xxx-xxxx
  - Escalation SLA: 2 hours

Secondary: Data Recovery Team
  - Email: recovery@example.com
  - Phone: +1-xxx-xxx-xxxx
  - Escalation SLA: 4 hours

Emergency: CEO (for decision on data loss acceptance)
  - See ceo-inbox/ for decision templates
```

### Escalation Checklist

Before escalating:

- [ ] Documented what happened
- [ ] Tried standard recovery procedures
- [ ] Verified backup status
- [ ] Estimated data loss
- [ ] Collected error messages/logs
- [ ] Determined business impact
- [ ] Identified time sensitivity

---

## Appendices

### A. Backup File Structure

```
backup-YYYYMMDD_HHMMSS/
├── backup_metadata.txt      # Backup information
├── checksums.md5            # File checksums
├── index.db                 # Binary database
├── index.sql                # SQL dump
├── vectors.db               # Binary database
├── vectors.sql              # SQL dump
├── scripts/                 # Framework scripts
├── memory/                  # Markdown files
├── golden-rules/            # Golden rules
└── [other git-tracked files]
```

### B. Database Schema

See `memory/schema.sql` for complete schema definition.

Key tables:
- `learnings`: Index of failures and successes
- `heuristics`: Extracted rules and patterns
- `experiments`: Active experiments
- `cycles`: Learning loop iterations
- `ceo_reviews`: Decisions needing human input

### C. Common Error Messages

**"database disk image is malformed"**
- Cause: Database corruption
- Solution: Restore from backup (Scenario 1)

**"unable to open database file"**
- Cause: File permissions or missing file
- Solution: Check permissions or restore from backup

**"UNIQUE constraint failed"**
- Cause: Duplicate key insertion
- Solution: Check application logic, not a backup issue

**"backup verification failed"**
- Cause: Corrupted backup file
- Solution: Use older backup (Scenario 5)

### D. Best Practices

1. **Always verify backups regularly**
   - Automated verification catches issues early
   - Manual testing ensures recovery procedures work

2. **Keep multiple backup generations**
   - Don't rely on single backup
   - Rotation policy preserves history

3. **Test recovery procedures**
   - Regular drills ensure readiness
   - Documentation stays current

4. **Monitor backup health**
   - Automated alerts on failure
   - Regular review of backup logs

5. **Secure backup storage**
   - Separate physical location for backups
   - Encrypted remote backups
   - Access controls on backup files

6. **Document everything**
   - Record what happened
   - Note what worked and what didn't
   - Update procedures based on experience

---

## Version History

- **v1.0** (2025-12-01): Initial disaster recovery procedures and tooling

---

**Remember:** When in doubt, restore from backup. Better to lose recent changes than to corrupt existing data further.

**Emergency Contact:** See Escalation section above.
