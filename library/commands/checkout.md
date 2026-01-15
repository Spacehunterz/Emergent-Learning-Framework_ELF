# /checkout Command

**Record session learnings and complete the learning cycle.**

## Quick Start

```bash
/checkout
```

Type `/checkout` before closing your session to capture learnings.

## What It Does

The `/checkout` command:

1. **Detects Active Plans** - Lists any plans you started but haven't completed
2. **Completes Postmortems** - Records what actually happened vs. what was planned
3. **Captures Heuristics** - Saves reusable patterns you discovered
4. **Documents Failures** - Provides templates to record failures
5. **Saves Quick Notes** - Stores notes for next session continuity
6. **Displays Statistics** - Shows how much learning was captured

## The Learning Cycle

`/checkout` closes the learning loop:

```
Session Start
    ↓
/checkin (load context & golden rules)
    ↓
[Do work]
    ↓
/checkout (record learnings & notes)
    ↓
Session End
```

## Interactive Flow

### 1. Banner
Shows the checkout banner to signal session-end learning recording.

### 2. Active Plans Check
If you have any open plans:
```
[*] 2 active plan(s) found:
   [5] Refactor authentication (domain: backend)
   [6] Add analytics feature (domain: frontend)
```

### 3. Postmortem Completion
For each plan, you can complete it:
```
Complete postmortem for plan 5 (Refactor authentication)? [Y/n]: y
   Actual outcome: Completed 80% of original scope
   What diverged from plan? Discovery took longer
   What went well? Clean module structure
   What went wrong? Underestimated test complexity
   Key lessons? Always spike complex integrations first
```

The postmortem is recorded and linked to the plan.

### 4. Heuristic Discovery
Capture reusable patterns:
```
[*] Heuristic Discovery
   Did you discover any reusable patterns or rules? [Y/n]: y
   Domain: backend
   Rule: Always validate auth before database queries
   Explanation: Prevents unauthorized data access
   Confidence (0.0-1.0) [0.7]: 0.8
```

Stored in database + markdown for future reference.

### 5. Failure Documentation
Document any unexpected failures:
```
[*] Failure Documentation
   Did anything break or fail unexpectedly? [Y/n]: y
   [+] Guidance: Create a failure analysis file at:
       ~/.claude/emergent-learning/failure-analysis/YYYY-MM-DD-brief.md
```

Provides template for manual documentation.

### 6. Quick Notes
Save continuity notes:
```
[*] Quick Notes for Next Session
   > Remember: Add rate limiting to login endpoint
   [OK] Notes saved
```

Retrieved and displayed in next `/checkin`.

### 7. Session Summary
Displays what was recorded:
```
[=] Session Summary
   Postmortems recorded: 1
   Heuristics recorded: 2
   Failures documented: 0
   Notes saved: Yes
```

### 8. Complete
Final confirmation:
```
[OK] Checkout complete. Session learnings recorded!
```

## Examples

### Example 1: Complete a Plan

```bash
$ /checkout
[...banner...]
[*] 1 active plan(s) found:
   [3] Implement dark mode (domain: frontend)

Complete postmortem for plan 3 (Implement dark mode)? [Y/n]: y
   Actual outcome: Completed successfully
   What diverged from plan? Required CSS refactoring
   What went well? Component API is clean
   What went wrong? Color palette took iteration
   Key lessons? Design validation early with domain experts
   [OK] Postmortem recorded

[*] Heuristic Discovery
   Did you discover any reusable patterns? [Y/n]: y
   Domain: frontend
   Rule: Use CSS variables for consistent theming
   Explanation: Simplifies dark mode toggling
   Confidence [0.7]: 0.85
   [OK] Heuristic recorded

[*] Failure Documentation
   Did anything break? [Y/n]: n

[*] Quick Notes for Next Session
   > Move avatar colors to theme variables
   [OK] Notes saved

[=] Session Summary
   Postmortems recorded: 1
   Heuristics recorded: 1
   Failures documented: 0
   Notes saved: Yes

[OK] Checkout complete. Session learnings recorded!
```

### Example 2: No Plans, Just Learnings

```bash
$ /checkout
[...banner...]
[*] 0 active plan(s) found

[*] Heuristic Discovery
   Did you discover any reusable patterns? [Y/n]: y
   Domain: security
   Rule: Validate input at system boundaries
   Explanation: Prevents injection attacks
   Confidence [0.7]: 0.9
   [OK] Heuristic recorded

[*] Failure Documentation
   Did anything break? [Y/n]: y
   [+] Guidance: Create failure-analysis/2026-01-15-cache-invalidation.md

[*] Quick Notes for Next Session
   > Research: Redis cluster failover strategies
   [OK] Notes saved

[=] Session Summary
   Postmortems recorded: 0
   Heuristics recorded: 1
   Failures documented: 1
   Notes saved: Yes

[OK] Checkout complete. Session learnings recorded!
```

## How It Integrates

### With Plans & Postmortems
- Detects active plans from database
- Completes postmortems and marks plans as done
- Links postmortems to plans for analysis

### With Heuristics
- Records patterns to database + markdown
- Confidence tracking (0.0-1.0)
- Domain categorization
- Discoverable by `/search` and future sessions

### With Failure Analysis
- Guides creation of failure-analysis/*.md files
- Provides template structure
- Captures root causes and lessons

### With Session Notes
- Stores in ~/.checkout_notes
- Displayed in next `/checkin`
- Provides continuity across sessions

## Troubleshooting

### No active plans shown
Normal if you didn't create plans at session start. You can still record heuristics, failures, and notes.

### Database errors
If you see "[!] Warning: Could not detect active plans", the database may be unavailable. Continue with heuristics/failures/notes - they'll still be recorded.

### Postmortem didn't save
Check console output for errors. Ensure record-postmortem.py is accessible in scripts/ directory.

### Notes file error
If notes don't save, check file permissions on ~/.checkout_notes. The file will be created automatically on first write.

## Golden Rule #6

This command implements **Golden Rule #6: "Record Learnings Before Ending Session"**

- `/checkin` loads context (read)
- `/checkout` saves learnings (write)
- Together they close the learning cycle

## Related Commands

- `/checkin` - Load context before starting work
- `/search` - Find heuristics and learnings
- `/swarm` - Multi-agent coordination

## Files Involved

- Core: `src/query/checkout.py`
- Skill: `src/skills/elf-checkout/SKILL.md`
- Workflow: `.agent/workflows/checkout/workflow.md`
- State: `~/.claude/.elf_checkout_state`
- Notes: `~/.claude/.checkout_notes`
- Records: `memory/index.db` (plans, postmortems, heuristics)
- Markdown: `memory/heuristics/` (domain-specific files)

## More Information

See:
- `.agent/workflows/checkout/workflow.md` for detailed workflow spec
- `src/skills/elf-checkout/SKILL.md` for technical implementation
- `memory/golden-rules.md` for Golden Rule #6
