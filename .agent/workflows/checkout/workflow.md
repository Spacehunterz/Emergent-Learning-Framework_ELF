# Checkout Workflow Specification

## Overview

The `/checkout` workflow captures and records session learnings before ending work. It complements `/checkin` to complete the learning cycle defined by Golden Rule #6.

**Inputs:** None (triggered manually by user with `/checkout`)
**Outputs:**
- Recorded postmortems (linked to plans)
- Recorded heuristics (stored in database + markdown)
- Documented failures (guidance only)
- Session notes (for continuity)

---

## 8-Step Workflow

### Step 1: Display Banner
**Purpose:** Signal session-end learning recording

**Action:**
- Print ASCII art checkout banner
- Show "Closing Session, Recording Learnings..."

**Success Condition:** Banner printed to stdout

**Failure Handling:** Non-critical, continue to Step 2

---

### Step 2: Detect Active Plans
**Purpose:** Find any plans open during this session

**Action:**
```sql
SELECT id, title, domain, created_at
FROM plans
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 10
```

**Outputs:**
- `plans: List[dict]` - List of active plans or empty list

**Success Condition:** Database query returns (empty or with results)

**Failure Handling:**
- Show warning: "[!] Warning: Could not detect active plans"
- Set `plans = []`
- Continue to Step 3

---

### Step 3: Postmortem Prompt
**Condition:** Only if `plans` is non-empty

**Purpose:** Complete open plans with postmortem analysis

**Interactive Mode:**
1. Display: `[*] N active plan(s) found:`
2. List each plan: `   [id] title (domain: ...)`
3. For each plan, ask: `Complete postmortem for plan N? [Y/n]:`
4. If yes, collect:
   - `outcome` (required): "What actually happened"
   - `divergences`: "How did it differ from plan"
   - `went_well`: "What succeeded"
   - `went_wrong`: "What failed"
   - `lessons`: "Key takeaways"
5. Call: `record-postmortem.py --plan-id N --outcome "..." --lessons "..."`
6. Track: `learnings_recorded['postmortems'] += 1` per successful record

**Non-Interactive Mode:**
- For each plan, emit: `[PROMPT_NEEDED] {"type": "postmortem", "plan_id": N, "title": "..."}`
- Let Claude handle via AskUserQuestion

**Success Condition:** User completes or skips all postmortems

**Failure Handling:**
- If record-postmortem.py fails: Show "[!] Failed to record postmortem", continue
- If subprocess times out: Show warning, continue
- Allow EOFError/KeyboardInterrupt to break loop gracefully

---

### Step 4: Heuristic Discovery
**Purpose:** Capture reusable patterns learned

**Interactive Mode:**
1. Display: `[*] Heuristic Discovery`
2. Ask: `Did you discover any reusable patterns or rules? [Y/n]:`
3. If no: Skip to Step 5
4. If yes, collect:
   - `domain` (required): e.g., "backend", "react", "security"
   - `rule` (required): The heuristic as imperative statement
   - `explanation`: Why it matters
   - `confidence`: 0.0-1.0 (default 0.7)
5. Call: `record-heuristic.py --domain D --rule R --explanation E --confidence C`
6. Track: `learnings_recorded['heuristics'] += 1`

**Non-Interactive Mode:**
- Emit: `[PROMPT_NEEDED] {"type": "heuristic"}`
- Let Claude collect via AskUserQuestion and call record-heuristic.py

**Success Condition:** User provides heuristic or skips

**Failure Handling:**
- If domain empty: Show "Skipped"
- If rule empty: Show "Skipped"
- If record-heuristic.py fails: Show error, continue
- Allow EOFError/KeyboardInterrupt

---

### Step 5: Failure Documentation
**Purpose:** Capture failures for learning

**Interactive Mode:**
1. Display: `[*] Failure Documentation`
2. Ask: `Did anything break or fail unexpectedly? [Y/n]:`
3. If no: Skip to Step 6
4. If yes, show guidance:
   ```
   [+] Create file: ~/.claude/emergent-learning/failure-analysis/YYYY-MM-DD-brief.md

   Template:
   # Failure Analysis: [Brief Description]
   **Date:** YYYY-MM-DD
   **Context:** [What you were attempting]

   ## What Went Wrong
   [Detailed description]

   ## Root Cause
   [Why it failed]

   ## Lesson Learned
   [Portable knowledge]
   ```
5. Track: `learnings_recorded['failures'] += 1`

**Non-Interactive Mode:**
- Emit: `[PROMPT_NEEDED] {"type": "failure"}`
- Let Claude ask and provide guidance

**Success Condition:** User acknowledges guidance or skips

**Failure Handling:**
- Non-critical (no automated recording)
- EOFError/KeyboardInterrupt handled gracefully

---

### Step 6: Quick Notes
**Purpose:** Capture continuity notes for next session

**Interactive Mode:**
1. Display: `[*] Quick Notes for Next Session`
2. Prompt: `> ` (free-text input)
3. If provided:
   - Store in `~/.claude/.checkout_notes`
   - Append: `[timestamp] {notes}`
   - Track: `learnings_recorded['notes'] = True`
