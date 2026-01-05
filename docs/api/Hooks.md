# Hook Development API

Comprehensive API reference for developing and using hooks in the Emergent Learning Framework. Hooks enable auto-injection of heuristics, outcome validation, and security verification during tool execution.

## Table of Contents

- [Overview](#overview)
- [Hook Types](#hook-types)
- [AdvisoryVerifier](#advisoryverifier)
- [Creating Custom Hooks](#creating-custom-hooks)
- [Hook Lifecycle](#hook-lifecycle)
- [Examples](#examples)

---

## Overview

ELF hooks intercept tool execution to:

1. **Pre-execution**: Inject relevant heuristics and complexity warnings
2. **Post-execution**: Validate outcomes, record learnings, and verify security
3. **Advisory only**: Security verification warns but never blocks

### Philosophy

> "Advisory only, human decides."

Hooks provide guidance and warnings but never prevent execution. All decisions remain with the human operator.

### Hook Integration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "python ~/.claude/emergent-learning/hooks/learning-loop/pre_tool_learning.py"
      }
    ],
    "PostToolUse": [
      {
        "command": "python ~/.claude/emergent-learning/hooks/learning-loop/post_tool_learning.py"
      }
    ]
  }
}
```

---

## Hook Types

### 1. Pre-Tool Hook (`pre_tool_learning.py`)

Fires **before** tool execution to inject learning context.

#### Purpose

- Auto-query relevant heuristics from the building
- Score task complexity and risk level
- Inject golden rules and domain-specific learnings
- Track which heuristics are consulted (for validation loop)

#### Input Schema

```python
{
    "tool_name": str,      # Name of tool about to execute
    "tool_input": dict     # Parameters being passed to tool
}
```

#### Output Schema

```python
{
    "decision": "approve",           # Always approve
    "tool_input": dict               # Modified input with injected context (optional)
}
```

#### Workflow

1. **Extract domains** from tool context (keywords in prompt/files)
2. **Score complexity** using `ComplexityScorer`
3. **Query heuristics** relevant to domains
4. **Get recent failures** in those domains
5. **Format learning context** with golden rules and warnings
6. **Inject into prompt** by modifying `tool_input["prompt"]`
7. **Track consultation** for post-validation

#### Complexity Scoring

The `ComplexityScorer` assigns risk levels:

```python
class ComplexityScorer:
    HIGH_RISK_PATTERNS = {
        'files': [r'auth', r'crypto', r'security', r'password', r'token'],
        'domains': ['authentication', 'security', 'database-migration'],
        'keywords': ['delete', 'drop', 'truncate', 'force', 'sudo', 'password']
    }

    MEDIUM_RISK_PATTERNS = {
        'files': [r'api', r'config', r'schema', r'migration'],
        'domains': ['api', 'configuration', 'database'],
        'keywords': ['update', 'modify', 'change', 'refactor']
    }
```

**Risk Levels:**

- `HIGH`: Extra scrutiny, consider CEO escalation
- `MEDIUM`: Moderate care required
- `LOW-MEDIUM`: Standard care
- `LOW`: Routine task

#### Injected Context Format

```markdown
---
## Building Knowledge (Auto-Injected)

### Task Complexity: HIGH ⚠️
**Reasons:**
- High-risk file pattern: auth
- High-risk keyword: password

**Recommendation:** Extra scrutiny recommended. Consider CEO escalation if uncertain.

### Golden Rules (Must Follow)
- **Never commit credentials or API keys**
- **Always validate user input before database queries**

### Relevant Heuristics (authentication, security)
- [authentication] Use bcrypt for password hashing (95% confidence, 12x validated)
- [security] Sanitize file paths to prevent traversal (88% confidence, 8x validated)

### Recent Failures (Avoid These)
- [security] Hardcoded API key detected in config file
- [authentication] JWT secret exposed in environment variable

---
```

#### API Functions

##### `extract_domain_from_context(tool_name, tool_input) -> List[str]`

Extract likely domains from tool context.

```python
domains = extract_domain_from_context("Task", {
    "prompt": "Fix authentication bug in login.py",
    "description": "Debug JWT token validation"
})
# Returns: ["authentication", "security", "python"]
```

##### `get_relevant_heuristics(domains, limit=5) -> List[Dict]`

Query heuristics for given domains.

```python
heuristics = get_relevant_heuristics(["authentication", "security"], limit=5)
# Returns: [
#     {
#         "id": 42,
#         "domain": "authentication",
#         "rule": "Use bcrypt for password hashing",
#         "explanation": "MD5/SHA1 are cryptographically weak",
#         "confidence": 0.95,
#         "times_validated": 12,
#         "is_golden": 0
#     },
#     ...
# ]
```

##### `get_recent_failures(domains, limit=3) -> List[Dict]`

Get recent failures in relevant domains.

```python
failures = get_recent_failures(["authentication"], limit=3)
# Returns: [
#     {
#         "id": 123,
#         "title": "Hardcoded password in config",
#         "summary": "Password stored in plaintext...",
#         "domain": "authentication"
#     },
#     ...
# ]
```

---

### 2. Post-Tool Hook (`post_tool_learning.py`)

Fires **after** tool execution to validate outcomes and close the learning loop.

#### Purpose

- Determine task outcome (success/failure/unknown)
- Validate consulted heuristics based on outcome
- Auto-record failures to learnings table
- Extract explicit learnings from output
- Advisory security verification for Edit/Write tools
- Lay pheromone trails for hotspot tracking
- Promote high-confidence heuristics to golden rules

#### Input Schema

```python
{
    "tool_name": str,       # Name of executed tool
    "tool_input": dict,     # Parameters that were passed
    "tool_output": dict     # Result from tool execution
}
```

#### Output Schema

```python
{
    "decision": "approve",    # Always approve
    "advisory": dict          # Optional security warnings (non-blocking)
}
```

#### Workflow for Task Tool

1. **Load session state** (which heuristics were consulted)
2. **Determine outcome** by analyzing tool output
3. **Validate heuristics**:
   - Success → increment `times_validated`, boost confidence
   - Failure → increment `times_violated`, reduce confidence
4. **Auto-record failure** if task failed
5. **Extract learnings** from output (if success)
6. **Check for golden rule promotions** (confidence ≥ 0.9, validations ≥ 10)
7. **Lay trails** for files mentioned in output

#### Workflow for Edit/Write Tools

1. **Analyze edits** using `AdvisoryVerifier`
2. **Log warnings** (non-blocking)
3. **Return approval** with advisory info

#### API Functions

##### `determine_outcome(tool_output) -> Tuple[str, str]`

Determine if task succeeded or failed.

```python
outcome, reason = determine_outcome({
    "content": "Successfully created user authentication module"
})
# Returns: ("success", "Successfully completed action")

outcome, reason = determine_outcome({
    "content": "Error: Module not found"
})
# Returns: ("failure", "Error detected")
```

**Outcome Types:**

- `success`: Task completed successfully
- `failure`: Explicit error detected
- `unknown`: Cannot determine (treated as success for optimism)

**Success Indicators:**

- Explicit phrases: "successfully", "completed", "task complete"
- Action verbs: "created", "fixed", "updated", "implemented"
- Reporting patterns: "here are the findings", "I have completed"
- Substantial output without errors (>50 chars)

**Failure Indicators:**

- Error patterns: "error:", "exception:", "failed:"
- Negative outcomes: "could not", "unable to", "permission denied"
- Timeout/not found: "timed out", "not found"

**False Positive Prevention:**

The system filters out:
- Discussions of errors: "error handling", "no errors", "fixed the error"
- Past analysis: "investigated the failure", "analyzed the error"

##### `validate_heuristics(heuristic_ids, outcome)`

Update heuristic validation counts.

```python
# On success
validate_heuristics([42, 43, 44], "success")
# Increments times_validated, boosts confidence by 0.01

# On failure
validate_heuristics([42, 43, 44], "failure")
# Increments times_violated, reduces confidence by 0.02
```

##### `auto_record_failure(tool_input, tool_output, outcome_reason, domains)`

Auto-record a failure to the learnings table.

```python
auto_record_failure(
    tool_input={"prompt": "Fix auth bug", "description": "Debug login"},
    tool_output={"content": "Error: JWT secret not found"},
    outcome_reason="Error detected",
    domains=["authentication"]
)
# Creates entry in learnings table: auto-failures/failure_TIMESTAMP.md
```

##### `extract_and_record_learnings(tool_output, domains)`

Extract explicit learnings from output.

```python
# Output contains: "[LEARNED:authentication] Always rotate JWT secrets"
extract_and_record_learnings(
    tool_output={"content": "Fixed bug. [LEARNED:authentication] Always rotate JWT secrets"},
    domains=["authentication"]
)
# Records heuristic if contains "always/never/should/must"
# Otherwise records as observation
```

**Learning Marker Format:**

```
[LEARNED:domain] description
[LEARNING:domain] description
[LEARN:domain] description
```

##### `check_golden_rule_promotion(conn)`

Promote high-confidence heuristics to golden rules.

```python
# Automatically called on each post-tool execution
check_golden_rule_promotion(conn)

# Promotes if:
# - is_golden = 0
# - confidence >= 0.9
# - times_validated >= 10
# - (times_violated = 0 OR times_validated / times_violated > 10)
```

---

## AdvisoryVerifier

Security pattern verification that warns but never blocks.

### Philosophy

> "Warn about risks, but always approve. The human decides."

### Pattern Categories

28 security patterns across 7 categories:

| Category | Count | Description |
|----------|-------|-------------|
| `code` | 13 | Code injection, hardcoded secrets, SQL injection |
| `file_operations` | 3 | Dangerous file operations |
| `deserialization` | 3 | Insecure deserialization |
| `cryptography` | 3 | Weak cryptographic functions |
| `command_injection` | 2 | OS command execution risks |
| `path_traversal` | 2 | Directory traversal attacks |
| `network` | 2 | Insecure network settings |

### API

#### `AdvisoryVerifier()`

Initialize the verifier.

```python
from post_tool_learning import AdvisoryVerifier

verifier = AdvisoryVerifier()
```

#### `analyze_edit(file_path, old_content, new_content) -> Dict`

Analyze a file edit for risky patterns.

```python
result = verifier.analyze_edit(
    file_path="config.py",
    old_content="# Empty file",
    new_content="password = 'admin123'"
)

# Returns:
{
    "has_warnings": True,
    "warnings": [
        {
            "category": "code",
            "message": "Hardcoded password detected",
            "line_preview": "password = 'admin123'"
        }
    ],
    "recommendation": "[!] Review flagged items before proceeding"
}
```

**Return Schema:**

```python
{
    "has_warnings": bool,
    "warnings": [
        {
            "category": str,        # Pattern category
            "message": str,         # Warning message
            "line_preview": str     # First 80 chars of flagged line
        }
    ],
    "recommendation": str           # Action recommendation
}
```

**Recommendations:**

- No warnings: "No concerns detected."
- 1-2 warnings: "[!] Review flagged items before proceeding"
- 3+ warnings: "[!] Multiple concerns - consider CEO escalation"

#### Comment Filtering

The verifier filters pure comment lines to avoid false positives:

```python
def _is_comment_line(line: str) -> bool:
    """Check if line is entirely a comment."""
    stripped = line.strip()
    comment_markers = ['#', '//', '/*', '*', '"""', "'''"]
    return any(stripped.startswith(marker) for marker in comment_markers)
```

**Pure comments (ignored):**

```python
# This uses eval() - dangerous
// eval() should never be used
/* Discussing pickle.load risks */
```

**Mixed lines (still scanned):**

```python
x = eval(user_input)  # Don't do this
data = pickle.load(file)  // Insecure
```

### Security Patterns

Located in `security_patterns.py`:

```python
RISKY_PATTERNS = {
    'code': [
        (r'eval\s*\(', 'eval() detected - potential code injection risk'),
        (r'exec\s*\(', 'exec() detected - potential code injection risk'),
        (r'subprocess.*shell\s*=\s*True', 'shell=True in subprocess'),
        (r'password\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded password detected'),
        (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded API key'),
        (r'["\']?secret["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded secret'),
        (r'Bearer\s+[A-Za-z0-9_-]{20,}', 'Hardcoded bearer token'),
        (r'SELECT.*\+.*user', 'Potential SQL injection'),
    ],
    'file_operations': [
        (r'rm\s+-rf\s+/', 'Dangerous recursive delete from root'),
        (r'chmod\s+777', 'Overly permissive file permissions'),
    ],
    'deserialization': [
        (r'pickle\.loads?\s*\(', 'pickle - insecure deserialization risk'),
        (r'yaml\.load\s*\([^,)]*\)(?!\s*,\s*Loader)', 'yaml.load without SafeLoader'),
    ],
    'cryptography': [
        (r'hashlib\.md5\s*\(', 'MD5 hash - cryptographically weak'),
        (r'hashlib\.sha1\s*\(', 'SHA1 hash - weak for passwords'),
        (r'random\.(randint|random|choice)', 'random module - use secrets instead'),
    ],
    'command_injection': [
        (r'os\.system\s*\(', 'os.system - prefer subprocess with shell=False'),
        (r'os\.popen\s*\(', 'os.popen - potential command injection'),
    ],
    'path_traversal': [
        (r'\.\.[/\\]\.\.[/\\]', 'Path traversal pattern detected'),
        (r'open\s*\([^)]*\+[^)]*user', 'File open with user input - validate path'),
    ],
    'network': [
        (r'verify\s*=\s*False', 'SSL/TLS verification disabled'),
        (r'ssl\._create_unverified_context', 'Unverified SSL context'),
    ]
}
```

### Adding New Patterns

Edit `security_patterns.py`:

```python
RISKY_PATTERNS = {
    'your_category': [
        (r'your_regex_pattern', 'Warning message to display'),
    ]
}
```

Pattern tuple format: `(regex_pattern, warning_message)`

---

## Creating Custom Hooks

### Hook Interface

All hooks follow this interface:

```python
#!/usr/bin/env python3
import json
import sys

def get_hook_input() -> dict:
    """Read hook input from stdin."""
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        return {}

def output_result(result: dict):
    """Output hook result to stdout."""
    print(json.dumps(result))

def main():
    """Main hook logic."""
    hook_input = get_hook_input()

    # Your logic here
    result = {"decision": "approve"}

    output_result(result)

if __name__ == "__main__":
    main()
```

### Pre-Tool Hook Template

```python
#!/usr/bin/env python3
"""
Custom pre-tool hook: [Description]
"""
import json
import sys

def get_hook_input() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        return {}

def output_result(result: dict):
    print(json.dumps(result))

def main():
    hook_input = get_hook_input()

    tool_name = hook_input.get("tool_name")
    tool_input = hook_input.get("tool_input", {})

    # Your pre-execution logic
    if tool_name == "Task":
        # Modify prompt or input
        modified_input = tool_input.copy()
        modified_input["prompt"] = tool_input.get("prompt", "") + "\n\n[Your injection]"

        output_result({
            "decision": "approve",
            "tool_input": modified_input
        })
    else:
        output_result({"decision": "approve"})

if __name__ == "__main__":
    main()
```

### Post-Tool Hook Template

```python
#!/usr/bin/env python3
"""
Custom post-tool hook: [Description]
"""
import json
import sys

def get_hook_input() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        return {}

def output_result(result: dict):
    print(json.dumps(result))

def main():
    hook_input = get_hook_input()

    tool_name = hook_input.get("tool_name")
    tool_input = hook_input.get("tool_input", {})
    tool_output = hook_input.get("tool_output", {})

    # Your post-execution logic
    if tool_name == "Task":
        # Analyze output, record metrics, etc.
        content = tool_output.get("content", "")

        # Example: Check for success markers
        if "successfully" in content.lower():
            sys.stderr.write("[CUSTOM] Task succeeded\n")

    # Always approve (advisory only)
    output_result({"decision": "approve"})

if __name__ == "__main__":
    main()
```

---

## Hook Lifecycle

### Execution Order

```
User Request
    │
    ▼
┌─────────────────────────────┐
│  Pre-Tool Hooks             │
│  - Load heuristics          │
│  - Score complexity         │
│  - Inject context           │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  Tool Execution             │
│  (Task, Edit, Write, etc.)  │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  Post-Tool Hooks            │
│  - Determine outcome        │
│  - Validate heuristics      │
│  - Security verification    │
│  - Record learnings         │
└─────────────────────────────┘
    │
    ▼
Result to User
```

### Session State

Hooks maintain state across tool executions:

```python
# Location: ~/.claude/hooks/learning-loop/session-state.json
{
    "session_start": "2025-12-11T10:30:00",
    "heuristics_consulted": [42, 43, 44],  # IDs of shown heuristics
    "domains_queried": ["authentication", "security"],
    "task_context": "Fix login bug"
}
```

#### State Management

```python
from pathlib import Path
import json

STATE_FILE = Path.home() / ".claude" / "hooks" / "learning-loop" / "session-state.json"

def load_session_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "session_start": datetime.now().isoformat(),
        "heuristics_consulted": [],
        "domains_queried": [],
        "task_context": None
    }

def save_session_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))
```

### Database Integration

Hooks interact with SQLite for persistence:

```python
import sqlite3
from pathlib import Path

