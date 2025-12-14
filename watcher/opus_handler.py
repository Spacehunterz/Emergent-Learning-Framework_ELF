#!/usr/bin/env python3
"""
Opus Handler - Real Claude Opus agent for intelligent intervention.

This is NOT a state machine. It spawns an actual Claude Opus agent
that THINKS about what action to take.

Usage:
    Called when Haiku watcher escalates an issue.

Design:
    - Receives escalation from Haiku watcher
    - Gathers full context (blackboard, logs, agent outputs)
    - Passes to Opus agent with intervention prompt
    - Agent reasons about best action
    - Returns decision with explanation
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Paths
COORDINATION_DIR = Path.home() / ".claude" / "emergent-learning" / ".coordination"
BLACKBOARD_FILE = COORDINATION_DIR / "blackboard.json"
WATCHER_LOG = COORDINATION_DIR / "watcher-log.md"
DECISION_FILE = COORDINATION_DIR / "decision.md"
CEO_INBOX = Path.home() / ".claude" / "emergent-learning" / "ceo-inbox"


def gather_full_context(escalation: Dict[str, Any]) -> Dict[str, Any]:
    """Gather comprehensive context for Opus to analyze."""
    context = {
        "timestamp": datetime.now().isoformat(),
        "escalation": escalation,
        "blackboard": {},
        "agent_outputs": {},
        "recent_log": "",
    }

    # Read blackboard
    if BLACKBOARD_FILE.exists():
        try:
            context["blackboard"] = json.loads(BLACKBOARD_FILE.read_text())
        except (json.JSONDecodeError, IOError, OSError) as e:
            context["blackboard"] = {"error": f"Could not parse: {e}"}

    # Read agent output files
    for f in COORDINATION_DIR.glob("agent_*.md"):
        try:
            content = f.read_text()
            # Truncate if too long
            if len(content) > 2000:
                content = content[:2000] + "\n...[truncated]..."
            context["agent_outputs"][f.stem] = content
        except (IOError, OSError, UnicodeDecodeError) as e:
            context["agent_outputs"][f.stem] = f"[could not read: {e}]"

    # Read recent watcher log
    if WATCHER_LOG.exists():
        try:
            log = WATCHER_LOG.read_text()
            # Last 2000 chars
            context["recent_log"] = log[-2000:] if len(log) > 2000 else log
        except (IOError, OSError, UnicodeDecodeError):
            pass  # Log is optional, skip if unreadable

    return context


def get_opus_prompt(context: Dict[str, Any]) -> str:
    """Build the prompt for the Opus intervention agent."""
    return f"""You are an intelligent intervention agent for a multi-agent swarm.

The Haiku monitoring agent has detected an issue and escalated to you.

## Escalation Details

```json
{json.dumps(context['escalation'], indent=2)}
```

## Current Blackboard State

```json
{json.dumps(context['blackboard'], indent=2)}
```

## Agent Outputs

{chr(10).join(f"### {name}{chr(10)}```{chr(10)}{content[:1000]}{chr(10)}```" for name, content in context['agent_outputs'].items())}

## Recent Watcher Log

```
{context['recent_log'][-1000:]}
```

## Your Task

Analyze this situation and decide on the best action:

### Available Actions

1. **RESTART** - Reset stuck agent(s) and let them retry
   - Use when: Agent appears frozen but task is likely recoverable
   - Least disruptive option

2. **REASSIGN** - Mark agent as failed, put task back in queue
   - Use when: Agent failed but a fresh agent might succeed
   - Gives task another chance with clean slate

3. **SYNTHESIZE** - Collect partial outputs and create synthesis task
   - Use when: Some useful work was done before failure
   - Preserves partial progress

4. **ABORT** - Stop all work on this task
   - Use when: Multiple failures, task seems impossible
   - Prevents wasting more resources

5. **ESCALATE_TO_HUMAN** - Write to CEO inbox for human decision
   - Use when: Conflict, ambiguity, or high-stakes decision
   - Requires human judgment

## Response Format

```
DECISION: [RESTART|REASSIGN|SYNTHESIZE|ABORT|ESCALATE_TO_HUMAN]

REASONING: [2-3 sentences explaining why this is the right action]

AFFECTED_AGENTS: [list of agent IDs]

SPECIFIC_ACTIONS:
- [concrete step 1]
- [concrete step 2]

CONFIDENCE: [low/medium/high]
```

Think carefully. Your decision affects whether work continues or is lost.
"""


def write_decision(decision_text: str) -> None:
    """Write the Opus decision to file."""
    timestamp = datetime.now().isoformat()
    content = f"""# Opus Handler Decision

**Timestamp:** {timestamp}
**Source:** Claude Opus Agent (real reasoning, not state machine)

---

{decision_text}

---
*Decision made by Opus agent via Task tool*
"""
    COORDINATION_DIR.mkdir(parents=True, exist_ok=True)
    DECISION_FILE.write_text(content)


def main():
    """
    Main entry point.

    For testing, creates a sample escalation and shows the prompt.
    In production, this is called with actual escalation data.
    """
    # Sample escalation for testing
    sample_escalation = {
        "status": "escalate",
        "reason": "Agent agent-3 has not updated in 180 seconds",
        "affected": ["agent-3"],
        "severity": "medium",
        "recommended_action": "restart",
        "detected_at": datetime.now().isoformat(),
    }

    context = gather_full_context(sample_escalation)
    prompt = get_opus_prompt(context)

    print("=" * 60)
    print("OPUS HANDLER - Context Gathered")
    print("=" * 60)
    print(f"\nContext summary:")
    print(f"  - Escalation reason: {sample_escalation['reason']}")
    print(f"  - Blackboard agents: {len(context['blackboard'].get('agents', {}))}")
    print(f"  - Agent outputs: {len(context['agent_outputs'])}")
    print(f"\nPrompt for Opus agent ({len(prompt)} chars):")
    print("-" * 40)
    print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
    print("-" * 40)
    print("\nTo actually run this, use the Task tool with model='opus'")
    print("and pass the gathered context + prompt.")

    return context, prompt


if __name__ == "__main__":
    main()
