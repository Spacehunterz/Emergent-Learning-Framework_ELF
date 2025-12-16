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


def ensure_hooks_installed():
    """
    Auto-install ELF hooks on first use.

    Checks for a .hooks-installed marker file. If not present,
    runs the hooks installation script.
    """
    marker = Path(__file__).parent.parent / ".hooks-installed"
    if marker.exists():
        return

    install_script = Path(__file__).parent.parent / "scripts" / "install-hooks.py"
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
