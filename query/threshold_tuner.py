#!/usr/bin/env python3
"""
Adaptive Threshold Tuning for Fraud Detection
Phase 2D Enhancement - Agent 2

Analyzes TP/FP data to recommend optimal thresholds.
NEVER auto-applies - generates recommendations for CEO review.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

@dataclass
class ThresholdRecommendation:
    """Recommendation for threshold adjustment."""
    detector_name: Optional[str]
    threshold_type: str  # 'detector' or 'classification'
    level: Optional[str]  # For classification: 'suspicious', 'fraud_likely', 'fraud_confirmed'
    current_threshold: float
    recommended_threshold: float
    target_fpr: float
    achieved_fpr: float
    achieved_tpr: float
    sample_size: int
    tp_count: int
    fp_count: int
    confidence: str
    reason: str

class ThresholdTuner:
    """Adaptive threshold tuning system."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # DETECTOR-LEVEL THRESHOLD TUNING
    # =========================================================================

    def calculate_optimal_threshold(
        self,
        detector_name: str,
        target_fpr: float = 0.05,
        min_samples: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate optimal threshold for a detector using frequentist approach.

        Uses empirical TP/FP rates to find threshold achieving target FPR.

        Args:
            detector_name: Which detector to tune (e.g., 'success_rate_anomaly')
            target_fpr: Maximum acceptable false positive rate (default 5%)
            min_samples: Minimum reviewed samples required (default 30)

        Returns:
            Dict with recommendation or error if insufficient data
        """
        conn = self._get_connection()
        try:
            # Get reviewed signal data
            cursor = conn.execute("""
                SELECT asig.score, fr.review_outcome
                FROM anomaly_signals asig
                JOIN fraud_reports fr ON asig.fraud_report_id = fr.id
                WHERE fr.review_outcome IN ('true_positive', 'false_positive')
                  AND asig.detector_name = ?
                ORDER BY asig.score ASC
            """, (detector_name,))

            signals = cursor.fetchall()

            if len(signals) < min_samples:
                return {
                    'detector_name': detector_name,
                    'error': 'insufficient_data',
                    'sample_size': len(signals),
                    'min_required': min_samples,
                    'reason': f'Need {min_samples - len(signals)} more reviewed samples'
                }

            # Extract data
            scores = [s['score'] for s in signals]
            outcomes = [1 if s['review_outcome'] == 'true_positive' else 0
                        for s in signals]

            total_positives = sum(outcomes)
            total_negatives = len(outcomes) - total_positives

            if total_positives < 10 or total_negatives < 10:
                return {
                    'detector_name': detector_name,
                    'error': 'imbalanced_data',
                    'tp_count': total_positives,
                    'fp_count': total_negatives,
                    'reason': 'Need at least 10 TP and 10 FP for reliable tuning'
                }

            # Try all unique scores as thresholds
            candidate_thresholds = sorted(set(scores))

            best_threshold = None
            best_tpr = 0
            best_fpr = 1.0

            for threshold in candidate_thresholds:
                tp = sum(1 for score, outcome in zip(scores, outcomes)
                         if score >= threshold and outcome == 1)
                fp = sum(1 for score, outcome in zip(scores, outcomes)
                         if score >= threshold and outcome == 0)
                tn = total_negatives - fp
                fn = total_positives - tp

                fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
                tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

                # Select if FPR within target and TPR better than current best
                if fpr <= target_fpr and tpr > best_tpr:
                    best_threshold = threshold
                    best_tpr = tpr
                    best_fpr = fpr

            # Fallback: most conservative threshold if none meet target
            if best_threshold is None:
                for threshold in reversed(candidate_thresholds):
                    tp = sum(1 for score, outcome in zip(scores, outcomes)
                             if score >= threshold and outcome == 1)
                    fp = sum(1 for score, outcome in zip(scores, outcomes)
                             if score >= threshold and outcome == 0)
                    tn = total_negatives - fp
                    fn = total_positives - tp

                    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
                    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

                    if threshold >= 0.10:  # Minimum safety bound
                        best_threshold = threshold
                        best_tpr = tpr
                        best_fpr = fpr
                        break

            if best_threshold is None:
                return {
                    'detector_name': detector_name,
                    'error': 'no_valid_threshold',
                    'reason': 'Could not find threshold meeting safety bounds'
                }

            # Confidence based on sample size
            if len(signals) >= 100:
                confidence = 'high'
            elif len(signals) >= 50:
                confidence = 'medium'
            else:
                confidence = 'low'

            # Get current threshold
            current_threshold = self._get_current_detector_threshold(conn, detector_name)

            # Apply gradual adjustment limit (max ±0.10 change)
            max_change = 0.10
            if abs(best_threshold - current_threshold) > max_change:
                if best_threshold > current_threshold:
                    best_threshold = current_threshold + max_change
                else:
                    best_threshold = current_threshold - max_change
                reason_suffix = ' (gradual adjustment, limited to ±0.10)'
            else:
                reason_suffix = ''

            return {
                'detector_name': detector_name,
                'current_threshold': current_threshold,
                'recommended_threshold': round(best_threshold, 3),
                'target_fpr': target_fpr,
                'achieved_fpr': round(best_fpr, 3),
                'achieved_tpr': round(best_tpr, 3),
                'sample_size': len(signals),
                'tp_count': total_positives,
                'fp_count': total_negatives,
                'confidence': confidence,
                'reason': f'Achieves {best_fpr:.1%} FPR (target {target_fpr:.1%}) with {best_tpr:.1%} TPR{reason_suffix}',
                'evaluated_at': datetime.now()
            }
        finally:
            conn.close()

    def _get_current_detector_threshold(self, conn: sqlite3.Connection, detector_name: str) -> float:
        """Get current threshold for detector from config or defaults."""
        # Check overrides table
        cursor = conn.execute("""
            SELECT threshold FROM detector_thresholds
            WHERE detector_name = ?
        """, (detector_name,))
        row = cursor.fetchone()

        if row:
            return row['threshold']

        # Fallback to hardcoded defaults (from fraud_detector.py FraudConfig)
        defaults = {
            'success_rate_anomaly': 0.5,
            'temporal_manipulation': 0.5,
            'unnatural_confidence_growth': 0.5
        }

        return defaults.get(detector_name, 0.5)

    # =========================================================================
    # CLASSIFICATION THRESHOLD TUNING
    # =========================================================================

    def calculate_optimal_classification_thresholds(
        self,
        target_fpr_suspicious: float = 0.10,
        target_fpr_likely: float = 0.05,
        target_fpr_confirmed: float = 0.01,
        min_samples: int = 50
    ) -> Dict[str, Any]:
        """
        Calculate optimal classification thresholds (suspicious/likely/confirmed).

        Analyzes fraud_score distribution vs review_outcome to find optimal cutoffs.

        Args:
            target_fpr_suspicious: Target FPR for 'suspicious' level (10%)
            target_fpr_likely: Target FPR for 'fraud_likely' level (5%)
            target_fpr_confirmed: Target FPR for 'fraud_confirmed' level (1%)
            min_samples: Minimum reviewed reports required

        Returns:
            Dict with recommendations for all three levels
        """
        conn = self._get_connection()
        try:
            # Get all reviewed reports
            cursor = conn.execute("""
                SELECT fraud_score, review_outcome
                FROM fraud_reports
                WHERE review_outcome IN ('true_positive', 'false_positive')
                ORDER BY fraud_score ASC
            """)

            reports = cursor.fetchall()

            if len(reports) < min_samples:
                return {
                    'error': 'insufficient_data',
                    'sample_size': len(reports),
                    'min_required': min_samples
                }

            scores = [r['fraud_score'] for r in reports]
            outcomes = [1 if r['review_outcome'] == 'true_positive' else 0
                        for r in reports]

            total_positives = sum(outcomes)
            total_negatives = len(outcomes) - total_positives

            if total_positives < 10 or total_negatives < 10:
                return {
                    'error': 'imbalanced_data',
                    'tp_count': total_positives,
                    'fp_count': total_negatives,
                    'reason': 'Need at least 10 TP and 10 FP for reliable tuning'
                }

            # Calculate thresholds for each level
            results = {}

            for level, target_fpr in [
                ('suspicious', target_fpr_suspicious),
                ('fraud_likely', target_fpr_likely),
                ('fraud_confirmed', target_fpr_confirmed)
            ]:
                threshold_result = self._find_threshold_for_fpr(
                    scores, outcomes, target_fpr
                )
                results[level] = threshold_result

            # Enforce ordering
            results = self._enforce_threshold_ordering(results)

            # Apply safety bounds
            results = self._apply_safety_bounds(results)

            # Get current thresholds
            current = self._get_current_classification_thresholds(conn)

            # Apply gradual adjustment
            for level in ['suspicious', 'fraud_likely', 'fraud_confirmed']:
                old = current[level]
                new = results[level]['threshold']
                if abs(new - old) > 0.10:
                    if new > old:
                        results[level]['threshold'] = round(old + 0.10, 3)
                    else:
                        results[level]['threshold'] = round(old - 0.10, 3)
                    results[level]['warning'] = 'Gradual adjustment applied (max ±0.10)'

            return {
                'suspicious': {
                    'current': current['suspicious'],
                    **results['suspicious']
                },
                'fraud_likely': {
                    'current': current['fraud_likely'],
                    **results['fraud_likely']
                },
                'fraud_confirmed': {
                    'current': current['fraud_confirmed'],
                    **results['fraud_confirmed']
                },
                'sample_size': len(reports),
                'evaluated_at': datetime.now()
            }
        finally:
            conn.close()

    def _find_threshold_for_fpr(
        self,
        scores: List[float],
        outcomes: List[int],
        target_fpr: float
    ) -> Dict[str, Any]:
        """Find threshold that achieves target FPR."""
        total_negatives = sum(1 for o in outcomes if o == 0)
        total_positives = sum(1 for o in outcomes if o == 1)

        candidate_thresholds = sorted(set(scores))

        for threshold in candidate_thresholds:
            fp = sum(1 for s, o in zip(scores, outcomes)
                     if s >= threshold and o == 0)
            tp = sum(1 for s, o in zip(scores, outcomes)
                     if s >= threshold and o == 1)

            fpr = fp / total_negatives
            tpr = tp / total_positives

            if fpr <= target_fpr:
                return {
                    'threshold': round(threshold, 3),
                    'fpr': round(fpr, 3),
                    'tpr': round(tpr, 3)
                }

        # No threshold meets target, use most conservative
        return {
            'threshold': round(max(candidate_thresholds), 3) if candidate_thresholds else 0.95,
            'fpr': 0.0,
            'tpr': 0.0,
            'warning': 'Could not meet target FPR, using maximum threshold'
        }

    def _enforce_threshold_ordering(self, results: Dict) -> Dict:
        """Ensure suspicious < likely < confirmed with minimum separation."""
        sus = results['suspicious']['threshold']
        likely = results['fraud_likely']['threshold']
        confirmed = results['fraud_confirmed']['threshold']

        # Minimum separation: 0.10
        if likely <= sus:
            likely = sus + 0.10
            results['fraud_likely']['warning'] = 'Adjusted to maintain ordering'
        if confirmed <= likely:
            confirmed = likely + 0.15
            results['fraud_confirmed']['warning'] = 'Adjusted to maintain ordering'

        results['fraud_likely']['threshold'] = round(likely, 3)
        results['fraud_confirmed']['threshold'] = round(confirmed, 3)

        return results

    def _apply_safety_bounds(self, results: Dict) -> Dict:
        """Enforce absolute min/max bounds."""
        bounds = {
            'suspicious': (0.10, 0.40),
            'fraud_likely': (0.30, 0.70),
            'fraud_confirmed': (0.60, 0.95)
        }

        for level, (min_val, max_val) in bounds.items():
            t = results[level]['threshold']
            old_t = t
            t = max(min_val, min(max_val, t))
            if t != old_t:
                results[level]['warning'] = f'Bounded to [{min_val}, {max_val}]'
            results[level]['threshold'] = round(t, 3)

        return results

    def _get_current_classification_thresholds(self, conn: sqlite3.Connection) -> Dict[str, float]:
        """Get current classification thresholds."""
        cursor = conn.execute("SELECT level, threshold FROM classification_thresholds")
        thresholds = {row['level']: row['threshold'] for row in cursor.fetchall()}

        # Fallback to defaults if not in DB
        defaults = {
            'suspicious': 0.20,
            'fraud_likely': 0.50,
            'fraud_confirmed': 0.80
        }

        return {level: thresholds.get(level, defaults[level])
                for level in ['suspicious', 'fraud_likely', 'fraud_confirmed']}

    # =========================================================================
    # RECOMMENDATION MANAGEMENT
    # =========================================================================

    def create_recommendation(
        self,
        recommendation: Dict[str, Any],
        threshold_type: str
    ) -> int:
        """
        Store threshold recommendation for CEO review.

        Args:
            recommendation: Output from calculate_optimal_*()
            threshold_type: 'detector' or 'classification'

        Returns:
            recommendation_id (or list of IDs for classification)
        """
        conn = self._get_connection()
        try:
            if threshold_type == 'detector':
                cursor = conn.execute("""
                    INSERT INTO threshold_recommendations
                    (detector_name, threshold_type, current_threshold,
                     recommended_threshold, target_fpr, achieved_fpr, achieved_tpr,
                     sample_size, tp_count, fp_count, confidence, reason)
                    VALUES (?, 'detector', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recommendation['detector_name'],
                    recommendation['current_threshold'],
                    recommendation['recommended_threshold'],
                    recommendation['target_fpr'],
                    recommendation['achieved_fpr'],
                    recommendation['achieved_tpr'],
                    recommendation['sample_size'],
                    recommendation['tp_count'],
                    recommendation['fp_count'],
                    recommendation['confidence'],
                    recommendation['reason']
                ))
                conn.commit()
                return cursor.lastrowid

            else:  # classification
                # Store one recommendation per level
                rec_ids = []
                for level in ['suspicious', 'fraud_likely', 'fraud_confirmed']:
                    level_data = recommendation[level]
                    cursor = conn.execute("""
                        INSERT INTO threshold_recommendations
                        (threshold_type, level, current_threshold,
                         recommended_threshold, target_fpr, achieved_fpr, achieved_tpr,
                         sample_size, confidence, reason)
                        VALUES ('classification', ?, ?, ?, ?, ?, ?, ?, 'medium', ?)
                    """, (
                        level,
                        level_data['current'],
                        level_data['threshold'],
                        level_data.get('target_fpr', 0.05),
                        level_data.get('fpr', 0),
                        level_data.get('tpr', 0),
                        recommendation['sample_size'],
                        level_data.get('warning', 'Recommended based on TP/FP analysis')
                    ))
                    rec_ids.append(cursor.lastrowid)
                conn.commit()
                return rec_ids

        finally:
            conn.close()

    def get_pending_recommendations(self) -> List[Dict]:
        """Get all recommendations pending CEO review."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM threshold_recommendations
                WHERE review_decision IS NULL
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def apply_threshold_update(
        self,
        recommendation_id: int,
        approved_by: str = 'ceo',
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a threshold recommendation.

        IMPORTANT: Only call after CEO approval.
        Records change in threshold_history for rollback.

        Args:
            recommendation_id: ID of approved recommendation
            approved_by: Who approved (default 'ceo')
            reason: Optional reason for applying

        Returns:
            {'success': bool, 'applied': {...}}
        """
        conn = self._get_connection()
        try:
            # Get recommendation
            cursor = conn.execute("""
                SELECT * FROM threshold_recommendations WHERE id = ?
            """, (recommendation_id,))
            rec = cursor.fetchone()

            if not rec:
                return {'success': False, 'error': 'Recommendation not found'}

            if rec['review_decision'] == 'rejected':
                return {'success': False, 'error': 'Recommendation was rejected'}

            # Apply based on type
            if rec['threshold_type'] == 'detector':
                # Update detector threshold
                conn.execute("""
                    INSERT OR REPLACE INTO detector_thresholds
                    (detector_name, threshold, updated_by, reason)
                    VALUES (?, ?, ?, ?)
                """, (
                    rec['detector_name'],
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason']
                ))

                # Record in history
                conn.execute("""
                    INSERT INTO threshold_history
                    (detector_name, threshold_type, old_threshold, new_threshold,
                     changed_by, reason)
                    VALUES (?, 'detector', ?, ?, ?, ?)
                """, (
                    rec['detector_name'],
                    rec['current_threshold'],
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason']
                ))

            else:  # classification
                # Update classification threshold
                conn.execute("""
                    UPDATE classification_thresholds
                    SET threshold = ?, updated_by = ?, reason = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE level = ?
                """, (
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason'],
                    rec['level']
                ))

                # Record in history
                conn.execute("""
                    INSERT INTO threshold_history
                    (threshold_type, level, old_threshold, new_threshold,
                     changed_by, reason)
                    VALUES ('classification', ?, ?, ?, ?, ?)
                """, (
                    rec['level'],
                    rec['current_threshold'],
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason']
                ))

            # Mark recommendation as approved and applied
            conn.execute("""
                UPDATE threshold_recommendations
                SET review_decision = 'approved',
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?,
                    applied_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (approved_by, recommendation_id))

            conn.commit()

            return {
                'success': True,
                'applied': {
                    'detector_name': rec['detector_name'],
                    'level': rec['level'],
                    'old_threshold': rec['current_threshold'],
                    'new_threshold': rec['recommended_threshold']
                }
            }
        finally:
            conn.close()

    def rollback_threshold(
        self,
        history_id: int,
        reverted_by: str = 'ceo'
    ) -> Dict[str, Any]:
        """
        Rollback a threshold change.

        Reverts to old_threshold from history record.
        """
        conn = self._get_connection()
        try:
            # Get history record
            cursor = conn.execute("""
                SELECT * FROM threshold_history WHERE id = ?
            """, (history_id,))
            hist = cursor.fetchone()

            if not hist:
                return {'success': False, 'error': 'History record not found'}

            if hist['reverted_at']:
                return {'success': False, 'error': 'Already reverted'}

            # Revert based on type
            if hist['threshold_type'] == 'detector':
                conn.execute("""
                    INSERT OR REPLACE INTO detector_thresholds
                    (detector_name, threshold, updated_by, reason)
                    VALUES (?, ?, ?, ?)
                """, (
                    hist['detector_name'],
                    hist['old_threshold'],
                    reverted_by,
                    f'Rollback of change on {hist["applied_at"]}'
                ))
            else:  # classification
                conn.execute("""
                    UPDATE classification_thresholds
                    SET threshold = ?, updated_by = ?, reason = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE level = ?
                """, (
                    hist['old_threshold'],
                    reverted_by,
                    f'Rollback of change on {hist["applied_at"]}',
                    hist['level']
                ))

            # Mark as reverted
            conn.execute("""
                UPDATE threshold_history
                SET reverted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (history_id,))

            conn.commit()

            return {
                'success': True,
                'reverted': {
                    'detector_name': hist['detector_name'],
                    'level': hist['level'],
                    'from': hist['new_threshold'],
                    'to': hist['old_threshold']
                }
            }
        finally:
            conn.close()

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def run_full_tuning_analysis(
        self,
        target_fpr: float = 0.05,
        min_samples_detector: int = 30,
        min_samples_classification: int = 50
    ) -> Dict[str, Any]:
        """
        Run complete tuning analysis for all detectors and classification.

        Generates recommendations, does NOT apply them.

        Returns:
            {
                'detectors': [...],
                'classification': {...},
                'recommendations_created': [...]
            }
        """
        results = {
            'detectors': [],
            'classification': None,
            'recommendations_created': []
        }

        # Tune each detector
        detector_names = [
            'success_rate_anomaly',
            'temporal_manipulation',
            'unnatural_confidence_growth'
        ]

        for detector in detector_names:
            result = self.calculate_optimal_threshold(
                detector, target_fpr, min_samples_detector
            )
            results['detectors'].append(result)

            # Create recommendation if sufficient data
            if 'error' not in result:
                rec_id = self.create_recommendation(result, 'detector')
                results['recommendations_created'].append(rec_id)

        # Tune classification thresholds
        class_result = self.calculate_optimal_classification_thresholds(
            target_fpr_suspicious=0.10,
            target_fpr_likely=0.05,
            target_fpr_confirmed=0.01,
            min_samples=min_samples_classification
        )

        results['classification'] = class_result

        if 'error' not in class_result:
            rec_ids = self.create_recommendation(class_result, 'classification')
            if isinstance(rec_ids, list):
                results['recommendations_created'].extend(rec_ids)
            else:
                results['recommendations_created'].append(rec_ids)

        return results


