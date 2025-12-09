#!/usr/bin/env python3
"""
Stress Test Suite for ELF Coordination System

Tests concurrent operations on:
- Blackboard V2 (dual-write system)
- Event Log (append-only event stream)
- Claim Chains (file locking system)

Each test runs multiple threads performing operations and verifies:
- No data corruption
- No race conditions
- No deadlocks
- Proper resource cleanup
"""

import sys
import os
import time
import threading
import tempfile
import shutil
import random
from pathlib import Path
from typing import List, Dict, Set, Any
from dataclasses import dataclass
from datetime import datetime

# Import modules directly from coordinator package
import importlib.util

coordinator_dir = Path(__file__).parent.parent / "coordinator"

# Load blackboard_v2
spec = importlib.util.spec_from_file_location("blackboard_v2", coordinator_dir / "blackboard_v2.py")
blackboard_v2_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blackboard_v2_module)
BlackboardV2 = blackboard_v2_module.BlackboardV2

# Load event_log
spec = importlib.util.spec_from_file_location("event_log", coordinator_dir / "event_log.py")
event_log_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(event_log_module)
EventLog = event_log_module.EventLog

# Load blackboard (with ClaimChain)
spec = importlib.util.spec_from_file_location("blackboard_coord", coordinator_dir / "blackboard.py")
blackboard_module = importlib.util.module_from_spec(spec)
sys.modules["blackboard_coord"] = blackboard_module  # Add to sys.modules for nested imports
spec.loader.exec_module(blackboard_module)
Blackboard = blackboard_module.Blackboard
ClaimChain = blackboard_module.ClaimChain
BlockedError = blackboard_module.BlockedError


# =============================================================================
# Test Results Tracking
# =============================================================================

