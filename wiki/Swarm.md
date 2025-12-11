# Swarm: Multi-Agent Coordination

**Requires Pro or Max plan** - Free plan can't use Task tool for subagents.

## What It Does

The conductor coordinates multiple Claude Code subagents with distinct personas:

| Agent | Role | When to Use |
|-------|------|-------------|
| **Researcher** | Deep investigation | "We need to understand X" |
| **Architect** | System design | "How should we structure X?" |
| **Skeptic** | Breaking things | "Is this robust?" |
| **Creative** | Novel solutions | "We're stuck on X" |

## Using Swarm

```bash
/swarm investigate the authentication system    # Start task
/swarm show                                     # View state
/swarm reset                                    # Clear and restart
/swarm stop                                     # Stop all agents
/swarm                                          # Continue pending
```

**Example:**
```
You: /swarm investigate why the API is slow

Claude: ## Swarm Plan
        **Task:** Investigate API performance
        **Agents:** 3

        | # | Subtask | Scope |
        |---|---------|-------|
        | 1 | Profile endpoints | src/api/ |
        | 2 | Check database queries | src/db/ |
        | 3 | Review caching | src/cache/ |

        Proceed? [Y/n]
```

## The Blackboard Pattern

Agents coordinate through shared SQLite database:

**Pheromone Trails:**
- `discovery` - "Found something interesting"
- `warning` - "Be careful here"
- `blocker` - "This is broken"
- `hot` - "High activity area"
- `cold` - "Already explored"

**Flow:**
1. Researcher explores, leaves `discovery` trails
2. Architect sees trails, focuses design
3. Skeptic leaves `warning` on risky parts
4. Findings recorded for future sessions

## Agent Personalities

Defined in `~/.claude/emergent-learning/agents/`:

**Researcher:** Thorough, methodical, breadth-first
**Architect:** Top-down, structural, considers extensions
**Skeptic:** Adversarial, tests edge cases
**Creative:** Lateral thinking, challenges assumptions

## Query Conductor

```bash
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflows
python ~/.claude/emergent-learning/conductor/query_conductor.py --failures
python ~/.claude/emergent-learning/conductor/query_conductor.py --hotspots
python ~/.claude/emergent-learning/conductor/query_conductor.py --trails --scent blocker
```

## When to Use Swarm

**Single agent:** Simple tasks, quick fixes, direct questions

**Swarm:** Complex investigations, architecture decisions, debugging from multiple angles
