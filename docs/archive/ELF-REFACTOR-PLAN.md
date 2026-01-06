# ELF Safe Refactoring Plan

> **CRITICAL**: Read this entire document before executing any commands. This is a step-by-step guide designed to be executed by Claude Code without breaking your project.

## Context

- **Project**: Emergent-Learning-Framework_ELF
- **Problem**: `query.py` is a monolith, file structure is messy, previous refactor attempts broke everything
- **Goal**: Clean root, modular structure, all scripts/hooks pointing to correct locations
- **Safety**: Use git worktree to test everything before touching main

---

## Phase 0: Safety Net Setup

### Step 0.1: Navigate to the ELF repository

```bash
# First, find where the repo is located
# Common locations to check:
# - ~/Emergent-Learning-Framework_ELF
# - ~/projects/Emergent-Learning-Framework_ELF
# - ~/code/Emergent-Learning-Framework_ELF

# Navigate to the repo root (adjust path as needed)
cd ~/Emergent-Learning-Framework_ELF
```

### Step 0.2: Verify clean git state

```bash
git status
```

**STOP if there are uncommitted changes.** Commit or stash them first:

```bash
git add -A
git commit -m "WIP: saving state before refactor"
```

### Step 0.3: Create restore point tag

```bash
git tag -a v0.9-pre-refactor -m "Working state before structure refactor - $(date)"
git push origin v0.9-pre-refactor
```

### Step 0.4: Create worktree for safe refactoring

```bash
# Go to parent directory
cd ..

# Create worktree (this creates a new folder with a copy of main)
git -C Emergent-Learning-Framework_ELF worktree add ../ELF-refactor main

# Enter the worktree
cd ELF-refactor

# Create refactor branch
git checkout -b refactor/clean-structure

# Verify we're in the right place
pwd
git branch
```

**Result**: You now have two folders:
- `Emergent-Learning-Framework_ELF/` → untouched main (your safety net)
- `ELF-refactor/` → your playground for refactoring

---

## Phase 1: Document Current State

### Step 1.1: Generate complete file tree

```bash
# Create a snapshot of current structure
find . -type f -name "*.py" -o -name "*.sh" -o -name "*.ps1" -o -name "*.ts" -o -name "*.tsx" -o -name "*.json" -o -name "*.md" | grep -v node_modules | grep -v __pycache__ | grep -v .git | sort > .refactor-file-list.txt

cat .refactor-file-list.txt
```

### Step 1.2: Map all Python imports

Create a script to analyze dependencies:

```bash
cat > .analyze-imports.py << 'EOF'
#!/usr/bin/env python3
"""Analyze all Python imports in the project."""
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

def find_python_files(root):
    """Find all Python files, excluding venv/node_modules."""
    for path in Path(root).rglob("*.py"):
        path_str = str(path)
        if "node_modules" not in path_str and "__pycache__" not in path_str and ".venv" not in path_str:
            yield path

def extract_imports(filepath):
    """Extract import statements from a Python file."""
    imports = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Match: import x, from x import y
        import_pattern = r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            module = match.group(1) or match.group(2)
            if module:
                imports.append(module.split('.')[0])  # Get root module
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
    return imports

def main():
    root = "."
    
    # Track which files import what
    file_imports = {}
    # Track which local modules are imported by whom
    local_module_importers = defaultdict(list)
    
    # Get list of local Python files (potential local modules)
    local_files = list(find_python_files(root))
    local_modules = {f.stem for f in local_files}
    
    print("=" * 60)
    print("IMPORT DEPENDENCY MAP")
    print("=" * 60)
    
    for filepath in local_files:
        imports = extract_imports(filepath)
        rel_path = str(filepath)
        file_imports[rel_path] = imports
        
        # Track local imports
        for imp in imports:
            if imp in local_modules:
                local_module_importers[imp].append(rel_path)
    
    print("\n## Files and their imports:\n")
    for filepath, imports in sorted(file_imports.items()):
        if imports:
            print(f"### {filepath}")
            print(f"   Imports: {', '.join(sorted(set(imports)))}\n")
    
    print("\n" + "=" * 60)
    print("LOCAL MODULE DEPENDENCIES (CRITICAL FOR REFACTOR)")
    print("=" * 60)
    print("\nThese local modules are imported by other files.")
    print("Moving these files will break the importers!\n")
    
    for module, importers in sorted(local_module_importers.items()):
        print(f"### {module}.py")
        print(f"   Imported by:")
        for imp in importers:
            print(f"   - {imp}")
        print()
    
    # Save to file
    with open(".import-map.md", "w") as f:
        f.write("# Import Dependency Map\n\n")
        f.write("## Local Module Dependencies\n\n")
        for module, importers in sorted(local_module_importers.items()):
            f.write(f"### {module}.py\n")
            f.write("Imported by:\n")
            for imp in importers:
                f.write(f"- {imp}\n")
            f.write("\n")
    
    print("\nSaved detailed map to .import-map.md")

if __name__ == "__main__":
    main()
EOF

python3 .analyze-imports.py
```

