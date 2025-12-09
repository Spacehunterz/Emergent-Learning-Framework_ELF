"""
Tests for EventLog - Append-only event stream for multi-agent coordination.

Extracted from embedded tests in coordinator/event_log.py.
"""
import json
import tempfile
import pytest
from coordinator.event_log import EventLog


def test_event_log_basic_operations():
    """Test basic event log operations: registration, findings, state reconstruction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_el = EventLog(tmpdir)

        # Test agent registration
        seq1 = test_el.append_event("agent.registered", {
            "agent_id": "test-agent-1",
            "task": "Test task",
            "interests": ["testing"]
        })
        assert seq1 >= 0, "Should return valid sequence number"

        # Test finding
        seq2 = test_el.append_event("finding.added", {
            "agent_id": "test-agent-1",
            "finding_type": "discovery",
            "content": "Found something interesting",
            "tags": ["test"]
        })
        assert seq2 > seq1, "Sequence numbers should be monotonic"

        # Test state reconstruction
        state = test_el.get_current_state()
        assert len(state['agents']) == 1, "Should have 1 agent"
        assert len(state['findings']) == 1, "Should have 1 finding"

        # Verify agent details
        assert "test-agent-1" in state["agents"], "Agent not found!"
        assert state["agents"]["test-agent-1"]["task"] == "Test task"
        
        # Verify finding details
        assert state["findings"][0]["content"] == "Found something interesting"
        assert state["findings"][0]["type"] == "discovery"


def test_event_log_stats():
    """Test event log statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_el = EventLog(tmpdir)
        
        # Add some events
        test_el.append_event("agent.registered", {"agent_id": "agent-1", "task": "Task 1"})
        test_el.append_event("agent.registered", {"agent_id": "agent-2", "task": "Task 2"})
        
        # Get stats
        stats = test_el.get_stats()
        assert "total_events" in stats
        assert stats["total_events"] >= 2


def test_event_log_concurrent_agents():
    """Test multiple agents writing to the same event log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_el = EventLog(tmpdir)
        
        # Register multiple agents
        for i in range(5):
            test_el.append_event("agent.registered", {
                "agent_id": f"agent-{i}",
                "task": f"Task {i}"
            })
        
        # Verify all agents are in state
        state = test_el.get_current_state()
        assert len(state["agents"]) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
