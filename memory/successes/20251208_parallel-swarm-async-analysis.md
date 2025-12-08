# Success: Parallel Swarm Analysis of Async Agents

**Date:** 2025-12-08
**Domain:** coordination, architecture, multi-agent
**Significance:** 5
**Tags:** async-agents, parallel-execution, swarm, stigmergy, coordination

## What Worked
Spawned 4 background agents in parallel (Skeptic, Creative, Researcher, Architect) to deeply analyze Claude Code's new async/background agent feature. Each agent brought a different perspective:
- **Skeptic**: Found pitfalls and blockers
- **Creative**: Found novel use cases and the 10x insight
- **Architect**: Designed patterns and abstractions
- **Researcher**: Surveyed industry landscape and prior art

All 4 ran simultaneously using Claude Code's `run_in_background: true` parameter on the Task tool. Results collected via `AgentOutputTool` as each completed.

## Key Decisions
1. Used `general-purpose` subagent type for deep thinking (not `Explore`)
2. Gave each agent a distinct personality/perspective from ELF's agent personas
3. Used `[SWARM]` marker in prompts for coordination protocol compatibility
4. Collected results as they arrived rather than waiting for all

## Why It Worked
1. **Parallel execution**: 4 agents working simultaneously = faster than sequential
2. **Diverse perspectives**: Each agent found things others missed
3. **Non-blocking coordinator**: Could chat with user while agents worked
4. **Structured output**: `## FINDINGS` format enabled synthesis

## Replicability
Yes - this pattern can be replicated for any complex analysis task:
1. Identify 3-4 distinct perspectives needed
2. Spawn agents with clear personas and output formats
3. Collect results as they complete
4. Synthesize findings

Best for: Architecture decisions, research questions, risk analysis, brainstorming

## Heuristics Extracted
> Append-only event logs enable stigmergic coordination - agents write events, coordination emerges from environment, eliminates race conditions.

> Async agent value is continuous daemons not parallel speedup - the 10x value is always-running background processes, not just faster parallel execution.

> Parallel agent cost is multiplicative not additive - each agent pays full context cost, 15x tokens for 90% time reduction.

## Key Insight: Stigmergic Agent Networks
The synthesis of all 4 agents revealed: combining append-only event logs (Architect) with pheromone trail patterns (Researcher) with continuous daemon concept (Creative) while avoiding race conditions (Skeptic) = stigmergic agent networks where coordination emerges from environment modification rather than direct communication.

This is the architectural pattern ELF should evolve toward.

## Related
- ELF blackboard.py - current coordination mechanism
- ELF conductor.py - workflow orchestration
- Anthropic multi-agent research system - 90% time reduction, 15x tokens
- Swarm intelligence / ant colony optimization - stigmergy concept
