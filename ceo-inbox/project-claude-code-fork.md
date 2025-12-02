# Project: Claude Code Fork - True Agent Coordination

## Mission
Fork Claude Code and add native agent-to-agent coordination to the Task tool.

## Background
Currently, Task-spawned agents are isolated one-shot processes. They cannot communicate with each other during execution. Coordination only happens through the orchestrator (main Claude) collecting results sequentially.

We want TRUE coordination where:
- Agents can share findings mid-execution
- Agent A can ask Agent B to investigate something
- Agents can read a shared blackboard/state
- Follow-up agents spawn automatically based on discoveries

## Brainstormed Architecture

### Option 1: SharedContext (Simplest)
```typescript
Task({
  agents: [...],
  sharedContext: true,  // All agents read/write to shared state
})
```
- Agents check SharedContext before returning
- Can respond to questions from other agents
- Requires polling or event system

### Option 2: Blackboard + Coordinator
```typescript
Task({
  agents: [...],
  coordination: {
    mode: "blackboard",
    iterations: 3,
    allowSpawnMore: true
  }
})
```
- Shared blackboard file/state
- Coordinator agent manages iterations
- Agents can spawn follow-up agents

### Option 3: PubSub Channels
```typescript
Task({
  agents: [...],
  coordination: {
    channels: ["findings", "questions", "actions"],
    subscribe: ["findings"],
    publish: ["questions"]
  }
})
```
- Agents subscribe to channels
- Publish messages during execution
- Event-driven coordination

## Resources
- Claude Code repo: github.com/anthropics/claude-code
- The building (our knowledge base): ~/.claude/emergent-learning/
- This project was brainstormed in data_overlay session 2025-12-01

## First Steps
1. Clone the Claude Code repo
2. Find where Task tool is implemented
3. Understand current agent spawning architecture
4. Design minimal coordination layer
5. Prototype with SharedContext approach
6. Test with building's edge case framework

## Success Criteria
- Agents can share state during execution
- No external daemon required (coordination built into Task)
- Backward compatible (existing Task calls still work)
- The building tests pass with coordinated agents

## Constraints
- Must work on Windows (MSYS2/Git Bash)
- Should not require external services (Redis, etc.)
- Latency should be low (sub-second message passing)

## Prompt for New Session

```
I want to fork Claude Code and add true agent coordination.

Currently Task-spawned agents are isolated - they can't talk to each other. I want to add a coordination layer so agents can:
1. Share findings mid-execution via a shared context/blackboard
2. Ask other agents to investigate things
3. Spawn follow-up agents based on discoveries

Check the building for context:
python ~/.claude/emergent-learning/query/query.py --domain architecture

The project spec is in:
~/.claude/emergent-learning/ceo-inbox/project-claude-code-fork.md

First step: Clone github.com/anthropics/claude-code and find where the Task tool is implemented. Map out the current architecture before we start modifying.
```

---
Created: 2025-12-01
Status: ON HOLD - Awaiting Anthropic source access
Note: Closed source. Built /swarm plugin workaround.
Priority: HIGH
Domain: architecture, coordination
