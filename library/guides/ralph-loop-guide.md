# Ralph Loop: Iterative Code Improvement Guide

## What is Ralph Loop?

Ralph Loop (named after the Ralph Wiggum technique) is an iterative code improvement pattern that coordinates two agents in an **automatic pre-commit workflow**:

1. **Code Reviewer** - Analyzes code and identifies issues
2. **Code Simplifier** - Refactors code based on review findings

They work in cycles until the code converges (no more changes possible) or reaches a quality gate.

**When it runs:** Automatically when you `git commit` on staged code files

---

## Why Ralph Loop?

**Problem:** Code review + refactoring is often manual, iterative, and repetitive.

**Solution:** Automate the cycle with agents working together:
- Reviewer finds issues
- Simplifier fixes them
- Reviewer finds *new* issues in the refactored code
- Simplifier fixes those
- Loop until stable or complete

**Result:** Code gets progressively better through focused, coordinated improvements.

---

## How It Works

### The Loop

```
┌─────────────────────────────┐
│  Iteration N: Start         │
└──────────────┬──────────────┘
               ↓
┌──────────────────────────────┐
│  1. Code Reviewer analyzes   │
│     current code             │
└──────────────┬───────────────┘
               ↓
    ┌──────────────────────┐
    │ Write findings to    │
    │ .coordination/       │
    └──────────────────────┘
               ↓
┌──────────────────────────────┐
│  2. Code Simplifier reads    │
│     findings & refactors     │
└──────────────┬───────────────┘
               ↓
    ┌──────────────────────┐
    │ Write improved code  │
    │ to .coordination/    │
    └──────────────────────┘
               ↓
┌──────────────────────────────┐
│  3. Orchestrator decides:    │
│     Continue or exit?        │
└──────────────┬───────────────┘
               ↓
        ┌──────┴──────┐
        ↓             ↓
    Continue      Exit
    Next iter.    Done
```

### Blackboard Communication

Agents don't talk directly. They write to and read from a shared folder:

```
~/.claude/.coordination/ralph-loop/
├── review-input.json          ← Orchestrator writes: "review this code"
├── review-findings.json       ← Reviewer writes: "found these issues"
├── simplify-input.json        ← Orchestrator writes: "fix these issues"
├── simplified-code.json       ← Simplifier writes: "here's the improved code"
└── status.json                ← Orchestrator state tracking
```

This is **blackboard architecture** - agents are decoupled and communicate through shared state.

---

## Usage

### Installation (First Time)

```bash
bash tools/setup/install-ralph-hook.sh
```

This installs the pre-commit hook that auto-runs Ralph loop.

### Basic Workflow

1. **Make changes to code files**
   ```bash
   # Edit src/api/client.ts, src/utils/helpers.ts, etc.
   ```

2. **Stage your changes**
   ```bash
   git add .
   ```

3. **Commit - Ralph runs automatically**
   ```bash
   git commit -m "Add new API endpoint"
   ```

   Ralph loop will:
   - Review staged code files
   - Simplify based on findings
   - Loop up to 2 iterations (pre-commit is fast)
   - If improvements are made, block the commit
   - You stage improvements and commit again

### Skipping Ralph (if needed)

**Option 1: Environment variable**
```bash
SKIP_RALPH_LOOP=1 git commit -m "message"
```

**Option 2: --no-verify flag**
```bash
git commit --no-verify -m "message"
```

**Option 3: Uninstall the hook**
```bash
rm .git/hooks/pre-commit
```

---

## Real-World Example

### Scenario: Commit a React Component Fix

**You write and stage code:**
```bash
# Edit src/components/DataTable.tsx - fix bugs, add features
git add src/components/DataTable.tsx
```

**You try to commit:**
```bash
git commit -m "fix: Improve DataTable sorting performance"
```

**Ralph runs automatically:**

```
🔄 Ralph Loop: Auto-improving staged code...

  Reviewing: src/components/DataTable.tsx
    ✓ Improved

⚠️  Files were improved by Ralph loop
   Stage the improvements and try committing again:

   git add .
   git commit
```

**What Ralph found & fixed:**
- **Iteration 1**: "Component is 200 lines. Extract 3 helper functions. Props validation missing."
  - Extracted helpers, added prop validation
  - File reduced to 120 lines

- **Iteration 2**: "Good. useEffect has stale dependencies. Consider useMemo for data transform."
  - Fixed useEffect, added useMemo
  - Better performance, no stale closures

**You update staged changes:**
```bash
git add src/components/DataTable.tsx
git commit -m "fix: Improve DataTable sorting performance"
```

**Ralph runs again - code is stable:**
```
🔄 Ralph Loop: Auto-improving staged code...

  Reviewing: src/components/DataTable.tsx
    ℹ️  No changes needed

✓ All code reviewed and improved
```

**Commit succeeds.** Your code is cleaner before it ever hits version control.

---

## Quality Gates

Ralph has built-in quality gates to decide when to stop:

### Gate 1: Stability
If Code Simplifier makes zero changes, code is stable → exit

