#!/usr/bin/env python3
"""
Install ELF hooks into Claude Code settings.

This script:
1. Locates hook sources in the current ELF base
2. Updates Claude Code settings.json to register the hooks
3. Only runs once (creates a marker file)

Run manually: python scripts/install-hooks.py
Or auto-runs on first query to the building.
"""

import json
import os
import sys
from pathlib import Path

# Paths
HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"


def _resolve_base_dir() -> Path:
    env_path = os.environ.get("ELF_BASE_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    repo_root = Path(__file__).resolve().parents[2]
    src_dir = repo_root / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))
        try:
            from elf_paths import get_base_path
            return get_base_path(repo_root)
        except ImportError:
            pass

    return repo_root


ELF_DIR = _resolve_base_dir()
SOURCE_HOOKS = ELF_DIR / "hooks" / "learning-loop"
if not SOURCE_HOOKS.exists():
    SOURCE_HOOKS = ELF_DIR / "src" / "hooks" / "learning-loop"
TARGET_HOOKS = SOURCE_HOOKS
MARKER_FILE = ELF_DIR / ".hooks-installed"


def install_hooks():
    """Verify hook sources are available for settings registration."""
    if not SOURCE_HOOKS.exists():
        print(f"Source hooks not found: {SOURCE_HOOKS}")
        return False

    if not TARGET_HOOKS.exists():
        TARGET_HOOKS.mkdir(parents=True, exist_ok=True)
    return True


def update_settings():
    """Update Claude Code settings to register hooks."""
    if not SETTINGS_FILE.exists():
        print("Claude settings.json not found - skipping hook registration")
        return False
    
    try:
        settings = json.loads(SETTINGS_FILE.read_text())
    except json.JSONDecodeError:
        print("Could not parse settings.json")
        return False
    
    # Define the hooks we want to register
    python_cmd = f'"{sys.executable}"' if sys.executable else "python"
    pre_hook = {
        "type": "command",
        "command": f'{python_cmd} "{TARGET_HOOKS / "pre_tool_learning.py"}"'
    }
    post_hook = {
        "type": "command",
        "command": f'{python_cmd} "{TARGET_HOOKS / "post_tool_learning.py"}"'
    }
    
    # Ensure hooks structure exists
    if "hooks" not in settings:
        settings["hooks"] = {}
    
    # Check if our hooks are already registered
    hooks = settings["hooks"]
    
    # PreToolUse for Task
    pre_registered = False
    if "PreToolUse" in hooks:
        for entry in hooks["PreToolUse"]:
            if entry.get("matcher") == "Task":
                # Check if our hook is in the list
                for h in entry.get("hooks", []):
                    if "pre_tool_learning.py" in h.get("command", ""):
                        pre_registered = True
                        break
    
    # PostToolUse for Task  
    post_registered = False
    if "PostToolUse" in hooks:
        for entry in hooks["PostToolUse"]:
            if entry.get("matcher") == "Task":
                for h in entry.get("hooks", []):
                    if "post_tool_learning.py" in h.get("command", ""):
                        post_registered = True
                        break
    
    if pre_registered and post_registered:
        print("Hooks already registered in settings.json")
        return True
    
    if not pre_registered or not post_registered:
        if "PreToolUse" not in hooks:
            hooks["PreToolUse"] = []
        if "PostToolUse" not in hooks:
            hooks["PostToolUse"] = []

        hooks["PreToolUse"] = [
            entry for entry in hooks["PreToolUse"]
            if "pre_tool_learning.py" not in str(entry)
        ]
        hooks["PostToolUse"] = [
            entry for entry in hooks["PostToolUse"]
            if "post_tool_learning.py" not in str(entry)
        ]

        hooks["PreToolUse"].append({"matcher": "Task", "hooks": [pre_hook]})
        hooks["PostToolUse"].append({"matcher": "Task", "hooks": [post_hook]})

        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
        print("Hooks registered in settings.json")
    
    return True


def main():
    """Main installation routine."""
    # Check if already installed
    if MARKER_FILE.exists():
        # Already installed, just verify files exist
        if (TARGET_HOOKS / "post_tool_learning.py").exists():
            return 0
        # Files missing, reinstall
    
    print("Installing ELF hooks...")
    
    if not install_hooks():
        return 1
    
    update_settings()
    
    # Create marker
    MARKER_FILE.write_text(f"Hooks installed")
    print("\nHooks installed successfully!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
