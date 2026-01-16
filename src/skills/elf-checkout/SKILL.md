---
name: checkout
description: Automated session closing - no prompts, just capture and display.
license: MIT
---

# ELF Checkout Command

Automated session closing - no prompts, just capture and display.

## What It Does

The `/checkout` command:
- Auto-detects session activity (commits, files, domains)
- Counts heuristics recorded during the session
- Displays a summary
- No questions asked

## Usage

```bash
/checkout
```

## Execution

```bash
python ~/.claude/emergent-learning/src/query/checkout.py
```

## Output Example

```
┌────────────────────────────────────┐
│    Emergent Learning Framework     │
├────────────────────────────────────┤
│                                    │
│      Session Complete              │
│      Auto-capturing learnings...   │
│                                    │
└────────────────────────────────────┘

[*] Session Summary (auto-detected)
   Domains: infrastructure, backend
   Commits: 3
   Files modified: 7
     - src/query/checkin.py
     - src/query/checkout.py
     ... and 5 more
   Heuristics recorded: 2

[OK] Checkout complete.
```

## What Gets Captured

- **Domains**: Auto-detected from file paths (dashboard, frontend, backend, infrastructure)
- **Commits**: Count of recent commits in the repo
- **Files**: List of recently modified files
- **Heuristics**: Count from database (last 4 hours)

## Philosophy

Checkout should be frictionless. Record learnings during the session using:
- `[LEARNED:domain] pattern` markers in subagent outputs
- `record-heuristic.py` script when you discover something
- Failure analysis files when things break

Checkout just summarizes what happened - it doesn't interrogate you at the end.

## Complementing /checkin

| Command | Purpose |
|---------|---------|
| `/checkin` | Load context at session start |
| `/checkout` | Show session summary at end |
