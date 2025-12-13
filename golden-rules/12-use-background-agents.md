# Golden Rule 12: Use Background Agents for Multi-Step Tasks

> For any task requiring multiple steps, parallel work, or monitoring, spawn background haiku agents. Don't do everything synchronously in main context.

## Why

- Background agents save context window in active session
- Parallel work completes faster
- Monitoring can happen while main work continues
- The capability exists and is powerful - USE IT

## When to Spawn Background Agents

1. **Multi-step tasks** - More than 3 sequential operations
2. **Batch processing** - Comparing N items, scanning files, etc.
3. **Monitoring** - Watching for changes, health checks
4. **Swarm work** - Always spawn watcher with /swarm
5. **Session start** - Consider spawning monitoring agent

## How

```python
Task(
    subagent_type="general-purpose",
    model="haiku",  # Cheap, fast, good enough for most background work
    description="[BACKGROUND] Task description",
    prompt="Your task...",
    run_in_background=True
)
```

Then later:
```python
TaskOutput(task_id="agent-xxx", block=False)  # Check progress
TaskOutput(task_id="agent-xxx", block=True)   # Wait for completion
```

## Anti-Pattern (What NOT to Do)

- Suggest background agents but never spawn them
- Spawn and forget (never check TaskOutput)
- Do everything synchronously when parallel would be faster
- Read docs about background agents, nod, then ignore them

## Enforcement

Before starting multi-step work, ask:
> "Should this run in background while I continue other work?"

Before ending session, ask:
> "Did I check all background agent outputs?"

---

**Promoted:** 2025-12-13
**Reason:** Capability exists but consistently underutilized. CEO identified pattern of suggesting but not using background agents.
**Status:** CONSTITUTIONAL - behavioral correction