### Gate 2: Iteration Limit
If reached `--max-iterations`, exit regardless

### Gate 3: Completion Promise
If output contains the completion promise text → exit with success

---

## Integration with ELF Workflow

```
START SESSION
    ↓
/checkin → Load golden rules + context
    ↓
WORK ON CODE
    ↓
/ralph-loop → Iterative review + refactoring
    ↓
TESTS PASS
    ↓
/checkout → Record learnings + heuristics
    ↓
END SESSION
```

Ralph fits naturally into the learning cycle:
- You work on code
- Ralph improves it iteratively
- You learn from the improvements
- Record those learnings for next time

---

## Viewing Progress

**Check orchestrator state:**
```bash
cat ~/.claude/.coordination/ralph-loop/status.json | jq '.'
```

**View iteration history:**
```bash
cat ~/.claude/.coordination/ralph-loop/status.json | jq '.iterations[]'
```

**See review findings:**
```bash
cat ~/.claude/.coordination/ralph-loop/review-findings.json | jq '.'
```

**See simplified code:**
```bash
cat ~/.claude/.coordination/ralph-loop/simplified-code.json | jq '.code' | head -20
```

---

## Tips & Tricks

### Tip 1: Use Completion Promises
Be explicit about success criteria:
```bash
/ralph-loop "src/auth/login.ts" \
  --completion-promise "DONE: Security validated, no TODOs"
```

Agents will work toward that goal.

### Tip 2: Bound Large Refactors
For big files, use 2-3 iterations first:
```bash
/ralph-loop "src/api/rest-client.ts" --max-iterations 2
```

See if smaller iterations are enough before going deep.

### Tip 3: Chain Ralph Loops
```bash
/ralph-loop "src/components/Button.tsx" --max-iterations 2
/ralph-loop "src/components/Card.tsx" --max-iterations 2
/ralph-loop "src/components/Modal.tsx" --max-iterations 2
```

Batch process related files.

### Tip 4: Record Learnings After
```bash
/ralph-loop "src/api/client.ts" --completion-promise "CLEAN"

# After Ralph completes, record the pattern:
python ~/.claude/emergent-learning/scripts/record-heuristic.py \
  --domain "api" \
  --rule "Split HTTP clients by responsibility" \
  --explanation "Ralph found this pattern improves readability"
  --confidence 0.8
```

### Tip 5: Check Before Commit
```bash
# Review staged changes with Ralph
/ralph-loop "$(git diff --cached --name-only | head -1)" --max-iterations 1
```

---

## Sharing Ralph Loop with Others

### For Your "ELF Homies"

Ralph loop is integrated as a pre-commit hook. To share with others:

**Prerequisites they need:**
1. Emergent Learning Framework installed
2. Code Reviewer agent (you provide setup)
3. Code Simplifier agent (you provide setup)

**Installation for them:**
```bash
# In their ELF repo
bash tools/setup/install-ralph-hook.sh
```

**That's it.** Next time they commit, Ralph runs automatically.

**Documentation to share:**
- Point them to this guide: `library/guides/ralph-loop-guide.md`
- Show them the workflow: code → git add → git commit (Ralph runs)
- Explain they can skip with `SKIP_RALPH_LOOP=1 git commit`

**No slash commands, no configuration.** It just works.

---

## Troubleshooting

### Ralph Doesn't Seem to Work

**Check 1:** Verify orchestrator state
```bash
ls ~/.claude/.coordination/ralph-loop/
```

**Check 2:** View latest status
```bash
cat ~/.claude/.coordination/ralph-loop/status.json
```

**Check 3:** Verify agents are writing output
```bash
ls -lh ~/.claude/.coordination/ralph-loop/review-findings.json
ls -lh ~/.claude/.coordination/ralph-loop/simplified-code.json
```

### Loop Won't Converge

**Solution 1:** Set `--max-iterations` to bound it
```bash
/ralph-loop "big-file.ts" --max-iterations 3
```

**Solution 2:** Check for contradictory findings
- Reviewer might find issues the Simplifier can't fix
- This is normal - stop when reasonable

### Completion Promise Never Triggers

**Check:** Is the promise text actually in the output?
```bash
cat ~/.claude/.coordination/ralph-loop/status.json | grep -i "done"
```

Make sure the promise is achievable and agents understand it.

---

## Next Steps

1. **Test Ralph:** Run `/ralph-loop` on a real file in your project
2. **Observe:** Watch agents improve the code
3. **Learn:** See what patterns Ralph prefers
4. **Share:** Pass setup to colleagues/friends
5. **Refine:** Adjust max-iterations and promises based on results

---

## Philosophy

Ralph Loop embodies the core ELF principle:

> **TRY → BREAK → ANALYZE → LEARN → NEXT**

Ralph Loop does this with code:
1. **TRY**: Reviewer analyzes current code
2. **BREAK**: Simplifier refactors (intentionally changes it)
3. **ANALYZE**: Reviewer checks the refactored code
4. **LEARN**: Simplifier learns from new findings
5. **NEXT**: Loop continues until convergence

It's automated iterative improvement.
