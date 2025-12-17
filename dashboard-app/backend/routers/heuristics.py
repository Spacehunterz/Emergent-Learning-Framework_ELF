"""
Heuristics Router - CRUD, graph visualization, promote/demote.
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from models import HeuristicUpdate, ActionResult
from utils import get_db, dict_from_row

router = APIRouter(prefix="/api", tags=["heuristics"])

# ConnectionManager will be injected from main.py
manager = None


def set_manager(m):
    """Set the ConnectionManager for broadcasting updates."""
    global manager
    manager = m


@router.get("/heuristics")
async def get_heuristics(
    domain: Optional[str] = None,
    golden_only: bool = False,
    sort_by: str = "confidence",
    limit: int = 50,
    scope: str = "global"
):
    """Get heuristics with optional filtering. scope: 'global' or 'project'"""
    with get_db(scope) as conn:
        cursor = conn.cursor()

        # Different schemas for global vs project
        if scope == "project":
            # Project schema: uses validation_count, source (not source_type), no is_golden
            query = """
                SELECT id, domain, rule, explanation, confidence,
                       validation_count as times_validated, 0 as times_violated,
                       0 as is_golden, source as source_type, created_at,
                       created_at as updated_at
                FROM heuristics
                WHERE 1=1
            """
        else:
            # Global schema
            query = """
                SELECT id, domain, rule, explanation, confidence,
                       times_validated, times_violated, is_golden,
                       source_type, created_at, updated_at
                FROM heuristics
                WHERE 1=1
            """
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if golden_only and scope == "global":
            query += " AND is_golden = 1"

        # Use correct column name based on scope
        sort_map = {
            "confidence": "confidence DESC",
            "validated": "validation_count DESC" if scope == "project" else "times_validated DESC",
            "violated": "times_violated DESC",
            "recent": "created_at DESC"
        }
        query += f" ORDER BY {sort_map.get(sort_by, 'confidence DESC')}"
        query += " LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.get("/heuristics/{heuristic_id}")
async def get_heuristic(heuristic_id: int):
    """Get single heuristic with full details."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM heuristics WHERE id = ?
        """, (heuristic_id,))
        heuristic = dict_from_row(cursor.fetchone())

        if not heuristic:
            raise HTTPException(status_code=404, detail="Heuristic not found")

        # Get validation/violation history from metrics
        cursor.execute("""
            SELECT metric_type, timestamp, context
            FROM metrics
            WHERE tags LIKE ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (f"%heuristic_id:{heuristic_id}%",))
        heuristic["history"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Get related heuristics (same domain)
        cursor.execute("""
            SELECT id, rule, confidence
            FROM heuristics
            WHERE domain = ? AND id != ?
            ORDER BY confidence DESC
            LIMIT 5
        """, (heuristic["domain"], heuristic_id))
        heuristic["related"] = [dict_from_row(r) for r in cursor.fetchall()]

        return heuristic


@router.get("/heuristic-graph")
async def get_heuristic_graph():
    """Get heuristic graph data for force-directed visualization.

    Returns nodes (heuristics) and edges (relationships based on domain similarity
    and concept overlap).
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get all heuristics with their key properties
        cursor.execute("""
            SELECT id, domain, rule, explanation, confidence,
                   times_validated, times_violated, is_golden,
                   created_at
            FROM heuristics
            ORDER BY confidence DESC
        """)

        heuristics = [dict_from_row(r) for r in cursor.fetchall()]

        # Create nodes
        nodes = []
        for h in heuristics:
            nodes.append({
                "id": h["id"],
                "label": h["rule"][:50] + ("..." if len(h["rule"]) > 50 else ""),
                "fullText": h["rule"],
                "domain": h["domain"],
                "confidence": h["confidence"],
                "is_golden": bool(h["is_golden"]),
                "times_validated": h["times_validated"],
                "times_violated": h["times_violated"],
                "explanation": h["explanation"],
                "created_at": h["created_at"]
            })

        # Create edges based on:
        # 1. Same domain (strong connection)
        # 2. Keyword overlap (weaker connection)
        edges = []
        edge_id = 0

        # Group heuristics by domain for same-domain connections
        domain_map = defaultdict(list)
        for h in heuristics:
            domain_map[h["domain"]].append(h["id"])

        # Create edges for same domain
        for domain, ids in domain_map.items():
            for i, id1 in enumerate(ids):
                for id2 in ids[i+1:]:
                    edges.append({
                        "id": edge_id,
                        "source": id1,
                        "target": id2,
                        "strength": 1.0,
                        "type": "same_domain",
                        "label": domain
                    })
                    edge_id += 1

        # Create edges for keyword similarity (limit to avoid too many edges)
        # Extract keywords from rules
        def extract_keywords(text):
            """Extract significant words from rule text."""
            if not text:
                return set()
            # Remove common words and extract significant terms
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
            words = re.findall(r'\w+', text.lower())
            return {w for w in words if len(w) > 3 and w not in stopwords}

        # Build keyword map
        heuristic_keywords = {}
        for h in heuristics:
            keywords = extract_keywords(h["rule"])
            if h["explanation"]:
                keywords.update(extract_keywords(h["explanation"]))
            heuristic_keywords[h["id"]] = keywords

        # Find keyword-based connections (only strong overlaps)
        for i, h1 in enumerate(heuristics):
            for h2 in heuristics[i+1:]:
                # Skip if same domain (already connected)
                if h1["domain"] == h2["domain"]:
                    continue

                keywords1 = heuristic_keywords[h1["id"]]
                keywords2 = heuristic_keywords[h2["id"]]

                # Calculate overlap
                overlap = keywords1 & keywords2
                if len(overlap) >= 2:  # At least 2 common keywords
                    strength = len(overlap) / max(len(keywords1), len(keywords2))
                    if strength > 0.2:  # Only strong connections
                        edges.append({
                            "id": edge_id,
                            "source": h1["id"],
                            "target": h2["id"],
                            "strength": strength,
                            "type": "keyword_similarity",
                            "label": ", ".join(list(overlap)[:3])
                        })
                        edge_id += 1

        # Limit edges per node to avoid clutter (keep strongest connections)
        MAX_EDGES_PER_NODE = 10
        node_edge_counts = defaultdict(list)
        for edge in edges:
            node_edge_counts[edge["source"]].append(edge)
            node_edge_counts[edge["target"]].append(edge)

        # Keep only top edges per node
        edges_to_keep = set()
        for node_id, node_edges in node_edge_counts.items():
            # Sort by strength and keep top N
            sorted_edges = sorted(node_edges, key=lambda e: e["strength"], reverse=True)
            for edge in sorted_edges[:MAX_EDGES_PER_NODE]:
                edges_to_keep.add(edge["id"])

        filtered_edges = [e for e in edges if e["id"] in edges_to_keep]

        return {
            "nodes": nodes,
            "edges": filtered_edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(filtered_edges),
                "golden_rules": sum(1 for n in nodes if n["is_golden"]),
                "domains": len(domain_map)
            }
        }


@router.post("/heuristics/{heuristic_id}/promote")
async def promote_to_golden(heuristic_id: int) -> ActionResult:
    """Promote a heuristic to golden rule."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM heuristics WHERE id = ?", (heuristic_id,))
        heuristic = cursor.fetchone()

        if not heuristic:
            raise HTTPException(status_code=404, detail="Heuristic not found")

        if heuristic["is_golden"]:
            return ActionResult(success=False, message="Already a golden rule")

        cursor.execute("""
            UPDATE heuristics
            SET is_golden = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), heuristic_id))

        # Log the promotion
        cursor.execute("""
            INSERT INTO metrics (metric_type, metric_name, metric_value, context, timestamp)
            VALUES ('golden_rule_promotion', 'manual_promotion', ?, ?, ?)
        """, (heuristic_id, heuristic["rule"][:100], datetime.now().isoformat()))

        conn.commit()

        if manager:
            await manager.broadcast_update("heuristic_promoted", {
                "heuristic_id": heuristic_id,
                "rule": heuristic["rule"]
            })

        return ActionResult(success=True, message="Promoted to golden rule")


@router.post("/heuristics/{heuristic_id}/demote")
async def demote_from_golden(heuristic_id: int) -> ActionResult:
    """Demote a golden rule back to regular heuristic."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE heuristics
            SET is_golden = 0, updated_at = ?
            WHERE id = ? AND is_golden = 1
        """, (datetime.now().isoformat(), heuristic_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Heuristic not found or not a golden rule")

        conn.commit()

        if manager:
            await manager.broadcast_update("heuristic_demoted", {"heuristic_id": heuristic_id})

        return ActionResult(success=True, message="Demoted from golden rule")


@router.put("/heuristics/{heuristic_id}")
async def update_heuristic(heuristic_id: int, update: HeuristicUpdate) -> ActionResult:
    """Update a heuristic."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify heuristic exists
        cursor.execute("SELECT id FROM heuristics WHERE id = ?", (heuristic_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Heuristic not found")

        updates = []
        params = []

        if update.rule is not None:
            updates.append("rule = ?")
            params.append(update.rule)

        if update.explanation is not None:
            updates.append("explanation = ?")
            params.append(update.explanation)

        if update.domain is not None:
            updates.append("domain = ?")
            params.append(update.domain)

        if update.is_golden is not None:
            updates.append("is_golden = ?")
            params.append(1 if update.is_golden else 0)

        if not updates:
            return ActionResult(success=False, message="No updates provided")

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(heuristic_id)

        cursor.execute(f"""
            UPDATE heuristics
            SET {", ".join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()

        if manager:
            await manager.broadcast_update("heuristic_updated", {"heuristic_id": heuristic_id})

        return ActionResult(success=True, message="Heuristic updated")


@router.delete("/heuristics/{heuristic_id}")
async def delete_heuristic(heuristic_id: int) -> ActionResult:
    """Delete a heuristic."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM heuristics WHERE id = ?", (heuristic_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Heuristic not found")

        conn.commit()

        if manager:
            await manager.broadcast_update("heuristic_deleted", {"heuristic_id": heuristic_id})

        return ActionResult(success=True, message="Heuristic deleted")
