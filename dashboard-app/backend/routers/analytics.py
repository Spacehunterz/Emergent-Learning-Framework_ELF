"""
Analytics Router - Stats, timeline, learning velocity, events, anomalies, domains.
"""

from fastapi import APIRouter
from utils import get_db, dict_from_row

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/stats")
async def get_stats():
    """Get overall statistics."""
    with get_db() as conn:
        cursor = conn.cursor()

        stats = {}

        # Counts
        cursor.execute("SELECT COUNT(*) FROM workflow_runs")
        stats["total_runs"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM node_executions")
        stats["total_executions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trails")
        stats["total_trails"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM heuristics")
        stats["total_heuristics"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")
        stats["golden_rules"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM learnings")
        stats["total_learnings"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM learnings WHERE type = 'failure'")
        stats["failures"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM learnings WHERE type = 'success'")
        stats["successes"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM decisions")
        stats["total_decisions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM decisions WHERE status = 'accepted'")
        stats["accepted_decisions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM decisions WHERE status = 'superseded'")
        stats["superseded_decisions"] = cursor.fetchone()[0]

        # Spike reports stats
        try:
            cursor.execute("SELECT COUNT(*) FROM spike_reports")
            stats["total_spike_reports"] = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(usefulness_score) FROM spike_reports WHERE usefulness_score > 0")
            stats["avg_spike_usefulness"] = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(time_invested_minutes) FROM spike_reports")
            stats["total_spike_time_invested"] = cursor.fetchone()[0] or 0
        except Exception:
            stats["total_spike_reports"] = 0
            stats["avg_spike_usefulness"] = 0
            stats["total_spike_time_invested"] = 0

        # Get actual run success/failure counts from workflow_runs status
        cursor.execute("SELECT COUNT(*) FROM workflow_runs WHERE status = 'completed'")
        stats["successful_runs"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM workflow_runs WHERE status IN ('failed', 'cancelled')")
        stats["failed_runs"] = cursor.fetchone()[0]

        # Averages
        cursor.execute("SELECT AVG(confidence) FROM heuristics")
        stats["avg_confidence"] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(times_validated) FROM heuristics")
        stats["total_validations"] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(times_violated) FROM heuristics")
        stats["total_violations"] = cursor.fetchone()[0] or 0

        # Recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM metrics
            WHERE timestamp > datetime('now', '-1 hour')
        """)
        stats["metrics_last_hour"] = cursor.fetchone()[0]

        # Runs today (actual workflow runs in last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM workflow_runs
            WHERE created_at > datetime('now', '-24 hours')
        """)
        stats["runs_today"] = cursor.fetchone()[0]

        # Query statistics
        cursor.execute("SELECT COUNT(*) FROM building_queries")
        stats["total_queries"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM building_queries
            WHERE created_at > datetime('now', '-24 hours')
        """)
        stats["queries_today"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT AVG(duration_ms) FROM building_queries
            WHERE duration_ms IS NOT NULL
        """)
        stats["avg_query_duration_ms"] = cursor.fetchone()[0] or 0

        # Invariant statistics
        cursor.execute("SELECT COUNT(*) FROM invariants")
        stats["total_invariants"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM invariants WHERE status = 'active'")
        stats["active_invariants"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM invariants WHERE status = 'violated'")
        stats["violated_invariants"] = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(violation_count) FROM invariants")
        stats["total_invariant_violations"] = cursor.fetchone()[0] or 0

        return stats


@router.get("/timeline")
async def get_timeline(days: int = 7):
    """Get activity timeline data."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Runs by day
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as runs
            FROM workflow_runs
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        runs_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Trails by day
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as trails, SUM(strength) as strength
            FROM trails
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        trails_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Validations by day
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as validations
            FROM metrics
            WHERE metric_type = 'heuristic_validated'
              AND timestamp > datetime('now', ?)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (f'-{days} days',))
        validations_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Failures by day
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as failures
            FROM metrics
            WHERE metric_type = 'auto_failure_capture'
              AND timestamp > datetime('now', ?)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (f'-{days} days',))
        failures_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        return {
            "runs": runs_by_day,
            "trails": trails_by_day,
            "validations": validations_by_day,
            "failures": failures_by_day
        }


@router.get("/learning-velocity")
async def get_learning_velocity(days: int = 30):
    """Get learning velocity metrics over time."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Heuristics created per day
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM heuristics
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        heuristics_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Learnings created per day
        cursor.execute("""
            SELECT DATE(created_at) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN type = 'failure' THEN 1 ELSE 0 END) as failures,
                   SUM(CASE WHEN type = 'success' THEN 1 ELSE 0 END) as successes
            FROM learnings
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        learnings_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Golden rule promotions per day
        cursor.execute("""
            SELECT DATE(updated_at) as date, COUNT(*) as count
            FROM heuristics
            WHERE is_golden = 1
              AND updated_at > datetime('now', ?)
              AND updated_at > created_at
            GROUP BY DATE(updated_at)
            ORDER BY date
        """, (f'-{days} days',))
        promotions_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Confidence improvement rate - track average confidence over time
        cursor.execute("""
            SELECT DATE(updated_at) as date, AVG(confidence) as avg_confidence
            FROM heuristics
            WHERE updated_at > datetime('now', ?)
            GROUP BY DATE(updated_at)
            ORDER BY date
        """, (f'-{days} days',))
        confidence_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Calculate weekly aggregates for trend analysis
        cursor.execute("""
            SELECT
                strftime('%Y-W%W', created_at) as week,
                COUNT(*) as heuristics_count
            FROM heuristics
            WHERE created_at > datetime('now', ?)
            GROUP BY week
            ORDER BY week
        """, (f'-{days} days',))
        heuristics_by_week = [dict_from_row(r) for r in cursor.fetchall()]

        # Learning streak - consecutive days with new heuristics or learnings
        cursor.execute("""
            WITH RECURSIVE dates(date) AS (
                SELECT DATE('now')
                UNION ALL
                SELECT DATE(date, '-1 day')
                FROM dates
                WHERE date > DATE('now', ?)
            ),
            activity AS (
                SELECT DISTINCT DATE(created_at) as date
                FROM (
                    SELECT created_at FROM heuristics
                    UNION ALL
                    SELECT created_at FROM learnings
                )
            )
            SELECT COUNT(*) as streak
            FROM dates d
            INNER JOIN activity a ON d.date = a.date
            WHERE d.date <= DATE('now')
            ORDER BY d.date DESC
        """, (f'-{days} days',))
        streak_result = cursor.fetchone()
        current_streak = streak_result[0] if streak_result else 0

        # Success/failure trend - ratio over time
        cursor.execute("""
            SELECT DATE(created_at) as date,
                   COUNT(*) as total,
                   CAST(SUM(CASE WHEN type = 'success' THEN 1 ELSE 0 END) AS FLOAT) /
                   CAST(COUNT(*) AS FLOAT) as success_ratio
            FROM learnings
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            HAVING total > 0
            ORDER BY date
        """, (f'-{days} days',))
        success_trend = [dict_from_row(r) for r in cursor.fetchall()]

        # Calculate velocity trends (% change week over week)
        heuristics_trend = 0.0
        if len(heuristics_by_week) >= 2:
            recent_week = heuristics_by_week[-1]['heuristics_count']
            prev_week = heuristics_by_week[-2]['heuristics_count']
            if prev_week > 0:
                heuristics_trend = ((recent_week - prev_week) / prev_week) * 100

        # Total stats for the period
        total_heuristics_period = sum(d['count'] for d in heuristics_by_day)
        total_learnings_period = sum(d['total'] for d in learnings_by_day)
        total_promotions_period = sum(d['count'] for d in promotions_by_day)

        return {
            "heuristics_by_day": heuristics_by_day,
            "learnings_by_day": learnings_by_day,
            "promotions_by_day": promotions_by_day,
            "confidence_by_day": confidence_by_day,
            "heuristics_by_week": heuristics_by_week,
            "success_trend": success_trend,
            "current_streak": current_streak,
            "heuristics_trend": round(heuristics_trend, 1),
            "totals": {
                "heuristics": total_heuristics_period,
                "learnings": total_learnings_period,
                "promotions": total_promotions_period
            }
        }


@router.get("/events")
async def get_events(limit: int = 50):
    """Get recent events feed."""
    with get_db() as conn:
        cursor = conn.cursor()

        events = []

        # Recent metrics (last hour)
        cursor.execute("""
            SELECT metric_type, metric_name, metric_value, tags, context, timestamp
            FROM metrics
            WHERE timestamp > datetime('now', '-1 hour')
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        for row in cursor.fetchall():
            r = dict_from_row(row)
            event_type = r["metric_type"]

            # Format event message
            if event_type == "heuristic_validated":
                message = "Heuristic validated"
            elif event_type == "heuristic_violated":
                message = "Heuristic violated"
            elif event_type == "auto_failure_capture":
                message = "Failure auto-captured"
            elif event_type == "golden_rule_promotion":
                message = "New golden rule promoted!"
            elif event_type == "task_outcome":
                message = f"Task {r['metric_name']}"
            else:
                message = f"{event_type}: {r['metric_name']}"

            events.append({
                "type": event_type,
                "message": message,
                "timestamp": r["timestamp"],
                "tags": r["tags"],
                "context": r["context"]
            })

        return events


@router.get("/domains")
async def get_domains():
    """Get all domains with counts."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT domain, COUNT(*) as heuristic_count, AVG(confidence) as avg_confidence
            FROM heuristics
            GROUP BY domain
            ORDER BY heuristic_count DESC
        """)

        return [dict_from_row(r) for r in cursor.fetchall()]


@router.get("/anomalies")
async def get_anomalies():
    """Detect and return current anomalies."""
    anomalies = []

    with get_db() as conn:
        cursor = conn.cursor()

        # Repeated failures (same node failing multiple times)
        cursor.execute("""
            SELECT node_name, COUNT(*) as fail_count
            FROM node_executions
            WHERE status = 'failed'
              AND created_at > datetime('now', '-1 day')
            GROUP BY node_name
            HAVING fail_count >= 3
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "repeated_failure",
                "severity": "error",
                "message": f"Node '{row['node_name']}' failed {row['fail_count']} times in 24h",
                "data": {"node_name": row["node_name"], "count": row["fail_count"]}
            })

        # Sudden hot spots
        cursor.execute("""
            SELECT location, SUM(strength) as strength, COUNT(*) as count
            FROM trails
            WHERE created_at > datetime('now', '-1 day')
              AND location NOT IN (
                  SELECT DISTINCT location FROM trails
                  WHERE created_at <= datetime('now', '-1 day')
                    AND created_at > datetime('now', '-7 days')
              )
            GROUP BY location
            HAVING strength > 1.0
            ORDER BY strength DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "new_hotspot",
                "severity": "info",
                "message": f"New hot spot: {row['location']} ({row['count']} trails)",
                "data": {"location": row["location"], "strength": row["strength"]}
            })

        # Heuristics being violated frequently
        cursor.execute("""
            SELECT id, rule, times_violated, confidence
            FROM heuristics
            WHERE times_violated > 3 AND confidence > 0.5
            ORDER BY times_violated DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "heuristic_violations",
                "severity": "warning",
                "message": f"Heuristic violated {row['times_violated']}x: {row['rule'][:50]}...",
                "data": {"heuristic_id": row["id"], "violations": row["times_violated"]}
            })

        # Stale runs (running for too long)
        cursor.execute("""
            SELECT id, workflow_name, started_at
            FROM workflow_runs
            WHERE status = 'running'
              AND started_at < datetime('now', '-1 hour')
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "stale_run",
                "severity": "warning",
                "message": f"Run #{row['id']} ({row['workflow_name']}) has been running for >1 hour",
                "data": {"run_id": row["id"]}
            })

    return anomalies
