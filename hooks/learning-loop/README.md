# Learning Loop Hooks

Advisory security verification and learning loop hooks for the Emergent Learning Framework.

## Overview

This directory contains hooks that:
1. **Pre-tool**: Load relevant heuristics before tasks (`pre_tool_learning.py`)
2. **Post-tool**: Validate outcomes and log learnings (`post_tool_learning.py`)
3. **Advisory verification**: Warn about risky code patterns (never blocks)

## AdvisoryVerifier

The AdvisoryVerifier scans code edits for security risks and provides **advisory warnings only**. It never blocks operations - the human decides.

### Philosophy

> "Advisory only, human decides."

The verifier warns about potentially risky patterns but always approves. Warnings are logged to the building for visibility.

### Pattern Categories

| Category | Patterns | Description |
|----------|----------|-------------|
| `code` | 13 | Code injection, hardcoded secrets, SQL injection |
| `file_operations` | 3 | Dangerous file operations (rm -rf, chmod 777) |
| `deserialization` | 3 | Insecure deserialization (pickle, yaml, marshal) |
| `cryptography` | 3 | Weak crypto (MD5, SHA1, random module) |
| `command_injection` | 2 | OS command execution (os.system, os.popen) |
| `path_traversal` | 2 | Directory traversal attacks |
| `network` | 2 | Insecure network settings (verify=False) |

**Total: 28 patterns across 7 categories**

### What Gets Flagged

```python
# Flagged - hardcoded password
password = "admin123"

# Flagged - insecure deserialization
data = pickle.load(untrusted_file)

# Flagged - weak hash
hash = hashlib.md5(password)

# Flagged - command injection risk
os.system(user_command)

# Flagged - SSL verification disabled
requests.get(url, verify=False)
```

### What Does NOT Get Flagged

```python
# Not flagged - comments
# eval() is dangerous, don't use it

# Not flagged - safe alternatives
data = yaml.safe_load(file)
hash = hashlib.sha256(data)
subprocess.run(["ls", "-la"])

# Not flagged - existing code (only new additions scanned)
```

### Comment Filtering

The verifier filters out pure comment lines to avoid false positives:
- Python: `#`
- JavaScript/C: `//`
- C-style: `/* */` and `*`
- Docstrings: `"""` and `'''`

Mixed lines (code + comment) ARE still scanned.

## Files

| File | Purpose |
|------|---------|
| `post_tool_learning.py` | Main hook - outcome validation + advisory verification |
| `pre_tool_learning.py` | Pre-tool hook - loads relevant heuristics |
| `security_patterns.py` | Pattern definitions for AdvisoryVerifier |
| `trail_helper.py` | Hotspot tracking (file visit trails) |

## Test Suites

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_advisory.py` | 8 | Core advisory functionality |
| `test_comment_filter.py` | 12 | Comment line filtering |
| `test_enhanced_patterns.py` | 20 | Secret detection patterns |
| `test_new_categories.py` | 41 | New pattern categories |

**Total: 81 tests**

### Running Tests

```bash
cd ~/.claude/emergent-learning/hooks/learning-loop

# Run all tests
python test_advisory.py
python test_comment_filter.py
python test_enhanced_patterns.py
python test_new_categories.py

# Quick validation
python -c "from post_tool_learning import AdvisoryVerifier; print('OK')"
```

## Hook Integration

The hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "command": "python ~/.claude/emergent-learning/hooks/learning-loop/post_tool_learning.py"
      }
    ]
  }
}
```

## Escalation

When 3+ warnings are detected in a single edit, the verifier recommends CEO escalation:

```
[!] Multiple concerns - consider CEO escalation
```

This is advisory only - the operation still proceeds.

## Adding New Patterns

Edit `security_patterns.py`:

```python
RISKY_PATTERNS = {
    'category_name': [
        (r'regex_pattern', 'Warning message to display'),
    ],
}
```

Then add tests in `test_new_categories.py`.

## Architecture

```
User Edit
    │
    ▼
┌─────────────────────┐
│  AdvisoryVerifier   │
│  ┌───────────────┐  │
│  │ _get_added_   │  │──► Only scan NEW lines
│  │    lines()    │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ _is_comment_  │  │──► Filter pure comments
│  │    line()     │  │
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ analyze_edit()│  │──► Match patterns
│  └───────────────┘  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Always Approve     │──► {"decision": "approve", "advisory": {...}}
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Log to Building    │──► metrics table, stderr
└─────────────────────┘
```

## Version History

- **Phase 4** (2025-12-11): Full test coverage, 28 patterns, 81 tests
- **Phase 3**: Added deserialization, crypto, command injection patterns
- **Phase 2**: Enhanced secret detection (password in strings)
- **Phase 1**: Comment filtering, basic patterns
