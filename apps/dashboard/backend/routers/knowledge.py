"""
Knowledge Router - Decisions, Assumptions, Invariants, Spike Reports, Learnings.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from models import (
    DecisionCreate, DecisionUpdate,
    AssumptionCreate, AssumptionUpdate,
    InvariantCreate, InvariantUpdate,
    SpikeReportCreate, SpikeReportUpdate, SpikeReportRate,
    ActionResult
)
from utils import get_db, dict_from_row, escape_like

router = APIRouter(prefix="/api", tags=["knowledge"])

# ConnectionManager will be injected from main.py
manager = None


def set_manager(m):
    """Set the ConnectionManager for broadcasting updates."""
    global manager
    manager = m


# ==============================================================================
# Learnings
# ==============================================================================

@router.get("/learnings")
async def get_learnings(
    type: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 50
):
    """Get learnings (failures, successes, observations)."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM learnings WHERE 1=1"
        params = []

        if type:
            query += " AND type = ?"
            params.append(type)

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


# ==============================================================================
# Decisions
# ==============================================================================

@router.get("/decisions")
async def get_decisions(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """Get architecture decisions with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, title, context, options_considered, decision, rationale,
                   domain, files_touched, tests_added, status, superseded_by,
                   created_at, updated_at
            FROM decisions
            WHERE 1=1
        """
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(skip)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: int):
    """Get single decision with full details."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        decision = dict_from_row(cursor.fetchone())

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        # Get related decisions (same domain)
        cursor.execute("""
            SELECT id, title, status, created_at
            FROM decisions
            WHERE domain = ? AND id != ?
            ORDER BY created_at DESC
            LIMIT 5
        """, (decision["domain"], decision_id))
        decision["related"] = [dict_from_row(r) for r in cursor.fetchall()]

        # If this decision supersedes another, get the superseded decision
        if decision.get("superseded_by"):
            cursor.execute("""
                SELECT id, title, status
                FROM decisions
                WHERE id = ?
            """, (decision["superseded_by"],))
            decision["supersedes"] = dict_from_row(cursor.fetchone())

        # Get decisions that this one superseded
        cursor.execute("""
            SELECT id, title, status, created_at
            FROM decisions
            WHERE superseded_by = ?
        """, (decision_id,))
        decision["superseded_decisions"] = [dict_from_row(r) for r in cursor.fetchall()]

        return decision


@router.post("/decisions")
async def create_decision(decision: DecisionCreate) -> ActionResult:
    """Create a new architecture decision."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO decisions (
                title, context, options_considered, decision, rationale,
                domain, files_touched, tests_added, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.title,
            decision.context,
            decision.options_considered,
            decision.decision,
            decision.rationale,
            decision.domain,
            decision.files_touched,
            decision.tests_added,
            decision.status,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        decision_id = cursor.lastrowid
        conn.commit()

        if manager:
            await manager.broadcast_update("decision_created", {
                "decision_id": decision_id,
                "title": decision.title,
                "domain": decision.domain
            })

        return ActionResult(
            success=True,
            message=f"Created decision: {decision.title}",
            data={"decision_id": decision_id}
        )


