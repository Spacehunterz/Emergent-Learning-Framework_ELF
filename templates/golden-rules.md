# Golden Rules

These are proven principles with high confidence. They are ALWAYS loaded into context.

---

## 1. Query Before Acting
> Always check existing knowledge before starting a task.

**Why:** Prevents repeating known mistakes and leverages accumulated wisdom.
**Promoted:** Initial setup
**Validations:** Foundational

---

## 2. Document Failures Immediately
> Record failures while context is fresh, before moving on.

**Why:** Details fade quickly; immediate documentation captures root causes.
**Promoted:** Initial setup
**Validations:** Foundational

---

## 3. Extract Heuristics, Not Just Outcomes
> Don't just note what happened; extract the transferable principle.

**Why:** Outcomes are specific; heuristics apply broadly.
**Promoted:** Initial setup
**Validations:** Foundational

---

## 4. Break It Before Shipping It
> Actively try to break your solution before declaring it done.

**Why:** You will find bugs now or users will find them later.
**Promoted:** Initial setup
**Validations:** Foundational

---

## 5. Escalate Uncertainty
> When unsure about high-stakes decisions, escalate to CEO.

**Why:** Better to ask than to assume incorrectly on important matters.
**Promoted:** Initial setup
**Validations:** Foundational

---

## 6. Record Learnings Before Ending Session
> Before closing any significant work session, review and record what was learned.

**Why:** The system only works if you use it. We built an entire learning framework and almost forgot to record the bugs we found while building it. Ironic and instructive.
**Promoted:** 2024-11-30 (first real failure)
**Validations:** 1 (the meta-failure itself)

---

# How Rules Become Golden

1. Start as heuristic with confidence 0.5
2. Each validation increases confidence
3. Each violation decreases confidence
4. When confidence > 0.9 AND validations > 10, eligible for promotion
5. CEO reviews and promotes to golden
6. Golden rules are loaded in EVERY agent context

---

## 7. Obey Direct Commands Immediately
> When user gives a direct action command (close, stop, kill, quit), execute it FIRST before anything else.

**Why:** User trust depends on responsiveness. Ignoring direct commands causes frustration and breaks trust.
**Promoted:** 2025-12-01 (from failure: ignored user command to close overlay)
**Validations:** 1

---

## 8. Log Before Summary
> Complete all logging to the building BEFORE giving the user a summary. The summary is the final step, not the trigger to log.

**Why:** Summaries signal "I'm done" to the user. If logging happens after, it requires user to remind you. Logging is part of completing the work, not a separate afterthought.
**Promoted:** 2025-12-01 (from repeated user feedback about wrong order)
**Validations:** 1

---

## 9. useEffect Callback Dependencies Cause Loops
> useEffect with callback deps causes reconnect loops - use refs for callbacks, empty deps for mount-only effects

**Why:** React useEffect re-runs when dependencies change. Callbacks like onMessage are new references each render, causing effect to re-run and reconnect WebSocket. Fix: store callback in useRef, update ref in separate effect, use empty [] deps for connection effect.
**Promoted:** 2025-12-11 (WebSocket reconnect loop debugging)
**Validations:** 1 (painful debugging session)


---

## 10. Trust User Reality Over Tool Metadata
> When user reports something is broken/empty/wrong, believe them immediately over tool outputs showing "valid" data.

**Why:** Tools can report files exist, sizes look right, headers check out, APIs confirm presence - but the actual content can still be empty/corrupt. The user sees the real result. Metadata lies; user experience doesn't.
**Promoted:** 2025-12-12 (from wasted 30 minutes insisting images were "valid" when user said blank)
**Validations:** 1

---

## 11. No External APIs - Subscription Only
> NEVER suggest external API calls (OpenAI, Anthropic API, etc.). This is a subscription-based app. Use Claude Code subagents via Task tool, covered by user's Max plan.

**Why:** User pays for Max subscription. Suggesting API calls means extra costs, API keys, external dependencies. Everything must work through Claude Code's existing infrastructure (Task tool with haiku/sonnet/opus models). No exceptions.
**Promoted:** 2025-12-13 (CEO direct order after repeated violations)
**Validations:** CONSTITUTIONAL - immediate promotion by CEO decree

---

## 12. Always Use Async Subagents
> Default to `run_in_background=True` for ALL subagent spawns. Block with TaskOutput only when you actually need the result. Never use synchronous subagents.

**Why:** Async lets you do other work while agents run. Multiple agents can run in parallel. Sync wastes time waiting. There's NO good reason to block immediately on spawn.
**Promoted:** 2025-12-13 (CEO identified that sync is pointless - async + block when needed is always better)
**Validations:** CONSTITUTIONAL - default behavior change
