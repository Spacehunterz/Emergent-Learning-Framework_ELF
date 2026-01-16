# /prd - Manage Product Requirements Document

Create, edit, and manage your Ralph Loop PRD (Product Requirements Document).

## Usage

### Create a New PRD

```bash
/prd create
```

Interactive prompt asks:
- Project name
- Stories (one per line, priority-based)

Generates `prd.json` with your specifications.

### View Current PRD

```bash
/prd show
```

Pretty-prints the current `prd.json`:
- All stories
- Status of each
- Priority order
- Description

### Edit a Story

```bash
/prd edit TASK-001
```

Opens editor for that story. Edit:
- title
- description
- acceptance_criteria
- files
- priority

### Add a Story

```bash
/prd add "Feature Title" "Description" "file1.ts,file2.ts"
```

Adds new story to prd.json with next available ID.

### Remove a Story

```bash
/prd remove TASK-001
```

Removes story from prd.json (confirmation required).

### Reset PRD

```bash
/prd reset
```

Creates fresh default PRD:
- Wipes current prd.json
- Creates 4 default stories
- Fresh progress.txt
- Confirmation required

### Validate PRD

```bash
/prd validate
```

Checks prd.json for:
- Valid JSON
- Required fields per story
- No duplicate IDs
- At least one story
- Proper status values

Returns errors and warnings.

### Convert to JSON

```bash
/prd export
```

Exports prd.json in formatted JSON to stdout. Useful for piping to other tools.

## Story Format

Each story should have:

```json
{
  "id": "TASK-001",
  "title": "User Authentication",
  "description": "Implement JWT-based login system",
  "priority": 1,
  "status": "pending",
  "acceptance_criteria": [
    "Users can login with email/password",
    "JWT tokens are issued",
    "Protected routes require token"
  ],
  "files": [
    "src/auth.ts",
    "tests/auth.test.ts"
  ]
}
```

## Status Values

- `pending` - Not yet started
- `in_progress` - Currently being worked on
- `done` - Completed and committed
- `blocked` - Unable to complete, needs intervention

## Priority

Lower number = higher priority. Ralph processes stories in priority order:

```
priority: 1  → Runs first
priority: 2  → Runs second
priority: 10 → Runs last
```

## Best Practices

### Story Titles
- Use active verbs: "Implement X", "Add Y", "Fix Z"
- Be specific: "Add user registration" not "User stuff"
- One task per story

### Descriptions
- Explain the "why" and "what"
- Reference related stories if dependencies exist
- Mention any constraints or gotchas

### Acceptance Criteria
- Write testable criteria
- Include edge cases
- Be specific: "Returns 401 if token expired"
- 3-5 criteria per story

### Files
- List only files that will change
- Include tests alongside implementation
- Path from repo root

## Integration with start-work

```bash
/prd create          # Create PRD
/start-work          # start-work reads your PRD and runs Ralph Loop
```

Or for quick start with defaults:

```bash
/start-work          # Auto-creates default PRD if missing
```

## Examples

### Create PRD for REST API

```bash
/prd create
# Prompts:
# Project name: REST API Service
# Story: 1 GET /users endpoint: Fetch all users
# Story: 2 POST /users endpoint: Create new user
# Story: 3 Authentication middleware: Protect endpoints
# Story: (blank to finish)
```

### Edit acceptance criteria

```bash
/prd edit TASK-001
# Editor opens with TASK-001 story
# Edit acceptance_criteria array
# Save and close
```

### Quick view

```bash
/prd show
# See all stories, priorities, and status
```

### Check validity

```bash
/prd validate
# Returns any errors or warnings
# Green light to proceed with /start-work
```

## Workflow

Typical workflow:

1. `prd create` - Define your stories
2. Review each story's acceptance criteria
3. `prd validate` - Ensure PRD is valid
4. `start-work` - Ralph Loop handles the rest
5. Stories complete automatically
6. Check `progress.txt` for learnings

## See Also

- `/start-work` - Begin work session with auto-init
- `/ralph` - Raw Ralph Loop control
- `prd.json` - The actual file (edit directly if needed)
- `library/guides/ralph-loop-guide.md` - Detailed architecture docs

---

**Philosophy:** Your PRD is your work plan. Make it clear, detailed, and testable. Ralph Loop handles execution. You focus on requirements and reviewing results.
