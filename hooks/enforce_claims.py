#!/usr/bin/env python3
"""
Enforce Claims Hook: Intercept Edit/Write tool calls to enforce file claims.

This hook ensures that agents cannot modify files without first claiming them
via the claim chain system. It provides clear error messages when files are:
1. Not claimed at all
2. Claimed by a different agent

Auto-expires claims that have passed their TTL.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Add coordinator to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "coordinator"))

from blackboard import Blackboard, ClaimChain


@dataclass
class HookResult:
    """Result of a pre-tool hook."""
    allowed: bool
    message: Optional[str] = None

    @staticmethod
    def allow() -> 'HookResult':
        """Allow the tool call to proceed."""
        return HookResult(allowed=True)

    @staticmethod
    def deny(message: str) -> 'HookResult':
        """Deny the tool call with an error message."""
        return HookResult(allowed=False, message=message)


def get_current_agent_id() -> str:
    """Get the current agent ID from environment or generate one.

    In production, this should read from a session variable or environment.
    For now, we use AGENT_ID env var or fallback to a default.
    """
    return os.environ.get("AGENT_ID", "default-agent")


def get_project_root() -> str:
    """Get the project root directory.

    Looks for .coordination directory or uses current working directory.
    """
    cwd = Path.cwd()

    # Walk up the directory tree looking for .coordination
    current = cwd
    while current != current.parent:
        if (current / ".coordination").exists():
            return str(current)
        current = current.parent

    # Default to current working directory
    return str(cwd)


def pre_tool_use(tool_name: str, tool_input: Dict[str, Any]) -> HookResult:
    """Intercept Edit/Write tool calls and enforce claims.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Arguments to the tool

    Returns:
        HookResult indicating whether to allow or deny the operation
    """
    # Only intercept Edit and Write operations
    if tool_name not in ["Edit", "Write"]:
        return HookResult.allow()

    # Get the file path from tool input
    file_path = tool_input.get("file_path")
    if not file_path:
        # No file path specified - shouldn't happen, but allow it
        return HookResult.allow()

    # Get current agent ID and project root
    agent_id = get_current_agent_id()
    project_root = get_project_root()

    # Check if file is claimed
    try:
        bb = Blackboard(project_root)
        claim = bb.get_claim_for_file(file_path)

        if claim is None:
            # File not claimed by anyone
            return HookResult.deny(
                f"WARNING:  File not claimed: {file_path}\n\n"
                f"You must claim this file before editing it.\n\n"
                f"To claim this file and its dependencies:\n"
                f"  1. Use dependency graph to find related files:\n"
                f"     python coordinator/dependency_graph.py cluster {project_root} {file_path}\n\n"
                f"  2. Claim the files:\n"
                f"     bb.claim_chain(\n"
                f"         agent_id='{agent_id}',\n"
                f"         files=['{file_path}', ...],\n"
                f"         reason='Description of your changes'\n"
                f"     )\n"
            )

        if claim.agent_id != agent_id:
            # File claimed by different agent
            expires_in = (claim.expires_at - claim.claimed_at).total_seconds() / 60
            time_left = max(0, (claim.expires_at.timestamp() - claim.claimed_at.timestamp()) / 60)

            return HookResult.deny(
                f"WARNING:  File claimed by another agent: {file_path}\n\n"
                f"Claimed by: {claim.agent_id}\n"
                f"Reason: {claim.reason}\n"
                f"Chain ID: {claim.chain_id}\n"
                f"Claimed at: {claim.claimed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Expires at: {claim.expires_at.strftime('%Y-%m-%d %H:%M:%S')} (TTL: {expires_in:.1f} min)\n\n"
                f"Options:\n"
                f"  1. Wait for claim to expire (est. {time_left:.1f} min remaining)\n"
                f"  2. Coordinate with {claim.agent_id} to release the claim\n"
                f"  3. Work on a different task\n"
            )

        # File is claimed by this agent - allow the operation
        return HookResult.allow()

    except Exception as e:
        # If enforcement fails for any reason, log it but allow the operation
        # This prevents the hook from breaking agent workflows
        print(f"WARNING: Claim enforcement failed: {e}", file=sys.stderr)
        return HookResult.allow()


def post_tool_use(tool_name: str, tool_input: Dict[str, Any], tool_output: Any) -> None:
    """Called after a tool has been used successfully.

    Currently unused, but could be used for:
    - Automatic claim extension if work is still in progress
    - Logging of file modifications
    - Notification to other agents about changes
    """
    pass


# CLI interface for testing
if __name__ == "__main__":
    import json

    # Test the hook with sample inputs
    test_cases = [
        {
            "tool": "Read",
            "input": {"file_path": "test.py"},
            "expected": "allow"
        },
        {
            "tool": "Edit",
            "input": {"file_path": "unclaimed.py", "old_string": "x", "new_string": "y"},
            "expected": "deny"
        },
    ]

    print("Testing enforcement hook...\n")

    for i, test in enumerate(test_cases, 1):
        result = pre_tool_use(test["tool"], test["input"])
        status = "PASS" if (result.allowed and test["expected"] == "allow") or \
                           (not result.allowed and test["expected"] == "deny") else "FAIL"

        print(f"Test {i}: {status} {test['tool']} on {test['input'].get('file_path', 'N/A')}")
        if result.message:
            print(f"  Message: {result.message[:80]}...")
        print()
