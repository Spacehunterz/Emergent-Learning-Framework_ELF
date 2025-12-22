# Opus Handler Implementation Specification

## Overview

The Opus Handler is Tier 2 of the Tiered Watcher Pattern. It provides intelligent intervention when multi-agent coordination encounters issues that require higher-level reasoning.

## Architecture

### Activation Trigger
- **ONLY** activates when `.coordination/escalate.md` appears
- Dormant otherwise (no polling, no resource usage)
- Can run in two modes:
  - One-shot: Check once and exit
  - Watch: Poll at intervals (default 30s)

### Decision Framework

The handler makes ONE of five decisions:

1. **reassign** - Reassign failed task to new agent
   - When: Agent failed without producing useful output
   - Action: Mark agent as failed, add task back to queue

2. **restart** - Restart the stalled/failed agent
   - When: Agent appears stuck/timeout but likely recoverable
   - Action: Clear state, re-queue task with fresh state

3. **abort** - Abort the task and mark as failed
   - When: Multiple failures detected (>= 3 failed agents)
   - Action: Mark all tasks as aborted, escalate to CEO

4. **synthesize** - Gather partial results and continue
   - When: Agent failed but produced partial outputs
   - Action: Collect outputs, create synthesis task

5. **escalate_ceo** - Problem requires human intervention
   - When: Conflict, deadlock, or ambiguous situations
   - Action: Write detailed escalation to ceo-inbox/

### Context Gathering

Before making a decision, the handler gathers:

1. **Escalation details** from `escalate.md`:
   - escalation_id
   - reason
   - trigger
   - raw_content

2. **Blackboard state** from `blackboard.json`:
   - All agent states
   - Task queue
   - Findings and messages

3. **Watcher log** (last 20 entries) from `watcher-log.md`:
   - Recent events
   - Previous interventions

4. **Worker outputs** from `.coordination/agent_*.md`:
   - Partial results
   - Completion reports

### Decision Heuristics

The handler uses conservative heuristics (in priority order):

1. **Timeout/Stuck** → RESTART
   - Least disruptive
   - Most likely to recover

2. **Error with outputs** → SYNTHESIZE
   - Preserves partial work
   - Allows continuation

3. **Error without outputs** → REASSIGN
   - Fresh attempt likely to succeed
   - Different agent may have better luck

4. **Conflict/Deadlock** → ESCALATE_CEO
   - Requires human judgment
   - Too risky for automated decision

5. **Multiple failures** → ABORT
   - Prevents resource waste
   - Escalates for process review

6. **Default/Unclear** → SYNTHESIZE
   - Conservative approach
   - Gathers what's available

### Execution Flow

```
1. Check for escalate.md
   ↓
2. Read and parse escalation
   ↓
3. Gather full context
   ↓
4. Make decision (heuristic-based)
   ↓
5. Write decision to decision.md
   ↓
6. Execute decision:
   - Update blackboard.json
   - Modify task_queue
   - Write CEO escalation if needed
   ↓
7. Cleanup:
   - Archive escalate.md
   - Update watcher-log.md
   ↓
8. Return to dormant state
```

### File Operations

**Reads:**
- `.coordination/escalate.md` (trigger)
- `.coordination/blackboard.json` (state)
- `.coordination/watcher-log.md` (history)
- `.coordination/agent_*.md` (worker outputs)

**Writes:**
- `.coordination/decision.md` (decision record)
- `.coordination/blackboard.json` (updated state)
- `.coordination/watcher-log.md` (intervention log)
- `ceo-inbox/YYYY-MM-DD-watcher-escalation-*.md` (CEO escalations)

**Archives:**
- `.coordination/archive/escalations/escalate-TIMESTAMP.md`

### Integration Points

1. **With Haiku Watcher:**
   - Haiku creates `escalate.md` when it needs help
   - Opus reads it, decides, executes, archives it

2. **With Conductor:**
   - Reads/writes `blackboard.json` for agent state
   - Updates `task_queue` for task reassignment/restart

3. **With CEO (Human):**
   - Writes detailed escalations to `ceo-inbox/`
   - Includes all context for human decision-making

### Error Handling

- Graceful degradation (missing files → empty dicts/lists)
- Logging to stderr for debugging
- Timeout handling (configurable via --timeout)
- Missing file tolerance (doesn't crash on absent files)

### CLI Interface

```bash
# One-shot check
python opus_handler.py

# Watch mode (poll every 30s)
python opus_handler.py --watch

# Custom interval (poll every 60s)
python opus_handler.py --watch --interval 60

# With timeout (watch for max 600s)
python opus_handler.py --watch --timeout 600

# Custom coordination directory
python opus_handler.py --coordination-dir /path/to/.coordination
```

### Exit Codes

- `0`: Success (escalation handled or no escalation found)
- Non-zero: Error during execution

### Logging

All logs go to stderr in format:
```
[YYYY-MM-DD HH:MM:SS] [OPUS] <message>
[YYYY-MM-DD HH:MM:SS] [OPUS] ERROR: <error>
```

Additionally logs to `.coordination/watcher-log.md` for historical tracking.

## Implementation Status

**File:** `opus_handler.py` (currently 89 lines - PLACEHOLDER)

**Required:** ~750 lines (comparable to haiku_watcher.py: 336 lines)

**Structure:**
- `Decision` enum (5 types)
- `OpusHandler` class with methods:
  - `check_escalation()` → bool
  - `read_escalation()` → Dict
  - `read_blackboard()` → Dict
  - `read_watcher_log()` → List[str]
  - `gather_context()` → Dict
  - `make_decision()` → Tuple[Decision, str, List[str]]
  - `write_decision()` → None
  - `execute_decision()` → bool
  - `_execute_reassign()` → bool
  - `_execute_restart()` → bool
  - `_execute_abort()` → bool
  - `_execute_synthesize()` → bool
  - `_execute_escalate_ceo()` → bool
  - `_save_blackboard()` → None
  - `cleanup()` → None
  - `_update_watcher_log()` → None
  - `_log()` → None
  - `_log_error()` → None
  - `handle_once()` → bool
  - `watch()` → None
- `main()` function (argparse CLI)

## Testing

To test the Opus Handler:

1. **Create test escalation:**
   ```bash
   cat > ~/.claude/emergent-learning/.coordination/escalate.md << 'EOF'
   # Escalation: test-001

   **Reason:** Agent timeout during test
   **Trigger:** stuck

   Agent test-agent has been stuck for 60 seconds.
   EOF
   ```

2. **Run handler:**
   ```bash
   cd ~/.claude/emergent-learning/watcher
   python opus_handler.py
   ```

3. **Verify:**
   - Check `.coordination/decision.md` created
   - Check `.coordination/archive/escalations/` has archived escalation
   - Check `.coordination/watcher-log.md` has intervention log
   - Check blackboard.json updated (if applicable)

## Future Enhancements

- [ ] Real Opus API integration for decision-making
- [ ] Machine learning from past interventions
- [ ] Confidence scores for decisions
- [ ] Multi-escalation batching
- [ ] Decision explanation improvements

---

**Agent 3 Task:** Implement the full opus_handler.py based on this specification.

**Estimated LOC:** ~750 lines
**Dependencies:** Standard library only (json, sys, time, argparse, pathlib, datetime, typing, enum)
**Complexity:** Moderate (similar to haiku_watcher.py but with more decision logic)
