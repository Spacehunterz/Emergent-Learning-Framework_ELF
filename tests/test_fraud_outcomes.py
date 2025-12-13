#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for TP/FP tracking system
Phase 3: Swarm Agent 1 deliverable test
"""

import sqlite3
import sys
import io
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add query directory to path
sys.path.insert(0, str(Path.home() / ".claude" / "emergent-learning" / "query"))

from fraud_outcomes import FraudOutcomeTracker, OutcomeType
from fraud_detector import FraudDetector


def setup_test_db():
    """Create a test database with sample data."""
    test_db = Path("/tmp/test_fraud_outcomes.db")
    if test_db.exists():
        test_db.unlink()

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Create minimal schema for testing
    cursor.executescript("""
        -- Heuristics table
        CREATE TABLE heuristics (
            id INTEGER PRIMARY KEY,
            domain TEXT,
            rule TEXT,
            confidence REAL,
            status TEXT DEFAULT 'active',
            is_golden INTEGER DEFAULT 0,
            times_validated INTEGER DEFAULT 0,
            times_violated INTEGER DEFAULT 0,
            times_contradicted INTEGER DEFAULT 0
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
            review_outcome TEXT CHECK(review_outcome IN
                ('false_positive', 'true_positive', 'pending', 'dismissed', NULL)),
            FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
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
            FOREIGN KEY (fraud_report_id) REFERENCES fraud_reports(id),
            FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
        );

        -- Fraud outcome history table (from migration 007)
        CREATE TABLE fraud_outcome_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fraud_report_id INTEGER NOT NULL,
            previous_outcome TEXT,
            new_outcome TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            change_reason TEXT,
            FOREIGN KEY (fraud_report_id) REFERENCES fraud_reports(id)
        );

        -- Trigger for outcome changes
        CREATE TRIGGER trg_fraud_outcome_change
        AFTER UPDATE OF review_outcome ON fraud_reports
        WHEN NEW.review_outcome IS NOT NULL AND
             (OLD.review_outcome IS NULL OR OLD.review_outcome != NEW.review_outcome)
        BEGIN
            INSERT INTO fraud_outcome_history
                (fraud_report_id, previous_outcome, new_outcome, changed_by, change_reason)
            VALUES
                (NEW.id, OLD.review_outcome, NEW.review_outcome,
                 COALESCE(NEW.reviewed_by, 'system'),
                 'Outcome changed from ' || COALESCE(OLD.review_outcome, 'null') || ' to ' || NEW.review_outcome);
        END;

        -- Views for analysis
        CREATE VIEW pending_review_queue AS
        SELECT
            fr.id as report_id,
            fr.heuristic_id,
            h.domain,
            h.rule,
            h.confidence as heuristic_confidence,
            fr.fraud_score,
            fr.classification,
            fr.signal_count,
            fr.created_at,
            (fr.fraud_score * 0.7 + (fr.signal_count / 10.0) * 0.3) as priority_score,
            GROUP_CONCAT(asig.detector_name, ', ') as detectors,
            GROUP_CONCAT(asig.severity, ', ') as severities
        FROM fraud_reports fr
        JOIN heuristics h ON fr.heuristic_id = h.id
        LEFT JOIN anomaly_signals asig ON fr.id = asig.fraud_report_id
        WHERE fr.review_outcome IS NULL OR fr.review_outcome = 'pending'
        GROUP BY fr.id
        ORDER BY priority_score DESC, fr.created_at DESC;

        CREATE VIEW classification_accuracy AS
        SELECT
            fr.classification,
            COUNT(*) as total,
            SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) as confirmed,
            SUM(CASE WHEN fr.review_outcome = 'false_positive' THEN 1 ELSE 0 END) as rejected,
            SUM(CASE WHEN fr.review_outcome IS NULL OR fr.review_outcome = 'pending' THEN 1 ELSE 0 END) as pending,
            CASE
                WHEN SUM(CASE WHEN fr.review_outcome IN ('true_positive', 'false_positive') THEN 1 ELSE 0 END) > 0
                THEN CAST(SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) AS REAL) /
                     SUM(CASE WHEN fr.review_outcome IN ('true_positive', 'false_positive') THEN 1 ELSE 0 END)
                ELSE NULL
            END as accuracy,
            AVG(fr.fraud_score) as avg_score,
            MIN(fr.fraud_score) as min_score,
            MAX(fr.fraud_score) as max_score
        FROM fraud_reports fr
        GROUP BY fr.classification;

        CREATE VIEW detector_confusion_matrix AS
        SELECT
            asig.detector_name,
            asig.severity,
            SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) as tp_count,
            SUM(CASE WHEN fr.review_outcome = 'false_positive' THEN 1 ELSE 0 END) as fp_count,
            SUM(CASE WHEN fr.review_outcome IS NULL OR fr.review_outcome = 'pending' THEN 1 ELSE 0 END) as pending_count,
            COUNT(*) as total_signals,
            AVG(asig.score) as avg_score,
            CASE
                WHEN COUNT(*) > 0
                THEN CAST(SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) AS REAL) / COUNT(*)
                ELSE NULL
            END as tp_rate
        FROM anomaly_signals asig
        JOIN fraud_reports fr ON asig.fraud_report_id = fr.id
        GROUP BY asig.detector_name, asig.severity;
    """)

    # Insert test heuristics
    cursor.executescript("""
        INSERT INTO heuristics (id, domain, rule, confidence) VALUES
            (1, 'git-workflow', 'Always commit before merge', 0.8),
            (2, 'testing', 'Run tests before push', 0.7),
            (3, 'code-review', 'Review PRs within 24h', 0.6);
    """)

    # Insert test fraud reports
    cursor.executescript("""
        INSERT INTO fraud_reports
            (heuristic_id, fraud_score, classification, likelihood_ratio, signal_count)
        VALUES
            (1, 0.85, 'fraud_likely', 8.5, 2),
            (1, 0.92, 'fraud_confirmed', 12.3, 3),
            (2, 0.45, 'suspicious', 3.2, 1),
            (3, 0.25, 'low_confidence', 2.1, 1);
    """)

    # Insert anomaly signals
    cursor.executescript("""
        INSERT INTO anomaly_signals
            (fraud_report_id, heuristic_id, detector_name, score, severity, reason)
        VALUES
            -- Report 1 (fraud_likely)
            (1, 1, 'success_rate_anomaly', 0.8, 'high', 'Success rate too high'),
            (1, 1, 'temporal_manipulation', 0.6, 'medium', 'Suspicious timing'),
            -- Report 2 (fraud_confirmed)
            (2, 1, 'success_rate_anomaly', 0.9, 'high', 'Success rate way too high'),
            (2, 1, 'temporal_manipulation', 0.7, 'high', 'Very suspicious timing'),
            (2, 1, 'unnatural_confidence_growth', 0.8, 'medium', 'Too smooth growth'),
            -- Report 3 (suspicious)
            (3, 2, 'temporal_manipulation', 0.5, 'medium', 'Some timing issues'),
            -- Report 4 (low_confidence)
            (4, 3, 'success_rate_anomaly', 0.3, 'low', 'Slightly elevated');
    """)

    conn.commit()
    conn.close()

    return test_db


def test_record_outcome(tracker, test_db):
    """Test recording outcomes."""
    print("\n=== Test: Record Outcome ===")

    # Record a true positive
    success = tracker.record_outcome(
        report_id=1,
        outcome='true_positive',
        decided_by='test_user',
        notes='Confirmed fraud after investigation'
    )
    assert success, "Failed to record outcome for report 1"
    print("✓ Recorded true_positive for report 1")

    # Record a false positive
    success = tracker.record_outcome(
        report_id=3,
        outcome='false_positive',
        decided_by='test_user',
        notes='Normal behavior for this domain'
    )
    assert success, "Failed to record outcome for report 3"
    print("✓ Recorded false_positive for report 3")

    # Try to record for non-existent report
    success = tracker.record_outcome(
        report_id=999,
        outcome='true_positive',
        decided_by='test_user'
    )
    assert not success, "Should fail for non-existent report"
    print("✓ Correctly rejected non-existent report")

    # Verify outcomes were recorded
    conn = sqlite3.connect(test_db)
    cursor = conn.execute("""
        SELECT id, review_outcome, reviewed_by
        FROM fraud_reports
        WHERE review_outcome IS NOT NULL
    """)
    results = cursor.fetchall()
    conn.close()

    assert len(results) == 2, f"Expected 2 outcomes, got {len(results)}"
    print(f"✓ Verified {len(results)} outcomes in database")


def test_detector_accuracy(tracker):
    """Test detector accuracy calculations."""
    print("\n=== Test: Detector Accuracy ===")

    # Record more outcomes for accuracy testing
    tracker.record_outcome(2, 'true_positive', 'test_user', 'Confirmed')
    tracker.record_outcome(4, 'false_positive', 'test_user', 'Normal')

    # Get accuracy for all detectors
    accuracies = tracker.get_detector_accuracy()
    print(f"✓ Retrieved accuracy for {len(accuracies)} detectors")

    for acc in accuracies:
        print(f"\n  Detector: {acc.detector_name}")
        print(f"    Total reports: {acc.total_reports}")
        print(f"    TP: {acc.true_positives}, FP: {acc.false_positives}")
        if acc.precision is not None:
            print(f"    Precision: {acc.precision:.1%}")
        else:
            print(f"    Precision: N/A (pending: {acc.pending})")

    # Check specific detector
    success_rate_acc = tracker.get_detector_accuracy(detector_name='success_rate_anomaly')
    assert len(success_rate_acc) == 1, "Should get exactly one detector"
    print(f"\n✓ Filtered to 'success_rate_anomaly': {success_rate_acc[0].total_reports} reports")


def test_domain_accuracy(tracker):
    """Test domain accuracy calculations."""
    print("\n=== Test: Domain Accuracy ===")

    accuracies = tracker.get_domain_accuracy()
    print(f"✓ Retrieved accuracy for {len(accuracies)} domains")

    for acc in accuracies:
        print(f"\n  Domain: {acc.domain}")
        print(f"    Total reports: {acc.total_reports}")
        print(f"    TP: {acc.true_positives}, FP: {acc.false_positives}")
        if acc.precision is not None:
            print(f"    Precision: {acc.precision:.1%}")
        else:
            print(f"    Precision: N/A")

    # Check specific domain
    git_acc = tracker.get_domain_accuracy(domain='git-workflow')
    assert len(git_acc) == 1, "Should get exactly one domain"
    print(f"\n✓ Filtered to 'git-workflow': {git_acc[0].total_reports} reports")


def test_pending_reports(tracker):
    """Test pending reports queue."""
    print("\n=== Test: Pending Reports ===")

    pending = tracker.get_pending_reports()
    print(f"✓ Retrieved {len(pending)} pending reports")

    for report in pending:
        print(f"\n  Report #{report['report_id']}: {report['classification']}")
        print(f"    Fraud score: {report['fraud_score']:.2f}")
        print(f"    Priority: {report['priority_score']:.2f}")
        print(f"    Detectors: {report['detectors']}")


def test_classification_accuracy(tracker):
    """Test classification accuracy view."""
    print("\n=== Test: Classification Accuracy ===")

    accuracies = tracker.get_classification_accuracy()
    print(f"✓ Retrieved accuracy for {len(accuracies)} classification levels")

    for acc in accuracies:
        print(f"\n  {acc['classification']}:")
        print(f"    Total: {acc['total']}")
        print(f"    Confirmed: {acc['confirmed']}, Rejected: {acc['rejected']}")
        if acc['accuracy'] is not None:
            print(f"    Accuracy: {acc['accuracy']:.1%}")
        print(f"    Score range: {acc['min_score']:.2f} - {acc['max_score']:.2f}")


def test_confusion_matrix(tracker):
    """Test detector confusion matrix."""
    print("\n=== Test: Confusion Matrix ===")

    matrix = tracker.get_detector_confusion_matrix()
    print(f"✓ Retrieved confusion matrix with {len(matrix)} entries")

    for entry in matrix:
        print(f"\n  {entry['detector_name']} ({entry['severity']}):")
        print(f"    TP: {entry['tp_count']}, FP: {entry['fp_count']}, Pending: {entry['pending_count']}")
        if entry['tp_rate'] is not None:
            print(f"    TP Rate: {entry['tp_rate']:.1%}")


def test_underperforming_detectors(tracker):
    """Test identification of underperforming detectors."""
    print("\n=== Test: Underperforming Detectors ===")

    # Need more data for this test
    # Record some more outcomes to create variance
    tracker.record_outcome(1, 'false_positive', 'test_user', 'Actually OK')

    underperforming = tracker.identify_underperforming_detectors(
        min_reports=1,  # Lower threshold for test
        max_precision=0.6
    )

    if underperforming:
        print(f"✓ Found {len(underperforming)} underperforming detectors:")
        for d in underperforming:
            print(f"\n  {d['detector_name']}: {d['precision']:.1%} precision")
            print(f"    TP: {d['true_positives']}, FP: {d['false_positives']}")
    else:
        print("✓ No underperforming detectors found (all performing well)")


def test_performance_report(tracker):
    """Test comprehensive performance report."""
    print("\n=== Test: Performance Report ===")

    report = tracker.generate_performance_report(days=30)

    print(f"\n  Time period: {report['time_period']}")
    print(f"  Total reports: {report['summary']['total_reports']}")
    print(f"  TP: {report['summary']['total_tp']}, FP: {report['summary']['total_fp']}")

    if report['summary']['overall_precision'] is not None:
        print(f"  Overall precision: {report['summary']['overall_precision']:.1%}")

    print(f"\n  Detectors analyzed: {len(report['detectors'])}")
    print(f"  Domains analyzed: {len(report['domains'])}")
    print(f"  Underperforming: {len(report['underperforming'])}")

    print("\n✓ Performance report generated successfully")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("TP/FP Tracking System Test Suite")
    print("=" * 60)

    # Setup
    test_db = setup_test_db()
    print(f"\n✓ Test database created: {test_db}")

    tracker = FraudOutcomeTracker(db_path=test_db)
    print("✓ FraudOutcomeTracker initialized")

    try:
        # Run all tests
        test_record_outcome(tracker, test_db)
        test_detector_accuracy(tracker)
        test_domain_accuracy(tracker)
        test_pending_reports(tracker)
        test_classification_accuracy(tracker)
        test_confusion_matrix(tracker)
        test_underperforming_detectors(tracker)
        test_performance_report(tracker)

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        test_db.unlink()
        print(f"\n✓ Test database cleaned up")

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