def get_db_connection():
    """Get SQLite connection to building."""
    db_path = EMERGENT_LEARNING_PATH / "memory" / "index.db"
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn
```

**Key Tables:**

- `heuristics`: Domain-specific rules and guidelines
- `learnings`: Failures, successes, observations
- `metrics`: Hook execution metrics
- `trails`: Pheromone trails for hotspot tracking

---

## Examples

### Example 1: Pre-Tool Injection

Input to pre-tool hook:

```json
{
    "tool_name": "Task",
    "tool_input": {
        "description": "Fix authentication bug",
        "prompt": "Debug the JWT token validation in login.py"
    }
}
```

Output from pre-tool hook:

```json
{
    "decision": "approve",
    "tool_input": {
        "description": "Fix authentication bug",
        "prompt": "Debug the JWT token validation in login.py\n\n---\n## Building Knowledge (Auto-Injected)\n\n### Golden Rules (Must Follow)\n- **Never commit credentials or API keys**\n\n### Relevant Heuristics (authentication)\n- [authentication] Use bcrypt for password hashing (95% confidence, 12x validated)\n\n---\n"
    }
}
```

### Example 2: Post-Tool Outcome Detection

Input to post-tool hook:

```json
{
    "tool_name": "Task",
    "tool_input": {
        "description": "Create user model"
    },
    "tool_output": {
        "content": "Successfully created User model with password hashing using bcrypt."
    }
}
```

Hook processing:

```python
outcome, reason = determine_outcome(tool_output)
# Returns: ("success", "Successfully completed action")

