---
name: story
description: Create and manage user stories in proper narrative format for Ralph Loop
license: MIT
---

# /story - Interactive User Story Management

Create, manage, and track user stories in proper narrative format. Stories feed into Ralph Loop for autonomous implementation.

## What It Does

The `/story` skill provides an interactive workflow for creating well-structured user stories that follow the proven "As a / I want / So that" narrative format. Stories are:

- **Narrative-driven** - Forces clarity of user role, desired action, and business value
- **Validated** - Ensures proper format before adding to work queue
- **Trackable** - Integrates with Ralph Loop for autonomous execution and progress tracking
- **Filterable** - Search by priority, status, or affected files
- **Exportable** - Generate markdown summaries for documentation

## Quick Start

### Create a Story
```bash
/story new
```

You'll be prompted for:
1. **User role** - "As a [developer/researcher/etc.]"
2. **Desired action** - "I want to [action]"
3. **Business value** - "So that [benefit]"
4. **Title** - Suggested auto-generated from action
5. **Priority** - 1 (high), 2 (normal), 3 (low)
6. **Files** - Affected files (comma-separated, optional)
7. **Acceptance criteria** - Multiple criteria (at least 1 required)

### View Stories
```bash
/story show                        # List all stories with status
/story view STORY-001             # Show full details for one story
/story list --priority 1          # Filter by priority
/story list --status in_progress  # Filter by status
/story list --files src/auth.ts   # Find stories touching a file
```

### Update Story
```bash
/story update STORY-001
```

Interactively change: status, priority, acceptance criteria

### Export
```bash
/story export > stories.md
```

Generate markdown summary grouped by priority and status.

## Two Paths: Quick vs Structured

When you run `/story new`, you choose your approach:

### Quick Path (Default)
Traditional narrative format - fast for simple stories.
- User role → Desired action → Business value
- Builds "As a X, I want Y, so that Z" automatically
- Best for: Simple features, quick iterations, clear scope

