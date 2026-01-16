---
name: checkout
description: Record session learnings before closing. Prompts for postmortems, heuristics, failures, and notes to complete the learning cycle. Complements /checkin to enforce Golden Rule #6.
license: MIT
---

# ELF Checkout Command

Interactive workflow to capture and record session learnings before closing work.

## What It Does

The `/checkout` command:
- Detects any active plans and offers to complete them with postmortems
- Prompts for heuristics discovered during the session
- Offers to document any failures or unexpected issues
- Collects quick notes for continuity in next session
- Displays session statistics
- Enforces Golden Rule #6: "Record Learnings Before Ending Session"

## Usage

```bash
/checkout
```

Simple - just type `/checkout` before closing your session to capture learnings.

## Execution

This skill runs the Python-based orchestrator in non-interactive mode:

```bash
python ~/.claude/emergent-learning/src/query/checkout.py --non-interactive
```

### Handling Non-Interactive Mode

The `--non-interactive` flag tells the script to output `[PROMPT_NEEDED]` JSON hints
instead of blocking on `input()`. When you see these in the output:

1. **Postmortem prompt**: `[PROMPT_NEEDED] {"type": "postmortem", "plan_id": ..., "title": "..."}`
   - Use `AskUserQuestion` tool to ask about completing the plan
   - Collect: actual outcome, divergences, what went well, what went wrong, lessons
   - If provided, call record-postmortem.py with the collected data

2. **Heuristic prompt**: `[PROMPT_NEEDED] {"type": "heuristic"}`
   - Use `AskUserQuestion` tool to ask: "Did you discover reusable patterns?"
   - If yes, collect: domain, rule, explanation, confidence
   - Call record-heuristic.py with the data

