#!/usr/bin/env python3
"""
Test suite for claim chain functionality.

Tests:
1. Claim chain succeeds when files are free
2. Claim chain fails atomically when any file is taken
3. Chains auto-expire after TTL
4. Release chain frees all files
5. Blocking info is returned correctly
6. Multiple agents cannot claim overlapping files
7. Same agent can claim files in multiple non-overlapping chains
"""

import sys
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add coordinator to path
sys.path.insert(0, str(Path(__file__).parent.parent / "coordinator"))

from blackboard import Blackboard, ClaimChain, BlockedError
import pytest


def normalize_path(path: str) -> str:
    """Normalize path separators for cross-platform testing."""
    return str(Path(path))


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_claim_chains_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def blackboard(temp_project):
    """Create a blackboard instance for testing."""
    return Blackboard(temp_project)


class TestClaimChainBasics:
    """Test basic claim chain operations."""

    def test_claim_single_file(self, blackboard):
        """Test claiming a single file."""
        chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="Refactoring main module"
        )

        assert chain.agent_id == "agent-1"
        assert normalize_path("src/main.py") in chain.files
        assert chain.status == "active"
        assert chain.reason == "Refactoring main module"

    def test_claim_multiple_files(self, blackboard):
        """Test claiming multiple files in one chain."""
        files = ["src/auth.py", "src/user.py", "tests/test_auth.py"]
        chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=files,
            reason="Implementing authentication"
        )

        assert len(chain.files) == 3
        for f in files:
            assert normalize_path(f) in chain.files

    def test_claim_with_custom_ttl(self, blackboard):
        """Test that custom TTL is respected."""
        ttl = 60  # 60 minutes
        chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="Long task",
            ttl_minutes=ttl
        )

        expected_expiry = chain.claimed_at + timedelta(minutes=ttl)
        # Allow 1 second tolerance for timing
        assert abs((chain.expires_at - expected_expiry).total_seconds()) < 1

    def test_get_claim_for_file(self, blackboard):
        """Test retrieving claim by file path."""
        files = ["src/auth.py", "src/user.py"]
        original_chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=files,
            reason="Test"
        )

        # Should find claim for both files
        for f in files:
            claim = blackboard.get_claim_for_file(f)
            assert claim is not None
            assert claim.chain_id == original_chain.chain_id
            assert claim.agent_id == "agent-1"

        # Should not find claim for unclaimed file
        claim = blackboard.get_claim_for_file("src/unclaimed.py")
        assert claim is None


class TestClaimConflicts:
    """Test conflict detection and blocking."""

    def test_cannot_claim_already_claimed_file(self, blackboard):
        """Test that claiming an already-claimed file raises BlockedError."""
        # Agent 1 claims a file
        blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="First claim"
        )

        # Agent 2 tries to claim the same file
        with pytest.raises(BlockedError) as exc_info:
            blackboard.claim_chain(
                agent_id="agent-2",
                files=["src/main.py"],
                reason="Second claim"
            )

        error = exc_info.value
        assert len(error.blocking_chains) == 1
        assert normalize_path("src/main.py") in error.conflicting_files

    def test_atomic_claim_failure(self, blackboard):
        """Test that claim fails atomically - all or nothing."""
        # Agent 1 claims one file
        blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/auth.py"],
            reason="Auth work"
        )

        # Agent 2 tries to claim multiple files, one of which conflicts
        files_to_claim = ["src/auth.py", "src/user.py", "src/db.py"]
        with pytest.raises(BlockedError):
            blackboard.claim_chain(
                agent_id="agent-2",
                files=files_to_claim,
                reason="Should fail"
            )

        # Verify that NONE of the files were claimed by agent-2
        for f in ["src/user.py", "src/db.py"]:
            claim = blackboard.get_claim_for_file(f)
            assert claim is None, f"{f} should not be claimed after atomic failure"

    def test_partial_overlap_blocks_claim(self, blackboard):
        """Test that partial file overlap blocks the claim."""
        # Agent 1 claims some files
        blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/auth.py", "src/user.py"],
            reason="Auth module"
        )

        # Agent 2 tries to claim files with partial overlap
        with pytest.raises(BlockedError) as exc_info:
            blackboard.claim_chain(
                agent_id="agent-2",
                files=["src/user.py", "src/db.py"],
                reason="User module"
            )

        error = exc_info.value
        assert normalize_path("src/user.py") in error.conflicting_files
        # src/db.py should NOT be in conflicting files (it wasn't claimed)
        assert "src/db.py" not in error.conflicting_files

    def test_same_agent_can_claim_twice(self, blackboard):
        """Test that the same agent can claim files they already own."""
        # This might extend the chain or be a no-op depending on requirements
        # For now, we allow it (idempotent)
        blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="First claim"
        )

        # Same agent claims again - should succeed
        chain2 = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="Second claim"
        )

        assert chain2.agent_id == "agent-1"

    def test_non_overlapping_chains_succeed(self, blackboard):
        """Test that multiple agents can claim non-overlapping files."""
        chain1 = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/auth.py"],
            reason="Auth work"
        )

        chain2 = blackboard.claim_chain(
            agent_id="agent-2",
            files=["src/db.py"],
            reason="DB work"
        )

        assert chain1.chain_id != chain2.chain_id
        assert chain1.agent_id != chain2.agent_id


