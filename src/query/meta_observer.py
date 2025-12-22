#!/usr/bin/env python3
"""
Meta-Observer for Heuristic Lifecycle - Phase 2C

Implements rolling window trend analysis with anomaly detection.
Based on: reports/phase2/meta-observer-trends-design.md

CEO Decisions (LOCKED):
- Statistical library: numpy/scipy
- Drift adjustment: Alert only (no auto-adjust)
- False positive tolerance: 5% FPR target
- Rolling windows: 1h, 24h, 7d, 30d
"""

import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
from scipy import stats

# Configuration
DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

@dataclass
class MetricObservation:
    """Single metric observation."""
    id: int
    metric_name: str
    value: float
    observed_at: datetime
    domain: Optional[str]
    metadata: Optional[str]


class MetaObserver:
    """
    Meta-Observer for trend analysis and anomaly detection.

    Monitors heuristic lifecycle metrics over rolling time windows
    to detect gradual degradation, sudden spikes, and system health issues.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        """Ensure Phase 2C schema is applied."""
        conn = self._get_connection()
        try:
            # Check if migration is needed
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='metric_observations'"
            )
            if cursor.fetchone() is None:
                # Run migration
                migration_path = self.db_path.parent / "migrations" / "005_meta_observer_trends.sql"
                if migration_path.exists():
                    with open(migration_path) as f:
                        conn.executescript(f.read())
                    conn.commit()
        finally:
            conn.close()

    # =========================================================================
    # 1. METRIC RECORDING
    # =========================================================================

    def record_metric(self, metric_name: str, value: float,
                     domain: Optional[str] = None,
                     metadata: Optional[Dict] = None) -> int:
        """
        Record a metric observation.

        Args:
            metric_name: Name of the metric (e.g., 'avg_confidence')
            value: Numeric value
            domain: Optional domain for domain-specific metrics
            metadata: Optional additional context as dict

        Returns:
            Observation ID
        """
        conn = self._get_connection()
        try:
            metadata_json = json.dumps(metadata) if metadata else None

            cursor = conn.execute("""
                INSERT INTO metric_observations (metric_name, value, domain, metadata)
                VALUES (?, ?, ?, ?)
            """, (metric_name, value, domain, metadata_json))

            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_rolling_window(self, metric_name: str, hours: int,
                          domain: Optional[str] = None) -> List[MetricObservation]:
        """
        Get observations within a rolling time window.

        Args:
            metric_name: Metric to query
            hours: Window size in hours
            domain: Optional domain filter

        Returns:
            List of observations, oldest to newest
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT id, metric_name, value, observed_at, domain, metadata
                FROM metric_observations
                WHERE metric_name = ?
                  AND observed_at >= datetime('now', ? || ' hours')
            """
            params = [metric_name, -hours]

            if domain is not None:
                query += " AND domain = ?"
                params.append(domain)

            query += " ORDER BY observed_at ASC"

            cursor = conn.execute(query, params)

            observations = []
            for row in cursor.fetchall():
                obs = MetricObservation(
                    id=row['id'],
                    metric_name=row['metric_name'],
                    value=row['value'],
                    observed_at=datetime.fromisoformat(row['observed_at']),
                    domain=row['domain'],
                    metadata=row['metadata']
                )
                observations.append(obs)

            return observations
        finally:
            conn.close()

    # =========================================================================
    # 2. TREND DETECTION
    # =========================================================================

    def calculate_trend(self, metric_name: str, hours: int,
                       domain: Optional[str] = None,
                       min_time_spread_hours: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate linear trend over window using least-squares regression.

        Args:
            metric_name: Metric to analyze
            hours: Window size in hours
            domain: Optional domain filter
            min_time_spread_hours: Minimum time spread required for valid trend.
                                   Defaults to 10% of window size (e.g., 16.8h for 168h window)

        Returns:
            {
                'slope': float,  # Change per hour
                'direction': 'increasing' | 'stable' | 'decreasing',
                'r_squared': float,  # Goodness of fit
                'p_value': float,
                'confidence': 'high' | 'medium' | 'low',
                'sample_count': int,
                'time_spread_hours': float
            }
        """
        observations = self.get_rolling_window(metric_name, hours, domain)

        if len(observations) < 10:
            return {
                'confidence': 'low',
                'reason': 'insufficient_data',
                'sample_count': len(observations),
                'required': 10
            }

        # Check time spread - prevents false trends from short bursts of activity
        # A "7-day trend" with all samples in 1 hour isn't meaningful
        time_spread = (observations[-1].observed_at - observations[0].observed_at).total_seconds() / 3600
        min_spread = min_time_spread_hours if min_time_spread_hours is not None else (hours * 0.1)  # 10% of window
        min_spread = max(min_spread, 1.0)  # At least 1 hour

        if time_spread < min_spread:
            return {
                'confidence': 'low',
                'reason': 'insufficient_time_spread',
                'sample_count': len(observations),
                'time_spread_hours': round(time_spread, 2),
                'required_spread_hours': round(min_spread, 2)
            }

        # Convert to numpy arrays
        x = np.arange(len(observations))  # Time index
        y = np.array([o.value for o in observations])

        # Linear regression: y = mx + b
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Determine direction (with significance threshold)
        if abs(slope) < std_err * 2:  # Not statistically significant
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'

        # Confidence based on p-value
        if p_value < 0.05:
            confidence = 'high'
        elif p_value < 0.1:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'slope': slope,
            'direction': direction,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'std_err': std_err,
            'confidence': confidence,
            'sample_count': len(observations),
            'time_spread_hours': round(time_spread, 2)
        }

    # =========================================================================
    # 3. ANOMALY DETECTION
    # =========================================================================

    def detect_anomaly(self, metric_name: str,
                      baseline_hours: int = 720,  # 30 days
                      current_hours: int = 1,      # Last hour
                      domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect if current window is anomalous vs. baseline using z-score.

        Uses robust statistics (median, MAD) to avoid outlier contamination.

        Returns:
            {
                'current_value': float,
                'baseline_median': float,
                'baseline_std': float,
                'z_score': float,
                'is_anomaly': bool,
                'severity': 'normal' | 'warning' | 'critical'
            }
        """
        # Get baseline (historical normal, excluding recent window)
        cutoff = datetime.now() - timedelta(hours=current_hours)

        conn = self._get_connection()
        try:
            query = """
                SELECT value FROM metric_observations
                WHERE metric_name = ?
                  AND observed_at >= datetime('now', ? || ' hours')
                  AND observed_at <= ?
            """
            params = [metric_name, -baseline_hours, cutoff.isoformat()]

            if domain is not None:
                query += " AND domain = ?"
                params.append(domain)

            cursor = conn.execute(query, params)
            baseline_values = [row['value'] for row in cursor.fetchall()]
        finally:
            conn.close()

        if len(baseline_values) < 30:  # Need sufficient baseline
            return {
                'is_anomaly': False,
                'reason': 'insufficient_baseline',
                'baseline_samples': len(baseline_values),
                'required': 30
            }

        # Robust statistics
        baseline_median = np.median(baseline_values)
        # MAD = Median Absolute Deviation
        mad = np.median([abs(v - baseline_median) for v in baseline_values])
        # Convert MAD to std-equivalent (for normal distribution)
        baseline_std = mad * 1.4826 if mad > 0 else np.std(baseline_values)

        # Get current window average
        current_obs = self.get_rolling_window(metric_name, current_hours, domain)
        if not current_obs:
            return {
                'is_anomaly': False,
                'reason': 'no_current_data'
            }

        current_value = np.mean([o.value for o in current_obs])

        # Calculate z-score
        if baseline_std > 0:
            z_score = (current_value - baseline_median) / baseline_std
        else:
            z_score = 0.0

        # Get threshold from config
        config = self._get_config(metric_name)
        threshold = config.get('z_score_threshold', 3.0)

        is_anomaly = abs(z_score) > threshold

        # Severity based on z-score magnitude
        if abs(z_score) > 4.0:
            severity = 'critical'
        elif abs(z_score) > threshold:
            severity = 'warning'
        else:
            severity = 'normal'

        return {
            'current_value': current_value,
            'baseline_median': baseline_median,
            'baseline_std': baseline_std,
            'z_score': z_score,
            'is_anomaly': is_anomaly,
            'severity': severity,
            'threshold': threshold,
            'baseline_samples': len(baseline_values),
            'current_samples': len(current_obs)
        }

    # =========================================================================
    # 4. ALERT MANAGEMENT
    # =========================================================================

    def create_alert(self, alert_type: str, severity: str, message: str,
                    metric_name: Optional[str] = None,
                    current_value: Optional[float] = None,
                    baseline_value: Optional[float] = None,
                    context: Optional[Dict] = None) -> int:
        """
        Create or update alert with deduplication.

        Same (alert_type, metric_name) = same alert (update last_seen).

        Returns:
            Alert ID
        """
        conn = self._get_connection()
        try:
            # Convert numpy types to native Python types for JSON serialization
            if context:
                context = self._serialize_context(context)
            context_json = json.dumps(context) if context else None

            # Check for existing alert
            cursor = conn.execute("""
                SELECT id, state FROM meta_alerts
                WHERE alert_type = ?
                  AND COALESCE(metric_name, '') = COALESCE(?, '')
                  AND state IN ('new', 'active')
                ORDER BY first_seen DESC
                LIMIT 1
            """, (alert_type, metric_name or ''))

            existing = cursor.fetchone()

            if existing:
                # Update existing alert
                conn.execute("""
                    UPDATE meta_alerts SET
                        last_seen = CURRENT_TIMESTAMP,
                        current_value = COALESCE(?, current_value),
                        baseline_value = COALESCE(?, baseline_value),
                        message = ?,
                        context = COALESCE(?, context)
                    WHERE id = ?
                """, (current_value, baseline_value, message, context_json, existing['id']))
                conn.commit()
                return existing['id']
            else:
                # Create new alert
                cursor = conn.execute("""
                    INSERT INTO meta_alerts
                    (alert_type, severity, metric_name, current_value, baseline_value,
                     message, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (alert_type, severity, metric_name, current_value, baseline_value,
                      message, context_json))
                conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    def get_active_alerts(self, severity: Optional[str] = None) -> List[Dict]:
        """Get all active/new alerts."""
        conn = self._get_connection()
        try:
            query = """
                SELECT * FROM meta_alerts
                WHERE state IN ('new', 'active')
            """
            params = []

            if severity:
                query += " AND severity = ?"
                params.append(severity)

            query += " ORDER BY severity DESC, first_seen DESC"

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark alert as acknowledged."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                UPDATE meta_alerts SET
                    state = 'ack',
                    acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = ? AND state IN ('new', 'active')
            """, (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def resolve_alert(self, alert_id: int) -> bool:
        """Mark alert as resolved."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                UPDATE meta_alerts SET
                    state = 'resolved',
                    resolved_at = CURRENT_TIMESTAMP
                WHERE id = ? AND state IN ('new', 'active', 'ack')
            """, (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # =========================================================================
    # 5. ALERT CONDITIONS
    # =========================================================================

    def check_alerts(self) -> List[Dict]:
        """
        Check all alert conditions and create alerts as needed.

        Returns list of triggered alerts.
        """
        alerts = []

        # Check if in bootstrap mode (need 30 samples minimum)
        # Sample-based, not calendar-based - adapts to actual usage patterns
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT COUNT(*) as count
                FROM metric_observations
            """)
            row = cursor.fetchone()
            sample_count = row['count'] or 0

            if sample_count == 0:
                return []  # No data yet

            # Bootstrap threshold: 30 samples (~8 queries, since each records 4 metrics)
            BOOTSTRAP_THRESHOLD = 30

            if sample_count < BOOTSTRAP_THRESHOLD:
                # Bootstrap mode - don't fire alerts yet
                return [{
                    'mode': 'bootstrap',
                    'samples': sample_count,
                    'samples_needed': BOOTSTRAP_THRESHOLD,
                    'message': f'Collecting baseline data ({sample_count}/{BOOTSTRAP_THRESHOLD} samples)'
                }]
        finally:
            conn.close()

        # Alert 1: Sustained confidence decline
        trend = self.calculate_trend('avg_confidence', hours=168)  # 7 days
        # Slope is per observation index, need to convert to meaningful rate
        # With ~hourly samples over 168 hours, slope represents per-observation change
        if (trend.get('confidence') in ['high', 'medium'] and
            trend.get('direction') == 'decreasing' and
            trend.get('slope', 0) < -0.0002):  # Approx -2% over 7 days for 168 samples

            alert_id = self.create_alert(
                alert_type='confidence_decline',
                severity='warning',
                message=f"System confidence declining over 7 days (slope: {trend['slope']:.6f})",
                metric_name='avg_confidence',
                context={'trend': trend}
            )
            alerts.append({'alert_id': alert_id, 'type': 'confidence_decline'})

        # Alert 2: Contradiction rate spike
        anomaly = self.detect_anomaly('contradiction_rate', baseline_hours=720, current_hours=24)
        if anomaly.get('is_anomaly') and anomaly.get('severity') in ['warning', 'critical']:
            alert_id = self.create_alert(
                alert_type='contradiction_spike',
                severity=anomaly['severity'],
                message=f"Contradiction rate spiked to {anomaly['current_value']:.1%} "
                       f"(baseline: {anomaly['baseline_median']:.1%}, z-score: {anomaly['z_score']:.2f})",
                metric_name='contradiction_rate',
                current_value=anomaly['current_value'],
                baseline_value=anomaly['baseline_median'],
                context={'anomaly': anomaly}
            )
            alerts.append({'alert_id': alert_id, 'type': 'contradiction_spike'})

        # Alert 3: Validation velocity drop
        anomaly = self.detect_anomaly('validation_velocity', baseline_hours=720, current_hours=168)
        if anomaly.get('is_anomaly') and anomaly.get('z_score', 0) < -2.5:
            alert_id = self.create_alert(
                alert_type='activity_decline',
                severity='info',
                message=f"Validation activity dropped to {anomaly['current_value']:.1f} "
                       f"(baseline: {anomaly['baseline_median']:.1f})",
                metric_name='validation_velocity',
                current_value=anomaly['current_value'],
                baseline_value=anomaly['baseline_median'],
                context={'anomaly': anomaly}
            )
            alerts.append({'alert_id': alert_id, 'type': 'activity_decline'})

        return alerts

    # =========================================================================
    # 6. CONFIGURATION
    # =========================================================================

    def _serialize_context(self, obj):
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._serialize_context(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_context(item) for item in obj]
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    def _get_config(self, metric_name: str) -> Dict:
        """Get configuration for a metric."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM meta_observer_config WHERE metric_name = ?
            """, (metric_name,))
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def record_alert_outcome(self, alert_id: int, is_true_positive: bool) -> None:
        """
        Record whether alert was true or false positive.

        CEO target: 5% false positive rate.
        Note: auto_adjust is LOCKED to 0, so this only tracks metrics.
        """
        conn = self._get_connection()
        try:
            # Get metric name from alert
            cursor = conn.execute("""
                SELECT metric_name FROM meta_alerts WHERE id = ?
            """, (alert_id,))
            row = cursor.fetchone()
            if not row or not row['metric_name']:
                return

            metric_name = row['metric_name']

            # Update config stats
            if is_true_positive:
                conn.execute("""
                    UPDATE meta_observer_config
                    SET true_positive_count = true_positive_count + 1
                    WHERE metric_name = ?
                """, (metric_name,))
            else:
                conn.execute("""
                    UPDATE meta_observer_config
                    SET false_positive_count = false_positive_count + 1
                    WHERE metric_name = ?
                """, (metric_name,))

            conn.commit()
        finally:
            conn.close()

    def get_fpr_stats(self) -> Dict[str, Dict]:
        """Get false positive rate statistics per metric."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    metric_name,
                    false_positive_count,
                    true_positive_count,
                    CASE
                        WHEN (false_positive_count + true_positive_count) > 0
                        THEN CAST(false_positive_count AS REAL) / (false_positive_count + true_positive_count)
                        ELSE 0.0
                    END as fpr
                FROM meta_observer_config
                WHERE (false_positive_count + true_positive_count) > 0
            """)

            stats = {}
            for row in cursor.fetchall():
                stats[row['metric_name']] = {
                    'false_positives': row['false_positive_count'],
                    'true_positives': row['true_positive_count'],
                    'fpr': row['fpr'],
                    'total_alerts': row['false_positive_count'] + row['true_positive_count']
                }
            return stats
        finally:
            conn.close()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Meta-Observer for Heuristic Lifecycle")
    parser.add_argument("command", choices=["record", "trend", "anomaly", "check-alerts", "fpr-stats"])
    parser.add_argument("--metric", help="Metric name")
    parser.add_argument("--value", type=float, help="Metric value")
    parser.add_argument("--hours", type=int, default=168, help="Window size in hours")
    parser.add_argument("--domain", help="Domain filter")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    observer = MetaObserver()

    if args.command == "record":
        if not args.metric or args.value is None:
            print("Error: --metric and --value required for record")
            exit(1)
        obs_id = observer.record_metric(args.metric, args.value, args.domain)
        result = {"observation_id": obs_id, "metric": args.metric, "value": args.value}

    elif args.command == "trend":
        if not args.metric:
            print("Error: --metric required for trend")
            exit(1)
        result = observer.calculate_trend(args.metric, args.hours, args.domain)

    elif args.command == "anomaly":
        if not args.metric:
            print("Error: --metric required for anomaly")
            exit(1)
        result = observer.detect_anomaly(args.metric, domain=args.domain)

    elif args.command == "check-alerts":
        result = observer.check_alerts()

    elif args.command == "fpr-stats":
        result = observer.get_fpr_stats()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(json.dumps(result, indent=2, default=str))
