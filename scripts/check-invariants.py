#!/usr/bin/env python3
"""
ELF Invariant Checker
Validates code invariants defined in the ELF database before commits.

Usage: check-invariants.py [--project <path>]
"""

import argparse
import sqlite3
import subprocess
import sys
import os
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass  # Python < 3.7


def main():
    parser = argparse.ArgumentParser(description='Check ELF invariants')
    parser.add_argument('--project', type=str, help='Project path')
    args = parser.parse_args()

    # Determine project path
    if args.project:
        project_path = Path(args.project).expanduser().resolve()
    else:
        project_path = Path.home() / '.claude' / 'emergent-learning'

    db_path = project_path / 'memory' / 'index.db'

    if not db_path.exists():
        print(f"⚠️  No database found at {db_path}")
        print("   Skipping invariant checks.")
        return 0

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, statement, validation_type, validation_code, severity
            FROM invariants
            WHERE status = 'active' AND validation_code IS NOT NULL
        ''')
        invariants = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"⚠️  Could not query invariants: {e}")
        return 0

    if not invariants:
        print("✅ No automated invariant checks defined.")
        return 0

    failed = False

    for inv_id, statement, validation_type, validation_code, severity in invariants:
        print(f"Checking: {statement}")

        if validation_type == 'command':
            try:
                result = subprocess.run(
                    validation_code,
                    shell=True,
                    cwd=str(project_path),
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"  ❌ FAILED (severity: {severity})")
                    if result.stderr:
                        print(f"     {result.stderr.strip()}")
                    if severity == 'error':
                        failed = True
                else:
                    print("  ✅ Passed")
            except Exception as e:
                print(f"  ⚠️  Error running check: {e}")

        elif validation_type == 'test':
            print("  ⏭️  Skipped (test-type, run via test suite)")

        else:
            print(f"  ⏭️  Skipped (unknown validation type: {validation_type})")

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
