# Claude Code Windows Tool Guide

**Version:** 1.0  
**Target Environment:** Windows 10/11 with Git Bash (MSYS2)  
**Last Updated:** 2025-12-02

---

## Quick Reference: Tool Selection

| Operation | Use This | Path Format | Notes |
|-----------|----------|-------------|-------|
| **Read file** | `Bash: cat` | Any (`~`, `/c/`, `C:/`) | Most reliable |
| **Read file** | `Read` tool | `C:/Users/...` only | No tilde/MSYS2 |
| **Write file (CRLF)** | `Write` tool | `C:/Users/...` only | Windows line endings |
| **Write file (LF)** | `Bash: echo/printf` | Any | Unix line endings |
| **Edit file** | `Edit` tool | `C:/Users/...` only | No tilde/MSYS2 |
| **Search contents** | `Bash: grep` | Any | Most reliable |
| **Search contents** | `Grep` tool | `C:/Users/...` only | No tilde/MSYS2 |
| **Find files** | `Bash: find/ls` | Any | Glob tool is broken |
| **Run commands** | `Bash` | N/A | Always works |

---

## Golden Rules for Windows

### 1. Bash Tool is Your Friend
When in doubt, use Bash. It handles ALL path formats.

### 2. Python Tools Need `C:/` Paths
Never use `~` or `/c/` with Read, Write, Edit, Grep, Glob.
```
✅ ~/Desktop/file.txt
❌ ~/Desktop/file.txt
❌ ~/Desktop/file.txt
```

### 3. Get Absolute Path First
```bash
pwd -W  # Returns ~/Desktop format
```

### 4. Quote Paths with Spaces
```bash
cat "C:/Users/Name/My Documents/file.txt"
```

### 5. Symlinks Don't Work
`ln -s` creates COPIES. Use hard links or enable Developer Mode.

### 6. chmod is Theater
Windows ignores Unix permissions. Just run: `bash script.sh`

### 7. Case Matters in Globs
Filesystem: case-insensitive. Bash globs: case-sensitive.
Use `find -iname` for case-insensitive search.

### 8. Line Endings Are Split
- Bash → LF (`\n`)
- Write tool → CRLF (`\r\n`)

### 9. Background PIDs Unreliable
Use `BashOutput` tool, not `$!`

### 10. Hook System is Broken
Install Git hooks manually via Bash.

---

## Path Format Matrix

| Format | Example | Bash | Read/Write/Edit/Grep | Glob |
|--------|---------|------|---------------------|------|
| Tilde | `~/file.txt` | ✅ | ❌ | ❌ |
| MSYS2 | `/c/Users/Name/file.txt` | ✅ | ❌ | ❌ |
| Windows Forward | `C:/Users/Name/file.txt` | ✅ | ✅ | ⚠️ |
| Windows Back | `C:\Users\Name\file.txt` | ⚠️ | ❌ | ❌ |

---

## Command Availability

### ✅ Available
```
ls, cat, grep, sed, awk, find, head, tail, wc
cp, mv, rm, mkdir, touch, tar, curl, ssh, git
```

### ❌ Missing (Install or Use Alternatives)
| Missing | Alternative |
|---------|-------------|
| `wget` | `curl -O <url>` |
| `jq` | `npm i -g jq` or Python |
| `make` | `choco install make` |

### ❌ Broken
| Command | Why | Workaround |
|---------|-----|------------|
| `ln -s` | Needs admin/Developer Mode | Use copies or hard links |
| `chmod` | Windows ignores Unix perms | Run with interpreter |
| `$!` | PID unreliable in MSYS2 | Use BashOutput tool |

---

## Environment Setup

Add to `~/.bashrc`:
```bash
# Windows-friendly paths
export DESKTOP="C:/Users/$(whoami)/Desktop"

# Fix slow search
export USE_BUILTIN_RIPGREP=0

# Git config
git config --global core.autocrlf true
git config --global core.filemode false

# Useful alias
alias wpwd='pwd -W'
```

---

## Known Issues

| Issue | Workaround |
|-------|------------|
| Slow Grep | `export USE_BUILTIN_RIPGREP=0` + install ripgrep |
| Glob path param broken | Use `Bash: find` instead |
| Tilde not expanding | Use `pwd -W` to get C:/ path |
| ALT+V is paste | Don't use CTRL+V |
| Hook system broken | Install hooks manually |

---

## Decision Tree

```
Need to work with files?
├── Have C:/ path? → Python tools OK
├── Have ~/path? → Use Bash
└── Have /c/ path? → Use Bash

Need to search?
├── File contents? → Bash: grep (most reliable)
└── File names? → Bash: find (Glob is broken)

Need to run commands?
└── Always use Bash tool
```

---

## Sources
- GitHub Issues: #9883, #3461, #4507, #12299
- Community: claude-code-windows-setup
- Swarm investigation: 2025-12-02
