# Swarm Over Single Agent

**Created:** 2024-12-04
**Confidence:** 0.7
**Domain:** claudex, ai-architecture, multi-agent

## Heuristic

For complex developer tasks, use a coordinated swarm of specialized agents rather than one general-purpose agent trying to do everything.

## The Architecture

```
Commander (coordinator)
    │
    ├── Scout (explores, finds files)
    ├── Builder (writes code)
    ├── Reviewer (catches bugs)
    ├── Tester (validates changes)
    └── Deployer (ships it)
```

## Why Swarm Wins

| Single Agent | Swarm |
|--------------|-------|
| Sequential execution | Parallel execution |
| One perspective | Multiple specialized perspectives |
| Gets confused on big tasks | Divides and conquers |
| User waits | Agents work simultaneously |
| Context window bloat | Each agent has focused context |

## User Control

The key is giving users visibility and control:
- See what each agent is doing (status indicators)
- Pause/resume/abort the swarm
- Enable/disable specific agents
- Review plans before execution

## UI Implication

The cockpit aesthetic serves this - status gauges, agent panels, control buttons. Not just decoration, but functional visibility into the swarm.

## Source

Claudex vision session, December 2024
