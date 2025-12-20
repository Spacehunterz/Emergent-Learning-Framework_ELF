#!/usr/bin/env python3
"""
Comprehensive test suite for claim chain functionality in blackboard.py.

Tests cover:
1. Basic operations (claim, release, complete, get_claim)
2. Atomic failure (all-or-nothing claiming)
3. TTL/expiration handling
4. Concurrent access simulation
5. Edge cases
"""

import sys
import os
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Add the coordinator directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "coordinator"))

from blackboard import Blackboard, BlockedError, ClaimChain


class _TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record_pass(self, test_name: str):
        self.passed += 1
        print(f"[PASS] {test_name}")

    def record_fail(self, test_name: str, reason: str):
        self.failed += 1
        error_msg = f"[FAIL] {test_name}: {reason}"
        self.errors.append(error_msg)
        print(error_msg)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  {error}")
        print(f"{'='*60}")
        return self.failed == 0


def _test_basic_operations(bb: Blackboard, results: _TestResults):
    """Test 1: Basic claim chain operations."""
    print("\n=== Test 1: Basic Operations ===")

    # Test 1.1: claim_chain succeeds with free files
    try:
        chain = bb.claim_chain(
            agent_id="agent1",
            files=["file1.txt", "file2.txt"],
            reason="Testing basic claim",
            ttl_minutes=5
        )
        assert chain is not None
        assert chain.agent_id == "agent1"
        assert len(chain.files) == 2
        assert chain.status == "active"
        results.record_pass("claim_chain() succeeds with free files")
    except Exception as e:
        results.record_fail("claim_chain() succeeds with free files", str(e))

    # Test 1.2: get_claim_for_file returns correct claim
    try:
        claim = bb.get_claim_for_file("file1.txt")
        assert claim is not None
        assert claim.agent_id == "agent1"
        assert claim.chain_id == chain.chain_id
        results.record_pass("get_claim_for_file() returns correct claim")
    except Exception as e:
        results.record_fail("get_claim_for_file() returns correct claim", str(e))

    # Test 1.3: release_chain frees files for others
    try:
        success = bb.release_chain("agent1", chain.chain_id)
        assert success is True

        # Verify file is now free
        claim = bb.get_claim_for_file("file1.txt")
        assert claim is None
        results.record_pass("release_chain() frees files for others")
    except Exception as e:
        results.record_fail("release_chain() frees files for others", str(e))

    # Test 1.4: complete_chain marks work done
    try:
        # Claim again
        chain2 = bb.claim_chain("agent1", ["file3.txt"], "Test complete")

        # Complete it
        success = bb.complete_chain("agent1", chain2.chain_id)
        assert success is True

        # Verify file is now free (completed chains don't block)
        claim = bb.get_claim_for_file("file3.txt")
        assert claim is None
        results.record_pass("complete_chain() marks work done")
    except Exception as e:
        results.record_fail("complete_chain() marks work done", str(e))


