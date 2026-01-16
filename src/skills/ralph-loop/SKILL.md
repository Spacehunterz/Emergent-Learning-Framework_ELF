# Ralph Loop Skill

```yaml
name: ralph-loop
version: 1.0.0
description: Iterative code improvement with Code Reviewer and Code Simplifier
license: MIT
domains:
  - code-review
  - refactoring
  - quality
requires:
  - code-reviewer agent
  - code-simplifier agent
```

---

## Overview

The Ralph Loop coordinates Code Reviewer and Code Simplifier agents in iterative cycles to progressively improve code quality. Named after the Ralph Wiggum technique, it embodies deterministic improvement through repeated cycles.

**What it does:**
1. Code Reviewer analyzes target code, identifies issues
2. Code Simplifier refactors based on findings
3. Loop repeats until code converges (no changes) or max iterations
4. Communicates via blackboard (.coordination/ folder)

**Use when:**
- Code has known issues and you want iterative improvement
- You want reviewer + simplifier cycling automatically
- You have a completion promise (clear success criteria)

**Typical workflow:**
```
User: /ralph-loop "Review and simplify src/api/client.ts" --max-iterations 5
  ↓
Orchestrator: Invoke Code Reviewer on target
  ↓
Code Reviewer: Analyze, write findings to .coordination/
  ↓
Orchestrator: Invoke Code Simplifier with findings
  ↓
Code Simplifier: Refactor, write improved code to .coordination/
  ↓
Orchestrator: Loop decision - repeat or exit
  ↓
User: See final improved code + iteration summary
```

---

## Execution

```bash
python ~/.claude/emergent-learning/src/query/ralph_orchestrator.py \
  --target <FILE> \
  --max-iterations <N> \
  --completion-promise "<PROMISE>"
```

---

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| target | string | ✓ | - | File to review and simplify |
| max-iterations | int | - | 5 | Maximum loop cycles before stopping |
| completion-promise | string | - | none | Promise text to signal completion |

---

## Handling Non-Interactive Mode (Claude Code Chat)

The skill emits JSON hints for Claude to coordinate with agents:

```
[PROMPT_NEEDED] {"type": "invoke_reviewer", "target": "src/api/client.ts"}
[PROMPT_NEEDED] {"type": "invoke_simplifier", "target": "src/api/client.ts", "findings": {...}}
```

Claude Code responds with:
```python
# Use Task tool to invoke Code Reviewer agent
# Code Reviewer analyzes and writes findings to .coordination/

# Use Task tool to invoke Code Simplifier agent
# Code Simplifier refactors and writes code to .coordination/
```

---

## 8-Step Ralph Loop Workflow

### Step 1: Initialize Orchestrator
- Create `.coordination/ralph-loop/` directory
- Load or create orchestrator state
- Parse target file
- Set iteration counter to 0

### Step 2: Reviewer Phase (per iteration)
- Write review request: `.coordination/ralph-loop/review-input.json`
- Invoke Code Reviewer agent via Claude Task tool
- Code Reviewer analyzes code structure, identifies issues
- Code Reviewer writes findings: `.coordination/ralph-loop/review-findings.json`

### Step 3: Simplifier Phase (per iteration)
- Write simplify request: `.coordination/ralph-loop/simplify-input.json`
- Invoke Code Simplifier agent via Claude Task tool
- Code Simplifier reads findings, refactors code
- Code Simplifier writes improved code: `.coordination/ralph-loop/simplified-code.json`

### Step 4: Convergence Check
- Compare original code to simplified code
- If identical: code is stable → exit loop
- If different: update current code, continue

### Step 5: Iteration Management
- Increment iteration counter
- Update `.coordination/ralph-loop/status.json`
- Check if iteration < max-iterations
- If yes: go to Step 2; if no: exit loop

### Step 6: Completion Decision
- Check if completion_promise matches output
- If yes: Ralph satisfied, exit with success
- If no: continue per iteration logic

### Step 7: Summary Generation
- Collect all iteration results
- Count issues resolved
- Document refactorings applied
- Generate performance metrics

### Step 8: Report Results
- Display final code quality metrics
- Show iteration count and convergence status
- List all changes made
- Confirm completion

---

## Examples

### Example 1: Single Pass Review
```
/ralph-loop "Review src/components/Button.tsx" --max-iterations 1
```

