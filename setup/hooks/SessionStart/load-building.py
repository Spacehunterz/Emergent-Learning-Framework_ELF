#!/usr/bin/env python3
"""
Session Start Hook - Load Building Context + Session Memory

Automatically loads context from the Emergent Learning Framework
and triggers summarization of the previous session.
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime


def reset_enforcer_state():
    """Reset the golden-rule-enforcer state so it recognizes we've queried."""
    state_file = Path.home() / ".claude" / "hooks" / "investigation-state.json"
    state = {
        "investigation_count": 0,
        "last_query_time": datetime.now().isoformat(),
        "session_start": datetime.now().isoformat()
    }
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception:
        return False


def find_previous_session():
    """Find the previous session's JSONL file (not current, not agent files)."""
    projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        return None

    # Find project dir based on cwd
    cwd = os.getcwd()
    project_name = 'C-' + cwd.replace(os.sep, '-').replace(':', '-').replace('/', '-')
    sessions_dir = projects_dir / project_name

    if not sessions_dir.exists():
        # Try most recent project
        dirs = [p for p in projects_dir.iterdir() if p.is_dir()]
        if dirs:
            sessions_dir = max(dirs, key=lambda p: p.stat().st_mtime)
        else:
            return None

    # Get all non-agent session files, sorted by mtime
    session_files = []
    for f in sessions_dir.glob("*.jsonl"):
        if not f.name.startswith("agent-"):
            session_files.append(f)

    if len(session_files) < 2:
        return None  # No previous session

    # Sort by modification time, most recent first
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Return the SECOND most recent (previous session)
    return session_files[1]


def check_summary_exists(session_file):
    """Check if a summary already exists for this session."""
    summaries_dir = Path.home() / ".claude" / "emergent-learning" / "memory" / "sessions"

    if not summaries_dir.exists():
        return False

    # Check by looking at session file mtime and comparing to summary mtimes
    session_mtime = session_file.stat().st_mtime
    session_time = datetime.fromtimestamp(session_mtime)

    for summary_file in summaries_dir.glob("*.md"):
        # Extract date from filename (YYYY-MM-DD-HH-MM-*.md)
        try:
            parts = summary_file.stem.split("-")
            if len(parts) >= 5:
                summary_time = datetime(
                    int(parts[0]), int(parts[1]), int(parts[2]),
                    int(parts[3]), int(parts[4])
                )
                # If summary is within 15 minutes of session, consider it matched
                diff = abs((summary_time - session_time).total_seconds())
                if diff < 900:  # 15 minutes
                    return True
        except (ValueError, IndexError):
            continue

    return False


def main():
    print("[SessionStart] Hook fired", flush=True)

    base_dir = Path.home() / ".claude" / "emergent-learning"
    query_script = base_dir / "query" / "query.py"

    if not query_script.exists():
        print(f"[SessionStart] ERROR: query.py not found at {query_script}", flush=True)
        return

    try:
        print("[SessionStart] Running query.py...", flush=True)
        result = subprocess.run(
            [sys.executable, str(query_script), "--context"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("[SessionStart] Building context loaded. Golden rules active.", flush=True)
            # Reset enforcer state so it knows we've queried
            if reset_enforcer_state():
                print("[SessionStart] Enforcer state reset (30 min cooldown active).", flush=True)
        else:
            print(f"[SessionStart] Query failed: {result.stderr}", flush=True)

    except subprocess.TimeoutExpired:
        print("[SessionStart] ERROR: Query timed out after 10s", flush=True)
    except Exception as e:
        print(f"[SessionStart] ERROR: {e}", flush=True)

    # Check for previous session to summarize
    try:
        prev_session = find_previous_session()
        if prev_session and not check_summary_exists(prev_session):
            print(f"[SessionStart] SUMMARIZE_PREVIOUS: {prev_session}", flush=True)
    except Exception as e:
        print(f"[SessionStart] Session check error: {e}", flush=True)


if __name__ == "__main__":
    main()
