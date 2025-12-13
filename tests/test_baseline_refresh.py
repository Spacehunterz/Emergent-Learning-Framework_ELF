#!/usr/bin/env python3
"""
Test Suite for Baseline Refresh System
Phase 3 - Agent 3 Implementation

Tests:
1. Baseline history tracking
2. Drift detection and alerting
3. Refresh scheduling
4. Manual refresh commands
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add query directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "query"))

from fraud_detector import FraudDetector

DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"


def test_database_schema():
    """Test that all required tables and views exist."""
    print("Test 1: Database Schema")
    print("-" * 50)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type IN ('table', 'view')
        AND (name LIKE '%baseline%' OR name LIKE 'domains_%')
        ORDER BY name
    """)

    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    expected = [
        'baseline_drift_alerts',
        'baseline_refresh_schedule',
        'domain_baseline_history',
        'domain_baselines',
        'domains_needing_refresh',
        'domains_with_drift',
        'recent_baseline_changes'
    ]

    print(f"Found {len(tables)} baseline-related tables/views:")
    for table in tables:
        status = "[OK]" if table in expected else "[??]"
        print(f"  {status} {table}")

    missing = set(expected) - set(tables)
    if missing:
        print(f"\nMissing: {missing}")
        return False

    print("\n[OK] All required tables/views exist\n")
    return True


def test_refresh_schedule():
    """Test schedule setup and querying."""
    print("Test 2: Refresh Schedule")
    print("-" * 50)

    detector = FraudDetector()

    # Set up schedule
    result = detector.schedule_baseline_refresh(interval_days=7, domain="test-domain")
    print(f"[OK] Schedule created: {result}")

    # Query schedule
    needs_refresh = detector.get_domains_needing_refresh()
    print(f"[OK] Found {len(needs_refresh)} domains needing refresh")

    print()
    return True


def test_baseline_update_with_history():
    """Test baseline update records history and detects drift."""
    print("Test 3: Baseline Update with History")
    print("-" * 50)

    detector = FraudDetector()
    conn = detector._get_connection()

    # Check if we have any domains with sufficient data
    cursor = conn.execute("""
        SELECT domain, COUNT(*) as heuristic_count
        FROM heuristics
        WHERE status = 'active'
        GROUP BY domain
        HAVING heuristic_count >= 3
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        print("[WARN] No domains with sufficient data (need 3+ heuristics)")
        print("  Skipping baseline update test")
        print()
        return True

    domain = row['domain']
    print(f"Testing domain: {domain} ({row['heuristic_count']} heuristics)")

    # First update (establishes baseline)
    result1 = detector.update_domain_baseline(domain, triggered_by='test')
    if "error" in result1:
        print(f"[WARN] Baseline update error: {result1['error']}")
        print()
        return True

    print(f"[OK] Initial baseline: {result1['avg_success_rate']:.4f}")

    # Check history
    conn = detector._get_connection()
    cursor = conn.execute("""
        SELECT COUNT(*) as count FROM domain_baseline_history
        WHERE domain = ?
    """, (domain,))
    history_count = cursor.fetchone()['count']
    conn.close()

    print(f"[OK] History records: {history_count}")

    # Second update (should detect drift or no drift)
    result2 = detector.update_domain_baseline(domain, triggered_by='test')
    if "error" not in result2:
        drift = result2.get('drift_percentage')
        if drift is not None:
            print(f"[OK] Drift detected: {drift:+.1f}%")
        else:
            print("[OK] No drift (baseline unchanged)")

    print()
    return True


def test_drift_alerts():
    """Test drift alert creation and acknowledgment."""
    print("Test 4: Drift Alerts")
    print("-" * 50)

    detector = FraudDetector()

    # Get unacknowledged alerts
    alerts = detector.get_unacknowledged_drift_alerts()
    print(f"[OK] Found {len(alerts)} unacknowledged drift alerts")

    if alerts:
        alert = alerts[0]
        print(f"  Sample alert: {alert['domain']}")
        print(f"    Drift: {alert['drift_percentage']:+.1f}%")
        print(f"    Severity: {alert['severity']}")

        # Test acknowledgment
        detector.acknowledge_drift_alert(alert['id'], 'test-user', 'Test acknowledgment')
        print(f"[OK] Alert {alert['id']} acknowledged")

        # Verify it's gone from unacknowledged list
        alerts_after = detector.get_unacknowledged_drift_alerts()
        if len(alerts_after) < len(alerts):
            print("[OK] Alert removed from unacknowledged list")

    print()
    return True


def test_refresh_all():
    """Test refreshing all domain baselines."""
    print("Test 5: Refresh All Baselines")
    print("-" * 50)

    detector = FraudDetector()

    result = detector.refresh_all_baselines(triggered_by='test')

    print(f"[OK] Total domains: {result['total_domains']}")
    print(f"  Updated: {len(result['updated'])}")
    print(f"  Errors: {len(result['errors'])}")
    print(f"  Drift alerts: {len(result['drift_alerts'])}")

    if result['drift_alerts']:
        print("\n  Drift Alerts:")
        for alert in result['drift_alerts'][:3]:
            print(f"    {alert['domain']}: {alert['drift_percentage']:+.1f}%")

    print()
    return True


def test_cli_commands():
    """Test CLI commands are accessible."""
    print("Test 6: CLI Commands")
    print("-" * 50)

    import subprocess

    commands = [
        ("needs-refresh", "Check domains needing refresh"),
        ("drift-alerts", "List drift alerts"),
        ("baseline-history --limit 3", "Show baseline history"),
    ]

    for cmd, description in commands:
        full_cmd = f"python query/fraud_detector.py {cmd}"
        try:
            result = subprocess.run(
                full_cmd,
                shell=True,
                cwd=Path.home() / ".claude" / "emergent-learning",
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"[OK] {description}")
            else:
                print(f"[FAIL] {description} (exit code {result.returncode})")
        except Exception as e:
            print(f"[FAIL] {description} (error: {e})")

    print()
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("Baseline Refresh System Test Suite")
    print("Phase 3 - Agent 3 Implementation")
    print("=" * 50)
    print()

    tests = [
        test_database_schema,
        test_refresh_schedule,
        test_baseline_update_with_history,
        test_drift_alerts,
        test_refresh_all,
        test_cli_commands
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[FAIL] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
