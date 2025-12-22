"""
Queries Router - Building queries and natural language interface.
"""

import re
from typing import Optional

from fastapi import APIRouter

from models import QueryRequest
from utils import get_db, dict_from_row, escape_like

router = APIRouter(prefix="/api", tags=["queries"])


@router.get("/queries")
async def get_queries(
    limit: int = 50,
    since: Optional[str] = None,
    domain: Optional[str] = None,
    query_type: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "recent"
):
    """Get building queries with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, query_type, session_id, agent_id, domain, tags,
                   limit_requested, max_tokens_requested, results_returned,
                   tokens_approximated, duration_ms, status, error_message,
                   error_code, golden_rules_returned, heuristics_count,
                   learnings_count, experiments_count, ceo_reviews_count,
                   query_summary, created_at, completed_at
            FROM building_queries
            WHERE 1=1
        """
        params = []

        if since:
            query += " AND created_at > ?"
            params.append(since)

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if query_type:
            query += " AND query_type = ?"
            params.append(query_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        # Apply sorting
        sort_map = {
            "recent": "created_at DESC",
            "oldest": "created_at ASC",
            "slowest": "duration_ms DESC"
        }
        query += f" ORDER BY {sort_map.get(sort_by, 'created_at DESC')}"

        query += " LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.post("/query")
async def natural_language_query(request: QueryRequest):
    """Natural language query interface."""
    query = request.query.lower()
    results = {
        "query": request.query,
        "heuristics": [],
        "learnings": [],
        "hotspots": [],
        "runs": [],
        "summary": ""
    }

    with get_db() as conn:
        cursor = conn.cursor()

        # Extract keywords
        keywords = re.findall(r'\b\w{3,}\b', query)
        # Escape each keyword individually before joining to prevent wildcard injection
        escaped_keywords = [escape_like(kw) for kw in keywords]
        keyword_pattern = "%".join(escaped_keywords) if escaped_keywords else "%"

        # Search heuristics
        cursor.execute("""
            SELECT id, domain, rule, confidence, times_validated
            FROM heuristics
            WHERE LOWER(rule) LIKE ? OR LOWER(domain) LIKE ? OR LOWER(explanation) LIKE ?
            ORDER BY confidence DESC
            LIMIT ?
        """, (f'%{keyword_pattern}%', f'%{keyword_pattern}%', f'%{keyword_pattern}%', request.limit))
        results["heuristics"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Search learnings
        cursor.execute("""
            SELECT id, type, title, summary, domain
            FROM learnings
            WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(domain) LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (f'%{keyword_pattern}%', f'%{keyword_pattern}%', f'%{keyword_pattern}%', request.limit))
        results["learnings"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Search hot spots
        cursor.execute("""
            SELECT location, SUM(strength) as strength, COUNT(*) as count
            FROM trails
            WHERE LOWER(location) LIKE ?
            GROUP BY location
            ORDER BY strength DESC
            LIMIT ?
        """, (f'%{keyword_pattern}%', request.limit))
        results["hotspots"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Generate summary
        h_count = len(results["heuristics"])
        l_count = len(results["learnings"])
        hs_count = len(results["hotspots"])

        results["summary"] = f"Found {h_count} heuristics, {l_count} learnings, and {hs_count} hot spots matching '{request.query}'"

    return results
