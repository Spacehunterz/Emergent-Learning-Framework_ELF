# Escape Sequence Editing on Windows

## Heuristic
> When editing code with escape sequences (\n, \\, \") via Claude Code tools on Windows, use Python scripts with raw byte operations rather than relying on Edit tool string handling.

## Context
- Windows uses CRLF line endings
- Edit tool can introduce literal newlines into string literals
- Rust byte literals like `b'\n'` become `b'\r\n'` (literal CRLF bytes)
- String escapes like `"\n"` can split across lines

## Pattern
When you see compiler errors like:
- "byte constant must be escaped: `\n`"
- "character literal may only contain one codepoint"
- "unterminated character literal"

The file likely has corrupted escape sequences from previous edits.

## Solution
Use Python with regex to fix:
```python
import re
with open('file.rs', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix literal CRLFs in byte strings
content = re.sub(r"b'\r?\n'", r"b'\\n'", content)

# Fix literal newlines in string joins
content = re.sub(r'\.join\("\r?\n"\)', r'.join("\\n")', content)

with open('file.rs', 'w', encoding='utf-8') as f:
    f.write(content)
```

## Confidence
0.7 (validated once in mcp_bridge.rs, 2025-12-06)

## Domain
rust, windows, editing
