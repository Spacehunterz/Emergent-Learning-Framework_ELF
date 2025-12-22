"""
Project detection and context management for per-project ELF support.

DEPRECATION NOTICE (2025-12-20):
The .elf/ per-project database approach is being deprecated in favor of
a simpler single-database architecture with a 'project_path' column for
location awareness. This module remains for backwards compatibility but
new code should use:
- QuerySystem with current_location parameter for location-aware queries
- record_heuristic_with_location() with project_path parameter

Legacy features that will be removed:
- .elf/ directory detection and project-specific databases
- Separate learnings.db files per project

This module handles:
- Detecting project root by walking up from cwd
- Distinguishing between ELF-initialized projects (.elf/) and regular projects
- Loading project-specific context and configuration
- Providing unified project context for the query system
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# yaml is optional - needed for config.yaml parsing
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Markers that indicate a project root (in priority order)
PROJECT_MARKERS = [
    '.elf',           # ELF project (highest priority)
    '.git',           # Git repository
    'package.json',   # Node.js project
    'Cargo.toml',     # Rust project
    'pyproject.toml', # Python project
    'go.mod',         # Go module
    'pom.xml',        # Maven project
    'build.gradle',   # Gradle project
    '.project-root',  # Explicit marker
]


@dataclass
class ProjectContext:
    """Represents the current project context."""

    # Project detection
    mode: str  # 'project' | 'global-only'
    project_root: Optional[Path] = None
    project_name: Optional[str] = None

    # ELF-specific paths (only set if .elf/ exists)
    elf_root: Optional[Path] = None
    project_db_path: Optional[Path] = None
    config_path: Optional[Path] = None
    context_md_path: Optional[Path] = None

    # Global paths (always set)
    global_root: Path = field(default_factory=lambda: Path.home() / ".claude" / "emergent-learning")
    global_db_path: Path = field(default_factory=lambda: Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db")

    # Loaded configuration
    config: Dict[str, Any] = field(default_factory=dict)
    domains: List[str] = field(default_factory=list)

    # Inheritance chain for monorepos
    inheritance_chain: List[Path] = field(default_factory=list)

    def has_project_context(self) -> bool:
        """Check if we have project-specific ELF context."""
        return self.mode == 'project' and self.elf_root is not None

    def get_context_md_content(self) -> Optional[str]:
        """Load and return the project context.md content if it exists."""
        if self.context_md_path and self.context_md_path.exists():
            try:
                content = self.context_md_path.read_text(encoding='utf-8')
                # Skip if it's just the template
                if '[Describe your project here]' in content:
                    return None
                return content
            except Exception:
                return None
        return None


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the project root by walking up from start_path.

    Looks for any PROJECT_MARKERS to determine the root.
    Does NOT require .elf/ - just finds the project boundary.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Path to project root, or None if no markers found
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path

    while True:
        for marker in PROJECT_MARKERS:
            marker_path = current / marker
            if marker_path.exists():
                return current

        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


def find_elf_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the nearest .elf/ directory by walking up from start_path.

    This specifically looks for ELF-initialized projects.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Path to directory containing .elf/, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path

    while True:
        elf_dir = current / '.elf'
        if elf_dir.exists() and elf_dir.is_dir():
            return current

        parent = current.parent
        if parent == current:
            return None
        current = parent


def find_inheritance_chain(elf_root: Path) -> List[Path]:
    """
    Find the inheritance chain for monorepo support.

    Walks up looking for parent .elf/ directories that this project
    might inherit from (based on inherits_from config).

    Args:
        elf_root: The current .elf/ project root

    Returns:
        List of parent .elf/ roots in inheritance order (closest first)
    """
    chain = []

    if not YAML_AVAILABLE:
        return chain

    # Load config to check for explicit inherits_from
    config_path = elf_root / '.elf' / 'config.yaml'
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            inherits_from = config.get('project', {}).get('inherits_from')
            if inherits_from:
                parent_path = (elf_root / inherits_from).resolve()
                parent_elf = parent_path / '.elf'
                if parent_elf.exists():
                    chain.append(parent_path)
                    # Recursively find grandparents
                    chain.extend(find_inheritance_chain(parent_path))
        except Exception:
            pass

    return chain


def load_project_config(elf_root: Path) -> Dict[str, Any]:
    """
    Load project configuration from .elf/config.yaml.

    Args:
        elf_root: Path to directory containing .elf/

    Returns:
        Configuration dictionary (empty if not found or invalid)
    """
    if not YAML_AVAILABLE:
        return {}

    config_path = elf_root / '.elf' / 'config.yaml'
    if not config_path.exists():
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config if isinstance(config, dict) else {}
    except Exception:
        return {}


def detect_project_context(start_path: Optional[Path] = None) -> ProjectContext:
    """
    Detect and build the full project context.

    This is the main entry point for project detection. It:
    1. Finds the project root (with or without .elf/)
    2. Checks if ELF is initialized (.elf/ exists)
    3. Loads configuration if available
    4. Builds inheritance chain for monorepos

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        ProjectContext with all relevant information
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    # Find project root (any marker)
    project_root = find_project_root(start_path)

    # Find ELF root specifically
    elf_root = find_elf_root(start_path)

    # Build context based on what we found
    if elf_root:
        # ELF-initialized project
        config = load_project_config(elf_root)
        inheritance_chain = find_inheritance_chain(elf_root)

        # Extract project name from config or directory name
        project_name = config.get('project', {}).get('name')
        if not project_name:
            project_name = elf_root.name

        # Extract domains
        domains = config.get('domains', [])

        return ProjectContext(
            mode='project',
            project_root=project_root or elf_root,
            project_name=project_name,
            elf_root=elf_root,
            project_db_path=elf_root / '.elf' / 'learnings.db',
            config_path=elf_root / '.elf' / 'config.yaml',
            context_md_path=elf_root / '.elf' / 'context.md',
            config=config,
            domains=domains,
            inheritance_chain=inheritance_chain,
        )
    else:
        # Global-only mode (no .elf/ found)
        project_name = project_root.name if project_root else None

        return ProjectContext(
            mode='global-only',
            project_root=project_root,
            project_name=project_name,
        )


