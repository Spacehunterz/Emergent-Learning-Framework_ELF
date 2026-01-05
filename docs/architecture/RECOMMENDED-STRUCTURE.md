# Recommended Architecture Structure

## Overview

This document defines the target architecture for the Emergent Learning Framework after addressing the issues identified in the architectural review.

---

## Directory Structure (Target State)

```
emergent-learning/
├── src/elf/                          # Main package namespace
│   ├── __init__.py                   # Public API exports
│   │
│   ├── core/                         # Core business logic (async)
│   │   ├── query.py                  # Canonical async query system
│   │   ├── coordination.py           # Unified orchestrator
│   │   └── learning.py               # Learning extraction
│   │
│   ├── sync/                         # Synchronous facades
│   │   ├── query.py                  # Sync wrapper for query
│   │   └── coordination.py           # Sync wrapper for coordination
│   │
│   ├── services/                     # Service layer (business logic)
│   │   ├── interfaces.py             # Service contracts
│   │   ├── heuristics_service.py
│   │   ├── learning_service.py
│   │   ├── workflow_service.py
│   │   └── analytics_service.py
│   │
│   ├── domain/                       # Domain models and logic
│   │   ├── models.py                 # Heuristic, Learning, etc.
│   │   ├── agents.py                 # Agent personalities
│   │   └── workflows.py              # Workflow definitions
│   │
│   ├── persistence/                  # Data access layer
│   │   ├── repositories/             # Repository pattern
│   │   │   ├── base.py              # Base repository
│   │   │   ├── heuristics.py
│   │   │   ├── learnings.py
│   │   │   └── sessions.py
│   │   ├── database.py              # Connection pooling
│   │   └── migrations.py            # Schema versioning
│   │
│   ├── coordination/                 # Agent coordination (unified)
│   │   ├── orchestrator.py          # Main coordination interface
│   │   ├── workflows/               # Persistent workflows
│   │   │   ├── executor.py
│   │   │   ├── scheduler.py
│   │   │   └── graph.py
│   │   ├── realtime/                # Real-time coordination
│   │   │   ├── blackboard.py
│   │   │   └── redis_blackboard.py  # Distributed option
│   │   └── events/                  # Event sourcing
│   │       ├── bus.py
│   │       └── log.py
│   │
│   ├── infrastructure/               # Cross-cutting concerns
│   │   ├── config.py                # Configuration management
│   │   ├── logging.py               # Structured logging
│   │   ├── cache.py                 # Caching layer
│   │   └── security.py              # Security utilities
│   │
│   ├── plugins/                      # Plugin system
│   │   ├── base.py                  # Plugin interface
│   │   ├── registry.py              # Discovery/loading
│   │   └── hooks.py                 # Hook system
│   │
│   └── events/                       # Event-driven architecture
│       ├── types.py                 # Event definitions
│       └── handlers/                # Event handlers
│           ├── learning_handler.py
│           └── notification_handler.py
│
├── apps/                             # Application layer
│   ├── dashboard/                    # Web dashboard
│   │   ├── backend/
│   │   │   ├── main.py              # FastAPI app
│   │   │   ├── api/v1/              # Versioned API
│   │   │   │   ├── heuristics.py
│   │   │   │   ├── learnings.py
│   │   │   │   ├── workflows.py
│   │   │   │   └── analytics.py
│   │   │   ├── services/            # Application services
│   │   │   │   └── (delegates to elf.services)
│   │   │   ├── websocket/           # WebSocket handlers
│   │   │   └── middleware/          # Custom middleware
│   │   └── frontend/                # React SPA
│   │       └── src/
│   │
│   └── cli/                          # Command-line interface
│       ├── main.py                   # Entry point
│       └── commands/                 # Subcommands
│           ├── checkin.py
│           ├── search.py
│           └── swarm.py
│
├── library/                          # Public SDK for external use
│   ├── sdk/                          # Python client library
│   │   ├── __init__.py              # ELFClient export
│   │   ├── client.py                # Main client interface
│   │   ├── async_client.py          # Async client
│   │   └── types.py                 # Public types
│   │
│   └── plugins/                      # Example plugins
│       ├── talkinhead/              # Avatar integration
│       └── vscode/                  # VS Code extension
│
├── scripts/                          # Operational scripts
│   ├── setup/                        # Installation
│   ├── migration/                    # Data migration
│   └── maintenance/                  # Cleanup, backup
│
├── tests/                            # Test suite
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   ├── e2e/                          # End-to-end tests
│   ├── performance/                  # Load/stress tests
│   └── contracts/                    # API contract tests
│
├── docs/                             # Documentation
│   ├── architecture/                 # ADRs, diagrams
│   ├── api/                          # API reference
│   ├── guides/                       # User guides
│   └── development/                  # Dev setup
│
└── memory/                           # Data storage
    ├── index.db                      # SQLite database
    ├── sessions/                     # Session logs
    └── heuristics/                   # Markdown exports
```

