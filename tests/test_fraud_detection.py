#!/usr/bin/env python3
"""
Test Suite for Fraud Detection System
Phase 2D Implementation

Tests:
1. Success rate anomaly detection
2. Temporal pattern detection (cooldown gaming, midnight clustering)
3. Confidence trajectory analysis
4. Combined scoring (Bayesian fusion)
5. False positive handling (golden rule whitelist)
6. Domain baseline calculation
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add src directory to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from query.fraud_detector import FraudDetector, FraudConfig, AnomalySignal
from query.lifecycle_manager import LifecycleManager, UpdateType


class TestFraudDetection:
    """Test fraud detection system."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp())
        db_path = temp_dir / "test_fraud.db"

        # Initialize schema
        conn = sqlite3.connect(db_path)

        # Use the actual database schema from the production database
        conn.executescript("""
            -- Core heuristics table with all current columns
            CREATE TABLE heuristics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                rule TEXT NOT NULL,
                explanation TEXT,
                source_type TEXT,
                confidence REAL DEFAULT 0.0,
                times_validated INTEGER DEFAULT 0,
                is_golden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_id INTEGER,
                times_violated INTEGER DEFAULT 0,
                updated_at DATETIME,
                status TEXT DEFAULT 'active',
                dormant_since DATETIME,
                revival_conditions TEXT,
                times_revived INTEGER DEFAULT 0,
                times_contradicted INTEGER DEFAULT 0,
                min_applications INTEGER DEFAULT 10,
                last_confidence_update DATETIME,
                update_count_today INTEGER DEFAULT 0,
                update_count_reset_date DATE,
                last_used_at DATETIME,
                confidence_ema REAL,
                ema_alpha REAL,
                ema_warmup_remaining INTEGER DEFAULT 0,
                last_ema_update DATETIME,
                fraud_flags INTEGER DEFAULT 0,
                is_quarantined INTEGER DEFAULT 0,
                last_fraud_check DATETIME,
                project_path TEXT DEFAULT NULL
            );

            -- Confidence updates table
            CREATE TABLE confidence_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                heuristic_id INTEGER NOT NULL,
                old_confidence REAL NOT NULL,
                new_confidence REAL NOT NULL,
                delta REAL NOT NULL,
                update_type TEXT NOT NULL,
                reason TEXT,
                session_id TEXT,
                agent_id TEXT,
                rate_limited INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                raw_target_confidence REAL,
                smoothed_delta REAL,
                alpha_used REAL,
                FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
            );

            -- Domain baselines table (current baseline)
            CREATE TABLE domain_baselines (
                domain TEXT PRIMARY KEY,
                avg_success_rate REAL,
                std_success_rate REAL,
                avg_update_frequency REAL,
                std_update_frequency REAL,
                sample_count INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- Domain baseline history table (historical baselines)
            CREATE TABLE domain_baseline_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                avg_success_rate REAL NOT NULL,
                std_success_rate REAL NOT NULL,
                avg_update_frequency REAL,
                std_update_frequency REAL,
                sample_count INTEGER NOT NULL,
                calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                prev_avg_success_rate REAL,
                prev_std_success_rate REAL,
                drift_percentage REAL,
                is_significant_drift BOOLEAN DEFAULT 0,
                triggered_by TEXT DEFAULT 'manual',
                notes TEXT
            );


            -- Fraud reports table
            CREATE TABLE fraud_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                heuristic_id INTEGER NOT NULL,
                fraud_score REAL NOT NULL,
                classification TEXT NOT NULL,
                likelihood_ratio REAL,
                signal_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME,
                reviewed_by TEXT,
                review_outcome TEXT,
                FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
            );

            -- Anomaly signals table
            CREATE TABLE anomaly_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fraud_report_id INTEGER NOT NULL,
                heuristic_id INTEGER NOT NULL,
                detector_name TEXT NOT NULL,
                score REAL NOT NULL,
                severity TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fraud_report_id) REFERENCES fraud_reports(id) ON DELETE CASCADE,
                FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
            );

            -- Fraud responses table
            CREATE TABLE fraud_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fraud_report_id INTEGER NOT NULL,
                response_type TEXT NOT NULL,
                parameters TEXT,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                executed_by TEXT DEFAULT 'system',
                rollback_at DATETIME,
                FOREIGN KEY (fraud_report_id) REFERENCES fraud_reports(id) ON DELETE CASCADE
            );

            -- Indexes
            CREATE INDEX idx_conf_updates_heuristic ON confidence_updates(heuristic_id);
            CREATE INDEX idx_conf_updates_created ON confidence_updates(created_at DESC);
            CREATE INDEX idx_fraud_reports_heuristic ON fraud_reports(heuristic_id);
            CREATE INDEX idx_anomaly_signals_heuristic ON anomaly_signals(heuristic_id);
            CREATE INDEX idx_domain_baselines_domain ON domain_baselines(domain);
        """)

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def detector(self, temp_db):
        """Create fraud detector instance."""
        return FraudDetector(db_path=temp_db)

    @pytest.fixture
    def lifecycle_manager(self, temp_db):
        """Create lifecycle manager instance."""
        return LifecycleManager(db_path=temp_db)

    def _create_heuristic(self, temp_db, domain="testing", rule="Test rule",
                          confidence=0.5, is_golden=False):
        """Helper to create a heuristic."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("""
            INSERT INTO heuristics
            (domain, rule, confidence, times_validated, times_violated,
             times_contradicted, status, is_golden, created_at, updated_at)
            VALUES (?, ?, ?, 0, 0, 0, 'active', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (domain, rule, confidence, 1 if is_golden else 0))
        heuristic_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return heuristic_id

    def _create_update(self, temp_db, heuristic_id, old_conf, new_conf,
                       update_type="success", created_at=None):
        """Helper to create a confidence update record."""
        conn = sqlite3.connect(temp_db)
        if created_at is None:
            created_at = datetime.now().isoformat()

        conn.execute("""
            INSERT INTO confidence_updates
            (heuristic_id, old_confidence, new_confidence, delta, update_type,
             reason, created_at)
            VALUES (?, ?, ?, ?, ?, 'test', ?)
        """, (heuristic_id, old_conf, new_conf, new_conf - old_conf,
              update_type, created_at))
        conn.commit()
        conn.close()

    # =========================================================================
    # TEST 1: Success Rate Anomaly Detection
    # =========================================================================

    def test_success_rate_anomaly_detection(self, temp_db, detector):
        """Test detection of abnormally high success rates."""
        # Create domain baseline
        # Create 5 normal heuristics with VARIED success rates (50-80%)
        success_counts = [5, 6, 7, 7, 8]  # 50%, 60%, 70%, 70%, 80%
        for i, successes in enumerate(success_counts):
            h_id = self._create_heuristic(temp_db, domain="testing")
            conn = sqlite3.connect(temp_db)
            failures = 10 - successes
            conn.execute("""
                UPDATE heuristics SET
                    times_validated = ?,
                    times_violated = ?
                WHERE id = ?
            """, (successes, failures, h_id))
            conn.commit()
            conn.close()

        # Update baseline
        detector.update_domain_baseline("testing")

        # Create suspicious heuristic with 100% success rate
        sus_id = self._create_heuristic(temp_db, domain="testing")
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            UPDATE heuristics SET
                times_validated = 15,
                times_violated = 0
            WHERE id = ?
        """, (sus_id,))
        conn.commit()
        conn.close()

        # Run detection
        signal = detector.detect_success_rate_anomaly(sus_id)

        # Assertions
        assert signal is not None, "Should detect success rate anomaly"
        assert signal.detector_name == "success_rate_anomaly"
        assert signal.score > 0.5, "Score should be significant"
        assert "above domain average" in signal.reason

    def test_success_rate_golden_rule_whitelist(self, temp_db, detector):
        """Test that golden rules are whitelisted from success rate detection."""
        # Create domain baseline
        for i in range(5):
            h_id = self._create_heuristic(temp_db, domain="testing")
            conn = sqlite3.connect(temp_db)
            conn.execute("""
                UPDATE heuristics SET times_validated = 7, times_violated = 3
                WHERE id = ?
            """, (h_id,))
            conn.commit()
            conn.close()

        detector.update_domain_baseline("testing")

        # Create golden rule with 100% success (legitimately good)
        golden_id = self._create_heuristic(temp_db, domain="testing", is_golden=True)
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            UPDATE heuristics SET times_validated = 20, times_violated = 0
            WHERE id = ?
        """, (golden_id,))
        conn.commit()
        conn.close()

        # Run detection
        signal = detector.detect_success_rate_anomaly(golden_id)

        # Should NOT flag golden rules
        assert signal is None, "Golden rules should be whitelisted"

    # =========================================================================
    # TEST 2: Temporal Pattern Detection
    # =========================================================================

    def test_temporal_cooldown_gaming(self, temp_db, detector):
        """Test detection of cooldown boundary gaming (updates at exactly 60-65 min)."""
        h_id = self._create_heuristic(temp_db)

        # Create updates clustered at cooldown boundary (61 minutes apart)
        base_time = datetime.now() - timedelta(days=1)
        for i in range(8):
            update_time = base_time + timedelta(minutes=61 * i)
            self._create_update(
                temp_db, h_id, 0.5 + i*0.01, 0.51 + i*0.01,
                created_at=update_time.isoformat()
            )

        # Run detection
        signal = detector.detect_temporal_manipulation(h_id)

        # Assertions
        assert signal is not None, "Should detect cooldown gaming"
        assert signal.detector_name == "temporal_manipulation"
        assert "cooldown boundary" in signal.reason
        assert signal.evidence['cooldown_cluster_rate'] > 0.5

    def test_temporal_midnight_gaming(self, temp_db, detector):
        """Test detection of midnight clustering (daily reset gaming)."""
        h_id = self._create_heuristic(temp_db)

        # Create updates clustered at midnight
        base_date = datetime.now().date()
        for i in range(10):
            # Updates at 23:30, 00:30 on different days
            hour = 23 if i % 2 == 0 else 0
            update_time = datetime.combine(base_date - timedelta(days=i//2), datetime.min.time()) + timedelta(hours=hour, minutes=30)
            self._create_update(
                temp_db, h_id, 0.5 + i*0.01, 0.51 + i*0.01,
                created_at=update_time.isoformat()
            )

        # Run detection
        signal = detector.detect_temporal_manipulation(h_id)

        # Assertions
        assert signal is not None, "Should detect midnight clustering"
        assert signal.evidence['midnight_rate'] > signal.evidence['expected_midnight_rate']

    def test_temporal_too_regular(self, temp_db, detector):
        """Test detection of too-regular update timing."""
        h_id = self._create_heuristic(temp_db)

        # Create updates at EXACTLY 62 minutes apart (cooldown gaming + too perfect)
        # This combines regularity + cooldown boundary clustering
        base_time = datetime.now() - timedelta(days=2)
        for i in range(10):
            update_time = base_time + timedelta(minutes=62 * i)
            self._create_update(
                temp_db, h_id, 0.5 + i*0.01, 0.51 + i*0.01,
                created_at=update_time.isoformat()
            )

        # Run detection
        signal = detector.detect_temporal_manipulation(h_id)

        # Assertions
        assert signal is not None, "Should detect too-regular timing"
        # Low coefficient of variation indicates regularity
        assert signal.evidence['coefficient_of_variation'] < 0.1
        # Should also flag cooldown clustering
        assert signal.evidence['cooldown_cluster_rate'] > 0.8

    # =========================================================================
    # TEST 3: Confidence Trajectory Analysis
    # =========================================================================

    def test_unnatural_confidence_growth(self, temp_db, detector):
        """Test detection of smooth, monotonic confidence growth."""
        h_id = self._create_heuristic(temp_db, confidence=0.3)

        # Create perfectly smooth monotonic growth (suspicious)
        base_time = datetime.now() - timedelta(days=30)
        for i in range(15):
            conf = 0.3 + (i * 0.03)  # Smooth linear growth
            update_time = base_time + timedelta(days=2 * i)
            self._create_update(
                temp_db, h_id, conf - 0.03, conf,
                created_at=update_time.isoformat()
            )

        # Run detection
        signal = detector.detect_unnatural_confidence_growth(h_id)

        # Assertions
        assert signal is not None, "Should detect unnatural growth"
        assert signal.detector_name == "unnatural_confidence_growth"
        assert signal.evidence['monotonic'] == True
        assert signal.evidence['smoothness_score'] > 0.5

    def test_natural_confidence_trajectory(self, temp_db, detector):
        """Test that natural (noisy) confidence growth is NOT flagged."""
        h_id = self._create_heuristic(temp_db, confidence=0.4)

        # Create natural noisy growth (some ups, some downs)
        base_time = datetime.now() - timedelta(days=30)
        deltas = [0.05, -0.02, 0.03, -0.01, 0.04, 0.06, -0.03, 0.02, -0.01, 0.05]
        conf = 0.4

        for i, delta in enumerate(deltas):
            old_conf = conf
            conf = max(0.05, min(0.95, conf + delta))
            update_time = base_time + timedelta(days=3 * i)
            self._create_update(
                temp_db, h_id, old_conf, conf,
                created_at=update_time.isoformat()
            )

        # Run detection
        signal = detector.detect_unnatural_confidence_growth(h_id)

        # Should NOT flag natural growth
        assert signal is None or signal.score < 0.3, "Natural growth should not be flagged"

    # =========================================================================
    # TEST 4: Bayesian Fusion
    # =========================================================================

    def test_bayesian_fusion_multiple_signals(self, detector):
        """Test that multiple weak signals combine into strong detection."""
        # Create multiple moderate signals
        signals = [
            AnomalySignal(
                detector_name="detector1",
                score=0.6,
                severity="medium",
                reason="Test signal 1",
                evidence={}
            ),
            AnomalySignal(
                detector_name="detector2",
                score=0.5,
                severity="medium",
                reason="Test signal 2",
                evidence={}
            ),
            AnomalySignal(
                detector_name="detector3",
                score=0.7,
                severity="high",
                reason="Test signal 3",
                evidence={}
            )
        ]

        # Calculate combined score
        fraud_score, lr = detector.calculate_combined_score(signals)

        # Multiple moderate signals should produce high combined score
        assert fraud_score > 0.5, "Multiple signals should combine strongly"
        assert lr > 1.0, "Likelihood ratio should favor fraud hypothesis"

    def test_bayesian_fusion_single_weak_signal(self, detector):
        """Test that single weak signal produces low fraud score."""
        signals = [
            AnomalySignal(
                detector_name="detector1",
                score=0.3,
                severity="low",
                reason="Weak signal",
                evidence={}
            )
        ]

        fraud_score, lr = detector.calculate_combined_score(signals)

        # Single weak signal should NOT produce high score
        assert fraud_score < 0.3, "Single weak signal should not trigger high fraud score"

    def test_fraud_classification_thresholds(self, detector):
        """Test fraud score classification into categories."""
        assert detector.classify_fraud_score(0.0) == "clean"
        assert detector.classify_fraud_score(0.15) == "low_confidence"
        assert detector.classify_fraud_score(0.3) == "suspicious"
        assert detector.classify_fraud_score(0.6) == "fraud_likely"
        assert detector.classify_fraud_score(0.85) == "fraud_confirmed"

    # =========================================================================
    # TEST 5: Domain Baseline Calculation
    # =========================================================================

    def test_domain_baseline_calculation(self, temp_db, detector):
        """Test baseline calculation from domain heuristics."""
        # Create 5 heuristics with varying success rates
        success_rates = [0.5, 0.6, 0.7, 0.75, 0.8]

        for i, rate in enumerate(success_rates):
            h_id = self._create_heuristic(temp_db, domain="baseline_test")
            successes = int(rate * 10)
            failures = 10 - successes

            conn = sqlite3.connect(temp_db)
            conn.execute("""
                UPDATE heuristics SET
                    times_validated = ?,
                    times_violated = ?
                WHERE id = ?
            """, (successes, failures, h_id))
            conn.commit()
            conn.close()

        # Calculate baseline
        result = detector.update_domain_baseline("baseline_test")

        # Assertions
        assert result['sample_count'] == 5
        assert 0.6 < result['avg_success_rate'] < 0.75  # Mean of rates
        assert result['std_success_rate'] > 0  # Should have variance

    def test_domain_baseline_insufficient_data(self, temp_db, detector):
        """Test that baseline calculation fails gracefully with insufficient data."""
        # Create only 2 heuristics (need 3+)
        for i in range(2):
            h_id = self._create_heuristic(temp_db, domain="sparse")
            conn = sqlite3.connect(temp_db)
            conn.execute("""
                UPDATE heuristics SET times_validated = 5, times_violated = 5
                WHERE id = ?
            """, (h_id,))
            conn.commit()
            conn.close()

        # Attempt baseline calculation
        result = detector.update_domain_baseline("sparse")

        # Should report insufficient data
        assert 'error' in result
        assert 'Insufficient sample size' in result['error']

    # =========================================================================
    # TEST 6: Integration Test - Full Detection Flow
    # =========================================================================

    def test_full_fraud_report_creation(self, temp_db, detector):
        """Test complete fraud detection report creation and storage."""
        # Setup: Create suspicious heuristic with multiple red flags

        # 1. Create domain baseline with varied success rates
        success_counts = [5, 6, 6, 7, 8]  # 50%, 60%, 60%, 70%, 80%
        for i, successes in enumerate(success_counts):
            h_id = self._create_heuristic(temp_db, domain="integration_test")
            conn = sqlite3.connect(temp_db)
            failures = 10 - successes
            conn.execute("""
                UPDATE heuristics SET times_validated = ?, times_violated = ?
                WHERE id = ?
            """, (successes, failures, h_id))
            conn.commit()
            conn.close()

        detector.update_domain_baseline("integration_test")

        # 2. Create suspicious heuristic
        sus_id = self._create_heuristic(temp_db, domain="integration_test")

        # High success rate
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            UPDATE heuristics SET times_validated = 15, times_violated = 0
            WHERE id = ?
        """, (sus_id,))
        conn.commit()
        conn.close()

        # Suspicious temporal pattern (cooldown gaming)
        base_time = datetime.now() - timedelta(days=1)
        for i in range(8):
            update_time = base_time + timedelta(minutes=61 * i)
            self._create_update(
                temp_db, sus_id, 0.5 + i*0.02, 0.52 + i*0.02,
                created_at=update_time.isoformat()
            )

        # 3. Run fraud detection
        report = detector.create_fraud_report(sus_id)

        # Assertions
        assert report.heuristic_id == sus_id
        assert len(report.signals) >= 2, "Should detect multiple anomalies"
        assert report.fraud_score > 0.5, "Should have significant fraud score"
        assert report.classification in ['suspicious', 'fraud_likely', 'fraud_confirmed']

        # Verify stored in database
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("""
            SELECT * FROM fraud_reports WHERE heuristic_id = ?
        """, (sus_id,))
        stored_report = cursor.fetchone()
        assert stored_report is not None, "Report should be stored in database"

        cursor = conn.execute("""
            SELECT COUNT(*) FROM anomaly_signals WHERE heuristic_id = ?
        """, (sus_id,))
        signal_count = cursor.fetchone()[0]
        assert signal_count == len(report.signals), "All signals should be stored"
        conn.close()

    def test_alert_response_action(self, temp_db, detector):
        """Test that fraud_likely triggers alert response."""
        # Create heuristic with high fraud score
        h_id = self._create_heuristic(temp_db, domain="alert_test")

        # Setup conditions for fraud_likely
        for i in range(5):
            baseline_id = self._create_heuristic(temp_db, domain="alert_test")
            conn = sqlite3.connect(temp_db)
            conn.execute("""
                UPDATE heuristics SET times_validated = 6, times_violated = 4
                WHERE id = ?
            """, (baseline_id,))
            conn.commit()
            conn.close()

        detector.update_domain_baseline("alert_test")

        # Make target heuristic suspicious
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            UPDATE heuristics SET times_validated = 20, times_violated = 0
            WHERE id = ?
        """, (h_id,))
        conn.commit()
        conn.close()

        # Run detection
        report = detector.create_fraud_report(h_id)

        # Verify alert was created
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("""
            SELECT * FROM fraud_responses
            WHERE fraud_report_id = (SELECT id FROM fraud_reports WHERE heuristic_id = ? ORDER BY created_at DESC LIMIT 1)
              AND response_type = 'alert'
        """, (h_id,))
        alert = cursor.fetchone()

        if report.classification in ['fraud_likely', 'fraud_confirmed']:
            assert alert is not None, "Alert should be created for fraud_likely/confirmed"
        conn.close()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