# CLI interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Adaptive Threshold Tuning")
    parser.add_argument("command", choices=[
        "analyze-detector",
        "analyze-classification",
        "full-analysis",
        "pending",
        "apply",
        "rollback"
    ])
    parser.add_argument("--detector", help="Detector name")
    parser.add_argument("--target-fpr", type=float, default=0.05)
    parser.add_argument("--rec-id", type=int, help="Recommendation ID")
    parser.add_argument("--history-id", type=int, help="History ID for rollback")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    tuner = ThresholdTuner()

    if args.command == "analyze-detector":
        if not args.detector:
            print("Error: --detector required")
            exit(1)
        result = tuner.calculate_optimal_threshold(args.detector, args.target_fpr)

    elif args.command == "analyze-classification":
        result = tuner.calculate_optimal_classification_thresholds()

    elif args.command == "full-analysis":
        result = tuner.run_full_tuning_analysis(args.target_fpr)

    elif args.command == "pending":
        result = tuner.get_pending_recommendations()

    elif args.command == "apply":
        if not args.rec_id:
            print("Error: --rec-id required")
            exit(1)
        result = tuner.apply_threshold_update(args.rec_id)

    elif args.command == "rollback":
        if not args.history_id:
            print("Error: --history-id required")
            exit(1)
        result = tuner.rollback_threshold(args.history_id)

    print(json.dumps(result, indent=2, default=str))
