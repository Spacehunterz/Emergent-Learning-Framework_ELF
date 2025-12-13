# BaseRepository - Generic CRUD Operations

## Overview

The `BaseRepository` class provides reusable database operations to eliminate code duplication across endpoints. Instead of writing manual SQL for every table, use this generic repository for standard CRUD operations.

## Motivation

**Before BaseRepository:**
- 5+ tables with nearly identical CRUD code
- ~109 lines of SQL per table
- Inconsistent error handling
- Difficult to maintain

**After BaseRepository:**
- ~39 lines per table (64% reduction)
- Consistent patterns across all tables
- Better error handling
- Single source of truth for CRUD operations

## Quick Start

```python
from utils import get_db, BaseRepository

# Basic usage
with get_db() as conn:
    repo = BaseRepository(conn)

    # Get a record
    decision = repo.get_by_id("decisions", 123)

    # List all records
    decisions = repo.list_all("decisions", limit=50)

    # Create a record
    new_id = repo.create("decisions", {
        "title": "Use BaseRepository",
        "context": "Eliminate duplication",
        "status": "active"
    })
```

## Methods

### get_by_id(table: str, id: int) -> Optional[dict]

Get a single record by ID.

```python
decision = repo.get_by_id("decisions", 123)
if decision:
    print(decision["title"])
else:
    print("Not found")
```

**Returns:** Dictionary of record data, or None if not found

---

### list_all(table: str, limit: int = 100, offset: int = 0, order_by: str = "created_at DESC") -> list[dict]

List all records with pagination.

```python
# Get first 50 decisions
decisions = repo.list_all("decisions", limit=50, offset=0)

# Get next 50 decisions
more_decisions = repo.list_all("decisions", limit=50, offset=50)

# Custom ordering
newest = repo.list_all("decisions", order_by="updated_at DESC")
```

**Parameters:**
- `table`: Table name
- `limit`: Max records to return (default: 100)
- `offset`: Number of records to skip (default: 0)
- `order_by`: SQL ORDER BY clause (default: "created_at DESC")

**Returns:** List of record dictionaries

---

### list_with_filters(table: str, filters: dict, limit: int = 100, offset: int = 0, order_by: str = "created_at DESC") -> list[dict]

List records with WHERE clause filters.

```python
# Get active decisions in auth domain
filters = {
    "domain": "auth",
    "status": "active"
}
decisions = repo.list_with_filters("decisions", filters, limit=20)

# None values are ignored
filters = {
    "domain": "auth",
    "status": None  # This filter will be skipped
}
decisions = repo.list_with_filters("decisions", filters)
```

**Parameters:**
- `table`: Table name
- `filters`: Dictionary of column: value pairs for WHERE clause
- `limit`: Max records to return (default: 100)
- `offset`: Number of records to skip (default: 0)
- `order_by`: SQL ORDER BY clause (default: "created_at DESC")

**Returns:** List of record dictionaries matching the filters

**Note:** Only supports equality (=) comparisons. For complex queries, use custom SQL.

---

### create(table: str, data: dict) -> int

Create a new record.

```python
from datetime import datetime

new_id = repo.create("decisions", {
    "title": "Use JWT for auth",
    "context": "Need secure authentication",
    "decision": "Implement JWT tokens",
    "rationale": "Industry standard",
    "domain": "auth",
    "status": "active",
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat()
})

print(f"Created decision ID: {new_id}")
```

**Parameters:**
- `table`: Table name
- `data`: Dictionary of column: value pairs

**Returns:** ID of the newly created record

**Raises:** `sqlite3.IntegrityError` if constraints are violated

---

### update(table: str, id: int, data: dict) -> bool

Update an existing record.

```python
# Update status
success = repo.update("decisions", 123, {
    "status": "superseded",
    "updated_at": datetime.now().isoformat()
})

if success:
    print("Updated successfully")
else:
    print("Record not found")
```

