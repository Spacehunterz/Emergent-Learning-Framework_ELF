"""
Comprehensive tests for EventLog dictionary dispatch pattern.

Tests the refactored event handler dispatch system that replaced
the if/elif chain with a dictionary-based dispatch table.

Test Coverage:
1. Handler coverage for all event types
2. Unknown event handling
3. State reconstruction accuracy
4. Concurrent access safety
5. Performance benchmarks
"""
import json
import tempfile
import pytest
import time
import sys
import threading
from io import StringIO
from pathlib import Path
from coordinator.event_log import EventLog


class TestHandlerCoverage:
    """Test that each event type routes to the correct handler."""

    def test_agent_registered_handler(self):
        """Test agent.registered routes to _handle_agent_registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)
            seq = el.append_event("agent.registered", {
                "agent_id": "test-agent",
                "task": "Test task",
                "scope": ["file1.py"],
                "interests": ["testing"],
                "context_cursor": 0
            })

            state = el.get_current_state()
            assert "test-agent" in state["agents"]
            assert state["agents"]["test-agent"]["task"] == "Test task"
            assert state["agents"]["test-agent"]["status"] == "active"
            assert state["agents"]["test-agent"]["scope"] == ["file1.py"]
            assert state["agents"]["test-agent"]["interests"] == ["testing"]
            assert state["agents"]["test-agent"]["context_cursor"] == 0

    def test_agent_status_updated_handler(self):
        """Test agent.status_updated routes to _handle_agent_status_updated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Register agent first
            el.append_event("agent.registered", {
                "agent_id": "test-agent",
                "task": "Test task"
            })

            # Update status
            el.append_event("agent.status_updated", {
                "agent_id": "test-agent",
                "status": "working",
                "result": {"progress": "50%"}
            })

            state = el.get_current_state()
            assert state["agents"]["test-agent"]["status"] == "working"
            assert state["agents"]["test-agent"]["result"]["progress"] == "50%"

    def test_agent_cursor_updated_handler(self):
        """Test agent.cursor_updated routes to _handle_agent_cursor_updated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Register agent
            el.append_event("agent.registered", {
                "agent_id": "test-agent",
                "task": "Test task"
            })

            # Update cursor
            el.append_event("agent.cursor_updated", {
                "agent_id": "test-agent",
                "cursor": 42
            })

            state = el.get_current_state()
            assert state["agents"]["test-agent"]["context_cursor"] == 42

    def test_agent_heartbeat_handler(self):
        """Test agent.heartbeat routes to _handle_agent_heartbeat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Register agent
            el.append_event("agent.registered", {
                "agent_id": "test-agent",
                "task": "Test task"
            })

            # Get initial last_seen
            state1 = el.get_current_state()
            last_seen_1 = state1["agents"]["test-agent"]["last_seen"]

            # Wait a tiny bit
            time.sleep(0.01)

            # Send heartbeat
            el.append_event("agent.heartbeat", {
                "agent_id": "test-agent"
            })

            state2 = el.get_current_state()
            last_seen_2 = state2["agents"]["test-agent"]["last_seen"]

            # last_seen should be updated
            assert last_seen_2 > last_seen_1

    def test_finding_added_handler(self):
        """Test finding.added routes to _handle_finding_added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            seq = el.append_event("finding.added", {
                "agent_id": "test-agent",
                "finding_type": "discovery",
                "content": "Found something",
                "files": ["file1.py", "file2.py"],
                "importance": "high",
                "tags": ["security", "bug"]
            })

            state = el.get_current_state()
            assert len(state["findings"]) == 1
            finding = state["findings"][0]
            assert finding["id"] == f"finding-{seq}"
            assert finding["seq"] == seq
            assert finding["agent_id"] == "test-agent"
            assert finding["type"] == "discovery"
            assert finding["content"] == "Found something"
            assert finding["files"] == ["file1.py", "file2.py"]
            assert finding["importance"] == "high"
            assert finding["tags"] == ["security", "bug"]

    def test_message_sent_handler(self):
        """Test message.sent routes to _handle_message_sent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            el.append_event("message.sent", {
                "id": "msg-123",
                "from_agent": "agent-1",
                "to_agent": "agent-2",
                "msg_type": "question",
                "content": "Can you help?"
            })

            state = el.get_current_state()
            assert len(state["messages"]) == 1
            msg = state["messages"][0]
            assert msg["id"] == "msg-123"
            assert msg["from"] == "agent-1"
            assert msg["to"] == "agent-2"
            assert msg["type"] == "question"
            assert msg["content"] == "Can you help?"
            assert msg["read"] is False

    def test_message_read_handler(self):
        """Test message.read routes to _handle_message_read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Send message
            el.append_event("message.sent", {
                "id": "msg-123",
                "from_agent": "agent-1",
                "to_agent": "agent-2",
                "content": "Test message"
            })

            # Mark as read
            el.append_event("message.read", {
                "message_id": "msg-123"
            })

            state = el.get_current_state()
            msg = state["messages"][0]
            assert msg["read"] is True

    def test_task_added_handler(self):
        """Test task.added routes to _handle_task_added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            el.append_event("task.added", {
                "id": "task-1",
                "task": "Write tests",
                "priority": 8,
                "depends_on": ["task-0"],
                "assigned_to": "agent-1"
            })

            state = el.get_current_state()
            assert len(state["task_queue"]) == 1
            task = state["task_queue"][0]
            assert task["id"] == "task-1"
            assert task["task"] == "Write tests"
            assert task["priority"] == 8
            assert task["depends_on"] == ["task-0"]
            assert task["assigned_to"] == "agent-1"
            assert task["status"] == "pending"

    def test_task_claimed_handler(self):
        """Test task.claimed routes to _handle_task_claimed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Add task
            el.append_event("task.added", {
                "id": "task-1",
                "task": "Write tests"
            })

            # Claim task
            el.append_event("task.claimed", {
                "task_id": "task-1",
                "agent_id": "agent-2"
            })

            state = el.get_current_state()
            task = state["task_queue"][0]
            assert task["assigned_to"] == "agent-2"
            assert task["status"] == "in_progress"
            assert "claimed_at" in task

    def test_task_completed_handler(self):
        """Test task.completed routes to _handle_task_completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Add and claim task
            el.append_event("task.added", {"id": "task-1", "task": "Write tests"})
            el.append_event("task.claimed", {"task_id": "task-1", "agent_id": "agent-1"})

            # Complete task
            el.append_event("task.completed", {
                "task_id": "task-1",
                "result": {"tests_written": 10}
            })

            state = el.get_current_state()
            task = state["task_queue"][0]
            assert task["status"] == "completed"
            assert task["result"]["tests_written"] == 10
            assert "completed_at" in task

    def test_question_asked_handler(self):
        """Test question.asked routes to _handle_question_asked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            el.append_event("question.asked", {
                "id": "q-1",
                "agent_id": "agent-1",
                "question": "Should I proceed?",
                "options": ["yes", "no"],
                "blocking": True
            })

            state = el.get_current_state()
            assert len(state["questions"]) == 1
            q = state["questions"][0]
            assert q["id"] == "q-1"
            assert q["agent_id"] == "agent-1"
            assert q["question"] == "Should I proceed?"
            assert q["options"] == ["yes", "no"]
            assert q["blocking"] is True
            assert q["status"] == "open"

    def test_question_answered_handler(self):
        """Test question.answered routes to _handle_question_answered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Ask question
            el.append_event("question.asked", {
                "id": "q-1",
                "agent_id": "agent-1",
                "question": "Should I proceed?"
            })

            # Answer question
            el.append_event("question.answered", {
                "question_id": "q-1",
                "answer": "yes",
                "answered_by": "human"
            })

            state = el.get_current_state()
            q = state["questions"][0]
            assert q["answer"] == "yes"
            assert q["answered_by"] == "human"
            assert q["status"] == "resolved"
            assert "answered_at" in q

    def test_context_set_handler(self):
        """Test context.set routes to _handle_context_set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            el.append_event("context.set", {
                "key": "project_name",
                "value": "Test Project"
            })

            state = el.get_current_state()
            assert "project_name" in state["context"]
            assert state["context"]["project_name"]["value"] == "Test Project"
            assert "updated_at" in state["context"]["project_name"]


class TestUnknownEventHandling:
    """Test handling of unknown event types."""

    def test_unknown_event_calls_handle_unknown(self):
        """Test that unknown event types are handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Capture stderr
            old_stderr = sys.stderr
            sys.stderr = StringIO()

            try:
                # Send unknown event type
                seq = el.append_event("unknown.event.type", {
                    "data": "test"
                })

                # Get state - should not crash
                state = el.get_current_state()

                # Check warning was logged
                stderr_output = sys.stderr.getvalue()
                assert "Warning: Unknown event type" in stderr_output
                assert f"seq {seq}" in stderr_output

            finally:
                sys.stderr = old_stderr

    def test_unknown_event_does_not_corrupt_state(self):
        """Test that unknown events don't corrupt the state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Add valid events
            el.append_event("agent.registered", {"agent_id": "agent-1", "task": "Task 1"})
            el.append_event("finding.added", {
                "agent_id": "agent-1",
                "finding_type": "fact",
                "content": "Test finding"
            })

            # Suppress stderr for this test
            old_stderr = sys.stderr
            sys.stderr = StringIO()

            try:
                # Add unknown event
                el.append_event("totally.bogus.event", {"random": "data"})

                # Add more valid events
                el.append_event("agent.registered", {"agent_id": "agent-2", "task": "Task 2"})

            finally:
                sys.stderr = old_stderr

            # State should still be valid
            state = el.get_current_state()
            assert len(state["agents"]) == 2
            assert len(state["findings"]) == 1
            assert "agent-1" in state["agents"]
            assert "agent-2" in state["agents"]


class TestStateReconstruction:
    """Test state reconstruction from event replay."""

    def test_replay_100_events(self):
        """Test replaying 100+ events reconstructs correct state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Register 25 agents
            for i in range(25):
                el.append_event("agent.registered", {
                    "agent_id": f"agent-{i}",
                    "task": f"Task {i}"
                })

            # Add 25 findings
            for i in range(25):
                el.append_event("finding.added", {
                    "agent_id": f"agent-{i % 10}",
                    "finding_type": "discovery",
                    "content": f"Finding {i}"
                })

            # Add 25 tasks
            for i in range(25):
                el.append_event("task.added", {
                    "id": f"task-{i}",
                    "task": f"Task {i}"
                })

            # Update some agent statuses
            for i in range(10):
                el.append_event("agent.status_updated", {
                    "agent_id": f"agent-{i}",
                    "status": "completed"
                })

            # Add some messages
            for i in range(10):
                el.append_event("message.sent", {
                    "id": f"msg-{i}",
                    "from_agent": f"agent-{i}",
                    "to_agent": "agent-0",
                    "content": f"Message {i}"
                })

            # Add some questions
            for i in range(10):
                el.append_event("question.asked", {
                    "id": f"q-{i}",
                    "agent_id": f"agent-{i}",
                    "question": f"Question {i}?"
                })

            # Total: 25 + 25 + 25 + 10 + 10 + 10 = 105 events

            # Verify state reconstruction
            state = el.get_current_state()

            assert len(state["agents"]) == 25
            assert len(state["findings"]) == 25
            assert len(state["task_queue"]) == 25
            assert len(state["messages"]) == 10
            assert len(state["questions"]) == 10

            # Verify specific details
            assert state["agents"]["agent-5"]["status"] == "completed"
            assert state["agents"]["agent-15"]["status"] == "active"
            assert state["findings"][0]["content"] == "Finding 0"
            assert state["task_queue"][10]["id"] == "task-10"

    def test_state_cache_validity(self):
        """Test get_current_state() caching works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Add some events
            el.append_event("agent.registered", {"agent_id": "agent-1", "task": "Task 1"})

            # First call - cache miss
            start = time.time()
            state1 = el.get_current_state()
            time1 = time.time() - start

            # Second call - cache hit (should be faster)
            start = time.time()
            state2 = el.get_current_state()
            time2 = time.time() - start

            # Cache should return same data
            assert state1 == state2

            # Add new event - invalidates cache
            el.append_event("finding.added", {
                "agent_id": "agent-1",
                "finding_type": "fact",
                "content": "New finding"
            })

            # Next call should rebuild state
            state3 = el.get_current_state()
            assert len(state3["findings"]) == 1
            assert state1 != state3

    def test_no_cache_option(self):
        """Test use_cache=False bypasses cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            el.append_event("agent.registered", {"agent_id": "agent-1", "task": "Task 1"})

            # Build cache
            state1 = el.get_current_state(use_cache=True)

            # Force rebuild
            state2 = el.get_current_state(use_cache=False)

            # Compare relevant fields (created_at differs since state is recreated)
            assert state1["agents"] == state2["agents"]
            assert state1["findings"] == state2["findings"]
            assert state1["updated_at"] == state2["updated_at"]


