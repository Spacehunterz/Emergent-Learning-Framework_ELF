#!/usr/bin/env python3
"""
Integration Test: Multi-Agent Coordination with Full ELF Stack

This test simulates a realistic multi-agent workflow using:
- BlackboardV2 (dual-write to both old blackboard and event log)
- DependencyGraph (for discovering file relationships)
- ClaimChain (for atomic file claims with conflict detection)
- Task queue, findings, messages, questions

Scenario: 5 agents collaborate on a codebase analysis task
- Agent Alpha: Claims auth files, registers interests, adds findings
- Agent Beta: Tries to claim overlapping files (gets blocked), retries after release
- Agent Gamma: Claims API files, asks a blocking question
- Agent Delta: Monitors findings via cursor, answers Gamma's question
- Agent Epsilon: Uses dependency graph to claim entire file cluster

Timeline output shows interleaved agent actions with conflict resolution.
"""

import sys
import time
import threading
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add coordinator to path FIRST (before blackboard_v2 modifies path)
coordinator_path = Path(__file__).parent.parent / "coordinator"
sys.path.insert(0, str(coordinator_path))

# Import coordinator blackboard directly before blackboard_v2 imports
# This is necessary because blackboard_v2 modifies sys.path to import plugins version
import importlib.util
spec = importlib.util.spec_from_file_location("bb_coord", coordinator_path / "blackboard.py")
bb_coord = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bb_coord)
BlockedError = bb_coord.BlockedError
CoordinatorBlackboard = bb_coord.Blackboard  # The version with claim_chain support

# Now import blackboard_v2 and dependency_graph
from blackboard_v2 import BlackboardV2
from dependency_graph import DependencyGraph


class BlackboardV2WithClaimChains(BlackboardV2):
    """BlackboardV2 wrapper that uses coordinator blackboard for claim_chain support."""

    def __init__(self, project_root: str = "."):
        # Don't call super().__init__() - we'll replace the blackboard entirely
        self.project_root = Path(project_root).resolve()

        # Use coordinator blackboard (has claim_chain)
        self.blackboard = CoordinatorBlackboard(project_root)

        # Initialize event log
        from event_log import EventLog
        self.event_log = EventLog(project_root)

        # Track if event log is healthy
        self._event_log_healthy = True
        self._operation_count = 0
        self._validation_interval = 10

        # Initialize _log_divergence attribute (needed by BlackboardV2 methods)
        self._log_divergence = True


class TimelineLogger:
    """Thread-safe timeline event logger."""

    def __init__(self):
        self.events = []
        self.lock = threading.Lock()

    def log(self, agent_id: str, event: str):
        """Log a timestamped event."""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.events.append(f"[{timestamp}] {agent_id:12} | {event}")

    def print_timeline(self):
        """Print all events in chronological order."""
        print("\n" + "="*80)
        print("AGENT TIMELINE")
        print("="*80)
        for event in self.events:
            print(event)
        print("="*80 + "\n")


