"""
Setup and initialization functions for the Query System.

Contains:
- ensure_hooks_installed: Auto-install ELF hooks on first use
- ensure_full_setup: Check setup status and handle first-time configuration
"""

import sys
import platform
import subprocess
from pathlib import Path


def _hook_command_path_exists(command: str, filename: str) -> bool:
    if not command or filename not in command:
        return False
    candidates = []
    for token in command.split():
        token = token.strip('"').strip("'")
        if token.endswith(filename):
            candidates.append(token)
    if not candidates:
        import re
        match = re.search(r'(["\'])([^"\']+' + re.escape(filename) + r')\1', command)
        if match:
            candidates.append(match.group(2))
    for candidate in candidates:
        try:
            if Path(candidate).exists():
                return True
        except Exception:
            continue
    return False


def _hooks_need_repair(settings_file: Path) -> bool:
    if not settings_file.exists():
        return False
    try:
        import json
        settings = json.loads(settings_file.read_text())
    except Exception:
        return True

    hooks = settings.get("hooks", {})
    pre_entries = hooks.get("PreToolUse", [])
    post_entries = hooks.get("PostToolUse", [])

    pre_found = False
    post_found = False

    for entry in pre_entries:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            if "pre_tool_learning.py" in cmd:
                pre_found = True
                if not _hook_command_path_exists(cmd, "pre_tool_learning.py"):
                    return True

    for entry in post_entries:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            if "post_tool_learning.py" in cmd:
                post_found = True
                if not _hook_command_path_exists(cmd, "post_tool_learning.py"):
                    return True

    return not (pre_found and post_found)


def ensure_hooks_installed():
    """
    Auto-install ELF hooks on first use.

    Checks for a .hooks-installed marker file. If not present,
    runs the hooks installation script.
    """
    repo_root = Path(__file__).resolve().parents[2]
    marker = repo_root / ".hooks-installed"
    settings_file = Path.home() / ".claude" / "settings.json"
    if marker.exists() and not _hooks_need_repair(settings_file):
        return

    install_script = repo_root / "tools" / "scripts" / "install-hooks.py"
    legacy_install = Path(__file__).parent.parent / "scripts" / "install-hooks.py"
    if not install_script.exists() and legacy_install.exists():
        install_script = legacy_install
    if install_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(install_script)],
                capture_output=True,
                timeout=10
            )
        except Exception:
            pass  # Silent fail - hooks are optional


def ensure_full_setup():
    """
    Check setup status and return status code for Claude to handle.
    Claude will use AskUserQuestion tool to show selection boxes if needed.

    Returns:
        "ok" - Already set up, proceed normally
        "fresh_install" - New user, auto-installed successfully
        "needs_user_choice" - Has existing config, Claude should ask user
        "install_failed" - Something went wrong
    """
    global_claude_md = Path.home() / ".claude" / "CLAUDE.md"
    elf_dir = Path(__file__).parent.parent

    # Detect OS and find appropriate installer
    is_windows = platform.system() == "Windows"

    if is_windows:
        setup_script = elf_dir / "install.ps1"
    else:
        setup_script = elf_dir / "setup" / "install.sh"

    if not setup_script.exists():
        return "ok"

    # Case 1: No CLAUDE.md - new user, auto-install
    if not global_claude_md.exists():
        print("")
        print("=" * 60)
        print("[ELF] Welcome! First-time setup...")
        print("=" * 60)
        print("")
        print("Installing:")
        print("  - CLAUDE.md : Core instructions")
        print("  - /search   : Session history search")
        print("  - /checkin  : Building check-in")
        print("  - /swarm    : Multi-agent coordination")
        print("  - Hooks     : Auto-query & enforcement")
        print("")
        try:
            if is_windows:
                # Windows: use PowerShell with CoreOnly to avoid dashboard during auto-setup
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(setup_script), "-CoreOnly"],
                    capture_output=True, text=True, timeout=60
                )
            else:
                # Unix: use bash
                result = subprocess.run(
                    ["bash", str(setup_script), "--mode", "fresh"],
                    capture_output=True, text=True, timeout=30
                )
            print("[ELF] Setup complete!")
            print("")
            return "fresh_install"
        except Exception as e:
            print(f"[ELF] Setup issue: {e}")
            return "install_failed"

    # Case 2: Has CLAUDE.md with ELF already
    try:
        with open(global_claude_md, 'r', encoding='utf-8') as f:
            content = f.read()
        if "Emergent Learning Framework" in content or "query the building" in content.lower():
            return "ok"
    except:
        pass

    # Case 3: Has CLAUDE.md but no ELF - Claude should ask user
    print("")
    print("=" * 60)
    print("[ELF] Existing configuration detected")
    print("=" * 60)
    print("")
    print("You have ~/.claude/CLAUDE.md but it doesn't include ELF.")
    print("Claude will ask how you'd like to proceed.")
    print("")
    print("[ELF_NEEDS_USER_CHOICE]")
    print("")
    return "needs_user_choice"
