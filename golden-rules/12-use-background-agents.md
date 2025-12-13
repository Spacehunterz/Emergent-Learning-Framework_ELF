# Golden Rule 12: Always Use Async Subagents

> Default to `run_in_background=True` for ALL subagent spawns. Block with TaskOutput only when you actually need the result. Never use synchronous subagents.

## Why

- Async lets you do other work while agent runs
- Multiple agents can run in parallel
- Main context stays responsive
- Sync wastes time waiting when you could be productive
- There's NO good reason to block immediately on spawn

## The Pattern

```python
# 1. SPAWN ASYNC (always)
task_id = Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="Your task...",
    run_in_background=True  # ALWAYS
)

# 2. DO OTHER WORK while agent runs
read_files()
check_status()
spawn_more_agents()

# 3. BLOCK ONLY WHEN YOU NEED THE RESULT
result = TaskOutput(task_id=task_id, block=True)
```

## Parallel Execution

Spawn multiple agents, then collect results:

```python
# Spawn all at once
task1 = Task(..., run_in_background=True)
task2 = Task(..., run_in_background=True)
task3 = Task(..., run_in_background=True)

# Do other work...

# Collect when needed
result1 = TaskOutput(task_id=task1, block=True)
result2 = TaskOutput(task_id=task2, block=True)
result3 = TaskOutput(task_id=task3, block=True)
```

## Anti-Patterns (NEVER DO)

- Synchronous subagent spawn (no `run_in_background`)
- Spawning async then immediately blocking (pointless)
- Suggesting async but never actually using it
- Spawn and forget (never check TaskOutput)

## Enforcement

Every Task tool call MUST have `run_in_background=True`.

Exception: None. There is no valid exception.

---

**Promoted:** 2025-12-13
**Reason:** CEO identified that sync subagents waste time. Async is always better - block only when result is needed.
**Status:** CONSTITUTIONAL - default behavior change