@router.put("/decisions/{decision_id}")
async def update_decision(decision_id: int, update: DecisionUpdate) -> ActionResult:
    """Update an existing decision."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM decisions WHERE id = ?", (decision_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Decision not found")

        updates = []
        params = []

        if update.title is not None:
            updates.append("title = ?")
            params.append(update.title)

        if update.context is not None:
            updates.append("context = ?")
            params.append(update.context)

        if update.options_considered is not None:
            updates.append("options_considered = ?")
            params.append(update.options_considered)

        if update.decision is not None:
            updates.append("decision = ?")
            params.append(update.decision)

        if update.rationale is not None:
            updates.append("rationale = ?")
            params.append(update.rationale)

        if update.domain is not None:
            updates.append("domain = ?")
            params.append(update.domain)

        if update.files_touched is not None:
            updates.append("files_touched = ?")
            params.append(update.files_touched)

        if update.tests_added is not None:
            updates.append("tests_added = ?")
            params.append(update.tests_added)

        if update.status is not None:
            updates.append("status = ?")
            params.append(update.status)

        if not updates:
            return ActionResult(success=False, message="No updates provided")

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(decision_id)

        cursor.execute(f"""
            UPDATE decisions
            SET {", ".join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()

        if manager:
            await manager.broadcast_update("decision_updated", {"decision_id": decision_id})

        return ActionResult(success=True, message="Decision updated")


@router.delete("/decisions/{decision_id}")
async def delete_decision(decision_id: int) -> ActionResult:
    """Delete a decision."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT title FROM decisions WHERE id = ?", (decision_id,))
        decision = cursor.fetchone()
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        cursor.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
        conn.commit()

        if manager:
            await manager.broadcast_update("decision_deleted", {"decision_id": decision_id})

        return ActionResult(success=True, message=f"Deleted decision: {decision['title']}")


@router.post("/decisions/{decision_id}/supersede")
async def supersede_decision(decision_id: int, new_decision: DecisionCreate) -> ActionResult:
    """Supersede a decision with a new one."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        old_decision = dict_from_row(cursor.fetchone())
        if not old_decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        # Create new decision
        cursor.execute("""
            INSERT INTO decisions (
                title, context, options_considered, decision, rationale,
                domain, files_touched, tests_added, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_decision.title,
            new_decision.context,
            new_decision.options_considered,
            new_decision.decision,
            new_decision.rationale,
            new_decision.domain,
            new_decision.files_touched,
            new_decision.tests_added,
            new_decision.status,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        new_decision_id = cursor.lastrowid

        # Update old decision to mark it as superseded
        cursor.execute("""
            UPDATE decisions
            SET status = 'superseded', superseded_by = ?, updated_at = ?
            WHERE id = ?
        """, (new_decision_id, datetime.now().isoformat(), decision_id))

        conn.commit()

        if manager:
            await manager.broadcast_update("decision_superseded", {
                "old_decision_id": decision_id,
                "new_decision_id": new_decision_id,
                "title": new_decision.title
            })

        return ActionResult(
            success=True,
            message=f"Superseded decision #{decision_id} with #{new_decision_id}",
            data={"new_decision_id": new_decision_id, "old_decision_id": decision_id}
        )


# ==============================================================================
# Assumptions
# ==============================================================================

@router.get("/assumptions")
async def get_assumptions(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    min_confidence: Optional[float] = None,
    skip: int = 0,
    limit: int = 50
):
    """Get assumptions with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, assumption, context, source, confidence, status, domain,
                   verified_count, challenged_count, last_verified_at,
                   created_at, updated_at
            FROM assumptions
            WHERE 1=1
        """
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if status:
            query += " AND status = ?"
            params.append(status)

        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(skip)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.get("/assumptions/{assumption_id}")
async def get_assumption(assumption_id: int):
    """Get single assumption with full details."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM assumptions WHERE id = ?", (assumption_id,))
        assumption = dict_from_row(cursor.fetchone())

        if not assumption:
            raise HTTPException(status_code=404, detail="Assumption not found")

        if assumption.get("domain"):
            cursor.execute("""
                SELECT id, assumption, status, confidence, created_at
                FROM assumptions
                WHERE domain = ? AND id != ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (assumption["domain"], assumption_id))
            assumption["related"] = [dict_from_row(r) for r in cursor.fetchall()]
        else:
            assumption["related"] = []

        return assumption


@router.post("/assumptions")
async def create_assumption(assumption: AssumptionCreate) -> ActionResult:
    """Create a new assumption."""
    with get_db() as conn:
        cursor = conn.cursor()

        confidence = assumption.confidence
        if confidence is None:
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        cursor.execute("""
            INSERT INTO assumptions (
                assumption, context, source, confidence, domain,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        """, (
            assumption.assumption,
            assumption.context,
            assumption.source,
            confidence,
            assumption.domain,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        assumption_id = cursor.lastrowid
        conn.commit()

        if manager:
            await manager.broadcast_update("assumption_created", {
                "assumption_id": assumption_id,
                "assumption": assumption.assumption[:100],
                "domain": assumption.domain
            })

        return ActionResult(
            success=True,
            message=f"Created assumption #{assumption_id}",
            data={"assumption_id": assumption_id}
        )


@router.put("/assumptions/{assumption_id}")
async def update_assumption(assumption_id: int, update: AssumptionUpdate) -> ActionResult:
    """Update an existing assumption."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM assumptions WHERE id = ?", (assumption_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Assumption not found")

        updates = []
        params = []

        if update.assumption is not None:
            updates.append("assumption = ?")
            params.append(update.assumption)

        if update.context is not None:
            updates.append("context = ?")
            params.append(update.context)

        if update.source is not None:
            updates.append("source = ?")
            params.append(update.source)

        if update.confidence is not None:
            confidence = max(0.0, min(1.0, update.confidence))
            updates.append("confidence = ?")
            params.append(confidence)

        if update.status is not None:
            valid_statuses = ['active', 'verified', 'challenged', 'invalidated']
            if update.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
            updates.append("status = ?")
            params.append(update.status)

        if update.domain is not None:
            updates.append("domain = ?")
            params.append(update.domain)

        if not updates:
            return ActionResult(success=False, message="No updates provided")

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(assumption_id)

        cursor.execute(f"""
            UPDATE assumptions
            SET {", ".join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()

        if manager:
            await manager.broadcast_update("assumption_updated", {"assumption_id": assumption_id})

        return ActionResult(success=True, message="Assumption updated")


@router.post("/assumptions/{assumption_id}/verify")
async def verify_assumption(assumption_id: int) -> ActionResult:
    """Mark an assumption as verified (increment verified_count)."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM assumptions WHERE id = ?", (assumption_id,))
        assumption = dict_from_row(cursor.fetchone())
        if not assumption:
            raise HTTPException(status_code=404, detail="Assumption not found")

        new_verified = assumption['verified_count'] + 1
        total_checks = new_verified + assumption['challenged_count']
        new_confidence = new_verified / total_checks if total_checks > 0 else assumption['confidence']

        cursor.execute("""
            UPDATE assumptions
            SET verified_count = ?,
                confidence = ?,
                status = CASE WHEN verified_count >= 3 THEN 'verified' ELSE status END,
                last_verified_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_verified,
            new_confidence,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            assumption_id
        ))

        conn.commit()

        if manager:
            await manager.broadcast_update("assumption_verified", {
                "assumption_id": assumption_id,
                "verified_count": new_verified,
                "confidence": new_confidence
            })

        return ActionResult(
            success=True,
            message=f"Assumption #{assumption_id} verified (count: {new_verified})",
            data={"verified_count": new_verified, "new_confidence": round(new_confidence, 3)}
        )


@router.post("/assumptions/{assumption_id}/challenge")
async def challenge_assumption(assumption_id: int) -> ActionResult:
    """Challenge an assumption (increment challenged_count, decrease confidence)."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM assumptions WHERE id = ?", (assumption_id,))
        assumption = dict_from_row(cursor.fetchone())
        if not assumption:
            raise HTTPException(status_code=404, detail="Assumption not found")

        new_challenged = assumption['challenged_count'] + 1
        total_checks = assumption['verified_count'] + new_challenged
        new_confidence = assumption['verified_count'] / total_checks if total_checks > 0 else 0

        new_status = assumption['status']
        if new_confidence < 0.3:
            new_status = 'challenged'
        if new_confidence == 0:
            new_status = 'invalidated'

        cursor.execute("""
            UPDATE assumptions
            SET challenged_count = ?,
                confidence = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_challenged,
            new_confidence,
            new_status,
            datetime.now().isoformat(),
            assumption_id
        ))

        conn.commit()

        if manager:
            await manager.broadcast_update("assumption_challenged", {
                "assumption_id": assumption_id,
                "challenged_count": new_challenged,
                "confidence": new_confidence
            })

        return ActionResult(
            success=True,
            message=f"Assumption #{assumption_id} challenged (count: {new_challenged})",
            data={"challenged_count": new_challenged, "new_confidence": round(new_confidence, 3)}
        )


@router.delete("/assumptions/{assumption_id}")
async def delete_assumption(assumption_id: int) -> ActionResult:
    """Delete an assumption."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT assumption FROM assumptions WHERE id = ?", (assumption_id,))
        assumption = cursor.fetchone()
        if not assumption:
            raise HTTPException(status_code=404, detail="Assumption not found")

        cursor.execute("DELETE FROM assumptions WHERE id = ?", (assumption_id,))
        conn.commit()

        if manager:
            await manager.broadcast_update("assumption_deleted", {"assumption_id": assumption_id})

        return ActionResult(success=True, message=f"Deleted assumption #{assumption_id}")


# ==============================================================================
# Invariants
# ==============================================================================

@router.get("/invariants")
async def get_invariants(
    domain: Optional[str] = None,
    scope: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """Get invariants with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, statement, rationale, domain, scope, validation_type,
                   validation_code, severity, status, violation_count,
                   last_validated_at, last_violated_at, created_at, updated_at
            FROM invariants
            WHERE 1=1
        """
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if scope:
            query += " AND scope = ?"
            params.append(scope)

        if status:
            query += " AND status = ?"
            params.append(status)

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(skip)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.get("/invariants/{invariant_id}")
async def get_invariant(invariant_id: int):
    """Get single invariant with full details."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM invariants WHERE id = ?", (invariant_id,))
        invariant = dict_from_row(cursor.fetchone())

        if not invariant:
            raise HTTPException(status_code=404, detail="Invariant not found")

        if invariant.get("domain"):
            cursor.execute("""
                SELECT id, statement, status, severity, created_at
                FROM invariants
                WHERE domain = ? AND id != ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (invariant["domain"], invariant_id))
            invariant["related"] = [dict_from_row(r) for r in cursor.fetchall()]
        else:
            invariant["related"] = []

        return invariant


@router.post("/invariants")
async def create_invariant(invariant: InvariantCreate) -> ActionResult:
    """Create a new invariant."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO invariants (
                statement, rationale, domain, scope, validation_type,
                validation_code, severity, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """, (
            invariant.statement,
            invariant.rationale,
            invariant.domain,
            invariant.scope,
            invariant.validation_type,
            invariant.validation_code,
            invariant.severity,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        invariant_id = cursor.lastrowid
        conn.commit()

        if manager:
            await manager.broadcast_update("invariant_created", {
                "invariant_id": invariant_id,
                "statement": invariant.statement[:100],
                "domain": invariant.domain
            })

        return ActionResult(
            success=True,
            message=f"Created invariant: {invariant.statement[:50]}...",
            data={"invariant_id": invariant_id}
        )


@router.put("/invariants/{invariant_id}")
async def update_invariant(invariant_id: int, update: InvariantUpdate) -> ActionResult:
    """Update an existing invariant."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM invariants WHERE id = ?", (invariant_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Invariant not found")

        updates = []
        params = []

        if update.statement is not None:
            updates.append("statement = ?")
            params.append(update.statement)

        if update.rationale is not None:
            updates.append("rationale = ?")
            params.append(update.rationale)

        if update.domain is not None:
            updates.append("domain = ?")
            params.append(update.domain)

        if update.scope is not None:
            updates.append("scope = ?")
            params.append(update.scope)

        if update.validation_type is not None:
            updates.append("validation_type = ?")
            params.append(update.validation_type)

        if update.validation_code is not None:
            updates.append("validation_code = ?")
            params.append(update.validation_code)

        if update.severity is not None:
            updates.append("severity = ?")
            params.append(update.severity)

        if update.status is not None:
            updates.append("status = ?")
            params.append(update.status)

        if not updates:
            return ActionResult(success=False, message="No updates provided")

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(invariant_id)

        cursor.execute(f"""
            UPDATE invariants
            SET {", ".join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()

        if manager:
            await manager.broadcast_update("invariant_updated", {"invariant_id": invariant_id})

        return ActionResult(success=True, message="Invariant updated")


@router.post("/invariants/{invariant_id}/validate")
async def validate_invariant(invariant_id: int) -> ActionResult:
    """Mark an invariant as validated (update last_validated_at)."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT statement FROM invariants WHERE id = ?", (invariant_id,))
        invariant = cursor.fetchone()
        if not invariant:
            raise HTTPException(status_code=404, detail="Invariant not found")

        cursor.execute("""
            UPDATE invariants
            SET last_validated_at = ?, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), invariant_id))

        conn.commit()

        if manager:
            await manager.broadcast_update("invariant_validated", {"invariant_id": invariant_id})

        return ActionResult(
            success=True,
            message=f"Invariant #{invariant_id} marked as validated",
            data={"invariant_id": invariant_id, "validated_at": datetime.now().isoformat()}
        )


@router.post("/invariants/{invariant_id}/violate")
async def record_invariant_violation(invariant_id: int) -> ActionResult:
    """Record a violation of an invariant (increment count, update timestamp)."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT statement, violation_count FROM invariants WHERE id = ?", (invariant_id,))
        invariant = cursor.fetchone()
        if not invariant:
            raise HTTPException(status_code=404, detail="Invariant not found")

        new_count = (invariant["violation_count"] or 0) + 1

        cursor.execute("""
            UPDATE invariants
            SET violation_count = ?,
                last_violated_at = ?,
                updated_at = ?,
                status = CASE WHEN ? >= 3 THEN 'violated' ELSE status END
            WHERE id = ?
        """, (new_count, datetime.now().isoformat(), datetime.now().isoformat(), new_count, invariant_id))

        conn.commit()

        if manager:
            await manager.broadcast_update("invariant_violated", {
                "invariant_id": invariant_id,
                "violation_count": new_count
            })

        return ActionResult(
            success=True,
            message=f"Recorded violation for invariant #{invariant_id} (total: {new_count})",
            data={"invariant_id": invariant_id, "violation_count": new_count}
        )


@router.delete("/invariants/{invariant_id}")
async def delete_invariant(invariant_id: int) -> ActionResult:
    """Delete an invariant."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT statement FROM invariants WHERE id = ?", (invariant_id,))
        invariant = cursor.fetchone()
        if not invariant:
            raise HTTPException(status_code=404, detail="Invariant not found")

        cursor.execute("DELETE FROM invariants WHERE id = ?", (invariant_id,))
        conn.commit()

        if manager:
            await manager.broadcast_update("invariant_deleted", {"invariant_id": invariant_id})

        return ActionResult(success=True, message=f"Deleted invariant: {invariant['statement'][:50]}...")


# ==============================================================================
# Spike Reports
# ==============================================================================

@router.get("/spike-reports")
async def get_spike_reports(
    domain: Optional[str] = None,
    tags: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "recent",
    skip: int = 0,
    limit: int = 50
):
    """Get spike reports with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, title, topic, question, findings, gotchas, resources,
                   time_invested_minutes, domain, tags, usefulness_score,
                   access_count, created_at, updated_at
            FROM spike_reports
            WHERE 1=1
        """
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tag_list])
            query += f" AND ({tag_conditions})"
            params.extend([f"%{escape_like(tag)}%" for tag in tag_list])

        if search:
            escaped_search = escape_like(search)
            query += " AND (title LIKE ? OR topic LIKE ? OR question LIKE ? OR findings LIKE ?)"
            params.extend([f"%{escaped_search}%"] * 4)

        sort_map = {
            "recent": "created_at DESC",
            "useful": "usefulness_score DESC",
            "accessed": "access_count DESC",
            "time": "time_invested_minutes DESC"
        }
        query += f" ORDER BY {sort_map.get(sort_by, 'created_at DESC')}"
        query += " LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(skip)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.get("/spike-reports/search")
