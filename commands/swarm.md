# /swarm - Coordinated Multi-Agent Execution

Spawn and manage coordinated agents using the blackboard pattern.

## Usage

```
/swarm [task]    # Execute task with automatic watcher
/swarm show      # View full state
/swarm reset     # Clear blackboard
/swarm stop      # Disable coordination
```

## Watcher (Automatic)

**Every swarm automatically starts a Haiku watcher** that monitors for stuck/failed agents.

- **Watcher (Haiku)**: Monitors coordination state every 30-60s, detects problems
- **Handler (Opus)**: Decides what to do when problems found

No flags needed. Watcher is always on.

## Examples

```
/swarm investigate the authentication system
/swarm implement feature X
/swarm show
/swarm reset
```

---

## Instructions

### `/swarm <task>` or `/swarm` (Execute/Continue)

**With task:** Start fresh coordinated execution
**Without task:** Continue - process pending follow-up tasks

1. **Initialize** (if needed):
   ```bash
   mkdir -p .coordination
   python ~/.claude/plugins/agent-coordination/utils/blackboard.py reset
   ```

2. **Start watcher agent** (runs in background):
   ```
   Task tool call:
   - description: "[WATCHER] Monitor swarm"
   - prompt: "Monitor ~/.claude/emergent-learning/.coordination/ for stuck agents..."
   - subagent_type: "general-purpose"
   - model: "haiku"
   - run_in_background: true
   ```

3. **Analyze & decompose** the task into parallel subtasks

4. **Show plan**:
   ```
   ## Swarm Plan

   **Task:** [task]
   **Agents:** [count]
   **Watcher:** haiku (automatic)

   | # | Subtask | Scope |
   |---|---------|-------|
   | 1 | ... | src/... |
   | 2 | ... | tests/... |

   Proceed? [Y/n]
   ```

5. **Spawn agents** using Task tool with `[SWARM]` marker:

   **IMPORTANT:**
   - Always include `[SWARM]` in description so hooks inject coordination
   - Always use `run_in_background: true` (Golden Rule #12)

   ```
   Task tool call:
   - description: "[SWARM] Investigate auth service"
   - prompt: "Your task: ..."
   - subagent_type: "general-purpose"
   - run_in_background: true   # REQUIRED - always async
   ```

   The hook will automatically:
   - Create `.coordination/` if needed
   - Register agent on blackboard
   - Inject context about other agents
   - Add coordination instructions

6. **Iterate** on follow-up tasks from queue (max 5 iterations)

7. **Synthesize** all findings into summary

### Watcher Behavior

The Haiku watcher runs in background and:
- Checks coordination state every 30-60 seconds
- Detects stuck agents (no heartbeat > 120s)
- Detects errors in agent outputs
- If problem found: spawns Opus handler to decide action

**Handler actions (Opus decides):**
- RESTART: Reset stuck agent
- REASSIGN: Put task back in queue
- SYNTHESIZE: Collect partial outputs
- ABORT: Stop work on task
- ESCALATE_TO_HUMAN: Write to ceo-inbox/

### `/swarm show` (View State)

Display everything:

```bash
python ~/.claude/plugins/agent-coordination/utils/blackboard.py summary
```

Output format:
```
## Swarm Status

**Agents:** 3 (2 completed, 1 active)
**Watcher:** haiku (running)

- agent-a1b2: Investigate auth [completed]
- agent-c3d4: Write tests [active]
- agent-e5f6: Update docs [completed]

**Findings:** 5
- [fact] Auth uses JWT tokens (agent-a1b2)
- [hypothesis] Rate limiting missing (agent-a1b2)
- [blocker] Need DB schema (agent-c3d4)

**Pending Tasks:** 2
- [8] Investigate token refresh
- [5] Add rate limiting

**Open Questions:** 1
- agent-c3d4: What auth provider to use?
```

### `/swarm reset` (Clear)

Clear all state:

```bash
python ~/.claude/plugins/agent-coordination/utils/blackboard.py reset
```

### `/swarm stop` (Disable)

Stop coordination and mark all agents as stopped:

```python
from blackboard import Blackboard
bb = Blackboard()
for agent_id in bb.get_active_agents():
    bb.update_agent_status(agent_id, 'stopped')
```

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
- Max 5 iterations
