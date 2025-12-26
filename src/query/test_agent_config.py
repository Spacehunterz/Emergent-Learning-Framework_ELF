"""
Unit tests for agent_config.py

Tests the agent configuration loading, merging, and formatting functionality.
"""

import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timezone

# Import the module under test
try:
    from query.agent_config import (
        get_default_agent_config,
        load_agent_config,
        get_config_value,
        format_config_for_context,
        load_yaml_safe,
        get_global_agent_config_path,
        get_project_agent_config_path,
    )
except ImportError:
    from agent_config import (
        get_default_agent_config,
        load_agent_config,
        get_config_value,
        format_config_for_context,
        load_yaml_safe,
        get_global_agent_config_path,
        get_project_agent_config_path,
    )


class TestGetDefaultAgentConfig(unittest.TestCase):
    """Test default configuration structure."""

    def test_get_default_agent_config(self):
        """Verify default structure has all required keys."""
        config = get_default_agent_config()

        # Check top-level keys
        assert 'defaults' in config
        assert 'category_weights' in config
        assert 'disabled_agents' in config
        assert 'always_include' in config
        assert 'tier_overrides' in config
        assert 'phase_weights' in config
        assert 'complexity_requirements' in config

        # Check nested structures
        assert 'max_agents' in config['defaults']
        assert 'prefer_tier' in config['defaults']

        assert 'security' in config['category_weights']
        assert 'testing' in config['category_weights']
        assert 'documentation' in config['category_weights']

        assert isinstance(config['disabled_agents'], list)
        assert isinstance(config['always_include'], dict)
        assert isinstance(config['tier_overrides'], dict)

        # Check phase_weights structure
        assert 'plan' in config['phase_weights']
        assert 'execute' in config['phase_weights']
        assert 'review' in config['phase_weights']

        assert 'opus' in config['phase_weights']['plan']
        assert 'sonnet' in config['phase_weights']['plan']
        assert 'haiku' in config['phase_weights']['plan']

        # Check complexity_requirements
        assert 'critical' in config['complexity_requirements']
        assert 'high' in config['complexity_requirements']
        assert 'medium' in config['complexity_requirements']
        assert 'low' in config['complexity_requirements']

    def test_default_config_values(self):
        """Verify default configuration has expected values."""
        config = get_default_agent_config()

        # Check specific default values
        assert config['defaults']['max_agents'] is None
        assert config['defaults']['prefer_tier'] is None

        assert config['category_weights']['security'] == 1.5
        assert config['category_weights']['testing'] == 1.2
        assert config['category_weights']['documentation'] == 0.8

        assert config['complexity_requirements']['critical'] == 'opus'
        assert config['complexity_requirements']['high'] == 'sonnet'
        assert config['complexity_requirements']['medium'] is None
        assert config['complexity_requirements']['low'] is None


class TestLoadAgentConfig(unittest.TestCase):
    """Test configuration loading and merging."""

    def setUp(self):
        """Clear cache before each test."""
        load_agent_config.cache_clear()

    def test_load_agent_config_returns_tuple(self):
        """Verify load_agent_config returns (dict, str) tuple."""
        result = load_agent_config()

        assert isinstance(result, tuple)
        assert len(result) == 2

        config, source = result
        assert isinstance(config, dict)
        assert isinstance(source, str)

    def test_load_agent_config_source_types(self):
        """Verify source is one of the expected types."""
        config, source = load_agent_config()

        # Source can include "(validation-repaired)" suffix
        valid_base_sources = ['global', 'project', 'merged (global + project)', 'defaults']
        base_source = source.replace(' (validation-repaired)', '')
        assert base_source in valid_base_sources

    @patch('agent_config.load_yaml_safe')
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    def test_load_agent_config_global_only(self, mock_project_path, mock_global_path, mock_load_yaml):
        """Test loading when only global config exists."""
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = None

        # Provide complete config that passes validation
        global_config = get_default_agent_config()
        global_config['defaults']['max_agents'] = 5
        mock_load_yaml.side_effect = [global_config, None]

        config, source = load_agent_config()

        assert source == 'global'
        assert config['defaults']['max_agents'] == 5

    @patch('agent_config.load_yaml_safe')
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    def test_load_agent_config_project_only(self, mock_project_path, mock_global_path, mock_load_yaml):
        """Test loading when only project config exists."""
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = Path('/fake/project/agents.yaml')

        # Provide complete config that passes validation
        project_config = get_default_agent_config()
        project_config['defaults']['max_agents'] = 3
        mock_load_yaml.side_effect = [None, project_config]

        config, source = load_agent_config()

        assert source == 'project'
        assert config['defaults']['max_agents'] == 3

    @patch('agent_config.load_yaml_safe')
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    @patch('agent_config.deep_merge')
    def test_load_agent_config_merged(self, mock_deep_merge, mock_project_path, mock_global_path, mock_load_yaml):
        """Test loading when both configs exist and merge."""
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = Path('/fake/project/agents.yaml')

        # Provide complete configs that pass validation
        global_config = get_default_agent_config()
        global_config['defaults']['max_agents'] = 5
        project_config = get_default_agent_config()
        project_config['defaults']['prefer_tier'] = 'opus'
        merged_config = get_default_agent_config()
        merged_config['defaults']['max_agents'] = 5
        merged_config['defaults']['prefer_tier'] = 'opus'

        mock_load_yaml.side_effect = [global_config, project_config]
        mock_deep_merge.return_value = merged_config

        config, source = load_agent_config()

        assert source == 'merged (global + project)'
        assert config['defaults']['max_agents'] == 5
        assert config['defaults']['prefer_tier'] == 'opus'
        mock_deep_merge.assert_called_once_with(global_config, project_config)

    @patch('agent_config.load_yaml_safe')
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    def test_load_agent_config_defaults_fallback(self, mock_project_path, mock_global_path, mock_load_yaml):
        """Test fallback to defaults when no configs exist."""
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = None

        mock_load_yaml.side_effect = [None, None]

        config, source = load_agent_config()

        assert source == 'defaults'
        # Should return the default config
        assert 'defaults' in config
        assert 'category_weights' in config


