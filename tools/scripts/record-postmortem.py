#!/usr/bin/env python3
"""
Record a postmortem after completing a task.

Part of the plan-postmortem learning system:
  PLAN (before) -> EXECUTE -> POSTMORTEM (after) -> LEARNING

The key insight: comparing plan vs. actual reveals higher-quality learnings.

Usage:
    python record-postmortem.py --plan-id 5 --outcome "Completed successfully"
    python record-postmortem.py --title "API refactor" --outcome "Failed" --went-wrong "Rate limits"
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DB_PATH = BASE_DIR / "memory" / "index.db"


def get_plan(plan_id: int) -> dict:
    """Fetch a plan by ID."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def complete_plan(plan_id: int):
    """Mark a plan as completed."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE plans
        SET status = 'completed', completed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), plan_id))

    conn.commit()
    conn.close()


def record_postmortem(
    title: str,
    actual_outcome: str,
    plan_id: int = None,
    divergences: str = "",
    went_well: str = "",
    went_wrong: str = "",
    lessons: str = "",
    domain: str = ""
) -> dict:
    """
    Record a postmortem to the database.

    If plan_id is provided, also marks the plan as completed.

    Returns: dict with postmortem_id and analysis
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Insert postmortem
    cursor.execute("""
        INSERT INTO postmortems (plan_id, title, actual_outcome, divergences, went_well, went_wrong, lessons, domain)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (plan_id, title, actual_outcome, divergences, went_well, went_wrong, lessons, domain))

    postmortem_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Mark plan as completed if linked
    if plan_id:
        complete_plan(plan_id)

    return {
        "postmortem_id": postmortem_id,
        "plan_id": plan_id,
        "linked_to_plan": plan_id is not None
    }


def analyze_divergence(plan: dict, outcome: str, divergences: str) -> dict:
    """
    Analyze divergence between plan and outcome.
    Returns structured analysis for learning extraction.
    """
    analysis = {
        "had_plan": True,
        "plan_title": plan["title"],
        "expected_outcome": plan.get("expected_outcome", ""),
        "actual_outcome": outcome,
        "identified_risks": plan.get("risks", ""),
        "divergences": divergences,
        "learning_opportunities": []
    }

    # Simple heuristic extraction hints
    if divergences:
        analysis["learning_opportunities"].append(
            f"Divergence detected: {divergences[:100]}..."
            if len(divergences) > 100 else f"Divergence detected: {divergences}"
        )

    if plan.get("risks") and "unexpected" in divergences.lower():
        analysis["learning_opportunities"].append(
            "Risk was identified but still caused issues - consider stronger mitigation"
        )

    return analysis


def list_recent_postmortems(limit: int = 10) -> list:
    """List recent postmortems with their linked plans."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pm.*, p.title as plan_title, p.expected_outcome
        FROM postmortems pm
        LEFT JOIN plans p ON pm.plan_id = p.id
        ORDER BY pm.created_at DESC
        LIMIT ?
    """, (limit,))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Record a postmortem after completing a task',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # With linked plan (recommended)
  python record-postmortem.py --plan-id 5 --outcome "Completed successfully"

  # Standalone postmortem
  python record-postmortem.py --title "Auth bug fix" --outcome "Fixed" --lessons "Check null first"

  # Full postmortem
  python record-postmortem.py --plan-id 3 \\
      --outcome "Partial success" \\
      --divergences "Took 2x longer than expected" \\
      --went-well "API design was clean" \\
      --went-wrong "Underestimated complexity" \\
      --lessons "Always spike complex integrations first"

  # List recent postmortems
  python record-postmortem.py --list
"""
    )

    parser.add_argument('--plan-id', type=int, help='Link to plan ID (from record-plan.py)')
    parser.add_argument('--title', type=str, help='Brief description (auto-filled if plan-id given)')
    parser.add_argument('--outcome', type=str, help='What actually happened')
    parser.add_argument('--divergences', type=str, default='', help='What differed from plan')
    parser.add_argument('--went-well', type=str, default='', help='What succeeded')
    parser.add_argument('--went-wrong', type=str, default='', help='What failed')
    parser.add_argument('--lessons', type=str, default='', help='Key takeaways')
    parser.add_argument('--domain', type=str, default='', help='Domain category')
    parser.add_argument('--list', action='store_true', help='List recent postmortems')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.list:
        postmortems = list_recent_postmortems()
        if args.json:
            print(json.dumps(postmortems, indent=2, default=str))
        else:
            print("Recent Postmortems:")
            print("-" * 70)
            for pm in postmortems:
                plan_info = f"[Plan: {pm['plan_title']}]" if pm.get('plan_title') else "[No plan]"
                print(f"  [{pm['id']}] {pm['title']} {plan_info}")
                print(f"      outcome: {(pm['actual_outcome'] or '-')[:50]}")
                if pm.get('lessons'):
                    print(f"      lessons: {pm['lessons'][:50]}...")
                print(f"      created: {pm['created_at']}")
                print()
        return 0

    # Validate input
    plan = None
    if args.plan_id:
        plan = get_plan(args.plan_id)
        if not plan:
            print(f"ERROR: Plan ID {args.plan_id} not found", file=sys.stderr)
            return 1

    title = args.title
    if not title and plan:
        title = f"Postmortem: {plan['title']}"
    if not title:
        print("ERROR: --title required (or use --plan-id to auto-fill)", file=sys.stderr)
        return 1

    if not args.outcome:
        print("ERROR: --outcome required", file=sys.stderr)
        return 1

    domain = args.domain or (plan.get('domain', '') if plan else '')

    result = record_postmortem(
        title=title,
        actual_outcome=args.outcome,
        plan_id=args.plan_id,
        divergences=args.divergences,
        went_well=args.went_well,
        went_wrong=args.went_wrong,
        lessons=args.lessons,
        domain=domain
    )

    # Add analysis if linked to plan
    if plan:
        result["analysis"] = analyze_divergence(plan, args.outcome, args.divergences)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Postmortem recorded!")
        print(f"  postmortem_id: {result['postmortem_id']}")
        if result['linked_to_plan']:
            print(f"  linked to plan: {args.plan_id} (now marked completed)")
        print()

        if plan and result.get("analysis", {}).get("learning_opportunities"):
            print("Learning opportunities identified:")
            for opp in result["analysis"]["learning_opportunities"]:
                print(f"  - {opp}")
            print()
            print("Consider recording heuristics:")
            print(f"  python record-heuristic.py --domain \"{domain}\" --rule \"...\" --source observation")

    return 0


if __name__ == "__main__":
    exit(main())
