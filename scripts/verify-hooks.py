#!/usr/bin/env python3
"""
Verify that ELF hooks are installed and offer to install missing ones.

Used by: checkin command, setup process

Returns:
    0 - All hooks installed
    1 - Some hooks missing (after user decline to install)
    2 - Installation failed
"""

import sys
from pathlib import Path
import subprocess

def get_required_hooks():
    """List all required hook templates."""
    elf_dir = Path.home() / '.claude/emergent-learning'
    templates_dir = elf_dir / '.hooks-templates'
    
    if not templates_dir.exists():
        return []
    
    hooks = []
    for f in templates_dir.rglob('*'):
        if f.is_file():
            rel_path = f.relative_to(templates_dir)
            hooks.append(rel_path)
    
    return hooks

def hooks_installed(required_hooks):
    """Check if all required hooks are installed."""
    hooks_dir = Path.home() / '.claude/hooks'
    
    for hook_path in required_hooks:
        if not (hooks_dir / hook_path).exists():
            return False
    
    return True

def auto_install_hooks():
    """Auto-install hooks."""
    elf_dir = Path.home() / '.claude/emergent-learning'
    installer = elf_dir / 'scripts/install-hooks.py'
    
    if not installer.exists():
        print(f"Error: Hook installer not found: {installer}", file=sys.stderr)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(installer)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True
        else:
            print(f"Hook installation failed: {result.stderr}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Error installing hooks: {e}", file=sys.stderr)
        return False

def verify_and_install():
    """Main verification and installation logic."""
    required_hooks = get_required_hooks()
    
    if not required_hooks:
        return 0
    
    if hooks_installed(required_hooks):
        return 0
    
    print(f"[ELF] Missing {len(required_hooks)} hook(s)")
    print("Hooks provide auto-syncing of golden rules and other framework features.")
    print("\nInstalling hooks...")
    
    if auto_install_hooks():
        print("[OK] Hooks installed successfully")
        return 0
    else:
        print("[WARN] Hook installation failed", file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(verify_and_install())