# Validate consulted heuristics (from session state)
validate_heuristics([42], "success")
# Increments times_validated for heuristic 42
```

### Example 3: Advisory Security Verification

Input to post-tool hook:

```json
{
    "tool_name": "Edit",
    "tool_input": {
        "file_path": "config.py",
        "old_string": "# Configuration",
        "new_string": "API_KEY = 'sk-1234567890abcdef'"
    },
    "tool_output": {
        "success": true
    }
}
```

Hook processing:

```python
verifier = AdvisoryVerifier()
result = verifier.analyze_edit(
    file_path="config.py",
    old_content="# Configuration",
    new_content="API_KEY = 'sk-1234567890abcdef'"
)

# result = {
#     "has_warnings": True,
#     "warnings": [{
#         "category": "code",
#         "message": "Hardcoded API key detected",
#         "line_preview": "API_KEY = 'sk-1234567890abcdef'"
#     }],
#     "recommendation": "[!] Review flagged items before proceeding"
# }

# Logged to stderr:
# [ADVISORY] code: Hardcoded API key detected
#            Line: API_KEY = 'sk-1234567890abcdef'
```

Output from post-tool hook:

```json
{
    "decision": "approve",
    "advisory": {
        "has_warnings": true,
        "warnings": [
            {
                "category": "code",
                "message": "Hardcoded API key detected",
                "line_preview": "API_KEY = 'sk-1234567890abcdef'"
            }
        ],
        "recommendation": "[!] Review flagged items before proceeding"
    }
}
```

Note: The operation is **approved** despite warnings. Advisory only.

### Example 4: Auto-Recording Failures

Input to post-tool hook:

```json
{
    "tool_name": "Task",
    "tool_input": {
        "description": "Deploy to production",
        "prompt": "Run deployment script"
    },
    "tool_output": {
        "content": "Error: Permission denied accessing production database"
    }
}
```

Hook processing:

```python
outcome, reason = determine_outcome(tool_output)
# Returns: ("failure", "Permission denied")

