#!/usr/bin/env python3
"""
Opus Learning Extractor Runner

Spawns an Opus agent to analyze session logs and extract learnings.
Designed to run in background (non-blocking) from session_integration.py.

Usage:
    python run_extractor.py <log_file1.jsonl> [log_file2.jsonl ...]
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Paths
EMERGENT_LEARNING_PATH = Path.home() / ".claude" / "emergent-learning"
PROMPT_PATH = EMERGENT_LEARNING_PATH / "agents" / "learning-extractor" / "PROMPT.md"
MEMORY_DB = EMERGENT_LEARNING_PATH / "memory" / "learnings.db"
PROPOSALS_PENDING = EMERGENT_LEARNING_PATH / "proposals" / "pending"
PROCESSED_MARKER = EMERGENT_LEARNING_PATH / "sessions" / ".processed"


def load_prompt() -> str:
    """Load the agent prompt from PROMPT.md."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding='utf-8')
    return ""


def load_existing_heuristics() -> List[Dict]:
    """Load existing heuristics from database for cross-referencing."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT domain, rule, explanation, confidence, is_golden
            FROM heuristics
            ORDER BY confidence DESC
            LIMIT 50
        """)

        heuristics = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return heuristics
    except Exception:
        return []


def load_recent_failures() -> List[Dict]:
    """Load recent failures from database."""
    if not MEMORY_DB.exists():
        return []

    try:
        conn = sqlite3.connect(str(MEMORY_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT title, summary, domain, tags
            FROM learnings
            WHERE type = 'failure'
            ORDER BY created_at DESC
            LIMIT 20
        """)

        failures = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return failures
    except Exception:
        return []


def load_session_logs(log_files: List[Path]) -> str:
    """Load and concatenate session log content."""
    all_entries = []

    for log_file in log_files:
        if not log_file.exists():
            continue

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entry['_source_file'] = log_file.name
                            all_entries.append(entry)
                        except json.JSONDecodeError:
                            continue
        except IOError:
            continue

    # Sort by timestamp
    all_entries.sort(key=lambda x: x.get('ts', ''))

    # Format for the agent
    lines = [f"# Session Logs ({len(log_files)} files, {len(all_entries)} entries)\n"]

    for entry in all_entries:
        ts = entry.get('ts', '')[:19]  # Trim to seconds
        tool = entry.get('tool', entry.get('type', 'unknown'))
        outcome = entry.get('outcome', '')
        input_summary = entry.get('input_summary', '')[:200]
        output_summary = entry.get('output_summary', '')[:200]

        outcome_marker = {'success': '+', 'failure': '!', 'unknown': '?'}.get(outcome, ' ')

        lines.append(f"[{ts}] [{outcome_marker}] {tool}")
        if input_summary:
            lines.append(f"  Input: {input_summary}")
        if output_summary:
            lines.append(f"  Output: {output_summary}")
        lines.append("")

    return "\n".join(lines)


def build_agent_prompt(session_content: str, heuristics: List[Dict], failures: List[Dict]) -> str:
    """Build the full prompt for the Opus agent."""
    prompt_parts = []

    # Base instructions
    base_prompt = load_prompt()
    if base_prompt:
        prompt_parts.append(base_prompt)

    prompt_parts.append("\n---\n")
    prompt_parts.append("# Context for This Extraction\n")

    # Add existing heuristics
    if heuristics:
        prompt_parts.append("\n## Existing Heuristics (for cross-reference)\n")
        for h in heuristics[:30]:
            golden = " [GOLDEN]" if h.get('is_golden') else ""
            prompt_parts.append(f"- [{h['domain']}]{golden} ({h['confidence']:.0%}): {h['rule']}")

    # Add recent failures
    if failures:
        prompt_parts.append("\n\n## Recent Failures (avoid duplicates)\n")
        for f in failures[:15]:
            prompt_parts.append(f"- [{f.get('domain', 'unknown')}] {f['title']}: {f.get('summary', '')[:100]}")

    # Add session content
    prompt_parts.append("\n\n---\n")
    prompt_parts.append(session_content)

    # Final instructions
    prompt_parts.append("\n\n---\n")
    prompt_parts.append("""
# Your Task

Analyze the session logs above and extract any valuable learnings.

For EACH proposal, output a complete markdown block following the format in the instructions.
Separate multiple proposals with `---PROPOSAL_SEPARATOR---`.

If no significant learnings are found, output:
```
NO_LEARNINGS_FOUND
```

Begin your analysis now.
""")

    return "\n".join(prompt_parts)


def parse_proposals(agent_output: str) -> List[str]:
    """Parse agent output into individual proposal markdown blocks."""
    if "NO_LEARNINGS_FOUND" in agent_output:
        return []

    # Split by separator
    proposals = []

    # Try splitting by separator first
    if "---PROPOSAL_SEPARATOR---" in agent_output:
        parts = agent_output.split("---PROPOSAL_SEPARATOR---")
    else:
        # Try finding markdown headers
        parts = re.split(r'(?=^# Proposal:)', agent_output, flags=re.MULTILINE)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Validate it looks like a proposal
        if "# Proposal:" in part or "**Type:**" in part:
            proposals.append(part)

    return proposals


def save_proposal(content: str, index: int) -> Optional[Path]:
    """Save a proposal to the pending directory."""
    PROPOSALS_PENDING.mkdir(parents=True, exist_ok=True)

    # Extract type and generate filename
    type_match = re.search(r'\*\*Type:\*\*\s*(\w+)', content)
    proposal_type = type_match.group(1) if type_match else "unknown"

    # Extract title for filename
    title_match = re.search(r'# Proposal:\s*(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else f"proposal-{index}"

    # Sanitize title for filename
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-').lower()[:40]

    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"{timestamp}_{proposal_type}_{safe_title}.md"
    filepath = PROPOSALS_PENDING / filename

    # Ensure we don't overwrite
    counter = 1
    while filepath.exists():
        filename = f"{timestamp}_{proposal_type}_{safe_title}_{counter}.md"
        filepath = PROPOSALS_PENDING / filename
        counter += 1

    try:
        filepath.write_text(content, encoding='utf-8')
        return filepath
    except IOError:
        return None


def mark_as_processed(log_files: List[Path]):
    """Mark log files as processed."""
    processed = []

    if PROCESSED_MARKER.exists():
        try:
            data = json.loads(PROCESSED_MARKER.read_text(encoding='utf-8'))
            processed = data.get('processed_files', [])
        except (json.JSONDecodeError, IOError):
            pass

    for f in log_files:
        if f.name not in processed:
            processed.append(f.name)

    data = {
        'processed_files': processed,
        'last_processed': datetime.now().isoformat()
    }

    PROCESSED_MARKER.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_MARKER.write_text(json.dumps(data, indent=2), encoding='utf-8')


def run_opus_agent(prompt: str) -> Optional[str]:
    """
    Run the Opus agent using Claude CLI with --print flag.

    Returns the agent's output or None on failure.
    """
    try:
        # Use claude CLI with --print for non-interactive execution
        result = subprocess.run(
            ["claude", "--print", "--model", "opus"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            encoding='utf-8'
        )

        if result.returncode == 0:
            return result.stdout
        else:
            print(f"[EXTRACTOR] Claude CLI error: {result.stderr}", file=sys.stderr)
            return None

    except subprocess.TimeoutExpired:
        print("[EXTRACTOR] Agent timed out after 5 minutes", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("[EXTRACTOR] Claude CLI not found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[EXTRACTOR] Error running agent: {e}", file=sys.stderr)
        return None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python run_extractor.py <log_file1.jsonl> [log_file2.jsonl ...]", file=sys.stderr)
        sys.exit(1)

    log_files = [Path(f) for f in sys.argv[1:]]

    # Filter to existing files
    existing_logs = [f for f in log_files if f.exists()]
    if not existing_logs:
        print("[EXTRACTOR] No valid log files found", file=sys.stderr)
        sys.exit(1)

    print(f"[EXTRACTOR] Processing {len(existing_logs)} log file(s)...", file=sys.stderr)

    # Load context
    heuristics = load_existing_heuristics()
    failures = load_recent_failures()
    session_content = load_session_logs(existing_logs)

    print(f"[EXTRACTOR] Loaded {len(heuristics)} heuristics, {len(failures)} failures", file=sys.stderr)

    # Build prompt
    full_prompt = build_agent_prompt(session_content, heuristics, failures)

    # Run Opus agent
    print("[EXTRACTOR] Spawning Opus agent...", file=sys.stderr)
    agent_output = run_opus_agent(full_prompt)

    if not agent_output:
        print("[EXTRACTOR] Agent returned no output", file=sys.stderr)
        # Still mark as processed to avoid infinite retries
        mark_as_processed(existing_logs)
        sys.exit(1)

    # Parse proposals
    proposals = parse_proposals(agent_output)

    if not proposals:
        print("[EXTRACTOR] No learnings extracted (this is okay)", file=sys.stderr)
        mark_as_processed(existing_logs)
        sys.exit(0)

    # Save proposals
    saved = []
    for i, proposal in enumerate(proposals):
        filepath = save_proposal(proposal, i)
        if filepath:
            saved.append(filepath)
            print(f"[EXTRACTOR] Saved: {filepath.name}", file=sys.stderr)

    print(f"[EXTRACTOR] Saved {len(saved)} proposal(s) to pending/", file=sys.stderr)

    # Mark as processed
    mark_as_processed(existing_logs)
    print("[EXTRACTOR] Marked logs as processed", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