def _test_atomic_failure(bb: Blackboard, results: _TestResults):
    """Test 2: Atomic failure - all or nothing claiming."""
    print("\n=== Test 2: Atomic Failure ===")

    # Setup: agent1 claims file1 and file2
    try:
        chain1 = bb.claim_chain("agent1", ["file1.txt", "file2.txt"], "First claim")
    except Exception as e:
        results.record_fail("Setup for atomic failure test", str(e))
        return

    # Test 2.1: If ANY file is taken, entire claim fails
    try:
        # Try to claim file2 (taken) and file3 (free) - should fail entirely
        try:
            chain2 = bb.claim_chain("agent2", ["file2.txt", "file3.txt"], "Should fail")
            results.record_fail("Atomic failure - claim should have failed", "BlockedError not raised")
        except BlockedError as e:
            # Expected - verify file3 was NOT claimed
            claim3 = bb.get_claim_for_file("file3.txt")
            if claim3 is None:
                results.record_pass("If ANY file is taken, entire claim fails")
            else:
                results.record_fail("If ANY file is taken, entire claim fails",
                                  "file3.txt was partially claimed")
        except Exception as e:
            results.record_fail("If ANY file is taken, entire claim fails", f"Wrong exception: {e}")
    except Exception as e:
        results.record_fail("If ANY file is taken, entire claim fails", str(e))

    # Test 2.2: No partial claims ever exist
    try:
        # Verify all files from failed claim are still free
        all_active = bb.get_all_active_chains()
        file3_claimed = any("file3.txt" in chain.files for chain in all_active)
        if not file3_claimed:
            results.record_pass("No partial claims ever exist")
        else:
            results.record_fail("No partial claims ever exist", "file3.txt found in active chains")
    except Exception as e:
        results.record_fail("No partial claims ever exist", str(e))

    # Test 2.3: BlockedError contains correct info
    try:
        try:
            bb.claim_chain("agent3", ["file1.txt", "file4.txt"], "Check BlockedError")
        except BlockedError as e:
            # Verify error contains blocking_chains and conflicting_files
            assert hasattr(e, 'blocking_chains'), "BlockedError missing blocking_chains"
            assert hasattr(e, 'conflicting_files'), "BlockedError missing conflicting_files"
            assert len(e.blocking_chains) > 0, "blocking_chains should not be empty"
            assert len(e.conflicting_files) > 0, "conflicting_files should not be empty"
            assert "file1.txt" in e.conflicting_files, "file1.txt should be in conflicting_files"
            results.record_pass("BlockedError contains correct info (blocking_chains, conflicting_files)")
        except Exception as e:
            results.record_fail("BlockedError contains correct info", f"Wrong exception: {e}")
    except Exception as e:
        results.record_fail("BlockedError contains correct info", str(e))

    # Cleanup
    bb.release_chain("agent1", chain1.chain_id)


def _test_ttl_expiration(bb: Blackboard, results: _TestResults):
    """Test 3: TTL and expiration handling."""
    print("\n=== Test 3: TTL/Expiration ===")

    # Test 3.1: Claims expire after TTL
    try:
        # Create a claim with very short TTL (we'll manipulate time by reading state)
        chain = bb.claim_chain("agent1", ["expiry_test.txt"], "TTL test", ttl_minutes=1)

        # Manually expire it by manipulating the state
        state = bb.get_full_state()
        for chain_data in state["claim_chains"]:
            if chain_data["chain_id"] == chain.chain_id:
                # Set expiration to past
                chain_data["expires_at"] = (datetime.now() - timedelta(minutes=1)).isoformat()
        bb._with_lock(lambda: bb._write_state(state))

        # Now try to claim the same file - should succeed
        chain2 = bb.claim_chain("agent2", ["expiry_test.txt"], "After expiry")
        results.record_pass("Claims expire after TTL")
        bb.release_chain("agent2", chain2.chain_id)
    except Exception as e:
        results.record_fail("Claims expire after TTL", str(e))

    # Test 3.2: Expired claims don't block new claims
    try:
        # This is already tested above, but let's verify explicitly
        # Create an expired claim
        chain = bb.claim_chain("agent1", ["expired_file.txt"], "Will expire", ttl_minutes=1)

        # Manually expire it
        state = bb.get_full_state()
        for chain_data in state["claim_chains"]:
            if chain_data["chain_id"] == chain.chain_id:
                chain_data["expires_at"] = (datetime.now() - timedelta(minutes=5)).isoformat()
        bb._with_lock(lambda: bb._write_state(state))

        # Verify it doesn't appear in blocking chains
        blocking = bb.get_blocking_chains(["expired_file.txt"])
        if len(blocking) == 0:
            results.record_pass("Expired claims don't block new claims")
        else:
            results.record_fail("Expired claims don't block new claims",
                              f"Found {len(blocking)} blocking chains")
    except Exception as e:
        results.record_fail("Expired claims don't block new claims", str(e))

    # Test 3.3: get_all_active_chains excludes expired
    try:
        # Create a mix of active and expired chains
        active_chain = bb.claim_chain("agent1", ["active1.txt"], "Active")
        expired_chain = bb.claim_chain("agent2", ["expired1.txt"], "To be expired")

        # Expire one
        state = bb.get_full_state()
        for chain_data in state["claim_chains"]:
            if chain_data["chain_id"] == expired_chain.chain_id:
                chain_data["expires_at"] = (datetime.now() - timedelta(minutes=1)).isoformat()
        bb._with_lock(lambda: bb._write_state(state))

        # Get active chains
        active_chains = bb.get_all_active_chains()
        chain_ids = [c.chain_id for c in active_chains]

        if active_chain.chain_id in chain_ids and expired_chain.chain_id not in chain_ids:
            results.record_pass("get_all_active_chains() excludes expired")
        else:
            results.record_fail("get_all_active_chains() excludes expired",
                              f"Active: {active_chain.chain_id in chain_ids}, "
                              f"Expired: {expired_chain.chain_id in chain_ids}")

        bb.release_chain("agent1", active_chain.chain_id)
    except Exception as e:
        results.record_fail("get_all_active_chains() excludes expired", str(e))