### Structured Path (Prevents Ralph Spiraling)
Ryan's methodology - comprehensive planning for complex work.
- Problem statement (what challenge does this solve?)
- Narrative format (As a / I want / So that)
- Functional requirements (what must the system do?)
- Constraints & non-goals (what's out of scope?)
- Success metrics (how do we measure success?)
- Auto-generates subtasks to prevent infinite iteration loops

**Choose Structured when:**
- Building large features with many moving parts
- You want Ralph to have clear sub-goals
- You need to prevent "Ralph spiraling" (infinite iteration loops)
- You want detailed requirements documented

**Why Structured prevents spiraling:**
- Breaks complex work into finite, testable subtasks
- Each subtask has one clear purpose
- Ralph processes TASK-001, TASK-002... in order
- Forces upfront thinking about scope and boundaries

## Story Format

Stories follow the **user story narrative**:

```
As a [user role]
I want to [desired action]
So that [business value]
```

**Why this format?**
- **Clarity** - Each part serves a specific purpose
- **User-focused** - Starts with who benefits and why
- **Context** - Helps Claude understand the bigger picture
- **Traceability** - Each story has clear reasoning

**Example story:**

```
As a developer in a Ralph loop
I want to see my task context in a collapsible JSON card
So that I can quickly reference my context without switching windows

Acceptance Criteria:
- Card displays TIER 0 project context
- Card shows top 5 relevant golden rules for current domain
- JSON is syntax-highlighted (keys, values, strings colored differently)
- Card has 'Collapse all' button to minimize nested objects
- Card loads in <500ms
- Works offline (no external CDN dependencies)
```

## Story Lifecycle

```
pending (waiting for work)
   ↓
in_progress (Ralph Loop assigned it)
   ↓
done ✓ (Ralph completed + tests passed)

OR blocked ✗ (Ralph encountered an issue)
```

**Automatic transitions:**
- Ralph Loop changes status to `in_progress` when starting work
- Status becomes `done` if implementation + tests succeed
- Status becomes `blocked` if tests fail or error occurs
- Manual update via `/story update` as needed

## Commands Reference

### `/story new`
Create a new story interactively.

First, you choose your path: **[Q] Quick** (default) or **[S] Structured**

#### Quick Path Prompts
1. Story ID (auto-suggest next available)
2. Path choice: `[Q/S, default=Q]`
3. User role (As a)
4. Desired action (I want to)
5. Business value (So that)
6. Title (auto-suggested from action)
7. Priority (1-3)
8. Files (comma-separated, optional)
9. Acceptance criteria (blank to finish, at least 1)

#### Structured Path Prompts
1. Story ID (auto-suggest next available)
2. Path choice: `[S]`
3. Problem statement (What problem does this solve?)
4. User role (As a)
5. Desired action (I want to)
6. Business value (So that)
7. Title (auto-suggested)
8. Priority (1-3)
9. Functional requirements (blank to finish)
10. Constraints & non-goals (blank to finish)
11. Success metrics (blank to finish, at least 1 recommended)
12. Files (comma-separated, optional)
13. Acceptance criteria (blank to finish, at least 1)
14. Generate subtasks? `[Y/n, default=Y]`
    - If yes: Automatically creates TASK-001, TASK-002... for each requirement

**Output (Quick Path):**
```
✓ Created story: [STORY-001] Your Story Title
```

**Output (Structured Path):**
```
✓ Created story: [STORY-006] Your Story Title
  Linked subtasks: 4
```

### `/story show`
List all stories with visual status and brief info.

**Output:**
```
STORIES (5 total, 2 complete)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] [P1] STORY-001: User Authentication
     Status: pending | Files: 2

[~] [P2] STORY-002: Dashboard UI
     Status: in_progress | Files: 4

[X] [P1] STORY-003: Database Migration
     Status: done | Files: 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Status icons: `[ ]` pending, `[~]` in_progress, `[X]` done, `[!]` blocked

### `/story view STORY-001`
Show complete details for a single story.

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STORY-001: User Authentication
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Description:
  As a developer, I want to implement JWT-based authentication,
  so that users can login securely.

Priority: 1 (High)
Status: pending

Acceptance Criteria:
  - Users can login with email/password
  - JWT tokens are issued on successful auth
  - Protected routes require valid token
  - Token expiration is enforced

Files:
  - src/auth/login.ts
  - src/auth/middleware.ts
  - tests/auth.test.ts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### `/story update STORY-001`
Interactively modify a story's status, priority, or criteria.

**Prompts:**
- Status (pending/in_progress/done/blocked)
- Priority (1-3)
- New acceptance criteria (optional)

**Output:**
```
✓ Updated story STORY-001
```

### `/story list [OPTIONS]`
Filter and display stories matching criteria.

**Options:**
```bash
--priority 1|2|3              # Filter by priority
--status pending|in_progress|done|blocked  # Filter by status
--files src/path/file.ts      # Find stories touching specific file
```

**Examples:**
```bash
/story list --priority 1                    # All high-priority stories
/story list --status in_progress            # What Ralph is currently working on
/story list --files src/components/Card.tsx # Stories affecting Card component
```

### `/story export`
Generate markdown summary of all stories.

**Output:** Markdown file with:
- Summary stats (total, complete %, in progress, pending)
- Stories grouped by priority
- Each story shows: status, narrative, criteria, files

**Redirect to file:**
```bash
/story export > stories.md
```

## Integration with Ralph Loop

### How Stories Flow Through Ralph Loop

```
1. /story new         → Create story in narrative format
2. /prd validate      → Verify format (warns on issues)
3. /loop start        → Ralph picks next story from prd.json
4. Ralph implements   → Writes code
5. Code review step   → Catches issues
6. Simplify code      → Cleans up
7. Run tests          → Validates correctness
8. If pass:
   - Commit to git
   - Set "passes": true in prd.json
   - Log learnings to progress.txt
   - Pick next story → back to step 3
9. If fail:
   - Set status to "blocked"
   - Log failure analysis
   - Human review required
```

### Story Status in Ralph Loop

Stories start as **pending** → Ralph changes to **in_progress** → ends as **done** (✓ tests passed) or **blocked** (✗ failed)

You can manually update status with `/story update` if needed.

### How Ralph Processes Stories with Subtasks

When a story has subtasks (created with structured path):

1. Ralph processes **subtasks in order** (TASK-001, TASK-002...)
2. Each subtask is a separate, finite work item
3. Ralph marks each subtask **in_progress → done** individually
4. When **all subtasks done** → parent story marked **done**
5. If any subtask **fails** → parent story marked **blocked**

**Why this prevents spiraling:**
- Each subtask is too small to spiral on (one clear purpose)
- Ralph finishes TASK-001 completely before TASK-002
- Clear success criteria at the subtask level
- Parent story only marks done when all children done

**Example flow:**
```
STORY-007: Search Context Card
  ├─ TASK-001: Create feature branch [DONE]
  ├─ TASK-002: Search is case-insensitive [DONE]
  ├─ TASK-003: Highlights matching [DONE]
  ├─ TASK-004: Returns count [IN_PROGRESS]
  └─ TASK-005: Filters nested objects [PENDING]
```

Ralph is working on TASK-004. When done, moves to TASK-005. Once all complete, STORY-007 marked done.

## Validation

Stories are validated for:

✅ **Required fields:**
- Unique ID
- Title
- Description with proper narrative format
- At least 1 acceptance criterion
- Valid status (pending, in_progress, done, blocked)
- Priority 1-3

⚠️ **Warnings (don't block):**
- Less than 3 acceptance criteria (recommend 3-5)
- Missing narrative format ("As a X, I want Y, so that Z")
- No files listed (sometimes OK for cross-cutting concerns)

**Validate stories:**
```bash
/prd validate    # Validates all stories (including format checks)
```

## Best Practices

### 1. Clear User Role
✅ "As a developer debugging a failed loop"
❌ "As a user"

### 2. Specific Action
✅ "I want to see the exact JSON state that triggered the failure"
❌ "I want to see something"

### 3. Real Business Value
✅ "So that I can understand what went wrong without digging through logs"
❌ "So that I have a feature"

### 4. Testable Criteria
✅ "Card displays TIER 0 project context"
✅ "JSON is syntax-highlighted"
❌ "Card is nice"
❌ "UI is better"

### 5. Right Scope
- One story = one feature or user interaction
- If it takes >4 hours to implement, consider breaking it
- List affected files upfront (helps Ralph plan work)

### 6. Priority Guidance
- **P1 (High)** - Blocks other work or critical path
- **P2 (Normal)** - Important but not urgent
- **P3 (Low)** - Nice to have, can defer

## Comparison: `/story` vs `/prd`

| Aspect | `/story` | `/prd` |
|--------|----------|--------|
| **Input** | Interactive prompts | Manual JSON editing |
| **Format** | Guided narrative | Free-form |
| **Validation** | Enforced | Optional |
| **ID Prefix** | STORY-XXX (user stories) | TASK-XXX (technical tasks) |
| **Use case** | Feature work | Project setup/management |
| **Best for** | Ralph Loop automation | Overall PRD management |

**When to use `/story`:**
- Creating new user stories for Ralph Loop
- Iterating on features with clear user benefits
- Ensuring narrative format is followed

**When to use `/prd`:**
- Viewing/managing entire PRD
- Adding technical tasks (non-story work)
- Validating entire project structure

Both tools read/write the same `prd.json` - they're complementary!

## Troubleshooting

### Story not appearing after creation
1. Check: `/story show` lists it
2. Validate: `/prd validate` shows no errors
3. File: Verify `prd.json` was updated: `tail prd.json`

### Ralph Loop not picking up story
1. Verify status is **pending** or **in_progress**
2. Run validation: `/prd validate`
3. Check story ID starts with `STORY-` or `TASK-`
4. View Ralph log: check `progress.txt` for errors

### Can't update story status
1. Verify story ID: `/story show`
2. Valid status: pending, in_progress, done, blocked
3. Try: `/story update STORY-001` (interactive mode)

## See Also

- `/prd` - Full PRD management and validation
- `/loop` - Start Ralph Loop for autonomous execution
- `prd.json` - Raw data file (view with `/story show`)
- `progress.txt` - Learnings and execution log
- `prompt.md` - Ralph's work order (generated per iteration)

## Examples

### Example 1: Quick Path - React Component Story

```bash
$ /story new

Story ID [STORY-006]:
Path [Q/S, default=Q]: Q
User role (As a): developer in a React project
Desired action (I want to): implement a collapsible JSON card component
Business value (So that): display context at a glance without opening other windows
Title [Implement Collapsible JSON Card]:
Priority [1=high, 2=normal, 3=low, default=2]: 1
Files (comma-separated, optional): src/components/ContextCard.tsx, src/hooks/useContext.ts, tests/ContextCard.test.tsx
Add acceptance criteria (blank line to finish, need at least 1):
  - Component accepts JSON data as prop
  - Sections collapse/expand on click
  - JSON is syntax-highlighted
  - Works with deeply nested objects
  - Component is <500ms to render
  - No external dependencies
  (blank to finish)

✓ Created story: [STORY-006] Implement Collapsible JSON Card
```

### Example 2: Structured Path - Complex Feature with Subtasks

```bash
$ /story new

Story ID [STORY-007]:
Path [Q/S, default=Q]: S

=== Problem Statement ===
What problem does this solve? Users can't easily search through large heuristics in the context card

Create narrative: 'As a X, I want Y, so that Z'
User role (As a): developer in Ralph loop with large knowledge base
Desired action (I want to): search the context card by domain or keyword
Business value (So that): I can find relevant heuristics without manual scrolling

Title [Search Context Card By Domain Or Keyword]:
Priority [1=high, 2=normal, 3=low, default=2]: 1

=== Functional Requirements ===
List what the system must do (blank to finish):
  Requirement: Search is case-insensitive
  Requirement: Highlights matching keys and values
  Requirement: Returns count of matches
  Requirement: Filters work with nested objects
  Requirement: Search input is sticky while scrolling
  Requirement: (blank to finish)

=== Constraints & Non-Goals ===
What should this NOT do? Any limits? (blank to finish):
  Constraint: Don't add external search libraries (keep it lightweight)
  Constraint: Don't modify the JSON structure for search purposes
  Constraint: (blank to finish)

=== Success Metrics ===
How do we measure success? (blank to finish, at least 1):
  Metric: Search returns results in <100ms
  Metric: All criteria work with 1000+ item datasets
  Metric: Works offline without external dependencies
  Metric: (blank to finish)

Files (comma-separated, optional): src/components/ContextCard.tsx, src/components/SearchFilter.tsx

Add acceptance criteria (blank line to finish, need at least 1):
  - Search box accepts text input
  - Results highlight in card
  - Count displayed: "X matches found"
  - Escape key clears search
  - (blank to finish)

Generate subtasks to prevent Ralph spiraling? [Y/n]: Y

=== Generating Subtasks ===
  - [TASK-001] Create feature branch
  - [TASK-002] Search is case-insensitive
  - [TASK-003] Highlights matching keys and values
  - [TASK-004] Returns count of matches
  - [TASK-005] Filters work with nested objects
  - [TASK-006] Search input is sticky while scrolling
✓ Generated 5 subtasks (plus feature branch)

✓ Created story: [STORY-007] Search Context Card By Domain Or Keyword
  Linked subtasks: 6
```

### Example 2: Filter High-Priority Pending Work

```bash
$ /story list --priority 1 --status pending

[STORY-001] User Authentication
[STORY-005] Dashboard KPI Display
[STORY-009] Error Handling Framework

→ Ralph will process these in order
```

### Example 3: Review Before Starting Ralph Loop

```bash
$ /story show
$ /prd validate    # Ensure all stories are valid
$ /loop            # Start Ralph Loop
```

## Contributing

To improve the `/story` skill:
1. Use it regularly and note friction points
2. Suggest UX improvements to the prompts
3. Add new filters for `/story list`
4. Extend validation rules (in `/prd validate`)
5. Share story templates for common patterns