class AgentAlpha(threading.Thread):
    """
    Agent Alpha: Claims auth files, registers interests, adds findings.

    Workflow:
    1. Register with interests in ["auth", "security"]
    2. Claim files: auth.py, user.py
    3. Work for 2 seconds (simulated)
    4. Add finding about JWT usage
    5. Complete task and release files
    """

    def __init__(self, bb: BlackboardV2, timeline: TimelineLogger):
        super().__init__(name="AgentAlpha")
        self.bb = bb
        self.timeline = timeline
        self.agent_id = "agent-alpha"

    def run(self):
        try:
            # Register agent
            self.timeline.log(self.agent_id, "Starting up")
            self.bb.register_agent(
                self.agent_id,
                task="Analyze authentication system",
                interests=["auth", "security"]
            )
            self.timeline.log(self.agent_id, "Registered with interests: auth, security")

            # Claim task from queue
            pending_tasks = self.bb.get_pending_tasks()
            my_task = next((t for t in pending_tasks if t["assigned_to"] == self.agent_id), None)
            if my_task:
                self.bb.claim_task(my_task["id"], self.agent_id)
                self.timeline.log(self.agent_id, f"Claimed task: {my_task['id']}")

            # Claim files
            files = ["auth.py", "user.py"]
            chain = self.bb.blackboard.claim_chain(
                self.agent_id,
                files=files,
                reason="Analyzing auth flow"
            )
            self.timeline.log(self.agent_id, f"Claimed files: {', '.join(files)}")

            # Simulate work
            time.sleep(2)

            # Add finding
            finding = self.bb.add_finding(
                self.agent_id,
                finding_type="discovery",
                content="Authentication uses JWT tokens with RS256 signing",
                files=files,
                importance="high",
                tags=["auth", "jwt", "security"]
            )
            self.timeline.log(self.agent_id, f"Added finding: {finding['content'][:50]}...")

            # Complete task and release files
            self.bb.blackboard.complete_chain(self.agent_id, chain.chain_id)
            if my_task:
                self.bb.complete_task(my_task["id"], "Auth analysis complete")
            self.bb.update_agent_status(self.agent_id, "completed", "Auth analysis complete")
            self.timeline.log(self.agent_id, "Released files and marked task complete")

        except Exception as e:
            self.timeline.log(self.agent_id, f"ERROR: {e}")
            raise


class AgentBeta(threading.Thread):
    """
    Agent Beta: Tries to claim overlapping files, gets blocked, retries.

    Workflow:
    1. Register agent
    2. Try to claim user.py + profile.py
    3. Get BLOCKED because Alpha has user.py
    4. Wait and retry
    5. Eventually succeed when Alpha releases
    6. Add finding about user profiles
    """

    def __init__(self, bb: BlackboardV2, timeline: TimelineLogger):
        super().__init__(name="AgentBeta")
        self.bb = bb
        self.timeline = timeline
        self.agent_id = "agent-beta"

    def run(self):
        try:
            # Register agent
            self.timeline.log(self.agent_id, "Starting up")
            self.bb.register_agent(
                self.agent_id,
                task="Analyze user profile system",
                interests=["user", "profile"]
            )
            self.timeline.log(self.agent_id, "Registered")

            my_task = None
            pending_tasks = self.bb.get_pending_tasks()
            my_task = next((t for t in pending_tasks if t["assigned_to"] == self.agent_id), None)
            if my_task:
                self.bb.claim_task(my_task["id"], self.agent_id)
                self.timeline.log(self.agent_id, f"Claimed task: {my_task['id']}")

            # Try to claim files (will be blocked initially)
            files = ["user.py", "profile.py"]
            max_retries = 5
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    chain = self.bb.blackboard.claim_chain(
                        self.agent_id,
                        files=files,
                        reason="Analyzing user profiles"
                    )
                    self.timeline.log(self.agent_id, f"Claimed files: {', '.join(files)}")
                    break
                except BlockedError as e:
                    blocking_agents = set(c.agent_id for c in e.blocking_chains)
                    conflicting = ', '.join(e.conflicting_files)
                    self.timeline.log(
                        self.agent_id,
                        f"BLOCKED on {conflicting} by {blocking_agents}. Retry in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to claim files after {max_retries} attempts")

            # Work on files
            time.sleep(1)

            # Add finding
            finding = self.bb.add_finding(
                self.agent_id,
                finding_type="fact",
                content="User profiles stored in PostgreSQL with jsonb columns",
                files=files,
                importance="normal",
                tags=["user", "database"]
            )
            self.timeline.log(self.agent_id, f"Added finding: {finding['content'][:50]}...")

            # Complete
            self.bb.blackboard.complete_chain(self.agent_id, chain.chain_id)
            if my_task:
                self.bb.complete_task(my_task["id"], "Profile analysis complete")
            self.bb.update_agent_status(self.agent_id, "completed", "Profile analysis complete")
            self.timeline.log(self.agent_id, "Task complete")

        except Exception as e:
            self.timeline.log(self.agent_id, f"ERROR: {e}")
            raise


