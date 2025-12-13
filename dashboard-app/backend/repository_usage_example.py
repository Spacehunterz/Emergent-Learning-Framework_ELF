"""
Example: How to refactor existing endpoints using BaseRepository.

This demonstrates the before/after comparison to show the code reduction.
"""

# ============================================================================
# BEFORE: Duplicated CRUD code (typical pattern in main.py)
# ============================================================================

# Example 1: Get all with filters (BEFORE)
def get_decisions_old(domain=None, status=None, skip=0, limit=50):
    """Old approach with duplicated SQL code."""
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


# Example 2: Get by ID (BEFORE)
def get_decision_old(decision_id: int):
    """Old approach with duplicated SQL code."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM decisions WHERE id = ?
        """, (decision_id,))
        decision = dict_from_row(cursor.fetchone())

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        return decision


# Example 3: Create (BEFORE)
def create_decision_old(decision_data: dict):
    """Old approach with manual INSERT."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO decisions (
                title, context, options_considered, decision, rationale,
                domain, files_touched, tests_added, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_data["title"],
            decision_data["context"],
            decision_data["options_considered"],
            decision_data["decision"],
            decision_data["rationale"],
            decision_data["domain"],
            decision_data["files_touched"],
            decision_data["tests_added"],
            decision_data["status"],
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        decision_id = cursor.lastrowid
        conn.commit()

        return decision_id


# Example 4: Update (BEFORE)
def update_decision_old(decision_id: int, update_data: dict):
    """Old approach with manual UPDATE building."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify decision exists
        cursor.execute("SELECT id FROM decisions WHERE id = ?", (decision_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Decision not found")

        updates = []
        params = []

        if "title" in update_data:
            updates.append("title = ?")
            params.append(update_data["title"])

        if "context" in update_data:
            updates.append("context = ?")
            params.append(update_data["context"])

        if "status" in update_data:
            updates.append("status = ?")
            params.append(update_data["status"])

        # ... repeat for all fields ...

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(decision_id)

        cursor.execute(f"""
            UPDATE decisions
            SET {", ".join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()
        return True


# Example 5: Delete (BEFORE)
def delete_decision_old(decision_id: int):
    """Old approach with manual DELETE."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if decision exists
        cursor.execute("SELECT title FROM decisions WHERE id = ?", (decision_id,))
        decision = cursor.fetchone()
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        # Delete the decision
        cursor.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
        conn.commit()

        return True


# ============================================================================
# AFTER: Using BaseRepository (much cleaner!)
# ============================================================================

from utils import get_db, BaseRepository

# Example 1: Get all with filters (AFTER)
def get_decisions_new(domain=None, status=None, skip=0, limit=50):
    """New approach using BaseRepository."""
    with get_db() as conn:
        repo = BaseRepository(conn)

        filters = {}
        if domain:
            filters["domain"] = domain
        if status:
            filters["status"] = status

        return repo.list_with_filters("decisions", filters, limit=limit, offset=skip)


# Example 2: Get by ID (AFTER)
def get_decision_new(decision_id: int):
    """New approach using BaseRepository."""
    with get_db() as conn:
        repo = BaseRepository(conn)
        decision = repo.get_by_id("decisions", decision_id)

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        return decision


# Example 3: Create (AFTER)
def create_decision_new(decision_data: dict):
    """New approach using BaseRepository."""
    decision_data["created_at"] = datetime.now().isoformat()
    decision_data["updated_at"] = datetime.now().isoformat()

    with get_db() as conn:
        repo = BaseRepository(conn)
        return repo.create("decisions", decision_data)


# Example 4: Update (AFTER)
def update_decision_new(decision_id: int, update_data: dict):
    """New approach using BaseRepository."""
    update_data["updated_at"] = datetime.now().isoformat()

    with get_db() as conn:
        repo = BaseRepository(conn)

        if not repo.exists("decisions", decision_id):
            raise HTTPException(status_code=404, detail="Decision not found")

        return repo.update("decisions", decision_id, update_data)


# Example 5: Delete (AFTER)
def delete_decision_new(decision_id: int):
    """New approach using BaseRepository."""
    with get_db() as conn:
        repo = BaseRepository(conn)

        if not repo.exists("decisions", decision_id):
            raise HTTPException(status_code=404, detail="Decision not found")

        return repo.delete("decisions", decision_id)


# ============================================================================
# COMPARISON
# ============================================================================
"""
LINES OF CODE COMPARISON (for 5 basic CRUD operations):

BEFORE (manual SQL):
- get_all with filters: ~25 lines
- get_by_id: ~12 lines
- create: ~25 lines
- update: ~35 lines
- delete: ~12 lines
TOTAL: ~109 lines per table

AFTER (BaseRepository):
- get_all with filters: ~8 lines
- get_by_id: ~8 lines
- create: ~6 lines
- update: ~9 lines
- delete: ~8 lines
TOTAL: ~39 lines per table

REDUCTION: 70 lines saved per table (64% reduction)

With 5 tables (decisions, assumptions, invariants, spike-reports, heuristics):
- BEFORE: 545 lines
- AFTER: 195 lines
- SAVED: 350 lines of duplicated CRUD code

Plus you get additional helper methods for free:
- count(): Count records with optional filters
- exists(): Check if a record exists
- Better error handling
- Consistent patterns across all tables
"""