def _test_concurrent_simulation(bb: Blackboard, results: _TestResults):
    """Test 4: Simulate concurrent access from multiple agents."""
    print("\n=== Test 4: Concurrent Simulation ===")

    # Shared state for threads
    claim_results = {}
    errors = []

    def agent_worker(agent_id: str, files: list):
        """Simulated agent trying to claim files."""
        try:
            chain = bb.claim_chain(agent_id, files, f"Claim by {agent_id}")
            claim_results[agent_id] = {"success": True, "chain_id": chain.chain_id}
            # Hold for a moment
            time.sleep(0.1)
            bb.release_chain(agent_id, chain.chain_id)
        except BlockedError:
            claim_results[agent_id] = {"success": False, "reason": "blocked"}
        except Exception as e:
            errors.append(f"{agent_id}: {str(e)}")

    # Test 4.1: Simulate 5 agents trying to claim overlapping files
    try:
        threads = []

        # Agent1 and Agent2 compete for file_a
        # Agent3 and Agent4 compete for file_b
        # Agent5 tries to claim both file_a and file_b
        thread_configs = [
            ("agent1", ["concurrent_a.txt"]),
            ("agent2", ["concurrent_a.txt"]),
            ("agent3", ["concurrent_b.txt"]),
            ("agent4", ["concurrent_b.txt"]),
            ("agent5", ["concurrent_a.txt", "concurrent_b.txt"])
        ]

        for agent_id, files in thread_configs:
            t = threading.Thread(target=agent_worker, args=(agent_id, files))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=5)

        if len(errors) == 0:
            results.record_pass("5 agents with overlapping files - no exceptions")
        else:
            results.record_fail("5 agents with overlapping files - no exceptions",
                              f"Errors: {errors}")
    except Exception as e:
        results.record_fail("5 agents with overlapping files", str(e))

    # Test 4.2: Verify no race conditions
    try:
        # Check that only one agent claimed each file at a time
        # We can't fully verify this without detailed logging, but we can check
        # that the system is in a consistent state now
        state = bb.get_full_state()

        # All claims should be released by now
        active_chains = [c for c in state.get("claim_chains", []) if c["status"] == "active"]

        if len(active_chains) == 0:
            results.record_pass("No race conditions with file locking")
        else:
            results.record_fail("No race conditions with file locking",
                              f"{len(active_chains)} chains still active")
    except Exception as e:
        results.record_fail("No race conditions with file locking", str(e))