---

## Layer Responsibilities

### 1. Core Layer (`src/elf/core/`)
**Responsibility:** Business logic, domain rules, async-first implementations

**Key Principles:**
- All logic is async
- No external dependencies (HTTP, filesystem, etc.)
- Pure business logic
- Testable in isolation

**Example:**
```python
# src/elf/core/query.py
class AsyncQuerySystem:
    """Canonical async implementation."""

    async def build_context(
        self,
        query: str,
        domain: Optional[str] = None
    ) -> str:
        # Pure logic, delegates to repositories
        heuristics = await self.heuristic_repo.find_by_domain(domain)
        learnings = await self.learning_repo.find_relevant(query)
        return self._format_context(heuristics, learnings)
```

### 2. Sync Layer (`src/elf/sync/`)
**Responsibility:** Backward-compatible synchronous facades

**Key Principles:**
- Thin wrappers around async core
- Use `asyncio.run()` to bridge sync/async
- Maintain identical API surface
- No business logic

**Example:**
```python
# src/elf/sync/query.py
class QuerySystem:
    """Sync facade for backward compatibility."""

    def build_context(self, query: str, **kwargs) -> str:
        return asyncio.run(
            self._async.build_context(query, **kwargs)
        )
```

### 3. Service Layer (`src/elf/services/`)
**Responsibility:** Orchestrate business operations, enforce rules

**Key Principles:**
- Interface-based design
- Transaction boundaries
- Use repositories for data access
- Coordinate multiple domain operations

**Example:**
```python
# src/elf/services/heuristics_service.py
class HeuristicsService:
    def __init__(
        self,
        heuristics_repo: IHeuristicsRepository,
        event_bus: EventBus
    ):
        self.repo = heuristics_repo
        self.events = event_bus

    async def promote_to_golden(self, heuristic_id: int) -> Heuristic:
        # Business logic
        heuristic = await self.repo.find_by_id(heuristic_id)

        if heuristic.confidence < 0.8:
            raise ValueError("Confidence too low")

        heuristic.is_golden = True
        heuristic.promoted_at = datetime.now()

        # Persist
        await self.repo.save(heuristic)

        # Notify
        await self.events.publish(HeuristicPromoted(heuristic))

        return heuristic
```

### 4. Domain Layer (`src/elf/domain/`)
**Responsibility:** Core domain models and business rules

**Key Principles:**
- Rich domain models (not anemic)
- Domain-driven design patterns
- Encapsulate business invariants
- No infrastructure dependencies

**Example:**
```python
# src/elf/domain/models.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Heuristic:
    """Domain model with business logic."""

    id: int
    domain: str
    rule: str
    confidence: float
    is_golden: bool = False

    def validate_promotion(self) -> None:
        """Business rule: golden requires high confidence."""
        if self.confidence < 0.8:
            raise ValueError(
                f"Confidence {self.confidence} too low for promotion"
            )

    def apply_feedback(self, successful: bool) -> None:
        """Update confidence based on validation."""
        if successful:
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            self.confidence = max(0.0, self.confidence - 0.1)
```

### 5. Persistence Layer (`src/elf/persistence/`)
**Responsibility:** Data access, storage abstraction