3. **Failure prompt**: `[PROMPT_NEEDED] {"type": "failure"}`
   - Use `AskUserQuestion` tool to ask: "Any failures to document?"
   - If yes, provide guidance on creating failure-analysis/*.md file

4. **Heuristic validation prompt**: `[PROMPT_NEEDED] {"type": "heuristic_validation", "heuristics": [...]}`
   - Use `AskUserQuestion` tool to ask about validating/violating displayed heuristics
   - Record validation/violation to update confidence scores

5. **Suggested heuristics prompt**: `[PROMPT_NEEDED] {"type": "suggested_heuristics", "suggestions": [...]}`
   - Use `AskUserQuestion` tool to ask which auto-detected patterns to record
   - Call record-heuristic.py for selected suggestions

6. **Notes prompt**: `[PROMPT_NEEDED] {"type": "notes"}`
   - Use `AskUserQuestion` tool to ask: "Quick notes for next session?"
   - Store notes for continuity

The orchestrator is a complete 11-step workflow:
- Step 0: Session analysis (auto - analyzes session data)
- Step 1: Display checkout banner + session summary
- Step 2: Detect active plans
- Step 3: Postmortem prompt (if plans exist)
- Step 4: Heuristic validation (review relevant heuristics)
- Step 5: Auto-detected patterns (suggest potential heuristics)
- Step 6: Heuristic discovery prompt (manual)
- Step 7: Failure documentation prompt
- Step 8: Quick notes collection
- Step 9: Session statistics
- Step 10: Complete

## Workflow Steps (11-Step Structured Process)

### Step 0: Session Analysis (auto) ✓
Automatically analyze session data before prompting user
- Reads current session JSONL file
- Counts tool usage patterns
- Detects domains worked on
- Identifies repeated patterns (3+ occurrences)
- Generates heuristic suggestions based on patterns

### Step 1: Display Banner ✓
Show checkout ASCII art to signal session-end learning recording
- **Always shown** on every checkout
- **Signals** that learning capture is beginning
- Displays session analysis summary (domains, tool usage, patterns)

### Step 2: Detect Active Plans ✓
Query the database for any active plans
- Lists all plans with status='active'
- Shows plan title, ID, and domain
- If none found, continues to next step

### Step 3: Postmortem Prompt ⚡
For each active plan, offer to complete with postmortem
- **Only if plans exist**
- Collects: actual outcome (required), divergences, what went well/wrong, lessons
- Links postmortem to plan and marks plan as completed
- Calls record-postmortem.py for each completed plan

### Step 4: Heuristic Validation ⚡ (NEW)
Review existing heuristics relevant to today's work
- Queries heuristics matching detected domains
- Displays relevant rules with confidence scores
- User can validate (confirm worked) or violate (didn't apply)
- Updates confidence scores based on feedback

### Step 5: Auto-Detected Patterns ⚡ (NEW)
Present auto-detected patterns as potential heuristics
- Shows patterns from session analysis
- Suggests heuristics based on tool usage patterns
- User can choose to record any as new heuristics
- Recorded with 0.5 confidence and 'auto-detected' source

### Step 6: Heuristic Discovery ⚡
Ask if any reusable patterns or rules were discovered
- "Did you discover any reusable patterns or rules?"
- If yes: collect domain, rule, explanation, confidence level
- Calls record-heuristic.py to store in database + markdown

### Step 7: Failure Documentation ⚡
Ask about any unexpected failures or breakages
- "Did anything break or fail unexpectedly?"
- If yes: provide template and guidance for failure-analysis/*.md
- Shows markdown template for users to complete manually

### Step 8: Quick Notes ⚡
Collect brief notes for continuity in next session
- "Any quick notes for next session?"
- Optional free-text input
- Stored in ~/.checkout_notes for future reference

### Step 9: Session Statistics ✓
Display summary of learning captured this session
- Postmortems recorded count
- Heuristics recorded count
- Heuristics validated/violated counts (if any)
- Failures documented count
- Notes saved (yes/no)

### Step 10: Complete ✓
Print completion message
- "Checkout complete. Session learnings recorded!"
- Marks checkout as done (state file)

## Key Improvements (Addresses Golden Rule #6)

✅ **Tooling Support** - Prompts users to record learnings (not just documentation)
✅ **Plan Completion** - Links postmortems to active plans and marks completed
✅ **Structured Capture** - All 8 steps executed in proper sequence
✅ **Non-Interactive Mode** - Works in Claude Code chat via JSON hints
✅ **Integration** - Calls existing record-*.py scripts for data persistence
✅ **State Tracking** - Uses ~/.elf_checkout_state to track completion

## Interactive Prompts

### Active Plans Detection
```
[*] 2 active plan(s) found:
   [5] Refactor authentication (domain: backend)
   [6] Add analytics feature (domain: frontend)
```

### Postmortem Prompt (if plans exist)
```
Complete postmortem for plan 5 (Refactor authentication)? [Y/n]: y
   Actual outcome: Completed with 80% test coverage
   What diverged from plan? Took longer due to integration complexity
   What went well? Clean module architecture achieved
   What went wrong? Underestimated test scope
   Key lessons? Always spike complex integrations first

   [OK] Postmortem recorded
```

### Heuristic Prompt
```
[*] Heuristic Discovery
   Did you discover any reusable patterns or rules? [Y/n]: y
   Domain: backend
   Rule (the heuristic): Always validate auth tokens before database queries
   Explanation: Prevents unauthorized data access vulnerabilities
   Confidence (0.0-1.0) [0.7]: 0.85

   [OK] Heuristic recorded
```

### Failure Prompt
```
[*] Failure Documentation
   Did anything break or fail unexpectedly? [Y/n]: y
   [+] Guidance: Create a failure analysis file at:
       ~/.claude/emergent-learning/failure-analysis/YYYY-MM-DD-brief-description.md
```

### Notes Prompt
```
[*] Quick Notes for Next Session
   > Add rate limiting to login endpoint - check quota service
   [OK] Notes saved
```

### Session Summary
```
[=] Session Summary
   Postmortems recorded: 1
   Heuristics recorded: 2
   Failures documented: 0
   Notes saved: Yes
```

## Integration with Learning System

The checkout workflow closes the learning cycle:
- **Plans** - Postmortems link to plans and mark completion
- **Heuristics** - Patterns stored in database + markdown (memory/heuristics/)
- **Failures** - Documented manually in failure-analysis/ directory
- **Notes** - Quick continuity stored for next session

Checkout + Checkin form a complete loop:
```
/checkin (load context)
  ↓
[Work & Learn]
  ↓
/checkout (record learnings)
  ↓
[Next session]
  ↓
/checkin (load context + last session notes)
```

## Complementing /checkin

While `/checkin` is load-only, `/checkout` is save-only:

| Operation | Command | Status |
|-----------|---------|--------|
| Load context at session start | `/checkin` | ✓ |
| Prompt to record learnings at session end | `/checkout` | ✓ |
| Complete learning cycle | Both | ✓ |

## Cross-Platform Support

Works on:
- ✅ Windows (PowerShell, MSYS)
- ✅ WSL (Windows Subsystem for Linux)
- ✅ macOS
- ✅ Linux

No platform-specific dependencies - pure Python with standard library.

## Error Handling

The checkout workflow handles common errors gracefully:
- **Database not accessible**: Shows warning, continues to next step
- **Record scripts fail**: Shows error, allows user to continue or retry
- **EOF/Interrupt**: Allows graceful cancellation
- **Missing ELF home**: Uses fallback discovery mechanism

## Success Criteria

✓ Checkout runs without errors
✓ Active plans detected and listed
✓ Postmortems link to plans correctly
✓ Heuristics stored in database + markdown files
✓ Session stats display accurately
✓ Works in non-interactive mode (Claude Code chat)
✓ State tracked for conversation continuity
