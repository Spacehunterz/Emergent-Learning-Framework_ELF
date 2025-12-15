"""
Auto-Capture Background Job for the Emergent Learning Framework.

This module provides a background job that automatically captures workflow failures
as learnings, enabling continuous learning without manual intervention.

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
    Background job that monitors workflow_runs for failures and automatically
    creates learning records in the learnings table.

    Attributes:
        interval_seconds: How often to check for new failures (default: 60)
        lookback_hours: How far back to look for failures (default: 24)
        running: Whether the capture loop is running
        last_check: Timestamp of the last successful check
        stats: Capture statistics
    """

    def __init__(self, interval_seconds: int = 60, lookback_hours: int = 24):
        """
        Initialize the auto-capture job.

        Args:
            interval_seconds: Interval between capture runs
            lookback_hours: How many hours back to look for failures
        """
        self.interval = interval_seconds
        self.lookback_hours = lookback_hours
        self.running = False
        self.last_check: Optional[datetime] = None
        self.stats = {
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
                captured = await self.capture_new_failures()
                self.stats["runs"] += 1
                self.stats["last_batch_size"] = captured

                if captured > 0:
                    logger.info(f"AutoCapture: captured {captured} new failure(s)")
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
                self.stats["total_captured"] += captured

            self.last_check = datetime.now()
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