**Key Principles:**
- Repository pattern (one per aggregate)
- No business logic
- Abstract storage implementation
- Connection pooling and transactions

**Example:**
```python
# src/elf/persistence/repositories/heuristics.py
class HeuristicsRepository(IHeuristicsRepository):
    def __init__(self, db_pool: DatabasePool):
        self.db = db_pool

    async def find_by_id(self, id: int) -> Optional[Heuristic]:
        async with self.db.acquire() as conn:
            row = await conn.fetchone(
                "SELECT * FROM heuristics WHERE id = ?",
                (id,)
            )
            return self._map_to_domain(row) if row else None

    async def save(self, heuristic: Heuristic) -> None:
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE heuristics
                SET confidence = ?, is_golden = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    heuristic.confidence,
                    heuristic.is_golden,
                    datetime.now(),
                    heuristic.id
                )
            )
```

### 6. Coordination Layer (`src/elf/coordination/`)
**Responsibility:** Agent orchestration, workflow execution

**Key Principles:**
- Unified interface for all coordination
- Support both persistent and real-time patterns
- Event sourcing for audit trail
- Distributed-ready design

**Example:**
```python
# src/elf/coordination/orchestrator.py
class Orchestrator:
    """Unified coordination interface."""

    def __init__(
        self,
        persistent: bool = True,   # SQLite workflows
        realtime: bool = True       # Blackboard coordination
    ):
        if persistent:
            self.workflow_executor = WorkflowExecutor(db)
        if realtime:
            self.blackboard = Blackboard()

    async def run_workflow(
        self,
        workflow_id: str,
        context: dict
    ) -> WorkflowResult:
        # Load workflow definition
        workflow = await self.workflow_executor.load(workflow_id)

        # Execute nodes in order
        for node in workflow.nodes:
            await self._execute_node(node, context)

        # Record to event log
        await self.event_log.append(WorkflowCompleted(workflow_id))

        return WorkflowResult(status="completed")
```

### 7. Infrastructure Layer (`src/elf/infrastructure/`)
**Responsibility:** Cross-cutting concerns, technical services

**Key Principles:**
- Configuration management
- Logging and monitoring
- Caching strategies
- Security utilities

**Example:**
```python
# src/elf/infrastructure/config.py
class ELFConfig:
    """Centralized configuration."""

    _instance = None

    @classmethod
    def initialize(
        cls,
        base_path: Optional[Path] = None,
        env: str = "production"
    ) -> 'ELFConfig':
        if cls._instance is None:
            cls._instance = cls._load_config(base_path, env)
        return cls._instance

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.base_path}/memory/index.db"

    @property
    def redis_url(self) -> Optional[str]:
        return os.getenv("ELF_REDIS_URL")
```

### 8. Application Layer (`apps/`)
**Responsibility:** User-facing applications (UI, CLI, API)

**Key Principles:**
- Thin adapters over services
- API versioning (v1, v2, etc.)
- Input validation and transformation
- Error handling and user feedback

**Example:**
```python
# apps/dashboard/backend/api/v1/heuristics.py
from fastapi import APIRouter, Depends, HTTPException
from elf.services import HeuristicsService, IHeuristicsService

router = APIRouter(prefix="/api/v1/heuristics", tags=["heuristics-v1"])

@router.post("/{id}/promote")
async def promote_heuristic(
    id: int,
    service: IHeuristicsService = Depends(get_heuristics_service)
):
    """
    Promote heuristic to golden rule.

    **Requires:** Confidence >= 0.8
    **Version:** 1.0 (stable)
    """
    try:
        heuristic = await service.promote_to_golden(id)
        return {"success": True, "heuristic": heuristic.dict()}
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
```

### 9. Library/SDK Layer (`library/`)
**Responsibility:** Public API for external consumers

**Key Principles:**
- Stable, versioned interface
- Comprehensive documentation
- Minimal dependencies
- Easy to use