class TestGetConfigValue(unittest.TestCase):
    """Test dot-notation config value retrieval."""

    @patch('agent_config.load_agent_config')
    def test_get_config_value_dot_notation(self, mock_load):
        """Test dot path access to nested config values."""
        mock_config = {
            'phase_weights': {
                'plan': {
                    'opus': 2.0,
                    'sonnet': 1.5,
                    'haiku': 0.5
                }
            },
            'category_weights': {
                'security': 1.5
            }
        }
        mock_load.return_value = (mock_config, 'global')

        # Test nested access
        assert get_config_value('phase_weights.plan.opus') == 2.0
        assert get_config_value('phase_weights.plan.sonnet') == 1.5
        assert get_config_value('category_weights.security') == 1.5

        # Test top-level access
        assert get_config_value('phase_weights') == mock_config['phase_weights']

    @patch('agent_config.load_agent_config')
    def test_get_config_value_missing_key(self, mock_load):
        """Test that missing keys return default value."""
        mock_config = {
            'phase_weights': {
                'plan': {
                    'opus': 2.0
                }
            }
        }
        mock_load.return_value = (mock_config, 'global')

        # Test missing keys with default
        assert get_config_value('nonexistent.key', default='fallback') == 'fallback'
        assert get_config_value('phase_weights.missing', default=None) is None
        assert get_config_value('phase_weights.plan.missing', default=0) == 0

    @patch('agent_config.load_agent_config')
    def test_get_config_value_no_default(self, mock_load):
        """Test that missing keys return None when no default specified."""
        mock_config = {'key': 'value'}
        mock_load.return_value = (mock_config, 'global')

        assert get_config_value('nonexistent') is None


class TestFormatConfigForContext(unittest.TestCase):
    """Test configuration formatting for context output."""

    @patch('agent_config.YAML_AVAILABLE', True)
    @patch('agent_config.yaml')
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    def test_format_config_for_context_output(self, mock_project_path, mock_global_path, mock_yaml, ):
        """Verify output contains expected markers and structure."""
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = None
        mock_yaml.dump.return_value = "max_agents: 5\n"

        config = {'defaults': {'max_agents': 5}}
        source = 'global'

        output = format_config_for_context(config, source, include_metadata=True)

        # Check for expected markers
        assert '# AGENT CONFIGURATION (Session-Loaded)' in output
        assert '```yaml' in output
        assert '**Config Source:** global' in output
        assert '**Loaded at:**' in output

        # Check timestamp format (should be ISO 8601 UTC)
        assert 'T' in output  # ISO format separator
        assert 'Z' in output  # UTC indicator

    @patch('agent_config.YAML_AVAILABLE', True)
    @patch('agent_config.yaml')
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    def test_format_config_without_metadata(self, mock_project_path, mock_global_path, mock_yaml):
        """Test formatting without metadata section."""
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = None
        mock_yaml.dump.return_value = "max_agents: 5\n"

        config = {'defaults': {'max_agents': 5}}
        source = 'global'

        output = format_config_for_context(config, source, include_metadata=False)

        # Should have main content
        assert '# AGENT CONFIGURATION (Session-Loaded)' in output
        assert '```yaml' in output

        # Should NOT have metadata
        assert '**Config Source:**' not in output
        assert '**Loaded at:**' not in output

    @patch('agent_config.YAML_AVAILABLE', False)
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    def test_format_config_without_yaml(self, mock_project_path, mock_global_path):
        """Test fallback formatting when YAML module not available."""
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = None

        config = {'defaults': {'max_agents': 5}}
        source = 'global'

        output = format_config_for_context(config, source, include_metadata=False)

        # Should still have config block, but not YAML-specific
        assert '# AGENT CONFIGURATION (Session-Loaded)' in output
        assert '```' in output
        # Should use text formatting instead
        assert 'defaults:' in output


