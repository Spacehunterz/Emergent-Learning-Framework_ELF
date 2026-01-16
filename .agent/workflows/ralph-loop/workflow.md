# Ralph Loop Workflow

## Overview

The Ralph Wiggum Loop runs as a **Git pre-commit hook** and implements an iterative code improvement pattern:

1. User runs `git commit` with staged code changes
2. **Pre-commit hook triggers** automatically
3. **Code Reviewer** analyzes staged files and identifies issues
4. **Code Simplifier** refactors code based on findings
5. Loop repeats (max 2 iterations - pre-commit is fast)
6. If improvements made: commit is blocked, user stages improvements, tries again
7. When code is stable: commit succeeds

Uses **blackboard architecture** via `.coordination/ralph-loop/` for agent communication.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Ralph Loop Orchestrator (ralph_orchestrator.py)             │
└─────────────────────────────────────────────────────────────┘
                           │
                  ┌────────┴────────┐
                  │                 │
         ┌────────▼────────┐  ┌────▼────────────┐
         │  Code Reviewer  │  │ Code Simplifier │
         │    (Agent)      │  │    (Agent)      │
         └────────┬────────┘  └────┬────────────┘
                  │                │
                  └────────┬────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │   Blackboard (.coordination/)       │
        │                                     │
        │  - review-input.json                │
        │  - review-findings.json             │
        │  - simplify-input.json              │
        │  - simplified-code.json             │
        │  - status.json                      │
        └─────────────────────────────────────┘
```

---

## Handoff Protocol

### Phase 1: Code Reviewer Analysis

**Orchestrator writes:**
```json
// .coordination/ralph-loop/review-input.json
{
  "iteration": 1,
  "action": "review",
  "code": "/* code to review */",
  "timestamp": 1705334400
}
```

**Code Reviewer writes back:**
```json
// .coordination/ralph-loop/review-findings.json
{
  "iteration": 1,
  "issues": [
    {
      "type": "complexity",
      "location": "line 42",
      "description": "Function is too long",
      "severity": "medium"
    }
  ],
  "summary": "Found 3 issues: 2 medium, 1 low",
  "timestamp": 1705334410
}
```

### Phase 2: Code Simplifier Refactor

**Orchestrator writes:**
```json
// .coordination/ralph-loop/simplify-input.json
{
  "iteration": 1,
  "action": "simplify",
  "code": "/* original code */",
  "review_findings": { /* findings from phase 1 */ },
  "timestamp": 1705334420
}
```

**Code Simplifier writes back:**
```json
// .coordination/ralph-loop/simplified-code.json
{
  "iteration": 1,
  "code": "/* refactored code */",
  "changes": [
    {
      "type": "extract_function",
      "before_lines": "40-60",
      "after_lines": "40-45"
    }
  ],
  "summary": "Extracted helper function, reduced complexity",
  "timestamp": 1705334430
}
```

### Phase 3: Loop Decision

**Orchestrator status:**
```json
// .coordination/ralph-loop/status.json
{
  "target": "/path/to/file.ts",
  "iterations": [
    {
      "iteration": 1,
      "timestamp": 1705334430,
      "issues_found": 3,
      "refactored": true
    }
  ],
  "current_iteration": 1,
  "status": "running",
  "started_at": 1705334400
}
```

---

## State Transitions

```
initialized → running → (loop)
                         ↓
                    reviewer ──→ findings
                         ↑          ↓
                         └─ simplifier ──→ code

                    repeat if:
                    - code changed
                    - iteration < max

                    exit if:
                    - no changes made
                    - max iterations reached
                    - completion_promise found

                            ↓
                        complete
```

---

## Quality Gates

Loop completes when **any** of these is true:

1. **Stability Gate**: Code Simplifier makes no changes
2. **Iteration Gate**: Reached `--max-iterations` limit
3. **Promise Gate**: Output matches `--completion-promise` text

**Example:**
```bash
python ralph_orchestrator.py \
  --target src/components/Button.tsx \
  --max-iterations 5 \
  --completion-promise "DONE: Code is clean, readable, performant"
```

---

## Agent Roles

### Code Reviewer
- **Input**: Code to analyze
- **Process**: Static analysis, readability check, performance review
- **Output**: Structured findings with issues and recommendations
- **Interface**: `.coordination/ralph-loop/review-findings.json`

### Code Simplifier
- **Input**: Code + review findings
- **Process**: Refactor based on findings, extract functions, reduce complexity
- **Output**: Improved code with changeset documentation
- **Interface**: `.coordination/ralph-loop/simplified-code.json`

### Orchestrator
- **Role**: Coordinate communication, manage iterations, detect convergence
- **Decision**: When to stop looping
- **State**: All iteration history in `status.json`

---

## Usage Patterns

### Pattern 1: Fix Specific Issues
```bash
python ralph_orchestrator.py \
  --target src/utils/api.ts \
  --max-iterations 3
```

### Pattern 2: Convergence Loop
```bash
python ralph_orchestrator.py \
  --target src/hooks/useData.ts \
  --completion-promise "DONE: Code is clean and readable"
```

### Pattern 3: Multiple Passes
```bash
for file in src/components/*.tsx; do
  python ralph_orchestrator.py --target "$file" --max-iterations 2
done
```

---

## Failure Modes & Recovery

### Issue: Agent Doesn't Write Output
**Symptom**: Orchestrator waits, times out
**Recovery**: Check `.coordination/ralph-loop/status.json` for last successful write

### Issue: Infinite Loop
**Symptom**: Never converges, keeps making changes
**Recovery**: Use `--max-iterations` to bound; check for feedback loops in findings

### Issue: Silent Failure
**Symptom**: Agent completes but no output file
**Recovery**: Check orchestrator logs for errors; verify file permissions

---

## Integration with /ralph-loop Skill

The skill will:
1. Parse user prompt for target file
2. Invoke `python ralph_orchestrator.py --target ...`
3. Use Claude Code Task tool to run Code Reviewer agent
4. Use Claude Code Task tool to run Code Simplifier agent
5. Coordinate via `.coordination/` folder
6. Report progress to user

**Example invocation from Claude Code:**
```
/ralph-loop "Review and simplify src/api/client.ts" --max-iterations 5
```

---

## Testing

### Unit Test: State Management
```bash
python -m pytest tests/test_ralph_orchestrator.py::test_state_persistence
```

### Integration Test: Full Cycle
```bash
python ralph_orchestrator.py \
  --target tests/fixtures/complex-code.ts \
  --max-iterations 2

# Verify outputs in .coordination/ralph-loop/
```

### End-to-End: Via /ralph-loop Skill
```
/ralph-loop "Review src/test.ts" --completion-promise "DONE"
```

---

## Future Enhancements

- [ ] WebSocket progress updates to dashboard
- [ ] Parallel reviewer + simplifier (different aspects)
- [ ] Pluggable quality gates (coverage thresholds, complexity metrics)
- [ ] AI-assisted decision for "stop now" vs "continue"
- [ ] Diff visualization in dashboard
