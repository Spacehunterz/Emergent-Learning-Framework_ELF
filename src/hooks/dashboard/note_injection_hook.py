#!/usr/bin/env python3
"""
Note Injection Hook - Injects dashboard notes into Claude's context.

This PreToolUse hook checks for new notes added via the dashboard and
injects them as system reminders so Claude sees user feedback in real-time.

How it works:
1. Finds the current session by looking for recently modified task files
2. Scans tasks for notes with source='dashboard'
3. Tracks which notes have been "seen" using a state file
4. Injects unseen notes into the tool's context
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Paths
TASKS_DIR = Path.home() / ".claude" / "tasks"
STATE_FILE = Path.home() / ".claude" / "hooks" / "dashboard" / "seen-notes.json"


def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError, ValueError):
        return {}


def output_result(result: dict):
    """Output hook result to stdout."""
    print(json.dumps(result))


def load_seen_notes() -> Dict[str, Set[str]]:
    """Load the set of note IDs that have been seen.

    Returns dict mapping session_id -> set of note keys (task_id:timestamp)
    """
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            # Convert lists back to sets
            return {k: set(v) for k, v in data.items()}
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_seen_notes(seen: Dict[str, Set[str]]):
    """Save seen notes state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Convert sets to lists for JSON
    data = {k: list(v) for k, v in seen.items()}
    STATE_FILE.write_text(json.dumps(data, indent=2))


def find_active_session() -> Optional[str]:
    """Find the most recently active session with tasks.

    Returns session_id or None.
    """
    if not TASKS_DIR.exists():
        return None

    # Find session with most recently modified task file
    latest_mtime = 0
    latest_session = None

    for session_dir in TASKS_DIR.iterdir():
        if not session_dir.is_dir():
            continue

        # Count task files in this session
        task_files = list(session_dir.glob("*.json"))
        if not task_files:
            continue  # Skip sessions with no tasks

        # Check for .lock file (indicates active session) AND has tasks
        lock_file = session_dir / ".lock"
        if lock_file.exists():
            # Active session with tasks - check if it's the most recent
            for task_file in task_files:
                try:
                    mtime = task_file.stat().st_mtime
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_session = session_dir.name
                except OSError:
                    pass
        else:
            # Check modification times for non-locked sessions too
            for task_file in task_files:
                try:
                    mtime = task_file.stat().st_mtime
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                        latest_session = session_dir.name
                except OSError:
                    pass

    return latest_session


def get_unseen_dashboard_notes(session_id: str, seen_notes: Dict[str, Set[str]]) -> List[Dict]:
    """Get all dashboard notes that haven't been seen yet.

    Returns list of {task_id, task_subject, note_text, timestamp}
    """
    session_dir = TASKS_DIR / session_id
    if not session_dir.exists():
        return []

    session_seen = seen_notes.get(session_id, set())
    unseen = []

    for task_file in session_dir.glob("*.json"):
        try:
            task_data = json.loads(task_file.read_text())
            task_id = task_data.get("id", task_file.stem)
            task_subject = task_data.get("subject", "Unknown task")

            notes = task_data.get("notes", [])
            for note in notes:
                # Only process dashboard notes
                if note.get("source") != "dashboard":
                    continue

                # Create unique key for this note
                note_key = f"{task_id}:{note.get('timestamp', '')}"

                if note_key not in session_seen:
                    unseen.append({
                        "task_id": task_id,
                        "task_subject": task_subject,
                        "note_text": note.get("text", ""),
                        "timestamp": note.get("timestamp", ""),
                        "note_key": note_key
                    })
        except (json.JSONDecodeError, IOError):
            pass

    # Sort by timestamp
    unseen.sort(key=lambda x: x.get("timestamp", ""))
    return unseen


def format_notes_injection(notes: List[Dict]) -> str:
    """Format notes for injection into context."""
    if not notes:
        return ""

    lines = [
        "",
        "---",
        "## 📬 Dashboard Notes (User Feedback)",
        "",
        "The following notes were added from the dashboard:",
        ""
    ]

    for note in notes:
        timestamp = note.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except ValueError:
                time_str = timestamp
        else:
            time_str = "unknown time"

        lines.append(f"**[Task #{note['task_id']}: {note['task_subject']}]** ({time_str})")
        lines.append(f"> {note['note_text']}")
        lines.append("")

    lines.extend([
        "Please acknowledge these notes and incorporate the feedback.",
        "---",
        ""
    ])

    return "\n".join(lines)


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    tool_name = hook_input.get("tool_name", hook_input.get("tool"))
    tool_input = hook_input.get("tool_input", hook_input.get("input", {}))

    if not tool_name:
        output_result({"decision": "approve"})
        return

    # Find active session
    session_id = find_active_session()
    if not session_id:
        output_result({"decision": "approve"})
        return

    # Load seen notes
    seen_notes = load_seen_notes()

    # Get unseen dashboard notes
    unseen = get_unseen_dashboard_notes(session_id, seen_notes)

    if not unseen:
        output_result({"decision": "approve"})
        return

    # Mark notes as seen
    if session_id not in seen_notes:
        seen_notes[session_id] = set()
    for note in unseen:
        seen_notes[session_id].add(note["note_key"])
    save_seen_notes(seen_notes)

    # Format injection
    injection = format_notes_injection(unseen)

    # For Task tool, append to prompt
    if tool_name == "Task" and "prompt" in tool_input:
        modified_input = tool_input.copy()
        modified_input["prompt"] = tool_input["prompt"] + injection
        output_result({
            "decision": "approve",
            "tool_input": modified_input,
            "message": injection
        })
    else:
        # For other tools, return message in the result
        # This should be displayed to Claude as context
        output_result({
            "decision": "approve",
            "message": injection
        })


if __name__ == "__main__":
    main()
