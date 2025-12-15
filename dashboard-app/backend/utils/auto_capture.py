"""
Auto-Capture Background Job for the Emergent Learning Framework.

This module provides a background job that automatically captures workflow outcomes
(both failures AND successes) as learnings, enabling continuous learning without
manual intervention.

Usage:
    from utils.auto_capture import AutoCapture

    auto_capture = AutoCapture(interval_seconds=60)

    # In FastAPI startup:
    @app.on_event("startup")
    async def start_auto_capture():
        asyncio.create_task(auto_capture.start())

    @app.on_event("shutdown")
    async def stop_auto_capture():
        auto_capture.stop()
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from utils.database import get_db

logger = logging.getLogger(__name__)


class AutoCapture:
    """
    Background job that monitors workflow_runs for outcomes (failures AND successes)
    and automatically creates learning records in the learnings table.

    Attributes:
        interval_seconds: How often to check for new outcomes (default: 60)
        lookback_hours: How far back to look for outcomes (default: 24)
        running: Whether the capture loop is running
        last_check: Timestamp of the last successful check
        stats: Capture statistics (failures and successes tracked separately)
    """

    def __init__(self, interval_seconds: int = 60, lookback_hours: int = 24):
        """
        Initialize the auto-capture job.

        Args:
            interval_seconds: Interval between capture runs
            lookback_hours: How many hours back to look for outcomes
        """
        self.interval = interval_seconds
        self.lookback_hours = lookback_hours
        self.running = False
        self.last_check: Optional[datetime] = None
        self.stats = {
            "failures_captured": 0,
            "successes_captured": 0,
            "total_captured": 0,
            "last_batch_size": 0,
            "errors": 0,
            "runs": 0,
        }

    async def start(self):
        """Start the auto-capture background loop."""
        self.running = True
        logger.info(
            f"AutoCapture started: interval={self.interval}s, lookback={self.lookback_hours}h"
        )

        while self.running:
            try:
                # Capture both failures and successes
                failures = await self.capture_new_failures()
                successes = await self.capture_new_successes()
                total = failures + successes

                self.stats["runs"] += 1
                self.stats["last_batch_size"] = total

                if failures > 0:
                    logger.info(f"AutoCapture: captured {failures} new failure(s)")
                if successes > 0:
                    logger.info(f"AutoCapture: captured {successes} new success(es)")
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"AutoCapture error: {e}")

            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop the auto-capture background loop."""
        self.running = False
        logger.info("AutoCapture stopped")

    async def capture_new_failures(self) -> int:
        """
        Convert new workflow failures to learnings.

        Returns:
            Number of failures captured
        """
        with get_db() as conn:
            cursor = conn.cursor()

            # Find failures not yet captured
            cursor.execute(
                """
                SELECT wr.id, wr.workflow_name, wr.error_message, wr.created_at
                FROM workflow_runs wr
                WHERE wr.status IN ('failed', 'cancelled')
                AND wr.created_at > datetime('now', ?)
                AND NOT EXISTS (
                    SELECT 1 FROM learnings l
                    WHERE l.filepath = 'workflow_runs/' || wr.id
                    AND l.type = 'failure'
                )
                """,
                (f"-{self.lookback_hours} hours",),
            )

            failures = cursor.fetchall()
            captured = 0

            for f in failures:
                run_id, workflow_name, error_message, created_at = f
                title = f"Workflow failed: {workflow_name} [run:{run_id}]"
                summary = error_message or "No error message"

                try:
                    cursor.execute(
                        """
                        INSERT INTO learnings (type, filepath, title, summary, domain, severity, created_at)
                        VALUES ('failure', ?, ?, ?, 'workflow', 3, ?)
                        """,
                        (f"workflow_runs/{run_id}", title, summary, created_at),
                    )
                    captured += 1
                except Exception as e:
                    logger.warning(f"Failed to capture run {run_id}: {e}")

            if captured > 0:
                # Record capture metric
                cursor.execute(
                    """
                    INSERT INTO metrics (metric_type, metric_name, metric_value, context)
                    VALUES ('auto_failure_capture', 'background_job', ?, 'auto_capture.py')
                    """,
                    (captured,),
                )
                conn.commit()
                self.stats["failures_captured"] += captured
                self.stats["total_captured"] += captured

            self.last_check = datetime.now()
            return captured

    async def capture_new_successes(self) -> int:
        """
        Convert new workflow successes to learnings.

        Captures completed workflow runs as success learnings, enabling
        the system to learn from what works, not just what fails.

        Returns:
            Number of successes captured
        """
        with get_db() as conn:
            cursor = conn.cursor()

            # Find completed runs not yet captured as successes
            cursor.execute(
                """
                SELECT wr.id, wr.workflow_name, wr.output_json, wr.created_at,
                       wr.completed_nodes, wr.total_nodes
                FROM workflow_runs wr
                WHERE wr.status = 'completed'
                AND wr.created_at > datetime('now', ?)
                AND NOT EXISTS (
                    SELECT 1 FROM learnings l
                    WHERE l.filepath = 'workflow_runs/' || wr.id
                    AND l.type = 'success'
                )
                """,
                (f"-{self.lookback_hours} hours",),
            )

            successes = cursor.fetchall()
            captured = 0

            for s in successes:
                run_id, workflow_name, output_json, created_at, completed_nodes, total_nodes = s
                title = f"Workflow completed: {workflow_name} [run:{run_id}]"

                # Build summary from available data
                summary_parts = []
                if completed_nodes and total_nodes:
                    summary_parts.append(f"Completed {completed_nodes}/{total_nodes} nodes")
                if output_json and output_json != '{}':
                    # Truncate long output
                    output_preview = output_json[:200] + "..." if len(output_json) > 200 else output_json
                    summary_parts.append(f"Output: {output_preview}")

                summary = ". ".join(summary_parts) if summary_parts else "Workflow completed successfully"

                try:
                    cursor.execute(
                        """
                        INSERT INTO learnings (type, filepath, title, summary, domain, severity, created_at)
                        VALUES ('success', ?, ?, ?, 'workflow', 1, ?)
                        """,
                        (f"workflow_runs/{run_id}", title, summary, created_at),
                    )
                    captured += 1
                except Exception as e:
                    logger.warning(f"Failed to capture success run {run_id}: {e}")

            if captured > 0:
                # Record capture metric
                cursor.execute(
                    """
                    INSERT INTO metrics (metric_type, metric_name, metric_value, context)
                    VALUES ('auto_success_capture', 'background_job', ?, 'auto_capture.py')
                    """,
                    (captured,),
                )
                conn.commit()
                self.stats["successes_captured"] += captured
                self.stats["total_captured"] += captured

            return captured

    def get_status(self) -> dict:
        """
        Get the current status of the auto-capture job.

        Returns:
            Dictionary with status information
        """
        return {
            "running": self.running,
            "interval_seconds": self.interval,
            "lookback_hours": self.lookback_hours,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "stats": self.stats.copy(),
        }


# Global instance for easy import
auto_capture = AutoCapture()
