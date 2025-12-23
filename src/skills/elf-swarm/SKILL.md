---
name: swarm
description: Coordinate multi-agent orchestration for complex tasks. Launch parallel and sequential agents, manage dependencies, aggregate results, and orchestrate sophisticated workflows. Use for tasks requiring multiple specialized perspectives or parallel processing.
license: MIT
---

# ELF Swarm Coordination Command

Orchestrate multi-agent workflows for complex tasks requiring parallel processing or multiple specialized perspectives.

## Purpose

The `/swarm` command enables:
- **Parallel processing** - Multiple agents working simultaneously
- **Specialized perspectives** - Researcher, Architect, Creative, Skeptic agents
- **Dependency management** - Sequential processing when needed
- **Result aggregation** - Combine outputs from multiple agents
- **Sophisticated workflows** - Complex orchestration patterns

## Usage Examples

```
/swarm analyze my architecture from 4 perspectives
/swarm run parallel searches on [topics]
/swarm investigate this failure through agent lenses
/swarm parallelize this migration task
```

## Key Agent Perspectives

**Researcher**
- Asks: "What does the evidence say?"
- Strength: Finds authoritative knowledge
- Use: For data-driven decisions

**Architect**  
- Asks: "How does this scale?"
- Strength: Systems thinking
- Use: For structural decisions

**Creative**
- Asks: "What if we tried something different?"
- Strength: Novel solutions
- Use: When stuck on problems

**Skeptic**
- Asks: "What could go wrong?"
- Strength: Finds edge cases
- Use: For validation

## How Swarm Orchestration Works

When you invoke `/swarm`:

1. **Parse your request** - Understand task and constraints
2. **Plan execution** - Determine parallel vs sequential
3. **Launch agents** - Spawn subagents in background
4. **Manage dependencies** - Block only when needed
5. **Aggregate results** - Combine perspectives
6. **Synthesize insights** - Extract unified understanding

## Swarm Patterns

### Parallel Analysis
Launch all 4 agents simultaneously on the same problem.
Best for: Complex decisions, design reviews, failure analysis

### Sequential Pipeline
Run agents in sequence where each builds on previous.
Best for: Iterative refinement, progressive investigation

### Expert Consultation
Launch specific agents for their expertise.
Best for: Targeted investigation

### Parallel + Synthesis
Run multiple agents in parallel, then synthesize results.
Best for: Comprehensive analysis

## Agent Coordination Rules

- **Always run in background** - `run_in_background=True`
- **Block only when needed** - Use `TaskOutput` to wait for results
- **Specify agent type** - Researcher, Architect, Creative, Skeptic
- **Use models efficiently** - Haiku for small tasks, Sonnet/Opus for complex
- **Aggregate thoughtfully** - Synthesize perspectives, don't just list them

## Integration with ELF

Swarm results can feed back into the building:
- **Document learnings** - Record what agents discovered
- **Update heuristics** - If swarm validates/challenges existing knowledge
- **Propose rules** - If discovery is universal enough
- **Escalate decisions** - If swarm surfaces ambiguity

## Example Workflow

```
1. User: "/swarm analyze my architecture from 4 perspectives"
2. System: Launches 4 agents in parallel
   - Researcher: Evidence-based evaluation
   - Architect: Structural analysis
   - Creative: Alternative approaches
   - Skeptic: Risk identification
3. System: Aggregates results into synthesis
4. User: Gets comprehensive perspective
5. Building: Results documented if significant
```

## When to Use Swarm

- **Complex decisions** - Need multiple viewpoints
- **Ambitious goals** - Parallel processing helps
- **Risk management** - Skeptic finds what you missed
- **Stuck problems** - Creative breaks conventional thinking
- **Learning opportunities** - Results feed building's knowledge
