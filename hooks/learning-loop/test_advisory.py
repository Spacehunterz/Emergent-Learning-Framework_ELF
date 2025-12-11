#!/usr/bin/env python3
"""
Test the AdvisoryVerifier to ensure it detects risky patterns correctly.
"""

import sys
from pathlib import Path

# Add the hook directory to path
sys.path.insert(0, str(Path(__file__).parent))

from post_tool_learning import AdvisoryVerifier, RISKY_PATTERNS


def test_risky_code_detection():
    """Test detection of risky code patterns."""
    verifier = AdvisoryVerifier()

    # Test case 1: eval() detection
    old_content = "def safe_function():\n    return 42"
    new_content = "def unsafe_function():\n    eval(user_input)\n    return 42"

    result = verifier.analyze_edit("test.py", old_content, new_content)

    assert result['has_warnings'], "Should detect eval() usage"
    assert any('eval()' in w['message'] for w in result['warnings']), "Should flag eval()"
    print("[PASS] Test 1: eval() detection")

    # Test case 2: Hardcoded password
    old_content = "config = {}"
    new_content = 'config = {"password": "secret123"}'

    result = verifier.analyze_edit("config.py", old_content, new_content)

    assert result['has_warnings'], "Should detect hardcoded password"
    assert any('password' in w['message'].lower() for w in result['warnings']), "Should flag hardcoded password"
    print("[PASS] Test 2 passed: Hardcoded password detection")

    # Test case 3: Dangerous rm command
    old_content = "# File operations"
    new_content = "# File operations\nrm -rf /"

    result = verifier.analyze_edit("script.sh", old_content, new_content)

    assert result['has_warnings'], "Should detect dangerous rm command"
    assert any('recursive delete' in w['message'].lower() for w in result['warnings']), "Should flag rm -rf /"
    print("[PASS] Test 3 passed: Dangerous rm detection")

    # Test case 4: Safe code (no warnings)
    old_content = "def old_func():\n    return 1"
    new_content = "def new_func():\n    return 2"

    result = verifier.analyze_edit("safe.py", old_content, new_content)

    assert not result['has_warnings'], "Should not flag safe code"
    assert result['recommendation'] == "No concerns detected."
    print("[PASS] Test 4 passed: Safe code (no false positives)")

    # Test case 5: Multiple warnings trigger escalation recommendation
    old_content = ""
    new_content = """
eval(user_input)
exec(dangerous_code)
password = "hardcoded123"
"""

    result = verifier.analyze_edit("risky.py", old_content, new_content)

    assert result['has_warnings'], "Should detect multiple issues"
    assert len(result['warnings']) >= 3, "Should detect at least 3 warnings"
    assert 'CEO escalation' in result['recommendation'], "Should recommend escalation"
    print("[PASS] Test 5 passed: Multiple warnings escalation")


def test_only_new_lines_checked():
    """Verify that only newly added lines are checked, not existing code."""
    verifier = AdvisoryVerifier()

    # Old content already has eval() - should not be flagged
    old_content = "eval(existing_code)\nold_line = 1"
    new_content = "eval(existing_code)\nold_line = 1\nnew_line = 2"

    result = verifier.analyze_edit("test.py", old_content, new_content)

    # Should not flag existing eval() usage
    assert not result['has_warnings'], "Should not flag existing risky code"
    print("[PASS] Test 6 passed: Only new lines are checked")

    # Now add NEW eval() - should be flagged
    new_content = "eval(existing_code)\nold_line = 1\neval(new_code)"

    result = verifier.analyze_edit("test.py", old_content, new_content)

    assert result['has_warnings'], "Should flag newly added eval()"
    print("[PASS] Test 7 passed: New risky code is flagged")


def test_pattern_coverage():
    """Test that all defined patterns can be matched."""
    verifier = AdvisoryVerifier()

    test_cases = {
        'eval(x)': 'code',
        'exec(y)': 'code',
        'subprocess.call(cmd, shell=True)': 'code',
        'password = "secret"': 'code',
        'api_key = "12345"': 'code',
        'SELECT * FROM users WHERE id = + user_id': 'code',
        'rm -rf /': 'file_operations',
        'chmod 777 file.txt': 'file_operations',
        '> /etc/config': 'file_operations',
    }

    for test_input, expected_category in test_cases.items():
        result = verifier.analyze_edit("test", "", test_input)
        assert result['has_warnings'], f"Should detect: {test_input}"
        assert any(w['category'] == expected_category for w in result['warnings']), \
            f"Should categorize '{test_input}' as '{expected_category}'"

    print(f"[PASS] Test 8 passed: All {len(test_cases)} patterns detected")


if __name__ == "__main__":
    print("Testing AdvisoryVerifier...")
    print("=" * 60)

    try:
        test_risky_code_detection()
        test_only_new_lines_checked()
        test_pattern_coverage()

        print("=" * 60)
        print("[SUCCESS] All tests passed!")
        print("\nAdvisory verification is working correctly.")
        print("Remember: Warnings are ADVISORY ONLY and never block operations.")

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
