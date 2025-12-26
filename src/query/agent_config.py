"""
Agent Configuration Loader for Session-Start Injection.

Loads agent selector configuration at session start and formats it
for inclusion in the context. This makes agent weights, tier preferences,
and routing rules available to Claude throughout the session.

Config loading hierarchy:
1. Global: ~/.claude/emergent-learning/agent_selector/config.yaml
2. Project override: .elf/agents.yaml (if exists in current directory)
3. Final: Deep merge with project values taking precedence
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from functools import lru_cache
import logging
import os

# Setup module logger
logger = logging.getLogger(__name__)

# Try to import yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Import deep_merge from config_loader
try:
    from query.config_loader import deep_merge, get_base_path
except ImportError:
    from config_loader import deep_merge, get_base_path


def get_global_agent_config_path() -> Optional[Path]:
    """
    Get path to global agent selector config.

    Returns None if base path cannot be determined.
    """
    try:
        base = get_base_path()
        return base / 'agent_selector' / 'config.yaml'
    except RuntimeError as e:
        logger.warning(f"Failed to get base path for agent config: {e}")
        return None


def get_project_agent_config_path() -> Optional[Path]:
    """
    Get path to project-local agent config if it exists.

    Looks for .elf/agents.yaml in the current working directory.
    Returns None if not found.
    """
    cwd = Path(os.getcwd())
    project_config = cwd / '.elf' / 'agents.yaml'

    if project_config.exists():
        return project_config

    return None


def load_yaml_safe(path: Path) -> Optional[Dict[str, Any]]:
    """Load YAML file safely, returning None on any error."""
    if not path.exists():
        return None

    if not YAML_AVAILABLE:
        logger.warning(f"YAML library not available, cannot load config from {path}")
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else None
    except PermissionError:
        logger.warning(f"Permission denied reading config file {path}")
        return None
    except Exception as e:
        logger.warning(f"Failed to parse YAML config at {path}: {e}")
        return None


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate agent configuration schema.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
        - is_valid: True if all required keys present with correct types
        - list_of_errors: List of validation error messages (empty if valid)
    """
    errors = []

    # Required top-level keys
    required_keys = {
        'defaults': dict,
        'category_weights': dict,
        'phase_weights': dict,
        'complexity_requirements': dict,
    }

    # Check required keys exist with correct types
    for key, expected_type in required_keys.items():
        if key not in config:
            errors.append(f"Missing required key: '{key}'")
        elif not isinstance(config[key], expected_type):
            actual_type = type(config[key]).__name__
            errors.append(f"Invalid type for '{key}': expected {expected_type.__name__}, got {actual_type}")

    # Validate phase_weights structure if present
    if 'phase_weights' in config and isinstance(config['phase_weights'], dict):
        required_phases = ['plan', 'execute', 'review']
        for phase in required_phases:
            if phase not in config['phase_weights']:
                errors.append(f"Missing required phase in phase_weights: '{phase}'")
            elif not isinstance(config['phase_weights'][phase], dict):
                actual_type = type(config['phase_weights'][phase]).__name__
                errors.append(f"Invalid type for phase_weights.{phase}: expected dict, got {actual_type}")

    # Validate complexity_requirements keys if present
    if 'complexity_requirements' in config and isinstance(config['complexity_requirements'], dict):
        required_levels = ['critical', 'high', 'medium', 'low']
        for level in required_levels:
            if level not in config['complexity_requirements']:
                errors.append(f"Missing required complexity level: '{level}'")

    # Validate defaults structure if present
    if 'defaults' in config and isinstance(config['defaults'], dict):
        if 'max_agents' not in config['defaults']:
            errors.append("Missing 'max_agents' in defaults")
        if 'prefer_tier' not in config['defaults']:
            errors.append("Missing 'prefer_tier' in defaults")

    is_valid = len(errors) == 0
    return is_valid, errors


def get_default_agent_config() -> Dict[str, Any]:
    """Return default agent configuration when no config files exist."""
    return {
        'defaults': {
            'max_agents': None,
            'prefer_tier': None,
        },
        'category_weights': {
            'security': 1.5,
            'testing': 1.2,
            'documentation': 0.8,
        },
        'disabled_agents': [],
        'always_include': {},
        'tier_overrides': {},
        'phase_weights': {
            'plan': {'opus': 2.0, 'sonnet': 1.5, 'haiku': 0.5},
            'execute': {'opus': 1.0, 'sonnet': 1.5, 'haiku': 1.5},
            'review': {'opus': 2.0, 'sonnet': 2.0, 'haiku': 0.5},
        },
        'complexity_requirements': {
            'critical': 'opus',
            'high': 'sonnet',
            'medium': None,
            'low': None,
        },
    }


