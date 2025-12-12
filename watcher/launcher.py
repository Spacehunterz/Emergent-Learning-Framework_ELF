#!/usr/bin/env python3
"""
Watcher Launcher - Documentation for Tiered Watcher Pattern

## Usage (via /swarm command)

```
/swarm [task]    # Haiku watcher (automatic)
```

Watcher starts automatically with any swarm. No flags needed.

## How It Works

1. Swarm starts → Haiku watcher spawned in background
2. Watcher monitors coordination state every 30-60s
3. If problem detected → Opus handler spawned to decide action
4. Handler writes decision → action executed
5. Repeat until swarm completes

## Why Haiku for Watcher?

Watcher is a low-level job: "is anything broken?"
- Haiku is fast, cheap, good enough for observation
- Opus is overkill for simple health checks

Opus is for the Handler: "what should we do about it?"
- Complex decisions need reasoning
- Worth the cost when intervention is needed
"""

WATCHER_PROMPT = '''You are monitoring a multi-agent swarm.

Check the coordination state at: ~/.claude/emergent-learning/.coordination/

Read:
- blackboard.json (agent states, task queue)
- agent_*.md files (agent outputs)
- watcher-log.md (recent history)

Determine if anything needs attention:
- Stale agents (no update > 120 seconds)
- Errors in blackboard or outputs
- Deadlocks or conflicts
- Stuck tasks

Respond with:
- "STATUS: nominal" if all good
- "STATUS: escalate" with REASON, AFFECTED agents, SEVERITY if something's wrong
'''

HANDLER_PROMPT = '''You are an intervention agent. The watcher detected an issue:

{escalation}

Read full context at ~/.claude/emergent-learning/.coordination/

Decide on action:
- RESTART: Reset stuck agent, let it retry
- REASSIGN: Mark failed, put task back in queue
- SYNTHESIZE: Collect partial outputs, create synthesis task
- ABORT: Stop work, too many failures
- ESCALATE_TO_HUMAN: Write to ceo-inbox/ for human decision

Explain your reasoning. Write decision to .coordination/decision.md.
'''

# Task tool call for watcher (always Haiku)
SPAWN_WATCHER = """
Task(
    subagent_type="general-purpose",
    model="haiku",
    description="[WATCHER] Monitor swarm",
    prompt=WATCHER_PROMPT,
    run_in_background=True
)
"""

# Task tool call for handler (always Opus)
SPAWN_HANDLER = """
Task(
    subagent_type="general-purpose",
    model="opus",
    description="[HANDLER] Intervene in swarm",
    prompt=HANDLER_PROMPT.format(escalation=escalation_details)
)
"""


def main():
    print("TIERED WATCHER PATTERN")
    print("=" * 40)
    print()
    print("Usage: /swarm [task]")
    print("Watcher (Haiku) starts automatically.")
    print("Handler (Opus) spawns only when needed.")
    print()
    print("Watcher prompt:")
    print("-" * 40)
    print(WATCHER_PROMPT)
    print()
    print("Handler prompt:")
    print("-" * 40)
    print(HANDLER_PROMPT)


if __name__ == "__main__":
    main()
