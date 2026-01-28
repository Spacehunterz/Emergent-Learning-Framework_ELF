# Plan Mode Integration

This page details how ELF integrates with Claude Code's Plan Mode to ensure heuristics are applied during plan creation.

## The Problem (Issue #98)

Plan creation happens in multiple contexts:

| Context | Hook Coverage | Issue |
|---------|--------------|-------|
| User presses Shift+Tab | ❌ No hook fires | Heuristics not loaded |
| `--permission-mode plan` | ❌ No hook fires | Heuristics not loaded |
| Claude thinks "I'll plan..." | ❌ No hook fires | Heuristics not loaded |
| Claude calls `EnterPlanMode` | ✅ PreToolUse fires | Works |
| Claude spawns Plan subagent | ✅ SubagentStart fires | Works |
| Claude writes plan to `.md` | ✅ PreToolUse fires | **Our solution** |

**The Insight:** Plans must eventually be written to files. We catch the write operation.

---

## Our Solution: Multi-Layer Approach

### Layer 1: Pre-Tool Semantic Memory

When Claude writes a plan file, we:

1. **Detect** plan context (path + thinking)
2. **Boost** planning-relevant heuristics
3. **Inject** with special 🎯 formatting
4. **Track** what was injected for validation

### Layer 2: Post-Tool Validation

After the plan is written, we:

1. **Read** the plan content
2. **Check** if injected heuristics were addressed
3. **Warn** if any are missing

---

## Plan Detection

### File-Based Detection

```python
PLAN_PATH_PATTERNS = [
    ".claude/plans/",      # Standard plan directory
    "/plans/",             # Any plans folder
    "roadmap",             # Roadmap files
    "architecture",        # Architecture docs
    "design.md",           # Design documents
]
```

**Matches:**
- `~/.claude/plans/auth-refactor.md`
- `~/project/docs/architecture-overview.md`
- `/tmp/roadmap-q1.md`

### Thinking-Based Detection

```python
PLAN_KEYWORDS = [
    "create a plan",
    "design document",
    "architecture for",
    "roadmap",
    "strategy for",
    "planning to",
]
```

**Matches thinking like:**
- "I need to create a plan for the authentication system"
- "Let me design the architecture for this feature"
- "I'll write a strategy document"

---

## Heuristic Boosting

During plan mode, these heuristics get priority:

### Golden Rules (+20% boost)

Always shown prominently:
```
⭐ GOLDEN RULES (Must Apply to Plan)
- Always validate inputs at system boundaries
- Use Sequential Thinking for complex tasks
```

### Sequential Thinking (+15% boost)

Patterns matching:
- "sequential thinking"
- "step by step"
- "before implementing"

### Architecture Patterns (+15% boost)

Patterns matching:
- "architecture decision record"
- "adr"
- "design pattern"

---

## Validation

### What Gets Validated

After a plan is written, we check if it addresses:

1. **Sequential Thinking** - Are there numbered steps?
2. **Input Validation** - Is data validation mentioned?
3. **ADRs** - Are architectural decisions documented?
4. **Testing** - Is test strategy included?

### How Validation Works

```python
def check_heuristic_addressed(rule: str, plan_content: str) -> bool:
    # Extract key concepts from rule
    concepts = extract_key_concepts(rule)
    # e.g., "Use Sequential Thinking" → ["sequential", "thinking", "step"]
    
    # Count matches in plan
    matches = sum(1 for c in concepts if c in plan_content.lower())
    
    # Consider addressed if 2+ concepts found
    return matches >= 2
```

### Example Validation

**Injected heuristic:** "Use Sequential Thinking before implementing critical changes"

**Plan content:**
```markdown
# Auth Refactor Plan

## Steps
1. Audit current JWT implementation
2. Update validation logic
3. Add tests
4. Deploy
```

**Result:** ✅ ADDRESSED (steps present)

---

**Injected heuristic:** "Create Architecture Decision Records for major changes"

**Plan content:**
```markdown
# Auth Refactor Plan

We'll use JWT tokens for auth.

## Steps
1. Update code
2. Test
```

**Result:** ❌ MISSING (no ADR mentioned)

---

## Configuration

### Enable/Disable Plan Detection

Currently always enabled. To request a toggle:

```bash
# Proposed environment variable
export ELF_PLAN_DETECTION=true  # or false
```

### Adjust Boost Levels

Edit `pre_tool_semantic_memory.py`:

```python
BOOST_CONFIG = {
    "golden_rule": 0.20,           # +20%
    "sequential_thinking": 0.15,   # +15%
    "architecture_decision": 0.15, # +15%
    # Add your own
    "my_pattern": 0.10,
}
```

---

## Testing

### Manual Test

```bash
# Start Claude Code
claude

# Enter plan mode or create a plan file
# Write plan to ~/.claude/plans/test.md

# Check if heuristics were injected
# Look for 🎯 [Plan Mode] header in context

# Check validation
# After writing, see if warnings appear for missing heuristics
```

### Automated Test

```bash
python test_plan_semantic_memory.py
```

Expected output:
```
TEST 4: Formatting - Plan vs Regular
  ✓ Plan mode formatting correct
  Sample Plan Mode Output:
    ---
    ## 🎯 [Plan Mode] Critical Heuristics
    ...
```

---

## Best Practices

### For Users

1. **Write plans to `.claude/plans/`** - Ensures detection
2. **Mention methodology in thinking** - "I'll use Sequential Thinking"
3. **Address injected heuristics** - Don't ignore the warnings
4. **Update plans if warned** - Add missing considerations

### For Contributors

1. **Add planning patterns** - Edit `PLAN_BOOST_PATTERNS`
2. **Test with real plans** - Verify detection works
3. **Document new patterns** - Update this wiki page

---

## Future Enhancements

### SubagentStart Hook

When spawning a Plan subagent, inject context directly:

```python
# SubagentStart hook (proposed)
if agent_type == "Plan":
    heuristics = query_semantic_heuristics(agent_prompt)
    return {"additionalContext": format_for_planning(heuristics)}
```

### PrePlan Hook

Claude Code doesn't have a native PrePlan hook, but we could simulate:

```python
# Detect planning intent in thinking
if "plan" in thinking and "implement" in thinking:
    return {"decision": "ask", "reason": "Planning detected. Load heuristics?"}
```

### LLM-Based Validation

Instead of keyword matching, use LLM to validate:

```python
# Send plan + heuristics to Haiku
# Ask: "Does this plan address these heuristics?"
# More accurate but higher latency
```

---

## Troubleshooting

### Plan not detected

```bash
# Check file path
ls -la ~/.claude/plans/

# Check detection logic
python -c "
from pre_tool_semantic_memory import detect_plan_context
print(detect_plan_context('~/.claude/plans/test.md', None))
"
```

### Heuristics not boosted

```bash
# Check heuristic content
grep -i "sequential\|step by step" memory/index.db

# Check boosting logic
python -c "
from pre_tool_semantic_memory import boost_plan_heuristics
heuristics = [{'rule': 'Use Sequential Thinking', 'is_golden': False, '_final_score': 0.5}]
print(boost_plan_heuristics(heuristics))
"
```

### Validation not working

```bash
# Check if plan is detected as plan file
# Check validation threshold (2+ concepts)
# Lower threshold to 1 for testing
```

---

## See Also

- [Mid-Stream Semantic Memory](./Mid-Stream-Semantic-Memory)
- [Issue #98](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues/98)
- [Hooks Reference](./Hooks)