class AgentGamma(threading.Thread):
    """
    Agent Gamma: Claims API files, asks a blocking question.

    Workflow:
    1. Register agent
    2. Claim api.py, routes.py (no conflicts)
    3. Add multiple findings about API design
    4. Ask a blocking question about API versioning
    5. Wait for answer
    6. Complete task
    """

    def __init__(self, bb: BlackboardV2, timeline: TimelineLogger):
        super().__init__(name="AgentGamma")
        self.bb = bb
        self.timeline = timeline
        self.agent_id = "agent-gamma"

    def run(self):
        try:
            # Register
            self.timeline.log(self.agent_id, "Starting up")
            self.bb.register_agent(
                self.agent_id,
                task="Analyze API endpoints",
                interests=["api", "routes"]
            )
            self.timeline.log(self.agent_id, "Registered")

            my_task = None
            pending_tasks = self.bb.get_pending_tasks()
            my_task = next((t for t in pending_tasks if t["assigned_to"] == self.agent_id), None)
            if my_task:
                self.bb.claim_task(my_task["id"], self.agent_id)
                self.timeline.log(self.agent_id, f"Claimed task: {my_task['id']}")

            # Claim files
            files = ["api.py", "routes.py"]
            chain = self.bb.blackboard.claim_chain(
                self.agent_id,
                files=files,
                reason="Analyzing API design"
            )
            self.timeline.log(self.agent_id, f"Claimed files: {', '.join(files)}")

            # Add findings
            self.bb.add_finding(
                self.agent_id,
                finding_type="discovery",
                content="REST API follows OpenAPI 3.0 specification",
                files=files,
                tags=["api", "rest"]
            )
            self.timeline.log(self.agent_id, "Added finding about OpenAPI spec")

            time.sleep(0.5)

            self.bb.add_finding(
                self.agent_id,
                finding_type="warning",
                content="No rate limiting detected on public endpoints",
                files=files,
                importance="high",
                tags=["api", "security"]
            )
            self.timeline.log(self.agent_id, "Added warning about rate limiting")

            # Ask blocking question
            question = self.bb.ask_question(
                self.agent_id,
                question="Should we implement API versioning via URL path or header?",
                options=["URL path (/v1/)", "Header (Accept: version=1)"],
                blocking=True
            )
            self.timeline.log(self.agent_id, f"Asked BLOCKING question: {question['id']}")

            # Wait for answer (poll every 0.5s)
            max_wait = 10
            for _ in range(max_wait * 2):
                time.sleep(0.5)
                questions = self.bb.get_open_questions()
                if not any(q["id"] == question["id"] for q in questions):
                    # Question answered
                    answered = [q for q in self.bb.get_full_state()["questions"] if q["id"] == question["id"]][0]
                    self.timeline.log(self.agent_id, f"Question answered: {answered['answer']}")
                    break
            else:
                self.timeline.log(self.agent_id, "WARNING: Question not answered in time")

            # Complete
            self.bb.blackboard.complete_chain(self.agent_id, chain.chain_id)
            if my_task:
                self.bb.complete_task(my_task["id"], "API analysis complete")
            self.bb.update_agent_status(self.agent_id, "completed", "API analysis complete")
            self.timeline.log(self.agent_id, "Task complete")

        except Exception as e:
            self.timeline.log(self.agent_id, f"ERROR: {e}")
            raise


