#!/usr/bin/env python3
"""
Golden Rule Enforcer Hook
Enforces Golden Rule #1: "Query Before Acting"

This PreToolUse hook blocks investigation tools (Grep, Read, Bash, Task, Glob)
until the building has been queried via emergent-learning/query/query.py
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
STATE_FILE = Path.home() / ".claude" / "hooks" / "investigation-state.json"
INVESTIGATION_TOOLS = ["Grep", "Read", "Bash", "Task", "Glob"]
THRESHOLD = 3  # Max investigation tools before requiring building query
COOLDOWN_MINUTES = 30  # After querying, good for 30 minutes
OVERRIDE_ENV_VAR = "CLAUDE_SKIP_GOLDEN_RULE"

def load_state():
    """Load the current state from the state file."""
    if not STATE_FILE.exists():
        return {
            "investigation_count": 0,
            "last_query_time": None,
            "session_start": datetime.now().isoformat()
        }

    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            return state
    except (json.JSONDecodeError, IOError):
        # If file is corrupted, start fresh
        return {
            "investigation_count": 0,
            "last_query_time": None,
            "session_start": datetime.now().isoformat()
        }

def save_state(state):
    """Save the current state to the state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def is_building_query(tool_name, tool_input):
    """Check if this tool call is a building query."""
    if tool_name != "Bash":
        return False

    command = tool_input.get("command", "")
    return "emergent-learning/query/query.py" in command

def is_in_cooldown(last_query_time):
    """Check if we're still in cooldown period after a query."""
    if last_query_time is None:
        return False

    last_query = datetime.fromisoformat(last_query_time)
    cooldown_end = last_query + timedelta(minutes=COOLDOWN_MINUTES)
    return datetime.now() < cooldown_end

def format_time_remaining(last_query_time):
    """Format remaining cooldown time in a human-readable way."""
    last_query = datetime.fromisoformat(last_query_time)
    cooldown_end = last_query + timedelta(minutes=COOLDOWN_MINUTES)
    remaining = cooldown_end - datetime.now()

    minutes = int(remaining.total_seconds() / 60)
    seconds = int(remaining.total_seconds() % 60)

    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def should_block(tool_name, tool_input, state):
    """Determine if this tool call should be blocked."""
    # Check for override
    if os.environ.get(OVERRIDE_ENV_VAR):
        return False, None

    # If this is a building query, allow it
    if is_building_query(tool_name, tool_input):
        return False, None

    # If not an investigation tool, allow it
    if tool_name not in INVESTIGATION_TOOLS:
        return False, None

    # If we're in cooldown period, allow it
    if is_in_cooldown(state.get("last_query_time")):
        return False, None

    # Check if we've hit the threshold
    count = state.get("investigation_count", 0)
    if count >= THRESHOLD:
        time_info = ""
        if state.get("last_query_time"):
            time_info = f"\n\nLast query was more than {COOLDOWN_MINUTES} minutes ago. Query again to continue."

        reason = f"""🏢 Golden Rule #1: Query Before Acting

You've used {count} investigation tools without querying the building.

The building contains institutional knowledge that could:
- Save you from repeating past failures
- Provide proven heuristics for this type of task
- Alert you to ongoing experiments or CEO decisions
- Guide your approach with hard-won lessons

Query the building first:
  python ~/.claude/emergent-learning/query/query.py --context

Or for domain-specific guidance:
  python ~/.claude/emergent-learning/query/query.py --domain [domain]

Override (emergency only): export {OVERRIDE_ENV_VAR}=1{time_info}"""

        return True, reason

    return False, None

def update_state_for_tool(tool_name, tool_input, state):
    """Update state based on the tool being called."""
    # If this is a building query, reset the counter and update timestamp
    if is_building_query(tool_name, tool_input):
        state["investigation_count"] = 0
        state["last_query_time"] = datetime.now().isoformat()
    # If it's an investigation tool and not in cooldown, increment counter
    elif tool_name in INVESTIGATION_TOOLS and not is_in_cooldown(state.get("last_query_time")):
        state["investigation_count"] = state.get("investigation_count", 0) + 1

    return state

def main():
    """Main hook execution."""
    try:
        # Read stdin for tool call information
        input_data = json.loads(sys.stdin.read())
        tool_name = input_data.get("tool_name", input_data.get("tool"))
        tool_input = input_data.get("tool_input", input_data.get("input", {}))

        # Load current state
        state = load_state()

        # Check if we should block
        block, reason = should_block(tool_name, tool_input, state)

        if block:
            # Output block decision
            result = {
                "decision": "block",
                "reason": reason
            }
            print(json.dumps(result))
            save_state(state)
            sys.exit(0)

        # Update state for this tool
        state = update_state_for_tool(tool_name, tool_input, state)
        save_state(state)

        # Approve the tool use
        result = {"decision": "approve"}
        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        # On any error, fail open (approve the tool use)
        # This ensures the hook doesn't break normal operation
        result = {
            "decision": "approve",
            "note": f"Hook error (failing open): {str(e)}"
        }
        print(json.dumps(result))
        sys.exit(0)

if __name__ == "__main__":
    main()
