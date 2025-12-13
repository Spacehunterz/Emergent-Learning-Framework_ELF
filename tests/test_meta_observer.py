#!/usr/bin/env python3
"""
Tests for Meta-Observer - Phase 2C

Tests rolling window trend analysis, anomaly detection, and alert management.

Run with: python -m pytest tests/test_meta_observer.py -v
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
import unittest
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "query"))

from meta_observer import MetaObserver


class TestDatabase:
    """Test database manager with isolation."""

    def __init__(self):
        self.db_path = Path(__file__).parent / "test_meta_observer.db"
        self.setup()

    def setup(self):
        """Create test database with schema."""
        if self.db_path.exists():
            self.db_path.unlink()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create schema
        cursor.executescript("""
            CREATE TABLE metric_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                domain TEXT,
                metadata TEXT
            );

            CREATE UNIQUE INDEX idx_obs_unique
                ON metric_observations(metric_name, observed_at, IFNULL(domain, ''));

            CREATE INDEX idx_obs_metric_time
                ON metric_observations(metric_name, observed_at DESC);

            CREATE TABLE metric_hourly_rollups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                hour_start DATETIME NOT NULL,
                domain TEXT,
                min_value REAL,
                max_value REAL,
                avg_value REAL,
                sample_count INTEGER
            );

            CREATE UNIQUE INDEX idx_rollup_unique
                ON metric_hourly_rollups(metric_name, hour_start, IFNULL(domain, ''));

            CREATE TABLE meta_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'critical')),
                state TEXT NOT NULL DEFAULT 'new' CHECK(state IN ('new', 'active', 'ack', 'resolved')),
                metric_name TEXT,
                current_value REAL,
                baseline_value REAL,
                message TEXT NOT NULL,
                context TEXT,
                first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at DATETIME,
                resolved_at DATETIME,
                created_by TEXT DEFAULT 'meta_observer'
            );

            CREATE INDEX idx_alerts_state
                ON meta_alerts(state, severity, first_seen DESC);

            CREATE TABLE meta_observer_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT UNIQUE NOT NULL,
                threshold REAL,
                auto_adjust INTEGER DEFAULT 0,
                trend_window_hours INTEGER DEFAULT 168,
                trend_sensitivity REAL DEFAULT 0.05,
                baseline_window_hours INTEGER DEFAULT 720,
                z_score_threshold REAL DEFAULT 3.0,
                false_positive_count INTEGER DEFAULT 0,
                true_positive_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO meta_observer_config (metric_name, z_score_threshold)
            VALUES
                ('avg_confidence', 3.0),
                ('contradiction_rate', 3.0),
                ('validation_velocity', 2.5);
        """)

        conn.commit()
        conn.close()

    def teardown(self):
        """Remove test database."""
        if self.db_path.exists():
            self.db_path.unlink()

    def insert_observation(self, metric_name: str, value: float,
                          timestamp: datetime, domain: str = None) -> int:
        """Insert a test observation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use ISO format with microseconds to ensure uniqueness
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
        cursor.execute("""
            INSERT INTO metric_observations (metric_name, value, observed_at, domain)
            VALUES (?, ?, ?, ?)
        """, (metric_name, value, timestamp_str, domain))
        conn.commit()
        obs_id = cursor.lastrowid
        conn.close()
        return obs_id