**Parameters:**
- `table`: Table name
- `id`: Record ID to update
- `data`: Dictionary of column: value pairs to update

**Returns:** True if record was updated, False if not found

---

### delete(table: str, id: int) -> bool

Delete a record by ID.

```python
success = repo.delete("decisions", 123)

if success:
    print("Deleted successfully")
else:
    print("Record not found")
```

**Parameters:**
- `table`: Table name
- `id`: Record ID to delete

**Returns:** True if record was deleted, False if not found

---

### exists(table: str, id: int) -> bool

Check if a record exists.

```python
if repo.exists("decisions", 123):
    print("Decision exists")
else:
    raise HTTPException(status_code=404, detail="Decision not found")
```

**Parameters:**
- `table`: Table name
- `id`: Record ID to check

**Returns:** True if record exists, False otherwise

**Use case:** Validate before update/delete operations

---

### count(table: str, filters: Optional[dict] = None) -> int

Count records in a table, optionally with filters.

```python
# Count all decisions
total = repo.count("decisions")
print(f"Total decisions: {total}")

# Count active decisions
active_count = repo.count("decisions", {"status": "active"})
print(f"Active decisions: {active_count}")

# Count by domain
auth_count = repo.count("decisions", {"domain": "auth"})
print(f"Auth decisions: {auth_count}")
```

**Parameters:**
- `table`: Table name
- `filters`: Optional dictionary of column: value pairs for WHERE clause

**Returns:** Number of matching records

---

## Common Patterns

### Pattern 1: Get with 404 handling

```python
@app.get("/api/decisions/{decision_id}")
async def get_decision(decision_id: int):
    with get_db() as conn:
        repo = BaseRepository(conn)
        decision = repo.get_by_id("decisions", decision_id)

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        return decision
```

### Pattern 2: List with optional filters

```python
@app.get("/api/decisions")
async def get_decisions(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    with get_db() as conn:
        repo = BaseRepository(conn)

        # Build filters dict (None values are ignored automatically)
        filters = {
            "domain": domain,
            "status": status
        }

        return repo.list_with_filters("decisions", filters, limit=limit, offset=skip)
```

### Pattern 3: Create with timestamps

```python
@app.post("/api/decisions")
async def create_decision(decision: DecisionCreate):
    from datetime import datetime

    # Convert Pydantic model to dict
    data = decision.model_dump()

    # Add timestamps
    data["created_at"] = datetime.now().isoformat()
    data["updated_at"] = datetime.now().isoformat()

    with get_db() as conn:
        repo = BaseRepository(conn)
        new_id = repo.create("decisions", data)

        return {"id": new_id, "message": "Decision created"}
```

### Pattern 4: Update with validation

```python
@app.put("/api/decisions/{decision_id}")
async def update_decision(decision_id: int, update: DecisionUpdate):
    from datetime import datetime

    # Convert Pydantic model to dict, excluding unset fields
    data = update.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Add updated timestamp
    data["updated_at"] = datetime.now().isoformat()

    with get_db() as conn:
        repo = BaseRepository(conn)

        if not repo.exists("decisions", decision_id):
            raise HTTPException(status_code=404, detail="Decision not found")

        repo.update("decisions", decision_id, data)

        return {"message": "Decision updated"}
```

### Pattern 5: Delete with existence check

```python
@app.delete("/api/decisions/{decision_id}")
async def delete_decision(decision_id: int):
    with get_db() as conn:
        repo = BaseRepository(conn)

        if not repo.delete("decisions", decision_id):
            raise HTTPException(status_code=404, detail="Decision not found")

        return {"message": "Decision deleted"}
```

### Pattern 6: Paginated list with count

```python
@app.get("/api/decisions")
async def get_decisions(skip: int = 0, limit: int = 50):
    with get_db() as conn:
        repo = BaseRepository(conn)

        # Get total count for pagination metadata
        total = repo.count("decisions")

        # Get paginated results
        decisions = repo.list_all("decisions", limit=limit, offset=skip)

        return {
            "data": decisions,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": (skip + limit) < total
            }
        }
```

