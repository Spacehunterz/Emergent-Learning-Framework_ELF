# Checkin Workflow

**Description:** Load the Emergent Learning Framework building, display context, and enable dashboard and model selection.

**Execution:** `python ~/.claude/emergent-learning/src/query/checkin.py`

---

## Workflow Steps

### Step 1: Display Banner
Show the ELF ASCII art banner to signal the start of checkin.
- **Output:** ASCII art + newline
- **Conditions:** Always

### Step 2: Load Building Context
Query the learning framework to load golden rules, heuristics, and recent context.
- **Command:** `query.py --context`
- **Output:** Formatted context with Tier 1, 2, 3 information
- **Timeout:** 30 seconds

### Step 3: Display Golden Rules & Heuristics
Parse and format the loaded context for display.
- **Output:** Golden rules count, relevant heuristics
- **Conditions:** Always

### Step 4: Summarize Previous Session (Optional)
Spawn an async haiku agent to summarize the previous session.
- **Async:** Yes (spawn only, don't block)
- **Output:** Session summary from DB (if exists)
- **Conditions:** Only if session history available

### Step 5: Ask About Dashboard
Interactive prompt to start the ELF dashboard.
- **Prompt:** "Start ELF Dashboard? [Y/n]"
- **Action if Yes:** Launch `run-dashboard.sh` in background
- **Conditions:** First checkin only (tracked via state file)
- **State Guard:** After this step, sets `checkin_completed` flag

### Step 6: Ask About Model Selection
Interactive prompt to select active AI model.
- **Options:**
  - `(c)laude` - Orchestrator, backend, architecture [active]
  - `(g)emini` - Frontend, React, large codebases [1M context]
  - `(o)dex` - Graphics, debugging, precision [128K context]
  - `(s)kip` - Use current model
- **Action:** Store in `ELF_MODEL` environment variable
- **Conditions:** First checkin only
- **Persistence:** Set in environment for subprocess calls

### Step 7: Check CEO Decisions
List any pending CEO decisions from `ceo-inbox/`.
- **Output:** Count + list of first 3 items
- **Conditions:** If any decisions exist
- **Action:** Informational only

### Step 8: Complete
Print completion message.
- **Output:** "✅ Checkin complete. Ready to work!"
- **Actions:** Mark first checkin as done (state file)

---

## State Tracking

**State File Location:** `~/.claude/.elf_checkin_state`

**Contents:**
```json
{
  "checkin_completed": true,
  "timestamp": "2025-12-23T14:30:00"
}
```

**Purpose:** Ensure dashboard and model selection prompts appear only on first checkin of conversation.

---

## Environment Variables

- `ELF_MODEL` - Currently selected model (claude, gemini, codex)
  - Set by: Step 6 (model selection)
  - Consulted by: Downstream subagent invocations

---

## Exit Codes

- `0` - Success
- `1` - Failure (Python error, missing script, etc.)
- `2` - Interrupted (Ctrl+C during prompt)

---

## Specifications Met

✓ Banner displayed first (Step 1)
✓ Dashboard prompt one-time per conversation (Step 5 + state guard)
✓ Model selection with interactive prompt (Step 6)
✓ Model persistence via environment variable (Step 6)
✓ 8-step structured workflow
✓ Proper step sequencing
