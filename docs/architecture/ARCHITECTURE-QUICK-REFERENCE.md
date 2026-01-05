# Architecture Quick Reference

**Date:** 2026-01-05
**Version:** 0.3.2

---

## Critical Issues At A Glance

| Issue | Severity | Impact | Recommendation |
|-------|----------|--------|----------------|
| Dual Query System (sync + async) | HIGH | Maintenance burden, drift risk | Unify: async core + sync facade |
| Overlapping Coordination (coordinator/ + conductor/) | HIGH | Developer confusion, code duplication | Merge into src/coordination/ |
| No Service Layer | MEDIUM | Business logic in routers | Extract services + repositories |
| SQLite Concurrency | MEDIUM | Write contention | Connection pooling + read replicas |
| Missing API Versioning | MEDIUM | Future breaking changes hard | Add /api/v1/ prefix |
| Inconsistent Imports | LOW | Fragile refactoring | Standardize to elf.* namespace |

---

## Current vs Target Architecture

### Current State
```
Apps ──────────────┐
                   ├──> src/query/ (sync 2620 lines)
                   ├──> src/query/core.py (async 421 lines)  ← DUPLICATION
                   ├──> coordinator/blackboard.py
                   └──> src/conductor/conductor.py           ← OVERLAP
                            │
                            └──> SQLite (direct access)
```

### Target State
```
Apps/Library
    │
    ├──> elf.services (HeuristicsService, WorkflowService)
    │        │
    │        ├──> elf.domain (Heuristic, Learning models)
    │        │
    │        └──> elf.persistence.repositories (HeuristicsRepo)
    │                 │
    │                 └──> Database (connection pool)
    │
    └──> elf.coordination.orchestrator (unified)
             │
             ├──> workflows/ (persistent, SQLite)
             └──> realtime/ (blackboard)
```

---

## Architecture Layers (One-Page)

```
┌────────────────────────────────────────────────────────────────┐
│                     APPLICATIONS                               │
│  apps/dashboard (FastAPI + React)    library/sdk (Public API)  │
└────────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────────┐
│                      SERVICES                                  │
│  elf.services.* (Business logic orchestration)                 │
│  - HeuristicsService  - WorkflowService  - AnalyticsService    │
└────────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────────┐
│                    DOMAIN LAYER                                │
│  elf.domain.* (Business rules, domain models)                  │
│  - Heuristic  - Learning  - Workflow  - Agent                  │
└────────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────────┐
│                  PERSISTENCE                                   │
│  elf.persistence.repositories.* (Data access)                  │
│  - HeuristicsRepository  - LearningsRepository                 │
└────────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────────┐
│                INFRASTRUCTURE                                  │
│  Database, Config, Logging, Events                             │
└────────────────────────────────────────────────────────────────┘
```

**Golden Rule:** Dependencies flow downward only. Lower layers never import from higher layers.

---

## Module Responsibilities (One-Line Each)

| Module | Responsibility |
|--------|----------------|
| `elf.core.*` | Async business logic, domain operations |
| `elf.sync.*` | Sync facades for backward compatibility (thin wrappers) |
| `elf.services.*` | Orchestrate operations, enforce business rules |
| `elf.domain.*` | Domain models with encapsulated business logic |
| `elf.persistence.*` | Data access via repository pattern |
| `elf.coordination.*` | Agent orchestration (workflows + blackboard) |
| `elf.infrastructure.*` | Cross-cutting: config, logging, caching |
| `elf.events.*` | Event bus for decoupled communication |
| `elf.plugins.*` | Extension framework for third-party code |
| `apps/dashboard/` | Web UI + versioned REST API (/api/v1/) |
| `library/sdk/` | Public Python client for external projects |

---

## Top 5 Architectural Patterns to Apply

### 1. Repository Pattern
**Problem:** Direct database access in routers
**Solution:** Abstract data access behind interfaces

```python
# ✗ Before
@router.get("/heuristics")
def get_heuristics():
    return Heuristic.select().where(Heuristic.is_golden == True)

# ✓ After
@router.get("/api/v1/heuristics")
async def get_heuristics(service: HeuristicsService = Depends()):
    return await service.get_golden_rules()
```

### 2. Service Layer
**Problem:** Business logic scattered across routers
**Solution:** Centralize in service classes

```python
class HeuristicsService:
    async def promote_to_golden(self, id: int) -> Heuristic:
        # Validation
        h = await self.repo.find_by_id(id)
        if h.confidence < 0.8:
            raise ValueError("Confidence too low")

        # Business logic
        h.is_golden = True
        await self.repo.save(h)

        # Side effects
        await self.events.publish(HeuristicPromoted(h))
        return h
```

