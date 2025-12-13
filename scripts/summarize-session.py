#!/usr/bin/env python3
"""
Session Summarizer - Uses Haiku to generate compact session summaries.

Designed to be called as a background agent or CLI tool.
Reads raw session JSONL, extracts key info, generates summary via Claude.

Usage:
    python summarize-session.py <session_id>
    python summarize-session.py --batch --older-than 1h
    python summarize-session.py --all-unsummarized
"""

import json
import sqlite3
import sys
import os
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import Counter

# Paths
ELF_DIR = Path.home() / ".claude" / "emergent-learning"
PROJECTS_DIR = Path.home() / ".claude" / "projects"
DB_PATH = ELF_DIR / "memory" / "index.db"


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def find_session_file(session_id: str) -> Optional[Path]:
    """Find the JSONL file for a session ID."""
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        jsonl_path = project_dir / f"{session_id}.jsonl"
        if jsonl_path.exists():
            return jsonl_path
    return None


def extract_session_data(file_path: Path) -> Dict[str, Any]:
    """
    Extract structured data from session JSONL without loading full content.
    Returns metadata and truncated summaries suitable for haiku processing.
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
                    # Extract user prompt (first 200 chars)
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

                                    # Extract file paths from tool inputs
                                    tool_input = item.get("input", {})
                                    if isinstance(tool_input, dict):
                                        for key in ["file_path", "path", "filepath"]:
                                            if key in tool_input:
                                                files_touched.add(tool_input[key])

    except Exception as e:
        return {"error": str(e)}

    return {
        "message_count": message_count,
        "tool_counts": dict(tool_counts),
        "files_touched": list(files_touched)[:50],  # Cap at 50 files
        "user_prompts": user_prompts[:10],  # First 10 prompts
        "assistant_snippets": assistant_snippets[:5],  # First 5 snippets
        "file_size": file_path.stat().st_size
    }


def generate_summary_prompt(session_data: Dict[str, Any], session_id: str) -> str:
    """Create a prompt for haiku to summarize the session."""
    tool_str = ", ".join(f"{k}: {v}" for k, v in session_data.get("tool_counts", {}).items())
    files_str = "\n".join(f"  - {f}" for f in session_data.get("files_touched", [])[:20])
    prompts_str = "\n".join(f"  - {p}" for p in session_data.get("user_prompts", [])[:5])

    return f"""Summarize this Claude Code session concisely. Return JSON only.

Session ID: {session_id}
Messages: {session_data.get('message_count', 0)}
Tools used: {tool_str or 'none'}
Files touched:
{files_str or '  (none)'}

User prompts (first few):
{prompts_str or '  (none)'}

Return this exact JSON structure (no markdown, just raw JSON):
{{
  "tool_summary": "<one line: what tools were used and how many times>",
  "content_summary": "<one line: what files/code was worked on>",
  "conversation_summary": "<one line: what the user asked for and what was done>"
}}"""


def call_haiku(prompt: str) -> Optional[Dict[str, Any]]:
    """Call Claude haiku via claude CLI to generate summary."""
    try:
        # Use claude CLI in print mode with haiku model
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "haiku"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"Claude CLI error: {result.stderr}", file=sys.stderr)
            return None

        # Parse JSON from response
        response = result.stdout.strip()
        # Try to extract JSON from response
        try:
            # Handle case where response has extra text
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        return None

    except subprocess.TimeoutExpired:
        print("Haiku call timed out", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("Claude CLI not found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error calling haiku: {e}", file=sys.stderr)
        return None


def generate_fallback_summary(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a basic summary without LLM when haiku fails."""
    tool_counts = session_data.get("tool_counts", {})
    files = session_data.get("files_touched", [])

    # Tool summary
    if tool_counts:
        parts = [f"{v}x {k}" for k, v in sorted(tool_counts.items(), key=lambda x: -x[1])[:5]]
        tool_summary = f"Used {', '.join(parts)}"
    else:
        tool_summary = "No tool usage recorded"

    # Content summary
    if files:
        # Group by directory
        dirs = set(str(Path(f).parent) for f in files[:10])
        content_summary = f"Worked on {len(files)} files in {len(dirs)} directories"
    else:
        content_summary = "No files modified"

    # Conversation summary from first prompt
    prompts = session_data.get("user_prompts", [])
    if prompts:
        first_prompt = prompts[0][:100]
        conversation_summary = f"Started with: {first_prompt}..."
    else:
        conversation_summary = "Session content not available"

    return {
        "tool_summary": tool_summary,
        "content_summary": content_summary,
        "conversation_summary": conversation_summary
    }


