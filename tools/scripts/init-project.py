#!/usr/bin/env python3
"""
Initialize ELF for a project.

Creates the .elf/ directory structure with:
- config.yaml: Project configuration
- context.md: Project context for Claude (template)
- learnings.db: Project-specific learning database

Usage:
    python init-project.py [--name NAME] [--domains DOMAINS] [--auto-context]
    python init-project.py --help
"""

import os
import sys
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


# Default templates
CONFIG_TEMPLATE = '''project:
  name: {name}
  description: ""

domains: []

inherit_global:
  golden_rules: true
  heuristics:
    min_confidence: 0.8

team:
  share_heuristics: true
'''

CONTEXT_TEMPLATE = '''# Project Context

<!--
Describe your project for Claude. Include:
- What this project does
- Tech stack and patterns
- Key architectural decisions
- Team conventions
- Known quirks or gotchas
-->

## Overview
[Describe your project here]

## Tech Stack
-

## Architecture
-

## Conventions
-

## Known Quirks
-
'''

GITIGNORE_ADDITION = '''
# ELF project-specific database (not shared via git)
.elf/learnings.db
.elf/sync-manifest.json
'''


def create_project_db(db_path: Path) -> None:
    """Create the project-specific SQLite database with schema."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Heuristics table (project-specific learnings)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS heuristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule TEXT NOT NULL,
            explanation TEXT,
            domain TEXT,
            confidence REAL DEFAULT 0.7,
            source TEXT DEFAULT 'observation',
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_validated TIMESTAMP,
            validation_count INTEGER DEFAULT 0,
            promoted_to_global INTEGER DEFAULT 0,
            promoted_at TIMESTAMP
        )
    ''')

    # Learnings table (successes, failures, observations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            summary TEXT NOT NULL,
            details TEXT,
            domain TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Experiments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hypothesis TEXT,
            status TEXT DEFAULT 'active',
            outcome TEXT,
            domain TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            concluded_at TIMESTAMP
        )
    ''')

    # Decisions table (project-specific ADRs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            decision TEXT NOT NULL,
            rationale TEXT,
            alternatives TEXT,
            status TEXT DEFAULT 'accepted',
            domain TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')

    # Schema version tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (1)')

    conn.commit()
    conn.close()


def detect_project_info(project_path: Path) -> dict:
    """Auto-detect project information from common files."""
    info = {
        'name': project_path.name,
        'domains': [],
        'tech_stack': [],
    }

    # Check package.json for Node.js projects
    package_json = project_path / 'package.json'
    if package_json.exists():
        try:
            import json
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                if pkg.get('name'):
                    info['name'] = pkg['name']
                if pkg.get('description'):
                    info['description'] = pkg['description']

                # Detect frameworks from dependencies
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                if 'react' in deps:
                    info['domains'].append('react')
                    info['tech_stack'].append('React')
                if 'vue' in deps:
                    info['domains'].append('vue')
                    info['tech_stack'].append('Vue')
                if 'typescript' in deps:
                    info['domains'].append('typescript')
                    info['tech_stack'].append('TypeScript')
                if 'next' in deps:
                    info['domains'].append('nextjs')
                    info['tech_stack'].append('Next.js')
                if 'express' in deps:
                    info['domains'].append('express')
                    info['tech_stack'].append('Express')
        except Exception:
            pass

    # Check pyproject.toml for Python projects
    pyproject = project_path / 'pyproject.toml'
    if pyproject.exists():
        info['domains'].append('python')
        info['tech_stack'].append('Python')
        try:
            content = pyproject.read_text(encoding='utf-8')
            if 'fastapi' in content.lower():
                info['domains'].append('fastapi')
                info['tech_stack'].append('FastAPI')
            if 'django' in content.lower():
                info['domains'].append('django')
                info['tech_stack'].append('Django')
            if 'flask' in content.lower():
                info['domains'].append('flask')
                info['tech_stack'].append('Flask')
        except Exception:
            pass

    # Check Cargo.toml for Rust projects
    cargo = project_path / 'Cargo.toml'
    if cargo.exists():
        info['domains'].append('rust')
        info['tech_stack'].append('Rust')

    # Check go.mod for Go projects
    gomod = project_path / 'go.mod'
    if gomod.exists():
        info['domains'].append('go')
        info['tech_stack'].append('Go')

    return info


def update_gitignore(project_path: Path) -> bool:
    """Add ELF entries to .gitignore if it exists."""
    gitignore = project_path / '.gitignore'

    if not gitignore.exists():
        return False

    try:
        content = gitignore.read_text(encoding='utf-8')

        # Check if already has ELF entries
        if '.elf/learnings.db' in content:
            return False

        # Append ELF entries
        with open(gitignore, 'a', encoding='utf-8') as f:
            f.write(GITIGNORE_ADDITION)

        return True
    except Exception:
        return False


def generate_auto_context(project_path: Path, info: dict) -> str:
    """Generate context.md content from auto-detected info."""
    lines = ['# Project Context', '']

    if info.get('description'):
        lines.append(f"## Overview")
        lines.append(info['description'])
        lines.append('')
    else:
        lines.append('## Overview')
        lines.append(f"{info['name']} project.")
        lines.append('')

    if info.get('tech_stack'):
        lines.append('## Tech Stack')
        for tech in info['tech_stack']:
            lines.append(f'- {tech}')
        lines.append('')

    lines.append('## Architecture')
    lines.append('[Add architectural decisions here]')
    lines.append('')

    lines.append('## Conventions')
    lines.append('[Add team conventions here]')
    lines.append('')

    lines.append('## Known Quirks')
    lines.append('[Add known issues or gotchas here]')

    return '\n'.join(lines)


def init_project(
    project_path: Path,
    name: Optional[str] = None,
    domains: Optional[list] = None,
    auto_context: bool = False,
    force: bool = False
) -> int:
    """
    Initialize ELF for a project.

    Args:
        project_path: Path to project root
        name: Project name (auto-detected if not provided)
        domains: List of domains (auto-detected if not provided)
        auto_context: Generate context.md from codebase analysis
        force: Overwrite existing .elf/ if present

    Returns:
        Exit code (0 for success)
    """
    elf_dir = project_path / '.elf'

    # Check if already initialized
    if elf_dir.exists() and not force:
        print(f"[!]  ELF already initialized at {elf_dir}")
        print("   Use --force to reinitialize")
        return 1

    # Auto-detect project info
    info = detect_project_info(project_path)

    # Override with explicit values
    if name:
        info['name'] = name
    if domains:
        info['domains'] = domains

    print(f"Initializing ELF for: {info['name']}")
    print()

    # Create .elf/ directory
    elf_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created: {elf_dir}")

    # Create config.yaml
    config_path = elf_dir / 'config.yaml'
    config_content = CONFIG_TEMPLATE.format(name=info['name'])
    if info['domains']:
        # Replace empty domains list with detected ones
        domain_lines = '\n'.join(f'  - {d}' for d in info['domains'])
        config_content = config_content.replace('domains: []', f'domains:\n{domain_lines}')
    config_path.write_text(config_content, encoding='utf-8')
    print(f"Created: {config_path}")

    # Create context.md
    context_path = elf_dir / 'context.md'
    if auto_context:
        context_content = generate_auto_context(project_path, info)
        print(f"Created: {context_path} (auto-generated)")
    else:
        context_content = CONTEXT_TEMPLATE
        print(f"Created: {context_path} (template)")
    context_path.write_text(context_content, encoding='utf-8')

    # Create heuristics/ directory for git-tracked markdown
    heuristics_dir = elf_dir / 'heuristics'
    heuristics_dir.mkdir(exist_ok=True)
    print(f"Created: {heuristics_dir}")

    # Create learnings.db
    db_path = elf_dir / 'learnings.db'
    create_project_db(db_path)
    print(f"Created: {db_path}")

    # Update .gitignore
    if update_gitignore(project_path):
        print(f"Updated: {project_path / '.gitignore'} (added .elf/learnings.db)")

    print()
    print("[OK] ELF initialized successfully!")
    print()

    if not auto_context:
        print("Note: Next steps:")
        print(f"   1. Edit {context_path} to describe your project")
        print("   2. Update domains in config.yaml if needed")
        print("   3. Run 'query.py --context' to verify setup")
    else:
        print("Note: Auto-generated context.md - please review and refine.")

    if info['domains']:
        print()
        print(f"Detected: Detected domains: {', '.join(info['domains'])}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Initialize ELF for a project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize in current directory
  python init-project.py

  # Initialize with explicit name
  python init-project.py --name my-awesome-project

  # Initialize with domains
  python init-project.py --domains react,typescript,api

  # Auto-generate context.md from codebase
  python init-project.py --auto-context

  # Reinitialize (overwrite existing)
  python init-project.py --force
        """
    )

    parser.add_argument('--path', type=str, default='.',
                       help='Project path (default: current directory)')
    parser.add_argument('--name', type=str,
                       help='Project name (auto-detected if not provided)')
    parser.add_argument('--domains', type=str,
                       help='Comma-separated list of domains')
    parser.add_argument('--auto-context', action='store_true',
                       help='Auto-generate context.md from codebase analysis')
    parser.add_argument('--force', action='store_true',
                       help='Overwrite existing .elf/ if present')

    args = parser.parse_args()

    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"ERROR: Path does not exist: {project_path}")
        return 1

    domains = args.domains.split(',') if args.domains else None

    return init_project(
        project_path=project_path,
        name=args.name,
        domains=domains,
        auto_context=args.auto_context,
        force=args.force
    )


if __name__ == '__main__':
    sys.exit(main())
