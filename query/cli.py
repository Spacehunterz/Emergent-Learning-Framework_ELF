"""
Command-line interface for the Query System.
"""

import argparse
import sys

# Import core components with fallbacks
try:
    from query.core import QuerySystem
    from query.exceptions import (
        QuerySystemError, ValidationError, DatabaseError, TimeoutError
    )
    from query.formatters import format_output, generate_accountability_banner
    from query.setup import ensure_hooks_installed, ensure_full_setup
except ImportError:
    from core import QuerySystem
    from exceptions import (
        QuerySystemError, ValidationError, DatabaseError, TimeoutError
    )
    from formatters import format_output, generate_accountability_banner
    from setup import ensure_hooks_installed, ensure_full_setup

# MetaObserver is optional
META_OBSERVER_AVAILABLE = False
try:
    from meta_observer import MetaObserver
    META_OBSERVER_AVAILABLE = True
except ImportError:
    pass


def main():
    """Command-line interface for the query system."""
    # Auto-run full setup on first use
    ensure_full_setup()
    # Auto-install hooks on first query
    ensure_hooks_installed()

    parser = argparse.ArgumentParser(
        description="Emergent Learning Framework - Query System (v2.0 - 10/10 Robustness)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic queries
  python query.py --context --domain coordination
  python query.py --domain debugging --limit 5
  python query.py --tags error,fix --limit 10
  python query.py --recent 10
  python query.py --experiments
  python query.py --ceo-reviews
  python query.py --stats

  # Advanced usage
  python query.py --domain testing --format json --debug
  python query.py --recent 20 --timeout 60 --format csv
  python query.py --validate
  python query.py --tags performance,optimization --format json > results.json

Error Codes:
  QS000 - General query system error
  QS001 - Validation error (invalid input)
  QS002 - Database error (connection/query failed)
  QS003 - Timeout error (query took too long)
  QS004 - Configuration error (setup failed)
        """
    )

    # Basic arguments
    parser.add_argument('--base-path', type=str, help='Base path to emergent-learning directory')
    parser.add_argument('--context', action='store_true', help='Build full context for agents')
    parser.add_argument('--domain', type=str, help='Query by domain')
    parser.add_argument('--tags', type=str, help='Query by tags (comma-separated)')
    parser.add_argument('--recent', type=int, metavar='N', help='Get N recent learnings')
    parser.add_argument('--type', type=str, help='Filter recent learnings by type')
    parser.add_argument('--experiments', action='store_true', help='List active experiments')
    parser.add_argument('--ceo-reviews', action='store_true', help='List pending CEO reviews')
    parser.add_argument('--golden-rules', action='store_true', help='Display golden rules')
    parser.add_argument('--stats', action='store_true', help='Display knowledge base statistics')
    parser.add_argument('--violations', action='store_true', help='Show violation summary')
    parser.add_argument('--violation-days', type=int, default=7, help='Days to look back for violations (default: 7)')
    parser.add_argument('--accountability-banner', action='store_true', help='Show accountability banner')
    parser.add_argument('--decisions', action='store_true', help='List architecture decision records (ADRs)')
    parser.add_argument('--spikes', action='store_true', help='List spike reports (research knowledge)')
    parser.add_argument('--decision-status', type=str, default='accepted', help='Filter decisions by status (default: accepted)')
    parser.add_argument('--assumptions', action='store_true', help='List assumptions')
    parser.add_argument('--assumption-status', type=str, default='active', help='Filter assumptions by status: active, verified, challenged, invalidated (default: active)')
    parser.add_argument('--min-confidence', type=float, default=0.0, help='Minimum confidence for assumptions (default: 0.0)')
    parser.add_argument('--invariants', action='store_true', help='List invariants (what must always be true)')
    parser.add_argument('--invariant-status', type=str, default='active', help='Filter invariants by status: active, deprecated, violated (default: active)')
    parser.add_argument('--invariant-scope', type=str, help='Filter invariants by scope: codebase, module, function, runtime')
    parser.add_argument('--invariant-severity', type=str, help='Filter invariants by severity: error, warning, info')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of results (default: 10, max: 1000)')

    # Enhanced arguments
    parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--max-tokens', type=int, default=5000,
                       help='Max tokens for context building (default: 5000, max: 50000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Query timeout in seconds (default: 30)')
    parser.add_argument('--validate', action='store_true', help='Validate database integrity')
    parser.add_argument('--health-check', action='store_true',
                       help='Run system health check and display alerts (meta-observer)')

    args = parser.parse_args()

    # Initialize query system with error handling
    try:
        query_system = QuerySystem(base_path=args.base_path, debug=args.debug)
    except QuerySystemError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error during initialization: {e} [QS000]", file=sys.stderr)
        return 1

    # Execute query based on arguments
    result = None
    exit_code = 0

    try:
        if args.validate:
            # Validate database
            result = query_system.validate_database()
            if result['valid']:
                print("Database validation: PASSED")
            else:
                print("Database validation: FAILED")
                exit_code = 1
            print(format_output(result, args.format))
            return exit_code

        elif args.health_check:
            # Run system health check via meta-observer
            if not META_OBSERVER_AVAILABLE:
                print("ERROR: Meta-observer not available. Cannot run health check.", file=sys.stderr)
                return 1

            print("🏥 [94mSystem Health Check[0m")
            print("━" * 40)

            # Check alerts
            alerts = query_system._check_system_alerts()

            if not alerts:
                print("✓ No active alerts")
            else:
                for alert in alerts:
                    if isinstance(alert, dict):
                        if alert.get('mode') == 'bootstrap':
                            print(f"⏳ Bootstrap mode: {alert.get('message', 'Collecting baseline data')}")
                            samples = alert.get('samples', 0)
                            needed = alert.get('samples_needed', 30)
                            print(f"   Progress: {samples}/{needed} samples (~{(needed - samples) // 4} more queries needed)")
                        else:
                            alert_type = alert.get('type', alert.get('alert_type', 'unknown'))
                            severity = alert.get('severity', 'info')
                            icon = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}.get(severity, '⚪')
                            print(f"{icon} [{severity.upper()}] {alert_type}")
                            if alert.get('message'):
                                print(f"   {alert['message']}")

            # Show recent metrics
            print("\n📊 [94mRecent Metrics[0m")
            print("━" * 40)
            try:
                observer = MetaObserver(db_path=query_system.db_path)

                for metric in ['avg_confidence', 'validation_velocity', 'contradiction_rate']:
                    trend = observer.calculate_trend(metric, hours=168)  # 7 days
                    if trend.get('confidence') != 'low':
                        direction = trend.get('direction', 'stable')
                        arrow = {'increasing': '↑', 'decreasing': '↓', 'stable': '→'}.get(direction, '?')
                        spread = trend.get('time_spread_hours', 0)
                        print(f"  {metric}: {arrow} {direction} (confidence: {trend.get('confidence')}, {spread:.1f}h spread)")
                    elif trend.get('reason') == 'insufficient_time_spread':
                        spread = trend.get('time_spread_hours', 0)
                        required = trend.get('required_spread_hours', 0)
                        print(f"  {metric}: (need more time spread - {spread:.1f}h/{required:.1f}h)")
                    else:
                        print(f"  {metric}: (insufficient data - {trend.get('sample_count', 0)}/{trend.get('required', 10)} samples)")

                # Show active alerts from DB
                active_alerts = observer.get_active_alerts()
                if active_alerts:
                    print(f"\n⚠️  {len(active_alerts)} active alert(s) in database")
            except Exception as e:
                print(f"  (Could not retrieve metrics: {e})")

            return 0

        elif args.context:
            # Build full context
            task = "Agent task context generation"
            domain = args.domain
            tags = args.tags.split(',') if args.tags else None
            result = query_system.build_context(task, domain, tags, args.max_tokens, args.timeout)
            print(result)
            return exit_code

        elif args.golden_rules:
            result = query_system.get_golden_rules()
            print(result)
            return exit_code

        elif args.decisions:
            # Handle decisions query (must come before --domain check)
            result = query_system.get_decisions(args.domain, args.decision_status, args.limit, args.timeout)


        elif args.spikes:
            result = query_system.get_spike_reports(
                domain=args.domain,
                tags=args.tags.split(',') if args.tags else None,
                limit=args.limit,
                timeout=args.timeout
            )

        elif args.assumptions:
            # Handle assumptions query
            result = query_system.get_assumptions(
                domain=args.domain,
                status=args.assumption_status,
                min_confidence=args.min_confidence,
                limit=args.limit,
                timeout=args.timeout
            )
            # Also show challenged/invalidated if viewing all or specifically requested
            if args.assumption_status in ['challenged', 'invalidated']:
                pass  # Already filtering by that status
            elif not result:
                # If no active assumptions, show a summary
                challenged = query_system.get_challenged_assumptions(args.domain, args.limit, args.timeout)
                if challenged:
                    print("\n--- Challenged/Invalidated Assumptions ---\n")
                    result = challenged


        elif args.invariants:
            # Handle invariants query
            result = query_system.get_invariants(
                domain=args.domain,
                status=args.invariant_status,
                scope=args.invariant_scope,
                severity=args.invariant_severity,
                limit=args.limit,
                timeout=args.timeout
            )

        elif args.domain:
            result = query_system.query_by_domain(args.domain, args.limit, args.timeout)

        elif args.tags:
            tags = [t.strip() for t in args.tags.split(',')]
            result = query_system.query_by_tags(tags, args.limit, args.timeout)

        elif args.recent is not None:
            result = query_system.query_recent(args.type, args.recent, args.timeout)

        elif args.experiments:
            result = query_system.get_active_experiments(args.timeout)

        elif args.ceo_reviews:
            result = query_system.get_pending_ceo_reviews(args.timeout)

        elif args.stats:
            result = query_system.get_statistics(args.timeout)

        elif args.violations:
            result = query_system.get_violation_summary(args.violation_days, args.timeout)

        elif args.accountability_banner:
            # Generate accountability banner
            summary = query_system.get_violation_summary(7, args.timeout)
            print(generate_accountability_banner(summary))
            return exit_code

        else:
            parser.print_help()
            return exit_code

        # Output result
        if result is not None:
            print(format_output(result, args.format))

    except ValidationError as e:
        print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        exit_code = 1
    except TimeoutError as e:
        print(f"TIMEOUT ERROR: {e}", file=sys.stderr)
        exit_code = 3
    except DatabaseError as e:
        print(f"DATABASE ERROR: {e}", file=sys.stderr)
        exit_code = 2
    except QuerySystemError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        exit_code = 1
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e} [QS000]", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        exit_code = 1
    finally:
        # Clean up connections
        query_system.cleanup()

    return exit_code


if __name__ == '__main__':
    exit(main())