async def search_spike_reports(
    q: str,
    limit: int = 20
):
    """Full-text search spike reports."""
    with get_db() as conn:
        cursor = conn.cursor()

        escaped_q = escape_like(q)
        search_pattern = f"%{escaped_q}%"

        cursor.execute("""
            SELECT id, title, topic, question, findings, gotchas,
                   time_invested_minutes, domain, tags, usefulness_score, created_at
            FROM spike_reports
            WHERE title LIKE ? OR topic LIKE ? OR question LIKE ?
                  OR findings LIKE ? OR gotchas LIKE ? OR tags LIKE ?
            ORDER BY usefulness_score DESC, created_at DESC
            LIMIT ?
        """, (search_pattern, search_pattern, search_pattern,
              search_pattern, search_pattern, search_pattern, limit))

        return [dict_from_row(r) for r in cursor.fetchall()]


@router.get("/spike-reports/{spike_id}")
async def get_spike_report(spike_id: int):
    """Get single spike report with full details."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM spike_reports WHERE id = ?", (spike_id,))
        spike = dict_from_row(cursor.fetchone())

        if not spike:
            raise HTTPException(status_code=404, detail="Spike report not found")

        # Increment access count
        cursor.execute("""
            UPDATE spike_reports
            SET access_count = COALESCE(access_count, 0) + 1
            WHERE id = ?
        """, (spike_id,))
        conn.commit()

        # Get related spikes (same domain or overlapping tags)
        if spike.get("domain"):
            cursor.execute("""
                SELECT id, title, topic, usefulness_score, created_at
                FROM spike_reports
                WHERE domain = ? AND id != ?
                ORDER BY usefulness_score DESC
                LIMIT 5
            """, (spike["domain"], spike_id))
            spike["related"] = [dict_from_row(r) for r in cursor.fetchall()]
        else:
            spike["related"] = []

        return spike


@router.post("/spike-reports")
async def create_spike_report(spike: SpikeReportCreate) -> ActionResult:
    """Create a new spike report."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO spike_reports (
                title, topic, question, findings, gotchas, resources,
                time_invested_minutes, domain, tags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            spike.title,
            spike.topic,
            spike.question,
            spike.findings,
            spike.gotchas,
            spike.resources,
            spike.time_invested_minutes,
            spike.domain,
            spike.tags,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        spike_id = cursor.lastrowid
        conn.commit()

        if manager:
            await manager.broadcast_update("spike_report_created", {
                "spike_id": spike_id,
                "title": spike.title,
                "domain": spike.domain
            })

        return ActionResult(
            success=True,
            message=f"Created spike report: {spike.title}",
            data={"spike_id": spike_id}
        )