# Auto-record failure
auto_record_failure(
    tool_input=tool_input,
    tool_output=tool_output,
    outcome_reason=reason,
    domains=["production", "database"]
)

# Creates: auto-failures/failure_20251211_103045.md
# Inserts into learnings table
```

### Example 5: Explicit Learning Extraction

Agent output:

```
Fixed the authentication bug by rotating the JWT secret.

## FINDINGS
[LEARNED:authentication] Always rotate JWT secrets after suspected compromise
[LEARNED:security] Monitor failed login attempts for brute force patterns
```

Hook processing:

```python
extract_and_record_learnings(tool_output, domains=["authentication"])

# Extracts:
# 1. "[LEARNED:authentication] Always rotate JWT secrets after suspected compromise"
#    → Recorded as heuristic (contains "always")
# 2. "[LEARNED:security] Monitor failed login attempts..."
#    → Recorded as heuristic (contains "always" implied by "monitor")
```

### Example 6: Golden Rule Promotion

After many validations:

```python
# Heuristic state:
# - confidence: 0.92
# - times_validated: 15
# - times_violated: 0
# - is_golden: 0

check_golden_rule_promotion(conn)

# Promotes to golden rule:
# - Sets is_golden = 1
# - Logs promotion metric
# - Writes to stderr: "PROMOTED TO GOLDEN RULE: Use bcrypt for password..."
```

---

## Best Practices

### For Hook Development

1. **Always approve**: Hooks are advisory, never blocking
2. **Handle errors gracefully**: Don't fail if DB is unavailable
3. **Write to stderr for visibility**: Use `sys.stderr.write()` for logging
4. **Keep performance in mind**: Hooks run on every tool execution
5. **Use session state sparingly**: Only for cross-tool coordination
6. **Validate input**: Check for missing/malformed hook input

### For Security Patterns

1. **Filter comments**: Use `_is_comment_line()` to avoid false positives
2. **Only scan new lines**: Use `_get_added_lines()` to avoid flagging existing code
3. **Use word boundaries**: Patterns like `\beval\b` prevent matching "medieval"
4. **Test thoroughly**: Add test cases for each new pattern
5. **Provide context**: Include line preview in warnings

### For Learning Loop

1. **Be optimistic**: Treat "unknown" outcomes as success
2. **Avoid false positives**: Filter phrases like "fixed the error"
3. **Promote conservatively**: Require high confidence + many validations
4. **Auto-record failures**: Don't rely on manual reporting
5. **Extract explicit learnings**: Look for `[LEARNED:]` markers

---

## Testing Hooks

### Manual Testing

```bash
# Create test input
echo '{"tool_name": "Task", "tool_input": {"prompt": "test"}}' | \
  python ~/.claude/emergent-learning/hooks/learning-loop/pre_tool_learning.py

