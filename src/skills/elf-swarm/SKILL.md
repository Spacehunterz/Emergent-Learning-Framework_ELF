---
name: swarm
description: Coordinate multi-agent orchestration for complex tasks. Launch parallel and sequential agents, manage dependencies, aggregate results, and orchestrate sophisticated workflows. Use for tasks requiring multiple specialized perspectives or parallel processing.
license: MIT
---

# ELF Swarm Coordination

Orchestrate multi-agent workflows using the **full agent pool** (~100+ specialized agents).

## Swarm Modes

### ultrathink
Maximum depth analysis. Launch 10-20+ agents across all relevant categories.
```
/swarm ultrathink [target]
```

### focused
Targeted analysis. Launch 3-5 agents for specific domain.
```
/swarm focused security [target]
/swarm focused architecture [target]
```

### quick
Fast survey. Launch 2-3 core agents.
```
/swarm quick [target]
```

## Agent Selection Logic

**DO NOT hardcode agents.** Select based on task characteristics:

### Step 1: Detect Task Domains
Analyze the request and codebase to identify:
- Languages present (Python, TypeScript, Rust, Go, etc.)
- Frameworks (React, FastAPI, Django, etc.)
- Infrastructure (Docker, K8s, Terraform, etc.)
- Concerns (security, performance, architecture, etc.)

### Step 2: Map Domains to Agent Categories

| Domain | Agents to Consider |
|--------|-------------------|
| **Code Quality** | code-reviewer, debugger, test-automator |
| **Architecture** | architect-review, backend-architect, cloud-architect, database-architect |
| **Security** | security-auditor, backend-security-coder, frontend-security-coder, mobile-security-coder |
| **Python** | python-pro, fastapi-pro, django-pro, python-testing-patterns |
| **TypeScript/JS** | typescript-pro, javascript-pro, frontend-developer, react-state-management |
| **Rust** | rust-pro, rust-async-patterns, memory-safety-patterns |
| **Go** | golang-pro, go-concurrency-patterns |
| **Databases** | database-architect, database-optimizer, database-admin, sql-pro |
| **Infrastructure** | devops-troubleshooter, kubernetes-architect, terraform-specialist, deployment-engineer |
| **Documentation** | docs-architect, tutorial-engineer, reference-builder, api-documenter |
| **Performance** | performance-engineer, database-optimizer |
| **AI/Agents** | ai-engineer, prompt-engineer, context-manager |
| **Frontend** | frontend-developer, ui-ux-designer, tailwind-design-system |
| **DevEx** | dx-optimizer |
| **Testing** | test-automator, tdd-orchestrator, e2e-testing-patterns |
| **Shell/Scripts** | bash-pro, posix-shell-pro, shellcheck-configuration |

### Step 3: Select Agent Count by Mode

| Mode | Agents per Category | Total Target |
|------|--------------------:|-------------:|
| ultrathink | 2-3 | 15-25 |
| focused | 1-2 | 4-8 |
| quick | 1 | 2-4 |

## Execution Rules

1. **Always async**: `run_in_background=True` for ALL agents
2. **Parallel launch**: Send ALL agent spawns in ONE message
3. **Block only at end**: Use `TaskOutput` only when aggregating results
4. **Model selection**:
   - Haiku for quick/simple analysis
   - Sonnet for standard analysis (default)
   - Opus for deep architectural/security audits

## Example: ultrathink on a Python/React Project

Detected: Python backend, React frontend, SQLite database, shell scripts

Agents to launch:
```
# Code Quality
- code-reviewer
- debugger

# Architecture
- architect-review
- backend-architect
- database-architect

# Security
- security-auditor
- backend-security-coder
- frontend-security-coder

# Language-Specific
- python-pro
- typescript-pro
- frontend-developer

# Database
- database-optimizer

# Documentation
- docs-architect

# DevEx
- dx-optimizer

# Testing
- test-automator

# Shell
- bash-pro

# AI (if agent framework)
- prompt-engineer
- context-manager
- ai-engineer
```

Total: 18 agents in parallel

## Prompt Template for Agents

Each agent gets a focused prompt:
```
[Agent Type] analysis of [TARGET_PATH].

Focus on:
- [Domain-specific concerns]
- [What to look for]
- [What to report]

Be thorough. Report findings with file:line references.
```

## Result Aggregation

After all agents complete:

1. Read all output files
2. Group findings by severity/category
3. Identify patterns across agents (multiple agents flagging same issue = high confidence)
4. Synthesize into actionable summary
5. Optionally record learnings to ELF building

## Anti-Patterns (DO NOT DO)

- Hardcoding 4 agents (Researcher/Architect/Creative/Skeptic is OBSOLETE)
- Launching agents synchronously
- Using same prompt for all agents
- Ignoring detected technologies
- Using Opus for everything (wasteful)

## Integration with ELF

After swarm completes:
- Record significant findings as heuristics
- Update golden rules if patterns emerge
- Escalate architectural decisions to CEO inbox