class TestClaimLifecycle:
    """Test claim lifecycle: release, complete, expire."""

    def test_release_chain(self, blackboard):
        """Test releasing a claim chain."""
        chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="Test"
        )

        # Release the chain
        result = blackboard.release_chain("agent-1", chain.chain_id)
        assert result is True

        # File should now be claimable by another agent
        chain2 = blackboard.claim_chain(
            agent_id="agent-2",
            files=["src/main.py"],
            reason="After release"
        )
        assert chain2.agent_id == "agent-2"

    def test_cannot_release_other_agents_chain(self, blackboard):
        """Test that an agent cannot release another agent's chain."""
        chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="Test"
        )

        # Agent 2 tries to release agent 1's chain
        result = blackboard.release_chain("agent-2", chain.chain_id)
        assert result is False

        # File should still be claimed by agent-1
        claim = blackboard.get_claim_for_file("src/main.py")
        assert claim.agent_id == "agent-1"

    def test_complete_chain(self, blackboard):
        """Test marking a chain as completed."""
        chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="Test"
        )

        # Complete the chain
        result = blackboard.complete_chain("agent-1", chain.chain_id)
        assert result is True

        # File should now be claimable by another agent
        chain2 = blackboard.claim_chain(
            agent_id="agent-2",
            files=["src/main.py"],
            reason="After completion"
        )
        assert chain2.agent_id == "agent-2"

    def test_chain_auto_expires(self, blackboard):
        """Test that chains automatically expire after TTL."""
        # Create a chain with 1-second TTL (using a very short TTL for testing)
        # Note: In production, minimum TTL should be higher
        chain = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/main.py"],
            reason="Short-lived task",
            ttl_minutes=0.01  # ~0.6 seconds
        )

        # Wait for expiration
        time.sleep(2)

        # Should now be claimable by another agent
        chain2 = blackboard.claim_chain(
            agent_id="agent-2",
            files=["src/main.py"],
            reason="After expiry"
        )
        assert chain2.agent_id == "agent-2"


