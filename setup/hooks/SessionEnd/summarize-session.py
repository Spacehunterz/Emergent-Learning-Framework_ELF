#!/usr/bin/env python3
"""
SessionEnd Hook - Trigger session summarization.

When a Claude session ends, queue it for summarization.
Uses fallback mode (no LLM) for immediate completion,
haiku summarization happens in background via dashboard API.
"""

import subprocess
import sys
import os
from pathlib import Path

# Script location
SUMMARIZER = Path.home() / ".claude" / "emergent-learning" / "scripts" / "summarize-session.py"


def get_current_session_id():
    """Try to get current session ID from environment or session file."""
    # Check if there's a session ID in env
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        return session_id

    # Try to find most recent session file
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    # Find most recently modified jsonl file
    newest = None
    newest_time = 0

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            if jsonl_file.name.startswith("agent-"):
                continue
            mtime = jsonl_file.stat().st_mtime
            if mtime > newest_time:
                newest_time = mtime
                newest = jsonl_file.stem

    return newest


def main():
    if not SUMMARIZER.exists():
        return

    session_id = get_current_session_id()
    if not session_id:
        return

    # Run summarizer with fallback mode (fast, no API call)
    # This creates basic summary immediately
    try:
        subprocess.run(
            [sys.executable, str(SUMMARIZER), session_id, "--no-llm"],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass  # Best effort - don't block session end


if __name__ == "__main__":
    main()