class TestLoadYamlSafe(unittest.TestCase):
    """Test safe YAML loading functionality."""

    def test_load_yaml_safe_missing_file(self):
        """Test that missing file returns None."""
        result = load_yaml_safe(Path('/nonexistent/file.yaml'))
        assert result is None

    @patch('agent_config.YAML_AVAILABLE', True)
    @patch('builtins.open', new_callable=mock_open, read_data='key: value\n')
    @patch('agent_config.yaml')
    def test_load_yaml_safe_valid_yaml(self, mock_yaml, mock_file):
        """Test loading valid YAML file."""
        mock_yaml.safe_load.return_value = {'key': 'value'}

        fake_path = Path('/fake/config.yaml')
        with patch.object(Path, 'exists', return_value=True):
            result = load_yaml_safe(fake_path)

        assert result == {'key': 'value'}

    @patch('agent_config.YAML_AVAILABLE', True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('agent_config.yaml')
    def test_load_yaml_safe_invalid_yaml(self, mock_yaml, mock_file):
        """Test that invalid YAML returns None."""
        # Simulate YAML parsing error
        mock_yaml.safe_load.side_effect = Exception("Invalid YAML")

        fake_path = Path('/fake/bad.yaml')
        with patch.object(Path, 'exists', return_value=True):
            result = load_yaml_safe(fake_path)

        assert result is None

    @patch('agent_config.YAML_AVAILABLE', True)
    @patch('builtins.open', new_callable=mock_open, read_data='just a string\n')
    @patch('agent_config.yaml')
    def test_load_yaml_safe_non_dict_yaml(self, mock_yaml, mock_file):
        """Test that non-dict YAML content returns None."""
        # YAML parses to a string instead of dict
        mock_yaml.safe_load.return_value = "just a string"

        fake_path = Path('/fake/string.yaml')
        with patch.object(Path, 'exists', return_value=True):
            result = load_yaml_safe(fake_path)

        assert result is None

    @patch('agent_config.YAML_AVAILABLE', False)
    def test_load_yaml_safe_no_yaml_module(self):
        """Test that missing YAML module returns None."""
        fake_path = Path('/fake/config.yaml')
        with patch.object(Path, 'exists', return_value=True):
            result = load_yaml_safe(fake_path)

        assert result is None


class TestPathGetters(unittest.TestCase):
    """Test path getter functions."""

    @patch('agent_config.get_base_path')
    def test_get_global_agent_config_path(self, mock_base_path):
        """Test global config path construction."""
        mock_base_path.return_value = Path('/home/user/.claude/emergent-learning')

        result = get_global_agent_config_path()

        assert result == Path('/home/user/.claude/emergent-learning/agent_selector/config.yaml')

    @patch('os.getcwd')
    def test_get_project_agent_config_path_exists(self, mock_getcwd):
        """Test project config path when .elf/agents.yaml exists."""
        mock_getcwd.return_value = '/fake/project'

        fake_path = Path('/fake/project/.elf/agents.yaml')
        with patch.object(Path, 'exists', return_value=True):
            result = get_project_agent_config_path()

        assert result == fake_path

    @patch('os.getcwd')
    def test_get_project_agent_config_path_missing(self, mock_getcwd):
        """Test project config path when .elf/agents.yaml doesn't exist."""
        mock_getcwd.return_value = '/fake/project'

        with patch.object(Path, 'exists', return_value=False):
            result = get_project_agent_config_path()

        assert result is None


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows."""

    @patch('agent_config.load_agent_config')
    @patch('agent_config.get_global_agent_config_path')
    @patch('agent_config.get_project_agent_config_path')
    @patch('agent_config.YAML_AVAILABLE', True)
    @patch('agent_config.yaml')
    def test_full_workflow_with_config(self, mock_yaml, mock_project_path, mock_global_path, mock_load):
        """Test complete workflow from loading to formatting."""
        # Setup
        mock_global_path.return_value = Path('/fake/global/config.yaml')
        mock_project_path.return_value = None

        config = get_default_agent_config()
        mock_load.return_value = (config, 'global')
        mock_yaml.dump.return_value = "defaults:\n  max_agents: null\n"

        # Execute
        output = format_config_for_context(config, 'global', include_metadata=True)

        # Verify
        assert '# AGENT CONFIGURATION (Session-Loaded)' in output
        assert '```yaml' in output
        assert '**Config Source:** global' in output

    def test_default_config_completeness(self):
        """Verify default config has all necessary fields for operation."""
        config = get_default_agent_config()

        # Verify critical operational fields exist
        assert config['defaults']['max_agents'] is None  # Unlimited by default
        assert config['defaults']['prefer_tier'] is None  # No preference by default

        # Verify all phases have weights
        for phase in ['plan', 'execute', 'review']:
            assert phase in config['phase_weights']
            for tier in ['opus', 'sonnet', 'haiku']:
                assert tier in config['phase_weights'][phase]
                assert isinstance(config['phase_weights'][phase][tier], (int, float))

        # Verify complexity requirements are sensible
        assert config['complexity_requirements']['critical'] == 'opus'
        assert config['complexity_requirements']['high'] == 'sonnet'


# Run tests if executed directly
if __name__ == '__main__':
    unittest.main(verbosity=2)