### Step 1.3: Document current query.py structure

```bash
# Analyze query.py specifically - find all functions and classes
cat > .analyze-query.py << 'EOF'
#!/usr/bin/env python3
"""Analyze query.py to plan its decomposition."""
import re
import sys
from pathlib import Path

def find_query_py():
    """Find query.py in the project."""
    for path in Path(".").rglob("query.py"):
        if "__pycache__" not in str(path):
            return path
    return None

def analyze_file(filepath):
    """Extract classes, functions, and their sizes."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    total_lines = len(lines)
    
    # Find all class and function definitions
    class_pattern = r'^class\s+(\w+)'
    func_pattern = r'^def\s+(\w+)'
    async_func_pattern = r'^async\s+def\s+(\w+)'
    
    definitions = []
    current_def = None
    current_start = 0
    
    for i, line in enumerate(lines):
        class_match = re.match(class_pattern, line)
        func_match = re.match(func_pattern, line)
        async_match = re.match(async_func_pattern, line)
        
        if class_match or func_match or async_match:
            # Save previous definition
            if current_def:
                definitions.append((current_def, current_start, i - 1))
            
            if class_match:
                current_def = f"class {class_match.group(1)}"
            elif func_match:
                current_def = f"def {func_match.group(1)}"
            else:
                current_def = f"async def {async_match.group(1)}"
            current_start = i
    
    # Don't forget the last one
    if current_def:
        definitions.append((current_def, current_start, total_lines - 1))
    
    print(f"# Analysis of {filepath}")
    print(f"\nTotal lines: {total_lines}\n")
    print("## Definitions found:\n")
    
    # Group by type
    classes = []
    functions = []
    
    for defn, start, end in definitions:
        size = end - start + 1
        entry = f"- `{defn}` (lines {start+1}-{end+1}, ~{size} lines)"
        if defn.startswith("class"):
            classes.append(entry)
        else:
            functions.append(entry)
    
    if classes:
        print("### Classes:")
        for c in classes:
            print(c)
        print()
    
    if functions:
        print("### Functions:")
        for f in functions:
            print(f)
        print()
    
    # Suggest decomposition
    print("\n## Suggested Module Decomposition:\n")
    print("Based on the structure, consider splitting into:\n")
    print("```")
    print("src/elf/query/")
    print("├── __init__.py      # Re-exports everything for backward compat")
    print("├── core.py          # Main QueryEngine class")
    print("├── builders.py      # Query building functions")
    print("├── formatters.py    # Output formatting")
    print("├── database.py      # SQLite operations")
    print("└── cli.py           # CLI argument parsing and main()")
    print("```")

def main():
    query_path = find_query_py()
    if not query_path:
        print("ERROR: Could not find query.py in project")
        sys.exit(1)
    
    analyze_file(query_path)

if __name__ == "__main__":
    main()
EOF

