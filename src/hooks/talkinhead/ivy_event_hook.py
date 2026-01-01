#!/usr/bin/env python3
"""
Ivy Event Hook - Triggers TalkinHead avatar speech.

This hook writes events to ~/.claude/ivy_events.json which TalkinHead monitors.
Supports different event types based on tool usage patterns.

Usage in settings.json hooks:
  PreToolUse/PostToolUse with matcher to trigger specific phrases.
"""

import json
import sys
import time
from pathlib import Path

EVENT_FILE = Path.home() / ".claude" / "ivy_events.json"


def write_event(event_type: str, message: str = ""):
    """Write an event for TalkinHead to pick up."""
    event = {
        "event": event_type,
        "message": message,
        "timestamp": time.time()
    }
    EVENT_FILE.write_text(json.dumps(event))


def main():
    """
    Hook entry point. Reads stdin for hook context.

    Environment variables or stdin JSON can specify the event type.
    """
    import os

    # Get event type from environment or default
    event_type = os.environ.get("IVY_EVENT", "thinking")
    message = os.environ.get("IVY_MESSAGE", "")

    # Try to read stdin for hook context
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data.strip():
                hook_data = json.loads(stdin_data)

                # Determine event based on hook context
                tool_name = hook_data.get("tool_name", "")
                hook_type = hook_data.get("hook_type", "")

                # Map tools to events
                if hook_type == "PreToolUse":
                    if tool_name == "Grep":
                        event_type = "searching"
                    elif tool_name == "Task":
                        event_type = "thinking"
                    elif tool_name == "Bash":
                        cmd = hook_data.get("tool_input", {}).get("command", "")
                        if "git commit" in cmd:
                            event_type = "commit"
                        else:
                            event_type = "thinking"

                elif hook_type == "PostToolUse":
                    result = hook_data.get("tool_result", {})
                    is_error = result.get("is_error", False)

                    if is_error:
                        event_type = "error"
                    else:
                        # Don't trigger on every post-tool, too noisy
                        # Only trigger on significant completions
                        pass
    except (json.JSONDecodeError, KeyError):
        pass

    # Write the event
    if event_type:
        write_event(event_type, message)
        print(f"IVY: {event_type}")


if __name__ == "__main__":
    main()
