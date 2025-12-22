# /swarm - Coordinated Multi-Agent Execution

Spawn and manage coordinated agents using the blackboard pattern.

## Usage

```
/swarm [task]    # Execute task with monitoring
/swarm show      # View full state
/swarm reset     # Clear blackboard
/swarm stop      # Stop monitoring
```

## Examples

```
/swarm investigate the authentication system
/swarm implement feature X
/swarm show
/swarm reset
```

---

## How Monitoring Works

**Single-Pass Watcher Model:**
1. You spawn work agents with `[SWARM]` tag
2. Hook reminds main Claude if watcher needed
3. Main Claude spawns haiku watcher (single pass)
4. Watcher analyzes state, fixes problems, logs, exits
5. Next user message triggers next monitoring cycle

Watchers do NOT self-perpetuate (cost control). The cycle is driven by user interaction.

---

## Instructions

### `/swarm <task>` (Execute)

**With task:** Start fresh coordinated execution

1. **Initialize** (if needed):
   ```bash
   mkdir -p ~/.claude/emergent-learning/.coordination
   python ~/.claude/emergent-learning/watcher/watcher_loop.py clear
   ```

2. **Analyze & decompose** the task into parallel subtasks

3. **Show plan**:
   ```
   ## Swarm Plan

   **Task:** [task]
   **Agents:** [count]

   | # | Subtask | Scope |
   |---|---------|-------|
   | 1 | ... | src/... |
   | 2 | ... | tests/... |

   Proceed? [Y/n]
   ```

4. **Spawn work agents** using Task tool with `[SWARM]` marker:

   **IMPORTANT:**
   - Always include `[SWARM]` in description (triggers hooks)
   - Always use `run_in_background: true` (Golden Rule #12)

   ```
   Task tool call:
   - description: "[SWARM] Investigate auth service"
   - prompt: "Your task: ..."
   - subagent_type: "general-purpose"
   - run_in_background: true
   ```

5. **Spawn watcher** (optional but recommended):
   ```bash
   python ~/.claude/emergent-learning/watcher/watcher_loop.py prompt
   ```

   Then spawn with Task tool:
   ```
   - description: "[WATCHER] Monitor swarm"
   - subagent_type: "general-purpose"
   - model: "haiku"
   - run_in_background: true
   - prompt: (output from above command)
   ```

   The watcher will:
   - Do ONE comprehensive monitoring pass
   - Detect problems (stale agents, errors)
   - Fix issues directly (update blackboard)
   - Log findings and exit

   A UserPromptSubmit hook will remind you to spawn another watcher if needed.

6. **Iterate** on follow-up tasks from queue (max 5 iterations)

7. **Synthesize** all findings into summary

8. **Stop monitoring** when done:
   ```bash
   python ~/.claude/emergent-learning/watcher/watcher_loop.py stop
   ```

### `/swarm show` (View State)

```bash
python ~/.claude/emergent-learning/watcher/watcher_loop.py status
```

Also check blackboard:
```bash
cat ~/.claude/emergent-learning/.coordination/blackboard.json | python -m json.tool
```

### `/swarm reset` (Clear)

Clear all state:
```bash
rm -rf ~/.claude/emergent-learning/.coordination/*
```

### `/swarm stop` (Disable)

Stop monitoring:
```bash
python ~/.claude/emergent-learning/watcher/watcher_loop.py stop
```

This creates a `watcher-stop` file that prevents future watcher spawns.

---

## Finding Types

Agents report in `## FINDINGS` section:
- `[fact]` - Confirmed information
- `[hypothesis]` - Suspected pattern
- `[blocker]` - Cannot proceed
- `[question]` - Need input

## Constraints

- File-based IPC (no external services)
- Windows compatible
- Single-pass watchers (user-driven cycle)
- Max 5 iterations per swarm
