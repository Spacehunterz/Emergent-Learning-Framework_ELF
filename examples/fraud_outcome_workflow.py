#!/usr/bin/env python3
"""
Example: Complete Fraud Detection and Outcome Tracking Workflow

This example demonstrates the full lifecycle:
1. Fraud detector creates reports
2. CEO reviews pending reports
3. CEO records decisions
4. System calculates detector accuracy
5. System identifies underperforming detectors

Run this to see the TP/FP tracking system in action.
"""

import sys
from pathlib import Path

# Add query directory to path
sys.path.insert(0, str(Path.home() / ".claude" / "emergent-learning" / "query"))

from fraud_detector import FraudDetector
from fraud_outcomes import FraudOutcomeTracker


def main():
    print("=" * 70)
    print("Fraud Detection and Outcome Tracking Workflow")
    print("=" * 70)

    detector = FraudDetector()
    tracker = FraudOutcomeTracker()

    # Step 1: Get pending reports (simulated - assumes some exist)
    print("\nStep 1: Review Pending Fraud Reports")
    print("-" * 70)

    pending = tracker.get_pending_reports(limit=5)

    if not pending:
        print("No pending reports. (Create some using fraud_detector.py first)")
        print("\nExample:")
        print("  python query/fraud_detector.py check --heuristic-id 1")
        return

    print(f"Found {len(pending)} pending reports:\n")

    for i, report in enumerate(pending[:3], 1):  # Show first 3
        print(f"{i}. Report #{report['report_id']}: {report['classification'].upper()}")
        print(f"   Domain: {report['domain']}")
        print(f"   Heuristic: {report['rule'][:60]}...")
        print(f"   Fraud Score: {report['fraud_score']:.2f}")
        print(f"   Priority: {report['priority_score']:.2f}")
        print(f"   Detectors: {report['detectors']}")
        print(f"   Severities: {report['severities']}")
        print()

    # Step 2: Record CEO decisions (example)
    print("\nStep 2: Record CEO Decisions")
    print("-" * 70)

    # In real usage, this would be interactive or from a UI
    # For this example, we'll simulate some decisions
    examples = [
        (pending[0]['report_id'], 'true_positive', 'Confirmed fraud pattern'),
        (pending[1]['report_id'] if len(pending) > 1 else None, 'false_positive', 'Normal behavior for domain'),
        (pending[2]['report_id'] if len(pending) > 2 else None, 'dismissed', 'Need more data'),
    ]

    for report_id, outcome, notes in examples:
        if report_id is None:
            continue

        print(f"\nRecording decision for report #{report_id}:")
        print(f"  Outcome: {outcome}")
        print(f"  Notes: {notes}")

        success = tracker.record_outcome(
            report_id=report_id,
            outcome=outcome,
            decided_by='ceo@example.com',
            notes=notes
        )

        if success:
            print("  ✓ Recorded successfully")
        else:
            print("  ✗ Failed to record")

    # Step 3: Get Detector Accuracy
    print("\n\nStep 3: Analyze Detector Performance")
    print("-" * 70)

    accuracies = tracker.get_detector_accuracy(days=30)

    if accuracies:
        print(f"\nDetector Accuracy (Last 30 Days):\n")

        for acc in accuracies:
            print(f"Detector: {acc.detector_name}")
            print(f"  Reports: {acc.total_reports}")
            print(f"  True Positives: {acc.true_positives}")
            print(f"  False Positives: {acc.false_positives}")
            print(f"  Pending: {acc.pending}")

            if acc.precision is not None:
                print(f"  Precision: {acc.precision:.1%}")
            else:
                print(f"  Precision: N/A (no decisions yet)")

            print(f"  Avg Anomaly Score: {acc.avg_anomaly_score:.2f}")
            print()
    else:
        print("No detector data available yet.")

    # Step 4: Check for Underperforming Detectors
    print("\nStep 4: Identify Underperforming Detectors")
    print("-" * 70)

    underperforming = tracker.identify_underperforming_detectors(
        min_reports=3,
        max_precision=0.7
    )

    if underperforming:
        print(f"\n⚠️  Found {len(underperforming)} underperforming detectors:\n")

        for d in underperforming:
            print(f"  {d['detector_name']}")
            print(f"    Precision: {d['precision']:.1%}")
            print(f"    TP: {d['true_positives']}, FP: {d['false_positives']}")
            print(f"    Recommendation: Increase threshold or review detection logic")
            print()
    else:
        print("\n✓ All detectors performing within acceptable range (≥70% precision)")

    # Step 5: Domain Accuracy
    print("\nStep 5: Domain-Level Accuracy")
    print("-" * 70)

    domain_accs = tracker.get_domain_accuracy(days=30)

    if domain_accs:
        print(f"\nFraud Detection Accuracy by Domain:\n")

        for acc in domain_accs[:5]:  # Top 5
            print(f"Domain: {acc.domain}")
            print(f"  Reports: {acc.total_reports}")
            print(f"  TP: {acc.true_positives}, FP: {acc.false_positives}")

            if acc.precision is not None:
                print(f"  Precision: {acc.precision:.1%}")
            else:
                print(f"  Precision: N/A")

            print(f"  Avg Fraud Score: {acc.avg_fraud_score:.2f}")
            print()
    else:
        print("No domain data available yet.")

    # Step 6: Performance Report
    print("\nStep 6: Generate Performance Report")
    print("-" * 70)

    report = tracker.generate_performance_report(days=30)

    print(f"\nTime Period: {report['time_period']}")
    print(f"\nOverall Metrics:")
    print(f"  Total Reports: {report['summary']['total_reports']}")
    print(f"  True Positives: {report['summary']['total_tp']}")
    print(f"  False Positives: {report['summary']['total_fp']}")
    print(f"  Pending Review: {report['summary']['pending']}")

    if report['summary']['overall_precision'] is not None:
        print(f"  Overall Precision: {report['summary']['overall_precision']:.1%}")
    else:
        print(f"  Overall Precision: N/A (no decisions yet)")

    print(f"\nDetectors Analyzed: {len(report['detectors'])}")
    print(f"Domains Analyzed: {len(report['domains'])}")

    if report['underperforming']:
        print(f"\n⚠️  Underperforming Detectors: {len(report['underperforming'])}")

    # Step 7: Classification Accuracy
    print("\n\nStep 7: Classification Threshold Alignment")
    print("-" * 70)

    classifications = tracker.get_classification_accuracy()

    if classifications:
        print("\nHow well do our fraud_score thresholds match human decisions?\n")

        for cls in classifications:
            print(f"{cls['classification'].upper()}:")
            print(f"  Total: {cls['total']}")
            print(f"  Confirmed: {cls['confirmed']}, Rejected: {cls['rejected']}")

            if cls['accuracy'] is not None:
                print(f"  Accuracy: {cls['accuracy']:.1%}")
            else:
                print(f"  Accuracy: N/A")

            print(f"  Score Range: {cls['min_score']:.2f} - {cls['max_score']:.2f}")
            print()

    print("\n" + "=" * 70)
    print("Workflow Complete")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