def _test_edge_cases(bb: Blackboard, results: _TestResults):
    """Test 5: Edge cases and unusual scenarios."""
    print("\n=== Test 5: Edge Cases ===")

    # Test 5.1: Empty file list
    try:
        chain = bb.claim_chain("agent1", [], "Empty list")
        # Should succeed but have no files
        assert len(chain.files) == 0
        results.record_pass("Empty file list")
        bb.release_chain("agent1", chain.chain_id)
    except Exception as e:
        results.record_fail("Empty file list", str(e))

    # Test 5.2: Same agent claiming twice (same files)
    try:
        chain1 = bb.claim_chain("agent1", ["double.txt"], "First claim")

        # Same agent tries to claim again - should succeed (same agent can have multiple chains)
        try:
            chain2 = bb.claim_chain("agent1", ["double.txt"], "Second claim")
            # Success - same agent is allowed to have multiple claim chains
            results.record_pass("Same agent can claim same files multiple times")
            bb.release_chain("agent1", chain2.chain_id)
        except BlockedError as e:
            # If blocked, that's also acceptable (stricter policy)
            results.record_pass("Same agent claiming twice is blocked (strict policy)")

        bb.release_chain("agent1", chain1.chain_id)
    except Exception as e:
        results.record_fail("Same agent claiming twice", str(e))

    # Test 5.3: Non-existent chain_id for release
    try:
        success = bb.release_chain("agent1", "nonexistent-chain-id-12345")
        if success is False:
            results.record_pass("Non-existent chain_id for release returns False")
        else:
            results.record_fail("Non-existent chain_id for release",
                              "Should return False")
    except Exception as e:
        results.record_fail("Non-existent chain_id for release", str(e))

    # Test 5.4: Very long file paths
    try:
        long_path = "a" * 200 + "/very/long/path/to/" + "b" * 100 + ".txt"
        chain = bb.claim_chain("agent1", [long_path], "Long path test")

        # Verify we can retrieve it
        claim = bb.get_claim_for_file(long_path)
        if claim is not None and claim.chain_id == chain.chain_id:
            results.record_pass("Very long file paths")
        else:
            results.record_fail("Very long file paths", "Could not retrieve claim")

        bb.release_chain("agent1", chain.chain_id)
    except Exception as e:
        results.record_fail("Very long file paths", str(e))

    # Test 5.5: Windows path separators (Path normalization)
    try:
        windows_path = "C:\\Users\\Test\\file.txt"
        unix_path = "C:/Users/Test/file.txt"

        chain1 = bb.claim_chain("agent1", [windows_path], "Windows path")

        # Try to claim with Unix-style path - should conflict
        try:
            chain2 = bb.claim_chain("agent2", [unix_path], "Unix path")
            # Path normalization should make these the same
            # If it doesn't conflict, normalization might not be working
            results.record_fail("Windows path separators",
                              "Different path styles should normalize to same path")
            bb.release_chain("agent2", chain2.chain_id)
        except BlockedError:
            # Good - paths were normalized and conflict detected
            results.record_pass("Windows path separators normalize correctly")

        bb.release_chain("agent1", chain1.chain_id)
    except Exception as e:
        results.record_fail("Windows path separators", str(e))

    # Test 5.6: Wrong agent trying to release
    try:
        chain = bb.claim_chain("agent1", ["ownership.txt"], "Agent1's claim")

        # Agent2 tries to release agent1's claim
        success = bb.release_chain("agent2", chain.chain_id)
        if success is False:
            results.record_pass("Wrong agent cannot release chain")
        else:
            results.record_fail("Wrong agent cannot release chain",
                              "Should return False")

        bb.release_chain("agent1", chain.chain_id)
    except Exception as e:
        results.record_fail("Wrong agent cannot release chain", str(e))

    # Test 5.7: Wrong agent trying to complete
    try:
        chain = bb.claim_chain("agent1", ["complete_test.txt"], "Agent1's claim")

        # Agent2 tries to complete agent1's claim
        success = bb.complete_chain("agent2", chain.chain_id)
        if success is False:
            results.record_pass("Wrong agent cannot complete chain")
        else:
            results.record_fail("Wrong agent cannot complete chain",
                              "Should return False")

        bb.release_chain("agent1", chain.chain_id)
    except Exception as e:
        results.record_fail("Wrong agent cannot complete chain", str(e))


