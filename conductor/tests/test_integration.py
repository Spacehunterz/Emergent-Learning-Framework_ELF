#!/usr/bin/env python3
"""
Integration Tests: End-to-end tests for conductor system.

Tests the full workflow from:
1. Workflow definition
2. Conductor execution
3. Hook interception
4. SQLite persistence
5. Trail laying
6. Query and replay

USAGE:
    python test_integration.py              # Run all tests
    python test_integration.py -v           # Verbose output
    python test_integration.py TestWorkflow # Run specific test class
"""

import json
import os
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "plugins" / "agent-coordination" / "utils"))

from conductor import Conductor, Node, NodeType, Edge
from replay import ReplayManager
from dashboard import DashboardGenerator


def init_test_db(db_path: Path):
    """Initialize test database with schema."""
    conn = sqlite3.connect(str(db_path))
    # Create prerequisite table that conductor schema references
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    schema_path = Path(__file__).parent.parent / "schema.sql"
    if schema_path.exists():
        conn.executescript(schema_path.read_text())
    conn.commit()
    conn.close()


class TestDatabaseSetup(unittest.TestCase):
    """Test database schema and setup."""

    def setUp(self):
        """Create temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "memory" / "index.db"
        self.db_path.parent.mkdir(parents=True)

        # Initialize schema using helper
        init_test_db(self.db_path)

        # Create conductor with temp path
        self.conductor = Conductor(base_path=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_schema_exists(self):
        """Test that all required tables exist."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        required_tables = [
            'workflows', 'workflow_edges', 'workflow_runs',
            'node_executions', 'trails', 'conductor_decisions'
        ]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            self.assertIn(table, existing_tables, f"Missing table: {table}")

        conn.close()

    def test_create_workflow(self):
        """Test workflow creation."""
        workflow_id = self.conductor.create_workflow(
            name="test-workflow",
            description="Test workflow",
            nodes=[
                {"id": "node1", "name": "First Node", "node_type": "single",
                 "prompt_template": "Do something"},
                {"id": "node2", "name": "Second Node", "node_type": "single",
                 "prompt_template": "Do something else"}
            ],
            edges=[
                {"from_node": "__start__", "to_node": "node1"},
                {"from_node": "node1", "to_node": "node2"},
                {"from_node": "node2", "to_node": "__end__"}
            ]
        )

        self.assertIsNotNone(workflow_id)
        self.assertGreater(workflow_id, 0)

        # Retrieve and verify
        workflow = self.conductor.get_workflow("test-workflow")
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow["name"], "test-workflow")
        self.assertEqual(len(workflow["nodes"]), 2)
        self.assertEqual(len(workflow["edges"]), 3)


