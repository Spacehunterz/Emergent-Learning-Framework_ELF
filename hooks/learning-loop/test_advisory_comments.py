#!/usr/bin/env python3
"""Test that AdvisoryVerifier correctly filters out comment lines."""

import sys
sys.path.insert(0, '.')

from post_tool_learning import AdvisoryVerifier

def test_comment_filtering():
    """Test that comments don't trigger warnings but code does."""
    verifier = AdvisoryVerifier()

    # Test 1: Pure comment lines should NOT trigger warnings
    print("Test 1: Pure comment lines")
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content="# eval() is dangerous\n# exec() too\n"
    )
    assert not result['has_warnings'], f"Comments should not trigger warnings, got: {result['warnings']}"
    print("  [OK] Python comments with risky words don't trigger warnings")

    # Test 2: Actual code SHOULD trigger warnings
    print("\nTest 2: Actual risky code")
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content="eval(user_input)\n"
    )
    assert result['has_warnings'], "eval() code should trigger warning"
    assert len(result['warnings']) == 1
    assert 'eval()' in result['warnings'][0]['message']
    print("  [OK] eval() code triggers warning")

    # Test 3: Mixed line (code with comment) SHOULD trigger
    print("\nTest 3: Mixed lines (code + comment)")
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content="x = eval(y)  # This is dangerous\n"
    )
    assert result['has_warnings'], "Mixed line with eval() should trigger warning"
    print("  [OK] Mixed line triggers warning for the code part")

    # Test 4: JS comments
    print("\nTest 4: JS/C-style comments")
    result = verifier.analyze_edit(
        file_path="test.js",
        old_content="",
        new_content="// eval() is used here\n/* exec() in comment */\n"
    )
    assert not result['has_warnings'], f"JS comments should not trigger warnings, got: {result['warnings']}"
    print("  [OK] JS/C comments don't trigger warnings")

    # Test 5: Actual exec() SHOULD trigger
    print("\nTest 5: exec() code")
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content="exec(code)\n"
    )
    assert result['has_warnings'], "exec() code should trigger warning"
    assert 'exec()' in result['warnings'][0]['message']
    print("  [OK] exec() code triggers warning")

    # Test 6: shell=True pattern
    print("\nTest 6: subprocess shell=True")
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content="subprocess.call(cmd, shell=True)\n"
    )
    assert result['has_warnings'], "shell=True should trigger warning"
    print("  [OK] shell=True triggers warning")

    # Test 7: Comment about shell=True should NOT trigger
    print("\nTest 7: Comment about shell=True")
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content="# Don't use shell=True\n"
    )
    assert not result['has_warnings'], f"Comment should not trigger, got: {result['warnings']}"
    print("  [OK] Comment about shell=True doesn't trigger")

    # Test 8: Docstring
    print("\nTest 8: Docstrings")
    result = verifier.analyze_edit(
        file_path="test.py",
        old_content="",
        new_content='"""This function uses eval() internally"""\n'
    )
    assert not result['has_warnings'], f"Docstring should not trigger, got: {result['warnings']}"
    print("  [OK] Docstrings don't trigger warnings")

    print("\n" + "="*50)
    print("ALL TESTS PASSED!")
    print("="*50)
    return 0

if __name__ == '__main__':
    try:
        exit(test_comment_filtering())
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
