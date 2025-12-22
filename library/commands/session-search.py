#!/usr/bin/env python3
"""Session search script - called by /search command"""
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows encoding issues - force UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def get_relative_time(dt):
    """Convert datetime to relative time string"""
    now = datetime.now()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        mins = int(diff.total_seconds() / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=2):
        return "yesterday"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime('%Y-%m-%d')

def load_session_summaries():
    """Load all session summaries from memory/sessions/*.md"""
    summaries = {}
    sessions_dir = Path.home() / '.claude' / 'emergent-learning' / 'memory' / 'sessions'

    if not sessions_dir.exists():
        return summaries

    for summary_file in sessions_dir.glob('*.md'):
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract title from first heading
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else summary_file.stem

            # Extract summary section
            summary_match = re.search(r'##\s+Summary\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
            summary_text = summary_match.group(1).strip() if summary_match else ''

            # Get file modification time as proxy for session time
            mtime = datetime.fromtimestamp(summary_file.stat().st_mtime)

            summaries[summary_file.stem] = {
                'title': title,
                'summary': summary_text,
                'time': mtime,
                'file': summary_file
            }
        except Exception as e:
            # Skip files that can't be parsed
            pass

    return summaries

def find_matching_summary(session_file, summaries):
    """Find a summary that matches this session by timestamp proximity"""
    session_time = datetime.fromtimestamp(session_file.stat().st_mtime)

    # Try to match within 10 minutes
    best_match = None
    best_diff = timedelta(minutes=10)

    for summary_data in summaries.values():
        time_diff = abs(summary_data['time'] - session_time)
        if time_diff < best_diff:
            best_diff = time_diff
            best_match = summary_data

    return best_match if best_diff < timedelta(minutes=10) else None

def main():
    cwd = os.getcwd()
    # Build project name from cwd
    project_name = 'C-' + cwd.replace(os.sep, '-').replace(':', '-').replace('/', '-')
    sessions_dir = Path.home() / '.claude' / 'projects' / project_name

    if not sessions_dir.exists():
        projects = Path.home() / '.claude' / 'projects'
        if projects.exists():
            dirs = [p for p in projects.iterdir() if p.is_dir()]
            if dirs:
                sessions_dir = max(dirs, key=lambda p: p.stat().st_mtime)

    if not sessions_dir.exists():
        print("No session logs found")
        return

    # Load all session summaries
    summaries = load_session_summaries()

    session_files = sorted(sessions_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime, reverse=True)
    main_sessions = [f for f in session_files if not f.name.startswith('agent-')]

    for i, session_file in enumerate(main_sessions[:5]):
        session_time = datetime.fromtimestamp(session_file.stat().st_mtime)
        relative_time = get_relative_time(session_time)

        # Find matching summary
        summary = find_matching_summary(session_file, summaries)

        if summary:
            # Use summary title and show summary
            print(f"\n=== SESSION: {summary['title']} ({relative_time}) ===")
            if summary['summary']:
                print(f"Summary: {summary['summary'][:200]}{'...' if len(summary['summary']) > 200 else ''}")
                print()
        else:
            # Fallback to basic format
            print(f"\n=== SESSION {i+1} ({relative_time}) ===")

        # Extract and show user prompts
        print("User prompts:")
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'user':
                        content = data.get('message', {}).get('content', '')
                        if isinstance(content, str) and content.strip():
                            if content.startswith('<') or content.startswith('Caveat:') or content.startswith('Unknown slash'):
                                continue
                            print(f"  > {content[:300]}")
                except:
                    pass

if __name__ == '__main__':
    main()
