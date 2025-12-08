# Agent Coordination Skill

> Multi-agent coordination for Claude Code sessions using shared state and structured communication.

## Overview

This skill enables multiple Claude Code agents (subagents) to work together on complex tasks by sharing findings, coordinating work, and avoiding duplication of effort.

## When to Use

Use agent coordination when:
- A task has multiple independent parts that can be parallelized
- You need different perspectives (investigation, design, critique)
- The problem benefits from divide-and-conquer
- You're spawning subagents with the Task tool

## Core Concepts

### The Blackboard

Agents coordinate through a shared "blackboard" - a file-based state store at `.coordination/blackboard.json` in the project root. The blackboard tracks:

- **Agent Registry** - Who is working on what
- **Findings** - Discoveries, warnings, blockers agents want to share
- **Messages** - Direct agent-to-agent communication
- **Task Queue** - Pending work items
- **Questions** - Blockers needing resolution

### Agent Personas

Four specialized personas for different thinking styles:

| Persona | Role | When to Use |
|---------|------|-------------|
| **Researcher** | Deep investigation, gathering evidence | "We need to understand X" |
| **Architect** | System design, big picture planning | "How should we structure X?" |
| **Skeptic** | Breaking things, finding edge cases | "Is this robust?" |
| **Creative** | Novel solutions, alternative approaches | "We're stuck on X" |

Personality definitions are in `~/.claude/emergent-learning/agents/*/personality.md`.

### Finding Types

When sharing discoveries, use these types:

- `discovery` - Found something interesting
- `warning` - Potential issue to be aware of
- `decision` - A choice that was made
- `blocker` - Something preventing progress
- `fact` - Verified information
- `hypothesis` - Unverified theory to test

## Setup

### 1. Initialize Coordination Directory

Copy the templates to your project:

```bash
mkdir -p .coordination
cp ~/.claude/plugins/agent-coordination/templates/* .coordination/
```

### 2. Include in Subagent Prompts

When spawning subagents, include coordination instructions:

```
You are working as part of a coordinated team.

Before starting:
1. Register yourself: python .coordination/blackboard.py register "<agent-id>" "<task>"
2. Check for existing findings: python .coordination/blackboard.py summary

During work:
- Add findings: python .coordination/blackboard.py finding "<agent-id>" "<type>" "<content>"
- Check for updates: python .coordination/blackboard.py delta "<agent-id>"

When done:
- Update status with final result
```

## API Reference

### Blackboard CLI

```bash
# View current state
python .coordination/blackboard.py summary

# Register as working agent
python .coordination/blackboard.py register <agent-id> "<task>" [interest-tags...]

# Add a finding
python .coordination/blackboard.py finding <agent-id> <type> "<content>" [tags...]

# Search findings (keyword)
python .coordination/blackboard.py search "<query>"

# Check what's new since last check
python .coordination/blackboard.py delta <agent-id>

# Reset blackboard
python .coordination/blackboard.py reset
```

### Python API

```python
from blackboard import Blackboard

bb = Blackboard(project_root=".")

# Register
bb.register_agent("agent-1", "Investigate auth system", interests=["auth", "security"])

# Add finding
bb.add_finding("agent-1", "discovery", "Found unused JWT validation",
               files=["src/auth.py"], importance="high", tags=["jwt", "security"])

# Get findings relevant to interests
relevant = bb.get_findings_for_interests(["security"])

# Get new findings since last check
cursor = bb.get_agent_cursor("agent-1")
new_findings = bb.get_findings_since_cursor(cursor)
bb.update_agent_cursor("agent-1")
```

## Integration with Basic Memory (Optional)

For semantic search across findings, you can optionally use Basic Memory MCP tools (requires Basic Memory MCP server):

```python
# Write finding to Basic Memory for semantic search
mcp__basic-memory__write_note(
    title="Discovery: JWT validation unused",
    content="Found that jwt_validate() is never called...",
    folder="coordination",
    project="my-project"
)

# Semantic search across all findings
mcp__basic-memory__search_notes(
    query="authentication security issues",
    project="my-project"
)

# Build context from coordination folder
mcp__basic-memory__build_context(
    url="coordination/*",
    project="my-project"
)
```

The blackboard handles real-time coordination; Basic Memory provides persistent semantic search.

## Best Practices

1. **Register before working** - Let other agents know what you're doing
2. **Share findings early** - Don't wait until done to share discoveries
3. **Use appropriate finding types** - Helps other agents prioritize
4. **Tag findings** - Makes filtering and searching easier
5. **Check for updates** - Periodically check what others have found
6. **Mark blockers clearly** - Use `blocker` type and `critical` importance

## Limitations

- **Pro/Max plan required** - Free plan can't use Task tool for subagents
- **File-based locking** - Works for moderate concurrency, not high-throughput
- **No built-in semantic search** - Use Basic Memory MCP for that capability
- **Manual cursor management** - Agents must track their own position

## Files

```
~/.claude/plugins/agent-coordination/
  hooks/
    hooks.json          # Hook definitions
    pre_task.py         # Pre-task context injection
    post_task.py        # Post-task finding recording
    session_end.py      # Session cleanup
  utils/
    blackboard.py       # Core coordination logic
    sqlite_bridge.py    # Database integration

.coordination/          # Per-project (in project root)
  blackboard.json       # Shared state file
  .blackboard.lock      # Lock file for concurrency
```

## See Also

- [Swarm Commands](/commands/swarm.md) - `/swarm` slash command for orchestrated multi-agent work
- [Conductor](/src/emergent-learning/conductor/) - Workflow orchestration for complex tasks
- [Agent Personas](/src/emergent-learning/agents/) - Personality definitions for each agent type
