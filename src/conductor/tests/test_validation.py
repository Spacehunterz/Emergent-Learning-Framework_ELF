#!/usr/bin/env python3
"""
Tests for input validation utilities.

Tests the validation functions to ensure they properly reject malicious input
and accept valid identifiers.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validation import (
    validate_identifier,
    validate_node_id,
    validate_workflow_id,
    validate_run_id,
    validate_agent_id,
    validate_agent_type,
    validate_filename_safe,
    ValidationError
)


class TestValidation(unittest.TestCase):
    """Test validation functions."""

    def test_valid_identifiers(self):
        """Test that valid identifiers pass validation."""
        valid_ids = [
            "node123",
            "node-123",
            "node_123",
            "Node123",
            "NODE123",
            "a1b2c3",
            "test-node-id",
            "test_node_id",
            "node123abc",
        ]
        for valid_id in valid_ids:
            with self.subTest(valid_id=valid_id):
                result = validate_identifier(valid_id, "test_id")
                self.assertEqual(result, valid_id)

    def test_invalid_identifiers_special_chars(self):
        """Test that identifiers with special characters are rejected."""
        invalid_ids = [
            "node;id",           # Semicolon (command separator)
            "node|id",           # Pipe (command chaining)
            "node&id",           # Ampersand (background execution)
            "node$id",           # Dollar sign (variable expansion)
            "node`id`",          # Backticks (command substitution)
            "node$(id)",         # Command substitution
            "node id",           # Space
            "node'id",           # Single quote
            'node"id',           # Double quote
            "node\\id",          # Backslash
            "node/id",           # Forward slash
            "node\nid",          # Newline
            "node\tid",          # Tab
            "node<id",           # Less than
            "node>id",           # Greater than
            "node*id",           # Asterisk
            "node?id",           # Question mark
            "node[id]",          # Brackets
            "node{id}",          # Braces
            "node(id)",          # Parentheses
            "../node",           # Path traversal
            "../../etc/passwd",  # Path traversal attack
        ]
        for invalid_id in invalid_ids:
            with self.subTest(invalid_id=invalid_id):
                with self.assertRaises(ValidationError):
                    validate_identifier(invalid_id, "test_id")

    def test_invalid_identifiers_edge_cases(self):
        """Test edge cases for identifier validation."""
        # Empty string
        with self.assertRaises(ValidationError):
            validate_identifier("", "test_id")

        # Starts with hyphen
        with self.assertRaises(ValidationError):
            validate_identifier("-node", "test_id")

        # Ends with hyphen
        with self.assertRaises(ValidationError):
            validate_identifier("node-", "test_id")

        # Starts with underscore
        with self.assertRaises(ValidationError):
            validate_identifier("_node", "test_id")

        # Ends with underscore
        with self.assertRaises(ValidationError):
            validate_identifier("node_", "test_id")

        # Too long
        with self.assertRaises(ValidationError):
            validate_identifier("a" * 101, "test_id")

        # Not a string
        with self.assertRaises(ValidationError):
            validate_identifier(123, "test_id")

    def test_specific_id_validators(self):
        """Test specific ID validators (node_id, workflow_id, etc.)."""
        # Valid IDs
        self.assertEqual(validate_node_id("node123"), "node123")
        self.assertEqual(validate_workflow_id("workflow-1"), "workflow-1")
        self.assertEqual(validate_run_id("run-abc-123"), "run-abc-123")
        self.assertEqual(validate_agent_id("agent-scout-0"), "agent-scout-0")

        # Invalid IDs
        with self.assertRaises(ValidationError):
            validate_node_id("node;drop table")

        with self.assertRaises(ValidationError):
            validate_workflow_id("workflow`cmd`")

        with self.assertRaises(ValidationError):
            validate_run_id("run$(whoami)")

        with self.assertRaises(ValidationError):
            validate_agent_id("agent|ls")

    def test_agent_type_validation(self):
        """Test agent type validation (allows spaces)."""
        # Valid agent types
        valid_types = [
            "general-purpose",
            "Explore",
            "code-review",
            "data analysis",
            "Test Agent",
            "agent_123",
        ]
        for agent_type in valid_types:
            with self.subTest(agent_type=agent_type):
                result = validate_agent_type(agent_type)
                self.assertEqual(result, agent_type)

        # Invalid agent types
        invalid_types = [
            "agent;type",
            "agent|type",
            "agent$type",
            "agent`type`",
            "agent/type",
            "agent\\type",
            "agent\ntype",
            "",
            "a" * 51,  # Too long
        ]
        for agent_type in invalid_types:
            with self.subTest(agent_type=agent_type):
                with self.assertRaises(ValidationError):
                    validate_agent_type(agent_type)

    def test_filename_validation(self):
        """Test filename validation."""
        # Valid filenames
        valid_filenames = [
            "file.txt",
            "file-123.json",
            "file_name.py",
            "my-file.md",
            "script.sh",
            "data.csv",
        ]
        for filename in valid_filenames:
            with self.subTest(filename=filename):
                result = validate_filename_safe(filename)
                self.assertEqual(result, filename)

        # Invalid filenames
        invalid_filenames = [
            "../etc/passwd",      # Path traversal
            "../../file.txt",     # Path traversal
            "dir/file.txt",       # Path separator
            "dir\\file.txt",      # Path separator (Windows)
            "file;name.txt",      # Semicolon
            "file|name.txt",      # Pipe
            "file$name.txt",      # Dollar sign
            "file`name`.txt",     # Backticks
            "file name.txt",      # Space (could be problematic)
            "CON",                # Reserved name (Windows)
            "PRN",                # Reserved name (Windows)
            "AUX",                # Reserved name (Windows)
            "NUL",                # Reserved name (Windows)
            "COM1",               # Reserved name (Windows)
            "LPT1",               # Reserved name (Windows)
            "",                   # Empty
            "a" * 256,            # Too long
        ]
        for filename in invalid_filenames:
            with self.subTest(filename=filename):
                with self.assertRaises(ValidationError):
                    validate_filename_safe(filename)

    def test_command_injection_attempts(self):
        """Test that common command injection attempts are blocked."""
        injection_attempts = [
            # Command chaining
            "node; rm -rf /",
            "node && rm -rf /",
            "node || rm -rf /",
            "node | cat /etc/passwd",

            # Command substitution
            "node$(whoami)",
            "node`whoami`",
            "node${PATH}",

            # Environment variable injection
            "node$PATH",
            "node${USER}",

            # File operations
            "node > /tmp/evil",
            "node < /etc/passwd",
            "node >> /tmp/evil",

            # Path traversal
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",

            # Null byte injection
            "node\x00",

            # Newline injection
            "node\nrm -rf /",
            "node\r\nrm -rf /",
        ]

        for attempt in injection_attempts:
            with self.subTest(attempt=attempt):
                with self.assertRaises(ValidationError):
                    validate_identifier(attempt, "test_id")


class TestValidationErrorMessages(unittest.TestCase):
    """Test that validation error messages are helpful."""

    def test_error_messages_include_field_name(self):
        """Test that error messages include the field name."""
        try:
            validate_identifier("invalid;id", "node_id")
            self.fail("Should have raised ValidationError")
        except ValidationError as e:
            self.assertIn("node_id", str(e))

    def test_error_messages_describe_issue(self):
        """Test that error messages describe the issue."""
        try:
            validate_identifier("invalid|id", "test_id")
            self.fail("Should have raised ValidationError")
        except ValidationError as e:
            self.assertIn("alphanumeric", str(e).lower())

        try:
            validate_identifier("", "test_id")
            self.fail("Should have raised ValidationError")
        except ValidationError as e:
            self.assertIn("empty", str(e).lower())

        try:
            validate_identifier("a" * 101, "test_id")
            self.fail("Should have raised ValidationError")
        except ValidationError as e:
            self.assertIn("too long", str(e).lower())


if __name__ == "__main__":
    unittest.main()
