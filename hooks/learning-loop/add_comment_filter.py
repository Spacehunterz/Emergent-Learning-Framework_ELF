#!/usr/bin/env python3
"""Script to add comment filtering to AdvisoryVerifier."""

def main():
    # Read the original file
    with open('post_tool_learning.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The new _is_comment_line method to add
    is_comment_method = '''    def _is_comment_line(self, line: str) -> bool:
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
        comment_markers = ['#', '//', '/*', '*', '\\"\\"\\"', "\\'\\'\\'"]
        return any(stripped.startswith(marker) for marker in comment_markers)

'''

    # Find the location to insert (before _get_added_lines method)
    search_str = '    def _get_added_lines(self, old: str, new: str) -> List[str]:'
    insert_pos = content.find(search_str)

    if insert_pos == -1:
        print("ERROR: Could not find _get_added_lines method!")
        return 1

    # Insert the new method
    content = content[:insert_pos] + is_comment_method + '\n' + content[insert_pos:]

    # Now update the _get_added_lines method to use the new helper
    old_implementation = '''    def _get_added_lines(self, old: str, new: str) -> List[str]:
        """Get lines that were added (simple diff)."""
        old_lines = set(old.split('\\n')) if old else set()
        new_lines = new.split('\\n') if new else []
        return [line for line in new_lines if line not in old_lines]'''

    new_implementation = '''    def _get_added_lines(self, old: str, new: str) -> List[str]:
        """Get lines that were added (simple diff), excluding pure comment lines."""
        old_lines = set(old.split('\\n')) if old else set()
        new_lines = new.split('\\n') if new else []
        added_lines = [line for line in new_lines if line not in old_lines]

        # Filter out pure comment lines to avoid false positives
        return [line for line in added_lines if not self._is_comment_line(line)]'''

    if old_implementation in content:
        content = content.replace(old_implementation, new_implementation)
        print("✓ Updated _get_added_lines method")
    else:
        print("WARNING: Could not find exact _get_added_lines implementation to replace")
        print("The method was inserted, but you may need to manually update _get_added_lines")

    # Write the modified content
    with open('post_tool_learning.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Added _is_comment_line method")
    print("\nFile successfully modified!")
    return 0

if __name__ == '__main__':
    exit(main())