class TestMetricRecording(unittest.TestCase):
    """Test basic metric recording and retrieval."""

    def setUp(self):
        self.db = TestDatabase()
        self.observer = MetaObserver(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_record_metric(self):
        """Should record metric observation."""
        obs_id = self.observer.record_metric('avg_confidence', 0.75)
        self.assertGreater(obs_id, 0)

        # Verify it was recorded
        observations = self.observer.get_rolling_window('avg_confidence', hours=1)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].value, 0.75)

    def test_record_metric_with_domain(self):
        """Should record domain-specific metric."""
        obs_id = self.observer.record_metric('avg_confidence', 0.65, domain='security')
        self.assertGreater(obs_id, 0)

        # Should be filtered by domain
        obs_all = self.observer.get_rolling_window('avg_confidence', hours=1)
        obs_domain = self.observer.get_rolling_window('avg_confidence', hours=1, domain='security')

        self.assertEqual(len(obs_all), 1)
        self.assertEqual(len(obs_domain), 1)
        self.assertEqual(obs_domain[0].domain, 'security')

    def test_record_metric_with_metadata(self):
        """Should store metadata as JSON."""
        metadata = {'source': 'test', 'sample_count': 10}
        obs_id = self.observer.record_metric('avg_confidence', 0.8, metadata=metadata)

        observations = self.observer.get_rolling_window('avg_confidence', hours=1)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].metadata, json.dumps(metadata))


