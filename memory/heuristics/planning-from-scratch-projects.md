---
domain: architecture
confidence: medium
validations: 1
created: 2025-12-03
tags: [planning, from-scratch, systems-programming]
---

# Planning From-Scratch Systems Projects

## Pattern
When planning a "from scratch" project (no external dependencies), always:
1. Define what "from scratch" actually means (OS APIs? FFI? Dev tools?)
2. Identify the HIGHEST RISK component (often font rendering or GPU)
3. Plan to tackle high-risk early to fail fast
4. Have fallback plan for each risky component
5. Build in vertical slices (window→GPU→text→feature) not horizontal layers

## Rationale
- "From scratch" is ambiguous - clarify with user
- High-risk components can block everything if left to end
- Vertical slices give working demos at each milestone
- Fallbacks prevent complete project failure

## Example
Claudex terminal emulator:
- Highest risk: Font rendering (TTF parsing + Bezier rasterization)
- Scheduled for weeks 5-12 (early, not late)
- Fallback: Use DirectWrite temporarily, replace later
- Vertical slice: Each milestone has visible progress

## Exceptions
- If timeline is flexible, can explore high-risk without fallback
- If user explicitly wants no fallbacks (learning is the goal)
