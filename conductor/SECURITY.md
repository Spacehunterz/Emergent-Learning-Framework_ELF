# Security Guidelines for Conductor

This document outlines the security measures implemented in the Conductor system and provides guidelines for maintaining secure code.

## Input Validation

### Overview

All user-provided identifiers (node_id, workflow_id, run_id, agent_id, etc.) are validated before use to prevent:
- Command injection attacks
- Path traversal attacks
- SQL injection (defense in depth)
- Environment variable injection
- File system attacks

### Validation Module

Location: `conductor/validation.py`

This module provides validation functions for all identifier types used in the system.

### Key Validation Functions

#### `validate_identifier(value, name, max_length=100)`

Base validation function that ensures identifiers contain only safe characters:
- Alphanumeric characters (a-z, A-Z, 0-9)
- Underscores (_)
- Hyphens (-)
- Maximum length: 100 characters (configurable)
- Cannot start or end with special characters

**Rejects:**
- Command injection characters: `;`, `|`, `&`, `$`, `` ` ``, `\n`, etc.
- Path traversal: `../`, `..\\`
- File operations: `>`, `<`, `*`, `?`
- Quotes: `'`, `"`
- Whitespace in identifiers

#### Specific Validators

- `validate_node_id(node_id)` - Validates node identifiers
- `validate_workflow_id(workflow_id)` - Validates workflow identifiers
- `validate_run_id(run_id)` - Validates run identifiers
- `validate_agent_id(agent_id)` - Validates agent identifiers
- `validate_agent_type(agent_type)` - Validates agent types (allows spaces)
- `validate_filename_safe(filename)` - Validates filenames for filesystem operations

### Where Validation is Applied

#### executor.py

All execution methods validate identifiers before use:

1. **`_execute_single()`** - Validates `node.id` and `agent_type` before:
   - Writing signal files
   - Spawning subprocess
   - Setting environment variables

2. **`_execute_swarm()`** - Validates `node.id`, `agent_type`, and `role` before:
   - Creating ant node IDs
   - Spawning multiple subprocesses

3. **`_execute_parallel()`** - Validates `node.id` and `agent_type` before:
   - Creating parallel node IDs
   - Spawning multiple subprocesses

4. **`_spawn_claude_task()`** - Validates `node_id` and `agent_type` before:
   - Creating temporary files with node_id in filename
   - Passing node_id in subprocess environment variable `CLAUDE_SWARM_NODE`
   - Writing result files

5. **`_write_signal()`** - Validates `node_id` before:
   - Creating signal files with node_id in filename

6. **`HookSignalExecutor.execute()`** - Validates `node.id` before:
   - Writing signal files
   - Creating conductor signal files

## Critical Security Points

### 1. Subprocess Execution

**Risk:** Command injection through unsanitized input

**Protection:**
- All identifiers validated before use
- Subprocess called with argument list (not shell string)
- Environment variables validated before setting

```python
# SECURE: Uses list of arguments, validated node_id
cmd = ["claude", "--print", "--dangerously-skip-permissions", "-p", prompt]
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=self.timeout,
    cwd=str(self.project_root),
    env={**os.environ, "CLAUDE_SWARM_NODE": validated_node_id}  # Validated!
)
```

### 2. File Operations

**Risk:** Path traversal, arbitrary file write/read

**Protection:**
- Filenames constructed with validated identifiers only
- No user input used directly in paths
- Files created within controlled directories

```python
# SECURE: node_id is validated
prompt_file = self.coordination_dir / f"prompt-{validated_node_id}.md"
result_file = self.coordination_dir / f"result-{validated_node_id}.json"
```

### 3. SQL Queries

**Risk:** SQL injection

**Protection:**
- All SQL queries use parameterized statements with `?` placeholders
- No string concatenation in SQL queries
- SQLite's parameter binding handles escaping

```python
# SECURE: Parameterized query
cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
```

**Note:** While conductor.py already uses parameterized queries correctly, identifier validation provides defense in depth.

