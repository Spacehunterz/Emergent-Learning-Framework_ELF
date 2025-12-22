#!/usr/bin/env python3
"""
Get Last Prompts - Retrieve user prompts from previous Claude Code sessions.

Usage:
    python get_last_prompts.py                  # Last 5 prompts from most recent session
    python get_last_prompts.py --limit 10       # Last 10 prompts
    python get_last_prompts.py --all-sessions   # Search across recent sessions
    python get_last_prompts.py --json           # Output as JSON

Fast, error-free retrieval of what you asked in previous sessions.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def get_claude_projects_dir() -> Path:
    """Get the Claude Code projects directory."""
    return Path.home() / ".claude" / "projects"


def get_current_project_dir() -> Optional[Path]:
    """Get the project directory for emergent-learning."""
    projects_dir = get_claude_projects_dir()

    # Look for emergent-learning project
    for pattern in ["*emergent-learning*", "*claude-emergent*"]:
        matches = list(projects_dir.glob(pattern))
        if matches:
            return matches[0]

    return None


def get_session_files(project_dir: Path, limit: int = 5) -> List[Path]:
    """Get recent session files, sorted by modification time."""
    if not project_dir.exists():
        return []

    # Get all JSONL files that aren't agent files
    files = []
    for f in project_dir.glob("*.jsonl"):
        if not f.name.startswith("agent-"):
            try:
                mtime = f.stat().st_mtime
                files.append((mtime, f))
            except OSError:
                continue

    # Sort by modification time, newest first
    files.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in files[:limit]]


def extract_user_prompts(session_file: Path) -> List[Dict]:
    """Extract actual user prompts from a session file."""
    prompts = []

    try:
        with open(session_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)

                    # Only process user messages
                    if entry.get('type') != 'user':
                        continue

                    message = entry.get('message', {})
                    content = None

                    if isinstance(message, str):
                        content = message
                    elif isinstance(message, dict):
                        content = message.get('content', '')

                    # Skip tool results (they start with [{)
                    if not content or not isinstance(content, str):
                        continue
                    if content.strip().startswith('[{'):
                        continue

                    # Get timestamp
                    ts = entry.get('timestamp', '')

                    prompts.append({
                        'prompt': content.strip(),
                        'timestamp': ts,
                        'session_file': session_file.name
                    })

                except json.JSONDecodeError:
                    continue

    except (OSError, IOError) as e:
        print(f"Warning: Could not read {session_file}: {e}", file=sys.stderr)

    return prompts


def format_output(prompts: List[Dict], as_json: bool = False) -> str:
    """Format prompts for display."""
    if as_json:
        return json.dumps(prompts, indent=2, ensure_ascii=False)

    if not prompts:
        return "No user prompts found."

    lines = []
    lines.append(f"\n{'='*50}")
    lines.append(f"  LAST {len(prompts)} USER PROMPTS")
    lines.append(f"{'='*50}\n")

    for i, p in enumerate(prompts, 1):
        ts = p.get('timestamp', '')[:19].replace('T', ' ') if p.get('timestamp') else 'Unknown time'
        prompt = p['prompt']

        # Truncate long prompts for display
        if len(prompt) > 200:
            prompt = prompt[:200] + "..."

        lines.append(f"[{i}] {ts}")
        lines.append(f"    {prompt}")
        lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve user prompts from previous Claude Code sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python get_last_prompts.py                  # Last 5 prompts
    python get_last_prompts.py --limit 10       # Last 10 prompts
    python get_last_prompts.py --all-sessions   # Search multiple sessions
    python get_last_prompts.py --json           # JSON output
        """
    )

    parser.add_argument('--limit', type=int, default=5,
                        help='Number of prompts to retrieve (default: 5)')
    parser.add_argument('--all-sessions', action='store_true',
                        help='Search across multiple recent sessions')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--project-dir', type=str,
                        help='Override project directory path')

    args = parser.parse_args()

    # Find project directory
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = get_current_project_dir()

    if not project_dir or not project_dir.exists():
        print("Error: Could not find Claude Code project directory", file=sys.stderr)
        return 1

    # Get session files
    session_limit = 5 if args.all_sessions else 2
    session_files = get_session_files(project_dir, limit=session_limit)

    if not session_files:
        print("Error: No session files found", file=sys.stderr)
        return 1

    # Extract prompts
    all_prompts = []
    for session_file in session_files:
        prompts = extract_user_prompts(session_file)
        all_prompts.extend(prompts)

        # If not searching all sessions, just use the most recent non-empty one
        if not args.all_sessions and prompts:
            break

    # Sort by timestamp and limit
    all_prompts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    all_prompts = all_prompts[:args.limit]

    # Reverse to show oldest first (chronological order)
    all_prompts.reverse()

    # Output
    print(format_output(all_prompts, as_json=args.json))

    return 0 if all_prompts else 1


if __name__ == '__main__':
    sys.exit(main())
