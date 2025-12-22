#!/usr/bin/env python3
"""Test the enhanced secret detection patterns."""

import re
import sys
from pathlib import Path

# Import the RISKY_PATTERNS from post_tool_learning
sys.path.insert(0, str(Path.home() / ".claude" / "emergent-learning" / "hooks" / "learning-loop"))
from post_tool_learning import RISKY_PATTERNS, AdvisoryVerifier

def test_pattern(test_name, code_sample, expected_detections):
    """Test a code sample against the patterns."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Code: {code_sample}")
    print(f"\nExpected: {expected_detections} detection(s)")

    # Test using AdvisoryVerifier
    verifier = AdvisoryVerifier()
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content=code_sample
    )

    detections = len(result['warnings'])
    print(f"Detected: {detections} warning(s)")

    if result['warnings']:
        for i, warning in enumerate(result['warnings'], 1):
            print(f"  {i}. [{warning['category']}] {warning['message']}")
            print(f"     Line: {warning['line_preview']}")

    # Check if it matches expected
    if detections == expected_detections:
        print(f"PASS PASS")
        return True
    else:
        print(f"FAIL FAIL (expected {expected_detections}, got {detections})")
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("ENHANCED SECRET DETECTION PATTERN TESTS")
    print("="*60)

    tests = [
        # Password tests
        ("Password in print statement", 'print("password: admin")', 1),
        ("Password with equals", 'password = "admin123"', 1),
        ("Password with colon", 'password: "secretpass"', 1),
        ("Password in JSON", '{"password": "admin123"}', 1),
        ("Uppercase PASSWORD", 'PASSWORD = "test123"', 1),

        # API key tests
        ("API key assignment", 'api_key = "sk-1234567890"', 1),
        ("API key with dash", 'api-key = "key123"', 1),

        # New secret types
        ("Secret token", 'secret = "mysecret123"', 1),
        ("Auth token", 'token = "abc123xyz"', 1),
        ("Credentials", 'credentials = "user:pass"', 1),
        ("Bearer token", 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9', 1),
        ("Private key", 'PRIVATE_KEY = "..."', 1),

        # SQL injection test
        ("SQL injection", 'SELECT * FROM users WHERE name = " + user_input', 1),

        # Code injection tests
        ("eval() usage", 'eval(user_input)', 1),
        ("exec() usage", 'exec(malicious_code)', 1),

        # File operation tests
        ("Dangerous rm", 'rm -rf /', 1),
        ("chmod 777", 'chmod 777 /tmp/file', 1),

        # False positives (should NOT detect)
        ("Variable named password", 'password_field = forms.CharField()', 0),
        ("Comment about passwords", '# Check if password is valid', 0),
        ("Function name", 'def validate_password():', 0),
    ]

    passed = 0
    failed = 0

    for test_name, code, expected in tests:
        if test_pattern(test_name, code, expected):
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\nPASS ALL TESTS PASSED!")
        return 0
    else:
        print(f"\nFAIL {failed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    exit(main())
