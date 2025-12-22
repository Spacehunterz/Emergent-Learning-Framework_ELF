"""
Plan-Postmortem query helpers for the ELF query system.

Since the plans and postmortems tables may not yet have ORM models,
this module provides raw SQL queries for integration.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def get_db_path() -> Path:
    """Get the ELF database path."""
    return Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"


def get_active_plans(domain: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get active plans, optionally filtered by domain.

    Returns list of plan dicts with: id, task_id, title, approach, risks, expected_outcome, domain, created_at
    """
    db_path = get_db_path()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if domain:
            cursor.execute("""
                SELECT id, task_id, title, description, approach, risks, expected_outcome, domain, created_at
                FROM plans
                WHERE status = 'active' AND domain = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (domain, limit))
        else:
            cursor.execute("""
                SELECT id, task_id, title, description, approach, risks, expected_outcome, domain, created_at
                FROM plans
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return []
    finally:
        conn.close()


def get_recent_postmortems(domain: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get recent postmortems with their linked plans.

    Returns list of postmortem dicts with plan info joined.
    """
    db_path = get_db_path()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if domain:
            cursor.execute("""
                SELECT pm.id, pm.title, pm.actual_outcome, pm.divergences,
                       pm.went_well, pm.went_wrong, pm.lessons, pm.domain, pm.created_at,
                       p.title as plan_title, p.expected_outcome as plan_expected
                FROM postmortems pm
                LEFT JOIN plans p ON pm.plan_id = p.id
                WHERE pm.domain = ?
                ORDER BY pm.created_at DESC
                LIMIT ?
            """, (domain, limit))
        else:
            cursor.execute("""
                SELECT pm.id, pm.title, pm.actual_outcome, pm.divergences,
                       pm.went_well, pm.went_wrong, pm.lessons, pm.domain, pm.created_at,
                       p.title as plan_title, p.expected_outcome as plan_expected
                FROM postmortems pm
                LEFT JOIN plans p ON pm.plan_id = p.id
                ORDER BY pm.created_at DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return []
    finally:
        conn.close()


def get_plan_postmortem_pairs(domain: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get completed plan-postmortem pairs for learning analysis.

    These are the high-value entries where we can compare intent vs outcome.
    """
    db_path = get_db_path()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        base_query = """
            SELECT
                p.id as plan_id, p.title as plan_title, p.approach, p.risks, p.expected_outcome,
                pm.id as postmortem_id, pm.title as postmortem_title,
                pm.actual_outcome, pm.divergences, pm.lessons,
                p.domain, pm.created_at
            FROM plans p
            INNER JOIN postmortems pm ON pm.plan_id = p.id
            WHERE p.status = 'completed'
        """

        if domain:
            cursor.execute(base_query + " AND p.domain = ? ORDER BY pm.created_at DESC LIMIT ?", (domain, limit))
        else:
            cursor.execute(base_query + " ORDER BY pm.created_at DESC LIMIT ?", (limit,))

        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def format_plans_for_context(plans: List[Dict], max_chars: int = 500) -> str:
    """Format plans for inclusion in query context output."""
    if not plans:
        return ""

    lines = ["## Active Plans\n"]
    for p in plans:
        lines.append(f"- **{p['title']}** (task: {p.get('task_id', 'N/A')})")
        if p.get('domain'):
            lines.append(f"  Domain: {p['domain']}")
        if p.get('approach'):
            approach = p['approach'][:100] + '...' if len(p['approach']) > 100 else p['approach']
            lines.append(f"  Approach: {approach}")
        if p.get('risks'):
            risks = p['risks'][:80] + '...' if len(p['risks']) > 80 else p['risks']
            lines.append(f"  Risks: {risks}")
        lines.append("")

    return '\n'.join(lines)


def format_postmortems_for_context(postmortems: List[Dict], max_chars: int = 500) -> str:
    """Format postmortems for inclusion in query context output."""
    if not postmortems:
        return ""

    lines = ["## Recent Postmortems\n"]
    for pm in postmortems:
        plan_ref = f" [Plan: {pm['plan_title']}]" if pm.get('plan_title') else ""
        lines.append(f"- **{pm['title']}**{plan_ref}")
        if pm.get('domain'):
            lines.append(f"  Domain: {pm['domain']}")
        if pm.get('actual_outcome'):
            outcome = pm['actual_outcome'][:80] + '...' if len(pm['actual_outcome']) > 80 else pm['actual_outcome']
            lines.append(f"  Outcome: {outcome}")
        if pm.get('lessons'):
            lessons = pm['lessons'][:100] + '...' if len(pm['lessons']) > 100 else pm['lessons']
            lines.append(f"  Lessons: {lessons}")
        if pm.get('divergences'):
            div = pm['divergences'][:80] + '...' if len(pm['divergences']) > 80 else pm['divergences']
            lines.append(f"  Divergences: {div}")
        lines.append("")

    return '\n'.join(lines)


def format_pairs_for_context(pairs: List[Dict]) -> str:
    """Format plan-postmortem pairs showing expectation vs reality."""
    if not pairs:
        return ""

    lines = ["## Plan vs Reality (Completed)\n"]
    for pair in pairs:
        lines.append(f"### {pair['plan_title']}")
        if pair.get('expected_outcome'):
            lines.append(f"**Expected:** {pair['expected_outcome'][:100]}...")
        if pair.get('actual_outcome'):
            lines.append(f"**Actual:** {pair['actual_outcome'][:100]}...")
        if pair.get('divergences'):
            lines.append(f"**Divergence:** {pair['divergences'][:100]}...")
        if pair.get('lessons'):
            lines.append(f"**Lesson:** {pair['lessons']}")
        lines.append("")

    return '\n'.join(lines)
