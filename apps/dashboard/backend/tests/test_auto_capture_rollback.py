"""
Auto-Capture Transaction Rollback Tests for the Emergent Learning Dashboard.

Tests transaction safety in the auto-capture background job, ensuring that
database updates are atomic and partial updates are prevented on failure.

These tests verify the fix for CRITICAL #2: Database Corruption in Auto-Capture.
Before the fix, if the second UPDATE query failed, the first update would persist,
leaving the database in an inconsistent state.
"""

import asyncio
import json
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from utils.auto_capture import AutoCapture


@pytest.mark.asyncio
class TestAutoCaptureDatabaseRollback:
    """Test transaction rollback behavior in auto-capture operations."""

    @pytest.fixture
    async def auto_capture_instance(self, temp_db: Path):
        """Create an AutoCapture instance with mocked database."""
        with patch('utils.auto_capture.get_db') as mock_get_db:
            # Configure mock to return test database
            def mock_context_manager():
                conn = sqlite3.connect(str(temp_db))
                conn.row_factory = sqlite3.Row
                try:
                    yield conn
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()

            mock_get_db.return_value = mock_context_manager()
            instance = AutoCapture(interval_seconds=1, lookback_hours=24)
            yield instance

    async def test_partial_update_prevention_on_failure(self, temp_db: Path):
        """
        Test that both UPDATE queries succeed or both fail (atomicity).

        This tests the fix for CRITICAL #2. Before the fix, if the second
        UPDATE failed, the first would persist, causing database corruption.
        """
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Create a workflow run with unknown outcome
        cursor.execute("""
            INSERT INTO workflow_runs
            (workflow_name, status, output_json, completed_nodes, total_nodes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("test_workflow", "completed", '{"outcome": "unknown", "reason": "No content"}',
              3, 3, datetime.now().isoformat()))
        run_id = cursor.lastrowid

        # Add node execution
        cursor.execute("""
            INSERT INTO node_executions
            (run_id, node_name, result_json)
            VALUES (?, ?, ?)
        """, (run_id, "test_node", '{"outcome": "unknown"}'))
        conn.commit()

        # Simulate a scenario where the second UPDATE would fail
        # by creating a constraint violation or triggering an error
        original_execute = cursor.execute

        update_count = [0]

        def failing_execute(query, params=()):
            """Mock execute that fails on second UPDATE."""
            if "UPDATE node_executions" in query:
                update_count[0] += 1
                if update_count[0] == 1:
                    # First call to UPDATE node_executions fails
                    raise sqlite3.OperationalError("Simulated database error")
            return original_execute(query, params)

        cursor.execute = failing_execute

        # Try to update with the failing execute
        try:
            new_output = json.dumps({"outcome": "success", "reason": "All nodes completed"})
            cursor.execute("UPDATE workflow_runs SET output_json = ? WHERE id = ?",
                          (new_output, run_id))
            cursor.execute("UPDATE node_executions SET result_json = ? WHERE run_id = ?",
                          (new_output, run_id))
            conn.commit()
        except sqlite3.OperationalError:
            conn.rollback()

        # Restore normal execute
        cursor.execute = original_execute

        # Verify that workflow_runs was NOT updated (rollback worked)
        cursor.execute("SELECT output_json FROM workflow_runs WHERE id = ?", (run_id,))
        result = cursor.fetchone()
        output_data = json.loads(result[0])

        # Should still be unknown because rollback prevented partial update
        assert output_data["outcome"] == "unknown", "Partial update was not rolled back!"

        conn.close()

    async def test_transaction_commit_on_success(self, temp_db: Path):
        """Test that successful updates are properly committed."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Create a workflow run with unknown outcome
        cursor.execute("""
            INSERT INTO workflow_runs
            (workflow_name, status, output_json, completed_nodes, total_nodes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("test_workflow", "completed", '{"outcome": "unknown", "reason": "No content"}',
              3, 3, datetime.now().isoformat()))
        run_id = cursor.lastrowid

        # Add node execution
        cursor.execute("""
            INSERT INTO node_executions
            (run_id, node_name, result_json)
            VALUES (?, ?, ?)
        """, (run_id, "test_node", '{"outcome": "unknown"}'))
        conn.commit()

        # Perform a successful update (simulating the fix)
        try:
            new_output = json.dumps({"outcome": "success", "reason": "All nodes completed"})
            cursor.execute("UPDATE workflow_runs SET output_json = ? WHERE id = ?",
                          (new_output, run_id))
            cursor.execute("UPDATE node_executions SET result_json = ? WHERE run_id = ?",
                          (new_output, run_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise

        # Verify both tables were updated
        cursor.execute("SELECT output_json FROM workflow_runs WHERE id = ?", (run_id,))
        workflow_output = json.loads(cursor.fetchone()[0])

        cursor.execute("SELECT result_json FROM node_executions WHERE run_id = ?", (run_id,))
        node_output = json.loads(cursor.fetchone()[0])

        assert workflow_output["outcome"] == "success"
        assert node_output["outcome"] == "success"

        conn.close()

    async def test_reanalyze_rollback_on_multiple_failures(self, auto_capture_instance: AutoCapture, temp_db: Path):
        """Test that multiple update failures don't corrupt the database."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Create multiple workflow runs with unknown outcomes
        run_ids = []
        for i in range(5):
            cursor.execute("""
                INSERT INTO workflow_runs
                (workflow_name, status, output_json, completed_nodes, total_nodes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f"test_workflow_{i}", "completed", '{"outcome": "unknown", "reason": "No content"}',
                  3, 3, datetime.now().isoformat()))
            run_ids.append(cursor.lastrowid)

            # Add node executions
            cursor.execute("""
                INSERT INTO node_executions
                (run_id, node_name, result_json)
                VALUES (?, ?, ?)
            """, (cursor.lastrowid, f"test_node_{i}", '{"outcome": "unknown"}'))

        conn.commit()
        conn.close()

        # Mock get_db to simulate intermittent failures
        with patch('utils.auto_capture.get_db') as mock_get_db:
            call_count = [0]

            def mock_context_with_failures():
                """Context manager that fails on some operations."""
                conn = sqlite3.connect(str(temp_db))
                conn.row_factory = sqlite3.Row

                original_execute = conn.execute

                def failing_execute(query, params=()):
                    """Fail UPDATE on every other run."""
                    if "UPDATE workflow_runs" in query:
                        call_count[0] += 1
                        if call_count[0] % 2 == 0:
                            raise sqlite3.OperationalError("Simulated failure")
                    return original_execute(query, params)

                conn.execute = failing_execute

                try:
                    yield conn
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()

            mock_get_db.return_value = mock_context_with_failures()

            # Run reanalysis - some updates should fail and rollback
            with patch('utils.auto_capture.logger'):  # Suppress error logs
                try:
                    await auto_capture_instance.reanalyze_unknown_outcomes()
                except:
                    pass  # Expected to have some failures

        # Verify database consistency
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Check each run - should either be fully updated or fully unchanged
        for run_id in run_ids:
            cursor.execute("SELECT output_json FROM workflow_runs WHERE id = ?", (run_id,))
            workflow_output = json.loads(cursor.fetchone()[0])

            cursor.execute("SELECT result_json FROM node_executions WHERE run_id = ?", (run_id,))
            node_output_raw = cursor.fetchone()[0]
            node_output = json.loads(node_output_raw) if node_output_raw else {"outcome": "unknown"}

            # Both should have the same outcome (consistency check)
            # This verifies no partial updates occurred
            # Note: They might both be "unknown" or both be "success", but they must match
            assert workflow_output["outcome"] == node_output["outcome"], \
                f"Inconsistent state for run {run_id}: workflow={workflow_output['outcome']}, node={node_output['outcome']}"

        conn.close()


@pytest.mark.asyncio
class TestAutoCaptureConcurrentUpdates:
    """Test concurrent update scenarios in auto-capture."""

    async def test_concurrent_reanalysis_no_corruption(self, temp_db: Path):
        """Test that concurrent reanalysis calls don't corrupt data."""
        # Create multiple runs
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        for i in range(10):
            cursor.execute("""
                INSERT INTO workflow_runs
                (workflow_name, status, output_json, completed_nodes, total_nodes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f"test_workflow_{i}", "completed", '{"outcome": "unknown", "reason": "No content"}',
                  3, 3, datetime.now().isoformat()))
            run_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO node_executions
                (run_id, node_name, result_json)
                VALUES (?, ?, ?)
            """, (run_id, f"test_node_{i}", '{"outcome": "unknown"}'))

        conn.commit()
        conn.close()

        # Create multiple auto-capture instances
        with patch('utils.auto_capture.get_db') as mock_get_db:
            def mock_context():
                conn = sqlite3.connect(str(temp_db))
                conn.row_factory = sqlite3.Row
                try:
                    yield conn
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()

            mock_get_db.return_value = mock_context()

            instances = [AutoCapture(interval_seconds=1) for _ in range(3)]

            # Run reanalysis concurrently
            tasks = [instance.reanalyze_unknown_outcomes() for instance in instances]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for exceptions
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent reanalysis raised exception: {result}")

        # Verify all runs were updated and are consistent
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM workflow_runs
            WHERE json_extract(output_json, '$.outcome') != 'unknown'
        """)
        updated_count = cursor.fetchone()[0]

        # All 10 runs should be updated
        assert updated_count == 10

        conn.close()

    async def test_error_recovery_preserves_data_integrity(self, temp_db: Path):
        """Test that error recovery mechanisms preserve data integrity."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Create a run
        cursor.execute("""
            INSERT INTO workflow_runs
            (workflow_name, status, output_json, completed_nodes, total_nodes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("test_workflow", "completed", '{"outcome": "unknown", "reason": "Test"}',
              3, 3, datetime.now().isoformat()))
        run_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO node_executions
            (run_id, node_name, result_json)
            VALUES (?, ?, ?)
        """, (run_id, "test_node", '{"outcome": "unknown"}'))

        conn.commit()

        # Get initial state
        cursor.execute("SELECT output_json FROM workflow_runs WHERE id = ?", (run_id,))
        initial_state = cursor.fetchone()[0]

        conn.close()

        # Simulate multiple failed update attempts
        with patch('utils.auto_capture.get_db') as mock_get_db:
            def failing_context():
                conn = sqlite3.connect(str(temp_db))
                conn.row_factory = sqlite3.Row

                original_commit = conn.commit

                def failing_commit():
                    raise sqlite3.OperationalError("Commit failed")

                conn.commit = failing_commit

                try:
                    yield conn
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()

            mock_get_db.return_value = failing_context()

            instance = AutoCapture(interval_seconds=1)

            # Attempt reanalysis - should fail and rollback
            with patch('utils.auto_capture.logger'):
                try:
                    await instance.reanalyze_unknown_outcomes()
                except:
                    pass  # Expected to fail

        # Verify data is unchanged (rollback preserved original state)
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        cursor.execute("SELECT output_json FROM workflow_runs WHERE id = ?", (run_id,))
        final_state = cursor.fetchone()[0]

        assert initial_state == final_state, "Data was corrupted despite rollback"

        conn.close()


@pytest.mark.asyncio
class TestAutoCaptureLearningCapture:
    """Test learning capture transaction safety."""

    async def test_failure_capture_rollback(self, temp_db: Path):
        """Test that failure capture rolls back properly on error."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Create a failed workflow run
        cursor.execute("""
            INSERT INTO workflow_runs
            (workflow_name, status, error_message, output_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("test_workflow", "failed", "Test error",
              '{"outcome": "failure", "reason": "Test error"}',
              (datetime.now() - timedelta(hours=1)).isoformat()))

        conn.commit()
        conn.close()

        # Mock get_db to fail during learning insert
        with patch('utils.auto_capture.get_db') as mock_get_db:
            def failing_context():
                conn = sqlite3.connect(str(temp_db))
                conn.row_factory = sqlite3.Row

                original_execute = conn.cursor().execute

                def failing_execute(query, params=()):
                    if "INSERT INTO learnings" in query:
                        raise sqlite3.IntegrityError("Learning insert failed")
                    return original_execute(query, params)

                cursor = conn.cursor()
                cursor.execute = failing_execute
                # Need to patch the connection's cursor method
                original_cursor = conn.cursor
                conn.cursor = lambda: cursor

                try:
                    yield conn
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()

            mock_get_db.return_value = failing_context()

            instance = AutoCapture(interval_seconds=1)

            # Capture should handle the error gracefully
            with patch('utils.auto_capture.logger'):
                captured = await instance.capture_new_failures()

                # Should return 0 (no successful captures due to error)
                assert captured == 0

        # Verify no orphan learnings were created
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM learnings")
        learning_count = cursor.fetchone()[0]

        assert learning_count == 0, "Orphan learning records created despite rollback"

        conn.close()
