---
name: checkin
description: Load and review Emergent Learning Framework context, institutional knowledge, golden rules, and recent session history. Runs the checkin workflow interactively with banner, context loading, and dashboard/multi-model prompts.
license: MIT
---

# ELF Checkin Command

Interactive workflow to load the building context before starting work.

## What It Does

The `/checkin` command:
- Shows the ELF banner with ASCII art **first** (before any prompts)
- Queries the building for golden rules and heuristics
- Displays relevant context and frameworks
- Asks if you want to launch the dashboard **(first checkin only)**
- Asks which AI model you want to use **(first checkin only)**
- Checks for pending CEO decisions
- Loads and displays recent session context

## Usage

```bash
/checkin
```

The checkin command is simple - just type `/checkin` to load framework context and prepare your session.

## Execution

This skill runs the new Python-based orchestrator:

```bash
python ~/.claude/emergent-learning/elf.py checkin
# OR directly:
python ~/.claude/emergent-learning/src/query/checkin.py
```

The orchestrator is a complete 8-step workflow:
- Step 1: Display banner
- Step 2: Load building context
- Step 3: Display golden rules & heuristics
- Step 4: Previous session summary (optional/async)
- Step 5: Dashboard prompt (first checkin only, with state tracking)
- Step 6: Model selection prompt (first checkin only, with persistence)
- Step 7: CEO decision checking
- Step 8: Ready signal

## Workflow Steps (8-Step Structured Process)

### Step 1: Display Banner ✓
Show ELF ASCII art immediately
- **Always shown** on every checkin
- **Signals** that framework is loading

### Step 2: Load Building Context ✓
Query the learning framework
- Loads golden rules (Tier 1)
- Loads heuristics (Tier 2)
- Loads recent patterns and learnings

### Step 3: Display Golden Rules & Heuristics ✓
Parse and format context for readability
- Shows rule count and key principles
- Displays relevant patterns

### Step 4: Previous Session Summary
Spawn async haiku agent to summarize recent work
- **Async execution** (doesn't block)
- Shows continuity with previous sessions

### Step 5: Dashboard Prompt ⚡ **NEW**
Ask user if they want to start the dashboard
- **Only on first checkin** (tracked via state file)
- "Start ELF Dashboard? [Y/n]"
- Launch in background if yes
- Never asked again in same conversation

### Step 6: Model Selection ⚡ **NEW**
Interactive prompt to select your active AI model
- **Only on first checkin** (state-tracked)
- Options: (c)laude / (g)emini / (o)dex / (s)kip
- Selection stored in `ELF_MODEL` environment variable
- Persists for subagent invocations

### Step 7: CEO Decisions
Check for pending CEO decisions in `ceo-inbox/`
- Lists count and first 3 items
- Informational only

### Step 8: Ready Signal ✓
Print completion message
- "✅ Checkin complete. Ready to work!"
- Marks first checkin complete (state file)

## Key Improvements (Full Spec Compliance)

✅ **Banner First** - Displayed before any prompts, not after
✅ **One-Time Prompts** - Dashboard and model selection appear only on first checkin
✅ **State Tracking** - Uses `~/.claude/.elf_checkin_state` to track conversation state
✅ **Model Persistence** - Selection stored in `ELF_MODEL` environment variable
✅ **Structured Workflow** - All 8 steps executed in proper sequence
✅ **Context Parsing** - Query output properly formatted for display

## Interactive Prompts

### Dashboard Prompt (First Checkin Only)
```
Start ELF Dashboard?
   The dashboard provides metrics, model routing, and system health.

Start Dashboard? [Y/n]:
```
- Default: Yes (just press Enter)
- Launches in background if accepted
- Never asks again in same conversation

### Model Selection Prompt (First Checkin Only)
```
Select Your Active Model
   Available models:
     (c)laude    - Orchestrator, backend, architecture (active)
     (g)emini    - Frontend, React, large codebases (1M context)
     (o)dex      - Graphics, debugging, precision (128K context)
     (s)kip      - Use current model

Select [c/g/o/s]:
```
- Stores choice in `ELF_MODEL` environment variable
- Used by subagent routing
- Default: Claude (s)kip option

## Integration with Building

The checkin workflow is your gateway to the building's knowledge:
- **Golden Rules** - Constitutional principles (always loaded)
- **Heuristics** - Reusable patterns and knowledge
- **Failures** - What went wrong and lessons learned
- **Successes** - What worked and can be replicated
- **Sessions** - Previous work summaries for continuity

Running checkin at the start of each session ensures you're working with current institutional knowledge.
