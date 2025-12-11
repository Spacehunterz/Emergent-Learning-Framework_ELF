#!/usr/bin/env python3
"""Test the comment line filtering logic."""


def is_comment_line(line: str) -> bool:
    """Check if a line is entirely a comment (not code with comment).

    Returns True for:
    - Python comments: starts with #
    - JS/C/Go single-line comments: starts with //
    - C-style multi-line comment start: starts with /*
    - Multi-line comment bodies: starts with *
    - Docstrings: starts with triple quotes

    Returns False for:
    - Mixed lines like: x = eval(y)  # comment
    - Code before comment: foo()  // comment
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Check for pure comment lines (line starts with comment marker)
    comment_markers = ['#', '//', '/*', '*', '"""', "'''"]
    return any(stripped.startswith(marker) for marker in comment_markers)


# Test cases
test_cases = [
    ("# eval() is dangerous", True, "Python comment should be filtered"),
    ("// This uses exec()", True, "JS comment should be filtered"),
    ("/* eval() here */", True, "C comment start should be filtered"),
    ("* eval() in comment body", True, "C comment body should be filtered"),
    ('"""eval() in docstring"""', True, "Docstring should be filtered"),
    ("eval(user_input)", False, "Code should NOT be filtered"),
    ("exec(code)", False, "Code should NOT be filtered"),
    ("x = eval(y)  # dangerous", False, "Mixed line should NOT be filtered"),
    ("foo()  // comment", False, "Mixed line should NOT be filtered"),
    ("    # This is a comment", True, "Indented comment should be filtered"),
    ("", False, "Empty line should not be filtered"),
    ("   ", False, "Whitespace line should not be filtered"),
]

print("Testing comment line detection:\n")
all_passed = True

for line, expected, description in test_cases:
    result = is_comment_line(line)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_passed = False
    print(f"{status}: {description}")
    print(f"  Line: '{line}'")
    print(f"  Expected: {expected}, Got: {result}\n")

if all_passed:
    print("All tests passed!")
else:
    print("Some tests failed!")
    exit(1)
