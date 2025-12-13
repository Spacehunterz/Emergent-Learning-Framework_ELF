#!/usr/bin/env python3
"""
Fraud Detection System for Heuristic Lifecycle
Phase 2D Implementation

Implements multi-layered fraud detection using:
1. Success Rate Anomaly Detection (Z-score vs domain baseline)
2. Temporal Pattern Detection (cooldown gaming, midnight clustering)
3. Confidence Trajectory Analysis (unnatural growth patterns)

Based on: reports/phase2/fraud-detection-design.md
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
from statistics import mean, stdev, variance
from math import prod

# Configuration
DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

@dataclass
class AnomalySignal:
    """Represents a single anomaly detection signal."""
    detector_name: str
    score: float  # 0.0 - 1.0
    severity: str  # low, medium, high, critical
    reason: str
    evidence: Dict[str, Any]

@dataclass
class FraudReport:
    """Complete fraud detection report."""
    heuristic_id: int
    fraud_score: float  # 0.0 - 1.0 (Bayesian posterior)
    classification: str  # clean, suspicious, fraud_likely, fraud_confirmed
    signals: List[AnomalySignal]
    likelihood_ratio: float
    timestamp: datetime

@dataclass
class FraudConfig:
    """Configuration for fraud detection."""
    # False positive tolerance (CEO decision: 5% FPR)
    fpr_tolerance: float = 0.05

    # Bayesian prior (assume 5% base rate of fraud)
    prior_fraud_rate: float = 0.05

    # Classification thresholds
    threshold_suspicious: float = 0.20
    threshold_fraud_likely: float = 0.50
    threshold_fraud_confirmed: float = 0.80

    # Detector-specific thresholds
    success_rate_z_threshold: float = 2.5  # >99% percentile
    temporal_score_threshold: float = 0.5
    trajectory_score_threshold: float = 0.5

    # Minimum data requirements
    min_applications: int = 10
    min_updates_for_temporal: int = 5
    min_updates_for_trajectory: int = 10

    # Context tracking (CEO decision: hash only, 7-day retention)
    context_retention_days: int = 7
    context_hash_algorithm: str = "sha256"


class FraudDetector:
    """
    Multi-layered fraud detection system.

    Detects:
    - Pump-and-dump attacks (selective validation, timing gaming)
    - Coordinated manipulation (multi-agent)
    - Revival gaming
    - Unnatural confidence trajectories
    """

    def __init__(self, db_path: Path = DB_PATH, config: Optional[FraudConfig] = None):
        self.db_path = db_path
        self.config = config or FraudConfig()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # DETECTOR 1: Success Rate Anomaly Detection
    # =========================================================================

    def detect_success_rate_anomaly(self, heuristic_id: int) -> Optional[AnomalySignal]:
        """
        Compare heuristic success rate to domain baseline using Z-score.

        Flags if:
        - Success rate > (domain_avg + 2.5*stddev) AND
        - Applications >= 10 AND
        - Not a golden rule (whitelisted)
        """
        conn = self._get_connection()
        try:
            # Get heuristic stats
            cursor = conn.execute("""
                SELECT
                    h.id, h.domain, h.confidence, h.is_golden,
                    h.times_validated, h.times_violated,
                    COALESCE(h.times_contradicted, 0) as times_contradicted
                FROM heuristics h
                WHERE h.id = ?
            """, (heuristic_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # Whitelist golden rules
            if row['is_golden']:
                return None

            total_apps = row['times_validated'] + row['times_violated'] + row['times_contradicted']

            # Insufficient data
            if total_apps < self.config.min_applications:
                return None

            success_rate = row['times_validated'] / total_apps

            # Get domain baseline
            baseline = self._get_domain_baseline(conn, row['domain'])
            if not baseline or baseline['sample_count'] < 3:
                # Not enough domain data, skip
                return None

            domain_avg = baseline['avg_success_rate']
            domain_std = baseline['std_success_rate']

            if domain_std == 0:
                # No variance in domain, skip
                return None

            # Calculate Z-score
            z_score = (success_rate - domain_avg) / domain_std

            # Anomaly detection
            if z_score > self.config.success_rate_z_threshold:
                score = min(z_score / 5.0, 1.0)  # Normalize to 0-1
                severity = "high" if z_score > 3.5 else "medium"

                return AnomalySignal(
                    detector_name="success_rate_anomaly",
                    score=score,
                    severity=severity,
                    reason=f"Success rate {success_rate:.1%} is {z_score:.1f}σ above domain average {domain_avg:.1%}",
                    evidence={
                        "success_rate": success_rate,
                        "domain_avg": domain_avg,
                        "domain_std": domain_std,
                        "z_score": z_score,
                        "total_applications": total_apps
                    }
                )

            return None
        finally:
            conn.close()

    def _get_domain_baseline(self, conn: sqlite3.Connection, domain: str) -> Optional[Dict]:
        """Get statistical baseline for a domain."""
        cursor = conn.execute("""
            SELECT * FROM domain_baselines WHERE domain = ?
        """, (domain,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_domain_baseline(self, domain: str) -> Dict[str, Any]:
        """
        Recalculate domain baseline from all heuristics in domain.

        Calculates:
        - Average success rate
        - Standard deviation of success rate
        - Average update frequency
        """
        conn = self._get_connection()
        try:
            # Get all heuristics in domain with sufficient data
            cursor = conn.execute("""
                SELECT
                    h.id,
                    h.times_validated,
                    h.times_violated,
                    COALESCE(h.times_contradicted, 0) as times_contradicted,
                    (h.times_validated + h.times_violated + COALESCE(h.times_contradicted, 0)) as total_apps
                FROM heuristics h
                WHERE h.domain = ?
                  AND h.status = 'active'
                  AND (h.times_validated + h.times_violated + COALESCE(h.times_contradicted, 0)) >= ?
            """, (domain, self.config.min_applications))

            heuristics = cursor.fetchall()

            if len(heuristics) < 3:
                # Not enough data for meaningful baseline
                return {
                    "domain": domain,
                    "sample_count": len(heuristics),
                    "error": "Insufficient sample size (need 3+)"
                }

            # Calculate success rates
            success_rates = []
            for h in heuristics:
                if h['total_apps'] > 0:
                    success_rates.append(h['times_validated'] / h['total_apps'])

            if not success_rates:
                return {"domain": domain, "error": "No valid success rates"}

            avg_success = mean(success_rates)
            std_success = stdev(success_rates) if len(success_rates) > 1 else 0.0

            # Calculate update frequency (updates per day)
            cursor = conn.execute("""
                SELECT
                    h.id,
                    COUNT(cu.id) as update_count,
                    JULIANDAY('now') - JULIANDAY(MIN(cu.created_at)) as days_active
                FROM heuristics h
                JOIN confidence_updates cu ON h.id = cu.heuristic_id
                WHERE h.domain = ?
                  AND h.status = 'active'
                GROUP BY h.id
                HAVING days_active > 0
            """, (domain,))

            update_frequencies = []
            for row in cursor.fetchall():
                freq = row['update_count'] / max(row['days_active'], 1)
                update_frequencies.append(freq)

            avg_freq = mean(update_frequencies) if update_frequencies else 0.0
            std_freq = stdev(update_frequencies) if len(update_frequencies) > 1 else 0.0

            # Store baseline
            conn.execute("""
                INSERT OR REPLACE INTO domain_baselines
                (domain, avg_success_rate, std_success_rate,
                 avg_update_frequency, std_update_frequency,
                 sample_count, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (domain, avg_success, std_success, avg_freq, std_freq, len(heuristics)))

            conn.commit()

            return {
                "domain": domain,
                "avg_success_rate": avg_success,
                "std_success_rate": std_success,
                "avg_update_frequency": avg_freq,
                "sample_count": len(heuristics)
            }
        finally:
            conn.close()

    # =========================================================================
    # DETECTOR 2: Temporal Pattern Analysis
    # =========================================================================

    def detect_temporal_manipulation(self, heuristic_id: int) -> Optional[AnomalySignal]:
        """
        Detect suspicious timing patterns in updates.

        Signals:
        1. Updates clustered at cooldown boundary (60-65 min intervals)
        2. Updates clustered at midnight (daily reset gaming)
        3. Too-regular timing (low coefficient of variation)
        """
        conn = self._get_connection()
        try:
            # Get recent updates
            cursor = conn.execute("""
                SELECT created_at, update_type
                FROM confidence_updates
                WHERE heuristic_id = ?
                  AND created_at > datetime('now', '-30 days')
                ORDER BY created_at ASC
            """, (heuristic_id,))

            updates = cursor.fetchall()

            if len(updates) < self.config.min_updates_for_temporal:
                return None

            # Calculate inter-update intervals (in minutes)
            intervals = []
            timestamps = [datetime.fromisoformat(u['created_at']) for u in updates]

            for i in range(1, len(timestamps)):
                delta_minutes = (timestamps[i] - timestamps[i-1]).total_seconds() / 60
                intervals.append(delta_minutes)

            if not intervals:
                return None

            # Signal 1: Cooldown boundary clustering (60-65 minutes)
            cooldown_cluster_count = sum(1 for iv in intervals if 60 <= iv <= 65)
            cooldown_cluster_rate = cooldown_cluster_count / len(intervals)

            # Signal 2: Midnight clustering
            midnight_hours = {0, 1, 23}
            midnight_count = sum(1 for ts in timestamps if ts.hour in midnight_hours)
            midnight_rate = midnight_count / len(timestamps)
            expected_midnight_rate = 3 / 24  # 3 hours out of 24

            # Signal 3: Regularity (low CV = suspicious)
            interval_mean = mean(intervals)
            interval_std = stdev(intervals) if len(intervals) > 1 else 0
            coefficient_of_variation = interval_std / interval_mean if interval_mean > 0 else 0

            # Low CV means very regular timing (suspicious)
            regularity_suspicion = max(0, 1.0 - (coefficient_of_variation / 0.5))

            # Combine signals
            anomaly_score = (
                0.4 * cooldown_cluster_rate +
                0.3 * max(0, (midnight_rate - expected_midnight_rate) * 4) +
                0.3 * regularity_suspicion
            )

            if anomaly_score > self.config.temporal_score_threshold:
                severity = "high" if anomaly_score > 0.7 else "medium"

                return AnomalySignal(
                    detector_name="temporal_manipulation",
                    score=anomaly_score,
                    severity=severity,
                    reason=f"Suspicious timing: {cooldown_cluster_rate:.0%} at cooldown boundary, {midnight_rate:.0%} at midnight, CV={coefficient_of_variation:.2f}",
                    evidence={
                        "cooldown_cluster_rate": cooldown_cluster_rate,
                        "midnight_rate": midnight_rate,
                        "expected_midnight_rate": expected_midnight_rate,
                        "coefficient_of_variation": coefficient_of_variation,
                        "total_updates": len(updates),
                        "interval_count": len(intervals)
                    }
                )

            return None
        finally:
            conn.close()

    # =========================================================================
    # DETECTOR 3: Confidence Trajectory Analysis
    # =========================================================================

    def detect_unnatural_confidence_growth(self, heuristic_id: int) -> Optional[AnomalySignal]:
        """
        Detect confidence growth patterns inconsistent with natural learning.

        Natural learning: noisy, plateaus, occasional drops
        Manipulated: smooth, monotonic, too fast
        """
        conn = self._get_connection()
        try:
            # Get confidence trajectory
            cursor = conn.execute("""
                SELECT new_confidence, created_at, update_type
                FROM confidence_updates
                WHERE heuristic_id = ?
                  AND created_at > datetime('now', '-60 days')
                ORDER BY created_at ASC
            """, (heuristic_id,))

            updates = cursor.fetchall()

            if len(updates) < self.config.min_updates_for_trajectory:
                return None

            confidences = [u['new_confidence'] for u in updates]
            timestamps = [datetime.fromisoformat(u['created_at']) for u in updates]

            # Signal 1: Monotonic growth (never drops)
            monotonic = all(confidences[i] >= confidences[i-1] for i in range(1, len(confidences)))

            # Signal 2: Growth rate (slope)
            time_days = [(timestamps[i] - timestamps[0]).days for i in range(len(timestamps))]
            if time_days[-1] > 0:
                slope = (confidences[-1] - confidences[0]) / time_days[-1]
            else:
                slope = 0

            # Signal 3: Smoothness (low variance in deltas)
            deltas = [confidences[i] - confidences[i-1] for i in range(1, len(confidences))]
            delta_variance = variance(deltas) if len(deltas) > 1 else 0

            # Low variance = too smooth (suspicious)
            smoothness_score = max(0, 1.0 - min(delta_variance / 0.01, 1.0))

            # Combine signals
            anomaly_score = (
                0.3 * (1.0 if (monotonic and len(updates) > 10) else 0) +
                0.4 * min(slope / 0.02, 1.0) +  # >0.02 conf/day = suspicious
                0.3 * smoothness_score
            )

            if anomaly_score > self.config.trajectory_score_threshold:
                return AnomalySignal(
                    detector_name="unnatural_confidence_growth",
                    score=anomaly_score,
                    severity="medium",
                    reason=f"Unnatural growth: monotonic={monotonic}, slope={slope:.4f}/day, smoothness={smoothness_score:.2f}",
                    evidence={
                        "monotonic": monotonic,
                        "growth_slope": slope,
                        "smoothness_score": smoothness_score,
                        "delta_variance": delta_variance,
                        "total_updates": len(updates),
                        "confidence_start": confidences[0],
                        "confidence_end": confidences[-1]
                    }
                )

            return None
        finally:
            conn.close()

    # =========================================================================
    # MAIN ORCHESTRATION
    # =========================================================================

    def run_all_detectors(self, heuristic_id: int) -> List[AnomalySignal]:
        """
        Run all detection algorithms on a heuristic.

        Returns list of detected anomalies (empty if clean).
        """
        signals = []

        # Run each detector
        detectors = [
            self.detect_success_rate_anomaly,
            self.detect_temporal_manipulation,
            self.detect_unnatural_confidence_growth
        ]

        for detector in detectors:
            signal = detector(heuristic_id)
            if signal:
                signals.append(signal)

        return signals

    def calculate_combined_score(self, signals: List[AnomalySignal]) -> Tuple[float, float]:
        """
        Combine anomaly signals using Bayesian fusion.

        Returns:
            (posterior_probability, combined_likelihood_ratio)
        """
        if not signals:
            return 0.0, 1.0

        # Prior probability of fraud
        prior_fraud = self.config.prior_fraud_rate

        # Calculate likelihood ratios for each signal
        likelihood_ratios = []
        for signal in signals:
            # P(signal | fraud) vs P(signal | clean)
            # Assumption:
            # - High-scoring signals are more likely from fraud (0.8 * score)
            # - Clean heuristics rarely show high scores (0.1 * score)

            p_signal_given_fraud = 0.8 * signal.score
            p_signal_given_clean = 0.1 * signal.score

            if p_signal_given_clean > 0:
                lr = p_signal_given_fraud / p_signal_given_clean
            else:
                lr = 10.0  # Default high LR

            likelihood_ratios.append(lr)

        # Combine likelihood ratios (multiply)
        combined_lr = prod(likelihood_ratios)

        # Posterior odds = prior odds * LR
        prior_odds = prior_fraud / (1 - prior_fraud)
        posterior_odds = prior_odds * combined_lr

        # Convert to probability
        posterior_prob = posterior_odds / (1 + posterior_odds)

        return posterior_prob, combined_lr

    def classify_fraud_score(self, fraud_score: float) -> str:
        """Classify fraud score into categories."""
        if fraud_score > self.config.threshold_fraud_confirmed:
            return "fraud_confirmed"
        elif fraud_score > self.config.threshold_fraud_likely:
            return "fraud_likely"
        elif fraud_score > self.config.threshold_suspicious:
            return "suspicious"
        elif fraud_score > 0:
            return "low_confidence"
        else:
            return "clean"

    def create_fraud_report(self, heuristic_id: int) -> FraudReport:
        """
        Run complete fraud detection analysis and create report.
        """
        # Run all detectors
        signals = self.run_all_detectors(heuristic_id)

        # Calculate combined score
        fraud_score, likelihood_ratio = self.calculate_combined_score(signals)

        # Classify
        classification = self.classify_fraud_score(fraud_score)

        # Create report
        report = FraudReport(
            heuristic_id=heuristic_id,
            fraud_score=fraud_score,
            classification=classification,
            signals=signals,
            likelihood_ratio=likelihood_ratio,
            timestamp=datetime.now()
        )

        # Store in database
        self._store_fraud_report(report)

        # Take response action
        self._handle_fraud_response(report)

        return report

    def _store_fraud_report(self, report: FraudReport):
        """Store fraud report in database."""
        conn = self._get_connection()
        try:
            # Insert fraud report
            cursor = conn.execute("""
                INSERT INTO fraud_reports
                (heuristic_id, fraud_score, classification, likelihood_ratio, signal_count)
                VALUES (?, ?, ?, ?, ?)
            """, (
                report.heuristic_id,
                report.fraud_score,
                report.classification,
                report.likelihood_ratio,
                len(report.signals)
            ))

            fraud_report_id = cursor.lastrowid

            # Insert anomaly signals
            for signal in report.signals:
                conn.execute("""
                    INSERT INTO anomaly_signals
                    (fraud_report_id, heuristic_id, detector_name, score, severity, reason, evidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    fraud_report_id,
                    report.heuristic_id,
                    signal.detector_name,
                    signal.score,
                    signal.severity,
                    signal.reason,
                    json.dumps(signal.evidence)
                ))

            # Update heuristic fraud tracking
            conn.execute("""
                UPDATE heuristics SET
                    fraud_flags = COALESCE(fraud_flags, 0) + 1,
                    last_fraud_check = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (report.heuristic_id,))

            conn.commit()
        finally:
            conn.close()

    def _handle_fraud_response(self, report: FraudReport):
        """
        Take appropriate action based on fraud classification.

        CEO Decision: Alert only for now (no auto-quarantine)
        """
        conn = self._get_connection()
        try:
            # Get fraud report ID
            cursor = conn.execute("""
                SELECT id FROM fraud_reports
                WHERE heuristic_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (report.heuristic_id,))
            row = cursor.fetchone()
            if not row:
                return

            fraud_report_id = row['id']

            # CEO Decision: Alert only (no auto-quarantine without CEO review)
            if report.classification in ('fraud_likely', 'fraud_confirmed'):
                # Record alert action
                conn.execute("""
                    INSERT INTO fraud_responses
                    (fraud_report_id, response_type, parameters, executed_by)
                    VALUES (?, 'alert', ?, 'system')
                """, (fraud_report_id, json.dumps({
                    "classification": report.classification,
                    "fraud_score": report.fraud_score,
                    "signal_count": len(report.signals)
                })))

                conn.commit()

                # TODO: Future enhancement - create CEO escalation file
                # For now, just log the alert
        finally:
            conn.close()

    def get_pending_reports(self) -> List[Dict]:
        """Get fraud reports pending CEO review."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    fr.*,
                    h.domain,
                    h.rule,
                    h.confidence
                FROM fraud_reports fr
                JOIN heuristics h ON fr.heuristic_id = h.id
                WHERE fr.review_outcome IS NULL OR fr.review_outcome = 'pending'
                ORDER BY fr.fraud_score DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def track_context(self, session_id: str, context_text: str,
                      heuristics_applied: List[int],
                      agent_id: Optional[str] = None):
        """
        Track session context for application selectivity detection.

        CEO Decision: Hash for privacy, 7-day retention
        """
        conn = self._get_connection()
        try:
            # Hash the context for privacy
            context_hash = hashlib.sha256(
                context_text.encode('utf-8')
            ).hexdigest()

            # Preview (first 100 chars for debugging)
            preview = context_text[:100] if len(context_text) > 100 else context_text

            conn.execute("""
                INSERT INTO session_contexts
                (session_id, agent_id, context_hash, context_preview, heuristics_applied)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                agent_id,
                context_hash,
                preview,
                json.dumps(heuristics_applied)
            ))

            conn.commit()
        finally:
            conn.close()

    def cleanup_old_contexts(self):
        """Remove context records older than retention period."""
        conn = self._get_connection()
        try:
            conn.execute("""
                DELETE FROM session_contexts
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (self.config.context_retention_days,))
            conn.commit()
        finally:
            conn.close()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fraud Detection System")
    parser.add_argument("command", choices=[
        "check", "update-baseline", "pending", "stats"
    ])
    parser.add_argument("--heuristic-id", type=int, help="Heuristic ID to check")
    parser.add_argument("--domain", help="Domain for baseline update")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    detector = FraudDetector()

    if args.command == "check":
        if not args.heuristic_id:
            print("Error: --heuristic-id required for check command")
            exit(1)
        report = detector.create_fraud_report(args.heuristic_id)
        result = {
            "heuristic_id": report.heuristic_id,
            "fraud_score": report.fraud_score,
            "classification": report.classification,
            "signals": [
                {
                    "detector": s.detector_name,
                    "score": s.score,
                    "severity": s.severity,
                    "reason": s.reason
                }
                for s in report.signals
            ]
        }

    elif args.command == "update-baseline":
        if not args.domain:
            print("Error: --domain required for update-baseline command")
            exit(1)
        result = detector.update_domain_baseline(args.domain)

    elif args.command == "pending":
        result = detector.get_pending_reports()

    elif args.command == "stats":
        # Get overall fraud detection stats
        conn = detector._get_connection()
        cursor = conn.execute("SELECT * FROM fraud_detection_metrics")
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(json.dumps(result, indent=2, default=str))
