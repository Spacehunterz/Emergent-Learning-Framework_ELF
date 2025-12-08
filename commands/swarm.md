# /swarm - Coordinated Multi-Agent Execution

Spawn and manage coordinated agents using the blackboard pattern.

## Usage

```
/swarm [task]    # Execute task (or continue/iterate if no task given)
/swarm show      # View full state (agents + findings + tasks + questions)
/swarm reset     # Clear blackboard
/swarm stop      # Disable coordination
```

## Examples

```
/swarm investigate the authentication system end-to-end
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

4. **Spawn agents** using Task tool with `[SWARM]` marker:

   **IMPORTANT:** Always include `[SWARM]` in the description so hooks inject coordination:
   ```
   Task tool call:
   - description: "[SWARM] Investigate auth service"
   - prompt: "Your task: ..."
   - subagent_type: "general-purpose"
   ```

   The hook will automatically:
   - Create `.coordination/` if needed
   - Register agent on blackboard
   - Inject context about other agents
   - Add coordination instructions

5. **Iterate** on follow-up tasks from queue (max 5 iterations)

6. **Synthesize** all findings into summary

### `/swarm show` (View State)

Display everything:

```bash
python ~/.claude/plugins/agent-coordination/utils/blackboard.py summary
```

Output format:
```
## Swarm Status

**Agents:** 3 (2 completed, 1 active)
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
