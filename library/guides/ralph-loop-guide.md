# Ralph Loop: Autonomous Task Execution

Ralph Loop is an infinite orchestrator that spawns fresh Claude Code sessions to complete stories from a PRD (Product Requirements Document). It solves context degradation by ensuring each iteration gets clean context.

## The Problem Ralph Solves

Claude gets "dumber" after ~100k tokens in a single session due to context window degradation. Ralph Loop prevents this by:
- Spawning a **fresh session per story**
- Keeping each session's scope **tight (one story)**
- Storing cross-session memory in **prd.json** (state) + **progress.txt** (learnings)

Result: No context degradation, even for multi-hundred-story projects.

## Architecture

### Three-File Blackboard Pattern

Ralph Loop uses three files to maintain state across stateless sessions:

#### 1. `prd.json` - Product Requirements Document
Contains the complete task list with completion tracking.

```json
{
  "name": "My Project",
  "version": "1.0.0",
  "stories": [
    {
      "id": "TASK-001",
      "title": "Feature A",
      "description": "What to implement",
      "priority": 1,
      "status": "pending",
      "acceptance_criteria": ["Criterion 1"],
      "files": ["src/a.ts"]
    }
  ]
}
```

**Ralph reads:** Which stories are incomplete
**Ralph writes:** Updates story status as they complete

#### 2. `progress.txt` - Append-Only Learnings
Institutional memory across sessions.

```
## 2026-01-15 - TASK-001: Feature A
- Key learning 1
- Key learning 2
```

**Ralph reads:** For context on previous attempts
**Sessions write:** Append learnings for next iteration

#### 3. `prompt.md` - Work Order
Generated fresh per iteration. Contains story details and instructions.

**Ralph writes:** Populates with current story details
**Session reads:** Via stdin

### Execution Loop

```
while true:
  1. Read prd.json - find incomplete stories
  2. Select highest priority incomplete story
  3. Generate prompt.md with story details
  4. Spawn fresh claude-code session
  5. Session implements, tests, commits
  6. Update story status based on result
  7. Continue until all done
```

## Getting Started

### 1. Bootstrap Ralph Loop

```bash
bash tools/scripts/init-ralph.sh
```

### 2. Customize Your PRD

Edit `prd.json` and define your stories

### 3. Run Ralph Loop

```bash
bash tools/scripts/ralph.sh
```

### 4. Each Session

Implement the story, test it, commit, append learnings to progress.txt

### 5. Monitor

```bash
# Check progress
cat prd.json | python3 -m json.tool

# View learnings
cat progress.txt

# See git history
git log --oneline
```

## Key Principles

1. **One Story Per Session** - Tight scope, clean context
2. **Fresh Context** - Only git history, prd.json, progress.txt carry over
3. **Append-Only Learnings** - progress.txt never rewrites
4. **Blackboard Communication** - Ralph and sessions share files, don't talk

## Commands

```bash
# Run Ralph Loop
bash tools/scripts/ralph.sh

# With options
bash tools/scripts/ralph.sh --max-iterations 5
bash tools/scripts/ralph.sh --prd custom.json

# Initialize new project
bash tools/scripts/init-ralph.sh --project "My App"
```

## Best Practices

### Story Design

Keep stories focused and testable:

```json
{
  "title": "Add user registration endpoint",
  "priority": 1,
  "acceptance_criteria": [
    "POST /auth/register accepts email/password",
    "Returns 201 on success",
    "Returns 409 if email exists"
  ],
  "files": ["src/auth.ts", "tests/auth.test.ts"]
}
```

### Commit Messages

Reference story ID:

```bash
git commit -m "feat(TASK-001): Add user registration

- POST /auth/register endpoint
- Email validation
- Tests for happy/error paths"
```

### Learnings

After each story:

```
## 2026-01-15 - TASK-001: User Registration
- Used bcrypt for password hashing
- Email indexing needed for duplicate checks
- Session migrations: had to manually setup schema
```

## Troubleshooting

### "Claude Code not found"
Install Claude Code CLI

### Story marked "blocked"
Check progress.txt for error details, fix issue, rerun ralph.sh

### Context still degrading
Stories might be too large. Split them into smaller pieces (40-100 lines each)

## Architecture Decisions

### Why Fresh Sessions?
- One long session: context degrades, errors cascade
- Fresh sessions: clean slate, predictable, resilient

### Why prd.json?
- No external dependencies
- Works offline
- Tracked in git
- Easy to understand

### Why Append-Only progress.txt?
- Preserves history
- Easy to debug
- Chronological record

---

Ralph Loop Philosophy: Automate the organizational structure of work (breaking into stories), not the implementation. Claude does the thinking—Ralph ensures each thinking session has a clean context window.
