#!/usr/bin/env python3
"""
Test script for event_log.py

Run this to verify the event log works WITHOUT touching your real coordination system.
Uses an isolated temp directory - completely safe.

Usage:
    python test_event_log.py
"""

import sys
import json
import tempfile
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from event_log import EventLog


def test_basic_operations():
    """Test basic event log operations."""
    print("\n=== Test 1: Basic Operations ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        el = EventLog(tmpdir)

        # Register an agent
        seq1 = el.append_event("agent.registered", {
            "agent_id": "agent-001",
            "task": "Analyze codebase",
            "interests": ["python", "testing"]
        })
        print(f"  [OK] Registered agent (seq={seq1})")

        # Add a finding
        seq2 = el.append_event("finding.added", {
            "agent_id": "agent-001",
            "finding_type": "discovery",
            "content": "Found 5 TODO comments",
            "importance": "normal",
            "tags": ["code-quality"]
        })
        print(f"  [OK] Added finding (seq={seq2})")

        # Get state
        state = el.get_current_state()
        assert "agent-001" in state["agents"], "Agent missing!"
        assert len(state["findings"]) == 1, "Finding missing!"
        print(f"  [OK] State reconstructed: {len(state['agents'])} agents, {len(state['findings'])} findings")

        # Test cursor-based delta
        cursor = seq1
        new_findings = el.get_findings_since(cursor)
        assert len(new_findings) == 1, "Delta query failed!"
        print(f"  [OK] Delta query: {len(new_findings)} new findings since seq={cursor}")

        print("  PASSED!")


def test_concurrent_simulation():
    """Simulate concurrent writes (sequential but tests the append pattern)."""
    print("\n=== Test 2: Simulated Concurrent Writes ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        el = EventLog(tmpdir)

        # Simulate 10 agents registering quickly
        for i in range(10):
            el.append_event("agent.registered", {
                "agent_id": f"agent-{i:03d}",
                "task": f"Task {i}"
            })

        state = el.get_current_state()
        assert len(state["agents"]) == 10, f"Expected 10 agents, got {len(state['agents'])}"
        print(f"  [OK] Registered 10 agents")

        # Simulate findings from multiple agents
        for i in range(10):
            for j in range(5):
                el.append_event("finding.added", {
                    "agent_id": f"agent-{i:03d}",
                    "finding_type": "fact",
                    "content": f"Finding {j} from agent {i}"
                })

        state = el.get_current_state()
        assert len(state["findings"]) == 50, f"Expected 50 findings, got {len(state['findings'])}"
        print(f"  [OK] Added 50 findings (5 per agent)")

        stats = el.get_stats()
        print(f"  [OK] Stats: {stats['total_events']} events, {stats['file_size_bytes']} bytes")

        print("  PASSED!")


def test_crash_recovery():
    """Test that corrupted lines are handled gracefully."""
    print("\n=== Test 3: Crash Recovery (Corrupted Lines) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        el = EventLog(tmpdir)

        # Add valid events
        el.append_event("agent.registered", {"agent_id": "agent-1", "task": "Task 1"})
        el.append_event("agent.registered", {"agent_id": "agent-2", "task": "Task 2"})

        # Manually corrupt a line (simulate crash mid-write)
        event_file = Path(tmpdir) / ".coordination" / "events.jsonl"
        with open(event_file, 'a') as f:
            f.write('{"seq":999,"type":"broken","data":{}|BADCHECKSUM\n')  # Bad checksum
            f.write('not valid json at all\n')  # Invalid JSON

        # Add more valid events after corruption
        el.append_event("agent.registered", {"agent_id": "agent-3", "task": "Task 3"})

        # Read should skip corrupted lines
        state = el.get_current_state()

        # Should have 3 valid agents (corrupted lines skipped)
        assert len(state["agents"]) == 3, f"Expected 3 agents, got {len(state['agents'])}"
        print(f"  [OK] Recovered {len(state['agents'])} agents, corrupted lines skipped")

        print("  PASSED!")


def test_state_caching():
    """Test that caching works correctly."""
    print("\n=== Test 4: State Caching ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        el = EventLog(tmpdir)

        # Add events
        el.append_event("agent.registered", {"agent_id": "agent-1", "task": "Task 1"})

        # First read (builds cache)
        start = time.time()
        state1 = el.get_current_state()
        first_read_ms = (time.time() - start) * 1000
        print(f"  [OK] First read: {first_read_ms:.2f}ms")

        # Second read (uses cache)
        start = time.time()
        state2 = el.get_current_state()
        cached_read_ms = (time.time() - start) * 1000
        print(f"  [OK] Cached read: {cached_read_ms:.2f}ms")

        # Add more events (invalidates cache)
        el.append_event("finding.added", {"agent_id": "agent-1", "finding_type": "fact", "content": "New finding"})

        # Third read (rebuilds cache)
        start = time.time()
        state3 = el.get_current_state()
        rebuild_read_ms = (time.time() - start) * 1000
        print(f"  [OK] After new event: {rebuild_read_ms:.2f}ms")

        assert len(state3["findings"]) == 1, "New finding not in state!"
        print("  PASSED!")


def test_full_workflow():
    """Test a realistic coordination workflow."""
    print("\n=== Test 5: Full Workflow Simulation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        el = EventLog(tmpdir)

        # Coordinator registers agents
        el.append_event("agent.registered", {
            "agent_id": "researcher",
            "task": "Research async patterns",
            "interests": ["async", "patterns"]
        })
        el.append_event("agent.registered", {
            "agent_id": "architect",
            "task": "Design event log",
            "interests": ["architecture", "design"]
        })
        print("  [OK] Registered 2 agents")

        # Agents add findings
        el.append_event("finding.added", {
            "agent_id": "researcher",
            "finding_type": "discovery",
            "content": "Kafka uses O_APPEND for atomic writes",
            "tags": ["prior-art", "kafka"]
        })
        el.append_event("finding.added", {
            "agent_id": "architect",
            "finding_type": "fact",
            "content": "JSONL format allows line-level atomicity",
            "tags": ["design", "format"]
        })
        print("  [OK] Added findings from both agents")

        # Agent asks a question
        q_seq = el.append_event("question.asked", {
            "agent_id": "researcher",
            "question": "Should we use SQLite or JSONL?",
            "options": ["SQLite", "JSONL", "Both"],
            "blocking": True
        })
        print("  [OK] Question asked")

        # Question answered (use the actual question ID from sequence)
        el.append_event("question.answered", {
            "question_id": f"q-{q_seq}",  # Match the auto-generated ID
            "answer": "Both - JSONL for real-time, SQLite for history",
            "answered_by": "human"
        })
        print("  [OK] Question answered")

        # Agents complete
        el.append_event("agent.status_updated", {
            "agent_id": "researcher",
            "status": "completed",
            "result": "Found 5 relevant patterns"
        })
        el.append_event("agent.status_updated", {
            "agent_id": "architect",
            "status": "completed",
            "result": "Design complete"
        })
        print("  [OK] Agents completed")

        # Final state check
        state = el.get_current_state()
        active = el.get_active_agents()

        assert len(state["agents"]) == 2, "Wrong agent count"
        assert len(active) == 0, "Should have no active agents"
        assert len(state["findings"]) == 2, "Wrong finding count"
        assert len(state["questions"]) == 1, "Wrong question count"
        assert state["questions"][0]["status"] == "resolved", "Question not resolved"

        print(f"  [OK] Final state: {len(state['agents'])} agents, {len(state['findings'])} findings")
        print("  PASSED!")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("EVENT LOG TEST SUITE")
    print("=" * 60)
    print("\nThis tests the NEW event log system in isolation.")
    print("Your real coordination system is NOT touched.\n")

    tests = [
        test_basic_operations,
        test_concurrent_simulation,
        test_crash_recovery,
        test_state_caching,
        test_full_workflow,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\nAll tests passed! Event log is ready for integration testing.")
        print("\nNext steps:")
        print("  1. Run with real project: python event_log.py --project /path/to/project --action test")
        print("  2. Create blackboard_v2.py adapter for dual-write")
        print("  3. Test dual-write in Phase 1 (read from old, write to both)")
    else:
        print("\nSome tests failed. Fix issues before proceeding.")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