@router.put("/spike-reports/{spike_id}")
async def update_spike_report(spike_id: int, update: SpikeReportUpdate) -> ActionResult:
    """Update a spike report."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM spike_reports WHERE id = ?", (spike_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Spike report not found")

        updates = []
        params = []

        if update.title is not None:
            updates.append("title = ?")
            params.append(update.title)

        if update.topic is not None:
            updates.append("topic = ?")
            params.append(update.topic)

        if update.question is not None:
            updates.append("question = ?")
            params.append(update.question)

        if update.findings is not None:
            updates.append("findings = ?")
            params.append(update.findings)

        if update.gotchas is not None:
            updates.append("gotchas = ?")
            params.append(update.gotchas)

        if update.resources is not None:
            updates.append("resources = ?")
            params.append(update.resources)

        if update.time_invested_minutes is not None:
            updates.append("time_invested_minutes = ?")
            params.append(update.time_invested_minutes)

        if update.domain is not None:
            updates.append("domain = ?")
            params.append(update.domain)

        if update.tags is not None:
            updates.append("tags = ?")
            params.append(update.tags)

        if not updates:
            return ActionResult(success=False, message="No updates provided")

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(spike_id)

        cursor.execute(f"""
            UPDATE spike_reports
            SET {", ".join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()

        if manager:
            await manager.broadcast_update("spike_report_updated", {"spike_id": spike_id})

        return ActionResult(success=True, message="Spike report updated")


@router.post("/spike-reports/{spike_id}/rate")
async def rate_spike_report(spike_id: int, rating: SpikeReportRate) -> ActionResult:
    """Rate the usefulness of a spike report (0-5 scale)."""
    if not 0 <= rating.score <= 5:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 5")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT usefulness_score, access_count
            FROM spike_reports WHERE id = ?
        """, (spike_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Spike report not found")

        current_score = row['usefulness_score'] or 0
        access_count = row['access_count'] or 1

        new_score = (current_score * access_count + rating.score) / (access_count + 1)

        cursor.execute("""
            UPDATE spike_reports
            SET usefulness_score = ?, updated_at = ?
            WHERE id = ?
        """, (new_score, datetime.now().isoformat(), spike_id))

        conn.commit()

        return ActionResult(
            success=True,
            message=f"Rated spike report with score {rating.score}",
            data={"new_average": round(new_score, 2)}
        )


@router.delete("/spike-reports/{spike_id}")
async def delete_spike_report(spike_id: int) -> ActionResult:
    """Delete a spike report."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT title FROM spike_reports WHERE id = ?", (spike_id,))
        spike = cursor.fetchone()
        if not spike:
            raise HTTPException(status_code=404, detail="Spike report not found")

        cursor.execute("DELETE FROM spike_reports WHERE id = ?", (spike_id,))
        conn.commit()

        if manager:
            await manager.broadcast_update("spike_report_deleted", {"spike_id": spike_id})

        return ActionResult(success=True, message=f"Deleted spike report: {spike['title']}")
