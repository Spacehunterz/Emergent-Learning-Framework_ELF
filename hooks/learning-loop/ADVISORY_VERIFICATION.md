# Advisory Verification System

## Overview

The Advisory Verification system analyzes Edit and Write tool operations for risky patterns and provides warnings, but **NEVER blocks operations**. This is a key philosophical difference from traditional security tools: we inform, but humans decide.

## Philosophy

**Advisory Only, Human Decides**

- Warnings are surfaced to stderr and logged to the building
- Operations always proceed (decision: "approve")
- Multiple warnings trigger an escalation recommendation
- The system learns from patterns but trusts human judgment

## How It Works

### 1. Post-Tool Hook Integration

The `post_tool_learning.py` hook intercepts Edit and Write tools:

```python
if tool_name in ('Edit', 'Write'):
    verifier = AdvisoryVerifier()
    result = verifier.analyze_edit(file_path, old_content, new_content)

    if result['has_warnings']:
        log_advisory_warning(file_path, result)

    # ALWAYS approve - never block
    output_result({"decision": "approve", "advisory": result})
```

### 2. Pattern Detection

The system checks for risky patterns in **newly added lines only** (not existing code):

#### Code Risks
- `eval()` - potential code injection
- `exec()` - potential code injection
- `shell=True` in subprocess - command injection risk
- Hardcoded passwords
- Hardcoded API keys
- SQL injection patterns (string concatenation in queries)

#### File Operation Risks
- `rm -rf /` - dangerous recursive delete
- `chmod 777` - overly permissive permissions
- Writing to `/etc/` - system config modification

### 3. Warning Levels

**Single Warning:**
```
⚠️ Review flagged items before proceeding
```

**Multiple Warnings (3+):**
```
⚠️ Multiple concerns - consider CEO escalation
```

**No Warnings:**
```
No concerns detected.
```

## Example Output

When a risky pattern is detected:

```
[ADVISORY] code: eval() detected - potential code injection risk
           Line: result = eval(user_input)
```

For multiple warnings:

```
[ADVISORY] code: eval() detected - potential code injection risk
           Line: result = eval(user_input)
[ADVISORY] code: Hardcoded password detected
           Line: password = "secret123"

[ADVISORY] ⚠️ Multiple concerns - consider CEO escalation
           File: /path/to/risky_file.py
```

## Logging to the Building

All warnings are logged to the building's metrics table:

```sql
INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
VALUES ('advisory_warning', 'code', 1, 'file:/path/to/file.py', 'eval() detected...')
```

This allows:
- Dashboard visualization of risky operations
- Pattern analysis over time
- Hotspot identification (which files get frequent warnings)

## Adding New Patterns

Edit `RISKY_PATTERNS` in `post_tool_learning.py`:

```python
RISKY_PATTERNS = {
    'code': [
        (r'pattern_regex', 'Warning message'),
        # Add new code patterns here
    ],
    'file_operations': [
        (r'pattern_regex', 'Warning message'),
        # Add new file operation patterns here
    ],
    'new_category': [
        # Add entirely new categories
    ]
}
```

### Pattern Guidelines

1. **Use regex for flexibility** - `r'eval\s*\('` matches `eval(`, `eval (`, etc.
2. **Be specific to avoid false positives** - Match context, not just keywords
3. **Provide actionable messages** - "Hardcoded password detected" is better than "Security issue"
4. **Test your patterns** - Add tests to `test_advisory.py`

## Testing

Run the test suite:

```bash
cd ~/.claude/emergent-learning/hooks/learning-loop
python test_advisory.py
```

Tests verify:
- Pattern detection works correctly
- Only new lines are checked (not existing code)
- Safe code doesn't trigger false positives
- Multiple warnings trigger escalation recommendation
- All defined patterns can be matched

## Key Design Decisions

### Why Advisory Only?

1. **Trust over enforcement** - Humans make better context-aware decisions
2. **Learning system** - We want to observe patterns, not dictate them
3. **Avoid blocking legitimate work** - False positives would be frustrating
4. **Institutional memory** - Warnings accumulate in the building for analysis

### Why Check Only Added Lines?

1. **Focus on new risks** - Don't flag existing technical debt
2. **Reduce noise** - Legacy code may have valid reasons for patterns
3. **Progressive improvement** - Encourage better patterns going forward
4. **Performance** - Simple diff is faster than full file analysis

### Why Multiple Warnings → CEO Escalation?

1. **Cumulative risk** - One issue might be acceptable, many indicate problems
2. **Human judgment call** - CEO (user) should review high-risk changes
3. **Not blocking** - Still advisory, just stronger recommendation

## Integration with Building

Advisory warnings feed into:

1. **Metrics** - Track warning frequency and categories
2. **Hotspots** - Files with frequent warnings become hotspots
3. **Dashboard** - Visualize risky operations over time
4. **Learning Loop** - Patterns that cause issues can become heuristics

## Future Enhancements

Potential improvements:

1. **Context-aware patterns** - Different rules for test files vs production
2. **Severity levels** - Info, Warning, Critical (still all advisory)
3. **Custom patterns per project** - Allow `.advisory-rules.json` in projects
4. **Machine learning** - Learn which warnings users actually fix
5. **Integration with failures** - If warned code causes failure, increase pattern confidence

## Remember

**Warnings are advisory. Humans decide. Always.**

This system exists to inform and guide, not to restrict or block. It's a learning tool, not a security gate.
