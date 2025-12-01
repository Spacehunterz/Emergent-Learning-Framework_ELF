# Heuristics: claude-code-tools

Generated from failures, successes, and observations in the **claude-code-tools** domain.

---

## H-9: Read immediately before write/edit with consistent path format

**Confidence**: 0.95
**Source**: failure (multiple instances, root cause identified)
**Created**: 2025-11-30
**Updated**: 2025-11-30

Tool safeguards require:
1. A fresh read immediately before write/edit - no interleaved tool calls
2. On Windows, use IDENTICAL path format for both read and write

The internal cache uses exact string matching, so `C:/path` and `C:\path` are treated as different files.

**Pattern**: When you need to write or edit a file on Windows:
1. Choose a path format (prefer backslashes: `C:\Users\...`)
2. Read the file using that exact path
3. Immediately write/edit using the SAME path string
4. Do NOT interleave other tool calls between read and write

**Evidence**:
- `Read(C:/...)` then `Write(C:/...)` → Failed
- `Read(C:\...)` then `Write(C:\...)` → Succeeded

---