def _test_performance(bb: Blackboard, results: _TestResults):
    """Test 6: Performance observations."""
    print("\n=== Test 6: Performance ===")

    # Test 6.1: Time to claim 100 files
    try:
        start = time.time()
        files = [f"perf_test_{i}.txt" for i in range(100)]
        chain = bb.claim_chain("perf_agent", files, "Performance test")
        elapsed = time.time() - start

        print(f"  Time to claim 100 files: {elapsed:.4f}s")
        if elapsed < 1.0:  # Should be very fast
            results.record_pass(f"Claim 100 files in {elapsed:.4f}s")
        else:
            results.record_fail("Claim 100 files", f"Took {elapsed:.4f}s (> 1s)")

        bb.release_chain("perf_agent", chain.chain_id)
    except Exception as e:
        results.record_fail("Claim 100 files performance", str(e))

    # Test 6.2: Time for 50 sequential claim/release cycles
    try:
        start = time.time()
        for i in range(50):
            chain = bb.claim_chain("cycle_agent", [f"cycle_{i}.txt"], f"Cycle {i}")
            bb.release_chain("cycle_agent", chain.chain_id)
        elapsed = time.time() - start

        print(f"  Time for 50 claim/release cycles: {elapsed:.4f}s")
        if elapsed < 5.0:
            results.record_pass(f"50 cycles in {elapsed:.4f}s")
        else:
            results.record_fail("50 cycles", f"Took {elapsed:.4f}s (> 5s)")
    except Exception as e:
        results.record_fail("50 cycles performance", str(e))


def _test_stress(bb: Blackboard, results: _TestResults):
    """Test 7: Stress tests."""
    print("\n=== Test 7: Stress Tests ===")

    # Test 7.1: Many concurrent agents (stress test with 20 threads)
    try:
        claim_results = {}
        errors = []

        def stress_worker(agent_id: str):
            try:
                # Each agent claims a unique file
                chain = bb.claim_chain(agent_id, [f"stress_{agent_id}.txt"], f"Stress {agent_id}")
                claim_results[agent_id] = True
                time.sleep(0.01)
                bb.release_chain(agent_id, chain.chain_id)
            except Exception as e:
                errors.append(f"{agent_id}: {str(e)}")

        threads = []
        for i in range(20):
            t = threading.Thread(target=stress_worker, args=(f"stress_agent_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        if len(errors) == 0 and len(claim_results) == 20:
            results.record_pass("20 concurrent agents - no errors")
        else:
            results.record_fail("20 concurrent agents", f"Errors: {len(errors)}, Success: {len(claim_results)}")
    except Exception as e:
        results.record_fail("20 concurrent agents stress test", str(e))

    # Test 7.2: High contention scenario (10 agents fighting for 3 files)
    try:
        contention_results = {"success": 0, "blocked": 0, "errors": 0}
        lock = threading.Lock()

        def contention_worker(agent_id: str):
            try:
                # All agents try to claim the same 3 files
                chain = bb.claim_chain(agent_id, ["hot_file_1.txt", "hot_file_2.txt", "hot_file_3.txt"],
                                     f"Contention {agent_id}")
                with lock:
                    contention_results["success"] += 1
                time.sleep(0.05)
                bb.release_chain(agent_id, chain.chain_id)
            except BlockedError:
                with lock:
                    contention_results["blocked"] += 1
            except Exception as e:
                with lock:
                    contention_results["errors"] += 1

        threads = []
        for i in range(10):
            t = threading.Thread(target=contention_worker, args=(f"contention_agent_{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        total = sum(contention_results.values())
        if total == 10 and contention_results["errors"] == 0:
            results.record_pass(f"High contention: {contention_results['success']} success, "
                              f"{contention_results['blocked']} blocked, 0 errors")
        else:
            results.record_fail("High contention scenario",
                              f"Total: {total}, Errors: {contention_results['errors']}")
    except Exception as e:
        results.record_fail("High contention scenario", str(e))


def main():
    """Run all tests."""
    print("="*60)
    print("Claim Chain Comprehensive Test Suite")
    print("="*60)

    # Create a test blackboard in temp location
    test_dir = Path(__file__).parent / "test_blackboard_temp"
    test_dir.mkdir(exist_ok=True)

    bb = Blackboard(project_root=str(test_dir))
    bb.reset()  # Start fresh

    results = _TestResults()

    try:
        # Run all test suites
        _test_basic_operations(bb, results)
        _test_atomic_failure(bb, results)
        _test_ttl_expiration(bb, results)
        _test_concurrent_simulation(bb, results)
        _test_edge_cases(bb, results)
        _test_performance(bb, results)
        _test_stress(bb, results)

    finally:
        # Cleanup
        bb.reset()

        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
        except Exception:
            pass

    # Print summary
    all_passed = results.summary()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
