# Heuristics: File Write Safety

Generated from conflicts during VRAM Manager + RAG Pipeline development (2025-11-30).

---

## H-10: Avoid editing files with active hooks or background processes

> When multiple processes or hooks modify the same file, interleave reads and edits to detect stale state before committing changes.

**Explanation:** During development, `tts_provider.py` was being edited by Claude Code while voice hooks also modified it. Naive sequential edits led to stale state - edits based on a 1-minute-old read would overwrite concurrent modifications. Solution: Always re-read before critical edits, and consider file-level locks or coordination markers for multi-writer scenarios.

**Source**: Session notes - file write conflicts while integrating VRAMClient into tts_provider.py

**Confidence**: 0.85

**Validations**: 1 (single incident, design principle validated)

**Tags**: file-safety, coordination, state-management, hooks

---

## H-11: Use platform-specific file locking (fcntl vs msvcrt) early

> On Windows, use `msvcrt.locking()` for exclusive file access; on Unix, use `fcntl.flock()`. Implement this BEFORE integration, not after conflicts arise.

**Explanation:** File conflicts became apparent only during integration testing. By this point, adding proper locking required retrofitting. Lesson: When designing systems with multiple writers (VRAM manager + voice hooks + agent edits), assume file contention and implement platform-specific locks from the start. Windows requires `msvcrt`, Unix requires `fcntl` - they are NOT interchangeable.

**Source**: Session design decisions - VRAM Manager file-based IPC

**Confidence**: 0.8

**Validations**: 1 (implemented but not battle-tested in production)

**Tags**: cross-platform, file-locking, ipc, windows, unix

---

## H-12: Batch file execution on Windows requires special handling (cmd /c wrapper)

> ComfyUI portable version scripts (.bat files) cannot be directly executed via subprocess on MSYS; wrap with `cmd /c` or use parent shell context.

**Explanation:** Auto-launch for ComfyUI attempted `subprocess.Popen(['start_windows.bat'])` which failed silently on MSYS. Attempted workarounds (shell=True, cwd change) didn't help. Root cause: MSYS shell context differs from cmd.exe context. Portable versions (ComfyUI) ship .bat files assuming cmd.exe; pure Python packages (Ollama) work fine. Workaround: Use `cmd /c start_windows.bat` or rely on user to manually launch portable tools.

**Source**: Session notes - service auto-launch implementation struggle

**Confidence**: 0.75

**Validations**: 1 (observed, workaround documented but not universally tested)

**Tags**: windows, portability, subprocess, batch-files, msys, comfyui

---