class TestClaimQueries:
    """Test query methods for claims."""

    def test_get_blocking_chains(self, blackboard):
        """Test getting chains that block specific files."""
        # Create two separate chains
        chain1 = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/auth.py", "src/user.py"],
            reason="Auth module"
        )

        chain2 = blackboard.claim_chain(
            agent_id="agent-2",
            files=["src/db.py"],
            reason="DB module"
        )

        # Query for files in chain 1
        blocking = blackboard.get_blocking_chains(["src/auth.py", "src/config.py"])
        assert len(blocking) == 1
        assert blocking[0].chain_id == chain1.chain_id

        # Query for files in chain 2
        blocking = blackboard.get_blocking_chains(["src/db.py"])
        assert len(blocking) == 1
        assert blocking[0].chain_id == chain2.chain_id

        # Query for files in both chains
        blocking = blackboard.get_blocking_chains(["src/auth.py", "src/db.py"])
        assert len(blocking) == 2

        # Query for unclaimed files
        blocking = blackboard.get_blocking_chains(["src/unclaimed.py"])
        assert len(blocking) == 0

    def test_get_agent_chains(self, blackboard):
        """Test getting all chains for an agent."""
        # Agent 1 creates two chains
        chain1 = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/auth.py"],
            reason="Auth"
        )

        chain2 = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/db.py"],
            reason="DB"
        )

        # Agent 2 creates one chain
        chain3 = blackboard.claim_chain(
            agent_id="agent-2",
            files=["src/config.py"],
            reason="Config"
        )

        # Get chains for agent-1
        agent1_chains = blackboard.get_agent_chains("agent-1")
        assert len(agent1_chains) == 2
        chain_ids = {c.chain_id for c in agent1_chains}
        assert chain1.chain_id in chain_ids
        assert chain2.chain_id in chain_ids

        # Get chains for agent-2
        agent2_chains = blackboard.get_agent_chains("agent-2")
        assert len(agent2_chains) == 1
        assert agent2_chains[0].chain_id == chain3.chain_id

    def test_get_all_active_chains(self, blackboard):
        """Test getting all active chains."""
        # Create multiple chains
        chain1 = blackboard.claim_chain(
            agent_id="agent-1",
            files=["src/auth.py"],
            reason="Auth"
        )

        chain2 = blackboard.claim_chain(
            agent_id="agent-2",
            files=["src/db.py"],
            reason="DB"
        )

        # Get all active chains
        active = blackboard.get_all_active_chains()
        assert len(active) == 2

        # Release one chain
        blackboard.release_chain("agent-1", chain1.chain_id)

        # Should now have only one active chain
        active = blackboard.get_all_active_chains()
        assert len(active) == 1
        assert active[0].chain_id == chain2.chain_id


class TestClaimChainDataclass:
    """Test ClaimChain dataclass serialization."""

    def test_to_dict(self):
        """Test converting ClaimChain to dict."""
        chain = ClaimChain(
            chain_id="test-123",
            agent_id="agent-1",
            files={"file1.py", "file2.py"},
            reason="Testing",
            claimed_at=datetime(2025, 1, 1, 12, 0, 0),
            expires_at=datetime(2025, 1, 1, 12, 30, 0),
            status="active"
        )

        data = chain.to_dict()
        assert data["chain_id"] == "test-123"
        assert data["agent_id"] == "agent-1"
        assert set(data["files"]) == {"file1.py", "file2.py"}
        assert data["status"] == "active"
        assert isinstance(data["claimed_at"], str)  # ISO format

    def test_from_dict(self):
        """Test creating ClaimChain from dict."""
        data = {
            "chain_id": "test-456",
            "agent_id": "agent-2",
            "files": ["file1.py", "file2.py"],
            "reason": "Testing",
            "claimed_at": "2025-01-01T12:00:00",
            "expires_at": "2025-01-01T12:30:00",
            "status": "active"
        }

        chain = ClaimChain.from_dict(data)
        assert chain.chain_id == "test-456"
        assert chain.agent_id == "agent-2"
        assert chain.files == {"file1.py", "file2.py"}
        assert chain.status == "active"
        assert isinstance(chain.claimed_at, datetime)

    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are inverses."""
        original = ClaimChain(
            chain_id="roundtrip-test",
            agent_id="agent-3",
            files={"a.py", "b.py", "c.py"},
            reason="Roundtrip test",
            claimed_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=30),
            status="active"
        )

        data = original.to_dict()
        restored = ClaimChain.from_dict(data)

        assert restored.chain_id == original.chain_id
        assert restored.agent_id == original.agent_id
        assert restored.files == original.files
        assert restored.reason == original.reason
        assert restored.status == original.status


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