class TestConcurrentAccess:
    """Test concurrent thread access to event log."""

    def test_concurrent_appends(self):
        """Test multiple threads appending events concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            errors = []
            sequences = []

            def append_events(thread_id, count):
                try:
                    for i in range(count):
                        seq = el.append_event("agent.registered", {
                            "agent_id": f"thread-{thread_id}-agent-{i}",
                            "task": f"Task {i}"
                        })
                        sequences.append(seq)
                except Exception as e:
                    errors.append(e)

            # Create 5 threads, each appending 20 events
            threads = []
            for t in range(5):
                thread = threading.Thread(target=append_events, args=(t, 20))
                threads.append(thread)

            # Start all threads
            for thread in threads:
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

            # Check for errors
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # Total events should be 5 * 20 = 100
            assert len(sequences) == 100

            # Verify state
            state = el.get_current_state()
            assert len(state["agents"]) == 100

    def test_sequence_numbers_monotonic(self):
        """Test that sequence numbers are strictly monotonic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            sequences = []

            def append_events(count):
                for i in range(count):
                    seq = el.append_event("finding.added", {
                        "agent_id": "test-agent",
                        "finding_type": "fact",
                        "content": f"Finding {i}"
                    })
                    sequences.append(seq)

            # Create multiple threads
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=append_events, args=(10,))
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Sort sequences
            sorted_seqs = sorted(sequences)

            # Check all are unique and monotonic
            assert len(sequences) == len(set(sequences)), "Duplicate sequence numbers found!"

            # Check no gaps in monotonicity
            for i in range(len(sorted_seqs)):
                assert sorted_seqs[i] == i + 1, f"Sequence gap at position {i}"

    def test_no_events_lost_concurrent(self):
        """Test that no events are lost during concurrent writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            num_threads = 4
            events_per_thread = 15
            expected_count = num_threads * events_per_thread  # 60 total

            def add_findings(thread_id, count):
                for i in range(count):
                    el.append_event("finding.added", {
                        "agent_id": f"thread-{thread_id}",
                        "finding_type": "fact",
                        "content": f"Thread {thread_id} finding {i}"
                    })

            threads = []
            for t in range(num_threads):
                thread = threading.Thread(target=add_findings, args=(t, events_per_thread))
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Verify all events recorded
            events = el.read_events()
            assert len(events) == 60, f"Expected 60 events, got {len(events)}"

            # Verify state
            state = el.get_current_state()
            assert len(state["findings"]) == 60


class TestPerformance:
    """Performance benchmarks for event log operations."""

    def test_1000_event_appends_performance(self):
        """Benchmark: Time 1000 event appends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            start = time.time()
            for i in range(1000):
                el.append_event("finding.added", {
                    "agent_id": "test-agent",
                    "finding_type": "fact",
                    "content": f"Finding {i}"
                })
            elapsed = time.time() - start

            avg_per_event = (elapsed / 1000) * 1000  # ms per event

            # Should be reasonably fast (< 10ms per event on average)
            print(f"\n1000 appends: {elapsed:.3f}s total, {avg_per_event:.3f}ms per event")
            assert avg_per_event < 10, f"Appends too slow: {avg_per_event:.3f}ms per event"

    def test_state_reconstruction_1000_events_performance(self):
        """Benchmark: Time state reconstruction from 1000 events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Create 1000 events
            for i in range(250):
                el.append_event("agent.registered", {
                    "agent_id": f"agent-{i}",
                    "task": f"Task {i}"
                })

            for i in range(250):
                el.append_event("finding.added", {
                    "agent_id": f"agent-{i % 250}",
                    "finding_type": "fact",
                    "content": f"Finding {i}"
                })

            for i in range(250):
                el.append_event("task.added", {
                    "id": f"task-{i}",
                    "task": f"Task {i}"
                })

            for i in range(250):
                el.append_event("message.sent", {
                    "id": f"msg-{i}",
                    "from_agent": f"agent-{i % 250}",
                    "content": f"Message {i}"
                })

            # Clear cache to force full reconstruction
            el._state_cache = None

            # Time state reconstruction
            start = time.time()
            state = el.get_current_state(use_cache=False)
            elapsed = time.time() - start

            print(f"\nState reconstruction (1000 events): {elapsed:.3f}s")

            # Should be fast (< 1 second)
            assert elapsed < 1.0, f"State reconstruction too slow: {elapsed:.3f}s"

            # Verify correctness
            assert len(state["agents"]) == 250
            assert len(state["findings"]) == 250
            assert len(state["task_queue"]) == 250
            assert len(state["messages"]) == 250

    def test_cache_performance_benefit(self):
        """Test that caching provides performance benefit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            # Add 100 events
            for i in range(100):
                el.append_event("finding.added", {
                    "agent_id": "test-agent",
                    "finding_type": "fact",
                    "content": f"Finding {i}"
                })

            # Time without cache
            el._state_cache = None
            start = time.time()
            state1 = el.get_current_state(use_cache=False)
            time_no_cache = time.time() - start

            # Time with cache (warm)
            start = time.time()
            state2 = el.get_current_state(use_cache=True)
            time_with_cache = time.time() - start

            print(f"\nNo cache: {time_no_cache:.4f}s, With cache: {time_with_cache:.4f}s")
            print(f"Speedup: {time_no_cache / time_with_cache:.1f}x")

            # Cache should be significantly faster
            assert time_with_cache < time_no_cache / 2, "Cache should provide at least 2x speedup"


