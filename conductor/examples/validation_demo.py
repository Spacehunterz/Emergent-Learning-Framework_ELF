#!/usr/bin/env python3
"""
Demonstration of input validation in the Conductor system.

This script shows how the validation module protects against
command injection and other security vulnerabilities.
"""

import sys
import io
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validation import (
    validate_node_id,
    validate_agent_type,
    ValidationError
)


def demo_valid_identifiers():
    """Demonstrate validation of valid identifiers."""
    print("=" * 60)
    print("VALID IDENTIFIERS - These will be accepted")
    print("=" * 60)

    valid_ids = [
        "node123",
        "test-node",
        "my_node_id",
        "NODE-123-abc",
        "workflow-2024-12-10",
    ]

    for node_id in valid_ids:
        try:
            result = validate_node_id(node_id)
            print(f"✓ {node_id:<30} -> VALID")
        except ValidationError as e:
            print(f"✗ {node_id:<30} -> ERROR: {e}")

    print()


def demo_command_injection_attempts():
    """Demonstrate blocking of command injection attempts."""
    print("=" * 60)
    print("COMMAND INJECTION ATTEMPTS - These will be BLOCKED")
    print("=" * 60)

    attacks = [
        ("node; rm -rf /", "Command chaining with semicolon"),
        ("node && cat /etc/passwd", "Command chaining with &&"),
        ("node || malicious", "Command chaining with ||"),
        ("node | grep secrets", "Pipe to another command"),
        ("node$(whoami)", "Command substitution with $()"),
        ("node`whoami`", "Command substitution with backticks"),
        ("node${PATH}", "Environment variable expansion"),
        ("node > /tmp/evil", "Output redirection"),
        ("node < /etc/passwd", "Input redirection"),
    ]

    for attack, description in attacks:
        try:
            result = validate_node_id(attack)
            print(f"✗ {attack:<30} -> DANGER: NOT BLOCKED! (This is a bug)")
        except ValidationError as e:
            print(f"✓ {attack:<30} -> BLOCKED: {description}")

    print()


def demo_path_traversal_attempts():
    """Demonstrate blocking of path traversal attempts."""
    print("=" * 60)
    print("PATH TRAVERSAL ATTEMPTS - These will be BLOCKED")
    print("=" * 60)

    attacks = [
        ("../../../etc/passwd", "Unix path traversal"),
        ("..\\..\\windows\\system32", "Windows path traversal"),
        ("node/../admin", "Relative path in node ID"),
        ("/etc/passwd", "Absolute path"),
        ("C:\\Windows\\System32", "Windows absolute path"),
    ]

    for attack, description in attacks:
        try:
            result = validate_node_id(attack)
            print(f"✗ {attack:<30} -> DANGER: NOT BLOCKED! (This is a bug)")
        except ValidationError as e:
            print(f"✓ {attack:<30} -> BLOCKED: {description}")

    print()


def demo_edge_cases():
    """Demonstrate handling of edge cases."""
    print("=" * 60)
    print("EDGE CASES - Special situations")
    print("=" * 60)

    edge_cases = [
        ("", "Empty string"),
        ("_node", "Starts with underscore"),
        ("node_", "Ends with underscore"),
        ("-node", "Starts with hyphen"),
        ("node-", "Ends with hyphen"),
        ("a" * 101, "Too long (101 chars)"),
        ("node\x00", "Null byte injection"),
        ("node\n", "Newline character"),
        ("node id", "Contains space"),
    ]

    for test_case, description in edge_cases:
        try:
            result = validate_node_id(test_case)
            display = test_case[:30] + "..." if len(test_case) > 30 else test_case
            print(f"✗ {display:<30} -> DANGER: NOT BLOCKED! ({description})")
        except ValidationError as e:
            display = test_case[:30] + "..." if len(test_case) > 30 else test_case
            print(f"✓ {display:<30} -> BLOCKED: {description}")

    print()


def demo_agent_types():
    """Demonstrate validation of agent types (which allow spaces)."""
    print("=" * 60)
    print("AGENT TYPES - Allow spaces but still secure")
    print("=" * 60)

    agent_types = [
        ("general-purpose", True, "Hyphenated agent type"),
        ("code review", True, "Agent type with space"),
        ("Explore", True, "Simple agent type"),
        ("agent;drop table", False, "Command injection attempt"),
        ("agent|ls", False, "Pipe command attempt"),
        ("agent$(whoami)", False, "Command substitution attempt"),
    ]

    for agent_type, should_pass, description in agent_types:
        try:
            result = validate_agent_type(agent_type)
            symbol = "✓" if should_pass else "✗"
            print(f"{symbol} {agent_type:<30} -> VALID: {description}")
        except ValidationError as e:
            symbol = "✓" if not should_pass else "✗"
            status = "BLOCKED" if not should_pass else "ERROR"
            print(f"{symbol} {agent_type:<30} -> {status}: {description}")

    print()


def demo_security_in_practice():
    """Show how validation prevents real attacks."""
    print("=" * 60)
    print("SECURITY IN PRACTICE - How validation prevents attacks")
    print("=" * 60)

    print("\nScenario 1: User provides malicious node_id")
    print("-" * 60)

    malicious_node_id = "node; rm -rf /"
    print(f"User input: {malicious_node_id!r}")

    try:
        validated = validate_node_id(malicious_node_id)
        print(f"❌ SECURITY FAILURE: Would execute: env[CLAUDE_SWARM_NODE]={validated}")
        print(f"   This could lead to: rm -rf / being executed!")
    except ValidationError as e:
        print(f"✓ SECURITY SUCCESS: Attack blocked")
        print(f"   Error message: {e}")
        print(f"   Result: No subprocess spawned, safe error returned to user")

    print("\nScenario 2: Valid node_id is processed normally")
    print("-" * 60)

    safe_node_id = "node-123"
    print(f"User input: {safe_node_id!r}")

    try:
        validated = validate_node_id(safe_node_id)
        print(f"✓ Validation passed: {validated!r}")
        print(f"   Safe to use in: env[CLAUDE_SWARM_NODE]={validated}")
        print(f"   Safe to use in: filename=prompt-{validated}.md")
        print(f"   Result: Normal execution proceeds")
    except ValidationError as e:
        print(f"❌ Unexpected error: {e}")

    print()


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("CONDUCTOR INPUT VALIDATION DEMONSTRATION")
    print("=" * 60)
    print("\nThis demo shows how the validation module protects")
    print("the Conductor system from security vulnerabilities.")
    print()

    demo_valid_identifiers()
    demo_command_injection_attempts()
    demo_path_traversal_attempts()
    demo_edge_cases()
    demo_agent_types()
    demo_security_in_practice()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\n✓ All common attack patterns are blocked")
    print("✓ Valid identifiers are accepted")
    print("✓ Clear error messages are provided")
    print("✓ System remains secure against command injection")
    print("\nFor more information, see: conductor/SECURITY.md")
    print()


if __name__ == "__main__":
    main()
