#!/usr/bin/env python3
"""
Event Log: Append-only event stream for multi-agent coordination.

This is a NEW system that runs alongside blackboard.py during migration.
It does NOT replace or modify the existing blackboard - safe to test.

ARCHITECTURE:
- Events are immutable, append-only (JSONL format)
- Each event has a monotonic sequence number
- State is derived by replaying events (event sourcing pattern)
- Platform-specific atomic append for concurrency safety

USAGE:
    from event_log import EventLog

    el = EventLog("/path/to/project")
    el.append_event("agent.registered", {"agent_id": "abc", "task": "test"})
    state = el.get_current_state()
"""

import json
import os
import sys
import time
import random
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime

# Platform-specific imports for atomic file operations
WINDOWS = sys.platform == 'win32'

if WINDOWS:
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
else:
    try:
        import fcntl
    except ImportError:
        fcntl = None


class EventLog:
    """
    Append-only event log for coordination state.

    Designed to fix race conditions in mutable blackboard.json:
    - TOCTOU vulnerability -> eliminated by append-only
    - Partial writes -> eliminated by newline atomicity boundary
    - Lock contention -> reduced by O_APPEND (lock-free writes)
    - Cursor skew -> fixed by monotonic sequence numbers
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.coordination_dir = self.project_root / ".coordination"
        self.event_log_file = self.coordination_dir / "events.jsonl"
        self.lock_file = self.coordination_dir / ".events.lock"
        self.seq_file = self.coordination_dir / ".events.seq"

        # In-memory cache
        self._state_cache: Optional[Dict] = None
        self._cache_seq: int = 0  # Sequence number when cache was built

    def _ensure_dir(self) -> None:
        """Create coordination directory if it doesn't exist."""
        self.coordination_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Locking (for sequence number only - writes are lock-free via O_APPEND)
    # =========================================================================

    def _get_lock(self, timeout: float = 30.0) -> Optional[Any]:
        """Acquire file lock for sequence number increment."""
        self._ensure_dir()
        start = time.time()
        handle = None

        while time.time() - start < timeout:
            try:
                if WINDOWS and msvcrt:
                    handle = open(self.lock_file, 'w')
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1024)
                    return handle
                elif fcntl:
                    handle = open(self.lock_file, 'w')
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return handle
                else:
                    # Fallback: no locking available
                    return open(self.lock_file, 'w')
            except (IOError, OSError):
                if handle is not None:
                    try:
                        handle.close()
                    except (IOError, OSError):
                        pass
                    handle = None
                time.sleep(0.1 + random.uniform(0, 0.1))

        return None

    def _release_lock(self, handle: Any) -> None:
        """Release file lock."""
        if handle:
            try:
                if WINDOWS and msvcrt:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1024)
                elif fcntl:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError, ValueError):
                pass
            finally:
                try:
                    handle.close()
                except (IOError, OSError):
                    pass

    # =========================================================================
    # Sequence Number Management
    # =========================================================================

    def _get_next_sequence(self) -> int:
        """
        Get next monotonic sequence number.
        Uses lock to ensure uniqueness across concurrent writers.
        """
        lock = self._get_lock(timeout=5.0)
        if lock is None:
            # Fallback: use timestamp-based sequence (less ideal but won't block)
            return int(time.time() * 1000000)

        try:
            # Read current sequence
            if self.seq_file.exists():
                try:
                    seq = int(self.seq_file.read_text().strip())
                except (ValueError, IOError):
                    seq = 0
            else:
                seq = 0

            # Increment and write
            next_seq = seq + 1
            self.seq_file.write_text(str(next_seq))

            return next_seq
        finally:
            self._release_lock(lock)

    # =========================================================================
    # Event Writing (Lock-free via O_APPEND)
    # =========================================================================

    def append_event(self, event_type: str, data: Dict) -> int:
        """
        Append an event to the log.

        Returns: sequence number of the appended event

        Thread-safe via O_APPEND atomic writes (no lock needed for append).
        Only sequence number generation uses a lock.
        """
        self._ensure_dir()

        # Get unique sequence number (this part uses lock)
        seq = self._get_next_sequence()

        # Build event
        timestamp = datetime.now().isoformat()
        event = {
            "seq": seq,
            "type": event_type,
            "ts": timestamp,
            "data": data
        }

        # Serialize to single line (JSONL format)
        line = json.dumps(event, separators=(',', ':'), default=str)

        # Add checksum for crash recovery
        checksum = hashlib.md5(line.encode()).hexdigest()[:8]
        line_with_checksum = f"{line}|{checksum}\n"

        # Atomic append (O_APPEND on Unix, best-effort on Windows)
        # Key: each line is independent, partial writes only affect that line
        with open(self.event_log_file, 'a', encoding='utf-8', newline='') as f:
            f.write(line_with_checksum)
            f.flush()
            os.fsync(f.fileno())  # Ensure durability

        # Invalidate cache
        self._state_cache = None

        return seq

    # =========================================================================
    # Event Reading
    # =========================================================================

    def read_events(self, since_seq: int = 0) -> List[Dict]:
        """
        Read events from the log.

        Args:
            since_seq: Only return events with seq > since_seq (for delta queries)

        Returns: List of events, ordered by sequence number
        """
        if not self.event_log_file.exists():
            return []

        events = []
        with open(self.event_log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                # Parse line with checksum
                try:
                    if '|' in line:
                        json_part, checksum = line.rsplit('|', 1)
                        # Verify checksum
                        expected = hashlib.md5(json_part.encode()).hexdigest()[:8]
                        if checksum != expected:
                            # Corrupted line - skip but log
                            sys.stderr.write(f"Warning: Corrupted event at line {line_num}, skipping\n")
                            continue
                        event = json.loads(json_part)
                    else:
                        # Legacy format without checksum
                        event = json.loads(line)

                    if event.get("seq", 0) > since_seq:
                        events.append(event)

                except json.JSONDecodeError as e:
                    sys.stderr.write(f"Warning: Invalid JSON at line {line_num}: {e}, skipping\n")
                    continue

        # Sort by sequence number (should already be ordered, but ensure)
        events.sort(key=lambda e: e.get("seq", 0))
        return events

    def get_latest_sequence(self) -> int:
        """Get the highest sequence number in the log."""
        events = self.read_events()
        if not events:
            return 0
        return max(e.get("seq", 0) for e in events)

    # =========================================================================
    # State Reconstruction (Event Sourcing)
    # =========================================================================

    def get_current_state(self, use_cache: bool = True) -> Dict:
        """
        Derive current state by replaying all events.

        This is the event sourcing pattern: State = f(events)
        """
        # Check cache
        if use_cache and self._state_cache is not None:
            # Verify cache is still valid
            current_seq = self.get_latest_sequence()
            if current_seq == self._cache_seq:
                return self._state_cache.copy()

        # Initialize empty state (matches blackboard.json structure)
        state = {
            "version": "2.0-eventlog",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "agents": {},
            "findings": [],
            "messages": [],
            "task_queue": [],
            "questions": [],
            "context": {}
        }

        # Replay all events
        events = self.read_events()
        for event in events:
            state = self._apply_event(state, event)

        # Update cache
        self._state_cache = state.copy()
        self._cache_seq = self.get_latest_sequence()

        return state

    def _apply_event(self, state: Dict, event: Dict) -> Dict:
        """
        Apply a single event to derive new state.
        Pure function: state' = apply(state, event)
        """
        event_type = event.get("type", "")
        data = event.get("data", {})
        timestamp = event.get("ts", datetime.now().isoformat())
        seq = event.get("seq", 0)

        # ----- Agent Events -----
        if event_type == "agent.registered":
            agent_id = data.get("agent_id")
            if agent_id:
                state["agents"][agent_id] = {
                    "task": data.get("task", ""),
                    "scope": data.get("scope", []),
                    "interests": data.get("interests", []),
                    "status": "active",
                    "started_at": timestamp,
                    "last_seen": timestamp,
                    "context_cursor": data.get("context_cursor", 0)
                }

        elif event_type == "agent.status_updated":
            agent_id = data.get("agent_id")
            if agent_id and agent_id in state["agents"]:
                state["agents"][agent_id]["status"] = data.get("status", "active")
                state["agents"][agent_id]["last_seen"] = timestamp
                if "result" in data:
                    state["agents"][agent_id]["result"] = data["result"]
                if data.get("status") in ("completed", "failed"):
                    state["agents"][agent_id]["finished_at"] = timestamp

        elif event_type == "agent.cursor_updated":
            agent_id = data.get("agent_id")
            if agent_id and agent_id in state["agents"]:
                state["agents"][agent_id]["context_cursor"] = data.get("cursor", 0)
                state["agents"][agent_id]["last_seen"] = timestamp

        elif event_type == "agent.heartbeat":
            agent_id = data.get("agent_id")
            if agent_id and agent_id in state["agents"]:
                state["agents"][agent_id]["last_seen"] = timestamp

        # ----- Finding Events -----
        elif event_type == "finding.added":
            finding_id = data.get("id", f"finding-{seq}")
            state["findings"].append({
                "id": finding_id,
                "agent_id": data.get("agent_id", "unknown"),
                "type": data.get("finding_type", "fact"),
                "content": data.get("content", ""),
                "files": data.get("files", []),
                "importance": data.get("importance", "normal"),
                "tags": data.get("tags", []),
                "timestamp": timestamp
            })

        # ----- Message Events -----
        elif event_type == "message.sent":
            msg_id = data.get("id", f"msg-{seq}")
            state["messages"].append({
                "id": msg_id,
                "from": data.get("from_agent", "unknown"),
                "to": data.get("to_agent", "*"),
                "type": data.get("msg_type", "info"),
                "content": data.get("content", ""),
                "read": False,
                "timestamp": timestamp
            })

        elif event_type == "message.read":
            msg_id = data.get("message_id")
            for msg in state["messages"]:
                if msg["id"] == msg_id:
                    msg["read"] = True
                    break

        # ----- Task Events -----
        elif event_type == "task.added":
            task_id = data.get("id", f"task-{seq}")
            state["task_queue"].append({
                "id": task_id,
                "task": data.get("task", ""),
                "priority": data.get("priority", 5),
                "depends_on": data.get("depends_on", []),
                "assigned_to": data.get("assigned_to"),
                "status": "pending",
                "created_at": timestamp
            })

        elif event_type == "task.claimed":
            task_id = data.get("task_id")
            for task in state["task_queue"]:
                if task["id"] == task_id:
                    task["assigned_to"] = data.get("agent_id")
                    task["status"] = "in_progress"
                    task["claimed_at"] = timestamp
                    break

        elif event_type == "task.completed":
            task_id = data.get("task_id")
            for task in state["task_queue"]:
                if task["id"] == task_id:
                    task["status"] = "completed"
                    if "result" in data:
                        task["result"] = data["result"]
                    task["completed_at"] = timestamp
                    break

        # ----- Question Events -----
        elif event_type == "question.asked":
            q_id = data.get("id", f"q-{seq}")
            state["questions"].append({
                "id": q_id,
                "agent_id": data.get("agent_id", "unknown"),
                "question": data.get("question", ""),
                "options": data.get("options"),
                "blocking": data.get("blocking", True),
                "status": "open",
                "answer": None,
                "answered_by": None,
                "created_at": timestamp
            })

        elif event_type == "question.answered":
            q_id = data.get("question_id")
            for q in state["questions"]:
                if q["id"] == q_id:
                    q["answer"] = data.get("answer")
                    q["answered_by"] = data.get("answered_by")
                    q["status"] = "resolved"
                    q["answered_at"] = timestamp
                    break

        # ----- Context Events -----
        elif event_type == "context.set":
            key = data.get("key")
            if key:
                state["context"][key] = {
                    "value": data.get("value"),
                    "updated_at": timestamp
                }

        # Update state timestamp
        state["updated_at"] = timestamp

        return state

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_findings_since(self, cursor: int) -> List[Dict]:
        """Get findings added since the given cursor (sequence number)."""
        state = self.get_current_state()
        # Filter findings by checking their position in the list
        # This assumes findings are appended in order
        events = self.read_events(since_seq=cursor)
        finding_events = [e for e in events if e.get("type") == "finding.added"]

        findings = []
        for event in finding_events:
            data = event.get("data", {})
            findings.append({
                "id": data.get("id", f"finding-{event.get('seq')}"),
                "agent_id": data.get("agent_id"),
                "type": data.get("finding_type"),
                "content": data.get("content"),
                "files": data.get("files", []),
                "importance": data.get("importance", "normal"),
                "tags": data.get("tags", []),
                "timestamp": event.get("ts")
            })

        return findings

    def get_active_agents(self) -> Dict:
        """Get agents with status='active'."""
        state = self.get_current_state()
        return {
            agent_id: agent_data
            for agent_id, agent_data in state["agents"].items()
            if agent_data.get("status") == "active"
        }

    def reset(self) -> None:
        """Clear all events (for testing only)."""
        if self.event_log_file.exists():
            self.event_log_file.unlink()
        if self.seq_file.exists():
            self.seq_file.unlink()
        self._state_cache = None
        self._cache_seq = 0

    def get_stats(self) -> Dict:
        """Get statistics about the event log."""
        events = self.read_events()
        state = self.get_current_state()

        return {
            "total_events": len(events),
            "latest_seq": self.get_latest_sequence(),
            "agents": len(state["agents"]),
            "findings": len(state["findings"]),
            "messages": len(state["messages"]),
            "tasks": len(state["task_queue"]),
            "questions": len(state["questions"]),
            "file_size_bytes": self.event_log_file.stat().st_size if self.event_log_file.exists() else 0
        }


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Event Log CLI")
    parser.add_argument("--project", default=".", help="Project root directory")
    parser.add_argument("--action", choices=["stats", "state", "events", "test"], default="stats")

    args = parser.parse_args()

    el = EventLog(args.project)

    if args.action == "stats":
        stats = el.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.action == "state":
        state = el.get_current_state()
        print(json.dumps(state, indent=2, default=str))

    elif args.action == "events":
        events = el.read_events()
        for event in events:
            print(json.dumps(event, default=str))

    elif args.action == "test":
        # Run a quick test
        print("Running event log test...")

        # Use temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_el = EventLog(tmpdir)

            # Test agent registration
            seq1 = test_el.append_event("agent.registered", {
                "agent_id": "test-agent-1",
                "task": "Test task",
                "interests": ["testing"]
            })
            print(f"  Registered agent (seq={seq1})")

            # Test finding
            seq2 = test_el.append_event("finding.added", {
                "agent_id": "test-agent-1",
                "finding_type": "discovery",
                "content": "Found something interesting",
                "tags": ["test"]
            })
            print(f"  Added finding (seq={seq2})")

            # Test state reconstruction
            state = test_el.get_current_state()
            print(f"  State has {len(state['agents'])} agents, {len(state['findings'])} findings")

            # Verify
            assert "test-agent-1" in state["agents"], "Agent not found!"
            assert len(state["findings"]) == 1, "Finding not found!"
            assert state["findings"][0]["content"] == "Found something interesting"

            print("  All tests passed!")