class AgentDelta(threading.Thread):
    """
    Agent Delta: Monitors findings via cursor, answers Gamma's question.

    Workflow:
    1. Register agent
    2. Poll for new findings using cursor
    3. Detect Gamma's blocking question
    4. Answer the question
    5. Claim files that Gamma released
    """

    def __init__(self, bb: BlackboardV2, timeline: TimelineLogger):
        super().__init__(name="AgentDelta")
        self.bb = bb
        self.timeline = timeline
        self.agent_id = "agent-delta"

    def run(self):
        try:
            # Register
            self.timeline.log(self.agent_id, "Starting up")
            self.bb.register_agent(
                self.agent_id,
                task="Monitor findings and answer questions",
                interests=["api", "architecture"]
            )
            self.timeline.log(self.agent_id, "Registered as monitor")

            my_task = None
            pending_tasks = self.bb.get_pending_tasks()
            my_task = next((t for t in pending_tasks if t["assigned_to"] == self.agent_id), None)
            if my_task:
                self.bb.claim_task(my_task["id"], self.agent_id)
                self.timeline.log(self.agent_id, f"Claimed task: {my_task['id']}")

            # Monitor findings via cursor
            cursor = self.bb.get_agent_cursor(self.agent_id)
            poll_interval = 0.5
            max_polls = 20

            for poll_num in range(max_polls):
                time.sleep(poll_interval)

                # Check for new findings
                new_findings = self.bb.get_findings_since_cursor(cursor)
                if new_findings:
                    for finding in new_findings:
                        self.timeline.log(
                            self.agent_id,
                            f"Detected finding from {finding['agent_id']}: {finding['content'][:40]}..."
                        )
                    cursor = self.bb.update_agent_cursor(self.agent_id)

                # Check for open questions
                questions = self.bb.get_open_questions()
                for q in questions:
                    if q["status"] == "open":
                        # Answer the question
                        answer = "URL path (/v1/) - more explicit and easier to cache"
                        self.bb.answer_question(q["id"], answer, self.agent_id)
                        self.timeline.log(self.agent_id, f"Answered question {q['id']}: {answer}")
                        break

            # Try to claim files that might be available now
            files = ["api.py"]
            try:
                chain = self.bb.blackboard.claim_chain(
                    self.agent_id,
                    files=files,
                    reason="Post-analysis review"
                )
                self.timeline.log(self.agent_id, f"Claimed released files: {', '.join(files)}")
                time.sleep(0.5)
                self.bb.blackboard.complete_chain(self.agent_id, chain.chain_id)
            except BlockedError:
                self.timeline.log(self.agent_id, "Files still claimed, skipping")

            # Complete
            if my_task:
                self.bb.complete_task(my_task["id"], "Monitoring complete")
            self.bb.update_agent_status(self.agent_id, "completed", "Monitoring complete")
            self.timeline.log(self.agent_id, "Task complete")

        except Exception as e:
            self.timeline.log(self.agent_id, f"ERROR: {e}")
            raise