class TestRegressions:
    """Test for known regressions and edge cases."""

    def test_agent_completion_sets_finished_at(self):
        """Regression: Ensure completed status sets finished_at timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            el.append_event("agent.registered", {"agent_id": "agent-1", "task": "Task 1"})
            el.append_event("agent.status_updated", {
                "agent_id": "agent-1",
                "status": "completed",
                "result": {"output": "done"}
            })

            state = el.get_current_state()
            agent = state["agents"]["agent-1"]

            assert agent["status"] == "completed"
            assert "finished_at" in agent
            assert "result" in agent

    def test_finding_id_uses_seq(self):
        """Regression: Ensure finding IDs use sequence numbers (C1 FIX)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            seq = el.append_event("finding.added", {
                "agent_id": "test-agent",
                "finding_type": "fact",
                "content": "Test finding"
            })

            state = el.get_current_state()
            finding = state["findings"][0]

            # ID should be finding-{seq}
            assert finding["id"] == f"finding-{seq}"
            # seq field should exist (C1 FIX)
            assert finding["seq"] == seq

    def test_message_default_to_broadcast(self):
        """Regression: Messages without to_agent default to broadcast."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            el.append_event("message.sent", {
                "id": "msg-1",
                "from_agent": "agent-1",
                "content": "Broadcast message"
            })

            state = el.get_current_state()
            msg = state["messages"][0]

            # Should default to "*" (broadcast)
            assert msg["to"] == "*"

    def test_empty_event_log_returns_empty_state(self):
        """Regression: Empty event log should return valid empty state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            el = EventLog(tmpdir)

            state = el.get_current_state()

            assert state["version"] == "2.0-eventlog"
            assert len(state["agents"]) == 0
            assert len(state["findings"]) == 0
            assert len(state["messages"]) == 0
            assert len(state["task_queue"]) == 0
            assert len(state["questions"]) == 0
            assert len(state["context"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
