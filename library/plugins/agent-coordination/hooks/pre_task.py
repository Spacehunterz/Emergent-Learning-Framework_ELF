#!/usr/bin/env python3
"""
PreToolUse Hook: Intercept Task tool calls and inject coordination context.

This hook:
1. Checks if coordination is enabled for the project
2. Registers the new agent on the blackboard
3. Injects shared context into the agent's prompt
4. Adds coordination instructions (including Basic Memory usage)

Features:
- Delta notifications (only show NEW findings since last check)
- Critical/blocker highlighting
- Interest-based relevance filtering
- Basic Memory integration for semantic search
"""

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import List, Tuple

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


def generate_agent_id() -> str:
    """Generate a short unique agent ID."""
    return f"agent-{uuid.uuid4().hex[:8]}"


def extract_task_info(tool_input: dict) -> tuple:
    """Extract task description and prompt from Task tool input."""
    description = tool_input.get("description", "unknown task")
    prompt = tool_input.get("prompt", "")
    subagent_type = tool_input.get("subagent_type", "general-purpose")
    return description, prompt, subagent_type


def extract_interests_from_task(description: str, prompt: str) -> List[str]:
    """Extract interest tags from task description/prompt.

    Looks for:
    - Explicit tags: [interests:auth,security,jwt]
    - Common domain keywords in the text
    """
    interests = []

    # Look for explicit interest tags
    match = re.search(r'\[interests?:([^\]]+)\]', description + " " + prompt, re.IGNORECASE)
    if match:
        interests.extend([t.strip().lower() for t in match.group(1).split(',')])

    # Common domain keywords to auto-detect
    domain_keywords = [
        'auth', 'authentication', 'security', 'jwt', 'token', 'session',
        'database', 'db', 'sql', 'query', 'schema', 'migration',
        'api', 'rest', 'graphql', 'endpoint', 'route',
        'frontend', 'ui', 'component', 'react', 'vue', 'css',
        'backend', 'server', 'service', 'controller',
        'test', 'testing', 'spec', 'coverage',
        'config', 'configuration', 'env', 'settings',
        'deploy', 'ci', 'docker', 'kubernetes',
        'performance', 'optimization', 'cache', 'memory',
        'error', 'exception', 'logging', 'debug',
    ]

    text = (description + " " + prompt).lower()
    for keyword in domain_keywords:
        if keyword in text and keyword not in interests:
            interests.append(keyword)

    return interests[:10]  # Limit to 10 interests


