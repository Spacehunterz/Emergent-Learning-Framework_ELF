# Golden Rule Accountability Tracking System

## Overview

The accountability tracking system monitors Golden Rule violations and provides progressive consequences to maintain adherence to established best practices.

## Database Schema

```sql
CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    rule_name TEXT NOT NULL,
    violation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    session_id TEXT,
    acknowledged BOOLEAN DEFAULT 0
);
```

## Recording Violations

### Quick Recording Script

```bash
~/.claude/emergent-learning/scripts/record-violation.sh <rule_number> "description"
```

**Example:**
```bash
record-violation.sh 1 "Started investigation without querying building"
```

The script will:
1. Validate rule number exists in golden-rules.md
2. Insert violation into database
3. Show current violation count
4. Display warning/probation/critical status if applicable
5. Auto-create CEO escalation at 10+ violations

## Viewing Violations

### Accountability Banner

```bash
python ~/.claude/emergent-learning/query/query.py --accountability-banner
```

Displays a visually distinct banner with:
- Total violations in last 7 days
- Status (NORMAL/WARNING/PROBATION/CRITICAL)
- Violations by rule
- Recent violations
- Progressive consequences

### Violation Summary

```bash
python ~/.claude/emergent-learning/query/query.py --violations --violation-days 7
```

Returns structured data:
- Total violations
- Acknowledged vs unacknowledged
- Violations grouped by rule
- Recent violations list

### Statistics

```bash
python ~/.claude/emergent-learning/query/query.py --stats
```

Includes violation statistics in overall framework statistics.

## Progressive Consequences

### 0-2 Violations (NORMAL)
- Status: Acceptable compliance level
- Action: None required
- Banner: Green status indicator

### 3-4 Violations (WARNING)
- Status: Review adherence to rules
- Action: Self-assessment recommended
- Banner: Yellow warning box
- Message: "2 more violations = probation"

### 5-9 Violations (PROBATION)
- Status: Increased scrutiny mode
- Action: Mandatory review of violations
- Banner: Yellow probation box
- Message: "Under probation - violations logged prominently"

### 10+ Violations (CRITICAL)
- Status: CEO escalation required
- Action: **Automatic CEO escalation created**
- Banner: Red critical box
- Auto-creates:
  - File in `ceo-inbox/VIOLATION_THRESHOLD_<timestamp>.md`
  - Entry in `ceo_reviews` table
- Contains:
  - All violations from last 7 days
  - Violations grouped by rule
  - Recommended actions

## Query System Integration

The violations system is fully integrated into query.py:

### Python API

```python
from query import QuerySystem

qs = QuerySystem()

# Get violations
violations = qs.get_violations(days=7, acknowledged=False)

# Get summary
summary = qs.get_violation_summary(days=7)

# Generate banner
from query import generate_accountability_banner
banner = generate_accountability_banner(summary)
print(banner)
```

### CLI Arguments

```bash
# Show banner
python query.py --accountability-banner

# Show violation summary
python query.py --violations [--violation-days N]

# Include in context
python query.py --context --domain coordination
# (violations banner automatically shown if > 0)

# Get statistics (includes violations)
python query.py --stats
```

## Acknowledgment System

To acknowledge violations (e.g., after CEO review):

```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "UPDATE violations SET acknowledged = 1 WHERE violation_date >= datetime('now', '-7 days');"
```

Or acknowledge specific violations:

```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "UPDATE violations SET acknowledged = 1 WHERE id = <violation_id>;"
```

## Integration with Emergent Learning Framework

### At Session Start

Check violations when querying the building:

```bash
python ~/.claude/emergent-learning/query/query.py --context
# Shows accountability banner if violations exist
```

### During Work

Record violations immediately when they occur:

```bash
record-violation.sh <rule_number> "Description of what happened"
```

### At Session End

Review violations before closing:

```bash
python query.py --accountability-banner
```

## CEO Escalation Document

When critical threshold is reached, auto-generated file includes:

1. **Context**: Total violations and timeframe
2. **Recent Violations**: Full table of last 10 violations
3. **Violations by Rule**: Grouped statistics
4. **Options**: Suggested courses of action
   - Review and Reset
   - System Adjustment (modify rules if impractical)
   - Enhanced Monitoring
   - Training
5. **Recommendation**: Framework for CEO decision

## Best Practices

1. **Be Honest**: Record violations immediately when they occur
2. **Be Specific**: Provide clear descriptions of what happened
3. **Review Regularly**: Check banner at start/end of sessions
4. **Acknowledge**: Mark violations as acknowledged after CEO review
5. **Learn**: Use violation patterns to improve practices

## Maintenance

### Reset After Review

After CEO reviews and corrective action is taken:

```bash
# Acknowledge all recent violations
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "UPDATE violations SET acknowledged = 1 WHERE acknowledged = 0;"

# Or delete old violations (use with caution)
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "DELETE FROM violations WHERE violation_date < datetime('now', '-30 days');"
```

### Adjust Thresholds

Edit thresholds in:
- `scripts/record-violation.sh` (lines 91-133)
- `query/query.py` generate_accountability_banner() (lines 1168-1183)

Current thresholds:
- Warning: 3+ violations
- Probation: 5+ violations
- Critical: 10+ violations

## Files Created/Modified

1. **Database**: `memory/index.db`
   - Added `violations` table
   - Added indexes for efficient querying

2. **Scripts**: `scripts/record-violation.sh`
   - Records violations with validation
   - Shows progressive warnings
   - Auto-creates CEO escalations

3. **Query System**: `query/query.py`
   - Added `get_violations()` method
   - Added `get_violation_summary()` method
   - Added `generate_accountability_banner()` function
   - CLI flags: `--violations`, `--accountability-banner`, `--violation-days`
   - Integrated violation stats into `--stats`

4. **Documentation**: `ACCOUNTABILITY_SYSTEM.md` (this file)

## Testing

System fully tested with:
- Single violation (NORMAL status)
- 3 violations (WARNING threshold)
- 5 violations (PROBATION threshold)
- 10 violations (CRITICAL threshold with CEO escalation)
- All progressive consequences verified
- CEO escalation file generation verified
- Database integration verified
- Query system integration verified

## Example Output

### Normal Status
```
╔═══════════════════════════════════════════════════════════════════════╗
║                    ACCOUNTABILITY TRACKING SYSTEM                     ║
║                     Golden Rule Violation Report                      ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Period: Last 7 days                                                     ║
║  Total Violations: 0                                                      ║
║  Status: NORMAL                                                       ║
║  Acceptable compliance level                                          ║
╠═══════════════════════════════════════════════════════════════════════╣
║  ✓  STATUS: Acceptable compliance. Keep up good practices.            ║
╚═══════════════════════════════════════════════════════════════════════╝
```

### Critical Status
```
╔═══════════════════════════════════════════════════════════════════════╗
║                    ACCOUNTABILITY TRACKING SYSTEM                     ║
║                     Golden Rule Violation Report                      ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Period: Last 7 days                                                     ║
║  Total Violations: 10                                                     ║
║  Status: CRITICAL                                                     ║
║  CEO ESCALATION REQUIRED                                              ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Violations by Rule:                                                  ║
║    Rule #4: Actively try to break your solution ( 5x) ║
║    Rule #2: Record failures while context is fr ( 3x) ║
╠═══════════════════════════════════════════════════════════════════════╣
║  ⚠️  CONSEQUENCES: CEO escalation auto-created in ceo-inbox/          ║
╚═══════════════════════════════════════════════════════════════════════╝
```
