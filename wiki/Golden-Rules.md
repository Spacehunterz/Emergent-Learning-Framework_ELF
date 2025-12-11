# Golden Rules

Golden Rules are constitutional principles all agents follow.

## Built-in Rules

1. **Query Before Acting** - Always check the building first
2. **Document Failures Immediately** - Record while context is fresh
3. **Extract Heuristics** - Document the WHY, not just outcomes
4. **Break It Before Shipping** - Test destructively before release
5. **Escalate Uncertainty** - Ask when unsure about big decisions

## Adding Project-Specific Rules

**Step 1:** Identify the pattern
- Validated 10+ times
- Applies broadly to your project
- Saves significant time when followed

**Step 2:** Add to CLAUDE.md
```markdown
## 6. Always Use Retry Logic for External APIs
> Any call to external services must include exponential backoff

**Why:** Third-party APIs are unreliable. Silent failures caused 3 incidents.
**Promoted:** 2025-12-01
**Validations:** 15
```

## Promoting Heuristics

When a heuristic has proven itself (confidence > 0.9, validations > 10):

1. Check confidence: `python query.py --context | grep "pattern"`
2. Edit `~/.claude/emergent-learning/memory/golden-rules.md`
3. Update CLAUDE.md to reference it

## Best Practices

**Good rules:**
- "Validate user input before processing"
- "Check file existence before reading"

**Bad rules:**
- "Use Joi schema with these exact fields" (too specific)
- "Be careful with files" (not actionable)

**Include the Why:**
- Good: "Hash passwords (Why: plaintext caused breach)"
- Bad: "Hash passwords"