class TestRollingWindow(unittest.TestCase):
    """Test rolling window queries."""

    def setUp(self):
        self.db = TestDatabase()
        self.observer = MetaObserver(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_rolling_window_filtering(self):
        """Should only return observations within time window."""
        now = datetime.now()

        # Insert observations at different times
        self.db.insert_observation('test_metric', 1.0, now - timedelta(hours=50))
        self.db.insert_observation('test_metric', 2.0, now - timedelta(hours=26))  # Just outside 24h
        self.db.insert_observation('test_metric', 3.0, now - timedelta(hours=12))
        self.db.insert_observation('test_metric', 4.0, now - timedelta(hours=1))

        # 24-hour window should get last 2 (12h and 1h ago)
        window_24h = self.observer.get_rolling_window('test_metric', hours=24)
        self.assertEqual(len(window_24h), 2)

        # 48-hour window should get last 3
        window_48h = self.observer.get_rolling_window('test_metric', hours=48)
        self.assertEqual(len(window_48h), 3)

    def test_rolling_window_ordering(self):
        """Should return observations in chronological order."""
        # Use observer.record_metric with longer sleeps to ensure distinct timestamps
        import time
        self.observer.record_metric('test_metric', 3.0)  # First
        time.sleep(0.1)  # 100ms should be enough
        self.observer.record_metric('test_metric', 1.0)  # Second
        time.sleep(0.1)
        self.observer.record_metric('test_metric', 2.0)  # Third

        window = self.observer.get_rolling_window('test_metric', hours=1)

        # Should be ordered chronologically (oldest to newest)
        self.assertEqual(len(window), 3)
        self.assertEqual(window[0].value, 3.0)  # First recorded
        self.assertEqual(window[1].value, 1.0)  # Second recorded
        self.assertEqual(window[2].value, 2.0)  # Third recorded


class TestTrendDetection(unittest.TestCase):
    """Test linear trend detection."""

    def setUp(self):
        self.db = TestDatabase()
        self.observer = MetaObserver(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_detect_gradual_decline(self):
        """Should detect declining trend."""
        now = datetime.now()
        base_confidence = 0.75

        # Create declining trend: -2% per day for 7 days
        for day in range(7):
            for hour in range(24):
                timestamp = now - timedelta(days=7-day, hours=23-hour)
                value = base_confidence - (day * 0.02)
                self.db.insert_observation('avg_confidence', value, timestamp)

        # Run trend detection
        trend = self.observer.calculate_trend('avg_confidence', hours=168)  # 7 days

        # Should detect declining trend
        self.assertEqual(trend['direction'], 'decreasing')
        self.assertLess(trend['slope'], 0)
        self.assertIn(trend['confidence'], ['high', 'medium'])

    def test_detect_increasing_trend(self):
        """Should detect increasing trend."""
        now = datetime.now()

        # Create increasing trend
        for i in range(50):
            timestamp = now - timedelta(hours=50-i)
            value = 0.5 + (i * 0.01)  # Steady increase
            self.db.insert_observation('test_metric', value, timestamp)

        trend = self.observer.calculate_trend('test_metric', hours=48)

        self.assertEqual(trend['direction'], 'increasing')
        self.assertGreater(trend['slope'], 0)

    def test_detect_stable_trend(self):
        """Should detect stable (flat) trend."""
        now = datetime.now()

        # Create stable trend with minor variance
        for i in range(50):
            timestamp = now - timedelta(hours=50-i)
            value = 0.7 + np.random.normal(0, 0.01)  # Stable around 0.7
            self.db.insert_observation('test_metric', value, timestamp)

        trend = self.observer.calculate_trend('test_metric', hours=48)

        # Should be stable (slope not statistically significant)
        self.assertEqual(trend['direction'], 'stable')

    def test_insufficient_data(self):
        """Should require minimum samples for trend detection."""
        now = datetime.now()

        # Only 5 observations (need 10)
        for i in range(5):
            timestamp = now - timedelta(hours=5-i)
            self.db.insert_observation('test_metric', 0.5, timestamp)

        trend = self.observer.calculate_trend('test_metric', hours=6)

        self.assertEqual(trend['confidence'], 'low')
        self.assertEqual(trend['reason'], 'insufficient_data')


class TestAnomalyDetection(unittest.TestCase):
    """Test z-score anomaly detection."""

    def setUp(self):
        self.db = TestDatabase()
        self.observer = MetaObserver(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_detect_sudden_spike(self):
        """Should detect sudden spike as anomaly."""
        now = datetime.now()
        baseline_rate = 0.05

        # Create 30 days of baseline data
        for day in range(30):
            for sample in range(24):
                timestamp = now - timedelta(days=30-day, hours=23-sample)
                # Normal variance around 5%
                value = baseline_rate + np.random.normal(0, 0.01)
                self.db.insert_observation('contradiction_rate', value, timestamp)

        # Spike in last 12 hours to 15%
        for i in range(12):
            timestamp = now - timedelta(hours=11-i)
            self.db.insert_observation('contradiction_rate', 0.15, timestamp)

        # Run anomaly detection
        anomaly = self.observer.detect_anomaly('contradiction_rate',
                                               baseline_hours=720,
                                               current_hours=12)

        # Should detect as anomaly
        self.assertTrue(anomaly['is_anomaly'])
        self.assertGreater(anomaly['z_score'], 3.0)
        self.assertIn(anomaly['severity'], ['warning', 'critical'])

    def test_normal_variance_not_anomaly(self):
        """Normal statistical variance should not trigger anomaly."""
        now = datetime.now()
        mean = 0.70
        std = 0.05

        # Create 30 days of normal data
        for day in range(30):
            for sample in range(24):
                timestamp = now - timedelta(days=30-day, hours=23-sample)
                value = np.random.normal(mean, std)
                self.db.insert_observation('avg_confidence', value, timestamp)

        # Current value within 2 std devs (normal)
        for i in range(12):
            timestamp = now - timedelta(hours=11-i)
            value = mean + 1.5 * std  # Within normal range
            self.db.insert_observation('avg_confidence', value, timestamp)

        anomaly = self.observer.detect_anomaly('avg_confidence')

        # Should NOT be anomaly (z-score < 3)
        self.assertFalse(anomaly.get('is_anomaly', False))
        if 'z_score' in anomaly:
            self.assertLess(anomaly['z_score'], 3.0)

    def test_insufficient_baseline(self):
        """Should require sufficient baseline data."""
        now = datetime.now()

        # Only 10 observations (need 30)
        for i in range(10):
            timestamp = now - timedelta(hours=20-i)
            self.db.insert_observation('test_metric', 0.5, timestamp)

        anomaly = self.observer.detect_anomaly('test_metric')

        self.assertFalse(anomaly['is_anomaly'])
        self.assertEqual(anomaly['reason'], 'insufficient_baseline')


class TestAlertManagement(unittest.TestCase):
    """Test alert creation and state management."""

    def setUp(self):
        self.db = TestDatabase()
        self.observer = MetaObserver(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_create_alert(self):
        """Should create new alert."""
        alert_id = self.observer.create_alert(
            alert_type='confidence_decline',
            severity='warning',
            message='Test alert',
            metric_name='avg_confidence'
        )

        self.assertGreater(alert_id, 0)

        # Verify it exists
        alerts = self.observer.get_active_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['alert_type'], 'confidence_decline')
        self.assertEqual(alerts[0]['state'], 'new')

    def test_alert_deduplication(self):
        """Should deduplicate same alert type/metric."""
        # Create first alert
        alert_id1 = self.observer.create_alert(
            alert_type='test_alert',
            severity='warning',
            message='First message',
            metric_name='test_metric'
        )

        # Create duplicate (same type + metric)
        alert_id2 = self.observer.create_alert(
            alert_type='test_alert',
            severity='warning',
            message='Updated message',
            metric_name='test_metric'
        )

        # Should be same alert (updated)
        self.assertEqual(alert_id1, alert_id2)

        # Should only have 1 active alert
        alerts = self.observer.get_active_alerts()
        self.assertEqual(len(alerts), 1)

    def test_acknowledge_alert(self):
        """Should transition alert to acknowledged state."""
        alert_id = self.observer.create_alert(
            alert_type='test_alert',
            severity='info',
            message='Test'
        )

        # Acknowledge
        success = self.observer.acknowledge_alert(alert_id)
        self.assertTrue(success)

        # Verify state changed
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT state FROM meta_alerts WHERE id = ?", (alert_id,))
        state = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(state, 'ack')

    def test_resolve_alert(self):
        """Should transition alert to resolved state."""
        alert_id = self.observer.create_alert(
            alert_type='test_alert',
            severity='info',
            message='Test'
        )

        # Resolve
        success = self.observer.resolve_alert(alert_id)
        self.assertTrue(success)

        # Should not appear in active alerts
        alerts = self.observer.get_active_alerts()
        self.assertEqual(len(alerts), 0)

    def test_alert_state_machine(self):
        """Test alert state transitions: new -> ack -> resolved."""
        alert_id = self.observer.create_alert(
            alert_type='test',
            severity='info',
            message='Test'
        )

        # Starts as 'new'
        alerts = self.observer.get_active_alerts()
        self.assertEqual(alerts[0]['state'], 'new')

        # Can acknowledge
        self.observer.acknowledge_alert(alert_id)
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("SELECT state FROM meta_alerts WHERE id = ?", (alert_id,))
        self.assertEqual(cursor.fetchone()[0], 'ack')

        # Can resolve from ack
        self.observer.resolve_alert(alert_id)
        cursor = conn.execute("SELECT state FROM meta_alerts WHERE id = ?", (alert_id,))
        self.assertEqual(cursor.fetchone()[0], 'resolved')
        conn.close()

    def test_filter_alerts_by_severity(self):
        """Should filter alerts by severity."""
        self.observer.create_alert('test1', 'info', 'Info alert')
        self.observer.create_alert('test2', 'warning', 'Warning alert')
        self.observer.create_alert('test3', 'critical', 'Critical alert')

        # Filter by critical
        critical = self.observer.get_active_alerts(severity='critical')
        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0]['severity'], 'critical')

        # All alerts
        all_alerts = self.observer.get_active_alerts()
        self.assertEqual(len(all_alerts), 3)


class TestAlertConditions(unittest.TestCase):
    """Test automatic alert triggering."""

    def setUp(self):
        self.db = TestDatabase()
        self.observer = MetaObserver(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_bootstrap_mode(self):
        """Should not fire alerts during bootstrap period (<7 days)."""
        now = datetime.now()

        # Only 3 days of data
        for day in range(3):
            for hour in range(24):
                timestamp = now - timedelta(days=3-day, hours=23-hour)
                self.db.insert_observation('avg_confidence', 0.5, timestamp)

        alerts = self.observer.check_alerts()

        # Should indicate bootstrap mode
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].get('mode'), 'bootstrap')

    def test_confidence_decline_alert(self):
        """Should trigger alert on sustained confidence decline."""
        now = datetime.now()

        # Create 8 days of steep declining confidence (-5% per day)
        # This ensures slope < -0.02 per day (or < -0.00083 per hour)
        for day in range(8):
            for hour in range(24):
                timestamp = now - timedelta(days=8-day, hours=23-hour)
                value = 0.75 - (day * 0.05)  # -5% per day
                self.db.insert_observation('avg_confidence', value, timestamp)

        alerts = self.observer.check_alerts()

        # Should trigger confidence decline alert
        decline_alerts = [a for a in alerts if a.get('type') == 'confidence_decline']
        self.assertGreater(len(decline_alerts), 0)

    def test_contradiction_spike_alert(self):
        """Should trigger alert on contradiction rate spike."""
        now = datetime.now()

        # 30 days baseline at 5%
        for day in range(30):
            for sample in range(24):
                timestamp = now - timedelta(days=31-day, hours=23-sample)
                value = 0.05 + np.random.normal(0, 0.005)
                self.db.insert_observation('contradiction_rate', value, timestamp)

        # Spike to 20% in last day
        for hour in range(24):
            timestamp = now - timedelta(hours=23-hour)
            self.db.insert_observation('contradiction_rate', 0.20, timestamp)

        alerts = self.observer.check_alerts()

        # Should trigger contradiction spike alert
        spike_alerts = [a for a in alerts if a.get('type') == 'contradiction_spike']
        self.assertGreater(len(spike_alerts), 0)


