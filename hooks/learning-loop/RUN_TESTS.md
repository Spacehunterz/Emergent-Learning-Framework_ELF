# AdvisoryVerifier Test Suite - Quick Reference

## Running All Tests

### Full Test Suite (54 tests)
```bash
cd ~/.claude/emergent-learning/hooks/learning-loop

# Run integration tests (13 tests)
python test_integration_phase4.py

# Run regression tests (41 tests)
python test_advisory.py
python test_comment_filter.py
python test_enhanced_patterns.py
```

### Quick Validation (Integration Only)
```bash
cd ~/.claude/emergent-learning/hooks/learning-loop
python test_integration_phase4.py
```

Expected output:
```
Total Passed: 13
Total Failed: 0
Success Rate: 13/13 (100.0%)

[SUCCESS] ALL INTEGRATION TESTS PASSED
```

---

## Test Suite Descriptions

### 1. test_integration_phase4.py (13 tests)
**Purpose:** End-to-end hook integration verification

**Tests:**
- Hook contract compliance (6 tests)
- Added lines detection (3 tests)
- Comment filtering (3 tests)
- Non-blocking behavior (1 test)
- Metrics logging (1 test)
- Regression prevention (runs all old tests)
- Pattern coverage (1 test)

**Runtime:** ~3 seconds

---

### 2. test_advisory.py (8 tests)
**Purpose:** Core AdvisoryVerifier functionality

**Tests:**
- Risky code detection (eval, exec, passwords)
- Safe code (no false positives)
- Multiple warnings escalation
- Only new lines checked
- Pattern coverage across categories

**Runtime:** <1 second

---

### 3. test_comment_filter.py (12 tests)
**Purpose:** Comment filtering accuracy

**Tests:**
- Python comments (#)
- JavaScript comments (//)
- C-style comments (/* */)
- Docstrings (""")
- Mixed lines (code + comment)
- Edge cases (indented, empty, whitespace)

**Runtime:** <1 second

---

### 4. test_enhanced_patterns.py (21 tests)
**Purpose:** Security pattern detection coverage

**Tests:**
- Password detection (5 patterns)
- API key detection (2 patterns)
- Secret/token detection (4 patterns)
- Code injection (2 patterns)
- File operations (2 patterns)
- False positive prevention (3 cases)

**Runtime:** <1 second

---

## Interpreting Results

### Success
```
[PASS] Test N: Description
...
Total Passed: N
Total Failed: 0
Success Rate: N/N (100.0%)
```

### Failure
```
[FAIL] Test N: Description
AssertionError: ...
```

If any test fails:
1. Read the error message
2. Check the test case details
3. Verify hook implementation
4. Re-run after fixes

---

## Test Coverage Summary

| Category | Tests | Coverage |
|----------|-------|----------|
| Hook Contract | 6 | Edit/Write tools, malformed input |
| Added Lines Detection | 3 | Diff accuracy, existing code |
| Comment Filtering | 15 | 5+ comment styles, edge cases |
| Non-Blocking | 1 | ALWAYS approve guarantee |
| Metrics Logging | 1 | Database integration |
| Pattern Detection | 28 | 5 categories, 12+ patterns |

**Total:** 54 tests

---

## Continuous Integration

To add to CI/CD pipeline:
```bash
#!/bin/bash
cd ~/.claude/emergent-learning/hooks/learning-loop

# Run all tests
python test_integration_phase4.py || exit 1
python test_advisory.py || exit 1
python test_comment_filter.py || exit 1
python test_enhanced_patterns.py || exit 1

echo "All tests passed!"
```

---

## Troubleshooting

### "No such table: metrics"
Database not initialized. Run:
```bash
cd ~/.claude/emergent-learning
python -c "from conductor.database import initialize_database; initialize_database()"
```

### "Module not found: post_tool_learning"
Wrong directory. Ensure you're in:
```bash
cd ~/.claude/emergent-learning/hooks/learning-loop
```

### Tests hang or timeout
Check for:
- Database locks (close other connections)
- Infinite loops in code
- Network issues (should not affect these tests)

---

## Adding New Tests

Template for new integration test:
```python
class TestNewFeature:
    """Test description."""

    @staticmethod
    def test_new_functionality():
        """Test specific behavior."""
        verifier = AdvisoryVerifier()

        result = verifier.analyze_edit(
            file_path="test.py",
            old_content="old code",
            new_content="new code"
        )

        assert result['has_warnings'] == expected_value, "Reason"

        print("[PASS] Test N: Description")
        return True
```

Add to `run_all_tests()` in test_integration_phase4.py

---

## Test Files Location

All test files are in:
```
~/.claude\emergent-learning\hooks\learning-loop\
├── test_integration_phase4.py  (NEW - Phase 4)
├── test_advisory.py
├── test_comment_filter.py
├── test_enhanced_patterns.py
└── RUN_TESTS.md (this file)
```

---

## Related Documentation

- **Test Report:** PHASE4_INTEGRATION_TEST_REPORT.md
- **Hook Implementation:** post_tool_learning.py
- **Security Patterns:** security_patterns.py

---

**Last Updated:** 2025-12-11
**Test Suite Version:** Phase 4 (Integration + Regression)
**Total Test Coverage:** 54 tests
