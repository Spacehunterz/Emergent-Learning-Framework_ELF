#!/usr/bin/env python3
"""
Self-Perpetuating Watcher Loop

This generates the complete watcher prompt that includes instructions
for the watcher to spawn the next iteration using the Task tool.

Design:
    Watcher (Haiku) → analyzes state → outputs status
    If nominal → spawns next Watcher (Haiku)
    If escalate → spawns Handler (Opus)
    Handler → makes decision → spawns next Watcher (Haiku)

    This creates an infinite monitoring loop until swarm completes.

Usage:
    python watcher_loop.py start     # Print prompt to start loop
    python watcher_loop.py stop      # Create stop signal file
    python watcher_loop.py status    # Check if watcher is active
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Paths
COORDINATION_DIR = Path.home() / ".claude" / "emergent-learning" / ".coordination"
BLACKBOARD_FILE = COORDINATION_DIR / "blackboard.json"
WATCHER_LOG = COORDINATION_DIR / "watcher-log.md"
STOP_FILE = COORDINATION_DIR / "watcher-stop"


def gather_state() -> Dict[str, Any]:
    """Gather current coordination state."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "blackboard": {},
        "agent_files": [],
        "stop_requested": STOP_FILE.exists(),
    }

    if BLACKBOARD_FILE.exists():
        try:
            state["blackboard"] = json.loads(BLACKBOARD_FILE.read_text())
        except:
            state["blackboard"] = {"error": "Could not parse blackboard.json"}

    for f in COORDINATION_DIR.glob("agent_*.md"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        age_seconds = (datetime.now() - mtime).total_seconds()
        state["agent_files"].append({
            "name": f.name,
            "age_seconds": round(age_seconds),
            "size_bytes": f.stat().st_size,
        })

    return state


def get_watcher_prompt(state: Dict[str, Any], interval_seconds: int = 45) -> str:
    """
    Generate the self-perpetuating watcher prompt.

    The watcher agent will:
    1. Analyze the provided state
    2. Output status (nominal/escalate)
    3. Spawn the next agent (watcher or handler) using Task tool
    """
    return f'''You are a self-perpetuating monitoring agent for a multi-agent swarm.

## Current Coordination State

```json
{json.dumps(state, indent=2)}
```

## Your Tasks

### 1. Analyze State

Check for problems:
- Stale agents (no update > 120 seconds)
- Errors in blackboard
- Stuck tasks
- Deadlocks

### 2. Output Status

```
STATUS: nominal
NOTES: [brief observation]
```

OR if problem found:

```
STATUS: escalate
REASON: [what's wrong]
AFFECTED: [which agents]
SEVERITY: [low/medium/high]
```

### 3. CRITICAL: Spawn Next Agent

**You MUST use the Task tool at the end of your response.**

If STATUS was `nominal`:
- Wait {interval_seconds} seconds (sleep command)
- Then spawn the next watcher (yourself, essentially)

If STATUS was `escalate`:
- Spawn the Opus handler to decide what to do

**Stop conditions (do NOT spawn next agent):**
- `stop_requested` is true in state
- Blackboard shows all agents completed
- No active swarm (blackboard empty or missing)

## Task Tool Calls

### To spawn next watcher (nominal case):

Use Task tool with:
- description: "[WATCHER] Monitor swarm"
- subagent_type: "general-purpose"
- model: "haiku"
- run_in_background: true
- prompt: (copy from below)

Watcher prompt to use:
```
You are a monitoring agent. Read coordination state from ~/.claude/emergent-learning/.coordination/

Check: blackboard.json, agent_*.md files, watcher-log.md

Look for: stale agents (>120s), errors, stuck tasks, deadlocks.

Output:
- "STATUS: nominal" + notes if OK
- "STATUS: escalate" + reason/affected/severity if problem

Then SPAWN NEXT AGENT using Task tool:
- If nominal: spawn another haiku watcher (model: haiku, run_in_background: true)
- If escalate: spawn opus handler (model: opus)
- If .coordination/watcher-stop exists or swarm complete: do NOT spawn

This creates a self-perpetuating monitoring loop.
```

### To spawn handler (escalate case):

Use Task tool with:
- description: "[HANDLER] Intervene in swarm"
- subagent_type: "general-purpose"
- model: "opus"
- prompt: Include the escalation details and ask Opus to decide action (RESTART/REASSIGN/SYNTHESIZE/ABORT/ESCALATE_TO_HUMAN)

## Important

- Always check for watcher-stop file before spawning
- Log your status to watcher-log.md
- Be concise - this runs frequently
- The loop continues until stopped or swarm completes
'''


def get_handler_prompt(escalation: Dict[str, Any]) -> str:
    """Generate prompt for Opus handler when escalation needed."""
    return f'''You are an intervention agent. The watcher detected an issue.

## Escalation

```json
{json.dumps(escalation, indent=2)}
```

## Full Context

Read: ~/.claude/emergent-learning/.coordination/
- blackboard.json (agent states)
- agent_*.md (outputs)
- watcher-log.md (history)

## Available Actions

1. **RESTART** - Reset stuck agent, let it retry
2. **REASSIGN** - Mark failed, put task back in queue
3. **SYNTHESIZE** - Collect partial outputs, create synthesis task
4. **ABORT** - Stop work on this task
5. **ESCALATE_TO_HUMAN** - Write to ceo-inbox/ for human decision

## Your Task

1. Analyze the situation
2. Decide on action
3. Write decision to .coordination/decision.md
4. **Spawn next watcher** to resume monitoring (Task tool, model: haiku, run_in_background: true)

Be decisive. Explain your reasoning briefly.
'''


def start_watcher_loop():
    """Print the initial watcher prompt to start the loop."""
    state = gather_state()
    prompt = get_watcher_prompt(state)

    print("=" * 60)
    print("TIERED WATCHER LOOP - Start Prompt")
    print("=" * 60)
    print()
    print("To start the watcher loop, use the Task tool with:")
    print()
    print("```")
    print("Task(")
    print('    description="[WATCHER] Monitor swarm",')
    print('    subagent_type="general-purpose",')
    print('    model="haiku",')
    print('    run_in_background=True,')
    print('    prompt="""')
    print(prompt[:2000])
    if len(prompt) > 2000:
        print("... [truncated for display]")
    print('"""')
    print(")")
    print("```")
    print()
    print("The watcher will self-perpetuate by spawning the next watcher.")
    print("To stop: python watcher_loop.py stop")


def stop_watcher_loop():
    """Create stop signal file."""
    COORDINATION_DIR.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text(f"Stop requested at {datetime.now().isoformat()}\n")
    print(f"Stop signal created: {STOP_FILE}")
    print("Watcher will stop after current iteration.")


def check_status():
    """Check if watcher loop is active."""
    print("=" * 40)
    print("Watcher Status")
    print("=" * 40)

    if STOP_FILE.exists():
        print(f"Stop requested: YES ({STOP_FILE.read_text().strip()})")
    else:
        print("Stop requested: NO")

    if WATCHER_LOG.exists():
        log = WATCHER_LOG.read_text()
        lines = log.strip().split("\n")
        print(f"Log entries: {log.count('## [')}")
        if lines:
            print(f"Last entry: {lines[-1][:60]}...")
    else:
        print("Log: Not started yet")

    state = gather_state()
    print(f"Active agents: {len(state['agent_files'])}")
    if state['blackboard']:
        agents = state['blackboard'].get('agents', {})
        print(f"Blackboard agents: {len(agents)}")


def clear_stop():
    """Clear the stop signal to allow restart."""
    if STOP_FILE.exists():
        STOP_FILE.unlink()
        print("Stop signal cleared. Watcher can be restarted.")
    else:
        print("No stop signal to clear.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python watcher_loop.py [start|stop|status|clear]")
        return

    cmd = sys.argv[1].lower()

    if cmd == "start":
        start_watcher_loop()
    elif cmd == "stop":
        stop_watcher_loop()
    elif cmd == "status":
        check_status()
    elif cmd == "clear":
        clear_stop()
    else:
        print(f"Unknown command: {cmd}")
        print("Use: start, stop, status, or clear")


if __name__ == "__main__":
    main()