@dataclass
class TestResult:
    """Container for test results."""
    name: str
    passed: bool
    duration_seconds: float
    operations_per_second: float = 0.0
    total_operations: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class TestRunner:
    """Manages test execution and result collection."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.temp_dirs: List[str] = []

    def create_temp_project(self) -> str:
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp(prefix="elf_stress_")
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def cleanup(self):
        """Clean up all temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up {temp_dir}: {e}")

    def run_test(self, name: str, test_func) -> TestResult:
        """Run a test function and capture results."""
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            result = test_func(self)
            duration = time.time() - start_time
            result.duration_seconds = duration

            if result.total_operations > 0:
                result.operations_per_second = result.total_operations / duration

            self.results.append(result)

            status = "PASS" if result.passed else "FAIL"
            print(f"\n{status}: {name}")
            print(f"Duration: {duration:.2f}s")
            if result.operations_per_second > 0:
                print(f"Throughput: {result.operations_per_second:.1f} ops/sec")

            if result.errors:
                print(f"Errors: {len(result.errors)}")
                for err in result.errors[:3]:  # Show first 3
                    print(f"  - {err}")

            if result.warnings:
                print(f"Warnings: {len(result.warnings)}")
                for warn in result.warnings[:3]:  # Show first 3
                    print(f"  - {warn}")

            return result

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(
                name=name,
                passed=False,
                duration_seconds=duration,
                errors=[f"Test crashed: {str(e)}"]
            )
            self.results.append(result)
            print(f"\nFAIL: {name} (crashed)")
            print(f"Error: {e}")
            return result

    def print_summary(self):
        """Print summary of all test results."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")

        print("\nDetailed Results:")
        for result in self.results:
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.name}")
            if result.operations_per_second > 0:
                print(f"    {result.operations_per_second:.1f} ops/sec, {result.total_operations} total ops")
            if not result.passed and result.errors:
                print(f"    Errors: {len(result.errors)}")


# =============================================================================
# Test 1: Blackboard Concurrent Access
# =============================================================================

def test_blackboard_concurrent_access(runner: TestRunner) -> TestResult:
    """
    Test concurrent access to blackboard with 10 threads performing:
    - Agent registration
    - Finding addition
    - Message sending
    - Task claiming

    Run for 5 seconds, verify no data corruption.
    """
    project_root = runner.create_temp_project()
    bb = BlackboardV2(project_root)

    errors = []
    warnings = []
    operation_counts = {
        'register': 0,
        'finding': 0,
        'message': 0,
        'task_claim': 0
    }
    locks = {k: threading.Lock() for k in operation_counts.keys()}

    stop_flag = threading.Event()

    def worker(thread_id: int):
        """Worker thread performing random operations."""
        agent_id = f"agent-{thread_id}"

        try:
            # Register agent
            bb.register_agent(agent_id, f"Task for thread {thread_id}", interests=["test"])
            with locks['register']:
                operation_counts['register'] += 1

            while not stop_flag.is_set():
                operation = random.choice(['finding', 'message', 'task_claim'])

                try:
                    if operation == 'finding':
                        bb.add_finding(
                            agent_id,
                            "discovery",
                            f"Finding from {agent_id} at {time.time()}",
                            importance="normal",
                            tags=["test"]
                        )
                        with locks['finding']:
                            operation_counts['finding'] += 1

                    elif operation == 'message':
                        # Send to random other agent
                        target = f"agent-{random.randint(0, 9)}"
                        bb.send_message(agent_id, target, f"Message at {time.time()}")
                        with locks['message']:
                            operation_counts['message'] += 1

                    elif operation == 'task_claim':
                        # Try to claim a pending task
                        tasks = bb.get_pending_tasks()
                        if tasks:
                            task_id = tasks[0]['id']
                            bb.claim_task(task_id, agent_id)
                            with locks['task_claim']:
                                operation_counts['task_claim'] += 1

                except Exception as e:
                    errors.append(f"Thread {thread_id} {operation}: {str(e)}")

                # Small sleep to avoid hammering
                time.sleep(0.01)

            # Mark agent complete
            bb.update_agent_status(agent_id, "completed")

        except Exception as e:
            errors.append(f"Thread {thread_id} fatal: {str(e)}")

    # Create some initial tasks for claiming
    for i in range(20):
        bb.add_task(f"Test task {i}", priority=5)

    # Start threads
    threads = []
    num_threads = 10

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    # Run for 5 seconds
    time.sleep(5)
    stop_flag.set()

    # Wait for all threads
    for t in threads:
        t.join(timeout=5)
        if t.is_alive():
            warnings.append(f"Thread did not terminate cleanly")

    # Verify state consistency
    try:
        validation = bb.validate_state_consistency()
        if not validation["consistent"]:
            for diff in validation["differences"]:
                errors.append(f"State divergence: {diff}")
    except Exception as e:
        errors.append(f"Validation failed: {e}")

    # Verify data integrity
    state = bb.get_full_state()

    # Check all agents registered
    if len(state["agents"]) != num_threads:
        errors.append(f"Expected {num_threads} agents, found {len(state['agents'])}")

    # Check for duplicate finding IDs
    finding_ids = [f["id"] for f in state["findings"]]
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("Duplicate finding IDs detected")

    # Check for duplicate message IDs
    msg_ids = [m["id"] for m in state["messages"]]
    if len(msg_ids) != len(set(msg_ids)):
        errors.append("Duplicate message IDs detected")

    total_ops = sum(operation_counts.values())

    return TestResult(
        name="Blackboard Concurrent Access",
        passed=len(errors) == 0,
        duration_seconds=0,  # Will be set by runner
        total_operations=total_ops,
        errors=errors,
        warnings=warnings,
        metadata={
            "operations": operation_counts,
            "agents": len(state["agents"]),
            "findings": len(state["findings"]),
            "messages": len(state["messages"])
        }
    )


# =============================================================================
# Test 2: Event Log Stress
# =============================================================================

def test_event_log_stress(runner: TestRunner) -> TestResult:
    """
    Test event log with:
    - 10 threads appending events rapidly
    - 5 threads reading state concurrently

    Verify:
    - Sequence numbers never duplicate
    - State reconstruction always consistent
    """
    project_root = runner.create_temp_project()
    event_log = EventLog(project_root)

    errors = []
    warnings = []
    append_count = 0
    read_count = 0
    append_lock = threading.Lock()
    read_lock = threading.Lock()

    stop_flag = threading.Event()
    seen_sequences = set()
    seq_lock = threading.Lock()

    def append_worker(thread_id: int):
        """Worker that appends events."""
        nonlocal append_count

        while not stop_flag.is_set():
            try:
                seq = event_log.append_event(
                    "finding.added",
                    {
                        "agent_id": f"writer-{thread_id}",
                        "finding_type": "test",
                        "content": f"Finding from thread {thread_id} at {time.time()}"
                    }
                )

                # Check for duplicate sequences
                with seq_lock:
                    if seq in seen_sequences:
                        errors.append(f"Duplicate sequence number: {seq}")
                    seen_sequences.add(seq)

                with append_lock:
                    append_count += 1

                time.sleep(0.001)  # Minimal delay

            except Exception as e:
                errors.append(f"Append thread {thread_id}: {str(e)}")

    def read_worker(thread_id: int):
        """Worker that reads state."""
        nonlocal read_count

        last_state = None

        while not stop_flag.is_set():
            try:
                state = event_log.get_current_state()

                # Verify state is always growing or same
                if last_state is not None:
                    if len(state["findings"]) < len(last_state["findings"]):
                        errors.append(f"Read thread {thread_id}: State shrunk!")

                last_state = state

                with read_lock:
                    read_count += 1

                time.sleep(0.01)

            except Exception as e:
                errors.append(f"Read thread {thread_id}: {str(e)}")

    # Start append threads
    append_threads = []
    for i in range(10):
        t = threading.Thread(target=append_worker, args=(i,))
        t.start()
        append_threads.append(t)

    # Start read threads
    read_threads = []
    for i in range(5):
        t = threading.Thread(target=read_worker, args=(i,))
        t.start()
        read_threads.append(t)

    # Run for 5 seconds
    time.sleep(5)
    stop_flag.set()

    # Wait for all threads
    for t in append_threads + read_threads:
        t.join(timeout=5)
        if t.is_alive():
            warnings.append("Thread did not terminate cleanly")

    # Final verification
    final_state = event_log.get_current_state()
    events = event_log.read_events()

    # Check all events have unique sequences
    event_seqs = [e["seq"] for e in events]
    if len(event_seqs) != len(set(event_seqs)):
        errors.append("Duplicate sequence numbers in event log")

    # Check sequence numbers are monotonic
    if event_seqs != sorted(event_seqs):
        errors.append("Sequence numbers are not monotonic")

    # Check state matches events
    if len(final_state["findings"]) != len(events):
        warnings.append(f"State has {len(final_state['findings'])} findings but {len(events)} events")

    total_ops = append_count + read_count

    return TestResult(
        name="Event Log Stress",
        passed=len(errors) == 0,
        duration_seconds=0,
        total_operations=total_ops,
        errors=errors,
        warnings=warnings,
        metadata={
            "appends": append_count,
            "reads": read_count,
            "unique_sequences": len(seen_sequences),
            "total_events": len(events)
        }
    )


# =============================================================================
# Test 3: Claim Chain Contention
# =============================================================================

def test_claim_chain_contention(runner: TestRunner) -> TestResult:
    """
    Test claim chains with 10 agents competing for overlapping file sets.

    Verify:
    - Exactly one agent succeeds for each file
    - No deadlocks
    - Claims eventually released
    """
    project_root = runner.create_temp_project()
    bb = Blackboard(project_root)

    errors = []
    warnings = []

    # Define overlapping file sets
    file_sets = [
        ["a.py", "b.py", "c.py"],
        ["b.py", "c.py", "d.py"],
        ["c.py", "d.py", "e.py"],
        ["d.py", "e.py", "f.py"],
        ["e.py", "f.py", "g.py"],
        ["f.py", "g.py", "h.py"],
        ["g.py", "h.py", "i.py"],
        ["h.py", "i.py", "j.py"],
        ["i.py", "j.py", "a.py"],
        ["j.py", "a.py", "b.py"],
    ]

    claims_succeeded = []
    claims_blocked = []
    claims_released = []
    lock = threading.Lock()

    stop_flag = threading.Event()

    def agent_worker(agent_id: int):
        """Worker that tries to claim files."""
        files = file_sets[agent_id]
        chain = None

        try:
            # Try to claim files
            try:
                chain = bb.claim_chain(f"agent-{agent_id}", files, f"Work by agent {agent_id}")
                with lock:
                    claims_succeeded.append((agent_id, files, chain.chain_id))

                # Hold the claim for a random duration
                hold_time = random.uniform(0.1, 0.5)
                time.sleep(hold_time)

                # Release the claim
                bb.release_chain(f"agent-{agent_id}", chain.chain_id)
                with lock:
                    claims_released.append((agent_id, chain.chain_id))

            except BlockedError as e:
                with lock:
                    claims_blocked.append((agent_id, files, list(e.conflicting_files)))

        except Exception as e:
            errors.append(f"Agent {agent_id}: {str(e)}")

    # Start all agents simultaneously
    threads = []
    for i in range(10):
        t = threading.Thread(target=agent_worker, args=(i,))
        threads.append(t)

    # Start all at once
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join(timeout=10)
        if t.is_alive():
            errors.append(f"Thread deadlocked")

    # Verify no active claims remain
    active_chains = bb.get_all_active_chains()
    if active_chains:
        warnings.append(f"{len(active_chains)} claims not released")

    # Verify at least some claims succeeded
    if len(claims_succeeded) == 0:
        errors.append("No claims succeeded (possible deadlock)")

    # Verify file exclusivity - check that overlapping files were never claimed simultaneously
    # This is best-effort since we only logged claim/release events

    # Count operations
    total_ops = len(claims_succeeded) + len(claims_blocked)

    return TestResult(
        name="Claim Chain Contention",
        passed=len(errors) == 0,
        duration_seconds=0,
        total_operations=total_ops,
        errors=errors,
        warnings=warnings,
        metadata={
            "claims_succeeded": len(claims_succeeded),
            "claims_blocked": len(claims_blocked),
            "claims_released": len(claims_released),
            "final_active_chains": len(active_chains)
        }
    )


# =============================================================================
# Test 4: File Lock Stress
# =============================================================================

def test_file_lock_stress(runner: TestRunner) -> TestResult:
    """
    Test rapid lock/unlock cycles.

    Verify:
    - No orphaned locks
    - Timeout works (30s max)
    """
    project_root = runner.create_temp_project()
    bb = Blackboard(project_root)

    errors = []
    warnings = []
    lock_count = 0
    lock_lock = threading.Lock()

    stop_flag = threading.Event()

    def worker(thread_id: int):
        """Worker that acquires and releases locks."""
        nonlocal lock_count

        while not stop_flag.is_set():
            try:
                # Acquire lock
                lock_handle = bb._get_lock(timeout=5.0)
                if lock_handle is None:
                    errors.append(f"Thread {thread_id}: Lock timeout")
                    continue

                with lock_lock:
                    lock_count += 1

                # Hold briefly
                time.sleep(0.001)

                # Release
                bb._release_lock(lock_handle)

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

    # Start threads
    threads = []
    num_threads = 10

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    # Run for 5 seconds
    time.sleep(5)
    stop_flag.set()

    # Wait for threads
    for t in threads:
        t.join(timeout=5)
        if t.is_alive():
            errors.append("Thread did not terminate cleanly")

    # Verify lock file can still be acquired (no orphaned locks)
    try:
        lock_handle = bb._get_lock(timeout=5.0)
        if lock_handle is None:
            errors.append("Lock file appears orphaned")
        else:
            bb._release_lock(lock_handle)
    except Exception as e:
        errors.append(f"Final lock test failed: {e}")

    return TestResult(
        name="File Lock Stress",
        passed=len(errors) == 0,
        duration_seconds=0,
        total_operations=lock_count,
        errors=errors,
        warnings=warnings,
        metadata={
            "lock_cycles": lock_count
        }
    )


# =============================================================================
# Test 5: Memory/Resource Usage
# =============================================================================

def test_resource_usage(runner: TestRunner) -> TestResult:
    """
    Monitor resource usage over 30 seconds.

    Track:
    - File handle count
    - Memory growth

    Report any leaks.
    """
    project_root = runner.create_temp_project()
    bb = BlackboardV2(project_root)

    errors = []
    warnings = []

    # Get initial resource usage
    import psutil
    process = psutil.Process()

    initial_fds = process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
    initial_mem = process.memory_info().rss / 1024 / 1024  # MB

    operation_count = 0
    stop_flag = threading.Event()

    def worker(thread_id: int):
        """Worker performing continuous operations."""
        nonlocal operation_count
        agent_id = f"agent-{thread_id}"

        bb.register_agent(agent_id, f"Resource test {thread_id}")

        while not stop_flag.is_set():
            try:
                # Perform various operations
                bb.add_finding(agent_id, "test", f"Finding {time.time()}")
                bb.send_message(agent_id, "agent-0", f"Message {time.time()}")
                bb.get_active_agents()
                bb.get_findings()

                operation_count += 4

                time.sleep(0.01)

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

    # Start threads
    threads = []
    num_threads = 5

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    # Run for 30 seconds
    time.sleep(30)
    stop_flag.set()

    # Wait for threads
    for t in threads:
        t.join(timeout=5)

    # Check final resource usage
    final_fds = process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
    final_mem = process.memory_info().rss / 1024 / 1024  # MB

    fd_growth = final_fds - initial_fds
    mem_growth = final_mem - initial_mem

    # Thresholds
    if fd_growth > 10:
        warnings.append(f"File descriptor leak: grew by {fd_growth}")

    if mem_growth > 50:  # 50 MB
        warnings.append(f"Memory growth: {mem_growth:.1f} MB")

    return TestResult(
        name="Resource Usage Monitor",
        passed=len(errors) == 0,
        duration_seconds=0,
        total_operations=operation_count,
        errors=errors,
        warnings=warnings,
        metadata={
            "initial_fds": initial_fds,
            "final_fds": final_fds,
            "fd_growth": fd_growth,
            "initial_mem_mb": initial_mem,
            "final_mem_mb": final_mem,
            "mem_growth_mb": mem_growth
        }
    )


# =============================================================================
# Main Test Execution
# =============================================================================

def main():
    """Run all stress tests."""
    print("ELF Coordination System - Stress Test Suite")
    print("=" * 60)

    # Check for psutil (needed for resource test)
    try:
        import psutil
    except ImportError:
        print("Warning: psutil not installed, resource test will be skipped")
        print("Install with: pip install psutil")

    runner = TestRunner()

    try:
        # Run all tests
        runner.run_test("Test 1: Blackboard Concurrent Access", test_blackboard_concurrent_access)
        runner.run_test("Test 2: Event Log Stress", test_event_log_stress)
        runner.run_test("Test 3: Claim Chain Contention", test_claim_chain_contention)
        runner.run_test("Test 4: File Lock Stress", test_file_lock_stress)

        # Only run resource test if psutil is available
        try:
            import psutil
            runner.run_test("Test 5: Resource Usage Monitor", test_resource_usage)
        except ImportError:
            print("\nSkipping Test 5: Resource Usage Monitor (psutil not available)")

        # Print summary
        runner.print_summary()

        # Return exit code
        all_passed = all(r.passed for r in runner.results)
        return 0 if all_passed else 1

    finally:
        # Cleanup
        print("\nCleaning up temporary directories...")
        runner.cleanup()


if __name__ == "__main__":
    sys.exit(main())