class TestWorkflowExecution(unittest.TestCase):
    """Test workflow execution."""

    def setUp(self):
        """Create temp database and conductor."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "memory" / "index.db"
        self.db_path.parent.mkdir(parents=True)

        # Initialize schema using helper
        init_test_db(self.db_path)

        self.conductor = Conductor(base_path=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_start_run(self):
        """Test starting a workflow run."""
        run_id = self.conductor.start_run(
            workflow_name="test-run",
            input_data={"param": "value"}
        )

        self.assertIsNotNone(run_id)
        self.assertGreater(run_id, 0)

        # Verify run exists
        run = self.conductor.get_run(run_id)
        self.assertIsNotNone(run)
        self.assertEqual(run["status"], "running")
        self.assertEqual(run["input"]["param"], "value")

    def test_record_node_execution(self):
        """Test recording node execution."""
        run_id = self.conductor.start_run(workflow_name="exec-test")

        node = Node(
            id="test-node",
            name="Test Node",
            node_type=NodeType.SINGLE,
            prompt_template="Test prompt"
        )

        exec_id = self.conductor.record_node_start(
            run_id=run_id,
            node=node,
            prompt="Test prompt"
        )

        self.assertIsNotNone(exec_id)

        # Complete the node
        self.conductor.record_node_completion(
            exec_id=exec_id,
            result_text="Test result",
            result_dict={"output": "data"},
            findings=[{"type": "fact", "content": "Test finding"}],
            duration_ms=100
        )

        # Verify
        executions = self.conductor.get_node_executions(run_id)
        self.assertEqual(len(executions), 1)
        self.assertEqual(executions[0]["status"], "completed")
        self.assertEqual(executions[0]["findings"][0]["type"], "fact")

    def test_record_node_failure(self):
        """Test recording node failure."""
        run_id = self.conductor.start_run(workflow_name="fail-test")

        node = Node(
            id="fail-node",
            name="Failing Node",
            node_type=NodeType.SINGLE,
            prompt_template="This will fail"
        )

        exec_id = self.conductor.record_node_start(run_id, node, "Prompt")
        self.conductor.record_node_failure(
            exec_id=exec_id,
            error_message="Test error",
            error_type="test_failure",
            duration_ms=50
        )

        executions = self.conductor.get_node_executions(run_id)
        self.assertEqual(executions[0]["status"], "failed")
        self.assertEqual(executions[0]["error_message"], "Test error")


class TestTrails(unittest.TestCase):
    """Test pheromone trail functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "memory" / "index.db"
        self.db_path.parent.mkdir(parents=True)

        # Initialize schema using helper
        init_test_db(self.db_path)

        self.conductor = Conductor(base_path=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_lay_trail(self):
        """Test laying a pheromone trail."""
        run_id = self.conductor.start_run(workflow_name="trail-test")

        self.conductor.lay_trail(
            run_id=run_id,
            location="src/main.py",
            scent="discovery",
            strength=0.8,
            agent_id="test-agent",
            message="Found important code"
        )

        trails = self.conductor.get_trails(location="main.py")
        self.assertEqual(len(trails), 1)
        self.assertEqual(trails[0]["scent"], "discovery")
        self.assertEqual(trails[0]["strength"], 0.8)

    def test_hot_spots(self):
        """Test hot spots aggregation."""
        run_id = self.conductor.start_run(workflow_name="hotspot-test")

        # Lay multiple trails at same location
        for i in range(3):
            self.conductor.lay_trail(
                run_id=run_id,
                location="src/critical.py",
                scent="warning",
                strength=0.5,
                agent_id=f"agent-{i}"
            )

        hot_spots = self.conductor.get_hot_spots(run_id)
        self.assertEqual(len(hot_spots), 1)
        self.assertEqual(hot_spots[0]["trail_count"], 3)
        self.assertAlmostEqual(hot_spots[0]["total_strength"], 1.5, places=2)

    def test_trail_decay(self):
        """Test trail strength decay."""
        run_id = self.conductor.start_run(workflow_name="decay-test")

        self.conductor.lay_trail(
            run_id=run_id,
            location="test.py",
            scent="hot",
            strength=1.0
        )

        # Decay trails
        self.conductor.decay_trails(decay_rate=0.5)

        trails = self.conductor.get_trails()
        self.assertAlmostEqual(trails[0]["strength"], 0.5, places=2)


class TestReplay(unittest.TestCase):
    """Test replay functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "memory" / "index.db"
        self.db_path.parent.mkdir(parents=True)

        # Initialize schema using helper
        init_test_db(self.db_path)

        self.conductor = Conductor(base_path=self.temp_dir)
        self.replay = ReplayManager(base_path=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_replay_plan(self):
        """Test generating replay plan."""
        run_id = self.conductor.start_run(workflow_name="replay-test")

        # Create some executions
        for i in range(3):
            node = Node(
                id=f"node{i}",
                name=f"Node {i}",
                node_type=NodeType.SINGLE,
                prompt_template=f"Prompt {i}"
            )
            exec_id = self.conductor.record_node_start(run_id, node, f"Prompt {i}")
            self.conductor.record_node_completion(exec_id, f"Result {i}")

        plan = self.replay.get_replay_plan(run_id, from_node="node1")

        self.assertEqual(len(plan["nodes_to_skip"]), 1)  # node0
        self.assertEqual(len(plan["nodes_to_replay"]), 2)  # node1, node2

    def test_retry_failed(self):
        """Test retrying failed nodes."""
        run_id = self.conductor.start_run(workflow_name="retry-test")

        # Create one success and one failure
        node1 = Node(id="success", name="Success", node_type=NodeType.SINGLE, prompt_template="P1")
        exec1 = self.conductor.record_node_start(run_id, node1, "P1")
        self.conductor.record_node_completion(exec1, "OK")

        node2 = Node(id="failure", name="Failure", node_type=NodeType.SINGLE, prompt_template="P2")
        exec2 = self.conductor.record_node_start(run_id, node2, "P2")
        self.conductor.record_node_failure(exec2, "Test error")

        # Get retry plan
        result = self.replay.retry_failed_nodes(run_id, dry_run=True)

        self.assertEqual(result["failed_nodes"], 1)
        self.assertEqual(result["nodes"][0]["node_id"], "failure")


class TestDashboard(unittest.TestCase):
    """Test dashboard generation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "memory" / "index.db"
        self.db_path.parent.mkdir(parents=True)

        # Initialize schema using helper
        init_test_db(self.db_path)

        self.conductor = Conductor(base_path=self.temp_dir)
        self.dashboard = DashboardGenerator(base_path=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_html(self):
        """Test HTML dashboard generation."""
        # Create some data
        run_id = self.conductor.start_run(workflow_name="dashboard-test")
        node = Node(id="n1", name="Test", node_type=NodeType.SINGLE, prompt_template="P")
        exec_id = self.conductor.record_node_start(run_id, node, "P")
        self.conductor.record_node_completion(exec_id, "Done")
        self.conductor.lay_trail(run_id, "test.py", "discovery")

        # Generate dashboard
        data = self.dashboard.get_dashboard_data()
        html = self.dashboard.generate_html(data)

        self.assertIn("Conductor Dashboard", html)
        self.assertIn("dashboard-test", html)
        self.assertIn("test.py", html)


class TestSQLiteBridge(unittest.TestCase):
    """Test SQLite bridge from hooks."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "memory" / "index.db"
        self.db_path.parent.mkdir(parents=True)

        # Initialize schema using helper
        init_test_db(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_import_bridge(self):
        """Test that SQLite bridge can be imported."""
        try:
            from sqlite_bridge import SQLiteBridge
            bridge = SQLiteBridge()
            # Override path for testing
            bridge.db_path = self.db_path
            self.assertIsNotNone(bridge._get_connection())
            bridge.close()
        except ImportError:
            self.skipTest("sqlite_bridge not in path")


class TestEndToEnd(unittest.TestCase):
    """Full end-to-end integration test."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "memory" / "index.db"
        self.db_path.parent.mkdir(parents=True)

        # Initialize schema using helper
        init_test_db(self.db_path)

        self.conductor = Conductor(base_path=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_workflow_cycle(self):
        """Test complete workflow: create, execute, query, replay."""
        # 1. Create workflow
        workflow_id = self.conductor.create_workflow(
            name="e2e-test",
            description="End-to-end test",
            nodes=[
                {"id": "scout", "name": "Scout", "node_type": "single",
                 "prompt_template": "Find files"},
                {"id": "analyze", "name": "Analyze", "node_type": "single",
                 "prompt_template": "Analyze {scout_result}"},
                {"id": "report", "name": "Report", "node_type": "single",
                 "prompt_template": "Report findings"}
            ],
            edges=[
                {"from_node": "__start__", "to_node": "scout"},
                {"from_node": "scout", "to_node": "analyze"},
                {"from_node": "analyze", "to_node": "report"},
                {"from_node": "report", "to_node": "__end__"}
            ]
        )
        self.assertIsNotNone(workflow_id)

        # 2. Start run
        run_id = self.conductor.start_run("e2e-test", workflow_id)
        self.assertIsNotNone(run_id)

        # 3. Execute nodes manually (simulating executor)
        nodes = [
            ("scout", "Scout", "Found 10 files"),
            ("analyze", "Analyze", "3 issues found"),
            ("report", "Report", "Report complete")
        ]

        for node_id, node_name, result in nodes:
            node = Node(
                id=node_id,
                name=node_name,
                node_type=NodeType.SINGLE,
                prompt_template="test"
            )
            exec_id = self.conductor.record_node_start(run_id, node, "test prompt")
            self.conductor.record_node_completion(
                exec_id,
                result_text=result,
                result_dict={f"{node_id}_result": result}
            )

            # Lay trail
            self.conductor.lay_trail(
                run_id=run_id,
                location=f"{node_id}.py",
                scent="discovery",
                agent_id=f"agent-{node_id}"
            )

        # 4. Complete run
        self.conductor.update_run_status(run_id, "completed")

        # 5. Query results
        run = self.conductor.get_run(run_id)
        self.assertEqual(run["status"], "completed")

        executions = self.conductor.get_node_executions(run_id)
        self.assertEqual(len(executions), 3)

        trails = self.conductor.get_trails(run_id=run_id)
        self.assertEqual(len(trails), 3)

        decisions = self.conductor.get_decisions(run_id)
        self.assertGreater(len(decisions), 0)

        # 6. Test replay
        replay = ReplayManager(base_path=self.temp_dir)
        plan = replay.get_replay_plan(run_id, from_node="analyze")

        self.assertEqual(len(plan["nodes_to_skip"]), 1)  # scout
        self.assertEqual(len(plan["nodes_to_replay"]), 2)  # analyze, report

        # 7. Generate dashboard
        dashboard = DashboardGenerator(base_path=self.temp_dir)
        data = dashboard.get_dashboard_data(run_id=run_id)

        self.assertIn("runs", data)
        self.assertIn("hotspots", data)
        self.assertIsNotNone(data.get("selected_run"))


def run_tests():
    """Run all tests with verbosity."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_tests())
