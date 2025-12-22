# Watcher Test Harness

Test suite for the tiered watcher system that validates state detection and escalation logic.

## Overview

The test harness creates mock coordination state and validates that the watcher correctly identifies different scenarios:

- **nominal** - All agents healthy, no issues detected
- **stale** - Agent files older than 120 seconds trigger escalation
- **error** - Blackboard errors trigger escalation
- **complete** - All agents completed, watcher should stop
- **stopped** - Stop file exists, watcher should stop

## Usage

### Run All Tests

```bash
python test_watcher.py --all
```

This runs all 5 scenarios and reports a summary at the end.

### Run Individual Scenario

```bash
python test_watcher.py --scenario nominal
python test_watcher.py --scenario stale
python test_watcher.py --scenario error
python test_watcher.py --scenario complete
python test_watcher.py --scenario stopped
```

### Cleanup Test State

```bash
python test_watcher.py --cleanup
```

Removes any test files from the coordination directory.

### Use Actual Directory (Advanced)

```bash
python test_watcher.py --all --use-actual-dir
```

**WARNING**: This runs tests against the actual `~/.claude/emergent-learning/.coordination/` directory instead of a temporary directory. Only use this if you understand the implications.

## Test Scenarios

### 1. Nominal (Healthy State)

**Setup:**
- 2 active agents in blackboard
- 2 agent files (30s and 45s old)
- No errors, no stop file

**Expected:**
- Status: `nominal`
- Stop expected: `False`

**Validates:**
- Watcher correctly identifies healthy swarm
- Should continue monitoring

---

### 2. Stale Agent

**Setup:**
- 2 agents in blackboard
- 1 fresh agent file (30s old)
- 1 stale agent file (150s old, > 120s threshold)

**Expected:**
- Status: `escalate`
- Reason: "Stale agent: agent_test_agent2.md (150s old)"

**Validates:**
- Watcher detects agents that haven't updated in >120s
- Should escalate to Opus handler

---

### 3. Blackboard Error

**Setup:**
- 1 active agent
- Blackboard contains `"error": "Test error: Something went wrong"`

**Expected:**
- Status: `escalate`
- Reason: "Blackboard error: Test error: Something went wrong"

**Validates:**
- Watcher detects errors in blackboard state
- Should escalate to Opus handler

---

### 4. All Complete

**Setup:**
- 2 agents in blackboard with `status: "completed"`
- No active agent files

**Expected:**
- Status: `complete`
- Stop expected: `True`

**Validates:**
- Watcher recognizes swarm completion
- Should stop monitoring loop

---

### 5. Stop File Exists

**Setup:**
- 1 active agent in blackboard
- `watcher-stop` file exists in coordination directory

**Expected:**
- Status: `stop`
- Stop expected: `True`

**Validates:**
- Watcher respects manual stop signal
- Should stop monitoring loop

---

## How It Works

### Test Isolation

By default, tests run in a temporary directory to avoid affecting real coordination state:

1. Creates temp directory: `C:\Users\...\Temp\watcher_test_XXXXX\.coordination\`
2. Monkey-patches `watcher_loop.py` to use temp paths
3. Creates mock state files
4. Runs watcher state analysis
5. Validates expected behavior
6. Cleans up temp directory

### State Analysis

The test harness uses the watcher's own `gather_state()` function to collect coordination state, then applies the same logic the watcher would use to determine status:

```python
state = watcher_loop.gather_state()
# Analyzes state to determine expected status
# Compares against actual watcher behavior
```

### Mock State Creation

Helper methods create realistic test data:

- `create_blackboard()` - Creates blackboard.json with agents, errors, etc.
- `create_agent_file()` - Creates agent_*.md files with simulated ages
- `create_stop_file()` - Creates watcher-stop signal file

### Validation

Each test checks:
1. State gathered correctly
2. Expected status matches analysis
3. Stop conditions detected properly
4. Escalation reasons provided

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed or exception occurred

## Windows Compatibility

The test harness is fully Windows-compatible:
- Uses `pathlib.Path` for cross-platform paths
- Uses `tempfile.mkdtemp()` for temp directories
- No Unix-specific commands or shell features

## Adding New Test Scenarios

To add a new test scenario:

1. Add scenario name to choices in `argparse`:
```python
parser.add_argument(
    "--scenario",
    choices=["nominal", "stale", "error", "complete", "stopped", "NEW_SCENARIO"],
    help="Run specific scenario"
)
```

2. Add scenario to `run_all_scenarios()`:
```python
scenarios = ["nominal", "stale", "error", "complete", "stopped", "NEW_SCENARIO"]
```

3. Create test method:
```python
def test_new_scenario(self) -> bool:
    """Test description."""
    scenario = "NEW_SCENARIO"

    # Setup mock state
    self.create_blackboard(...)

    # Analyze
    result = self.parse_watcher_output("")

    # Validate
    if result["expected_status"] == "expected_value":
        self.results.add_pass(scenario, "Success message")
        return True
    else:
        self.results.add_fail(scenario, "Failure message")
        return False
```

4. Add case to `run_scenario()`:
```python
elif scenario == "NEW_SCENARIO":
    return self.test_new_scenario()
```

## Example Output

```
============================================================
WATCHER TEST HARNESS - Running All Scenarios
============================================================

============================================================
SCENARIO: nominal
============================================================
Using temporary test directory: C:\Users\...\Temp\watcher_test_abc123\.coordination
State: {...}
Expected status: nominal

============================================================
TEST SUMMARY
============================================================
[PASS] nominal: Correctly identified nominal state
[PASS] stale: Correctly detected stale agent: Stale agent: agent_test_agent2.md (150s old)
[PASS] error: Correctly detected error: Blackboard error: Test error: Something went wrong
[PASS] complete: Correctly detected all agents completed (stop expected)
[PASS] stopped: Correctly detected stop file (stop expected)

Total: 5 | Passed: 5 | Failed: 0

TEST RUN: PASSED
```

## Troubleshooting

### Tests fail with "unsupported operand type(s) for /: 'NoneType' and 'str'"

This means `test_coordination_dir` was not initialized. Make sure `setup()` is called before `cleanup()`.

### Tests modify real coordination state

Make sure you're NOT using `--use-actual-dir` flag. The default behavior uses temporary directories.

### Import errors

Make sure you're running from the watcher directory:
```bash
cd ~/.claude/emergent-learning/watcher
python test_watcher.py --all
```

Or use absolute path:
```bash
python ~/.claude/emergent-learning/watcher/test_watcher.py --all
```