python3 .analyze-query.py > .query-analysis.md
cat .query-analysis.md
```

---

## Phase 2: Define Target Structure

### Target directory layout:

```
ELF/
├── README.md
├── GETTING_STARTED.md
├── UNINSTALL.md
├── LICENSE
├── pyproject.toml              # Modern Python packaging (NEW)
├── install.sh
├── install.ps1
│
├── src/
│   └── elf/                    # Main Python package
│       ├── __init__.py
│       ├── py.typed            # PEP 561 marker
│       │
│       ├── query/              # Query system (decomposed from monolith)
│       │   ├── __init__.py     # Re-exports for backward compat
│       │   ├── engine.py       # QueryEngine class
│       │   ├── builders.py     # Query building logic
│       │   ├── formatters.py   # Output formatting
│       │   ├── database.py     # SQLite operations
│       │   └── cli.py          # CLI interface
│       │
│       ├── memory/             # Memory/learning system
│       │   ├── __init__.py
│       │   ├── heuristics.py
│       │   ├── learnings.py
│       │   └── golden_rules.py
│       │
│       ├── conductor/          # Multi-agent orchestration
│       │   ├── __init__.py
│       │   ├── workflow.py
│       │   ├── blackboard.py
│       │   └── agents.py
│       │
│       └── hooks/              # Claude Code hooks
│           ├── __init__.py
│           ├── pre_tool.py
│           └── post_tool.py
│
├── apps/
│   └── dashboard/              # React dashboard (keep as-is)
│       ├── package.json
│       ├── src/
│       └── ...
│
├── templates/                  # CLAUDE.md templates etc
│
├── agents/                     # Agent personalities
│   ├── researcher/
│   ├── architect/
│   ├── skeptic/
│   └── creative/
│
└── scripts/                    # Utility scripts
    ├── record-failure.sh
    ├── record-heuristic.sh
    └── start-experiment.sh
```

---

## Phase 3: Create New Structure (Incremental)

### Step 3.1: Create package structure without moving files yet

```bash
# Create the new directory structure
mkdir -p src/elf/query
mkdir -p src/elf/memory
mkdir -p src/elf/conductor
mkdir -p src/elf/hooks

# Create __init__.py files
touch src/elf/__init__.py
touch src/elf/query/__init__.py
touch src/elf/memory/__init__.py
touch src/elf/conductor/__init__.py
touch src/elf/hooks/__init__.py

# Create py.typed marker for type checking
touch src/elf/py.typed
```

### Step 3.2: Create pyproject.toml

```bash
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "elf-framework"
version = "0.9.0"
description = "Emergent Learning Framework - Persistent memory and pattern tracking for Claude Code"
readme = "README.md"
license = "MIT"
requires-python = ">=3.8"
authors = [
    { name = "Spacehunterz" }
]
keywords = ["claude", "ai", "memory", "learning", "agents"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "black",
    "ruff",
]

[project.scripts]
elf-query = "elf.query.cli:main"

[project.urls]
Homepage = "https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF"
Repository = "https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF.git"
Issues = "https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/elf"]

[tool.black]
line-length = 100
target-version = ["py38"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]
EOF
```

---

## Phase 4: Decompose query.py

### Step 4.1: Identify the current query.py location

```bash
QUERY_PY=$(find . -name "query.py" -not -path "./__pycache__/*" -not -path "./node_modules/*" | head -1)
echo "Found query.py at: $QUERY_PY"
```

### Step 4.2: Read and understand query.py

**INSTRUCTION FOR CLAUDE CODE**: Read the entire query.py file and identify:
1. All imports at the top
2. All class definitions
3. All function definitions
4. The main() function or CLI entry point
5. Any global variables or constants

### Step 4.3: Create the decomposed modules

**IMPORTANT**: Do this one file at a time. After each file, run import test.

#### 4.3.1: Create database.py (database operations)

Extract all SQLite-related functions:
- Connection handling
- Query execution
- Table operations

```python
# src/elf/query/database.py
"""Database operations for ELF query system."""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

# Move database-related functions here
# Keep function signatures identical for backward compat
```

#### 4.3.2: Create formatters.py (output formatting)

Extract:
- Text formatting functions
- Markdown generation
- Context building for output

```python
# src/elf/query/formatters.py
"""Output formatting for ELF query results."""
from typing import List, Dict, Any

