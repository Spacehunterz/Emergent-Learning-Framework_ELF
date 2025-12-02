# Quick Start: Meta-Learning Capabilities

The Emergent Learning Framework now has comprehensive meta-learning capabilities. Here's how to use them.

## Daily Operations

### Check System Health
```bash
~/.claude/emergent-learning/scripts/self-test.sh
```

This runs 11 comprehensive tests and automatically records any issues found.

### View Learning Metrics
```bash
# Quick view
~/.claude/emergent-learning/scripts/learning-metrics.sh

# Detailed breakdown
~/.claude/emergent-learning/scripts/learning-metrics.sh --detailed

# JSON output for automation
~/.claude/emergent-learning/scripts/learning-metrics.sh --json
```

Tracks:
- Learnings per day/week/month
- Heuristic promotion rate
- Domain activity
- Learning acceleration trends

### Check for Duplicates
```bash
# Quick stats
~/.claude/emergent-learning/scripts/deduplicate-failures.sh --stats

# Full analysis
~/.claude/emergent-learning/scripts/deduplicate-failures.sh --all

# Generate report
~/.claude/emergent-learning/scripts/deduplicate-failures.sh --report
```

### Get Heuristic Suggestions
```bash
# Quick analysis
~/.claude/emergent-learning/scripts/suggest-heuristics.sh --stats

# Analyze recent failures
~/.claude/emergent-learning/scripts/suggest-heuristics.sh --recent 7

# Generate full opportunities report
~/.claude/emergent-learning/scripts/suggest-heuristics.sh --report

# Interactive heuristic generation
~/.claude/emergent-learning/scripts/suggest-heuristics.sh --generate
```

## Weekly Reviews

Run these once a week to maintain system health:

```bash
# 1. Self-test
~/.claude/emergent-learning/scripts/self-test.sh

# 2. Detailed metrics
~/.claude/emergent-learning/scripts/learning-metrics.sh --detailed

# 3. Heuristic opportunities
~/.claude/emergent-learning/scripts/suggest-heuristics.sh --report

# 4. Deduplication check
~/.claude/emergent-learning/scripts/deduplicate-failures.sh --report
```

## Troubleshooting

### System Corrupted or Database Missing

```bash
~/.claude/emergent-learning/scripts/bootstrap-recovery.sh
```

This will:
1. Create a backup of current state
2. Fix missing directories
3. Rebuild database from markdown files
4. Validate recovery

### Check Dependencies

```bash
~/.claude/emergent-learning/scripts/dependency-check.sh
```

Validates:
- No circular imports
- All external dependencies present
- System can safely monitor itself

## What Each Tool Does

### self-test.sh
**Can the system detect its own bugs?**
- Tests directory structure, database integrity, file-DB sync
- Validates scripts are executable
- Checks for circular dependencies
- Auto-records failures found

### learning-metrics.sh
**How fast is the system learning?**
- Learnings per day average
- Success/failure ratios
- Heuristic promotion rate
- Learning acceleration trends
- Domain activity distribution

### dependency-check.sh
**Are there circular dependencies?**
- Python import validation
- Shell script sourcing validation
- Generates dependency graph
- Proves system can monitor itself safely

### bootstrap-recovery.sh
**Can the system recover from corruption?**
- Rebuilds database from markdown
- Fixes missing directories
- Restores golden rules
- Auto-fixes common issues

### deduplicate-failures.sh
**Are we recording duplicates?**
- Exact duplicate detection
- Similarity scoring (domain + title + tags)
- Pre-record deduplication checks
- Improves signal-to-noise ratio

### suggest-heuristics.sh
**What heuristics should we extract?**
- Analyzes failure patterns by domain
- Auto-generates heuristic drafts
- Suggests promotion of validated heuristics
- Identifies domains without coverage

## Integration with Agent Workflow

When agents query the building:
```bash
python ~/.claude/emergent-learning/query/query.py --context
```

They should periodically check meta-learning insights:
```bash
# Check if system is healthy
~/.claude/emergent-learning/scripts/self-test.sh

# View recent learning trends
~/.claude/emergent-learning/scripts/learning-metrics.sh

# Get heuristic opportunities
~/.claude/emergent-learning/scripts/suggest-heuristics.sh --recent 7
```

## Key Metrics to Watch

### Learning Velocity
- **Good:** >5 learnings/day on active projects
- **Warning:** <1 learning/day (system not being used)
- **Monitor:** Week-over-week acceleration

### Heuristic Coverage
- **Good:** All failure domains have corresponding heuristics
- **Warning:** Domains with 3+ failures but no heuristics
- **Action:** Use suggest-heuristics.sh to generate drafts

### Deduplication
- **Good:** >90% uniqueness rate
- **Warning:** Multiple exact duplicates
- **Action:** Review recording process

### Promotion Rate
- **Good:** Heuristics with 3+ validations promoted to golden rules
- **Warning:** Many heuristics, few golden rules
- **Action:** Review validation tracking

## Advanced Usage

### Automated Daily Health Check
Add to cron or scheduled tasks:
```bash
0 9 * * * ~/.claude/emergent-learning/scripts/self-test.sh >> ~/daily-health.log 2>&1
```

### Weekly Summary Email
```bash
0 9 * * 1 ~/.claude/emergent-learning/scripts/learning-metrics.sh --detailed | mail -s "Weekly Learning Summary" you@example.com
```

### Continuous Monitoring
```bash
# Run metrics in JSON mode and feed to monitoring system
~/.claude/emergent-learning/scripts/learning-metrics.sh --json | your-monitoring-tool
```

## Understanding the Output

### Self-Test
```
✓ PASS: All checks passed
✗ FAIL: Issue detected (automatically recorded to building)
⚠ WARN: Non-critical issue
```

### Learning Metrics
```
Total learnings: 82          # All records in system
Total failures: 75           # Failures recorded
Total successes: 7           # Successes recorded
Heuristic promotion rate: 2% # Percentage of heuristics that became golden rules
Average per day (7d): 11.29  # Recent learning velocity
```

### Deduplication
```
Uniqueness rate: 93%         # Good (>90%)
Duplicate titles: 5          # Potential consolidation opportunities
Similar (75%): [ID] <-> [ID] # High similarity, consider merging
```

### Heuristic Suggestions
```
Domain: testing (23 failures) - HIGH PRIORITY
Common themes: error, timeout, connection
★ Strongly recommend creating a heuristic
```

## Best Practices

1. **Run self-test daily** - Catches issues early
2. **Review metrics weekly** - Track progress and trends
3. **Check heuristic suggestions monthly** - Extract learnings
4. **Monitor deduplication quarterly** - Prevent knowledge bloat
5. **Keep backups** - Bootstrap recovery creates them automatically

## What's Different Now?

**Before Meta-Learning:**
- No way to detect system bugs
- Unknown learning velocity
- Potential circular dependency issues
- Manual recovery from corruption
- Duplicate failures not detected
- Heuristic extraction manual and ad-hoc

**After Meta-Learning:**
- Self-test detects and records bugs automatically
- Metrics show exact learning velocity and trends
- Dependency checker validates safe architecture
- Bootstrap recovery script handles corruption
- Deduplication prevents redundant failures
- Heuristic suggestions automated from patterns

**The system can now improve itself.**

## Questions?

See full documentation in `META_LEARNING_REPORT.md`

All scripts have `--help` flags:
```bash
~/.claude/emergent-learning/scripts/self-test.sh --help
~/.claude/emergent-learning/scripts/learning-metrics.sh --help
# etc.
```

---

**Created:** 2025-12-01
**By:** Opus Agent J (Meta-Learning Specialist)
**Status:** Production Ready
