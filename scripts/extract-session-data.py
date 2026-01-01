#!/usr/bin/env python3
"""
Extract session data from JSONL files for summarization.

This script extracts structured data without LLM calls.
Use the output with Claude Code's Task tool (haiku model) for summarization.

Usage:
    python extract-session-data.py <session_id>
    python extract-session-data.py --previous       # Get previous session
    python extract-session-data.py --previous --json # Output as JSON
"""

import json
import sys
import argparse
from pathlib import Path
from collections import Counter
from typing import Optional, Dict, Any

PROJECTS_DIR = Path.home() / ".claude" / "projects"


def find_session_file(session_id: str) -> Optional[Path]:
    """Find the JSONL file for a session ID."""
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        jsonl_path = project_dir / f"{session_id}.jsonl"
        if jsonl_path.exists():
            return jsonl_path
    return None


def get_previous_session() -> Optional[tuple[str, Path]]:
    """Get the previous session (second most recent non-agent session)."""
    if not PROJECTS_DIR.exists():
        return None

    jsonl_files = [
        f for f in PROJECTS_DIR.glob("*/*.jsonl")
        if not f.name.startswith("agent-")
    ]
    jsonl_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    if len(jsonl_files) >= 2:
        prev_file = jsonl_files[1]
        return prev_file.stem, prev_file

    return None


def extract_session_data(file_path: Path) -> Dict[str, Any]:
    """
    Extract structured data from session JSONL.
    Returns metadata suitable for LLM summarization.
    """
    tool_counts = Counter()
    files_touched = set()
    message_count = 0
    user_prompts = []
    assistant_snippets = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Skip sidechains
                if data.get("isSidechain"):
                    continue

                msg_type = data.get("type")
                if msg_type == "user":
                    message_count += 1
                    msg_content = data.get("message", {}).get("content", "")
                    if isinstance(msg_content, str) and msg_content.strip():
                        user_prompts.append(msg_content[:200])
                    elif isinstance(msg_content, list):
                        for item in msg_content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                user_prompts.append(item.get("text", "")[:200])
                                break

                elif msg_type == "assistant":
                    msg_content = data.get("message", {}).get("content", [])
                    if isinstance(msg_content, list):
                        for item in msg_content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text = item.get("text", "")
                                    if text and len(text) > 50:
                                        assistant_snippets.append(text[:150])
                                elif item.get("type") == "tool_use":
                                    tool_name = item.get("name", "unknown")
                                    tool_counts[tool_name] += 1

                                    tool_input = item.get("input", {})
                                    if isinstance(tool_input, dict):
                                        for key in ["file_path", "path", "filepath"]:
                                            if key in tool_input:
                                                files_touched.add(tool_input[key])

    except Exception as e:
        return {"error": str(e)}

    return {
        "session_id": file_path.stem,
        "project": file_path.parent.name,
        "message_count": message_count,
        "tool_counts": dict(tool_counts),
        "files_touched": list(files_touched)[:30],
        "user_prompts": user_prompts[:10],
        "assistant_snippets": assistant_snippets[:5],
        "file_size": file_path.stat().st_size
    }


def main():
    parser = argparse.ArgumentParser(description="Extract session data for summarization")
    parser.add_argument("session_id", nargs="?", help="Session ID to extract")
    parser.add_argument("--previous", action="store_true", help="Extract previous session")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Determine which session to extract
    if args.previous:
        result = get_previous_session()
        if not result:
            print("No previous session found", file=sys.stderr)
            return 1
        session_id, file_path = result
    elif args.session_id:
        session_id = args.session_id
        file_path = find_session_file(session_id)
        if not file_path:
            print(f"Session file not found: {session_id}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    # Extract data
    data = extract_session_data(file_path)

    if "error" in data:
        print(f"Error: {data['error']}", file=sys.stderr)
        return 1

    # Output
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Session: {data['session_id']}")
        print(f"Project: {data['project']}")
        print(f"Messages: {data['message_count']}")
        print(f"Tools: {data['tool_counts']}")
        print(f"Files: {len(data['files_touched'])} touched")
        if data['user_prompts']:
            print(f"First prompt: {data['user_prompts'][0][:80]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