def get_effective_domains(ctx: ProjectContext, explicit_domain: Optional[str] = None) -> List[str]:
    """
    Get the effective domains for querying, merging project and explicit domains.

    Args:
        ctx: Project context
        explicit_domain: Explicitly requested domain (takes priority)

    Returns:
        List of domains to query
    """
    domains = []

    if explicit_domain:
        domains.append(explicit_domain)

    if ctx.domains:
        for d in ctx.domains:
            if d not in domains:
                domains.append(d)

    return domains


def format_project_status(ctx: ProjectContext) -> str:
    """
    Format project context as a status string for CLI output.

    Args:
        ctx: Project context

    Returns:
        Human-readable status string
    """
    lines = []

    if ctx.mode == 'project':
        lines.append(f"[Project] Project: {ctx.project_name} ({ctx.elf_root})")
        lines.append(f"   Mode: ELF-enabled")
        if ctx.domains:
            lines.append(f"   Domains: {', '.join(ctx.domains)}")
        if ctx.inheritance_chain:
            parents = [p.name for p in ctx.inheritance_chain]
            lines.append(f"   Inherits from: {' → '.join(parents)}")
    else:
        if ctx.project_root:
            lines.append(f"[Project] Project: {ctx.project_name} ({ctx.project_root})")
            lines.append(f"   Mode: Global-only (no .elf/ - run 'elf init' to enable)")
        else:
            lines.append(f"[Project] No project detected")
            lines.append(f"   Mode: Global-only")

    lines.append(f"[Global] Global: {ctx.global_root}")

    return '\n'.join(lines)