@lru_cache(maxsize=1)
def load_agent_config() -> Tuple[Dict[str, Any], str]:
    """
    Load agent configuration with hierarchy merging.

    Returns:
        Tuple of (merged_config, source_description)
        source_description indicates where config came from:
        - "global" - only global config used
        - "project" - only project config used
        - "merged" - both configs merged
        - "defaults" - no config files found, using defaults

    Note: Results are cached for the session. Call load_agent_config.cache_clear()
    to force reload from disk.
    """
    global_path = get_global_agent_config_path()
    project_path = get_project_agent_config_path()

    global_config = load_yaml_safe(global_path) if global_path else None
    project_config = load_yaml_safe(project_path) if project_path else None

    # Determine source and merge
    if global_config and project_config:
        merged = deep_merge(global_config, project_config)
        source = "merged (global + project)"
    elif global_config:
        merged = global_config
        source = "global"
    elif project_config:
        merged = project_config
        source = "project"
    else:
        # Return sensible defaults
        return get_default_agent_config(), "defaults"

    # Validate config schema
    is_valid, errors = validate_config(merged)

    if not is_valid:
        logger.warning(f"Agent config validation failed ({source}):")
        for error in errors:
            logger.warning(f"  - {error}")
        logger.warning("Falling back to defaults for missing/invalid keys")

        # Merge with defaults to fill gaps
        defaults = get_default_agent_config()
        merged = deep_merge(defaults, merged)
        source = f"{source} (validation-repaired)"

    return merged, source


def format_config_for_context(
    config: Dict[str, Any],
    source: str,
    include_metadata: bool = True
) -> str:
    """
    Format agent configuration for inclusion in context output.

    Args:
        config: The merged configuration dictionary
        source: Description of where config came from
        include_metadata: Whether to include timestamp and source info

    Returns:
        Formatted string ready for context injection
    """
    lines = []

    lines.append("# AGENT CONFIGURATION (Session-Loaded)")
    lines.append("")

    if YAML_AVAILABLE:
        # Output as YAML block
        lines.append("```yaml")
        lines.append(yaml.dump(config, default_flow_style=False, sort_keys=False))
        lines.append("```")
    else:
        # Fallback: format as readable text
        lines.append("```")
        lines.append(_format_config_text(config))
        lines.append("```")

    if include_metadata:
        lines.append("")
        lines.append(f"**Config Source:** {source}")
        lines.append(f"**Loaded at:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")

        # Show paths for debugging
        global_path = get_global_agent_config_path()
        project_path = get_project_agent_config_path()

        if global_path and global_path.exists():
            lines.append(f"**Global path:** `{global_path}`")
        if project_path and project_path.exists():
            lines.append(f"**Project path:** `{project_path}`")

    lines.append("")
    return "\n".join(lines)


def _format_config_text(config: Dict[str, Any], indent: int = 0) -> str:
    """Format config as readable text (fallback when YAML not available)."""
    lines = []
    prefix = "  " * indent

    for key, value in config.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_format_config_text(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: [{', '.join(str(v) for v in value)}]")
        else:
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def get_config_for_context(include_metadata: bool = True) -> str:
    """
    Main entry point: Load and format agent config for context injection.

    This is the function called by query.py when --include-config is set.

    Args:
        include_metadata: Include timestamp and source info

    Returns:
        Formatted config string ready for context
    """
    config, source = load_agent_config()
    return format_config_for_context(config, source, include_metadata)


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Get a specific config value by dot-notation path.

    Args:
        key_path: Dot-separated path like "phase_weights.plan.opus"
        default: Default value if path not found

    Returns:
        The config value or default
    """
    config, _ = load_agent_config()

    keys = key_path.split('.')
    current = config

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


# CLI for testing
if __name__ == '__main__':
    print("=== Agent Configuration Loader ===\n")

    # Show paths
    print(f"Global config path: {get_global_agent_config_path()}")
    print(f"Project config path: {get_project_agent_config_path()}")
    print()

    # Load and display
    config, source = load_agent_config()
    print(f"Source: {source}")
    print()

    # Show formatted output
    print("--- Formatted for Context ---")
    print(get_config_for_context())
