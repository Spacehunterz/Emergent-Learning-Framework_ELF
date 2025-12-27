"""
Tests for BlackboardV2 - Dual-write adapter for blackboard and event log.

Extracted from embedded tests in coordinator/blackboard_v2.py.
"""
import sys
import os
import tempfile
from pathlib import Path
import pytest

# Add coordinator to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "coordinator"))

from blackboard_v2 import BlackboardV2


def test_dual_write_consistency():
    """Test that dual-write maintains consistency between blackboard and event log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bb = BlackboardV2(tmpdir)
        
        # Register agent and add finding
        bb.register_agent("test-agent", "Testing dual-write", interests=["testing"])
        bb.add_finding("test-agent", "fact", "Dual-write test finding", tags=["test"])
        
        # Validate consistency
        result = bb.validate_state_consistency()
        assert result["consistent"], f"States inconsistent: {result.get('differences', [])}"


def test_blackboard_v2_stats():
    """Test that stats are available from both systems."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bb = BlackboardV2(tmpdir)
        
        # Get stats
        stats = bb.get_event_log_stats()
        assert "total_events" in stats


def test_blackboard_v2_multiple_agents():
    """Test multiple agents using dual-write system."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bb = BlackboardV2(tmpdir)
        
        # Register multiple agents
        bb.register_agent("agent-1", "Task 1", interests=["test1"])
        bb.register_agent("agent-2", "Task 2", interests=["test2"])
        
        # Add findings from both
        bb.add_finding("agent-1", "fact", "Finding from agent 1")
        bb.add_finding("agent-2", "fact", "Finding from agent 2")
        
        # Validate consistency
        result = bb.validate_state_consistency()
        assert result["consistent"], "Dual-write should maintain consistency"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
