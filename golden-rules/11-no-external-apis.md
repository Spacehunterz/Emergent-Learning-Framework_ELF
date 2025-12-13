# Golden Rule 11: No External APIs - Subscription Only

> NEVER suggest external API calls (OpenAI, Anthropic API, etc.). This is a subscription-based app. Use Claude Code subagents via Task tool, covered by user's Max plan.

## Why

User pays for Max subscription. Suggesting API calls means:
- Extra costs on top of subscription
- API keys to manage
- External dependencies
- Security/privacy concerns

Everything must work through Claude Code's existing infrastructure:
- Task tool with haiku/sonnet/opus models
- Run in background for async work
- No external services

## No Exceptions

This is CONSTITUTIONAL. CEO decree. Do not suggest:
- `anthropic.messages.create()`
- `openai.chat.completions.create()`
- Any `pip install anthropic` or similar
- Any API key configuration

## Correct Approach

```python
# WRONG - API call
response = anthropic.messages.create(model="claude-3-haiku", ...)

# RIGHT - Task tool subagent
Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt="...",
    run_in_background=True
)
```

---

**Promoted:** 2025-12-13
**Authority:** CEO direct order after repeated violations
**Status:** CONSTITUTIONAL - immediate promotion