## When NOT to Use BaseRepository

BaseRepository is great for standard CRUD, but use custom SQL for:

1. **Complex joins**: Multi-table queries with relationships
2. **Aggregations**: GROUP BY, SUM, AVG operations
3. **Custom logic**: Domain-specific queries that don't fit the generic pattern
4. **Performance-critical queries**: Where you need query optimization

```python
# DON'T use BaseRepository for this
# (This is a complex join with aggregation)
with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.id, d.title, COUNT(a.id) as assumption_count
        FROM decisions d
        LEFT JOIN assumptions a ON a.decision_id = d.id
        WHERE d.status = 'active'
        GROUP BY d.id
        HAVING assumption_count > 0
    """)
    results = [dict_from_row(r) for r in cursor.fetchall()]
```

## Extending BaseRepository

For domain-specific repositories, inherit from BaseRepository:

```python
from utils import BaseRepository

class DecisionRepository(BaseRepository):
    """Domain-specific repository for decisions."""

    def get_active_decisions(self, domain: str = None) -> list[dict]:
        """Get all active decisions, optionally filtered by domain."""
        filters = {"status": "active"}
        if domain:
            filters["domain"] = domain

        return self.list_with_filters("decisions", filters)

    def supersede(self, old_id: int, new_decision_data: dict) -> int:
        """Supersede an old decision with a new one."""
        # Custom business logic
        new_id = self.create("decisions", new_decision_data)
        self.update("decisions", old_id, {"superseded_by": new_id})
        return new_id

# Usage
with get_db() as conn:
    repo = DecisionRepository(conn)
    active = repo.get_active_decisions(domain="auth")
```

## Testing

Run the test suite to verify BaseRepository works correctly:

```bash
cd ~/.claude/emergent-learning/dashboard-app/backend
python test_repository.py
```

Expected output:
```
Testing BaseRepository...

1. Testing count()...
   Total decisions: X
   Total heuristics: Y

2. Testing list_all()...
   Retrieved N decisions
   First decision: [title]

3. Testing list_with_filters()...
   Retrieved N decisions with domain='elf-architecture'

4. Testing get_by_id()...
   Found decision ID X: [title]

5. Testing exists()...
   Decision ID X exists: True
   Decision ID 999999 exists: False

6. Testing create/update/delete...
   Creating test heuristic...
   Created heuristic ID: X
   Updating test heuristic...
   Update successful: True
   Updated confidence: 0.75
   Deleting test heuristic...
   Delete successful: True
   Exists after delete: False

[SUCCESS] All tests completed successfully!
```

## Migration Guide

See `repository_usage_example.py` for before/after comparison of typical endpoint code.

To refactor an endpoint to use BaseRepository:

1. Identify CRUD operations in the endpoint
2. Replace manual SQL with BaseRepository methods
3. Test the endpoint to ensure behavior is unchanged
4. Remove any unnecessary error handling that BaseRepository now handles

## Performance Considerations

- **Connection reuse**: BaseRepository reuses the connection passed to it
- **Transaction safety**: Commits are handled by BaseRepository methods
- **Query optimization**: Uses parameterized queries to prevent SQL injection
- **Pagination**: Built-in LIMIT/OFFSET support for efficient pagination

## Security

- **SQL injection protection**: All queries use parameterized statements
- **No dynamic table names from user input**: Table names should be hardcoded in your code
- **Constraint validation**: SQLite constraints are enforced (foreign keys, unique, etc.)

## Summary

BaseRepository provides:
- ✓ Standard CRUD operations
- ✓ Consistent error handling
- ✓ Pagination support
- ✓ Filter support
- ✓ Helper methods (exists, count)
- ✓ 64% code reduction
- ✓ Single source of truth
- ✓ Easy to test
- ✓ Easy to extend

Use it for all standard database operations to keep your codebase clean and maintainable.
