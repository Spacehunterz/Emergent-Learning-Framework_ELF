# Error Prevention Over Context Efficiency

## Heuristic
When designing enforcement systems, prioritize error prevention over token/context efficiency.

## Rationale
- One prevented mistake pays for 10+ queries
- 15 minutes wasted > 10 seconds querying
- Context window is renewable; user trust is not

## Applied Decision
Golden rule enforcer: Cooldown disabled (was 10 min, now 0). Every 3 investigation tools requires fresh building query.

## Date
2025-12-02

## Domain
enforcement, design-decisions
