# /swarm - Coordinated Multi-Agent Execution

Spawn and manage coordinated agents using the blackboard pattern with access to 99 specialized agents.

## Usage

```
/swarm [task]    # Execute task with agent picker
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

## Agent Pool (99 Specialists)

Agents are loaded from `~/.claude/agents/plugins/` with catalog at `~/.claude/agents/agent-catalog.json`.

### Categories

| Category | Agents | Use Case |
|----------|--------|----------|
| **backend** | backend-architect, graphql-architect, fastapi-pro, django-pro, event-sourcing-architect | API design, microservices |
| **frontend** | frontend-developer, mobile-developer, flutter-expert, ios-developer, ui-ux-designer | UI/UX, mobile apps |
| **infrastructure** | cloud-architect, kubernetes-architect, terraform-specialist, deployment-engineer, devops-troubleshooter | DevOps, cloud |
| **security** | security-auditor, threat-modeling-expert, backend-security-coder, frontend-security-coder | Security hardening |
| **database** | database-architect, database-optimizer, sql-pro, data-engineer | Schema, queries |
| **quality** | code-reviewer, test-automator, architect-review, tdd-orchestrator | Reviews, testing |
| **ai_ml** | ai-engineer, prompt-engineer, ml-engineer, data-scientist | AI/ML development |
| **debugging** | debugger, error-detective, incident-responder, dx-optimizer | Error analysis |
| **documentation** | docs-architect, api-documenter, mermaid-expert, tutorial-engineer | Docs, diagrams |
| **languages** | python-pro, typescript-pro, rust-pro, golang-pro, java-pro + 12 more | Language specialists |
| **observability** | observability-engineer, performance-engineer | Monitoring, metrics |

---

## Instructions

### `/swarm <task>` (Execute with Agent Picker)

**With task:** Start fresh coordinated execution

1. **Initialize** (if needed):
   ```bash
   mkdir -p ~/.claude/emergent-learning/.coordination
   python ~/.claude/emergent-learning/watcher/watcher_loop.py clear
   ```

2. **Analyze task** and recommend agents from pool:

   Based on task keywords, suggest relevant specialists:
   - Authentication → security-auditor, backend-architect
   - API design → backend-architect, graphql-architect
   - Performance → performance-engineer, debugger
   - Frontend → frontend-developer, ui-ux-designer
   - Database → database-architect, sql-pro

3. **Show agent picker**:
   ```
   ## Swarm Plan

   **Task:** [task]

   ### Recommended Agents:

   CORE (recommended):
   [x] backend-architect (opus) - API design, microservices
   [x] security-auditor (opus) - Security review

   SUPPORT (optional):
   [ ] test-automator (sonnet) - Test coverage
   [ ] code-reviewer (opus) - Code review
   [ ] debugger (sonnet) - Error analysis

   ### Custom Selection:
   Categories: backend, frontend, security, database, quality, ai_ml, debugging, docs, languages

   [Start] [Auto-select all] [Cancel]
   ```

4. **Load agent persona** from pool:

   For each selected agent, read its persona:
   ```bash
   cat ~/.claude/agents/plugins/*/agents/[agent-name].md | head -50
   ```

   The persona file contains:
   - YAML frontmatter (name, description, model tier)
   - Full persona instructions

5. **Spawn work agents** using Task tool with agent persona:

   **IMPORTANT:**
   - Include `[SWARM]` in description (triggers hooks)
   - Use `run_in_background: true` (Golden Rule #12)
   - Include agent persona in prompt

   ```
   Task tool call:
   - description: "[SWARM] backend-architect: Design API"
   - prompt: |
       ## Agent Persona
       [Insert persona from ~/.claude/agents/plugins/.../backend-architect.md]

       ## Task
       Your task: ...

       ## Output Format
       Report findings in ## FINDINGS section
   - subagent_type: "general-purpose"
   - model: "opus" | "sonnet" | "haiku" (per agent tier)
   - run_in_background: true
   ```

   **Model Selection by Agent Tier:**
   - Tier 1 (Opus): architecture, security, code review agents
   - Tier 2 (Inherit/Sonnet): most specialists
   - Tier 3 (Haiku): fast operational tasks

6. **Spawn watcher** (optional but recommended):
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

7. **Iterate** on follow-up tasks from queue (max 5 iterations)

8. **Synthesize** all findings into summary

9. **Stop monitoring** when done:
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

---

## Task-to-Agent Mapping

Use this reference when selecting agents:

| Task Type | Primary Agents | Support Agents |
|-----------|---------------|----------------|
| **New API** | backend-architect, graphql-architect | security-auditor, test-automator |
| **Auth System** | security-auditor, backend-security-coder | backend-architect |
| **Frontend Feature** | frontend-developer, ui-ux-designer | test-automator |
| **Database Schema** | database-architect, sql-pro | backend-architect |
| **Performance Issue** | performance-engineer, debugger | observability-engineer |
| **Code Review** | code-reviewer, architect-review | security-auditor |
| **Refactoring** | legacy-modernizer, code-reviewer | test-automator |
| **CI/CD Pipeline** | deployment-engineer, devops-troubleshooter | terraform-specialist |
| **Kubernetes** | kubernetes-architect, cloud-architect | network-engineer |
| **ML Pipeline** | ml-engineer, data-scientist | mlops-engineer |
| **Documentation** | docs-architect, api-documenter | mermaid-expert |

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