# Move formatting functions here
```

#### 4.3.3: Create builders.py (query construction)

Extract:
- Query building logic
- Filter construction
- Search logic

```python
# src/elf/query/builders.py
"""Query building utilities."""
from typing import Optional, List

# Move query building functions here
```

#### 4.3.4: Create engine.py (main QueryEngine class)

If there's a main class, move it here:

```python
# src/elf/query/engine.py
"""Main QueryEngine class."""
from .database import get_connection, execute_query
from .builders import build_query
from .formatters import format_results

class QueryEngine:
    # Move class here
    pass
```

#### 4.3.5: Create cli.py (CLI interface)

Extract the CLI/main entry point:

```python
# src/elf/query/cli.py
"""Command-line interface for ELF query system."""
import argparse
import sys
from .engine import QueryEngine

def parse_args():
    # Move argparse setup here
    pass

def main():
    # Move main() here
    pass

if __name__ == "__main__":
    main()
```

#### 4.3.6: Create __init__.py (backward compatibility)

```python
# src/elf/query/__init__.py
"""
ELF Query System

This module provides backward-compatible imports.
All original query.py exports are available here.
"""

from .database import (
    get_connection,
    execute_query,
    # ... all database functions
)

from .builders import (
    build_query,
    # ... all builder functions
)

from .formatters import (
    format_results,
    # ... all formatter functions
)

from .engine import QueryEngine

from .cli import main

# For backward compatibility: 
# `from query import X` should still work if PYTHONPATH includes src/elf/query
__all__ = [
    "QueryEngine",
    "get_connection",
    "execute_query",
    "build_query",
    "format_results",
    "main",
    # ... add all other exports
]
```

### Step 4.4: Test imports after decomposition

```bash
# Test the new module structure
cd src
python3 -c "from elf.query import QueryEngine; print('✓ QueryEngine import works')"
python3 -c "from elf.query.database import get_connection; print('✓ database import works')"
python3 -c "from elf.query.cli import main; print('✓ cli import works')"
cd ..
```

---

## Phase 5: Update All References

### Step 5.1: Find all files that import from query

```bash
grep -r "from query import\|import query\|from.*query.*import" --include="*.py" . | grep -v __pycache__ | grep -v .venv
```

### Step 5.2: Update each reference

For each file found, update the imports:

**Old:**
```python
from query import QueryEngine, build_context
```

**New:**
```python
from elf.query import QueryEngine, build_context
```

**OR for backward compat without changing imports**, add to the files that need it:

```python
import sys
from pathlib import Path
# Add src to path for backward compat
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

### Step 5.3: Update hook scripts

The hooks in `~/.claude/hooks/learning-loop/` reference query.py. These need updating:

```bash
# Find hook references
grep -r "query.py\|query import" hooks/ templates/ scripts/ 2>/dev/null || echo "No hook references found in repo (they may be in ~/.claude)"
```

**IMPORTANT**: The install scripts copy files to `~/.claude/`. You need to update:
1. The source files in the repo
2. The paths in install.sh and install.ps1

---

## Phase 6: Update Install Scripts

### Step 6.1: Review current install.sh

```bash
cat install.sh
```

### Step 6.2: Update paths in install.sh

The install script copies files to `~/.claude/emergent-learning/`. Update it to:
1. Copy from new locations
2. Maintain the expected structure in `~/.claude/`

Key changes needed:
- `src/query/query.py` → `src/elf/query/` (entire directory)
- Update any hardcoded paths

### Step 6.3: Same for install.ps1

```bash
cat install.ps1
```

---

## Phase 7: Clean Root Directory

### Step 7.1: Move stray files to appropriate locations

```bash
# Move any Python files in root to src/elf/
# (Be careful - some might need to stay for backward compat)

# Move scripts to scripts/
# Move templates to templates/
# Keep only essential files in root: README, LICENSE, install scripts, pyproject.toml
```

### Step 7.2: Update .gitignore

