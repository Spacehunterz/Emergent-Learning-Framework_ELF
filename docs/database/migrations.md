# Database Schema Migrations

## Overview

The Emergent Learning Framework includes an automatic schema migration system that ensures the database schema stays up to date with the codebase. Migrations run automatically on startup whenever a schema update is available.

**Issue Fixed:** #63 - `no such column: t1.topic` error

## How It Works

### Automatic Migration on Startup

When `QuerySystem.create()` is called:

1. Database tables are created via ORM models
2. `SchemaMigrator` checks the current schema version
3. Any pending migrations (newer than current version) are applied
4. Schema version is recorded in the `schema_version` table

### Zero Data Loss

All migrations are:
- **Idempotent** - Safe to run multiple times
- **Non-destructive** - Use `CREATE TABLE IF NOT EXISTS` and `ADD COLUMN` with defaults
- **Transactional** - Applied atomically or rolled back on error

## Current Migrations

| Version | File | Description | Status |
|---------|------|-------------|--------|
| 1-6 | (Previous) | Historical schema versions | Applied |
| 7 | `007_ensure_all_core_tables.sql` | Ensure all core tables exist | Applied |
| 8 | `008_fix_spike_reports_columns.sql` | Fix missing `topic` column in spike_reports | Applied |
| 9 | `009_conductor_workflow_tables.sql` | Create workflow orchestration tables | Applied |

## Migration File Format

Migration files are named using semantic versioning:

```
NNN_description_of_change.sql
 ↑
 └─ 3-digit version number
```

### Example: `008_fix_spike_reports_columns.sql`

```sql
-- Ensure spike_reports table exists with all required columns
-- Fixes: no such column: t1.topic error from issue #63

CREATE TABLE IF NOT EXISTS spike_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,    -- This column was missing
    question TEXT NOT NULL,
    findings TEXT NOT NULL,
    -- ... other columns
);

-- Add missing columns if they don't exist
ALTER TABLE spike_reports ADD COLUMN topic TEXT NOT NULL DEFAULT '';
ALTER TABLE spike_reports ADD COLUMN question TEXT NOT NULL DEFAULT '';
ALTER TABLE spike_reports ADD COLUMN findings TEXT NOT NULL DEFAULT '';

-- Ensure indexes exist
CREATE INDEX IF NOT EXISTS idx_spike_reports_topic ON spike_reports(topic);
```

## Schema Version Tracking

The `schema_version` table tracks which migrations have been applied:

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

Check current version:

```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "SELECT MAX(version) FROM schema_version"
```

## Troubleshooting

### Migration Partially Failed

If some migrations fail, the system continues and reports:

```
Status: partial
migrations_applied: [...]
migrations_failed: [...]
```

This prevents the entire system from breaking due to one failed migration.

### Manually Check Schema Health

```bash
python src/query/query.py --validate
```

Output will show:
- Database integrity
- Required tables
- Row counts per table
- Any missing columns

### Manual Migration

If needed, you can run migrations manually:

```python
import asyncio
from pathlib import Path
from src.query.migrations import SchemaMigrator

async def manual_migrate():
    db_path = str(Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db")
    migrator = SchemaMigrator(db_path)
    result = await migrator.migrate()
    print(result)

asyncio.run(manual_migrate())
```

## Adding New Migrations

1. **Check current version:**
   ```bash
   sqlite3 ~/.claude/emergent-learning/memory/index.db \
     "SELECT MAX(version) FROM schema_version"
   ```

2. **Create migration file:**
   - Location: `src/query/migrations/`
   - Name: `NNN_description.sql` (where NNN is next version number)

3. **Write SQL:**
   - Use `IF NOT EXISTS` for safety
   - Include both `CREATE TABLE` and `ALTER TABLE ADD COLUMN`
   - Add indexes at the end
   - Add migration record at the end

4. **Example template:**
   ```sql
   -- Description of what this migration does
   -- Fixes: (if fixing an issue, reference it)

   CREATE TABLE IF NOT EXISTS new_table (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       column1 TEXT NOT NULL,
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP
   );

   -- Add missing columns to existing table
   ALTER TABLE existing_table ADD COLUMN new_column TEXT;

   -- Create indexes
   CREATE INDEX IF NOT EXISTS idx_table_column ON table(column);

   -- Record migration
   INSERT OR IGNORE INTO schema_version (version, description)
   VALUES (10, 'Add new_table and new_column');
   ```

5. **Test:**
   ```bash
   python src/query/query.py --validate
   ```

## Performance Impact

- **First run:** Minimal overhead (tables created once)
- **Subsequent runs:** ~10-50ms (version check only)
- **Large migrations:** May add startup latency (logged in debug mode)

## Related

- Database schema documentation: `docs/database/schema.md`
- Migration system code: `src/query/migrations.py`
- Query system: `src/query/core.py` (calls migrations in `_init_database`)

## References

- Issue #63: "no such column: t1.topic" error when using query.py
- Solution: Automatic schema migrations with version tracking