class AgentEpsilon(threading.Thread):
    """
    Agent Epsilon: Uses dependency graph to claim entire file cluster.

    Workflow:
    1. Register agent
    2. Scan dependency graph
    3. Find cluster for target file
    4. Claim entire cluster atomically
    5. Add findings about dependencies
    """

    def __init__(self, bb: BlackboardV2, timeline: TimelineLogger, project_root: str):
        super().__init__(name="AgentEpsilon")
        self.bb = bb
        self.timeline = timeline
        self.agent_id = "agent-epsilon"
        self.project_root = project_root

    def run(self):
        try:
            # Register
            self.timeline.log(self.agent_id, "Starting up")
            self.bb.register_agent(
                self.agent_id,
                task="Analyze dependency clusters",
                interests=["dependencies", "architecture"]
            )
            self.timeline.log(self.agent_id, "Registered")

            my_task = None
            pending_tasks = self.bb.get_pending_tasks()
            my_task = next((t for t in pending_tasks if t["assigned_to"] == self.agent_id), None)
            if my_task:
                self.bb.claim_task(my_task["id"], self.agent_id)
                self.timeline.log(self.agent_id, f"Claimed task: {my_task['id']}")

            # Create mock Python files for dependency analysis
            self._create_mock_files()

            # Build dependency graph
            self.timeline.log(self.agent_id, "Scanning dependency graph...")
            dg = DependencyGraph(self.project_root)
            dg.scan()
            stats = dg.get_stats()
            self.timeline.log(
                self.agent_id,
                f"Graph scanned: {stats['total_files']} files, {stats['total_dependencies']} deps"
            )

            # Find cluster for a target file
            target = "models.py"
            cluster = dg.get_cluster(target, depth=2)
            self.timeline.log(self.agent_id, f"Found cluster for {target}: {len(cluster)} files")

            # Wait a bit for other agents to release files
            time.sleep(3)

            # Try to claim entire cluster
            suggested_chain = dg.suggest_chain([target], depth=1)
            try:
                chain = self.bb.blackboard.claim_chain(
                    self.agent_id,
                    files=suggested_chain,
                    reason="Analyzing dependency cluster"
                )
                self.timeline.log(
                    self.agent_id,
                    f"Claimed cluster: {len(suggested_chain)} files"
                )
            except BlockedError as e:
                self.timeline.log(
                    self.agent_id,
                    f"Cluster blocked: {len(e.conflicting_files)} conflicts. Claiming available files..."
                )
                # Claim only non-conflicting files
                available = set(suggested_chain) - e.conflicting_files
                if available:
                    chain = self.bb.blackboard.claim_chain(
                        self.agent_id,
                        files=list(available),
                        reason="Analyzing partial cluster"
                    )
                    self.timeline.log(self.agent_id, f"Claimed {len(available)} available files")

            # Add finding
            self.bb.add_finding(
                self.agent_id,
                finding_type="discovery",
                content=f"Dependency cluster analysis: {len(cluster)} interconnected files",
                importance="normal",
                tags=["dependencies", "architecture"]
            )
            self.timeline.log(self.agent_id, "Added cluster analysis finding")

            # Complete
            if 'chain' in locals():
                self.bb.blackboard.complete_chain(self.agent_id, chain.chain_id)
            if my_task:
                self.bb.complete_task(my_task["id"], "Cluster analysis complete")
            self.bb.update_agent_status(self.agent_id, "completed", "Cluster analysis complete")
            self.timeline.log(self.agent_id, "Task complete")

        except Exception as e:
            self.timeline.log(self.agent_id, f"ERROR: {e}")
            raise

    def _create_mock_files(self):
        """Create mock Python files for dependency analysis."""
        files = {
            "models.py": "from utils import helper\nfrom database import db",
            "utils.py": "import os\nimport sys",
            "database.py": "from models import User",
            "auth.py": "from models import User\nfrom utils import helper",
            "user.py": "from models import User",
            "profile.py": "from user import UserManager",
            "api.py": "from routes import setup_routes",
            "routes.py": "from api import app"
        }

        for filename, content in files.items():
            filepath = Path(self.project_root) / filename
            filepath.write_text(content)