**Execution:**
- Code Reviewer analyzes Button.tsx → identifies 5 issues
- Code Simplifier fixes issues → refactored Button.tsx
- Exit (max iterations reached)

### Example 2: Convergence Loop
```
/ralph-loop "Review and simplify src/hooks/useData.ts" --completion-promise "DONE: Clean and readable"
```

**Execution:**
- Iteration 1: Reviewer finds issues → Simplifier refactors
- Iteration 2: Reviewer finds new issues → Simplifier refactors again
- Iteration 3: Reviewer finds no issues → Convergence! Exit
- Status: "DONE: Clean and readable" output achieved

### Example 3: Bounded Improvement
```
/ralph-loop "Optimize src/utils/api.ts" --max-iterations 3
```

**Execution:**
- Iteration 1: Issues found and fixed
- Iteration 2: More issues found and fixed
- Iteration 3: Small issues found and fixed
- Exit (3 iterations reached)

---

## Blackboard State Files

Located at `~/.claude/.coordination/ralph-loop/`:

```
review-input.json          ← Orchestrator → Reviewer
review-findings.json       ← Reviewer → Orchestrator
simplify-input.json        ← Orchestrator → Simplifier
simplified-code.json       ← Simplifier → Orchestrator
status.json                ← Orchestrator state tracking
```

**View current progress:**
```bash
cat ~/.claude/.coordination/ralph-loop/status.json | jq .
```

---

## Completion Promises

A completion promise is the condition under which Ralph should stop looping.

**Examples:**
- `"DONE: Code is clean and readable"`
- `"SUCCESS: All issues resolved"`
- `"COMPLETE: Quality gates passed"`

The orchestrator checks if the completion promise appears in the agent output. If found, loop exits with success.

**Why promises?**
- Gives Ralph a clear exit condition
- Prevents infinite loops
- Makes quality gates explicit
- Allows agents to declare success

---

## Troubleshooting

### Ralph doesn't seem to be working
1. Check `.coordination/ralph-loop/status.json` for orchestrator state
2. Check if agents are writing output files
3. Verify file permissions in `.coordination/` directory
4. Look for error messages in agent logs

### Loop never converges
1. Use `--max-iterations` to bound the loop
2. Check review findings - may be contradictory
3. Verify completion promise is achievable
4. Consider if code requires manual intervention

### Agent timeouts
1. Increase bash timeout for long analyses
2. Split large files into smaller chunks
3. Check agent availability and resources

---

## Integration with ELF

Ralph Loop fits into the ELF workflow:

```
/checkin
  ↓ (load context + golden rules)
  ↓
Work on feature/bug
  ↓
/ralph-loop "Review my code" --max-iterations 3
  ↓ (Code Reviewer → Code Simplifier cycle)
  ↓
Tests pass → ready to commit
  ↓
/checkout
  ↓ (record learnings + heuristics)
```

---

## Advanced Usage

### Batch Process Multiple Files
```bash
for file in src/components/*.tsx; do
  /ralph-loop "Review $file" --max-iterations 2
done
```

### Integration with CI/CD
```bash
# Pre-commit hook: Review changed files
changed_files=$(git diff --name-only HEAD)
for file in $changed_files; do
  /ralph-loop "Review $file" --max-iterations 1
done
```

### Ralph + Heuristics
```bash
# After Ralph loop converges, record insights
/ralph-loop "Review api/client.ts" --completion-promise "CLEAN"
python ~/.claude/emergent-learning/scripts/record-heuristic.py \
  --domain "api" \
  --rule "Extract HTTP client patterns" \
  --source "ralph-loop" \
  --confidence 0.8
```

---

## Metrics & Monitoring

Ralph tracks:
- **Iterations**: How many cycles to convergence
- **Issues resolved**: Count per iteration
- **Code changes**: Measured by diff size
- **Convergence time**: Wall-clock time to completion

**View metrics:**
```bash
cat ~/.claude/.coordination/ralph-loop/status.json | jq '.iterations'
```

---

## See Also

- `/checkin` - Load session context before work
- `/checkout` - Record learnings after work
- `/code-reviewer` - Manual code review (no loop)
- `/code-simplifier` - Manual refactoring (no loop)
- `.agent/workflows/ralph-loop/` - Detailed workflow spec
