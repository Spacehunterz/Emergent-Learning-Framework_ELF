#!/usr/bin/env python3
"""
Emergent Learning Framework - Dashboard Query
Provides system health summary, recent operations, error trends, and storage usage.

Usage:
    python dashboard.py [--json] [--detailed]
"""

import sqlite3
import os
import sys
import io
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class Dashboard:
    """Dashboard for Emergent Learning Framework observability."""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the dashboard.

        Args:
            base_path: Base path to the emergent-learning directory.
                      Defaults to ~/.claude/emergent-learning
        """
        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.memory_path = self.base_path / "memory"
        self.db_path = self.memory_path / "index.db"

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get current system health status.

        Returns:
            Dictionary containing latest health check results
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get latest health check
        cursor.execute("""
            SELECT *
            FROM system_health
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        latest = cursor.fetchone()

        if not latest:
            conn.close()
            return {
                'status': 'unknown',
                'message': 'No health checks recorded yet'
            }

        result = dict(latest)

        # Get health trend (last 24 hours)
        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM system_health
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY status
        """)

        trend = {row['status']: row['count'] for row in cursor.fetchall()}

        result['trend_24h'] = trend

        conn.close()

        return result

    def get_recent_operations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent operations from metrics.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of recent operations
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                datetime(timestamp, 'localtime') as time,
                metric_name,
                metric_value,
                tags,
                context
            FROM metrics
            WHERE metric_name = 'operation_count'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        operations = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return operations

    def get_operation_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get operation statistics for the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary containing operation statistics
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Total operations
        cursor.execute("""
            SELECT
                SUM(metric_value) as total,
                COUNT(DISTINCT tags) as unique_ops
            FROM metrics
            WHERE metric_name = 'operation_count'
              AND timestamp > datetime('now', '-' || ? || ' hours')
        """, (hours,))

        totals = cursor.fetchone()

        # Operations by type
        cursor.execute("""
            SELECT
                CASE
                    WHEN tags LIKE '%operation:record_failure%' THEN 'record_failure'
                    WHEN tags LIKE '%operation:record_heuristic%' THEN 'record_heuristic'
                    WHEN tags LIKE '%operation:record_success%' THEN 'record_success'
                    WHEN tags LIKE '%operation:query%' THEN 'query'
                    ELSE 'other'
                END as operation_type,
                SUM(metric_value) as count,
                SUM(CASE WHEN tags LIKE '%status:success%' THEN metric_value ELSE 0 END) as successes,
                SUM(CASE WHEN tags LIKE '%status:failure%' THEN metric_value ELSE 0 END) as failures
            FROM metrics
            WHERE metric_name = 'operation_count'
              AND timestamp > datetime('now', '-' || ? || ' hours')
            GROUP BY operation_type
            ORDER BY count DESC
        """, (hours,))

        by_type = [dict(row) for row in cursor.fetchall()]

        # Calculate success rates
        for op in by_type:
            if op['count'] > 0:
                op['success_rate'] = round((op['successes'] / op['count']) * 100, 2)
            else:
                op['success_rate'] = 0.0

        conn.close()

        return {
            'total_operations': int(totals['total']) if totals['total'] else 0,
            'unique_operation_types': int(totals['unique_ops']) if totals['unique_ops'] else 0,
            'by_type': by_type,
            'time_window_hours': hours
        }

    def get_error_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Get error trends over the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary containing error trend data
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Error count by day
        cursor.execute("""
            SELECT
                date(timestamp) as date,
                SUM(metric_value) as error_count
            FROM metrics
            WHERE metric_name = 'error_count'
              AND timestamp > date('now', '-' || ? || ' days')
            GROUP BY date
            ORDER BY date DESC
        """, (days,))

        by_day = [dict(row) for row in cursor.fetchall()]

        # Failed operations by day
        cursor.execute("""
            SELECT
                date(timestamp) as date,
                SUM(metric_value) as failed_ops
            FROM metrics
            WHERE metric_name = 'operation_count'
              AND tags LIKE '%status:failure%'
              AND timestamp > date('now', '-' || ? || ' days')
            GROUP BY date
            ORDER BY date DESC
        """, (days,))

        failed_ops_by_day = [dict(row) for row in cursor.fetchall()]

        # Recent failures from learnings
        cursor.execute("""
            SELECT
                datetime(created_at, 'localtime') as time,
                title,
                domain,
                severity
            FROM learnings
            WHERE type = 'failure'
              AND created_at > datetime('now', '-' || ? || ' days')
            ORDER BY created_at DESC
            LIMIT 10
        """, (days,))

        recent_failures = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'errors_by_day': by_day,
            'failed_operations_by_day': failed_ops_by_day,
            'recent_failures': recent_failures,
            'time_window_days': days
        }

    def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.

        Returns:
            Dictionary containing storage information
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Current DB size
        db_size_bytes = os.path.getsize(str(self.db_path))
        db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

        # DB size history (last 30 days)
        cursor.execute("""
            SELECT
                date(timestamp) as date,
                AVG(metric_value) as avg_size_mb,
                MAX(metric_value) as max_size_mb
            FROM metrics
            WHERE metric_name LIKE '%db_size%'
              AND timestamp > date('now', '-30 days')
            GROUP BY date
            ORDER BY date DESC
        """)

        size_history = [dict(row) for row in cursor.fetchall()]

        # Record counts by table
        counts = {}
        for table in ['learnings', 'heuristics', 'experiments', 'metrics', 'system_health', 'ceo_reviews']:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                result = cursor.fetchone()
                counts[table] = result['count'] if result else 0
            except sqlite3.OperationalError:
                counts[table] = 0

        # Disk space (from latest health check)
        cursor.execute("""
            SELECT disk_free_mb
            FROM system_health
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        health = cursor.fetchone()
        disk_free_mb = health['disk_free_mb'] if health else None

        conn.close()

        return {
            'database_size_mb': db_size_mb,
            'database_size_bytes': db_size_bytes,
            'size_history': size_history,
            'record_counts': counts,
            'disk_free_mb': disk_free_mb
        }

    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance metrics for operations.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary containing performance data
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Operation durations - simplified query without percentiles for now
        cursor.execute("""
            SELECT
                REPLACE(metric_name, '_duration_ms', '') as operation,
                COUNT(*) as sample_count,
                ROUND(AVG(metric_value), 2) as avg_ms,
                ROUND(MIN(metric_value), 2) as min_ms,
                ROUND(MAX(metric_value), 2) as max_ms,
                ROUND(AVG(metric_value), 2) as p50_ms,
                ROUND(MAX(metric_value), 2) as p95_ms
            FROM metrics
            WHERE metric_name LIKE '%_duration_ms'
              AND timestamp > datetime('now', '-' || ? || ' hours')
            GROUP BY metric_name
            ORDER BY avg_ms DESC
        """, (hours,))

        durations = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'operation_durations': durations,
            'time_window_hours': hours
        }

    def get_full_dashboard(self, detailed: bool = False) -> Dict[str, Any]:
        """
        Get complete dashboard data.

        Args:
            detailed: Include detailed metrics

        Returns:
            Complete dashboard data
        """
        dashboard = {
            'timestamp': datetime.now().isoformat(),
            'system_health': self.get_system_health(),
            'storage': self.get_storage_usage(),
            'operations_24h': self.get_operation_stats(24),
            'errors_7d': self.get_error_trends(7),
        }

        if detailed:
            dashboard['recent_operations'] = self.get_recent_operations(50)
            dashboard['performance_24h'] = self.get_performance_metrics(24)

        return dashboard


