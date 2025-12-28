#!/usr/bin/env python3
"""
Promote a project heuristic to the global knowledge base.

When a project-specific heuristic proves valuable (high confidence, multiple
validations), it can be promoted to global so all projects benefit from it.

Usage:
    python promote-heuristic.py --id 5
    python promote-heuristic.py --list-candidates
    python promote-heuristic.py --id 5 --justification "Proven across 3 projects"
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

# Add query module to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'query'))

try:
    from project import detect_project_context, ProjectContext
except ImportError:
    print("ERROR: Could not import project module", file=sys.stderr)
    sys.exit(1)


def get_project_heuristics(ctx: ProjectContext, min_confidence: float = 0.0) -> List[Tuple]:
    """Get all project heuristics, optionally filtered by confidence."""
    if not ctx.project_db_path or not ctx.project_db_path.exists():
        return []

    conn = sqlite3.connect(str(ctx.project_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, rule, explanation, domain, confidence, validation_count,
               promoted_to_global, created_at
        FROM heuristics
        WHERE confidence >= ?
        ORDER BY confidence DESC, validation_count DESC
    """, (min_confidence,))

    results = cursor.fetchall()
    conn.close()
    return results


def get_promotion_candidates(ctx: ProjectContext, min_confidence: float = 0.8) -> List[Tuple]:
    """Get heuristics that are candidates for promotion (high confidence, not yet promoted)."""
    if not ctx.project_db_path or not ctx.project_db_path.exists():
        return []

    conn = sqlite3.connect(str(ctx.project_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, rule, explanation, domain, confidence, validation_count, created_at
        FROM heuristics
        WHERE confidence >= ? AND promoted_to_global = 0
        ORDER BY confidence DESC, validation_count DESC
    """, (min_confidence,))

    results = cursor.fetchall()
    conn.close()
    return results


def get_heuristic_by_id(ctx: ProjectContext, heuristic_id: int) -> Optional[Tuple]:
    """Get a specific heuristic by ID."""
    if not ctx.project_db_path or not ctx.project_db_path.exists():
        return None

    conn = sqlite3.connect(str(ctx.project_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, rule, explanation, domain, confidence, validation_count,
               promoted_to_global, source, tags
        FROM heuristics
        WHERE id = ?
    """, (heuristic_id,))

    result = cursor.fetchone()
    conn.close()
    return result


def mark_as_promoted(ctx: ProjectContext, heuristic_id: int) -> bool:
    """Mark a project heuristic as promoted to global."""
    if not ctx.project_db_path or not ctx.project_db_path.exists():
        return False

    conn = sqlite3.connect(str(ctx.project_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE heuristics
        SET promoted_to_global = 1, promoted_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), heuristic_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def add_to_global(global_db_path: Path, rule: str, explanation: str, domain: str,
                  confidence: float, source: str, tags: str,
                  project_name: str, justification: str) -> int:
    """Add a heuristic to the global database."""
    conn = sqlite3.connect(str(global_db_path))
    cursor = conn.cursor()

    # Enhance the explanation with promotion context
    full_explanation = explanation
    if justification:
        full_explanation += f"\n\n[Promoted from {project_name}] {justification}"
    else:
        full_explanation += f"\n\n[Promoted from {project_name}]"

    # Global schema uses source_type, not source
    source_type = f"promoted:{source}" if source else "promoted:observation"

    cursor.execute("""
        INSERT INTO heuristics (domain, rule, explanation, source_type, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (domain or "general", rule, full_explanation, source_type, confidence))

    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def promote_heuristic(ctx: ProjectContext, heuristic_id: int,
                      justification: Optional[str] = None) -> bool:
    """Promote a project heuristic to global."""
    # Get the heuristic
    heuristic = get_heuristic_by_id(ctx, heuristic_id)
    if not heuristic:
        print(f"ERROR: Heuristic #{heuristic_id} not found", file=sys.stderr)
        return False

    h_id, rule, explanation, domain, confidence, validation_count, promoted, source, tags = heuristic

    if promoted:
        print(f"WARNING: Heuristic #{heuristic_id} has already been promoted", file=sys.stderr)
        return False

    # Add to global
    global_id = add_to_global(
        ctx.global_db_path,
        rule=rule,
        explanation=explanation or "",
        domain=domain or "",
        confidence=confidence,
        source=source or "observation",
        tags=tags or "",
        project_name=ctx.project_name or "unknown",
        justification=justification or ""
    )

    # Mark as promoted in project DB
    mark_as_promoted(ctx, heuristic_id)

    print(f"[OK] Promoted heuristic #{heuristic_id} to global (new ID: #{global_id})")
    print(f"    Rule: {rule[:60]}...")
    print(f"    Domain: {domain or 'general'}")
    print(f"    Confidence: {confidence:.2f}")

    return True


def list_candidates(ctx: ProjectContext, min_confidence: float = 0.8):
    """List heuristics that are candidates for promotion."""
    candidates = get_promotion_candidates(ctx, min_confidence)

    if not candidates:
        print(f"No promotion candidates found (min confidence: {min_confidence})")
        print("Heuristics need confidence >= 0.8 to be promoted.")
        return

    print(f"## Promotion Candidates (confidence >= {min_confidence})")
    print()

    for h_id, rule, explanation, domain, confidence, validations, created in candidates:
        print(f"#{h_id}: {rule[:70]}")
        print(f"    Domain: {domain or 'general'} | Confidence: {confidence:.2f} | Validations: {validations}")
        if explanation:
            print(f"    {explanation[:80]}...")
        print()

    print(f"To promote: python promote-heuristic.py --id <ID>")


def list_all(ctx: ProjectContext):
    """List all project heuristics with promotion status."""
    heuristics = get_project_heuristics(ctx)

    if not heuristics:
        print("No project heuristics found.")
        return

    print(f"## All Project Heuristics ({ctx.project_name})")
    print()

    for h_id, rule, explanation, domain, confidence, validations, promoted, created in heuristics:
        status = "[PROMOTED]" if promoted else ""
        print(f"#{h_id}: {rule[:60]} {status}")
        print(f"    Domain: {domain or 'general'} | Confidence: {confidence:.2f} | Validations: {validations}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Promote project heuristics to global knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List candidates for promotion (confidence >= 0.8)
  python promote-heuristic.py --list-candidates

  # List all project heuristics
  python promote-heuristic.py --list-all

  # Promote a specific heuristic
  python promote-heuristic.py --id 5

  # Promote with justification
  python promote-heuristic.py --id 5 --justification "Validated in 3 different projects"
        """
    )

    parser.add_argument('--id', type=int, help='ID of the heuristic to promote')
    parser.add_argument('--list-candidates', action='store_true',
                       help='List heuristics that are candidates for promotion')
    parser.add_argument('--list-all', action='store_true',
                       help='List all project heuristics with promotion status')
    parser.add_argument('--min-confidence', type=float, default=0.8,
                       help='Minimum confidence for promotion candidates (default: 0.8)')
    parser.add_argument('--justification', type=str,
                       help='Why this heuristic should be global (added to explanation)')

    args = parser.parse_args()

    # Detect project context
    ctx = detect_project_context()

    if not ctx.has_project_context():
        print("ERROR: Not in an ELF-initialized project (no .elf/ found)", file=sys.stderr)
        print("Run 'python init-project.py' first.", file=sys.stderr)
        return 1

    print(f"Project: {ctx.project_name}")
    print()

    if args.list_candidates:
        list_candidates(ctx, args.min_confidence)
        return 0

    if args.list_all:
        list_all(ctx)
        return 0

    if args.id:
        success = promote_heuristic(ctx, args.id, args.justification)
        return 0 if success else 1

    # Default: show candidates
    list_candidates(ctx, args.min_confidence)
    return 0


if __name__ == '__main__':
    sys.exit(main())
