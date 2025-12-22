#!/usr/bin/env python3
"""
PostToolUse Hook: Capture agent results and extract findings.

This hook:
1. Parses the agent's output for findings
2. Updates agent status on blackboard
3. Extracts structured information (discoveries, decisions, warnings)
4. Reports pending tasks or blockers

Features:
- Tag parsing from findings: [type:tag1,tag2] or [type:tag1,tag2:importance]
- Importance level extraction

NOTE ON ARCHITECTURE:
- This hook writes findings to LOCAL blackboard.json for real-time coordination
- For PERSISTENT semantic search, agents should write to Basic Memory themselves
- Hooks cannot call MCP tools (only Claude can during conversation)
- The pre_task hook instructs agents to use Basic Memory for important findings
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict

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


def output_result(result: dict):
    """Output hook result to stdout."""
    print(json.dumps(result))


def extract_agent_id(prompt: str) -> str:
    """Extract agent ID from the prompt (injected by pre_task hook)."""
    match = re.search(r'\*\*Your Agent ID:\*\* `(agent-[a-f0-9]+)`', prompt)
    if match:
        return match.group(1)
    return None


def parse_finding_bracket(bracket_content: str) -> Dict:
    """Parse the bracket content of a finding.

    Formats supported:
    - [type] -> type only
    - [type:tag1,tag2] -> type + tags
    - [type:tag1,tag2:importance] -> type + tags + importance

    Returns dict with: type, tags, importance
    """
    parts = bracket_content.split(':')
    result = {
        'type': 'note',
        'tags': [],
        'importance': 'normal'
    }

    if len(parts) >= 1:
        result['type'] = parts[0].strip().lower()

    if len(parts) >= 2:
        # Second part could be tags or importance
        second = parts[1].strip()
        if second in ('low', 'normal', 'high', 'critical'):
            result['importance'] = second
        else:
            # It's tags
            result['tags'] = [t.strip().lower() for t in second.split(',') if t.strip()]

    if len(parts) >= 3:
        # Third part is importance
        third = parts[2].strip().lower()
        if third in ('low', 'normal', 'high', 'critical'):
            result['importance'] = third

    return result


def extract_findings(output: str) -> List[Dict]:
    """Extract findings from agent output.

    Supports enhanced format with tags and importance:
    - [fact:auth,jwt] JWT tokens are stored in cookies
    - [warning:security:high] Rate limiting missing
    - [blocker:api] Need documentation
    """
    findings = []

    # Look for FINDINGS section
    findings_match = re.search(r'## FINDINGS\s*\n(.*?)(?=\n##|\n---|\Z)', output, re.DOTALL | re.IGNORECASE)
    if findings_match:
        findings_text = findings_match.group(1)

        # Parse each finding line
        for line in findings_text.split('\n'):
            line = line.strip()
            if not line or not line.startswith('-'):
                continue

            # Enhanced pattern: [type:tags:importance] content
            # Matches: [word] or [word:stuff] or [word:stuff:stuff]
            type_match = re.match(r'-\s*\[([^\]]+)\]\s*(.+)', line)
            if type_match:
                bracket_content = type_match.group(1)
                content = type_match.group(2).strip()

                parsed = parse_finding_bracket(bracket_content)
                findings.append({
                    "type": parsed['type'],
                    "tags": parsed['tags'],
                    "importance": parsed['importance'],
                    "content": content
                })
            else:
                # Plain finding without type
                content = line.lstrip('- ').strip()
                if content:
                    findings.append({
                        "type": "note",
                        "tags": [],
                        "importance": "normal",
                        "content": content
                    })

    # Also look for inline findings marked with special syntax
    # Format: [FINDING:type:tags] content
    inline_pattern = r'\[FINDING:([^\]]+)\]\s*([^\n\[]+)'
    inline_findings = re.findall(inline_pattern, output)
    for bracket_content, content in inline_findings:
        parsed = parse_finding_bracket(bracket_content)
        findings.append({
            "type": parsed['type'],
            "tags": parsed['tags'],
            "importance": parsed['importance'],
            "content": content.strip()
        })

    return findings


def extract_files_modified(output: str) -> list:
    """Extract list of files that were modified."""
    files = []

    # Look for common file modification patterns
    patterns = [
        r'(?:created|modified|edited|wrote|updated)\s+[`"\']?([^\s`"\']+\.[a-zA-Z]+)',
        r'File\s+[`"\']([^\s`"\']+\.[a-zA-Z]+)[`"\']',
        r'Writing\s+to\s+[`"\']?([^\s`"\']+\.[a-zA-Z]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, output, re.IGNORECASE)
        files.extend(matches)

    return list(set(files))


def detect_blockers(output: str) -> list:
    """Detect if agent reported any blockers."""
    blockers = []

    # Look for blocker patterns
    blocker_patterns = [
        r'\[BLOCKER\]\s*([^\n]+)',
        r'(?:blocked|blocking|cannot proceed)(?:\s+because|\s*:)\s*([^\n]+)',
        r'## BLOCKERS?\s*\n(.*?)(?=\n##|\n---|\Z)',
    ]

    for pattern in blocker_patterns:
        matches = re.findall(pattern, output, re.IGNORECASE | re.DOTALL)
        for match in matches:
            if isinstance(match, str) and match.strip():
                blockers.append(match.strip())

    return blockers


def determine_status(output: str, blockers: list) -> tuple:
    """Determine agent completion status and result summary."""
    if blockers:
        return "blocked", f"Blocked: {blockers[0]}"

    # Check for success indicators
    success_patterns = [
        r'(?:successfully|completed|done|finished)',
        r'task\s+(?:complete|accomplished)',
        r'all\s+(?:tests?\s+)?pass',
    ]

    for pattern in success_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return "completed", "Task completed successfully"

    # Check for failure indicators
    failure_patterns = [
        r'(?:failed|error|exception|could not)',
        r'unable to',
        r'tests?\s+fail',
    ]

    for pattern in failure_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return "failed", "Task encountered errors"

    # Default to completed if no clear indicators
    return "completed", "Task finished"


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    # Get tool input and output
    tool_input = hook_input.get("tool_input", {})
    tool_output = hook_input.get("tool_output", {})

    if not tool_input:
        output_result({})
        return

    # Check if coordination is enabled
    cwd = os.getcwd()
    coordination_dir = Path(cwd) / ".coordination"

    if not coordination_dir.exists():
        output_result({})
        return

    # Initialize blackboard
    bb = Blackboard(cwd)

    # Extract agent ID from the original prompt
    prompt = tool_input.get("prompt", "")
    agent_id = extract_agent_id(prompt)

    if not agent_id:
        # Can't identify agent, skip processing
        output_result({})
        return

    # Get output content
    output_content = ""
    if isinstance(tool_output, dict):
        output_content = tool_output.get("content", "")
        if isinstance(output_content, list):
            output_content = "\n".join(
                item.get("text", "") for item in output_content
                if isinstance(item, dict)
            )
    elif isinstance(tool_output, str):
        output_content = tool_output

    # Extract findings
    findings = extract_findings(output_content)
    files = extract_files_modified(output_content)
    blockers = detect_blockers(output_content)

    # Determine status
    status, result_summary = determine_status(output_content, blockers)

    # Update blackboard
    try:
        # Update agent status
        bb.update_agent_status(agent_id, status, result_summary)

        # Add findings with tags and importance
        for finding in findings:
            # Use importance from finding, or infer from type
            importance = finding.get("importance", "normal")
            if importance == "normal" and finding["type"] in ("warning", "blocker", "decision"):
                importance = "high"

            bb.add_finding(
                agent_id=agent_id,
                finding_type=finding["type"],
                content=finding["content"],
                files=files,
                importance=importance,
                tags=finding.get("tags", [])
            )

        # Add blockers as questions
        for blocker in blockers:
            bb.ask_question(
                agent_id=agent_id,
                question=blocker,
                blocking=True
            )

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to update blackboard: {e}\n")

    # =========================================================================
    # SQLITE BRIDGE: Persist to index.db for historical queries
    # =========================================================================
    try:
        from sqlite_bridge import SQLiteBridge
        sqlite_bridge = SQLiteBridge()
        run_id = sqlite_bridge.get_or_create_run(cwd)
        if run_id:
            sqlite_bridge.record_node_execution(
                run_id=run_id,
                agent_id=agent_id,
                prompt=prompt,
                output=output_content,
                status=status,
                findings=findings,
                files_modified=files
            )
            # Lay trails for files modified
            for file_path in files:
                sqlite_bridge.lay_trail(
                    run_id=run_id,
                    location=file_path,
                    scent="discovery" if status == "completed" else "warning",
                    agent_id=agent_id,
                    message=f"Modified by {agent_id}"
                )
            # Lay trails for blockers
            for blocker in blockers:
                sqlite_bridge.lay_trail(
                    run_id=run_id,
                    location=blocker[:100],
                    scent="blocker",
                    agent_id=agent_id,
                    message=blocker
                )
        sqlite_bridge.close()
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to bridge to SQLite: {e}\n")


    # Output (no modification to tool output)
    output_result({})


if __name__ == "__main__":
    main()
