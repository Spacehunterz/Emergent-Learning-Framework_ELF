"""
Frontmatter parser and writer for markdown files.

Handles YAML frontmatter in the format:
---
key: value
status: active
---
# Content starts here

This enables state tracking, metadata, and filtering for knowledge files.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Try to import yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Frontmatter delimiter
FRONTMATTER_PATTERN = re.compile(
    r'^---\s*\n(.*?)\n---\s*\n',
    re.DOTALL
)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown content including frontmatter

    Returns:
        Tuple of (frontmatter_dict, remaining_content)
        If no frontmatter, returns ({}, original_content)
    """
    match = FRONTMATTER_PATTERN.match(content)

    if not match:
        return {}, content

    frontmatter_text = match.group(1)
    remaining_content = content[match.end():]

    if YAML_AVAILABLE:
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if frontmatter is None:
                frontmatter = {}
            return frontmatter, remaining_content
        except yaml.YAMLError:
            return {}, content
    else:
        # Basic fallback parser
        return _basic_frontmatter_parse(frontmatter_text), remaining_content


def _basic_frontmatter_parse(text: str) -> Dict[str, Any]:
    """Basic fallback parser for frontmatter without PyYAML."""
    result = {}

    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            # Try to parse value types
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                try:
                    value = float(value)
                except ValueError:
                    pass
            elif value.startswith('[') and value.endswith(']'):
                # Basic list parsing
                value = [v.strip().strip('"\'') for v in value[1:-1].split(',') if v.strip()]
            elif value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            result[key] = value

    return result


def format_frontmatter(data: Dict[str, Any]) -> str:
    """
    Format a dictionary as YAML frontmatter.

    Args:
        data: Dictionary to format

    Returns:
        Formatted frontmatter string including delimiters
    """
    if not data:
        return ""

    if YAML_AVAILABLE:
        yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_content}---\n\n"
    else:
        # Basic fallback formatter
        lines = ["---"]
        for key, value in data.items():
            if isinstance(value, bool):
                value = str(value).lower()
            elif isinstance(value, list):
                value = '[' + ', '.join(str(v) for v in value) + ']'
            lines.append(f"{key}: {value}")
        lines.append("---\n")
        return '\n'.join(lines)


def add_frontmatter(content: str, data: Dict[str, Any]) -> str:
    """
    Add or replace frontmatter in markdown content.

    Args:
        content: Markdown content (may or may not have existing frontmatter)
        data: Frontmatter data to set

    Returns:
        Content with new frontmatter
    """
    _, body = parse_frontmatter(content)
    return format_frontmatter(data) + body


def update_frontmatter(content: str, updates: Dict[str, Any]) -> str:
    """
    Update specific frontmatter fields without replacing all of it.

    Args:
        content: Markdown content with frontmatter
        updates: Fields to update/add

    Returns:
        Content with updated frontmatter
    """
    existing, body = parse_frontmatter(content)
    existing.update(updates)
    return format_frontmatter(existing) + body


def get_frontmatter(content: str) -> Dict[str, Any]:
    """
    Get just the frontmatter from content.

    Args:
        content: Markdown content

    Returns:
        Frontmatter dictionary (empty if none)
    """
    frontmatter, _ = parse_frontmatter(content)
    return frontmatter


def read_file_with_frontmatter(path: Path) -> Tuple[Dict[str, Any], str]:
    """
    Read a file and parse its frontmatter.

    Args:
        path: Path to markdown file

    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter)
    """
    if not path.exists():
        return {}, ""

    content = path.read_text(encoding='utf-8')
    return parse_frontmatter(content)


def write_file_with_frontmatter(path: Path, frontmatter: Dict[str, Any], content: str) -> None:
    """
    Write a file with frontmatter.

    Args:
        path: Path to write to
        frontmatter: Frontmatter data
        content: Content (without frontmatter)
    """
    full_content = format_frontmatter(frontmatter) + content
    path.write_text(full_content, encoding='utf-8')


def update_file_frontmatter(path: Path, updates: Dict[str, Any]) -> bool:
    """
    Update frontmatter in an existing file.

    Args:
        path: Path to file
        updates: Fields to update

    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return False

    try:
        content = path.read_text(encoding='utf-8')
        updated = update_frontmatter(content, updates)
        path.write_text(updated, encoding='utf-8')
        return True
    except Exception:
        return False


# === Standard frontmatter templates ===

def create_learning_frontmatter(
    status: str = 'active',
    confidence: float = 0.5,
    domain: str = 'general',
    tags: list = None,
    related: list = None
) -> Dict[str, Any]:
    """Create standard frontmatter for a learning."""
    return {
        'status': status,
        'confidence': confidence,
        'domain': domain,
        'tags': tags or [],
        'related': related or [],
        'created': datetime.now().strftime('%Y-%m-%d'),
        'updated': datetime.now().strftime('%Y-%m-%d'),
    }


def create_decision_frontmatter(
    status: str = 'pending',
    priority: str = 'medium',
    domain: str = None,
    assignee: str = None
) -> Dict[str, Any]:
    """Create standard frontmatter for a CEO decision."""
    data = {
        'status': status,
        'priority': priority,
        'created': datetime.now().strftime('%Y-%m-%d'),
    }
    if domain:
        data['domain'] = domain
    if assignee:
        data['assignee'] = assignee
    return data


def create_session_frontmatter(
    status: str = 'in_progress',
    checkpoint: str = None,
    task: str = None
) -> Dict[str, Any]:
    """Create standard frontmatter for a session file."""
    data = {
        'status': status,
        'started': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'updated': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
    }
    if checkpoint:
        data['checkpoint'] = checkpoint
    if task:
        data['task'] = task
    return data


# === Query helpers ===

def find_files_by_status(directory: Path, status: str) -> list:
    """
    Find all markdown files with a specific status in frontmatter.

    Args:
        directory: Directory to search
        status: Status to match

    Returns:
        List of paths with matching status
    """
    matches = []

    for path in directory.glob('**/*.md'):
        try:
            frontmatter, _ = read_file_with_frontmatter(path)
            if frontmatter.get('status') == status:
                matches.append(path)
        except Exception:
            continue

    return matches


def find_files_by_frontmatter(directory: Path, **criteria) -> list:
    """
    Find files matching frontmatter criteria.

    Args:
        directory: Directory to search
        **criteria: Key-value pairs to match

    Returns:
        List of paths matching all criteria
    """
    matches = []

    for path in directory.glob('**/*.md'):
        try:
            frontmatter, _ = read_file_with_frontmatter(path)
            if all(frontmatter.get(k) == v for k, v in criteria.items()):
                matches.append(path)
        except Exception:
            continue

    return matches


# CLI for testing
if __name__ == '__main__':
    # Test parsing
    test_content = """---
status: active
priority: high
tags: [test, example]
count: 42
---

# Test Document

This is the content.
"""

    print("=== Frontmatter Parser Test ===\n")

    frontmatter, content = parse_frontmatter(test_content)
    print("Parsed frontmatter:")
    print(f"  {frontmatter}")
    print(f"\nContent preview: {content[:50]}...")

    # Test update
    updated = update_frontmatter(test_content, {'status': 'reviewed', 'reviewer': 'claude'})
    new_fm, _ = parse_frontmatter(updated)
    print(f"\nAfter update: {new_fm}")

    # Test formatting
    print("\n=== Format Test ===")
    print(format_frontmatter({'status': 'new', 'tags': ['a', 'b']}))
