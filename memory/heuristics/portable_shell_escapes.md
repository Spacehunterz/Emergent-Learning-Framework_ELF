# Heuristic: Use POSIX-Compatible Escapes in Shell Scripts

## Domain
Shell Scripts, Cross-Platform

## Pattern
Escape sequences like `\x1b`, `\000-\010` work differently across platforms (Linux, macOS, Windows/MSYS).

## Anti-pattern
```bash
# Breaks on some platforms
tr -d '\000-\010\013-\037\177'
sed 's/\x1b\[[0-9;]*m//g'
```

## Solution
Use POSIX character classes instead:
```bash
# Works everywhere
tr -cd '[:print:][:space:]'
tr -d '[:cntrl:]'
```

## Confidence
0.9

## Source
2025-12-04 - sanitize_input() broke on Windows/MSYS due to non-portable escapes
