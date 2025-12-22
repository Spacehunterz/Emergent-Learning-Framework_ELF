#!/usr/bin/env python3
"""
Fraud Outcome Tracking and Detector Performance Analysis
Phase 3: TP/FP Tracking System

Provides functions for:
1. Recording human decisions on fraud reports
2. Calculating detector accuracy metrics
3. Identifying underperforming detectors
4. Generating performance reports
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Literal
from dataclasses import dataclass

# Configuration
DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

OutcomeType = Literal['true_positive', 'false_positive', 'dismissed', 'pending']
TimePeriod = Literal['all_time', 'last_30d', 'last_7d', 'last_24h']

@dataclass
class FraudOutcome:
    """Represents a human decision on a fraud report."""
    report_id: int
    outcome: OutcomeType
    decided_by: str
    decided_at: datetime
    notes: Optional[str] = None
    confidence: Optional[float] = None  # Reviewer confidence (0.0-1.0)

@dataclass
class DetectorAccuracy:
    """Accuracy metrics for a fraud detector."""
    detector_name: str
    time_period: TimePeriod
    total_reports: int
    true_positives: int
    false_positives: int
    pending: int
    precision: Optional[float]  # TP / (TP + FP)
    avg_anomaly_score: float
    first_detection: Optional[datetime]
    last_detection: Optional[datetime]

@dataclass
class DomainAccuracy:
    """Fraud detection accuracy for a domain."""
    domain: str
    total_reports: int
    true_positives: int
    false_positives: int
    pending: int
    precision: Optional[float]
    avg_fraud_score: float


class FraudOutcomeTracker:
    """
    Tracks human decisions on fraud reports and calculates detector accuracy.

    Use this to:
    - Record CEO/reviewer decisions on fraud alerts
    - Calculate which detectors are most accurate
    - Identify domains with high FP rates
    - Tune detector thresholds based on real outcomes
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # OUTCOME RECORDING
    # =========================================================================

    def record_outcome(
        self,
        report_id: int,
        outcome: OutcomeType,
        decided_by: str = 'user',
        notes: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> bool:
        """
        Record a human decision on a fraud report.

        Args:
            report_id: ID of the fraud_reports record
            outcome: Decision - 'true_positive', 'false_positive', 'dismissed', 'pending'
            decided_by: Who made the decision (email, agent ID, or 'user')
            notes: Optional explanation for the decision
            confidence: Optional reviewer confidence (0.0-1.0)

        Returns:
            True if recorded successfully, False if report not found

        Example:
            >>> tracker = FraudOutcomeTracker()
            >>> tracker.record_outcome(
            ...     report_id=123,
            ...     outcome='false_positive',
            ...     decided_by='ceo@example.com',
            ...     notes='This is normal behavior for this domain'
            ... )
        """
        conn = self._get_connection()
        try:
            # Check if report exists
            cursor = conn.execute(
                "SELECT id FROM fraud_reports WHERE id = ?",
                (report_id,)
            )
            if not cursor.fetchone():
                return False

            # Update the fraud report
            conn.execute("""
                UPDATE fraud_reports
                SET review_outcome = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?
                WHERE id = ?
            """, (outcome, decided_by, report_id))

            # Store notes if provided (in fraud_outcome_history via trigger)
            # The trigger automatically records this in fraud_outcome_history

            # If we want to store confidence, we'd need to add that column
            # For now, we can store it in the notes as structured data
            if confidence is not None or notes is not None:
                metadata = {}
                if confidence is not None:
                    metadata['confidence'] = confidence
                if notes is not None:
                    metadata['notes'] = notes

                # Store in outcome history manually (in addition to trigger)
                conn.execute("""
                    UPDATE fraud_outcome_history
                    SET change_reason = ?
                    WHERE fraud_report_id = ?
                      AND changed_at = (
                          SELECT MAX(changed_at)
                          FROM fraud_outcome_history
                          WHERE fraud_report_id = ?
                      )
                """, (json.dumps(metadata), report_id, report_id))

            conn.commit()
            return True

        finally:
            conn.close()

    def batch_record_outcomes(
        self,
        outcomes: List[Tuple[int, OutcomeType, str, Optional[str]]]
    ) -> Dict[str, int]:
        """
        Record multiple outcomes at once.

        Args:
            outcomes: List of (report_id, outcome, decided_by, notes) tuples

        Returns:
            Dictionary with 'success' and 'failed' counts

        Example:
            >>> tracker.batch_record_outcomes([
            ...     (123, 'true_positive', 'ceo', 'Confirmed fraud'),
            ...     (124, 'false_positive', 'ceo', 'Safe heuristic'),
            ...     (125, 'dismissed', 'ceo', 'Unclear')
            ... ])
            {'success': 3, 'failed': 0}
        """
        success = 0
        failed = 0

        for report_id, outcome, decided_by, notes in outcomes:
            if self.record_outcome(report_id, outcome, decided_by, notes):
                success += 1
            else:
                failed += 1

        return {'success': success, 'failed': failed}

    # =========================================================================
    # DETECTOR ACCURACY QUERIES
    # =========================================================================

    def get_detector_accuracy(
        self,
        detector_name: Optional[str] = None,
        days: Optional[int] = None
    ) -> List[DetectorAccuracy]:
        """
        Get accuracy metrics for one or all detectors.

        Args:
            detector_name: Specific detector to query (None = all detectors)
            days: Limit to last N days (None = all time)

        Returns:
            List of DetectorAccuracy objects

        Example:
            >>> tracker = FraudOutcomeTracker()
            >>> # Get all detectors in last 30 days
            >>> accuracies = tracker.get_detector_accuracy(days=30)
            >>> for acc in accuracies:
            ...     print(f"{acc.detector_name}: {acc.precision:.2%} precision")
        """
        conn = self._get_connection()
        try:
            # Build query based on filters
            query = """
                SELECT
                    asig.detector_name,
                    COUNT(DISTINCT fr.id) as total_reports,
                    SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) as true_positives,
                    SUM(CASE WHEN fr.review_outcome = 'false_positive' THEN 1 ELSE 0 END) as false_positives,
                    SUM(CASE WHEN fr.review_outcome IS NULL OR fr.review_outcome = 'pending' THEN 1 ELSE 0 END) as pending,
                    CASE
                        WHEN SUM(CASE WHEN fr.review_outcome IN ('true_positive', 'false_positive') THEN 1 ELSE 0 END) > 0
                        THEN CAST(SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) AS REAL) /
                             SUM(CASE WHEN fr.review_outcome IN ('true_positive', 'false_positive') THEN 1 ELSE 0 END)
                        ELSE NULL
                    END as precision,
                    AVG(asig.score) as avg_anomaly_score,
                    MIN(fr.created_at) as first_detection,
                    MAX(fr.created_at) as last_detection
                FROM anomaly_signals asig
                JOIN fraud_reports fr ON asig.fraud_report_id = fr.id
                WHERE 1=1
            """

            params = []

            if detector_name:
                query += " AND asig.detector_name = ?"
                params.append(detector_name)

            if days:
                query += " AND fr.created_at > datetime('now', '-' || ? || ' days')"
                params.append(days)

            query += " GROUP BY asig.detector_name ORDER BY precision DESC"

            cursor = conn.execute(query, params)
            results = []

            # Determine time period label
            if days is None:
                period = 'all_time'
            elif days <= 1:
                period = 'last_24h'
            elif days <= 7:
                period = 'last_7d'
            elif days <= 30:
                period = 'last_30d'
            else:
                period = 'all_time'

            for row in cursor.fetchall():
                results.append(DetectorAccuracy(
                    detector_name=row['detector_name'],
                    time_period=period,
                    total_reports=row['total_reports'],
                    true_positives=row['true_positives'],
                    false_positives=row['false_positives'],
                    pending=row['pending'],
                    precision=row['precision'],
                    avg_anomaly_score=row['avg_anomaly_score'],
                    first_detection=datetime.fromisoformat(row['first_detection']) if row['first_detection'] else None,
                    last_detection=datetime.fromisoformat(row['last_detection']) if row['last_detection'] else None
                ))

            return results

        finally:
            conn.close()

    def get_domain_accuracy(
        self,
        domain: Optional[str] = None,
        days: Optional[int] = None
    ) -> List[DomainAccuracy]:
        """
        Get fraud detection accuracy by domain.

        Args:
            domain: Specific domain to query (None = all domains)
            days: Limit to last N days (None = all time)

        Returns:
            List of DomainAccuracy objects

        Example:
            >>> accuracies = tracker.get_domain_accuracy(domain='git-workflow')
            >>> if accuracies:
            ...     acc = accuracies[0]
            ...     print(f"Domain: {acc.domain}")
            ...     print(f"Precision: {acc.precision:.2%}")
            ...     print(f"FP Rate: {acc.false_positives / acc.total_reports:.2%}")
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT
                    h.domain,
                    COUNT(DISTINCT fr.id) as total_reports,
                    SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) as true_positives,
                    SUM(CASE WHEN fr.review_outcome = 'false_positive' THEN 1 ELSE 0 END) as false_positives,
                    SUM(CASE WHEN fr.review_outcome IS NULL OR fr.review_outcome = 'pending' THEN 1 ELSE 0 END) as pending,
                    CASE
                        WHEN SUM(CASE WHEN fr.review_outcome IN ('true_positive', 'false_positive') THEN 1 ELSE 0 END) > 0
                        THEN CAST(SUM(CASE WHEN fr.review_outcome = 'true_positive' THEN 1 ELSE 0 END) AS REAL) /
                             SUM(CASE WHEN fr.review_outcome IN ('true_positive', 'false_positive') THEN 1 ELSE 0 END)
                        ELSE NULL
                    END as precision,
                    AVG(fr.fraud_score) as avg_fraud_score
                FROM fraud_reports fr
                JOIN heuristics h ON fr.heuristic_id = h.id
                WHERE 1=1
            """

            params = []

            if domain:
                query += " AND h.domain = ?"
                params.append(domain)

            if days:
                query += " AND fr.created_at > datetime('now', '-' || ? || ' days')"
                params.append(days)

            query += " GROUP BY h.domain HAVING total_reports > 0 ORDER BY precision DESC"

            cursor = conn.execute(query, params)
            results = []

            for row in cursor.fetchall():
                results.append(DomainAccuracy(
                    domain=row['domain'],
                    total_reports=row['total_reports'],
                    true_positives=row['true_positives'],
                    false_positives=row['false_positives'],
                    pending=row['pending'],
                    precision=row['precision'],
                    avg_fraud_score=row['avg_fraud_score']
                ))

            return results

        finally:
            conn.close()

    # =========================================================================
    # ANALYSIS & REPORTING
    # =========================================================================

    def get_pending_reports(self, limit: int = 50) -> List[Dict]:
        """
        Get fraud reports awaiting review, prioritized by severity.

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of pending reports with metadata

        Example:
            >>> pending = tracker.get_pending_reports(limit=10)
            >>> for report in pending:
            ...     print(f"Report {report['report_id']}: {report['classification']}")
            ...     print(f"  Domain: {report['domain']}, Score: {report['fraud_score']:.2f}")
            ...     print(f"  Detectors: {report['detectors']}")
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM pending_review_queue
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    def get_classification_accuracy(self) -> List[Dict]:
        """
        Check if fraud_score thresholds align with human decisions.

        Returns classification accuracy view showing how often each
        classification level (clean, suspicious, fraud_likely, etc.)
        is confirmed vs rejected by humans.

        Example:
            >>> accuracies = tracker.get_classification_accuracy()
            >>> for acc in accuracies:
            ...     print(f"{acc['classification']}: {acc['accuracy']:.1%} accuracy")
            ...     print(f"  Score range: {acc['min_score']:.2f} - {acc['max_score']:.2f}")
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM classification_accuracy")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_detector_confusion_matrix(self) -> List[Dict]:
        """
        Get confusion matrix showing TP/FP distribution per detector.

        Useful for understanding which detectors are most reliable
        at different severity levels.

        Returns:
            List of confusion matrix entries per detector/severity

        Example:
            >>> matrix = tracker.get_detector_confusion_matrix()
            >>> for entry in matrix:
            ...     print(f"{entry['detector_name']} ({entry['severity']}):")
            ...     print(f"  TP: {entry['tp_count']}, FP: {entry['fp_count']}")
            ...     print(f"  TP Rate: {entry['tp_rate']:.1%}")
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM detector_confusion_matrix")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def identify_underperforming_detectors(
        self,
        min_reports: int = 10,
        max_precision: float = 0.5
    ) -> List[Dict]:
        """
        Find detectors with low precision (high FP rate).

        Args:
            min_reports: Minimum reports needed to evaluate (default 10)
            max_precision: Precision threshold below which detector is flagged (default 0.5)

        Returns:
            List of underperforming detectors with their metrics

        Example:
            >>> bad_detectors = tracker.identify_underperforming_detectors()
            >>> if bad_detectors:
            ...     print("⚠️ Detectors needing attention:")
            ...     for d in bad_detectors:
            ...         print(f"  - {d['detector_name']}: {d['precision']:.1%} precision")
        """
        accuracies = self.get_detector_accuracy()

        underperforming = []
        for acc in accuracies:
            if (acc.total_reports >= min_reports and
                acc.precision is not None and
                acc.precision < max_precision):
                underperforming.append({
                    'detector_name': acc.detector_name,
                    'precision': acc.precision,
                    'total_reports': acc.total_reports,
                    'true_positives': acc.true_positives,
                    'false_positives': acc.false_positives,
                    'avg_anomaly_score': acc.avg_anomaly_score
                })

        return sorted(underperforming, key=lambda x: x['precision'])

    def generate_performance_report(self, days: int = 30) -> Dict:
        """
        Generate comprehensive performance report.

        Args:
            days: Time window for analysis (default 30 days)

        Returns:
            Dictionary with overall metrics, detector stats, and domain stats

        Example:
            >>> report = tracker.generate_performance_report(days=30)
            >>> print(f"Total reports: {report['summary']['total_reports']}")
            >>> print(f"Overall precision: {report['summary']['overall_precision']:.1%}")
            >>> print(f"Pending review: {report['summary']['pending']}")
        """
        conn = self._get_connection()
        try:
            # Overall summary
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_reports,
                    SUM(CASE WHEN review_outcome = 'true_positive' THEN 1 ELSE 0 END) as total_tp,
                    SUM(CASE WHEN review_outcome = 'false_positive' THEN 1 ELSE 0 END) as total_fp,
                    SUM(CASE WHEN review_outcome IS NULL OR review_outcome = 'pending' THEN 1 ELSE 0 END) as pending,
                    AVG(fraud_score) as avg_fraud_score
                FROM fraud_reports
                WHERE created_at > datetime('now', '-' || ? || ' days')
            """, (days,))

            summary = dict(cursor.fetchone())

            # Calculate overall precision
            reviewed = summary['total_tp'] + summary['total_fp']
            summary['overall_precision'] = summary['total_tp'] / reviewed if reviewed > 0 else None

            # Get detector accuracies
            detector_accuracies = self.get_detector_accuracy(days=days)

            # Get domain accuracies
            domain_accuracies = self.get_domain_accuracy(days=days)

            # Get underperforming detectors
            underperforming = self.identify_underperforming_detectors()

            return {
                'time_period': f'last_{days}d',
                'summary': summary,
                'detectors': [
                    {
                        'name': acc.detector_name,
                        'precision': acc.precision,
                        'total_reports': acc.total_reports,
                        'tp': acc.true_positives,
                        'fp': acc.false_positives,
                        'pending': acc.pending
                    }
                    for acc in detector_accuracies
                ],
                'domains': [
                    {
                        'domain': acc.domain,
                        'precision': acc.precision,
                        'total_reports': acc.total_reports,
                        'tp': acc.true_positives,
                        'fp': acc.false_positives
                    }
                    for acc in domain_accuracies
                ],
                'underperforming': underperforming
            }

        finally:
            conn.close()


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fraud Outcome Tracking")
    parser.add_argument("command", choices=[
        "record", "pending", "accuracy", "domains", "report", "underperforming"
    ])
    parser.add_argument("--report-id", type=int, help="Fraud report ID")
    parser.add_argument("--outcome", choices=['true_positive', 'false_positive', 'dismissed', 'pending'],
                       help="Outcome decision")
    parser.add_argument("--decided-by", default="cli", help="Who made the decision")
    parser.add_argument("--notes", help="Notes about the decision")
    parser.add_argument("--detector", help="Filter by detector name")
    parser.add_argument("--domain", help="Filter by domain")
    parser.add_argument("--days", type=int, default=30, help="Time period in days")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    tracker = FraudOutcomeTracker()
    result = None

    if args.command == "record":
        if not args.report_id or not args.outcome:
            print("Error: --report-id and --outcome required")
            exit(1)
        success = tracker.record_outcome(
            args.report_id,
            args.outcome,
            args.decided_by,
            args.notes
        )
        result = {"success": success, "report_id": args.report_id}

    elif args.command == "pending":
        result = tracker.get_pending_reports()

    elif args.command == "accuracy":
        accuracies = tracker.get_detector_accuracy(args.detector, args.days)
        result = [
            {
                'detector': acc.detector_name,
                'precision': acc.precision,
                'total': acc.total_reports,
                'tp': acc.true_positives,
                'fp': acc.false_positives,
                'pending': acc.pending
            }
            for acc in accuracies
        ]

    elif args.command == "domains":
        accuracies = tracker.get_domain_accuracy(args.domain, args.days)
        result = [
            {
                'domain': acc.domain,
                'precision': acc.precision,
                'total': acc.total_reports,
                'tp': acc.true_positives,
                'fp': acc.false_positives
            }
            for acc in accuracies
        ]

    elif args.command == "report":
        result = tracker.generate_performance_report(args.days)

    elif args.command == "underperforming":
        result = tracker.identify_underperforming_detectors()

    if args.json or result is not None:
        print(json.dumps(result, indent=2, default=str))
