# Swarm: Multi-Agent Coordination

**Requires Pro or Max plan** - Free plan can't use Task tool for subagents.

## What It Does

Swarm coordinates multiple Claude Code subagents with specialized personas. Each agent brings domain expertise to your task.

## Using Swarm

```bash
/swarm investigate the authentication system    # Start task
/swarm show                                     # View state
/swarm reset                                    # Clear and restart
/swarm stop                                     # Stop all agents
```

**Example:**
```
You: /swarm implement a new REST API

Claude: ## Swarm Plan
        **Task:** Implement REST API

        ### Recommended Agents:

        CORE:
        [x] backend-architect (opus) - API design, microservices
        [x] security-auditor (opus) - Security review

        SUPPORT:
        [ ] test-automator (sonnet) - Test coverage
        [ ] api-documenter (sonnet) - OpenAPI docs

        Proceed? [Y/n]
```

## Agent Pool (100 Specialists)

ELF integrates **100 specialized agents** from [wshobson/agents](https://github.com/wshobson/agents).

### Install

```bash
./tools/setup/install-agents.sh
```

This installs:
- Agents to `~/.claude/agents/`
- Agent catalog to `~/.claude/agents/agent-catalog.json`
- Updated `/swarm` command

### Categories

| Category | Agents | Use Case |
|----------|--------|----------|
| **backend** | backend-architect, graphql-architect, fastapi-pro, django-pro, event-sourcing-architect | API design, microservices |
| **frontend** | frontend-developer, mobile-developer, flutter-expert, ios-developer, ui-ux-designer | UI/UX, mobile apps |
| **infrastructure** | cloud-architect, kubernetes-architect, terraform-specialist, deployment-engineer, devops-troubleshooter | DevOps, cloud |
| **security** | security-auditor, threat-modeling-expert, backend-security-coder, frontend-security-coder | Security hardening |
| **database** | database-architect, database-optimizer, database-admin, sql-pro, data-engineer | Schema, queries |
| **quality** | code-reviewer, test-automator, architect-review, legacy-modernizer, tdd-orchestrator | Reviews, testing |
| **ai_ml** | ai-engineer, prompt-engineer, vector-database-engineer, data-scientist, ml-engineer, mlops-engineer | AI/ML development |
| **debugging** | debugger, error-detective, incident-responder, dx-optimizer | Error analysis |
| **documentation** | docs-architect, api-documenter, mermaid-expert, tutorial-engineer, reference-builder | Docs, diagrams |
| **languages** | python-pro, typescript-pro, javascript-pro, rust-pro, golang-pro, java-pro, csharp-pro, scala-pro, cpp-pro, c-pro, ruby-pro, php-pro, elixir-pro, haskell-pro, julia-pro, bash-pro, posix-shell-pro | Language specialists |
| **specialized** | blockchain-developer, quant-analyst, risk-manager, payment-integration, unity-developer, minecraft-bukkit-pro, arm-cortex-expert | Domain experts |
| **observability** | observability-engineer, performance-engineer | Monitoring, metrics |
| **architecture** | c4-code, c4-component, c4-container, c4-context, monorepo-architect | C4 diagrams |
| **business** | business-analyst, hr-pro, legal-advisor, customer-support, sales-automator, content-marketer | Business ops |
| **seo** | seo-content-writer, seo-content-planner, seo-meta-optimizer, seo-keyword-strategist | SEO optimization |

### Task-to-Agent Mapping

Swarm auto-selects agents based on task keywords:

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

### Model Tiers

| Tier | Model | Agent Types |
|------|-------|-------------|
| Tier 1 | Opus | architecture, security, code review |
| Tier 2 | Sonnet | most specialists |
| Tier 3 | Haiku | fast operational tasks |

## The Blackboard Pattern

Agents coordinate through shared state:

**Pheromone Trails:**
- `discovery` - "Found something interesting"
- `warning` - "Be careful here"
- `blocker` - "This is broken"
- `hot` - "High activity area"

**Flow:**
1. Agents explore, leave trails
2. Other agents see trails, adjust focus
3. Findings recorded for future sessions

## When to Use Swarm

**Single agent:** Simple tasks, quick fixes, direct questions

**Swarm:** Complex investigations, architecture decisions, multi-perspective analysis

## Credits

Agent pool by [@wshobson](https://github.com/wshobson) - [wshobson/agents](https://github.com/wshobson/agents)
