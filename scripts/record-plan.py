#!/usr/bin/env python3
"""
Record a plan before starting a task.

Part of the plan-postmortem learning system:
  PLAN (before) -> EXECUTE -> POSTMORTEM (after) -> LEARNING

Usage:
    python record-plan.py --title "Refactor auth" --approach "Extract to module"
    python record-plan.py --title "Add API endpoint" --domain api --risks "Rate limiting"
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DB_PATH = BASE_DIR / "memory" / "index.db"


def generate_task_id(title: str) -> str:
    """Generate a unique task_id slug from title."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = slug[:40].strip('-')
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    return f"{slug}-{timestamp}"


def record_plan(
    title: str,
    description: str = "",
    approach: str = "",
    risks: str = "",
    expected_outcome: str = "",
    domain: str = ""
) -> dict:
    """
    Record a plan to the database.

    Returns: dict with plan_id and task_id
    """
    task_id = generate_task_id(title)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO plans (task_id, title, description, approach, risks, expected_outcome, domain)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task_id, title, description, approach, risks, expected_outcome, domain))

    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"plan_id": plan_id, "task_id": task_id}


def list_active_plans() -> list:
    """List all active plans."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, task_id, title, domain, created_at
        FROM plans
        WHERE status = 'active'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    plans = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return plans


def main():
    parser = argparse.ArgumentParser(
        description='Record a plan before starting a task',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python record-plan.py --title "Refactor authentication module"
  python record-plan.py --title "Add user API" --approach "REST endpoints" --domain api
  python record-plan.py --list  # Show active plans
"""
    )

    parser.add_argument('--title', type=str, help='Brief task title')
    parser.add_argument('--description', type=str, default='', help='What we are trying to accomplish')
    parser.add_argument('--approach', type=str, default='', help='How we plan to do it')
    parser.add_argument('--risks', type=str, default='', help='Identified risks/concerns')
    parser.add_argument('--expected', type=str, default='', help='What success looks like')
    parser.add_argument('--domain', type=str, default='', help='Domain category')
    parser.add_argument('--list', action='store_true', help='List active plans')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.list:
        plans = list_active_plans()
        if args.json:
            print(json.dumps(plans, indent=2))
        else:
            print("Active Plans:")
            print("-" * 60)
            for p in plans:
                print(f"  [{p['id']}] {p['title']}")
                print(f"      task_id: {p['task_id']}")
                print(f"      domain: {p['domain'] or '-'}")
                print(f"      created: {p['created_at']}")
                print()
        return 0

    if not args.title:
        parser.print_help()
        return 1

    result = record_plan(
        title=args.title,
        description=args.description,
        approach=args.approach,
        risks=args.risks,
        expected_outcome=args.expected,
        domain=args.domain
    )

    if args.json:
        print(json.dumps(result))
    else:
        print(f"Plan recorded!")
        print(f"  plan_id: {result['plan_id']}")
        print(f"  task_id: {result['task_id']}")
        print()
        print("When done, run postmortem:")
        print(f"  python record-postmortem.py --plan-id {result['plan_id']} --outcome \"What happened\"")

    return 0


if __name__ == "__main__":
    exit(main())
