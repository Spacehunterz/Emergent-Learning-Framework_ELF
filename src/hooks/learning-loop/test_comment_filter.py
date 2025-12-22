#!/usr/bin/env python3
"""Test the comment line filtering logic."""

import pytest


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


class TestCommentLineDetection:
    """Tests for is_comment_line function."""

    def test_python_comment_is_filtered(self):
        """Python comment should be filtered."""
        assert is_comment_line("# eval() is dangerous") is True

    def test_js_comment_is_filtered(self):
        """JS comment should be filtered."""
        assert is_comment_line("// This uses exec()") is True

    def test_c_comment_start_is_filtered(self):
        """C comment start should be filtered."""
        assert is_comment_line("/* eval() here */") is True

    def test_c_comment_body_is_filtered(self):
        """C comment body should be filtered."""
        assert is_comment_line("* eval() in comment body") is True

    def test_docstring_is_filtered(self):
        """Docstring should be filtered."""
        assert is_comment_line('"""eval() in docstring"""') is True

    def test_code_is_not_filtered(self):
        """Code should NOT be filtered."""
        assert is_comment_line("eval(user_input)") is False
        assert is_comment_line("exec(code)") is False

    def test_mixed_line_with_trailing_comment_not_filtered(self):
        """Mixed line should NOT be filtered."""
        assert is_comment_line("x = eval(y)  # dangerous") is False
        assert is_comment_line("foo()  // comment") is False

    def test_indented_comment_is_filtered(self):
        """Indented comment should be filtered."""
        assert is_comment_line("    # This is a comment") is True

    def test_empty_line_not_filtered(self):
        """Empty line should not be filtered."""
        assert is_comment_line("") is False

    def test_whitespace_line_not_filtered(self):
        """Whitespace line should not be filtered."""
        assert is_comment_line("   ") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
