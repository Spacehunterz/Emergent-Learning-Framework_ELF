# Issue #43 Analysis: ELF Query System Dual-Database Architecture

**Issue:** https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues/43
**Author:** mimosel
**Date:** December 19, 2025
**Status:** Open

---

## Summary

The issue claims the ELF query system's dual-database architecture is undocumented and confusing. After investigation, this is **partially valid** - documentation exists but is not discoverable enough.

---

## Claims vs Reality

### 1. "Undocumented dual-database system"

| Claim | Reality |
|-------|---------|
| No documentation exists | Documentation exists in `docs/architecture/per-project-architecture.md` |
| Users don't know about two databases | True - main CLAUDE.md doesn't explain this clearly |

**Verdict:** Partially valid. Documentation exists but is buried.

---

### 2. "Global database has 12 heuristics"

| Claim | Reality |
|-------|---------|
| 12 heuristics in global | **176 heuristics** in global database |

**Verdict:** Inaccurate. The global database has significantly more content.

```bash
# Verified via:
sqlite3 ~/.claude/emergent-learning/memory/index.db "SELECT COUNT(*) FROM heuristics;"
# Output: 176
```

---

### 3. "Missing CLI flags for database selection"

| Requested | Current State |
|-----------|---------------|
| `--global` flag | Does not exist |
| `--all` flag | Does not exist (but `--context` merges both) |
| `--project-only` flag | **Already exists** |
| `--project-status` flag | **Already exists** |

**Verdict:** Partially valid. `--global-only` would be useful addition.

---

### 4. "Windows compatibility gap - sqlite3 CLI unavailable"

| Claim | Reality |
|-------|---------|
| sqlite3 CLI not available on Windows | True for MSYS/Git Bash |
| ELF requires sqlite3 CLI | **False** - ELF uses Python's built-in sqlite3 module |

**Verdict:** Non-issue. ELF is Python-based and works fine on Windows.

---

### 5. "Database selection logic not explained"

**Current behavior:**
- If `.elf/` exists in project → Project mode (merges both databases)
- If no `.elf/` → Global-only mode

**Query output already shows this:**
```
[Project] Project: my-project (/path/to/project)
   Mode: Project + Global merged
```
or
```
[Project] Project: emergent-learning
   Mode: Global-only (no .elf/ - run 'elf init' to enable)
```

**Verdict:** Already implemented, but could be more prominent.

---

### 6. "Unclear schema"

**Reality:** Schema is documented in `docs/architecture/per-project-architecture.md`:

```sql
-- Project DB schema
CREATE TABLE heuristics (
    id INTEGER PRIMARY KEY,
    rule TEXT NOT NULL,
    explanation TEXT,
    domain TEXT,
    confidence REAL DEFAULT 0.7,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ...
);
```

**Verdict:** Documentation exists, just not discoverable.

---

## What's Actually Missing

1. **`--global-only` flag** - Only `--project-only` exists
2. **Prominent documentation** - Dual-database info buried in `docs/architecture/`
3. **Schema quick reference** - No single-page schema reference

---

## Recommended Actions

### Option A: Quick Fix (Documentation Only)
- Add dual-database section to main README.md
- Add link to architecture docs in query.py `--help`

### Option B: Feature Addition
- Add `--global-only` flag to query.py
- Add `--schema` flag to display table structures
- Update CLAUDE.md with clearer database explanation

### Option C: Full Response
- Respond to issue explaining what already exists
- Link to existing documentation
- Offer to add `--global-only` flag if desired

---

## Existing Documentation Locations

| Topic | File |
|-------|------|
| Per-project architecture | `docs/architecture/per-project-architecture.md` |
| Query system architecture | `query/ARCHITECTURE.md` |
| Database schema | `docs/architecture/per-project-architecture.md` (lines 296-348) |
| CLI usage | `python query.py --help` |

---

## Recommended Issue Response

```markdown
Thanks for the detailed report! Let me clarify the current state:

## What Already Exists

1. **Documentation**: The dual-database architecture is documented in
   `docs/architecture/per-project-architecture.md` - I agree this could be
   more discoverable.

2. **CLI flags**:
   - `--project-only` - Shows only project context
   - `--project-status` - Shows current project/database status
   - `--context` - Merges both databases (default behavior)

3. **Database indicator**: The query output header already shows which mode
   you're in:
   ```
   [Project] Project: my-project
      Mode: Project + Global merged
   ```

4. **Windows compatibility**: ELF uses Python's built-in sqlite3 module,
   not the sqlite3 CLI, so it works on Windows without additional tools.

## Valid Points

- A `--global-only` flag would be useful - we can add this
- The documentation could be more prominent in the main README
- A schema quick-reference would help

Would you like me to submit a PR adding `--global-only` and improving
documentation discoverability?
```

---

## Files Referenced

- `~/.claude/emergent-learning/query/query.py`
- `~/.claude/emergent-learning/docs/architecture/per-project-architecture.md`
- `~/.claude/emergent-learning/query/ARCHITECTURE.md`
- `~/.claude/emergent-learning/memory/index.db`
