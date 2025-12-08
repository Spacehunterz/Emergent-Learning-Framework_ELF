# Heuristic: Assessing When Swarms Help Refactoring

**ID:** swarm-refactoring-assessment
**Created:** 2025-12-05
**Domain:** swarm, refactoring
**Confidence:** 0.6

## Pattern
Swarms can parallelize module extraction, but the benefit depends on file characteristics.

## When Swarms Help
1. **Large files** (1000+ lines) - enough work to parallelize
2. **Clear section boundaries** - comment headers, logical groupings
3. **Multiple independent chunks** - sections that don't cross-reference heavily
4. **Analysis-heavy work** - understanding dependencies, planning extraction

## When Swarms Don't Help
1. **Small files** - coordination overhead exceeds benefit
2. **Tightly coupled code** - everything depends on everything
3. **Sequential dependencies** - A must complete before B can start
4. **Simple mechanical changes** - single agent is faster

## Assessment Questions
Before spawning a swarm for refactoring, ask:
1. Is the file large enough? (>1000 lines)
2. Are there 3+ independent sections?
3. Can I extract a dependency bottleneck first?
4. Will coordination overhead be worth it?

## Evidence
- Claudex: 2216 lines, 12 sections, 4 parallel agents → SUCCESS
- Swarm extracted 4 modules simultaneously after Grid unblocked them

## Validation Count
1