def build_coordination_context(bb: Blackboard, agent_id: str,
                                is_returning_agent: bool = False) -> Tuple[str, int]:
    """Build context injection for the agent prompt.

    Returns:
        Tuple of (context_string, cursor_position)
    """
    lines = [
        "",
        "---",
        "## Multi-Agent Coordination Context",
        "",
        f"**Your Agent ID:** `{agent_id}`",
        "",
    ]

    # Get agent's current cursor (for delta calculation)
    cursor = bb.get_agent_cursor(agent_id)
    new_findings = bb.get_findings_since_cursor(cursor) if cursor > 0 else []

    # =========================================================================
    # CRITICAL/BLOCKERS - Always show these prominently
    # =========================================================================
    critical = bb.get_critical_findings()
    open_questions = bb.get_open_questions()
    blocking_questions = [q for q in open_questions if q.get("blocking")]

    if critical or blocking_questions:
        lines.append("### 🚨 CRITICAL ATTENTION REQUIRED")
        lines.append("")
        for f in critical:
            lines.append(f"- **[{f['type'].upper()}]** {f['content']}")
        for q in blocking_questions:
            lines.append(f"- **[BLOCKING QUESTION]** {q['agent_id']}: {q['question']}")
        lines.append("")

    # =========================================================================
    # DELTA NOTIFICATIONS - New findings since last check
    # =========================================================================
    if new_findings:
        lines.append("### 🆕 NEW FINDINGS (since your last update)")
        lines.append("")
        for f in new_findings:
            importance_marker = "⚠️ " if f.get('importance') in ('high', 'critical') else ""
            tags_str = f" `[{', '.join(f.get('tags', []))}]`" if f.get('tags') else ""
            lines.append(f"- {importance_marker}[{f['type']}]{tags_str} {f['content']}")
        lines.append("")
    elif cursor > 0:
        lines.append("*No new findings since your last update.*")
        lines.append("")

    # =========================================================================
    # ACTIVE AGENTS
    # =========================================================================
    active = bb.get_active_agents()
    other_agents = {k: v for k, v in active.items() if k != agent_id}
    if other_agents:
        lines.append("**Other Active Agents:**")
        for aid, info in other_agents.items():
            scope_str = f" (scope: {', '.join(info.get('scope', []))})" if info.get('scope') else ""
            interests_str = f" [interests: {', '.join(info.get('interests', [])[:3])}]" if info.get('interests') else ""
            lines.append(f"- `{aid}`: {info['task']}{scope_str}{interests_str}")
        lines.append("")

    # =========================================================================
    # CONTEXT FOR NEW AGENTS - Show recent history
    # =========================================================================
    if cursor == 0:
        # This is a new agent - show recent findings for context
        recent_findings = bb.get_findings()[-5:]
        if recent_findings:
            lines.append("**Recent Findings (for context):**")
            for f in recent_findings:
                tags_str = f" `[{', '.join(f.get('tags', []))}]`" if f.get('tags') else ""
                lines.append(f"- [{f['type']}]{tags_str} {f['content']}")
            lines.append("")

    # =========================================================================
    # NON-BLOCKING OPEN QUESTIONS
    # =========================================================================
    non_blocking = [q for q in open_questions if not q.get("blocking")]
    if non_blocking:
        lines.append("**Open Questions:**")
        for q in non_blocking:
            lines.append(f"- {q['agent_id']}: {q['question']}")
        lines.append("")

    # =========================================================================
    # PENDING TASKS
    # =========================================================================
    pending = bb.get_pending_tasks()[:3]
    if pending:
        lines.append("**Pending Tasks (you may claim one):**")
        for t in pending:
            lines.append(f"- `{t['id']}`: {t['task']} (priority {t['priority']})")
        lines.append("")

    # =========================================================================
    # SHARED CONTEXT
    # =========================================================================
    context = bb.get_context()
    if context:
        lines.append("**Shared Context:**")
        for k, v in context.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    # =========================================================================
    # INSTRUCTIONS
    # =========================================================================
    lines.extend([
        "---",
        "## Coordination Instructions",
        "",
        "### Before Starting",
        "Search for relevant prior knowledge using Basic Memory:",
        "```",
        'mcp__basic-memory__search_notes(query="<your topic>", project="coordination")',
        "```",
        "",
        "### While Working",
        "1. **Avoid conflicts**: Don't modify files owned by other agents",
        "2. **Share discoveries**: Report important findings with tags",
        "3. **Ask questions**: If blocked, raise a question",
        "4. **Persist important findings**: Write to Basic Memory for semantic search:",
        "```",
        "mcp__basic-memory__write_note(",
        '    title="finding-<topic>",',
        '    content="<your finding>",',
        '    folder="swarm/findings",',
        '    tags=["tag1", "tag2"],',
        '    project="coordination"',
        ")",
        "```",
        "",
        "### When Complete",
        "Include a FINDINGS section with tags:",
        "```",
        "## FINDINGS",
        "- [fact:auth,jwt] JWT tokens are stored in httpOnly cookies",
        "- [discovery:database] Found legacy schema in migrations/",
        "- [warning:security:high] Rate limiting not implemented",
        "- [blocker:api] Need API documentation to proceed",
        "```",
        "",
        "Format: `[type:tag1,tag2:importance]` where importance is optional (low/normal/high/critical)",
        "---",
        ""
    ])

    # Calculate new cursor position (total findings count)
    state = bb.get_full_state()
    new_cursor = len(state.get("findings", []))

    return "\n".join(lines), new_cursor


def is_swarm_task(tool_input: dict) -> bool:
    """Check if this is a swarm-coordinated task (has [SWARM] marker)."""
    prompt = tool_input.get("prompt", "")
    description = tool_input.get("description", "")
    return "[SWARM]" in prompt or "[SWARM]" in description


def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    # Get tool input
    tool_input = hook_input.get("tool_input", {})
    if not tool_input:
        output_result({"decision": "approve"})
        return

    # Only coordinate if this is a swarm task (marked with [SWARM])
    if not is_swarm_task(tool_input):
        output_result({"decision": "approve"})
        return

    # Auto-initialize coordination
    cwd = os.getcwd()
    coordination_dir = Path(cwd) / ".coordination"
    coordination_dir.mkdir(parents=True, exist_ok=True)

    # Initialize blackboard
    bb = Blackboard(cwd)

    # Extract task info
    description, prompt, subagent_type = extract_task_info(tool_input)

    # Extract interests from task description/prompt
    interests = extract_interests_from_task(description, prompt)

    # Generate agent ID
    agent_id = generate_agent_id()

    # Register agent with interests
    try:
        bb.register_agent(agent_id, description, interests=interests)
    except Exception as e:
        # Don't block on registration failure
        sys.stderr.write(f"Warning: Failed to register agent: {e}\n")

    # Build coordination context (with delta tracking)
    new_cursor = 0
    try:
        context, new_cursor = build_coordination_context(bb, agent_id)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to build context: {e}\n")
        context = f"\n---\n**Agent ID:** `{agent_id}`\n---\n"

    # Update agent's cursor after context injection
    try:
        bb.update_agent_cursor(agent_id)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to update cursor: {e}\n")

    # Inject context into prompt
    modified_prompt = prompt + context

    # Create modified tool input
    modified_input = tool_input.copy()
    modified_input["prompt"] = modified_prompt

    # Store agent_id in environment for post_task hook
    # (This is a limitation - we can't easily pass data between hooks)
    # Instead, we'll embed it in the prompt for extraction later

    output_result({
        "decision": "approve",
        "tool_input": modified_input
    })


if __name__ == "__main__":
    main()