# Check output
# Should return: {"decision": "approve", ...}
```

### Unit Testing

```python
import unittest
from post_tool_learning import AdvisoryVerifier, determine_outcome

class TestAdvisory(unittest.TestCase):
    def test_hardcoded_password(self):
        verifier = AdvisoryVerifier()
        result = verifier.analyze_edit(
            file_path="test.py",
            old_content="",
            new_content="password = 'admin123'"
        )
        self.assertTrue(result['has_warnings'])
        self.assertEqual(result['warnings'][0]['category'], 'code')

    def test_outcome_detection(self):
        outcome, reason = determine_outcome({
            "content": "Successfully created the module"
        })
        self.assertEqual(outcome, "success")

if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

Run existing test suites:

```bash
cd ~/.claude/emergent-learning/hooks/learning-loop

python test_advisory.py           # 8 tests - core advisory
python test_comment_filter.py     # 12 tests - comment filtering
python test_enhanced_patterns.py  # 20 tests - secret detection
python test_new_categories.py     # 41 tests - pattern categories

# Total: 81 tests
```

---

## Troubleshooting

### Hook Not Firing

Check `.claude/settings.json` configuration:

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

Verify Python path:

```bash
which python
# Should match the Python in hook command
```

### Database Errors

Check database path:

```python
from elf_paths import get_base_path
from pathlib import Path

base_path = get_base_path(Path("."))
db_path = base_path / "memory" / "index.db"

print(f"DB exists: {db_path.exists()}")
print(f"DB path: {db_path}")
```

### False Positives

Add to false positive patterns in `determine_outcome()`:

```python
false_positive_patterns = [
    r'(?i)your pattern here',
]
```

Or filter comments in `AdvisoryVerifier`:

```python
def _is_comment_line(line: str) -> bool:
    # Add your comment marker
    comment_markers = ['#', '//', '/*', '*', '"""', "'''", 'your_marker']
    return any(stripped.startswith(marker) for marker in comment_markers)
```

---

## See Also

- [Conductor API](./Conductor.md) - Multi-agent orchestration
- [Hook README](../../hooks/learning-loop/README.md) - Implementation details
- [Security Patterns](../../hooks/learning-loop/security_patterns.py) - Pattern definitions
