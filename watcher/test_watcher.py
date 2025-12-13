#!/usr/bin/env python3
"""
Test Harness for Tiered Watcher System

Tests various scenarios for the watcher loop to ensure correct status detection.

Usage:
    python test_watcher.py --all              # Run all scenarios
    python test_watcher.py --scenario nominal # Run specific scenario
    python test_watcher.py --cleanup          # Clean up test state only
"""

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# Import the watcher module
WATCHER_DIR = Path(__file__).parent
sys.path.insert(0, str(WATCHER_DIR))
import watcher_loop


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = []
        self.failed = []

    def add_pass(self, scenario: str, message: str):
        self.passed.append(f"[PASS] {scenario}: {message}")

    def add_fail(self, scenario: str, message: str):
        self.failed.append(f"[FAIL] {scenario}: {message}")

    def print_summary(self):
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        for result in self.passed:
            print(result)

        for result in self.failed:
            print(result)

        total = len(self.passed) + len(self.failed)
        print(f"\nTotal: {total} | Passed: {len(self.passed)} | Failed: {len(self.failed)}")

        if self.failed:
            print("\nTEST RUN: FAILED")
            return False
        else:
            print("\nTEST RUN: PASSED")
            return True


class WatcherTestHarness:
    """Test harness for watcher system."""

    def __init__(self, use_temp: bool = True):
        """
        Initialize test harness.

        Args:
            use_temp: If True, use temporary directory. If False, use actual .coordination dir.
        """
        self.use_temp = use_temp
        self.original_coordination_dir = None
        self.temp_dir = None
        self.test_coordination_dir = None
        self.results = TestResults()

    def setup(self):
        """Setup test environment."""
        if self.use_temp:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="watcher_test_")
            self.test_coordination_dir = Path(self.temp_dir) / ".coordination"
            self.test_coordination_dir.mkdir(parents=True, exist_ok=True)

            # Monkey-patch watcher_loop to use test directory
            self.original_coordination_dir = watcher_loop.COORDINATION_DIR
            watcher_loop.COORDINATION_DIR = self.test_coordination_dir
            watcher_loop.BLACKBOARD_FILE = self.test_coordination_dir / "blackboard.json"
            watcher_loop.WATCHER_LOG = self.test_coordination_dir / "watcher-log.md"
            watcher_loop.STOP_FILE = self.test_coordination_dir / "watcher-stop"

            print(f"Using temporary test directory: {self.test_coordination_dir}")
        else:
            # Use actual .coordination directory
            self.test_coordination_dir = Path.home() / ".claude" / "emergent-learning" / ".coordination"
            self.test_coordination_dir.mkdir(parents=True, exist_ok=True)
            print(f"Using actual .coordination directory: {self.test_coordination_dir}")

    def cleanup(self):
        """Cleanup test environment."""
        if self.use_temp and self.temp_dir:
            import shutil
            # Restore original paths
            if self.original_coordination_dir:
                watcher_loop.COORDINATION_DIR = self.original_coordination_dir
                watcher_loop.BLACKBOARD_FILE = self.original_coordination_dir / "blackboard.json"
                watcher_loop.WATCHER_LOG = self.original_coordination_dir / "watcher-log.md"
                watcher_loop.STOP_FILE = self.original_coordination_dir / "watcher-stop"

            # Remove temp directory
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
        elif self.test_coordination_dir:
            # Clean up test files from actual directory
            files_to_remove = [
                self.test_coordination_dir / "blackboard.json",
                self.test_coordination_dir / "watcher-stop",
            ]

            # Remove agent_test_*.md files
            for f in self.test_coordination_dir.glob("agent_test_*.md"):
                files_to_remove.append(f)

            for f in files_to_remove:
                if f.exists():
                    f.unlink()
                    print(f"Removed: {f}")

    def create_blackboard(self, agents: Dict[str, Any] = None, error: str = None):
        """Create mock blackboard.json."""
        blackboard = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "agents": agents or {},
            "findings": [],
            "messages": [],
            "task_queue": [],
            "questions": [],
            "context": {},
        }

        if error:
            blackboard["error"] = error

        blackboard_file = self.test_coordination_dir / "blackboard.json"
        blackboard_file.write_text(json.dumps(blackboard, indent=2))
        return blackboard_file

    def create_agent_file(self, agent_id: str, age_seconds: int = 0):
        """Create mock agent markdown file."""
        agent_file = self.test_coordination_dir / f"agent_{agent_id}.md"
        agent_file.write_text(f"# Agent {agent_id}\n\nTest agent file created at {datetime.now()}")

        # Set modification time to simulate age
        if age_seconds > 0:
            mtime = (datetime.now() - timedelta(seconds=age_seconds)).timestamp()
            import os
            os.utime(agent_file, (mtime, mtime))

        return agent_file

    def create_stop_file(self):
        """Create watcher-stop file."""
        stop_file = self.test_coordination_dir / "watcher-stop"
        stop_file.write_text(f"Stop requested at {datetime.now().isoformat()}\n")
        return stop_file

    def parse_watcher_output(self, prompt: str) -> Dict[str, Any]:
        """
        Parse watcher prompt to extract expected status.

        Since we're testing the prompt generation, we analyze the state
        that would be passed to the watcher.
        """
        # Gather state using watcher_loop's function
        state = watcher_loop.gather_state()

        # Analyze state to determine expected status
        result = {
            "state": state,
            "expected_status": "nominal",
            "stop_expected": False,
        }

        # Check stop condition
        if state.get("stop_requested", False):
            result["stop_expected"] = True
            result["expected_status"] = "stop"
            return result

        # Check for errors in blackboard
        blackboard = state.get("blackboard", {})
        if "error" in blackboard:
            result["expected_status"] = "escalate"
            result["reason"] = f"Blackboard error: {blackboard['error']}"
            return result

        # Check for stale agents
        agent_files = state.get("agent_files", [])
        for agent_file in agent_files:
            if agent_file.get("age_seconds", 0) > 120:
                result["expected_status"] = "escalate"
                result["reason"] = f"Stale agent: {agent_file['name']} ({agent_file['age_seconds']}s old)"
                return result

        # Check if all agents are completed
        agents = blackboard.get("agents", {})
        if agents:
            all_completed = all(
                agent.get("status") == "completed"
                for agent in agents.values()
            )
            if all_completed:
                result["stop_expected"] = True
                result["expected_status"] = "complete"
                return result

        # If blackboard is empty or missing agents, might indicate no active swarm
        if not agents and not agent_files:
            result["stop_expected"] = True
            result["expected_status"] = "no_swarm"
            return result

        return result

    def run_scenario(self, scenario: str) -> bool:
        """
        Run a specific test scenario.

        Returns:
            True if test passed, False otherwise.
        """
        print(f"\n{'=' * 60}")
        print(f"SCENARIO: {scenario}")
        print('=' * 60)

        # Clean up any existing test state
        self.cleanup()
        self.setup()

        if scenario == "nominal":
            return self.test_nominal()
        elif scenario == "stale":
            return self.test_stale_agent()
        elif scenario == "error":
            return self.test_blackboard_error()
        elif scenario == "complete":
            return self.test_all_complete()
        elif scenario == "stopped":
            return self.test_stop_file()
        else:
            print(f"Unknown scenario: {scenario}")
            self.results.add_fail(scenario, "Unknown scenario")
            return False

    def test_nominal(self) -> bool:
        """Test nominal case: all agents healthy."""
        scenario = "nominal"

        # Create healthy agents
        agents = {
            "agent1": {
                "task": "test task 1",
                "status": "active",
                "started_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            },
            "agent2": {
                "task": "test task 2",
                "status": "active",
                "started_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            },
        }

        self.create_blackboard(agents=agents)
        self.create_agent_file("test_agent1", age_seconds=30)
        self.create_agent_file("test_agent2", age_seconds=45)

        # Analyze state
        result = self.parse_watcher_output("")

        # Validate
        if result["expected_status"] == "nominal" and not result["stop_expected"]:
            self.results.add_pass(scenario, "Correctly identified nominal state")
            print(f"State: {json.dumps(result['state'], indent=2)}")
            print(f"Expected status: {result['expected_status']}")
            return True
        else:
            self.results.add_fail(
                scenario,
                f"Expected 'nominal', got '{result['expected_status']}'"
            )
            return False

    def test_stale_agent(self) -> bool:
        """Test stale agent detection (>120s old)."""
        scenario = "stale"

        # Create agents with one stale
        agents = {
            "agent1": {
                "task": "test task 1",
                "status": "active",
                "started_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            },
            "agent2": {
                "task": "test task 2 - stale",
                "status": "active",
                "started_at": (datetime.now() - timedelta(seconds=200)).isoformat(),
                "last_seen": (datetime.now() - timedelta(seconds=200)).isoformat(),
            },
        }

        self.create_blackboard(agents=agents)
        self.create_agent_file("test_agent1", age_seconds=30)
        self.create_agent_file("test_agent2", age_seconds=150)  # > 120s

        # Analyze state
        result = self.parse_watcher_output("")

        # Validate
        if result["expected_status"] == "escalate":
            self.results.add_pass(scenario, f"Correctly detected stale agent: {result.get('reason', 'N/A')}")
            print(f"State: {json.dumps(result['state'], indent=2)}")
            print(f"Expected status: {result['expected_status']}")
            print(f"Reason: {result.get('reason', 'N/A')}")
            return True
        else:
            self.results.add_fail(
                scenario,
                f"Expected 'escalate' for stale agent, got '{result['expected_status']}'"
            )
            return False

    def test_blackboard_error(self) -> bool:
        """Test blackboard error detection."""
        scenario = "error"

        # Create blackboard with error
        self.create_blackboard(
            agents={
                "agent1": {
                    "task": "test task",
                    "status": "active",
                    "started_at": datetime.now().isoformat(),
                }
            },
            error="Test error: Something went wrong"
        )

        # Analyze state
        result = self.parse_watcher_output("")

        # Validate
        if result["expected_status"] == "escalate":
            self.results.add_pass(scenario, f"Correctly detected error: {result.get('reason', 'N/A')}")
            print(f"State: {json.dumps(result['state'], indent=2)}")
            print(f"Expected status: {result['expected_status']}")
            print(f"Reason: {result.get('reason', 'N/A')}")
            return True
        else:
            self.results.add_fail(
                scenario,
                f"Expected 'escalate' for error, got '{result['expected_status']}'"
            )
            return False

    def test_all_complete(self) -> bool:
        """Test detection when all agents are completed."""
        scenario = "complete"

        # Create all completed agents
        agents = {
            "agent1": {
                "task": "test task 1",
                "status": "completed",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
            },
            "agent2": {
                "task": "test task 2",
                "status": "completed",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
            },
        }

        self.create_blackboard(agents=agents)

        # Analyze state
        result = self.parse_watcher_output("")

        # Validate
        if result["stop_expected"]:
            self.results.add_pass(scenario, "Correctly detected all agents completed (stop expected)")
            print(f"State: {json.dumps(result['state'], indent=2)}")
            print(f"Expected status: {result['expected_status']}")
            return True
        else:
            self.results.add_fail(
                scenario,
                "Expected stop_expected=True when all agents completed"
            )
            return False

    def test_stop_file(self) -> bool:
        """Test stop file detection."""
        scenario = "stopped"

        # Create normal state but with stop file
        agents = {
            "agent1": {
                "task": "test task",
                "status": "active",
                "started_at": datetime.now().isoformat(),
            }
        }

        self.create_blackboard(agents=agents)
        self.create_stop_file()

        # Analyze state
        result = self.parse_watcher_output("")

        # Validate
        if result["stop_expected"] and result["state"].get("stop_requested"):
            self.results.add_pass(scenario, "Correctly detected stop file (stop expected)")
            print(f"State: {json.dumps(result['state'], indent=2)}")
            print(f"Expected status: {result['expected_status']}")
            return True
        else:
            self.results.add_fail(
                scenario,
                "Expected stop_expected=True when stop file exists"
            )
            return False

    def run_all_scenarios(self):
        """Run all test scenarios."""
        scenarios = ["nominal", "stale", "error", "complete", "stopped"]

        print("=" * 60)
        print("WATCHER TEST HARNESS - Running All Scenarios")
        print("=" * 60)

        for scenario in scenarios:
            self.run_scenario(scenario)

        # Print summary
        return self.results.print_summary()


def main():
    parser = argparse.ArgumentParser(description="Test harness for tiered watcher system")
    parser.add_argument(
        "--scenario",
        choices=["nominal", "stale", "error", "complete", "stopped"],
        help="Run specific scenario"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test state only"
    )
    parser.add_argument(
        "--use-actual-dir",
        action="store_true",
        help="Use actual .coordination directory instead of temp (WARNING: may modify real state)"
    )

    args = parser.parse_args()

    # Create test harness
    use_temp = not args.use_actual_dir
    harness = WatcherTestHarness(use_temp=use_temp)

    try:
        if args.cleanup:
            harness.setup()
            harness.cleanup()
            print("Cleanup complete.")
            return 0

        if args.all:
            success = harness.run_all_scenarios()
            harness.cleanup()
            return 0 if success else 1

        if args.scenario:
            harness.setup()
            success = harness.run_scenario(args.scenario)
            harness.cleanup()
            return 0 if success else 1

        # No arguments - show help
        parser.print_help()
        return 0

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        harness.cleanup()
        return 1
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        harness.cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
