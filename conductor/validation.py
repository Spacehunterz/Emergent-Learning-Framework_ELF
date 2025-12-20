#!/usr/bin/env python3
"""
Input validation utilities for the Conductor system.

Provides validation functions to prevent command injection and other security issues
when handling user-provided identifiers like node_id, workflow_id, run_id, etc.
"""

import re


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_identifier(value: str, name: str = "identifier", max_length: int = 100) -> str:
    """
    Validate that an identifier contains only safe characters.

    Ensures the identifier:
    - Contains only alphanumeric characters, underscores, or hyphens
    - Is not empty
    - Does not exceed maximum length
    - Does not start or end with special characters

    Args:
        value: The identifier to validate
        name: Human-readable name for error messages (e.g., "node_id")
        max_length: Maximum allowed length (default: 100)

    Returns:
        The validated identifier (unchanged if valid)

    Raises:
        ValidationError: If the identifier is invalid

    Examples:
        >>> validate_identifier("node-123", "node_id")
        'node-123'
        >>> validate_identifier("valid_node_id_123", "node_id")
        'valid_node_id_123'
        >>> validate_identifier("invalid;id", "node_id")
        ValidationError: Invalid node_id: must contain only alphanumeric, underscore, or hyphen
    """
    if not value:
        raise ValidationError(f"Invalid {name}: cannot be empty")

    if not isinstance(value, str):
        raise ValidationError(f"Invalid {name}: must be a string")

    if len(value) > max_length:
        raise ValidationError(f"Invalid {name}: too long (max {max_length} chars, got {len(value)})")

    # Only allow alphanumeric, underscore, and hyphen
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValidationError(
            f"Invalid {name}: must contain only alphanumeric, underscore, or hyphen (got: {value!r})"
        )

    # Prevent identifiers that start or end with special characters (good practice)
    if value[0] in '-_' or value[-1] in '-_':
        raise ValidationError(f"Invalid {name}: cannot start or end with hyphen or underscore")

    return value


def validate_node_id(node_id: str) -> str:
    """
    Validate a node ID.

    Args:
        node_id: The node ID to validate

    Returns:
        The validated node ID

    Raises:
        ValidationError: If the node ID is invalid
    """
    return validate_identifier(node_id, "node_id", max_length=100)


def validate_workflow_id(workflow_id: str) -> str:
    """
    Validate a workflow ID.

    Args:
        workflow_id: The workflow ID to validate

    Returns:
        The validated workflow ID

    Raises:
        ValidationError: If the workflow ID is invalid
    """
    return validate_identifier(workflow_id, "workflow_id", max_length=100)


def validate_run_id(run_id: str) -> str:
    """
    Validate a run ID.

    Args:
        run_id: The run ID to validate

    Returns:
        The validated run ID

    Raises:
        ValidationError: If the run ID is invalid
    """
    return validate_identifier(run_id, "run_id", max_length=100)


def validate_agent_id(agent_id: str) -> str:
    """
    Validate an agent ID.

    Args:
        agent_id: The agent ID to validate

    Returns:
        The validated agent ID

    Raises:
        ValidationError: If the agent ID is invalid
    """
    return validate_identifier(agent_id, "agent_id", max_length=100)


def validate_agent_type(agent_type: str) -> str:
    """
    Validate an agent type string.

    Agent types can contain alphanumeric, underscores, hyphens, and spaces.

    Args:
        agent_type: The agent type to validate

    Returns:
        The validated agent type

    Raises:
        ValidationError: If the agent type is invalid
    """
    if not agent_type:
        raise ValidationError("Invalid agent_type: cannot be empty")

    if not isinstance(agent_type, str):
        raise ValidationError("Invalid agent_type: must be a string")

    if len(agent_type) > 50:
        raise ValidationError(f"Invalid agent_type: too long (max 50 chars, got {len(agent_type)})")

    # Allow alphanumeric, spaces, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9 _-]+$', agent_type):
        raise ValidationError(
            f"Invalid agent_type: must contain only alphanumeric, spaces, underscores, or hyphens (got: {agent_type!r})"
        )

    return agent_type


def validate_filename_safe(filename: str, name: str = "filename") -> str:
    """
    Validate a filename for safe filesystem operations.

    Ensures the filename:
    - Does not contain path separators or traversal sequences
    - Contains only safe characters
    - Is not empty
    - Is not a reserved name

    Args:
        filename: The filename to validate
        name: Human-readable name for error messages

    Returns:
        The validated filename

    Raises:
        ValidationError: If the filename is invalid
    """
    if not filename:
        raise ValidationError(f"Invalid {name}: cannot be empty")

    if not isinstance(filename, str):
        raise ValidationError(f"Invalid {name}: must be a string")

    if len(filename) > 255:
        raise ValidationError(f"Invalid {name}: too long (max 255 chars)")

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValidationError(f"Invalid {name}: cannot contain path separators or traversal sequences")

    # Check for reserved names on Windows
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                     'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                     'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    base_name = filename.split('.')[0].upper()
    if base_name in reserved_names:
        raise ValidationError(f"Invalid {name}: cannot use reserved name '{filename}'")

    # Only allow safe filename characters
    if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
        raise ValidationError(
            f"Invalid {name}: must contain only alphanumeric, underscore, hyphen, or period (got: {filename!r})"
        )

    return filename