class TestFalsePositiveTracking(unittest.TestCase):
    """Test false positive rate tracking."""

    def setUp(self):
        self.db = TestDatabase()
        self.observer = MetaObserver(db_path=self.db.db_path)

    def tearDown(self):
        self.db.teardown()

    def test_record_true_positive(self):
        """Should track true positive outcomes."""
        alert_id = self.observer.create_alert(
            'test_alert', 'warning', 'Test',
            metric_name='avg_confidence'
        )

        # Record as true positive
        self.observer.record_alert_outcome(alert_id, is_true_positive=True)

        # Check stats
        stats = self.observer.get_fpr_stats()
        self.assertEqual(stats['avg_confidence']['true_positives'], 1)
        self.assertEqual(stats['avg_confidence']['false_positives'], 0)

    def test_record_false_positive(self):
        """Should track false positive outcomes."""
        alert_id = self.observer.create_alert(
            'test_alert', 'warning', 'Test',
            metric_name='avg_confidence'
        )

        # Record as false positive
        self.observer.record_alert_outcome(alert_id, is_true_positive=False)

        # Check stats
        stats = self.observer.get_fpr_stats()
        self.assertEqual(stats['avg_confidence']['false_positives'], 1)
        self.assertEqual(stats['avg_confidence']['true_positives'], 0)

    def test_calculate_fpr(self):
        """Should calculate false positive rate correctly."""
        # Create config entry for test metric
        conn = sqlite3.connect(self.db.db_path)
        conn.execute("""
            INSERT INTO meta_observer_config (metric_name, z_score_threshold)
            VALUES ('test_metric', 3.0)
        """)
        conn.commit()
        conn.close()

        # Create multiple alerts and record outcomes
        for i in range(10):
            alert_id = self.observer.create_alert(
                f'alert_{i}', 'warning', f'Test {i}',
                metric_name='test_metric'
            )
            # 7 true positives, 3 false positives
            is_tp = i < 7
            self.observer.record_alert_outcome(alert_id, is_true_positive=is_tp)

        stats = self.observer.get_fpr_stats()

        # FPR should be 3/10 = 0.3
        self.assertEqual(stats['test_metric']['total_alerts'], 10)
        self.assertEqual(stats['test_metric']['false_positives'], 3)
        self.assertEqual(stats['test_metric']['true_positives'], 7)
        self.assertAlmostEqual(stats['test_metric']['fpr'], 0.3, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
