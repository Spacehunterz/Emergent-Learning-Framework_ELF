#!/usr/bin/env python3
"""
Install ELF hooks into Claude Code's hooks directory.

This script:
1. Copies hook files from the repo to ~/.claude/hooks/learning-loop/
2. Updates Claude Code settings.json to register the hooks
3. Only runs once (creates a marker file)

Run manually: python scripts/install-hooks.py
Or auto-runs on first query to the building.
"""

import json
import shutil
import sys
from pathlib import Path

# Paths
HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
ELF_DIR = CLAUDE_DIR / "emergent-learning"
SOURCE_HOOKS = ELF_DIR / "hooks" / "learning-loop"
TARGET_HOOKS = CLAUDE_DIR / "hooks" / "learning-loop"
SETTINGS_FILE = CLAUDE_DIR / "settings.json"
MARKER_FILE = ELF_DIR / ".hooks-installed"


def install_hooks():
    """Copy hook files to Claude hooks directory (only if not already present)."""
    if not SOURCE_HOOKS.exists():
        print(f"Source hooks not found: {SOURCE_HOOKS}")
        return False

    # Create target directory
    TARGET_HOOKS.mkdir(parents=True, exist_ok=True)

    # Copy hook files - BUT don't overwrite existing files
    files_copied = []
    files_skipped = []
    for src_file in SOURCE_HOOKS.glob("*.py"):
        dst_file = TARGET_HOOKS / src_file.name
        if dst_file.exists():
            # Don't overwrite - user may have customized
            files_skipped.append(src_file.name)
        else:
            shutil.copy2(src_file, dst_file)
            files_copied.append(src_file.name)

    if files_copied:
        print(f"Copied {len(files_copied)} hook files: {', '.join(files_copied)}")
    if files_skipped:
        print(f"Skipped {len(files_skipped)} existing files: {', '.join(files_skipped)}")
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
    pre_hook = {
        "type": "command",
        "command": f'python3 "{TARGET_HOOKS / "pre_tool_learning.py"}"'
    }
    post_hook = {
        "type": "command", 
        "command": f'python3 "{TARGET_HOOKS / "post_tool_learning.py"}"'
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
    
    # We'd need to add hooks, but modifying settings.json programmatically
    # risks breaking other hooks. Just report what's needed.
    if not pre_registered or not post_registered:
        print("\nHooks need to be registered in ~/.claude/settings.json")
        print("Add these to your hooks configuration:")
        if not pre_registered:
            print(f'\nPreToolUse -> Task: python3 "{TARGET_HOOKS / "pre_tool_learning.py"}"')
        if not post_registered:
            print(f'\nPostToolUse -> Task: python3 "{TARGET_HOOKS / "post_tool_learning.py"}"')
    
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
