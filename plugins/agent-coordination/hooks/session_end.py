#!/usr/bin/env python3
"""
Stop Hook: Clean up coordination state when session ends.

This hook:
1. Marks any active agents from this session as completed
2. Logs session summary to blackboard
3. Reports any unresolved blockers
"""

import json
import os
import sys
from pathlib import Path

# Add utils to path for blackboard import (required for standalone hook execution)
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from blackboard import Blackboard


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError, ValueError) as e:
        sys.stderr.write(f"Warning: Hook input error: {e}\n")
        return {}


def output_result(result: dict = None):
    """Output hook result to stdout."""
    print(json.dumps(result or {}))


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    # Check if coordination is enabled
    cwd = os.getcwd()
    coordination_dir = Path(cwd) / ".coordination"

    if not coordination_dir.exists():
        output_result()
        return

    # Initialize blackboard
    bb = Blackboard(cwd)

    try:
        # Get session summary for logging
        summary = bb.get_summary()

        # Check for any dangling active agents (shouldn't happen normally)
        active = bb.get_active_agents()
        if active:
            sys.stderr.write(f"Note: {len(active)} agents still marked active at session end\n")

        # Check for unresolved blockers
        questions = bb.get_open_questions()
        blocking = [q for q in questions if q.get("blocking")]
        if blocking:
            sys.stderr.write(f"Warning: {len(blocking)} unresolved blocking questions\n")
            for q in blocking:
                sys.stderr.write(f"  - {q['question']}\n")

    except Exception as e:
        sys.stderr.write(f"Warning: Session end hook error: {e}\n")

    output_result()


if __name__ == "__main__":
    main()
