# CEO Decision: Track Claude Code Task Agents in Dashboard

**Date:** 2025-12-10
**Priority:** Medium
**Status:** Pending

## Context

The dashboard tracks workflow runs from the **conductor** system, but when we spawn agents using Claude Code's built-in `Task` tool (subagents), these don't get recorded. Today we ran 8 security audit agents - none showed up in the dashboard.

## The Gap

| Agent Type | Tracked? | Where |
|------------|----------|-------|
| Conductor workflows | ✅ Yes | workflow_runs table |
| Claude Code Task agents | ❌ No | Not recorded |

## Options

### Option 1: Hook Claude Code agents into conductor
- Add a hook that fires when Task agents complete
- Record to workflow_runs or a new task_runs table
- **Pro:** Unified tracking
- **Con:** May require Claude Code hooks customization

### Option 2: Use conductor for all multi-agent work
- Stop using Claude Code's Task tool for complex work
- Route everything through conductor
- **Pro:** Full control, already works
- **Con:** Loses convenience of Task tool

### Option 3: Separate tracking for ad-hoc agents
- Create new table `adhoc_agent_runs`
- Manual recording via script after agent work
- **Pro:** Simple, flexible
- **Con:** Manual step, easy to forget

### Option 4: Leave as-is
- Dashboard tracks formal workflows only
- Task agents are "informal" and don't need tracking
- **Pro:** No work needed
- **Con:** Incomplete picture of agent activity

## Questions for CEO

1. Do you want ALL agent activity tracked, or just formal workflows?
2. Is manual recording acceptable, or must it be automatic?
3. Should Task agents and conductor workflows be in the same table or separate?

## Recommendation

Option 3 (separate tracking with easy recording script) seems pragmatic - keeps it simple while allowing tracking when desired.

---
*Created by: Claude session 2025-12-10*