4. If empty: Skip (don't track)

**Non-Interactive Mode:**
- Emit: `[PROMPT_NEEDED] {"type": "notes"}`
- Let Claude collect via AskUserQuestion

**Success Condition:** Notes stored or skipped

**Failure Handling:**
- If file write fails: Show "[!] Could not save notes: {e}"
- Continue to Step 7

---

### Step 7: Session Statistics
**Purpose:** Display learning capture summary

**Output:**
```
[=] Session Summary
   Postmortems recorded: N
   Heuristics recorded: N
   Failures documented: N
   Notes saved: Yes/No
```

**Success Condition:** Statistics displayed

**Failure Handling:** Non-critical, continue to Step 8

---

### Step 8: Complete
**Purpose:** Signal successful completion

**Output:**
```
[OK] Checkout complete. Session learnings recorded!
```

**State Update:**
- Save to `~/.claude/.elf_checkout_state`:
  ```json
  {
    "last_checkout": "2026-01-15T14:30:00",
    "learnings_recorded": {
      "postmortems": 1,
      "heuristics": 2,
      "failures": 0,
      "notes": true
    }
  }
  ```

**Success Condition:** Exit code 0

**Failure Handling:** Exit code 1 if critical error (e.g., database unavailable)

---

## State Management

### State File: `~/.claude/.elf_checkout_state`

```json
{
  "last_checkout": "2026-01-15T14:30:00",
  "learnings_recorded": {
    "postmortems": 1,
    "heuristics": 2,
    "failures": 0,
    "notes": true
  }
}
```

**Usage:**
- Load on `__init__`
- Update at end of `run()`
- Track cumulative learnings across sessions

---

## Error Handling Strategy

### Database Errors
- **Condition:** SQLite connection fails
- **Action:** Print warning, continue without stopping
- **Impact:** Steps 2-3 skipped, continue to Step 4

### Subprocess Failures
- **Condition:** record-*.py returns non-zero exit code
- **Action:** Print error message, continue
- **Impact:** Individual learning not recorded, continue

### IO Errors (file operations)
- **Condition:** Cannot read/write files
- **Action:** Print error, continue
- **Impact:** Notes not saved, continue

### Timeout
- **Condition:** Subprocess takes >30 seconds
- **Action:** Raise subprocess.TimeoutExpired, catch and warn
- **Impact:** Record not made, continue

### EOFError / KeyboardInterrupt
- **Condition:** User presses Ctrl+C or no more input
- **Action:** Break from current loop, continue to next step
- **Impact:** Graceful exit from current prompt

### Critical Errors
- **Condition:** Cannot resolve ELF home, cannot parse arguments
- **Action:** Print to stderr, exit(1)
- **Impact:** Workflow stops

---

## Non-Interactive Mode Hints

Emitted as `[PROMPT_NEEDED] {json}` in stdout:

```python
# Postmortem for each active plan
[PROMPT_NEEDED] {"type": "postmortem", "plan_id": 5, "title": "Refactor auth"}

# Heuristic discovery
[PROMPT_NEEDED] {"type": "heuristic"}

# Failure documentation
[PROMPT_NEEDED] {"type": "failure"}

# Quick notes
[PROMPT_NEEDED] {"type": "notes"}
```

**Claude's Response:**
1. Recognize `[PROMPT_NEEDED]` pattern
2. Parse JSON to identify prompt type
3. Use `AskUserQuestion` tool to collect response
4. Call appropriate record-*.py script with collected data
5. Continue workflow

---

## Exit Codes

- **0:** Successful completion (all steps executed)
- **1:** Critical error (cannot proceed)

---

## Cross-Platform Considerations

- **Path handling:** Use `Path()` for cross-platform compatibility
- **Subprocess:** Use `subprocess.run()` with proper argument handling
- **Database:** SQLite works on all platforms
- **File I/O:** UTF-8 encoding with proper error handling

---

## Testing Checklist

### Unit Tests
- [ ] Display banner without errors
- [ ] Detect plans query returns empty list or data
- [ ] Postmortem subprocess called with correct arguments
- [ ] Heuristic subprocess called with correct arguments
- [ ] Notes written to file correctly
- [ ] State file saved and loaded correctly

### Integration Tests
- [ ] No active plans → continues without Step 3
- [ ] Multiple active plans → processes all
- [ ] Postmortem marks plan as completed
- [ ] Heuristic appears in markdown + database
- [ ] Notes persist across sessions

### Edge Cases
- [ ] Database file doesn't exist
- [ ] Database locked by another process
- [ ] File permissions prevent writing notes
- [ ] User cancels with Ctrl+C
- [ ] Subprocess hangs (timeout)
- [ ] Empty user input (just Enter)

### End-to-End
- [ ] Run `/checkout` in Claude Code chat
- [ ] Complete full workflow via AskUserQuestion
- [ ] Verify all data persisted
- [ ] Run `/checkin` → verify notes displayed
