#!/usr/bin/env python3
"""
Fraud Review Interface
Extends fraud_detector.py with human review capabilities.

Provides:
- Recording review outcomes (true_positive/false_positive)
- Retrieving detailed reports with signals
- CLI for reviewing pending fraud reports
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configuration
DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"


class FraudReviewer:
    """
    Human review interface for fraud detection system.

    Allows humans to confirm or reject fraud alerts, providing
    feedback to improve detection accuracy.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_pending_reports(self) -> List[Dict]:
        """Get fraud reports pending human review."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    fr.*,
                    h.domain,
                    h.rule,
                    h.confidence,
                    h.status,
                    h.times_validated,
                    h.times_violated,
                    COALESCE(h.times_contradicted, 0) as times_contradicted
                FROM fraud_reports fr
                JOIN heuristics h ON fr.heuristic_id = h.id
                WHERE fr.review_outcome IS NULL OR fr.review_outcome = 'pending'
                ORDER BY fr.fraud_score DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_report_with_signals(self, fraud_report_id: int) -> Optional[Dict]:
        """
        Get a fraud report with all its anomaly signals.

        Returns detailed fraud report including all detection signals.
        """
        conn = self._get_connection()
        try:
            # Get the main report
            cursor = conn.execute("""
                SELECT
                    fr.*,
                    h.domain,
                    h.rule,
                    h.confidence,
                    h.status,
                    h.times_validated,
                    h.times_violated,
                    COALESCE(h.times_contradicted, 0) as times_contradicted
                FROM fraud_reports fr
                JOIN heuristics h ON fr.heuristic_id = h.id
                WHERE fr.id = ?
            """, (fraud_report_id,))
            report = cursor.fetchone()

            if not report:
                return None

            # Get all anomaly signals for this report
            cursor = conn.execute("""
                SELECT * FROM anomaly_signals
                WHERE fraud_report_id = ?
                ORDER BY score DESC
            """, (fraud_report_id,))
            signals = cursor.fetchall()

            # Convert to dict and parse evidence JSON
            report_dict = dict(report)
            report_dict['signals'] = []

            for signal in signals:
                signal_dict = dict(signal)
                if signal_dict.get('evidence'):
                    try:
                        signal_dict['evidence'] = json.loads(signal_dict['evidence'])
                    except json.JSONDecodeError:
                        signal_dict['evidence'] = {}
                report_dict['signals'].append(signal_dict)

            return report_dict
        finally:
            conn.close()

    def record_review_outcome(self, fraud_report_id: int, outcome: str,
                             reviewed_by: str = 'human',
                             notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Record human review outcome for a fraud report.

        Args:
            fraud_report_id: ID of the fraud report being reviewed
            outcome: 'true_positive' (confirmed fraud) or 'false_positive' (not fraud)
            reviewed_by: Identifier for who reviewed (default: 'human')
            notes: Optional notes about the review decision

        Returns:
            Dict with review details and updated report
        """
        if outcome not in ('true_positive', 'false_positive'):
            raise ValueError(f"Invalid outcome: {outcome}. Must be 'true_positive' or 'false_positive'")

        conn = self._get_connection()
        try:
            # Get the fraud report
            cursor = conn.execute("""
                SELECT fr.*, h.domain, h.rule, h.confidence, h.status
                FROM fraud_reports fr
                JOIN heuristics h ON fr.heuristic_id = h.id
                WHERE fr.id = ?
            """, (fraud_report_id,))
            report = cursor.fetchone()

            if not report:
                raise ValueError(f"Fraud report {fraud_report_id} not found")

            # Update the fraud report
            conn.execute("""
                UPDATE fraud_reports SET
                    review_outcome = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?
                WHERE id = ?
            """, (outcome, reviewed_by, fraud_report_id))

            # Record the review as a response action
            response_params = {
                "outcome": outcome,
                "reviewed_by": reviewed_by,
                "notes": notes
            }

            conn.execute("""
                INSERT INTO fraud_responses
                (fraud_report_id, response_type, parameters, executed_by)
                VALUES (?, 'ceo_escalation', ?, ?)
            """, (fraud_report_id, json.dumps(response_params), reviewed_by))

            # If confirmed as true positive, quarantine the heuristic automatically
            if outcome == 'true_positive':
                conn.execute("""
                    UPDATE heuristics SET
                        fraud_flags = COALESCE(fraud_flags, 0) + 1,
                        status = 'quarantined',
                        is_golden = 0
                    WHERE id = ?
                """, (report['heuristic_id'],))

                # Record the quarantine action as a response
                conn.execute("""
                    INSERT INTO fraud_responses
                    (fraud_report_id, response_type, parameters, executed_by)
                    VALUES (?, 'quarantine', ?, ?)
                """, (fraud_report_id, json.dumps({
                    "heuristic_id": report['heuristic_id'],
                    "previous_status": report['status'],
                    "action": "auto_quarantine_on_true_positive"
                }), reviewed_by))

            conn.commit()

            return {
                "success": True,
                "fraud_report_id": fraud_report_id,
                "heuristic_id": report['heuristic_id'],
                "outcome": outcome,
                "reviewed_by": reviewed_by,
                "reviewed_at": datetime.now().isoformat(),
                "quarantined": outcome == 'true_positive',
                "heuristic_info": {
                    "domain": report['domain'],
                    "rule": report['rule'],
                    "confidence": report['confidence'],
                    "status": 'quarantined' if outcome == 'true_positive' else report['status']
                }
            }
        finally:
            conn.close()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fraud Review Interface")
    parser.add_argument("command", choices=[
        "list", "show", "confirm", "reject", "dismiss"
    ])
    parser.add_argument("--report-id", type=int, help="Fraud report ID")
    parser.add_argument("--notes", help="Review notes (optional)")
    parser.add_argument("--reviewed-by", default="human", help="Reviewer identifier")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    reviewer = FraudReviewer()

    if args.command == "list":
        # List all pending reports
        reports = reviewer.get_pending_reports()
        if args.json:
            print(json.dumps(reports, indent=2, default=str))
        else:
            if not reports:
                print("No pending fraud reports.")
            else:
                print(f"\n{'='*80}")
                print(f"PENDING FRAUD REPORTS ({len(reports)})")
                print(f"{'='*80}\n")

                for r in reports:
                    total_apps = r['times_validated'] + r['times_violated'] + r['times_contradicted']
                    success_rate = r['times_validated'] / total_apps if total_apps > 0 else 0

                    print(f"Report ID: {r['id']}")
                    print(f"  Heuristic: [{r['domain']}] {r['rule'][:60]}...")
                    print(f"  Classification: {r['classification'].upper()}")
                    print(f"  Fraud Score: {r['fraud_score']:.1%}")
                    print(f"  Success Rate: {success_rate:.1%} ({r['times_validated']}/{total_apps})")
                    print(f"  Signals: {r['signal_count']}")
                    print(f"  Detected: {r['created_at']}")
                    print()

    elif args.command == "show":
        if not args.report_id:
            print("Error: --report-id required for show command")
            exit(1)

        report = reviewer.get_report_with_signals(args.report_id)
        if not report:
            print(f"Error: Report {args.report_id} not found")
            exit(1)

        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            print(f"\n{'='*80}")
            print(f"FRAUD REPORT #{report['id']}")
            print(f"{'='*80}\n")

            print(f"Heuristic ID: {report['heuristic_id']}")
            print(f"Domain: {report['domain']}")
            print(f"Rule: {report['rule']}")
            print(f"Current Confidence: {report['confidence']:.2%}")
            print(f"Status: {report['status']}")
            print()

            total_apps = report['times_validated'] + report['times_violated'] + report['times_contradicted']
            success_rate = report['times_validated'] / total_apps if total_apps > 0 else 0

            print(f"Performance:")
            print(f"  Success Rate: {success_rate:.1%} ({report['times_validated']}/{total_apps})")
            print(f"  Validated: {report['times_validated']}")
            print(f"  Violated: {report['times_violated']}")
            print(f"  Contradicted: {report['times_contradicted']}")
            print()

            print(f"Fraud Detection:")
            print(f"  Classification: {report['classification'].upper()}")
            print(f"  Fraud Score: {report['fraud_score']:.1%}")
            print(f"  Likelihood Ratio: {report['likelihood_ratio']:.2f}")
            print(f"  Detected: {report['created_at']}")
            print()

            print(f"Anomaly Signals ({len(report['signals'])}):")
            for sig in report['signals']:
                print(f"\n  [{sig['detector_name']}] - {sig['severity'].upper()}")
                print(f"  Score: {sig['score']:.2%}")
                print(f"  Reason: {sig['reason']}")
                if sig.get('evidence'):
                    print(f"  Evidence:")
                    for key, val in sig['evidence'].items():
                        print(f"    {key}: {val}")

    elif args.command in ["confirm", "reject", "dismiss"]:
        if not args.report_id:
            print(f"Error: --report-id required for {args.command} command")
            exit(1)

        # Map command to outcome
        outcome_map = {
            "confirm": "true_positive",
            "reject": "false_positive",
            "dismiss": "false_positive"  # dismiss = not fraud
        }
        outcome = outcome_map[args.command]

        # Record the review
        result = reviewer.record_review_outcome(
            fraud_report_id=args.report_id,
            outcome=outcome,
            reviewed_by=args.reviewed_by,
            notes=args.notes
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n✓ Fraud report #{args.report_id} marked as: {outcome}")
            print(f"  Heuristic: [{result['heuristic_info']['domain']}] {result['heuristic_info']['rule'][:60]}...")
            print(f"  Reviewed by: {result['reviewed_by']}")
            print(f"  Reviewed at: {result['reviewed_at']}")
            if args.notes:
                print(f"  Notes: {args.notes}")
            print()
