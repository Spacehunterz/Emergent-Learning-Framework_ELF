#!/usr/bin/env python3
"""
Verify that enforcement hooks are properly registered and functional.
Run this to confirm Golden Rule #1 enforcement is active.
"""

import json
from pathlib import Path
import sys

SETTINGS_FILE = Path.home() / ".claude" / "settings.json"

REQUIRED_HOOKS = {
    "SessionStart": ["load-building.py"],
    "PreToolUse": ["golden-rule-enforcer.py"]
}

def verify():
    print("=" * 50)
    print("[BUILDING] Enforcement Verification")
    print("=" * 50)
    
    if not SETTINGS_FILE.exists():
        print("[X] settings.json not found")
        return False
    
    try:
        settings = json.loads(SETTINGS_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"[X] settings.json is invalid JSON: {e}")
        return False
    
    hooks = settings.get("hooks", {})
    
    all_ok = True
    
    for hook_type, required_files in REQUIRED_HOOKS.items():
        print(f"\n{hook_type}:")
        
        if hook_type not in hooks:
            print(f"  [X] Not registered")
            all_ok = False
            continue
        
        # Collect all hook commands
        hook_commands = []
        for entry in hooks[hook_type]:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                hook_commands.append(cmd)
        
        for required_file in required_files:
            found = any(required_file in cmd for cmd in hook_commands)
            if found:
                print(f"  [OK] {required_file}")
            else:
                print(f"  [X] {required_file} - NOT FOUND")
                all_ok = False
    
    # Check hook files exist
    print(f"\nHook files:")
    hook_files = [
        Path.home() / ".claude" / "hooks" / "SessionStart" / "load-building.py",
        Path.home() / ".claude" / "hooks" / "golden-rule-enforcer.py"
    ]
    
    for hf in hook_files:
        if hf.exists():
            print(f"  [OK] {hf.name}")
        else:
            print(f"  [X] {hf.name} - FILE MISSING")
            all_ok = False
    
    print("\n" + "=" * 50)
    if all_ok:
        print("[SUCCESS] Golden Rule #1 enforcement is ACTIVE")
        print("   - Building will auto-query on session start")
        print("   - Tools blocked after 3 uses without query")
    else:
        print("[WARNING] Enforcement NOT fully configured")
        print("   Run: python ~/.claude/emergent-learning/scripts/register-enforcement-hooks.py")
    print("=" * 50)
    
    return all_ok

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
