"""
Configuration loader with customization layer support.

Loads default configs and merges with user customizations from custom/ directory.
Custom configs override defaults (deep merge for dicts, replace for other types).
"""

from pathlib import Path
from typing import Any, Dict, Optional
import os

# Try to import yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Resolve paths
def get_base_path() -> Path:
    """Get the base path for emergent-learning directory."""
    # Check environment variable first
    env_path = os.environ.get('ELF_BASE_PATH')
    if env_path:
        return Path(env_path)

    # Default to ~/.claude/emergent-learning
    return Path.home() / '.claude' / 'emergent-learning'


BASE_PATH = get_base_path()
CUSTOM_PATH = BASE_PATH / 'custom'
AGENTS_PATH = BASE_PATH / 'agents'
MEMORY_PATH = BASE_PATH / 'memory'


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Values from override take precedence.
    Nested dicts are merged recursively.
    Lists are replaced (not concatenated).
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_yaml_file(path: Path) -> Optional[Dict]:
    """Load a YAML file, returning None if not found or invalid."""
    if not path.exists():
        return None

    if not YAML_AVAILABLE:
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def get_default_config() -> Dict[str, Any]:
    """Return default configuration values."""
    return {
        'preferences': {
            'default_depth': 'standard',
            'default_format': 'text',
            'default_timeout': 30,
        },
        'query': {
            'max_results': 10,
            'include_challenged': True,
            'show_similar_failures': True,
        },
        'always_load_categories': ['core'],
        'my_domains': [],
        'dashboard': {
            'auto_start': False,
            'backend_port': 8888,
            'frontend_port': 3001,
        },
        'agents': {
            'default_review_party': 'code-review',
            'default_feature_party': 'new-feature',
        },
        'notifications': {
            'show_bootstrap_progress': True,
            'alert_on_violations': True,
        },
    }


def load_config() -> Dict[str, Any]:
    """
    Load configuration with customization layer.

    1. Load defaults
    2. Load custom/config.yaml if exists
    3. Deep merge custom over defaults
    """
    config = get_default_config()

    # Try to load custom config
    custom_config_path = CUSTOM_PATH / 'config.yaml'
    custom_config = load_yaml_file(custom_config_path)

    if custom_config:
        config = deep_merge(config, custom_config)

    return config


def load_custom_golden_rules() -> Optional[str]:
    """
    Load custom golden rules if they exist.

    Returns the content of custom/golden-rules.md, or None if not found.
    """
    custom_rules_path = CUSTOM_PATH / 'golden-rules.md'

    if not custom_rules_path.exists():
        return None

    try:
        return custom_rules_path.read_text(encoding='utf-8')
    except Exception:
        return None


def load_custom_parties() -> Dict[str, Any]:
    """
    Load custom party definitions.

    Returns dict of custom parties, or empty dict if none.
    """
    custom_parties_path = CUSTOM_PATH / 'parties.yaml'
    data = load_yaml_file(custom_parties_path)

    if data and 'parties' in data:
        return data['parties']

    return {}


def load_all_parties() -> Dict[str, Any]:
    """
    Load all parties (default + custom merged).

    Custom parties override defaults with same name.
    """
    # Load default parties
    default_parties_path = AGENTS_PATH / 'parties.yaml'
    default_data = load_yaml_file(default_parties_path)
    default_parties = default_data.get('parties', {}) if default_data else {}

    # Load custom parties
    custom_parties = load_custom_parties()

    # Merge (custom overrides default)
    return deep_merge(default_parties, custom_parties)


def get_always_load_categories() -> list:
    """Get categories that should always be loaded (even in minimal depth)."""
    config = load_config()
    return config.get('always_load_categories', ['core'])


def get_user_domains() -> list:
    """Get user's primary domains for better suggestions."""
    config = load_config()
    return config.get('my_domains', [])


# Convenience function for quick access
_cached_config = None


def get_config(reload: bool = False) -> Dict[str, Any]:
    """
    Get configuration (cached).

    Args:
        reload: Force reload from disk

    Returns:
        Configuration dictionary
    """
    global _cached_config

    if _cached_config is None or reload:
        _cached_config = load_config()

    return _cached_config


# CLI for testing
if __name__ == '__main__':
    import json

    print("=== ELF Configuration ===\n")

    config = load_config()
    print("Config:")
    print(json.dumps(config, indent=2))

    print("\n--- Custom Golden Rules ---")
    custom_rules = load_custom_golden_rules()
    if custom_rules:
        print(f"Found: {len(custom_rules)} chars")
    else:
        print("None found")

    print("\n--- All Parties ---")
    parties = load_all_parties()
    print(f"Total parties: {len(parties)}")
    for name in parties:
        print(f"  - {name}")