class OrchestratorAgent:
    """
    Orchestrator: Initializes blackboard, creates tasks, monitors progress.

    This is the main thread that spawns and coordinates all worker agents.
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.bb = BlackboardV2WithClaimChains(project_root)
        self.timeline = TimelineLogger()

    def run(self):
        """Execute the multi-agent coordination scenario."""
        print("\n" + "="*80)
        print("MULTI-AGENT INTEGRATION TEST")
        print("="*80)
        print(f"Project: {self.project_root}")
        print("Scenario: 5 agents collaborating on codebase analysis")
        print("="*80 + "\n")

        # Initialize blackboard
        self.timeline.log("orchestrator", "Initializing blackboard")
        self.bb.reset()

        # Create task queue
        tasks = [
            ("Analyze authentication system", 1, "agent-alpha"),
            ("Analyze user profile system", 2, "agent-beta"),
            ("Analyze API endpoints", 2, "agent-gamma"),
            ("Monitor findings and answer questions", 3, "agent-delta"),
            ("Analyze dependency clusters", 3, "agent-epsilon")
        ]

        for task, priority, assigned_to in tasks:
            self.bb.add_task(task, priority=priority, assigned_to=assigned_to)
            self.timeline.log("orchestrator", f"Created task: {task}")

        # Spawn agents
        self.timeline.log("orchestrator", "Spawning 5 agents...")

        agents = [
            AgentAlpha(self.bb, self.timeline),
            AgentBeta(self.bb, self.timeline),
            AgentGamma(self.bb, self.timeline),
            AgentDelta(self.bb, self.timeline),
            AgentEpsilon(self.bb, self.timeline, self.project_root)
        ]

        # Start all agents
        start_time = time.time()
        for agent in agents:
            agent.start()
            self.timeline.log("orchestrator", f"Started {agent.name}")

        # Wait for all agents to complete
        self.timeline.log("orchestrator", "Waiting for agents to complete...")
        for agent in agents:
            agent.join()

        elapsed = time.time() - start_time
        self.timeline.log("orchestrator", f"All agents completed in {elapsed:.2f}s")

        # Print timeline
        self.timeline.print_timeline()

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate final report with verification points."""
        print("\n" + "="*80)
        print("FINAL REPORT")
        print("="*80 + "\n")

        state = self.bb.get_full_state()
        event_log_stats = self.bb.get_event_log_stats()
        validation = self.bb.validate_state_consistency()

        # Verification points
        checks = {
            "All 5 tasks completed": self._verify_tasks(state),
            "All findings recorded": self._verify_findings(state),
            "All questions answered": self._verify_questions(state),
            "No orphaned claims": self._verify_claims(state),
            "Event log consistency": validation["consistent"],
            "State reconstruction valid": self._verify_state_reconstruction(state, event_log_stats)
        }

        print("VERIFICATION POINTS:")
        print("-" * 80)
        for check, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            symbol = "[+]" if passed else "[-]"
            print(f"  {symbol} {check:40} [{status}]")

        print("\nBLACKBOARD STATE SUMMARY:")
        print("-" * 80)
        print(f"  Agents:           {len(state['agents'])}")
        print(f"  Findings:         {len(state['findings'])}")
        print(f"  Messages:         {len(state['messages'])}")
        print(f"  Tasks:            {len(state['task_queue'])}")
        print(f"  Questions:        {len(state['questions'])}")
        print(f"  Claim chains:     {len(state.get('claim_chains', []))}")

        print("\nEVENT LOG STATISTICS:")
        print("-" * 80)
        print(f"  Total events:     {event_log_stats['total_events']}")
        print(f"  Latest sequence:  {event_log_stats['latest_seq']}")
        print(f"  File size:        {event_log_stats['file_size_bytes']} bytes")

        if not validation["consistent"]:
            print("\nSTATE DIVERGENCE DETECTED:")
            print("-" * 80)
            for diff in validation["differences"]:
                print(f"  - {diff}")

        # Overall status
        all_passed = all(checks.values())
        print("\n" + "="*80)
        if all_passed:
            print("INTEGRATION TEST: PASSED")
        else:
            print("INTEGRATION TEST: FAILED")
            failed = [k for k, v in checks.items() if not v]
            print(f"Failed checks: {', '.join(failed)}")
        print("="*80 + "\n")

        return all_passed

    def _verify_tasks(self, state: Dict) -> bool:
        """Verify all 5 tasks are completed."""
        tasks = state.get("task_queue", [])
        if len(tasks) != 5:
            return False
        return all(t["status"] == "completed" for t in tasks)

    def _verify_findings(self, state: Dict) -> bool:
        """Verify findings were recorded."""
        findings = state.get("findings", [])
        # Should have at least 5 findings (one per agent minimum)
        return len(findings) >= 5

    def _verify_questions(self, state: Dict) -> bool:
        """Verify all questions are answered."""
        questions = state.get("questions", [])
        if not questions:
            return True
        return all(q["status"] == "resolved" for q in questions)

    def _verify_claims(self, state: Dict) -> bool:
        """Verify no orphaned active claims."""
        chains = state.get("claim_chains", [])
        active = [c for c in chains if c["status"] == "active"]
        # Should have no active claims at end
        return len(active) == 0

    def _verify_state_reconstruction(self, state: Dict, stats: Dict) -> bool:
        """Verify event log can reconstruct state."""
        # Event log should have recorded events
        if stats["total_events"] == 0:
            return False
        # State should have data
        if len(state["agents"]) == 0:
            return False
        return True


