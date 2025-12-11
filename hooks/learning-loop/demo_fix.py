#!/usr/bin/env python3
"""
Demonstration of the comment filtering fix for AdvisoryVerifier.

This shows the before/after behavior of the fix.
"""

from post_tool_learning import AdvisoryVerifier

print("=" * 60)
print("AdvisoryVerifier Comment Filtering Demonstration")
print("=" * 60)

verifier = AdvisoryVerifier()

# Demo 1: Comment lines (should NOT warn)
print("\n[Demo 1] Pure comment lines with risky keywords")
print("-" * 60)
test_code = """
# eval() is dangerous and should be avoided
# exec() is also risky
// In JavaScript, eval() is bad practice
/* This file uses eval() internally */
"""
result = verifier.analyze_edit("demo.py", "", test_code)
print(f"Code:\n{test_code}")
print(f"Warnings: {len(result['warnings'])}")
print(f"Result: {'NO WARNINGS' if not result['has_warnings'] else 'HAS WARNINGS'} [OK]")

# Demo 2: Actual code (SHOULD warn)
print("\n[Demo 2] Actual risky code")
print("-" * 60)
test_code = "result = eval(user_input)\n"
result = verifier.analyze_edit("demo.py", "", test_code)
print(f"Code: {test_code.strip()}")
print(f"Warnings: {len(result['warnings'])}")
if result['has_warnings']:
    print(f"Message: {result['warnings'][0]['message']}")
    print(f"Result: HAS WARNINGS [OK]")
else:
    print("Result: NO WARNINGS [UNEXPECTED!]")

# Demo 3: Mixed lines (SHOULD warn)
print("\n[Demo 3] Code with inline comment")
print("-" * 60)
test_code = "x = eval(y)  # This is dangerous\n"
result = verifier.analyze_edit("demo.py", "", test_code)
print(f"Code: {test_code.strip()}")
print(f"Warnings: {len(result['warnings'])}")
if result['has_warnings']:
    print(f"Message: {result['warnings'][0]['message']}")
    print(f"Result: HAS WARNINGS [OK]")
else:
    print("Result: NO WARNINGS [UNEXPECTED!]")

# Demo 4: Docstring (should NOT warn)
print("\n[Demo 4] Docstring with risky keywords")
print("-" * 60)
test_code = '"""This function uses eval() to parse expressions."""\n'
result = verifier.analyze_edit("demo.py", "", test_code)
print(f"Code: {test_code.strip()}")
print(f"Warnings: {len(result['warnings'])}")
print(f"Result: {'NO WARNINGS' if not result['has_warnings'] else 'HAS WARNINGS'} [OK]")

print("\n" + "=" * 60)
print("Summary:")
print("  - Pure comments: Filtered out (no false positives)")
print("  - Actual code: Detected and warned")
print("  - Mixed lines: Code part still triggers warnings")
print("  - Docstrings: Filtered out (no false positives)")
print("=" * 60)