**Example:**
```python
# library/sdk/client.py
class ELFClient:
    """Public SDK for external projects."""

    @classmethod
    async def create(
        cls,
        base_path: str = "~/.claude/emergent-learning"
    ) -> 'ELFClient':
        config = ELFConfig.initialize(Path(base_path).expanduser())
        return cls(config)

    async def get_golden_rules(
        self,
        domain: Optional[str] = None
    ) -> List[Heuristic]:
        """Fetch golden rules, optionally filtered by domain."""
        return await self._heuristics_service.get_golden_rules(domain)

    async def record_learning(
        self,
        title: str,
        summary: str,
        domain: str
    ) -> Learning:
        """Record a new learning."""
        return await self._learning_service.create(title, summary, domain)
```

---

## Dependency Flow

### Correct Dependency Direction

```
┌─────────────────────────────────────────────┐
│        Applications (apps/, library/)       │
│                                             │
│  ┌─────────────┐         ┌──────────────┐ │
│  │  Dashboard  │         │  CLI Client  │ │
│  └─────────────┘         └──────────────┘ │
└─────────────────────────────────────────────┘
            │                        │
            └────────┬───────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│          Services (src/elf/services/)       │
│                                             │
│  Orchestrate business operations            │
│  Use repositories for data                  │
└─────────────────────────────────────────────┘
            │                        │
            ▼                        ▼
┌──────────────────┐    ┌────────────────────┐
│ Domain Models    │    │  Coordination      │
│ (src/elf/domain/)│    │ (src/elf/coord/)   │
│                  │    │                    │
│ Business rules   │    │ Workflows          │
└──────────────────┘    └────────────────────┘
            │                        │
            └────────┬───────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│      Persistence (src/elf/persistence/)     │
│                                             │
│  Repositories, database access              │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│    Infrastructure (src/elf/infrastructure/) │
│                                             │
│  Config, logging, caching, security         │
└─────────────────────────────────────────────┘
```

**Rules:**
1. Higher layers depend on lower layers
2. Lower layers never import from higher layers
3. Domain layer has minimal dependencies
4. Infrastructure is used by all layers via dependency injection

---

## API Design Standards

### RESTful API Conventions

```python
# Version prefix
/api/v1/heuristics

# Plural resource names
/api/v1/heuristics/{id}

# Sub-resources
/api/v1/workflows/{id}/nodes

# Actions as verbs
POST /api/v1/heuristics/{id}/promote
POST /api/v1/workflows/{id}/execute

# Query parameters for filtering
GET /api/v1/heuristics?domain=testing&is_golden=true

# Pagination
GET /api/v1/learnings?limit=20&offset=40
```

### Response Format

```json
{
  "success": true,
  "data": {
    "id": 123,
    "domain": "testing",
    "rule": "Always mock external APIs",
    "confidence": 0.95
  },
  "meta": {
    "version": "1.0",
    "timestamp": "2026-01-05T12:34:56Z"
  }
}
```

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Confidence must be between 0 and 1",
    "field": "confidence",
    "value": 1.5
  },
  "meta": {
    "version": "1.0",
    "timestamp": "2026-01-05T12:34:56Z"
  }
}
```

---

## Event-Driven Architecture

### Event Types

```python
# src/elf/events/types.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class EventType(Enum):
    HEURISTIC_CREATED = "heuristic.created"
    HEURISTIC_PROMOTED = "heuristic.promoted"
    LEARNING_RECORDED = "learning.recorded"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    AGENT_REGISTERED = "agent.registered"

@dataclass
class Event:
    """Base event class."""
    type: EventType
    timestamp: datetime
    data: dict
    correlation_id: str

@dataclass
class HeuristicPromoted(Event):
    """Emitted when heuristic becomes golden."""
    heuristic_id: int
    domain: str
    confidence: float
```

### Event Bus Usage

```python
# Publish events
await event_bus.publish(HeuristicPromoted(
    heuristic_id=123,
    domain="testing",
    confidence=0.95
))

# Subscribe to events
async def update_dashboard(event: HeuristicPromoted):
    await websocket.broadcast({
        "type": "heuristic_promoted",
        "data": event.dict()
    })

