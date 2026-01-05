#!/usr/bin/env python3
"""
Validate or invalidate heuristics in the Emergent Learning Framework.

This script tracks when heuristics are confirmed (validated) or contradicted (violated),
updating the times_validated and times_violated counters in the database.

Usage:
  # Validate a heuristic (it worked as expected)
  python validate-heuristic.py --id 5 --validate
  python validate-heuristic.py --id 5 --validate --note "Confirmed during testing"

  # Violate a heuristic (it didn't work as expected)
  python validate-heuristic.py --id 5 --violate
  python validate-heuristic.py --id 5 --violate --note "Failed in edge case"

  # List heuristics with validation stats
  python validate-heuristic.py --list
  python validate-heuristic.py --list --domain testing

  # Recalculate confidence based on validation ratio
  python validate-heuristic.py --id 5 --recalc
"""

import sqlite3
import argparse
import sys
from pathlib import Path
from datetime import datetime
import logging

# Setup paths
script_dir = Path(__file__).parent
base_dir = script_dir.parent
logs_dir = base_dir / "logs"
logs_dir.mkdir(exist_ok=True)

# Database path
db_path = base_dir / "memory" / "index.db"

# Setup logging
log_file = logs_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [validate-heuristic] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


def get_connection():
    """Get database connection."""
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(str(db_path))


def validate_heuristic(heuristic_id: int, note: str = None):
    """Record a validation (heuristic worked as expected)."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check heuristic exists
    cursor.execute("SELECT id, rule, times_validated FROM heuristics WHERE id = ?", (heuristic_id,))
    row = cursor.fetchone()
    if not row:
        print(f"ERROR: Heuristic ID {heuristic_id} not found", file=sys.stderr)
        conn.close()
        return False

    # Update validation count
    cursor.execute("""
        UPDATE heuristics
        SET times_validated = times_validated + 1,
            updated_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), heuristic_id))

    conn.commit()
    new_count = row[2] + 1

    logger.info(f"Validated heuristic {heuristic_id}: {row[1][:50]}... (count: {new_count})")
    print(f"Validated heuristic {heuristic_id} (times_validated: {new_count})")

    if note:
        logger.info(f"Validation note: {note}")
        print(f"Note: {note}")

    conn.close()
    return True


def violate_heuristic(heuristic_id: int, note: str = None):
    """Record a violation (heuristic didn't work as expected)."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check heuristic exists
    cursor.execute("SELECT id, rule, times_violated FROM heuristics WHERE id = ?", (heuristic_id,))
    row = cursor.fetchone()
    if not row:
        print(f"ERROR: Heuristic ID {heuristic_id} not found", file=sys.stderr)
        conn.close()
        return False

    # Update violation count
    cursor.execute("""
        UPDATE heuristics
        SET times_violated = times_violated + 1,
            updated_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), heuristic_id))

    conn.commit()
    new_count = row[2] + 1

    logger.info(f"Violated heuristic {heuristic_id}: {row[1][:50]}... (count: {new_count})")
    print(f"Violated heuristic {heuristic_id} (times_violated: {new_count})")

    if note:
        logger.info(f"Violation note: {note}")
        print(f"Note: {note}")

    conn.close()
    return True


def recalculate_confidence(heuristic_id: int):
    """Recalculate confidence based on validation/violation ratio."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, rule, confidence, times_validated, times_violated
        FROM heuristics WHERE id = ?
    """, (heuristic_id,))
    row = cursor.fetchone()

    if not row:
        print(f"ERROR: Heuristic ID {heuristic_id} not found", file=sys.stderr)
        conn.close()
        return False

    _, rule, old_confidence, validated, violated = row
    total = validated + violated

    if total == 0:
        print(f"No validations recorded yet for heuristic {heuristic_id}")
        conn.close()
        return False

    # Calculate new confidence: base confidence adjusted by validation ratio
    # Formula: new_confidence = base_confidence * (validated / total) + 0.1 * (validated / total)
    # This weights toward the validation ratio but maintains some of the original confidence
    validation_ratio = validated / total

    # Blend: 50% original confidence, 50% validation ratio, bounded [0.1, 0.95]
    new_confidence = (old_confidence * 0.5) + (validation_ratio * 0.5)
    new_confidence = max(0.1, min(0.95, new_confidence))

    cursor.execute("""
        UPDATE heuristics
        SET confidence = ?,
            updated_at = ?
        WHERE id = ?
    """, (round(new_confidence, 2), datetime.now().isoformat(), heuristic_id))

    conn.commit()

    logger.info(f"Recalculated confidence for heuristic {heuristic_id}: {old_confidence} -> {new_confidence:.2f}")
    print(f"Heuristic {heuristic_id}:")
    print(f"  Rule: {rule[:60]}...")
    print(f"  Validations: {validated}, Violations: {violated}")
    print(f"  Validation ratio: {validation_ratio:.2%}")
    print(f"  Confidence: {old_confidence} -> {new_confidence:.2f}")

    conn.close()
    return True


def list_heuristics(domain: str = None):
    """List heuristics with validation statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    if domain:
        cursor.execute("""
            SELECT id, domain, rule, confidence, times_validated, times_violated, is_golden
            FROM heuristics
            WHERE domain = ?
            ORDER BY times_validated + times_violated DESC, confidence DESC
        """, (domain,))
    else:
        cursor.execute("""
            SELECT id, domain, rule, confidence, times_validated, times_violated, is_golden
            FROM heuristics
            ORDER BY times_validated + times_violated DESC, confidence DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No heuristics found.")
        return

    print(f"\n{'ID':>4} {'Domain':<15} {'Conf':>5} {'Valid':>5} {'Viol':>5} {'Ratio':>7} {'Golden':>6} Rule")
    print("-" * 100)

    for row in rows:
        h_id, h_domain, rule, conf, validated, violated, is_golden = row
        total = validated + violated
        ratio = f"{validated/total:.0%}" if total > 0 else "N/A"
        golden = "Yes" if is_golden else ""
        rule_short = rule[:40] + "..." if len(rule) > 40 else rule

        print(f"{h_id:>4} {h_domain:<15} {conf:>5.2f} {validated:>5} {violated:>5} {ratio:>7} {golden:>6} {rule_short}")

    print(f"\nTotal: {len(rows)} heuristics")


def main():
    parser = argparse.ArgumentParser(
        description="Validate or invalidate heuristics in the Emergent Learning Framework"
    )
    parser.add_argument('--id', type=int, help='Heuristic ID to validate/violate')
    parser.add_argument('--validate', action='store_true', help='Record a validation (heuristic worked)')
    parser.add_argument('--violate', action='store_true', help='Record a violation (heuristic failed)')
    parser.add_argument('--recalc', action='store_true', help='Recalculate confidence based on validation ratio')
    parser.add_argument('--note', help='Optional note for the validation/violation')
    parser.add_argument('--list', action='store_true', help='List heuristics with validation stats')
    parser.add_argument('--domain', help='Filter by domain (for --list)')

    args = parser.parse_args()

    if args.list:
        list_heuristics(args.domain)
        return

    if not args.id:
        parser.print_help()
        print("\nError: --id is required for validation/violation operations", file=sys.stderr)
        sys.exit(1)

    if args.validate and args.violate:
        print("Error: Cannot both validate and violate in same operation", file=sys.stderr)
        sys.exit(1)

    if args.validate:
        success = validate_heuristic(args.id, args.note)
    elif args.violate:
        success = violate_heuristic(args.id, args.note)
    elif args.recalc:
        success = recalculate_confidence(args.id)
    else:
        parser.print_help()
        print("\nError: Specify --validate, --violate, or --recalc", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