### 3. Async Core + Sync Facade
**Problem:** Duplicate implementations (query.py vs core.py)
**Solution:** Single async implementation, thin sync wrapper

```python
# elf/core/query.py - Canonical implementation (async)
class AsyncQuerySystem:
    async def build_context(self, query: str) -> str:
        # Real implementation

# elf/sync/query.py - Backward compatibility
class QuerySystem:
    def build_context(self, query: str) -> str:
        return asyncio.run(self._async.build_context(query))
```

### 4. Event-Driven Architecture
**Problem:** Tight coupling between modules
**Solution:** Publish events, subscribe to changes

```python
# Publish
await event_bus.publish(HeuristicPromoted(id=123))

# Subscribe (dashboard)
event_bus.subscribe(EventType.HEURISTIC_PROMOTED, update_ui)

# Subscribe (TalkinHead)
event_bus.subscribe(EventType.WORKFLOW_COMPLETED, celebrate)
```

### 5. Dependency Injection
**Problem:** Hard-coded dependencies, difficult to test
**Solution:** Inject dependencies via constructors

```python
# ✗ Before
class HeuristicsService:
    def __init__(self):
        self.repo = HeuristicsRepository()  # Hard-coded

# ✓ After
class HeuristicsService:
    def __init__(self, repo: IHeuristicsRepository):
        self.repo = repo  # Injected, mockable

# Usage
service = HeuristicsService(repo=MockRepository())  # Testing
service = HeuristicsService(repo=SQLiteRepository())  # Production
```

---

## Decision-Making Framework

### When to Add a New Layer?
**Ask:** Does this responsibility fit an existing layer?
- If NO and it's a new cross-cutting concern → Create new layer
- If YES → Add to existing layer

### When to Create a Service?
**Triggers:**
- Multiple routers duplicate the same business logic
- Operation spans multiple repositories
- Complex validation or business rules
- Need to emit events or trigger side effects

### When to Use Events vs Direct Calls?
**Use Events When:**
- Decoupling is important (dashboard, plugins)
- Multiple subscribers need to react
- Side effects are optional (notification, logging)

**Use Direct Calls When:**
- Operation is synchronous and must complete
- Failure must propagate to caller
- Strong typing needed

---

## API Design Cheat Sheet

### RESTful Endpoint Design
```
GET    /api/v1/heuristics           # List
GET    /api/v1/heuristics/{id}      # Get by ID
POST   /api/v1/heuristics           # Create
PUT    /api/v1/heuristics/{id}      # Update (full)
PATCH  /api/v1/heuristics/{id}      # Update (partial)
DELETE /api/v1/heuristics/{id}      # Delete

# Actions (RPC-style)
POST   /api/v1/heuristics/{id}/promote
POST   /api/v1/workflows/{id}/execute

# Filtering
GET /api/v1/heuristics?domain=testing&is_golden=true&limit=20
```

### Response Format (Standard)
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "version": "1.0",
    "timestamp": "2026-01-05T12:34:56Z"
  }
}
```

### Error Format (Standard)
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "field": "confidence",
    "details": { ... }
  }
}
```

---

## Testing Strategy (One-Page)

### Test Pyramid

```
        ┌─────────┐
        │   E2E   │  ← Few, slow (full workflows)
        └─────────┘
      ┌─────────────┐
      │ Integration │  ← Some, medium (cross-layer)
      └─────────────┘
    ┌─────────────────┐
    │      Unit       │  ← Many, fast (isolated)
    └─────────────────┘
```

### What to Test at Each Layer

| Layer | Test Type | Example |
|-------|-----------|---------|
| Services | Unit | `test_promote_requires_high_confidence()` |
| Repositories | Integration | `test_save_persists_to_database()` |
| API Endpoints | Integration | `test_promote_endpoint_returns_200()` |
| Workflows | E2E | `test_complete_code_review_workflow()` |
| Domain Models | Unit | `test_heuristic_validation()` |

### Critical Tests to Add

```python
# 1. Sync/Async Parity
async def test_sync_async_produce_same_results():
    sync_result = sync_qs.build_context("query")
    async_result = await async_qs.build_context("query")
    assert sync_result == async_result

# 2. Concurrent Writes
async def test_concurrent_writes_no_corruption():
    await asyncio.gather(*[write_heuristic(i) for i in range(100)])
    assert len(await repo.find_all()) == 100

# 3. API Contract Stability
def test_api_v1_response_schema():
    response = client.get("/api/v1/heuristics/1")
    assert "id" in response.json()
    assert isinstance(response.json()["confidence"], float)
```

---

## Migration Roadmap (4 Weeks)