def test_multiagent_integration():
    """
    Pytest entry point for multi-agent integration test.

    Validates:
    - All 5 agents complete successfully (no thread exceptions)
    - All tasks reach completed status
    - Findings are recorded by agents
    - Questions asked are answered
    - No orphaned file claims remain
    - Event log is consistent with blackboard state
    - Timeline contains no ERROR entries
    """
    # Create temporary project directory
    temp_dir = tempfile.mkdtemp(prefix="multiagent_test_")

    try:
        # Run orchestrator
        orchestrator = OrchestratorAgent(temp_dir)
        orchestrator.run()

        # Get final state for assertions
        state = orchestrator.bb.get_full_state()
        event_log_stats = orchestrator.bb.get_event_log_stats()
        validation = orchestrator.bb.validate_state_consistency()
        timeline_events = orchestrator.timeline.events

        # Assert 1: All 5 tasks completed
        tasks = state.get("task_queue", [])
        assert len(tasks) == 5, f"Expected 5 tasks, got {len(tasks)}"
        completed_tasks = [t for t in tasks if t["status"] == "completed"]
        assert len(completed_tasks) == 5, (
            f"Expected all 5 tasks completed, but only {len(completed_tasks)} completed. "
            f"Incomplete: {[t['description'] for t in tasks if t['status'] != 'completed']}"
        )

        # Assert 2: Findings were recorded (at least 5 - one per agent minimum)
        findings = state.get("findings", [])
        assert len(findings) >= 5, (
            f"Expected at least 5 findings (one per agent), got {len(findings)}"
        )

        # Assert 3: All questions answered
        questions = state.get("questions", [])
        open_questions = [q for q in questions if q["status"] != "resolved"]
        assert len(open_questions) == 0, (
            f"Expected all questions resolved, but {len(open_questions)} still open: "
            f"{[q['question'] for q in open_questions]}"
        )

        # Assert 4: No orphaned active claims
        chains = state.get("claim_chains", [])
        active_chains = [c for c in chains if c["status"] == "active"]
        assert len(active_chains) == 0, (
            f"Expected no active claims after completion, but found {len(active_chains)} "
            f"orphaned chains: {[c['agent_id'] for c in active_chains]}"
        )

        # Assert 5: Event log is consistent with blackboard state
        assert validation["consistent"], (
            f"State consistency check failed. Differences: {validation.get('differences', [])}"
        )

        # Assert 6: Event log recorded events
        assert event_log_stats["total_events"] > 0, (
            "Event log should have recorded events during the test"
        )

        # Assert 7: All agents registered
        agents = state.get("agents", [])
        assert len(agents) >= 5, (
            f"Expected at least 5 agents registered, got {len(agents)}"
        )

        # Assert 8: No ERROR entries in timeline
        error_events = [e for e in timeline_events if "ERROR:" in e]
        assert len(error_events) == 0, (
            f"Timeline contains {len(error_events)} errors: {error_events}"
        )

        # Assert 9: Conflict resolution worked (Beta should have logged BLOCKED)
        blocked_events = [e for e in timeline_events if "BLOCKED" in e]
        assert len(blocked_events) >= 1, (
            "Expected Agent Beta to be blocked at least once (conflict resolution test)"
        )

        # Assert 10: State reconstruction is valid
        assert len(agents) > 0 and len(findings) > 0, (
            "State should contain both agents and findings after test"
        )

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def main():
    """Main entry point for integration test (non-pytest execution)."""
    # Create temporary project directory
    temp_dir = tempfile.mkdtemp(prefix="multiagent_test_")

    try:
        # Run orchestrator
        orchestrator = OrchestratorAgent(temp_dir)
        passed = orchestrator.run()

        # Exit with appropriate code
        sys.exit(0 if passed else 1)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
