#!/usr/bin/env python3
"""
Install hooks from ELF templates to ~/.claude/hooks/

This script:
1. Discovers all hook templates in .hooks-templates/
2. Copies them to ~/.claude/hooks/ preserving directory structure
3. Makes them executable
4. Reports what was installed

Usage:
    python install-hooks.py [--verbose] [--force]
    
Options:
    --verbose   Show all hooks being installed
    --force     Overwrite existing hooks (default: skip if exists)
"""

import sys
import os
import shutil
from pathlib import Path

def install_hooks(verbose=False, force=False):
    """Install hooks from templates to ~/.claude/hooks/"""
    
    elf_dir = Path.home() / '.claude/emergent-learning'
    templates_dir = elf_dir / '.hooks-templates'
    hooks_dir = Path.home() / '.claude/hooks'
    
    if not templates_dir.exists():
        print(f"Error: Hook templates directory not found: {templates_dir}")
        return False
    
    installed = []
    skipped = []
    
    # Walk through templates and copy
    for template_file in templates_dir.rglob('*'):
        if not template_file.is_file():
            continue
        
        # Calculate relative path from templates dir
        rel_path = template_file.relative_to(templates_dir)
        target_path = hooks_dir / rel_path
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if target exists
        if target_path.exists() and not force:
            skipped.append(str(rel_path))
            if verbose:
                print(f"[SKIP] {rel_path} (already exists)")
            continue
        
        # Copy file
        try:
            shutil.copy2(template_file, target_path)
            os.chmod(target_path, 0o755)  # Make executable
            installed.append(str(rel_path))
            if verbose:
                print(f"[+] {rel_path}")
        except Exception as e:
            print(f"[ERROR] Failed to install {rel_path}: {e}", file=sys.stderr)
            return False
    
    # Print summary
    if installed:
        print(f"Installed {len(installed)} hook(s)")
        if verbose:
            for h in installed:
                print(f"  + {h}")
    
    if skipped:
        if verbose:
            print(f"Skipped {len(skipped)} existing hook(s)")
            for h in skipped:
                print(f"  ~ {h}")
    
    return True

if __name__ == '__main__':
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    force = '--force' in sys.argv
    
    if install_hooks(verbose=verbose, force=force):
        sys.exit(0)
    else:
        sys.exit(1)
