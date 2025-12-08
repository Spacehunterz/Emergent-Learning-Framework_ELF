# Async Agent Heuristics

**Domain:** coordination, multi-agent
**Confidence:** 0.8
**Validations:** 1

## Core Heuristics

### Async value is continuous daemons, not parallel speedup
> The 10x value of async agents is always-running background processes, not just faster parallel execution.

**Why:** Security daemon, quality daemon, learning daemon - these provide continuous value. Parallel speedup is nice but costs 15x tokens for 90% time reduction.

### Parallel agent cost is multiplicative not additive
> Each parallel agent pays full context cost independently.

**Why:** 4 agents = 4x token cost minimum, not 1x with parallelism.

### Stigmergic coordination via environment
> Agents coordinate by modifying shared environment (event logs) rather than direct messaging.

**Why:** Like ant pheromone trails - coordination emerges from environment, no central coordinator needed.

### Non-blocking coordinator is the unlock
> Coordinator can continue working while agents run in background.

**Why:** User interaction continues, agents report back when done.

## Patterns

### Swarm Analysis Pattern
1. Spawn 3-5 agents with distinct perspectives (Skeptic, Architect, Researcher, Creative)
2. Each runs in background with run_in_background: true
3. Collect results as they complete via AgentOutputTool
4. Synthesize findings

### Continuous Daemon Pattern
1. Spawn long-running background agent
2. Agent monitors for relevant events
3. Reports findings periodically
4. Runs until explicitly stopped
