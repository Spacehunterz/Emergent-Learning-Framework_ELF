#!/usr/bin/env python3
"""Add comment line filtering to AdvisoryVerifier._get_added_lines method."""

import re

with open('post_tool_learning.py', 'r') as f:
    content = f.read()

# Step 1: Add the _is_comment_line method before _get_added_lines
new_method_code = """    def _is_comment_line(self, line: str) -> bool:
        \"\"\"Check if a line is entirely a comment (not code with comment).

        Returns True for:
        - Python comments: starts with #
        - JS/C/Go single-line comments: starts with //
        - C-style multi-line comment start: starts with /*
        - Multi-line comment bodies: starts with *
        - Docstrings: starts with triple quotes

        Returns False for:
        - Mixed lines like: x = eval(y)  # comment
        - Code before comment: foo()  // comment
        \"\"\"
        stripped = line.strip()
        if not stripped:
            return False

        # Check for pure comment lines (line starts with comment marker)
        triple_quote = chr(34) * 3
        single_triple = chr(39) * 3
        comment_markers = ['#', '//', '/*', '*', triple_quote, single_triple]
        return any(stripped.startswith(marker) for marker in comment_markers)

"""

# Find where to insert (before _get_added_lines)
pattern = r'(\n    def _get_added_lines\(self, old: str, new: str\) -> List\[str\]:)'
match = re.search(pattern, content)
if not match:
    print("ERROR: Could not find _get_added_lines method")
    exit(1)

# Insert the new method
content = content[:match.start()] + '\n' + new_method_code + content[match.start()+1:]

# Step 2: Update _get_added_lines to filter comments
old_return = 'return [line for line in new_lines if line not in old_lines]'
new_return = '''added_lines = [line for line in new_lines if line not in old_lines]

        # Filter out pure comment lines to avoid false positives
        return [line for line in added_lines if not self._is_comment_line(line)]'''

content = content.replace(old_return, new_return, 1)  # Only replace first occurrence in _get_added_lines

# Also update the docstring
old_docstring = '"""Get lines that were added (simple diff)."""'
new_docstring = '"""Get lines that were added (simple diff), excluding pure comment lines."""'
# Find it within the _get_added_lines method context
content = re.sub(
    r'(def _get_added_lines\(self, old: str, new: str\) -> List\[str\]:\n        )"""Get lines that were added \(simple diff\)\."""',
    r'\1"""Get lines that were added (simple diff), excluding pure comment lines."""',
    content
)

# Write back
with open('post_tool_learning.py', 'w') as f:
    f.write(content)

print("✓ Successfully patched AdvisoryVerifier")
print("✓ Added _is_comment_line() method")
print("✓ Updated _get_added_lines() to filter comment lines")