event_bus.subscribe(EventType.HEURISTIC_PROMOTED, update_dashboard)
```

---

## Plugin System

### Plugin Interface

```python
# src/elf/plugins/base.py
from abc import ABC, abstractmethod

class ELFPlugin(ABC):
    """Base class for all plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""

    @abstractmethod
    async def initialize(self, elf: 'ELFClient') -> None:
        """Called when plugin is loaded."""

    @abstractmethod
    async def on_event(self, event: Event) -> None:
        """Handle ELF events."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown."""
```

### Example Plugin

```python
# library/plugins/talkinhead/plugin.py
class TalkinHeadPlugin(ELFPlugin):
    @property
    def name(self) -> str:
        return "talkinhead"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, elf: 'ELFClient'):
        self.elf = elf
        self.avatar = TalkinHead()
        await self.avatar.start()

    async def on_event(self, event: Event):
        if event.type == EventType.WORKFLOW_COMPLETED:
            await self.avatar.celebrate()

    async def shutdown(self):
        await self.avatar.stop()
```

---

## Migration Strategy

### Step 1: Introduce Namespace (Week 1)
```bash
# Create elf package
mkdir -p src/elf
mv src/query src/elf/query
mv src/conductor src/elf/coordination

# Update imports
sed -i 's/from query import/from elf.query import/g' **/*.py
```

### Step 2: Extract Services (Week 2)
```python
# Create service layer
src/elf/services/heuristics_service.py

# Migrate logic from routers
apps/dashboard/backend/routers/heuristics.py
  → calls HeuristicsService instead of direct DB access
```

### Step 3: Add Repositories (Week 3)
```python
# Create repository interfaces
src/elf/persistence/repositories/base.py
src/elf/persistence/repositories/heuristics.py

# Services use repositories
HeuristicsService(heuristics_repo=HeuristicsRepository())
```

### Step 4: Event Bus (Week 4)
```python
# Add event infrastructure
src/elf/events/bus.py

# Services publish events
await event_bus.publish(HeuristicPromoted(...))

# Dashboard subscribes
event_bus.subscribe(EventType.HEURISTIC_PROMOTED, update_ui)
```

---

## Testing Strategy

### Unit Tests (Fast, Isolated)
```python
# tests/unit/test_heuristics_service.py
@pytest.mark.asyncio
async def test_promote_requires_high_confidence():
    # Arrange
    repo = Mock(IHeuristicsRepository)
    repo.find_by_id.return_value = Heuristic(
        id=1, confidence=0.5, is_golden=False
    )
    service = HeuristicsService(repo)

    # Act & Assert
    with pytest.raises(ValueError, match="Confidence too low"):
        await service.promote_to_golden(1)
```

### Integration Tests (Cross-Layer)
```python
# tests/integration/test_heuristic_promotion.py
@pytest.mark.asyncio
async def test_end_to_end_promotion(test_db):
    # Real database, real services
    config = ELFConfig(database_url=test_db)
    client = await ELFClient.create(config)

    # Create heuristic
    h = await client.create_heuristic(
        domain="test", rule="test", confidence=0.9
    )

    # Promote
    promoted = await client.promote_to_golden(h.id)

    # Verify
    assert promoted.is_golden
    assert promoted.promoted_at is not None
```

### Contract Tests (API Stability)
```python
# tests/contracts/test_api_v1.py
def test_heuristic_response_schema():
    """Ensure v1 API contract is maintained."""
    response = client.get("/api/v1/heuristics/1")

    # Must have these fields
    assert "id" in response.json()
    assert "domain" in response.json()
    assert "confidence" in response.json()

    # Types must match
    assert isinstance(response.json()["confidence"], float)
```

---

## Summary

This architecture provides:

1. **Clear Separation** - Each layer has distinct responsibility
2. **Testability** - Layers can be tested in isolation
3. **Scalability** - Ready for distributed deployment
4. **Maintainability** - Easy to understand and modify
5. **Extensibility** - Plugin system for additions
6. **Stability** - Versioned APIs prevent breaking changes

**Next Steps:**
1. Review with team
2. Begin Step 1 migration (introduce namespace)
3. Update documentation
4. Train developers on new patterns
