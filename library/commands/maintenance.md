# ELF Database Maintenance

Run comprehensive database maintenance to keep all ELF systems healthy and populated.

## What It Does

1. **Fraud Detection** - Analyzes recently modified heuristics for manipulation patterns
2. **Session Summaries** - Summarizes unsummarized sessions to database
3. **Domain Baselines** - Refreshes stale domain baselines (>7 days old)
4. **Context Cleanup** - Removes session contexts older than 7 days
5. **Postmortem Generation** - Auto-creates postmortems for completed/failed workflows
6. **CEO Reviews** - Creates review items for drift alerts, fraud reports, violations

## Usage

Run the maintenance script:
```bash
python ~/.claude/emergent-learning/scripts/maintenance.py
```

### Options

- `--dry-run` - Show what would be done without making changes
- `--fraud` - Run fraud detection only
- `--sessions` - Run session summaries only
- `--baselines` - Run baseline refresh only
- `--postmortems` - Run postmortem generation only
- `--json` - Output results as JSON
- `--quiet` - Suppress progress output

## When to Run

- After extended coding sessions
- When database tables seem stale
- Before important checkins
- Periodically (recommended: daily)

## Example Output

```
==================================================
ELF Database Maintenance
==================================================

[1/6] Fraud Detection
------------------------------
  Found 5 heuristics to check
  Checked: 5, Flagged: 0

[2/6] Session Summaries
------------------------------
  Found 3 unsummarized sessions
  Summarized: 3/3

[3/6] Domain Baselines
------------------------------
  Found 2 domains needing refresh
  Refreshed: 2/2

[4/6] Context Cleanup
------------------------------
  Found 15 old context records
  Deleted: 15 old contexts

[5/6] Postmortem Generation
------------------------------
  Found 2 workflows needing postmortems
  Created: 2/2

[6/6] CEO Review Creation
------------------------------
  Found 3 issues needing review
    - Drift alerts: 1
    - Fraud reports: 1
    - Invariant violations: 1
  Created: 3 CEO reviews

==================================================
Maintenance Complete
==================================================
```
