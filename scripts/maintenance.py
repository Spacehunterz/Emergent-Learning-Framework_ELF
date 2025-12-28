#!/usr/bin/env python3
"""
ELF Database Maintenance System

Runs all maintenance tasks to keep database tables populated and healthy:
1. Fraud Detection - Analyze recently modified heuristics
2. Session Summaries - Summarize unsummarized sessions
3. Domain Baselines - Refresh stale baselines
4. Session Contexts - Cleanup old contexts
5. Postmortems - Auto-generate for failed workflows
6. CEO Reviews - Auto-create for issues needing attention

Usage:
    python maintenance.py              # Run all tasks
    python maintenance.py --fraud      # Fraud detection only
    python maintenance.py --sessions   # Session summaries only
    python maintenance.py --baselines  # Baseline refresh only
    python maintenance.py --postmortems # Postmortems only
    python maintenance.py --dry-run    # Show what would be done
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Paths
def get_base_path() -> Path:
    """Get ELF base path."""
    import os
    env_path = os.environ.get("ELF_BASE_PATH")
    if env_path:
        return Path(env_path)
    return Path.home() / ".claude" / "emergent-learning"

ELF_DIR = get_base_path()
DB_PATH = ELF_DIR / "memory" / "index.db"
PROJECTS_DIR = Path.home() / ".claude" / "projects"


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


class MaintenanceRunner:
    """Runs all ELF maintenance tasks."""

    def __init__(self, dry_run: bool = False, verbose: bool = True):
        self.dry_run = dry_run
        self.verbose = verbose
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "tasks": {}
        }

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def run_all(self) -> Dict[str, Any]:
        """Run all maintenance tasks."""
        self.log("=" * 50)
        self.log("ELF Database Maintenance")
        self.log("=" * 50)

        self.run_fraud_detection()
        self.run_session_summaries()
        self.run_baseline_refresh()
        self.run_context_cleanup()
        self.run_postmortem_generation()
        self.run_ceo_review_creation()

        self.log("\n" + "=" * 50)
        self.log("Maintenance Complete")
        self.log("=" * 50)

        return self.results

    # =========================================================================
    # 1. FRAUD DETECTION
    # =========================================================================

    def run_fraud_detection(self) -> Dict[str, Any]:
        """Run fraud detection on recently modified heuristics."""
        self.log("\n[1/6] Fraud Detection")
        self.log("-" * 30)

        conn = get_db()
        try:
            # Find heuristics modified in last 24 hours that haven't been checked
            cursor = conn.execute("""
                SELECT id, domain, rule, confidence,
                       times_validated, times_violated,
                       last_fraud_check
                FROM heuristics
                WHERE status = 'active'
                  AND (last_fraud_check IS NULL
                       OR last_fraud_check < datetime('now', '-24 hours'))
                  AND (times_validated + times_violated) >= 10
                ORDER BY confidence DESC
                LIMIT 50
            """)
            heuristics = cursor.fetchall()

            self.log(f"  Found {len(heuristics)} heuristics to check")

            if self.dry_run:
                self.results["tasks"]["fraud_detection"] = {
                    "status": "dry_run",
                    "heuristics_to_check": len(heuristics)
                }
                return self.results["tasks"]["fraud_detection"]

            # Run fraud detection
            checked = 0
            flagged = 0

            try:
                sys.path.insert(0, str(ELF_DIR / "query"))
                from fraud_detector import FraudDetector
                detector = FraudDetector()

                for h in heuristics:
                    try:
                        report = detector.create_fraud_report(h['id'])
                        checked += 1
                        if report.classification != 'clean':
                            flagged += 1
                            self.log(f"    [!] Heuristic {h['id']}: {report.classification} (score: {report.fraud_score:.2f})")
                    except Exception as e:
                        self.log(f"    [E] Heuristic {h['id']}: {e}")

                self.log(f"  Checked: {checked}, Flagged: {flagged}")

            except ImportError as e:
                self.log(f"  [SKIP] Fraud detector not available: {e}")
                checked = 0
                flagged = 0

            self.results["tasks"]["fraud_detection"] = {
                "status": "completed",
                "heuristics_checked": checked,
                "heuristics_flagged": flagged
            }

        finally:
            conn.close()

        return self.results["tasks"]["fraud_detection"]

    # =========================================================================
    # 2. SESSION SUMMARIES
    # =========================================================================

    def run_session_summaries(self) -> Dict[str, Any]:
        """Summarize unsummarized sessions."""
        self.log("\n[2/6] Session Summaries")
        self.log("-" * 30)

        conn = get_db()
        try:
            # Get already summarized sessions
            cursor = conn.execute("SELECT session_id FROM session_summaries WHERE is_stale = 0")
            summarized = set(row['session_id'] for row in cursor.fetchall())

            # Find unsummarized sessions (older than 1 hour)
            unsummarized = []
            cutoff_time = datetime.now() - timedelta(hours=1)

            for project_dir in PROJECTS_DIR.iterdir():
                if not project_dir.is_dir():
                    continue
                for jsonl_file in project_dir.glob("*.jsonl"):
                    if jsonl_file.name.startswith("agent-"):
                        continue
                    session_id = jsonl_file.stem
                    if session_id not in summarized:
                        mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                        if mtime < cutoff_time:
                            unsummarized.append(session_id)

            self.log(f"  Found {len(unsummarized)} unsummarized sessions")

            if self.dry_run:
                self.results["tasks"]["session_summaries"] = {
                    "status": "dry_run",
                    "sessions_to_summarize": len(unsummarized)
                }
                return self.results["tasks"]["session_summaries"]

            # Summarize up to 10 sessions
            summarized_count = 0
            try:
                sys.path.insert(0, str(ELF_DIR / "scripts"))
                from pathlib import Path as P
                summarize_script = ELF_DIR / "scripts" / "summarize-session.py"

                if summarize_script.exists():
                    import subprocess
                    for session_id in unsummarized[:10]:
                        try:
                            result = subprocess.run(
                                ["python", str(summarize_script), session_id],
                                capture_output=True, text=True, timeout=120
                            )
                            if result.returncode == 0:
                                summarized_count += 1
                                self.log(f"    [+] Summarized {session_id[:8]}...")
                            else:
                                self.log(f"    [E] Failed {session_id[:8]}...")
                        except Exception as e:
                            self.log(f"    [E] {session_id[:8]}: {e}")
                else:
                    self.log("  [SKIP] summarize-session.py not found")

            except Exception as e:
                self.log(f"  [SKIP] Summarization error: {e}")

            self.log(f"  Summarized: {summarized_count}/{min(len(unsummarized), 10)}")

            self.results["tasks"]["session_summaries"] = {
                "status": "completed",
                "sessions_found": len(unsummarized),
                "sessions_summarized": summarized_count
            }

        finally:
            conn.close()

        return self.results["tasks"]["session_summaries"]

    # =========================================================================
    # 3. DOMAIN BASELINE REFRESH
    # =========================================================================

    def run_baseline_refresh(self) -> Dict[str, Any]:
        """Refresh stale domain baselines."""
        self.log("\n[3/6] Domain Baselines")
        self.log("-" * 30)

        conn = get_db()
        try:
            # Check domains needing refresh (older than 7 days)
            cursor = conn.execute("""
                SELECT DISTINCT h.domain,
                       db.last_updated,
                       COUNT(*) as heuristic_count
                FROM heuristics h
                LEFT JOIN domain_baselines db ON h.domain = db.domain
                WHERE h.status = 'active'
                GROUP BY h.domain
                HAVING db.last_updated IS NULL
                   OR db.last_updated < datetime('now', '-7 days')
            """)
            domains = cursor.fetchall()

            self.log(f"  Found {len(domains)} domains needing refresh")

            if self.dry_run:
                self.results["tasks"]["baseline_refresh"] = {
                    "status": "dry_run",
                    "domains_to_refresh": len(domains)
                }
                return self.results["tasks"]["baseline_refresh"]

            refreshed = 0
            try:
                sys.path.insert(0, str(ELF_DIR / "query"))
                from fraud_detector import FraudDetector
                detector = FraudDetector()

                for d in domains:
                    try:
                        result = detector.update_domain_baseline(d['domain'], triggered_by='maintenance')
                        if "error" not in result:
                            refreshed += 1
                            self.log(f"    [+] {d['domain']}: avg={result['avg_success_rate']:.2f}")
                    except Exception as e:
                        self.log(f"    [E] {d['domain']}: {e}")

            except ImportError as e:
                self.log(f"  [SKIP] Fraud detector not available: {e}")

            self.log(f"  Refreshed: {refreshed}/{len(domains)}")

            self.results["tasks"]["baseline_refresh"] = {
                "status": "completed",
                "domains_found": len(domains),
                "domains_refreshed": refreshed
            }

        finally:
            conn.close()

        return self.results["tasks"]["baseline_refresh"]

    # =========================================================================
    # 4. SESSION CONTEXT CLEANUP
    # =========================================================================

    def run_context_cleanup(self) -> Dict[str, Any]:
        """Cleanup old session contexts."""
        self.log("\n[4/6] Context Cleanup")
        self.log("-" * 30)

        conn = get_db()
        try:
            # Count old contexts
            cursor = conn.execute("""
                SELECT COUNT(*) as count
                FROM session_contexts
                WHERE created_at < datetime('now', '-7 days')
            """)
            old_count = cursor.fetchone()['count']

            self.log(f"  Found {old_count} old context records")

            if self.dry_run:
                self.results["tasks"]["context_cleanup"] = {
                    "status": "dry_run",
                    "contexts_to_delete": old_count
                }
                return self.results["tasks"]["context_cleanup"]

            # Delete old contexts
            conn.execute("""
                DELETE FROM session_contexts
                WHERE created_at < datetime('now', '-7 days')
            """)
            conn.commit()

            self.log(f"  Deleted: {old_count} old contexts")

            self.results["tasks"]["context_cleanup"] = {
                "status": "completed",
                "contexts_deleted": old_count
            }

        except sqlite3.OperationalError:
            self.log("  [SKIP] session_contexts table not found")
            self.results["tasks"]["context_cleanup"] = {
                "status": "skipped",
                "reason": "table_not_found"
            }

        finally:
            conn.close()

        return self.results["tasks"]["context_cleanup"]

    # =========================================================================
    # 5. POSTMORTEM GENERATION
    # =========================================================================

    def run_postmortem_generation(self) -> Dict[str, Any]:
        """Auto-generate postmortems for failed/completed workflows."""
        self.log("\n[5/6] Postmortem Generation")
        self.log("-" * 30)

        conn = get_db()
        try:
            # Find completed workflows without postmortems
            cursor = conn.execute("""
                SELECT wr.id, wr.workflow_id, wr.status, wr.started_at, wr.completed_at,
                       w.name as workflow_name
                FROM workflow_runs wr
                JOIN workflows w ON wr.workflow_id = w.id
                LEFT JOIN postmortems pm ON pm.title LIKE '%' || wr.id || '%'
                WHERE wr.status IN ('completed', 'failed', 'error')
                  AND wr.completed_at > datetime('now', '-7 days')
                  AND pm.id IS NULL
                LIMIT 10
            """)
            workflows = cursor.fetchall()

            self.log(f"  Found {len(workflows)} workflows needing postmortems")

            if self.dry_run:
                self.results["tasks"]["postmortem_generation"] = {
                    "status": "dry_run",
                    "workflows_to_process": len(workflows)
                }
                return self.results["tasks"]["postmortem_generation"]

            created = 0
            for wf in workflows:
                try:
                    # Get node execution summary
                    cursor = conn.execute("""
                        SELECT node_id, status, error_message, started_at, completed_at
                        FROM node_executions
                        WHERE run_id = ?
                        ORDER BY started_at
                    """, (wf['id'],))
                    nodes = cursor.fetchall()

                    # Create postmortem
                    failed_nodes = [n for n in nodes if n['status'] in ('failed', 'error')]
                    completed_nodes = [n for n in nodes if n['status'] == 'completed']

                    title = f"Workflow {wf['workflow_name']} Run {wf['id']}"
                    actual_outcome = wf['status']
                    went_well = f"Completed {len(completed_nodes)} nodes successfully"
                    went_wrong = f"Failed {len(failed_nodes)} nodes" if failed_nodes else "No failures"
                    lessons = "Auto-generated postmortem - review and add learnings"

                    # Check if table has columns
                    cursor.execute("PRAGMA table_info(postmortems)")
                    cols = [c[1] for c in cursor.fetchall()]

                    if 'title' in cols:
                        conn.execute("""
                            INSERT INTO postmortems (title, actual_outcome, went_well, went_wrong, lessons, domain, created_at)
                            VALUES (?, ?, ?, ?, ?, 'workflow', CURRENT_TIMESTAMP)
                        """, (title, actual_outcome, went_well, went_wrong, lessons))
                        conn.commit()
                        created += 1
                        self.log(f"    [+] Created postmortem for {wf['workflow_name']}")

                except Exception as e:
                    self.log(f"    [E] Workflow {wf['id']}: {e}")

            self.log(f"  Created: {created}/{len(workflows)}")

            self.results["tasks"]["postmortem_generation"] = {
                "status": "completed",
                "workflows_found": len(workflows),
                "postmortems_created": created
            }

        except sqlite3.OperationalError as e:
            self.log(f"  [SKIP] Table error: {e}")
            self.results["tasks"]["postmortem_generation"] = {
                "status": "skipped",
                "reason": str(e)
            }

        finally:
            conn.close()

        return self.results["tasks"]["postmortem_generation"]

    # =========================================================================
    # 6. CEO REVIEW CREATION
    # =========================================================================

    def run_ceo_review_creation(self) -> Dict[str, Any]:
        """Auto-create CEO reviews for issues needing attention."""
        self.log("\n[6/6] CEO Review Creation")
        self.log("-" * 30)

        conn = get_db()
        try:
            reviews_created = 0

            # Check for unacknowledged drift alerts
            cursor = conn.execute("""
                SELECT id, domain, drift_percentage, severity
                FROM baseline_drift_alerts
                WHERE acknowledged_at IS NULL
                  AND severity IN ('high', 'critical')
            """)
            drift_alerts = cursor.fetchall()

            # Check for high-score fraud reports
            cursor = conn.execute("""
                SELECT id, heuristic_id, fraud_score, classification
                FROM fraud_reports
                WHERE review_outcome IS NULL
                  AND classification IN ('fraud_likely', 'fraud_confirmed')
            """)
            fraud_reports = cursor.fetchall()

            # Check for violated invariants
            cursor = conn.execute("""
                SELECT id, statement, violation_count
                FROM invariants
                WHERE violation_count > 0
                  AND status = 'active'
            """)
            violations = cursor.fetchall()

            total_issues = len(drift_alerts) + len(fraud_reports) + len(violations)
            self.log(f"  Found {total_issues} issues needing review")
            self.log(f"    - Drift alerts: {len(drift_alerts)}")
            self.log(f"    - Fraud reports: {len(fraud_reports)}")
            self.log(f"    - Invariant violations: {len(violations)}")

            if self.dry_run:
                self.results["tasks"]["ceo_review_creation"] = {
                    "status": "dry_run",
                    "issues_found": total_issues
                }
                return self.results["tasks"]["ceo_review_creation"]

            # Create CEO reviews for each category
            for alert in drift_alerts[:5]:
                try:
                    title = f"[DRIFT] Domain {alert['domain']} baseline shifted {alert['drift_percentage']:+.1f}%"
                    context = f"Severity: {alert['severity']}"
                    recommendation = "Review domain heuristics for unusual patterns"

                    conn.execute("""
                        INSERT INTO ceo_reviews (title, context, recommendation, status, created_at)
                        VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                    """, (title, context, recommendation))
                    reviews_created += 1
                except Exception as e:
                    self.log(f"    [E] Drift alert {alert['id']}: {e}")

            for report in fraud_reports[:5]:
                try:
                    title = f"[FRAUD] Heuristic {report['heuristic_id']} flagged as {report['classification']}"
                    context = f"Score: {report['fraud_score']:.2f}"
                    recommendation = "Review heuristic for manipulation"

                    conn.execute("""
                        INSERT INTO ceo_reviews (title, context, recommendation, status, created_at)
                        VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                    """, (title, context, recommendation))
                    reviews_created += 1
                except Exception as e:
                    self.log(f"    [E] Fraud report {report['id']}: {e}")

            for inv in violations[:5]:
                try:
                    title = f"[VIOLATION] Invariant violated {inv['violation_count']}x"
                    context = inv['statement'][:200]
                    recommendation = "Review invariant or fix code causing violations"

                    conn.execute("""
                        INSERT INTO ceo_reviews (title, context, recommendation, status, created_at)
                        VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                    """, (title, context, recommendation))
                    reviews_created += 1
                except Exception as e:
                    self.log(f"    [E] Invariant {inv['id']}: {e}")

            conn.commit()
            self.log(f"  Created: {reviews_created} CEO reviews")

            self.results["tasks"]["ceo_review_creation"] = {
                "status": "completed",
                "issues_found": total_issues,
                "reviews_created": reviews_created
            }

        except sqlite3.OperationalError as e:
            self.log(f"  [SKIP] Table error: {e}")
            self.results["tasks"]["ceo_review_creation"] = {
                "status": "skipped",
                "reason": str(e)
            }

        finally:
            conn.close()

        return self.results["tasks"]["ceo_review_creation"]


def main():
    parser = argparse.ArgumentParser(description="ELF Database Maintenance")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--fraud", action="store_true", help="Run fraud detection only")
    parser.add_argument("--sessions", action="store_true", help="Run session summaries only")
    parser.add_argument("--baselines", action="store_true", help="Run baseline refresh only")
    parser.add_argument("--postmortems", action="store_true", help="Run postmortem generation only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")

    args = parser.parse_args()

    runner = MaintenanceRunner(dry_run=args.dry_run, verbose=not args.quiet)

    # Run specific task or all
    if args.fraud:
        runner.run_fraud_detection()
    elif args.sessions:
        runner.run_session_summaries()
    elif args.baselines:
        runner.run_baseline_refresh()
    elif args.postmortems:
        runner.run_postmortem_generation()
    else:
        runner.run_all()

    if args.json:
        print(json.dumps(runner.results, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