### 4. Environment Variables

**Risk:** Environment variable injection

**Protection:**
- Only validated identifiers used in environment variables
- No special characters that could break shell parsing

## Testing

### Test Suite

Location: `conductor/tests/test_validation.py`

The test suite includes:
- Valid identifier tests
- Invalid identifier rejection tests
- Command injection attempt blocking
- Path traversal blocking
- Edge case handling
- Error message validation

Run tests with:
```bash
cd ~/.claude\emergent-learning\conductor
python -m pytest tests/test_validation.py -v
```

### Common Attack Patterns Tested

1. **Command chaining:** `node; rm -rf /`, `node && ls`, `node || cat`
2. **Command substitution:** `node$(whoami)`, `node\`cmd\``, `node${VAR}`
3. **Path traversal:** `../../../etc/passwd`, `..\\..\\windows\\`
4. **Special characters:** `node|cmd`, `node&cmd`, `node>file`, `node<file`
5. **Quotes:** `node'cmd'`, `node"cmd"`
6. **Newlines:** `node\nrm`, `node\r\nrm`

## Best Practices

### For Developers

1. **Always validate identifiers** before use, even if they come from trusted sources
2. **Use validation functions** from `validation.py` - don't write custom validation
3. **Validate early** - at the entry point where data enters the system
4. **Never trust user input** - validate everything
5. **Use parameterized queries** for all SQL operations
6. **Pass lists to subprocess** - never construct shell strings
7. **Test with malicious input** - include security tests for new features

### When Adding New Features

If you add new functionality that uses identifiers:

1. Import validation functions:
   ```python
   from validation import validate_node_id, ValidationError
   ```

2. Validate at the entry point:
   ```python
   try:
       validated_id = validate_node_id(user_input)
   except ValidationError as e:
       return error_response(f"Invalid input: {e}")
   ```

3. Use validated values everywhere:
   ```python
   # Use validated_id, not user_input
   filename = f"data-{validated_id}.json"
   ```

4. Add tests for security:
   ```python
   def test_rejects_malicious_input(self):
       with self.assertRaises(ValidationError):
           validate_node_id("node;rm -rf /")
   ```

## Error Handling

### Validation Errors

When validation fails, the system returns a structured error:

```python
{
    "error": "validation_error",
    "error_message": "Invalid node_id: must contain only alphanumeric, underscore, or hyphen",
    "findings": [],
    "files_modified": []
}
```

This ensures:
- Clear error messages for debugging
- No leaking of sensitive information
- Consistent error format across the system

### Logging

Validation errors are logged with `[VALIDATION ERROR]` or `[SECURITY ERROR]` prefix for easy identification in logs.

## Threat Model

### In Scope

- Command injection through identifiers
- Path traversal through filenames
- SQL injection through identifiers (defense in depth)
- Environment variable injection
- Arbitrary file read/write

### Out of Scope

- Prompt injection (handled at LLM level)
- Network attacks (no network code in executor)
- Cryptographic attacks (no crypto operations)
- DOS attacks (handled at system level)

## Updates and Maintenance

### When to Update

1. **New attack patterns discovered** - Add to validation and tests
2. **New identifier types added** - Create specific validators
3. **New file operations** - Ensure validation applied
4. **Subprocess changes** - Review argument handling

### Review Checklist

Before merging code that handles identifiers:

- [ ] All identifiers validated at entry points
- [ ] Validated values used consistently
- [ ] No string concatenation in SQL
- [ ] No shell=True in subprocess calls
- [ ] Security tests added
- [ ] Error handling includes validation errors

## Contact

For security concerns or to report vulnerabilities, create an issue in the ceo-inbox with priority: high.

## References

- OWASP Command Injection: https://owasp.org/www-community/attacks/Command_Injection
- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
- CWE-78 OS Command Injection: https://cwe.mitre.org/data/definitions/78.html
- CWE-89 SQL Injection: https://cwe.mitre.org/data/definitions/89.html