def summarize_session(session_id: str, use_llm: bool = True) -> bool:
    """
    Summarize a single session and store in database.

    Args:
        session_id: The session UUID
        use_llm: Whether to use haiku (True) or fallback summary (False)

    Returns:
        True if successful, False otherwise
    """
    # Find session file
    file_path = find_session_file(session_id)
    if not file_path:
        print(f"Session file not found: {session_id}", file=sys.stderr)
        return False

    project = file_path.parent.name

    # Extract session data
    session_data = extract_session_data(file_path)
    if "error" in session_data:
        print(f"Error extracting session data: {session_data['error']}", file=sys.stderr)
        return False

    # Generate summary
    if use_llm:
        prompt = generate_summary_prompt(session_data, session_id)
        summary = call_haiku(prompt)
        if not summary:
            print(f"Haiku failed, using fallback summary", file=sys.stderr)
            summary = generate_fallback_summary(session_data)
            model = "fallback"
        else:
            model = "haiku"
    else:
        summary = generate_fallback_summary(session_data)
        model = "fallback"

    # Store in database
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO session_summaries (
                session_id, project,
                tool_summary, content_summary, conversation_summary,
                files_touched, tool_counts, message_count,
                session_file_path, session_file_size, session_last_modified,
                summarized_at, summarizer_model, is_stale
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 0)
        """, (
            session_id,
            project,
            summary.get("tool_summary", ""),
            summary.get("content_summary", ""),
            summary.get("conversation_summary", ""),
            json.dumps(session_data.get("files_touched", [])),
            json.dumps(session_data.get("tool_counts", {})),
            session_data.get("message_count", 0),
            str(file_path),
            session_data.get("file_size", 0),
            datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            model
        ))
        conn.commit()
        print(f"Summarized {session_id} ({model})")
        return True

    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


def get_unsummarized_sessions(older_than_hours: float = 1.0) -> List[str]:
    """Get list of session IDs that need summarization."""
    unsummarized = []
    cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

    conn = get_db()
    cursor = conn.cursor()

    # Get already summarized sessions
    cursor.execute("SELECT session_id FROM session_summaries WHERE is_stale = 0")
    summarized = set(row[0] for row in cursor.fetchall())
    conn.close()

    # Scan projects for unsummarized sessions
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            # Skip agent files
            if jsonl_file.name.startswith("agent-"):
                continue

            session_id = jsonl_file.stem

            # Skip if already summarized
            if session_id in summarized:
                continue

            # Check if file is old enough
            file_mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
            if file_mtime < cutoff_time:
                unsummarized.append(session_id)

    return unsummarized


def main():
    parser = argparse.ArgumentParser(description="Summarize Claude sessions with haiku")
    parser.add_argument("session_id", nargs="?", help="Session ID to summarize")
    parser.add_argument("--batch", action="store_true", help="Batch summarize multiple sessions")
    parser.add_argument("--older-than", type=str, default="1h", help="Only sessions older than (e.g., 1h, 30m)")
    parser.add_argument("--limit", type=int, default=10, help="Max sessions to process in batch")
    parser.add_argument("--no-llm", action="store_true", help="Use fallback summary (no API call)")
    parser.add_argument("--list-unsummarized", action="store_true", help="List unsummarized sessions")

    args = parser.parse_args()

    # Parse time threshold
    older_than_str = args.older_than
    if older_than_str.endswith("h"):
        older_than_hours = float(older_than_str[:-1])
    elif older_than_str.endswith("m"):
        older_than_hours = float(older_than_str[:-1]) / 60
    else:
        older_than_hours = float(older_than_str)

    if args.list_unsummarized:
        sessions = get_unsummarized_sessions(older_than_hours)
        print(f"Found {len(sessions)} unsummarized sessions (older than {args.older_than}):")
        for sid in sessions[:20]:
            print(f"  {sid}")
        if len(sessions) > 20:
            print(f"  ... and {len(sessions) - 20} more")
        return 0

    if args.session_id:
        # Summarize single session
        success = summarize_session(args.session_id, use_llm=not args.no_llm)
        return 0 if success else 1

    if args.batch:
        # Batch summarize
        sessions = get_unsummarized_sessions(older_than_hours)
        print(f"Found {len(sessions)} unsummarized sessions, processing up to {args.limit}")

        success_count = 0
        for session_id in sessions[:args.limit]:
            if summarize_session(session_id, use_llm=not args.no_llm):
                success_count += 1

        print(f"Summarized {success_count}/{min(len(sessions), args.limit)} sessions")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