```bash
cat >> .gitignore << 'EOF'

# Refactor artifacts
.refactor-file-list.txt
.import-map.md
.query-analysis.md
.analyze-imports.py
.analyze-query.py

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environments
.env
.venv
env/
venv/
ENV/
EOF
```

---

## Phase 8: Test Everything

### Step 8.1: Test Python imports

```bash
cd src
python3 -c "
from elf.query import main
from elf.query.engine import QueryEngine
from elf.query.database import get_connection
print('✓ All imports successful')
"
cd ..
```

### Step 8.2: Test CLI

```bash
python3 -m elf.query --help
# or
python3 src/elf/query/cli.py --stats
```

### Step 8.3: Test install script (dry run)

```bash
# Create a temp directory to test install
mkdir -p /tmp/test-elf-install
ELF_BASE_PATH=/tmp/test-elf-install ./install.sh

# Check what got installed
find /tmp/test-elf-install -type f | head -20

# Clean up
rm -rf /tmp/test-elf-install
```

### Step 8.4: Test hooks work

```bash
# If hooks reference the query system, test them
python3 hooks/learning-loop/pre_tool_learning.py --help 2>/dev/null || echo "Test hook manually"
```

---

## Phase 9: Commit and Merge

### Step 9.1: Review all changes

```bash
git status
git diff --stat
```

### Step 9.2: Commit the refactor

```bash
git add -A
git commit -m "refactor: modular structure with decomposed query system

- Split query.py monolith into query/{engine,database,builders,formatters,cli}.py
- Created proper Python package structure under src/elf/
- Added pyproject.toml for modern packaging
- Updated install scripts for new paths
- Maintained backward compatibility via __init__.py re-exports
- Cleaned root directory

Breaking changes: None (backward compat maintained)
"
```

### Step 9.3: Push branch for review (optional but recommended)

```bash
git push -u origin refactor/clean-structure
```

### Step 9.4: Merge to main (when confident)

```bash
# Switch to main in the original repo
cd ../Emergent-Learning-Framework_ELF
git fetch origin
git merge origin/refactor/clean-structure

# Or if you prefer to stay in worktree:
git checkout main
git merge refactor/clean-structure
git push origin main
```

---

## Phase 10: Cleanup

### Step 10.1: Remove worktree

```bash
cd ..
git -C Emergent-Learning-Framework_ELF worktree remove ELF-refactor
```

### Step 10.2: Clean up analysis files

```bash
cd Emergent-Learning-Framework_ELF
rm -f .refactor-file-list.txt .import-map.md .query-analysis.md .analyze-imports.py .analyze-query.py
```

### Step 10.3: Create a release tag

```bash
git tag -a v0.9.0 -m "Release v0.9.0 - Clean modular structure"
git push origin v0.9.0
```

---

## Emergency Rollback

If everything goes wrong:

```bash
# Option 1: Reset to pre-refactor tag
cd Emergent-Learning-Framework_ELF
git fetch --tags
git reset --hard v0.9-pre-refactor
git push --force origin main  # CAREFUL: force push

# Option 2: Just delete worktree and pretend nothing happened
rm -rf ../ELF-refactor
git -C . worktree prune
```

---

## Checklist

Before considering the refactor complete:

- [ ] All Python imports work (`python -c "from elf.query import main"`)
- [ ] CLI works (`python -m elf.query --stats`)
- [ ] Install script works (test in temp directory)
- [ ] Hooks work after fresh install
- [ ] Dashboard still starts
- [ ] No files in root that should be in subdirectories
- [ ] .gitignore updated
- [ ] README updated with new paths if needed
- [ ] All tests pass (if you have tests)

---

## Notes for Claude Code Execution

1. **Work incrementally**: Complete each phase before moving to the next
2. **Test after each change**: Don't batch multiple structural changes
3. **Keep backward compatibility**: The `__init__.py` re-exports are critical
4. **Check hook paths**: These are the most likely to break
5. **Use the worktree**: Don't touch main until everything works

If you get stuck, the safest action is:
```bash
cd ../Emergent-Learning-Framework_ELF
git status  # Verify main is untouched
```

Your main branch is always safe as long as you work in the worktree.