### Week 1: Foundation
- [ ] Add connection pooling to SQLite
- [ ] Create service interfaces (IHeuristicsService, etc.)
- [ ] Add structured logging
- [ ] Write ADRs for key decisions

### Week 2: Unification
- [ ] Implement async core (query.py becomes facade)
- [ ] Merge coordinator/ into src/coordination/
- [ ] Update all internal imports

### Week 3: Service Extraction
- [ ] Extract HeuristicsService from routers
- [ ] Create repository pattern for data access
- [ ] Add event bus infrastructure

### Week 4: API Versioning
- [ ] Prefix routes with /api/v1/
- [ ] Add OpenAPI documentation
- [ ] Create public SDK (library/sdk/)

---

## Common Pitfalls to Avoid

### 1. Anemic Domain Models
**Bad:**
```python
class Heuristic:
    id: int
    confidence: float  # Just data, no behavior
```

**Good:**
```python
class Heuristic:
    def validate_promotion(self):
        if self.confidence < 0.8:
            raise ValueError("Too low")
```

### 2. Fat Controllers
**Bad:**
```python
@router.post("/promote/{id}")
def promote(id: int):
    h = Heuristic.get_by_id(id)  # Data access in controller
    if h.confidence < 0.8:        # Business logic in controller
        raise HTTPException(400)
    h.is_golden = True
    h.save()
    websocket.broadcast(...)      # Side effects in controller
```

**Good:**
```python
@router.post("/api/v1/promote/{id}")
async def promote(id: int, service: HeuristicsService = Depends()):
    return await service.promote_to_golden(id)  # Delegate to service
```

### 3. Circular Dependencies
**Bad:**
```python
# coordinator/blackboard.py
from conductor import Conductor  # ← Import from higher layer

# src/conductor/conductor.py
from coordinator.blackboard import Blackboard  # ← Circular!
```

**Good:**
```python
# Use dependency injection
class Conductor:
    def __init__(self, blackboard: IBlackboard):
        self.blackboard = blackboard  # Interface, not concrete class
```

### 4. No Versioning
**Bad:**
```python
@router.get("/heuristics")  # What happens when schema changes?
```

**Good:**
```python
@router.get("/api/v1/heuristics")  # v2 can coexist
```

### 5. Direct Database Access in Routes
**Bad:**
```python
@router.get("/heuristics")
def get_heuristics():
    return Heuristic.select()  # ORM in controller
```

**Good:**
```python
@router.get("/api/v1/heuristics")
async def get_heuristics(service: HeuristicsService = Depends()):
    return await service.list_heuristics()
```

---

## When to Refactor vs When to Rebuild

### Refactor (Recommended)
- Core logic is sound
- Architecture is recoverable
- Users depend on current API
- **ELF is in this category**

### Rebuild (Not Recommended)
- Fundamental design flaws
- Tech stack is obsolete
- Cheaper to start over

---

## Quick Wins (1-3 Days Each)

1. **Add Connection Pooling** (1 day)
   - Immediate performance improvement
   - Low risk, high reward

2. **API Versioning** (1 day)
   - Prefix routes with /api/v1/
   - Prevents future breaking changes

3. **Extract HeuristicsService** (2 days)
   - Move logic out of routers
   - Template for other services

4. **Standardize Imports** (1 day)
   - Search/replace to elf.* namespace
   - Easier future refactoring

---

## Resources

- **Full Review:** `docs/architecture/ARCHITECTURAL-REVIEW-2026-01-05.md`
- **Target Structure:** `docs/architecture/RECOMMENDED-STRUCTURE.md`
- **Refactor Plan:** `ELF-REFACTOR-PLAN-v2.md`
- **Architecture Patterns:** https://martinfowler.com/architecture/
- **Clean Architecture:** Robert C. Martin (Uncle Bob)
- **Domain-Driven Design:** Eric Evans

---

## Questions? Decision Tree

**Q: Where should this code go?**
```
Is it HTTP handling? → apps/dashboard/backend/api/v1/
Is it business logic? → elf/services/
Is it domain rule?    → elf/domain/
Is it data access?    → elf/persistence/repositories/
Is it infrastructure? → elf/infrastructure/
Is it public API?     → library/sdk/
```

**Q: Should I create a new service?**
```
Does it orchestrate multiple repos? → Yes
Does it enforce business rules?     → Yes
Does it emit events?                → Yes
Is it just CRUD?                    → Maybe (repository might suffice)
```

**Q: Async or sync?**
```
Is it new code?           → Async (elf.core.*)
Is it external-facing?    → Provide both (facade pattern)
Is it I/O intensive?      → Async
Is it CPU-bound?          → Sync is fine
```

---

**Last Updated:** 2026-01-05
**Maintainer:** Architecture Team
**Review Frequency:** Monthly
