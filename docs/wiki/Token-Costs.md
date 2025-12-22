# Token Costs

This adds tokens to usage. Here's the breakdown:

## Per-Session Costs

- **CLAUDE.md load:** ~1,500 tokens (once per session)
- **Golden rules injection:** ~500 tokens (every session)

## Per-Task Costs

- **Pre-hook query:** 200-500 tokens
- **Heuristic injection:** 50-200 tokens per heuristic
- **Post-hook recording:** Minimal (writes to DB, no API)

## Typical Usage

| Scenario | Token Overhead |
|----------|----------------|
| Simple task, no heuristics | ~1,700 tokens |
| Task with 3 heuristics | ~2,000 tokens |
| Complex task, 10+ heuristics | ~2,500 tokens |
| Swarm multi-agent | 2,500 x N agents |

## Cost-Benefit

**The tradeoff:** Higher tokens per task, but fewer wasted attempts.

**Example:**
- Without ELF: Repeat bug 5 times = 50 wasted messages
- With ELF: 500 extra tokens, avoid those 50 messages
- Break-even: Avoid 1-2 repeated bugs

## Reducing Costs

1. **Prune low-value heuristics** - Archive confidence < 0.3
2. **Use domain queries** - `--domain testing` instead of `--context`
3. **Disable for trivial tasks** - Settings profile without hooks
4. **Periodic cleanup** - Review heuristics monthly