def format_dashboard_text(data: Dict[str, Any], detailed: bool = False) -> str:
    """
    Format dashboard data as human-readable text.

    Args:
        data: Dashboard data
        detailed: Include detailed information

    Returns:
        Formatted text output
    """
    lines = []

    lines.append("=" * 80)
    lines.append("EMERGENT LEARNING FRAMEWORK - DASHBOARD")
    lines.append("=" * 80)
    lines.append(f"Generated: {data['timestamp']}")
    lines.append("")

    # System Health
    health = data['system_health']
    lines.append("SYSTEM HEALTH")
    lines.append("-" * 80)

    status = health.get('status', 'unknown').upper()
    status_icon = "✓" if status == "HEALTHY" else ("⚠" if status == "DEGRADED" else "✗")
    lines.append(f"Status: {status_icon} {status}")

    if 'timestamp' in health:
        lines.append(f"Last Check: {health['timestamp']}")

    if 'db_integrity' in health:
        lines.append(f"Database Integrity: {health['db_integrity']}")

    if 'db_size_mb' in health:
        lines.append(f"Database Size: {health['db_size_mb']} MB")

    if 'disk_free_mb' in health and health['disk_free_mb']:
        lines.append(f"Disk Free: {health['disk_free_mb']} MB")

    if 'stale_locks' in health:
        lines.append(f"Stale Locks: {health['stale_locks']}")

    if 'trend_24h' in health and health['trend_24h']:
        lines.append("\n24h Health Trend:")
        for status, count in health['trend_24h'].items():
            lines.append(f"  {status}: {count} checks")

    lines.append("")

    # Storage
    storage = data['storage']
    lines.append("STORAGE USAGE")
    lines.append("-" * 80)
    lines.append(f"Database Size: {storage['database_size_mb']} MB ({storage['database_size_bytes']:,} bytes)")

    if storage.get('disk_free_mb'):
        lines.append(f"Disk Space Free: {storage['disk_free_mb']} MB")

    lines.append("\nRecord Counts:")
    for table, count in sorted(storage['record_counts'].items()):
        lines.append(f"  {table:20s}: {count:6d}")

    if detailed and storage.get('size_history'):
        lines.append("\nDatabase Growth (last 30 days):")
        for entry in storage['size_history'][:10]:
            lines.append(f"  {entry['date']}: {entry['avg_size_mb']:.2f} MB (max: {entry['max_size_mb']:.2f} MB)")

    lines.append("")

    # Operations
    ops = data['operations_24h']
    lines.append(f"OPERATIONS (Last {ops['time_window_hours']} hours)")
    lines.append("-" * 80)
    lines.append(f"Total Operations: {ops['total_operations']}")
    lines.append(f"Unique Types: {ops['unique_operation_types']}")

    if ops['by_type']:
        lines.append("\nBy Operation Type:")
        lines.append(f"{'Type':<20} {'Total':>8} {'Success':>8} {'Failed':>8} {'Rate':>8}")
        lines.append("-" * 80)

        for op in ops['by_type']:
            lines.append(
                f"{op['operation_type']:<20} "
                f"{int(op['count']):8d} "
                f"{int(op['successes']):8d} "
                f"{int(op['failures']):8d} "
                f"{op['success_rate']:7.1f}%"
            )

    lines.append("")

    # Errors
    errors = data['errors_7d']
    lines.append(f"ERROR TRENDS (Last {errors['time_window_days']} days)")
    lines.append("-" * 80)

    if errors['errors_by_day']:
        lines.append("Error Count by Day:")
        for entry in errors['errors_by_day']:
            lines.append(f"  {entry['date']}: {int(entry['error_count'])} errors")
    else:
        lines.append("No error metrics recorded")

    if errors['recent_failures']:
        lines.append("\nRecent Failures:")
        for failure in errors['recent_failures'][:5]:
            severity_icon = "!" * min(int(failure.get('severity', 1)), 5)
            lines.append(f"  [{severity_icon}] {failure['time']}: {failure['title']} ({failure['domain']})")

    lines.append("")

    # Performance (detailed mode)
    if detailed and 'performance_24h' in data:
        perf = data['performance_24h']
        lines.append(f"PERFORMANCE METRICS (Last {perf['time_window_hours']} hours)")
        lines.append("-" * 80)

        if perf['operation_durations']:
            lines.append(f"{'Operation':<30} {'Samples':>8} {'Avg':>8} {'P50':>8} {'P95':>8} {'Max':>8}")
            lines.append("-" * 80)

            for op in perf['operation_durations']:
                lines.append(
                    f"{op['operation']:<30} "
                    f"{int(op['sample_count']):8d} "
                    f"{op['avg_ms']:7.1f}ms "
                    f"{op['p50_ms']:7.1f}ms "
                    f"{op['p95_ms']:7.1f}ms "
                    f"{op['max_ms']:7.1f}ms"
                )

        lines.append("")

    # Recent operations (detailed mode)
    if detailed and 'recent_operations' in data:
        recent_ops = data['recent_operations']
        lines.append(f"RECENT OPERATIONS (Last {len(recent_ops)})")
        lines.append("-" * 80)

        for op in recent_ops[:10]:
            tags = op.get('tags', '')
            lines.append(f"{op['time']}: {tags}")

        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    """Command-line interface for the dashboard."""
    parser = argparse.ArgumentParser(
        description="Emergent Learning Framework - Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dashboard.py
  python dashboard.py --detailed
  python dashboard.py --json
  python dashboard.py --json --detailed > dashboard.json
        """
    )

    parser.add_argument('--base-path', type=str, help='Base path to emergent-learning directory')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--detailed', action='store_true', help='Include detailed metrics')

    args = parser.parse_args()

    try:
        dashboard = Dashboard(base_path=args.base_path)
        data = dashboard.get_full_dashboard(detailed=args.detailed)

        if args.json:
            print(json.dumps(data, indent=2, default=str))
        else:
            print(format_dashboard_text(data, detailed=args.detailed))

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
