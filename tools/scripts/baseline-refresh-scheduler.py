#!/usr/bin/env python3
"""
Baseline Refresh Scheduler
Windows-compatible periodic baseline recalculation

Usage:
    # Run once manually:
    python baseline-refresh-scheduler.py --run-once

    # Run in scheduler mode (checks every hour, executes based on schedule):
    python baseline-refresh-scheduler.py --daemon

    # Set up Windows Task Scheduler (generates command):
    python baseline-refresh-scheduler.py --setup-task-scheduler

For Windows Task Scheduler integration:
    1. Run with --setup-task-scheduler to get the command
    2. Open Task Scheduler (taskschd.msc)
    3. Create Basic Task -> Daily or Hourly
    4. Action: Start a program -> paste the generated command
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add query directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "query"))

from fraud_detector import FraudDetector


def run_scheduled_refresh():
    """
    Check schedule and run baseline refresh if needed.
    Called by scheduler daemon or Task Scheduler.
    """
    detector = FraudDetector()

    print(f"[{datetime.now().isoformat()}] Checking baseline refresh schedule...")

    # Get domains needing refresh
    domains_needing = detector.get_domains_needing_refresh()

    if not domains_needing:
        print("No domains need refresh at this time.")
        return

    print(f"Found {len(domains_needing)} domains needing refresh:")
    for domain in domains_needing:
        print(f"  - {domain['domain'] or 'ALL'}: {domain['days_since_refresh']:.1f} days since last refresh")

    # Run refresh for all domains
    print("\nExecuting baseline refresh...")
    results = detector.refresh_all_baselines(triggered_by='scheduled')

    # Print summary
    print(f"\nRefresh complete:")
    print(f"  Total domains: {results['total_domains']}")
    print(f"  Updated: {len(results['updated'])}")
    print(f"  Errors: {len(results['errors'])}")
    print(f"  Drift alerts: {len(results['drift_alerts'])}")

    if results['drift_alerts']:
        print("\n*** DRIFT ALERTS ***")
        for alert in results['drift_alerts']:
            print(f"  {alert['domain']}: {alert['drift_percentage']:+.1f}% " +
                  f"({alert['previous']:.2f} -> {alert['new']:.2f})")

    if results['errors']:
        print("\nErrors encountered:")
        for error in results['errors']:
            print(f"  {error}")

    # Log results to file
    log_file = Path.home() / ".claude" / "emergent-learning" / "logs" / "baseline-refresh.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n[{datetime.now().isoformat()}] Baseline Refresh\n")
        f.write(f"  Triggered by: scheduled\n")
        f.write(f"  Domains updated: {len(results['updated'])}\n")
        f.write(f"  Drift alerts: {len(results['drift_alerts'])}\n")
        if results['drift_alerts']:
            f.write("  Alerts:\n")
            for alert in results['drift_alerts']:
                f.write(f"    - {alert['domain']}: {alert['drift_percentage']:+.1f}%\n")
        f.write("\n")

    print(f"\nLog written to: {log_file}")

    # Show unacknowledged drift alerts
    unacked = detector.get_unacknowledged_drift_alerts()
    if unacked:
        print(f"\n*** {len(unacked)} UNACKNOWLEDGED DRIFT ALERTS ***")
        for alert in unacked:
            print(f"  [{alert['severity'].upper()}] {alert['domain']}: " +
                  f"{alert['drift_percentage']:+.1f}% drift ({alert['days_pending']:.0f} days pending)")
        print("\nRun 'python fraud_detector.py drift-alerts' to manage alerts.")


def daemon_mode(check_interval_minutes: int = 60):
    """
    Run as a daemon, checking schedule every N minutes.

    Note: On Windows, Task Scheduler is preferred. This is a fallback.
    """
    print(f"Starting baseline refresh daemon (checking every {check_interval_minutes} minutes)")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            run_scheduled_refresh()
            print(f"\nNext check in {check_interval_minutes} minutes...")
            time.sleep(check_interval_minutes * 60)
    except KeyboardInterrupt:
        print("\nDaemon stopped.")


def setup_task_scheduler():
    """
    Generate Windows Task Scheduler setup instructions and command.
    """
    script_path = Path(__file__).resolve()
    python_exe = sys.executable

    command = f'"{python_exe}" "{script_path}" --run-once'

    print("=== Windows Task Scheduler Setup ===\n")
    print("1. Open Task Scheduler:")
    print("   - Press Win+R, type: taskschd.msc, press Enter\n")
    print("2. Create a new task:")
    print("   - Action -> Create Basic Task")
    print("   - Name: 'ELF Baseline Refresh'")
    print("   - Description: 'Periodic recalculation of domain baselines for fraud detection'\n")
    print("3. Trigger:")
    print("   - Choose: Daily")
    print("   - Start: Tomorrow at 02:00 AM (or preferred time)")
    print("   - Recur every: 1 days (or customize interval)\n")
    print("4. Action:")
    print("   - Choose: Start a program")
    print("   - Program/script: (copy-paste below)\n")
    print(f"     {python_exe}\n")
    print("   - Add arguments: (copy-paste below)\n")
    print(f'     "{script_path}" --run-once\n')
    print("5. Finish and verify:")
    print("   - Right-click task -> Run to test")
    print("   - Check log file for results\n")
    print("=== Full Command (for reference) ===")
    print(command)
    print("\n=== Alternative: Run from Command Line ===")
    print("To run manually at any time:")
    print(f"  {command}")


def setup_schedule(interval_days: int = 30):
    """Initialize or update the baseline refresh schedule."""
    detector = FraudDetector()
    result = detector.schedule_baseline_refresh(interval_days=interval_days)

    print(f"Baseline refresh schedule configured:")
    print(f"  Domain: {result['domain']}")
    print(f"  Interval: {result['interval_days']} days")
    print(f"  Next refresh: {result['next_refresh']}")


def show_drift_alerts():
    """Display all unacknowledged drift alerts."""
    detector = FraudDetector()
    alerts = detector.get_unacknowledged_drift_alerts()

    if not alerts:
        print("No unacknowledged drift alerts.")
        return

    print(f"=== {len(alerts)} Unacknowledged Drift Alerts ===\n")
    for alert in alerts:
        print(f"Alert ID: {alert['id']}")
        print(f"  Domain: {alert['domain']}")
        print(f"  Severity: {alert['severity'].upper()}")
        print(f"  Drift: {alert['drift_percentage']:+.1f}%")
        print(f"  Previous baseline: {alert['previous_baseline']:.4f}")
        print(f"  New baseline: {alert['new_baseline']:.4f}")
        print(f"  Alerted: {alert['days_pending']:.0f} days ago")
        print()


def acknowledge_alert(alert_id: int, user: str, notes: str = None):
    """Acknowledge a drift alert."""
    detector = FraudDetector()
    detector.acknowledge_drift_alert(alert_id, user, notes)
    print(f"Alert {alert_id} acknowledged by {user}.")


def main():
    parser = argparse.ArgumentParser(
        description="Baseline Refresh Scheduler for ELF Fraud Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run baseline refresh once and exit (for Task Scheduler)'
    )

    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon, checking schedule periodically'
    )

    parser.add_argument(
        '--daemon-interval',
        type=int,
        default=60,
        help='Minutes between daemon checks (default: 60)'
    )

    parser.add_argument(
        '--setup-task-scheduler',
        action='store_true',
        help='Show Windows Task Scheduler setup instructions'
    )

    parser.add_argument(
        '--setup-schedule',
        action='store_true',
        help='Initialize baseline refresh schedule'
    )

    parser.add_argument(
        '--interval-days',
        type=int,
        default=30,
        help='Days between refreshes (default: 30)'
    )

    parser.add_argument(
        '--drift-alerts',
        action='store_true',
        help='Show unacknowledged drift alerts'
    )

    parser.add_argument(
        '--ack-alert',
        type=int,
        help='Acknowledge alert by ID'
    )

    parser.add_argument(
        '--ack-user',
        default='user',
        help='Username for acknowledgment (default: user)'
    )

    parser.add_argument(
        '--ack-notes',
        help='Notes for alert acknowledgment'
    )

    args = parser.parse_args()

    # Execute based on arguments
    if args.setup_task_scheduler:
        setup_task_scheduler()

    elif args.setup_schedule:
        setup_schedule(args.interval_days)

    elif args.drift_alerts:
        show_drift_alerts()

    elif args.ack_alert:
        acknowledge_alert(args.ack_alert, args.ack_user, args.ack_notes)

    elif args.run_once:
        run_scheduled_refresh()

    elif args.daemon:
        daemon_mode(args.daemon_interval)

    else:
        parser.print_help()
        print("\n=== Quick Start ===")
        print("1. Setup schedule:")
        print("     python baseline-refresh-scheduler.py --setup-schedule --interval-days 30")
        print("\n2. Setup Windows Task Scheduler:")
        print("     python baseline-refresh-scheduler.py --setup-task-scheduler")
        print("\n3. Or run once manually:")
        print("     python baseline-refresh-scheduler.py --run-once")


if __name__ == "__main__":
    main()
