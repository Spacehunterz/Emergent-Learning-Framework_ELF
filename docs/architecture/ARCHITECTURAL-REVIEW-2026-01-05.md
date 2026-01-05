# Architectural Review: Emergent Learning Framework
**Date:** 2026-01-05
**Reviewer:** Software Architect Agent
**Version:** 0.3.2
**Impact:** HIGH - Critical structural issues identified

---

## Executive Summary

The Emergent Learning Framework exhibits a hybrid architecture combining monolithic scripts, modular components, and distributed coordination patterns. While the conceptual design is sound, the implementation reveals significant architectural debt across module boundaries, inconsistent separation of concerns, and duplicated coordination logic.

### Critical Findings

1. **Dual Query System Implementation** - Sync and async versions coexist with different APIs
2. **Blurred Service Boundaries** - src/, apps/, library/, coordinator/ have overlapping responsibilities
3. **Inconsistent Dependency Management** - Import patterns vary wildly across codebase
4. **No Clear API Contract Layer** - Internal and external APIs lack formal definitions
5. **Coordination Logic Scattered** - Blackboard, Conductor, and event systems overlap

**Architecture Integrity: 6.5/10**
**Scalability Rating: 5/10**
**Maintainability: 6/10**

---

## 1. Current Architecture Overview

### 1.1 Directory Structure Analysis

```
emergent-learning/
├── src/                    # Core framework (mixed responsibilities)
│   ├── query/             # Data access layer (DUPLICATED: sync + async)
│   ├── agents/            # Agent personalities (domain logic)
│   ├── conductor/         # Workflow orchestration
│   ├── hooks/             # Event handlers (tightly coupled)
│   ├── skills/            # Reusable capabilities
│   └── watcher/           # Background monitoring
│
├── apps/                  # Application layer
│   └── dashboard/         # Web UI + FastAPI backend
│       ├── backend/       # REST API + WebSocket
│       └── frontend/      # React SPA
│
├── coordinator/           # Multi-agent coordination (overlaps conductor)
│   ├── blackboard.py     # Real-time state management
│   ├── event_log.py      # Append-only event stream
│   └── dependency_graph.py
│
├── library/               # Reusable components (unclear boundaries)
│   ├── commands/         # CLI commands
│   ├── plugins/          # Extension points
│   └── skills/           # Duplicates src/skills
│
├── scripts/              # Operational utilities
├── tools/                # Setup and maintenance
└── memory/               # Persistent knowledge store
```

### 1.2 Architectural Layers

**Current State:**
```
┌─────────────────────────────────────────┐
│         Applications (apps/)            │
│  ┌─────────────┐    ┌──────────────┐  │
│  │  Dashboard  │    │ CLI Commands │  │
│  └─────────────┘    └──────────────┘  │
└─────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────┐
│     Service Layer (UNCLEAR)             │
│  ┌──────────┐  ┌──────────┐           │
│  │ Conductor│  │Blackboard│  ← OVERLAP│
│  └──────────┘  └──────────┘           │
└─────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────┐
│      Data Access (src/query/)           │
│  ┌──────────┐  ┌──────────┐           │
│  │ query.py │  │ core.py  │  ← DUPLICATION
│  │  (sync)  │  │ (async)  │           │
│  └──────────┘  └──────────┘           │
└─────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────┐
│         Persistence Layer               │
│  SQLite (Peewee ORM) + JSON Files       │
└─────────────────────────────────────────┘
```

**Problem:** Layers are not clearly separated. Service logic bleeds into data access, coordination logic duplicates across modules, and applications directly access persistence.

---

## 2. Separation of Concerns Analysis

### 2.1 src/ Directory - Core Framework

**Current Issues:**

1. **query/ Module - CRITICAL DUPLICATION**
   - `query.py` (2620 lines) - Synchronous implementation
   - `core.py` (421 lines) - Async implementation with mixins
   - Both are complete, independent implementations
   - External callers depend on sync API
   - Internal code migrating to async API

   **Impact:** HIGH - Creates maintenance burden, drift risk, unclear single source of truth

   **Recommendation:**
   ```python
   # Strategy: Async core with sync facade
   # query.py becomes thin wrapper:

   class QuerySystem:
       """Sync wrapper for backward compatibility."""

       def __init__(self, **kwargs):
           self._async_qs = None
           self._init_args = kwargs

       def build_context(self, query: str, **kwargs):
           return asyncio.run(self._get_async().build_context(query, **kwargs))

       def _get_async(self):
           if not self._async_qs:
               self._async_qs = asyncio.run(
                   AsyncQuerySystem.create(**self._init_args)
               )
           return self._async_qs
   ```

2. **conductor/ vs coordinator/ - OVERLAP**
   - `src/conductor/` - Workflow orchestration with SQLite persistence
   - Root `coordinator/` - Real-time blackboard coordination
   - Both handle agent coordination but with different paradigms
   - No clear boundary on when to use which

   **Impact:** MEDIUM - Confusion about coordination patterns

   **Recommendation:** Merge into single coordination service:
   ```
   src/coordination/
   ├── workflows/          # Persistent workflow definitions
   ├── realtime/           # Blackboard for live coordination
   ├── orchestrator.py     # Unified orchestration interface
   └── event_stream.py     # Event sourcing for audit trail
   ```

3. **hooks/ - Tight Coupling**
   - Event handlers directly import core modules
   - No dependency injection or plugin architecture
   - Difficult to test in isolation

   **Impact:** MEDIUM - Reduces testability and extensibility

   **Recommendation:** Implement hook registry pattern:
   ```python
   # src/hooks/registry.py
   class HookRegistry:
       def __init__(self, query_system: QuerySystem):
           self.qs = query_system
           self._hooks = {}

       def register(self, event: str, handler: Callable):
           self._hooks.setdefault(event, []).append(handler)

       async def trigger(self, event: str, context: dict):
           for handler in self._hooks.get(event, []):
               await handler(self.qs, context)
   ```

### 2.2 apps/ Directory - Application Layer

**Current State:** Well-structured but lacks API versioning

**Dashboard Architecture:**
```
apps/dashboard/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── routers/             # API endpoints (12 routers)
│   │   ├── analytics.py
│   │   ├── heuristics.py
│   │   ├── game.py         ← Domain logic in API layer!
│   │   └── ...
│   ├── utils/               # Shared utilities
│   └── models.py            # Peewee ORM models
└── frontend/
    └── src/components/      # React components
```

**Issues:**

1. **Domain Logic in Routers**
   - `routers/game.py` contains game mechanics
   - Business logic mixed with HTTP handling
   - Violates Single Responsibility Principle

2. **No API Versioning**
   - Routes lack `/api/v1/` prefix
   - Future breaking changes will be difficult

3. **Direct Database Access**
   - Routers query Peewee models directly
   - No repository pattern or service layer
   - Difficult to swap persistence implementation

**Recommendation:**

```python
# apps/dashboard/backend/services/heuristics_service.py
class HeuristicsService:
    """Business logic for heuristics management."""

    def __init__(self, repository: HeuristicsRepository):
        self.repo = repository

    async def get_golden_rules(self) -> List[Heuristic]:
        return await self.repo.find_all(is_golden=True)

    async def promote_to_golden(self, heuristic_id: int) -> bool:
        heuristic = await self.repo.find_by_id(heuristic_id)
        if heuristic.confidence < 0.8:
            raise ValueError("Confidence too low for promotion")
        heuristic.is_golden = True
        return await self.repo.save(heuristic)

# apps/dashboard/backend/routers/heuristics.py
@router.post("/api/v1/heuristics/{id}/promote")
async def promote_heuristic(
    id: int,
    service: HeuristicsService = Depends(get_heuristics_service)
):
    """HTTP endpoint - thin wrapper around service."""
    try:
        await service.promote_to_golden(id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(400, str(e))
```

### 2.3 library/ Directory - Reusable Components

**Current Issues:**

1. **Unclear Purpose**
   - `library/skills/` duplicates `src/skills/`
   - `library/commands/` vs `src/query/cli.py` - overlap
   - No clear distinction from src/

2. **Plugin System Underutilized**
   - `library/plugins/agent-coordination/` exists but minimal adoption
   - Hook mechanism not leveraged elsewhere

**Recommendation:**

Clarify library/ as the **public SDK layer**:

```
library/
├── sdk/                    # Public Python API
│   ├── __init__.py        # Main export
│   ├── client.py          # ELF client interface
│   └── types.py           # Public data types
│
├── plugins/               # Extension framework
│   ├── base.py           # Plugin interface
│   ├── registry.py       # Discovery/loading
│   └── examples/
│
└── cli/                   # Command-line tools
    ├── commands/         # Subcommands
    └── main.py           # Entry point
```

Usage:
```python
# External projects using ELF as library
from elf.sdk import ELFClient

client = await ELFClient.create(base_path="~/.claude/emergent-learning")
golden_rules = await client.get_golden_rules(domain="testing")
```

### 2.4 coordinator/ vs src/conductor/ - Critical Overlap

**Analysis:**

| Feature | coordinator/blackboard.py | src/conductor/conductor.py |
|---------|--------------------------|----------------------------|
| Purpose | Real-time agent coordination | Workflow orchestration |
| Storage | .coordination/blackboard.json | SQLite workflows table |
| Pattern | Shared state | Command execution |
| Concurrency | File locking | SQLite transactions |
| Persistence | Transient | Historical |

**The Problem:** Both coordinate agents but with different philosophies:
- Blackboard: "Agents share state in real-time"
- Conductor: "Workflows execute nodes sequentially"

**Impact:** HIGH - Developers must understand two coordination models

**Recommendation:** Unified Coordination Architecture

```
src/coordination/
├── __init__.py
├── orchestrator.py        # Unified interface
├── models.py             # Workflow, Node, Edge definitions
├── persistence/
│   ├── sqlite_store.py   # Historical workflows
│   └── memory_store.py   # Real-time state
├── execution/
│   ├── executor.py       # Node execution engine
│   └── scheduler.py      # Dependency resolution
└── messaging/
    ├── blackboard.py     # Shared state
    └── events.py         # Event bus
```

Usage:
```python
# Unified API
from coordination import Orchestrator

orchestrator = Orchestrator(
    persistent=True,       # Use SQLite for history
    realtime=True          # Use blackboard for live coordination
)

# Define workflow
workflow = orchestrator.create_workflow("code-review")
workflow.add_node("analyze", agent="architect", prompt="Review {file}")
workflow.add_node("suggest", agent="creative", prompt="Propose improvements")
workflow.add_edge("analyze", "suggest", condition="analysis.score < 0.8")

# Execute (uses both systems transparently)
result = await orchestrator.run(workflow, context={"file": "src/main.py"})
```

---

## 3. Module Boundaries and Dependencies

### 3.1 Import Pattern Analysis

**Current State - Inconsistent Import Strategies:**

```python
# Pattern 1: Try/except imports (query/)
try:
    from query.models import Learning
except ImportError:
    from models import Learning

# Pattern 2: Relative imports (dashboard/backend/)
from .utils import get_db
from utils.database import initialize_database

# Pattern 3: sys.path manipulation (conductor/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "coordinator"))
from blackboard import Blackboard

# Pattern 4: Conditional imports (hooks/)
try:
    from query import QuerySystem
except ImportError:
    QuerySystem = None
```

**Problems:**

1. **No single import strategy** - Each module solves imports differently
2. **Circular dependency risk** - sys.path manipulation indicates coupling
3. **Fragile to refactoring** - Moving files breaks imports
4. **Testing difficulty** - Hard to mock dependencies

**Recommendation:** Establish clear module hierarchy:

```python
# pyproject.toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["elf*"]

# All imports from elf namespace
from elf.query import QuerySystem
from elf.coordination import Orchestrator
from elf.persistence import Heuristic, Learning
```

### 3.2 Dependency Graph

**High-Level Dependencies:**

```
apps/dashboard/backend/  →  src/query/
                         →  coordinator/

src/conductor/          →  coordinator/blackboard
                        →  src/query/

src/hooks/              →  src/query/
                        →  coordinator/

coordinator/            →  (no dependencies - good!)

library/                →  src/query/  ← Should be reversed!
```

**Violations:**

1. **Library depends on src/** - Should be opposite
2. **Circular potential** - conductor → coordinator → (could import conductor)
3. **Apps depend on internals** - Dashboard imports src/ directly

**Ideal Dependency Flow:**

```
Applications (apps/)
     ↓
Services (src/services/)
     ↓
Domain Logic (src/domain/)
     ↓
Repositories (src/persistence/)
     ↓
Infrastructure (src/infrastructure/)

Library (library/) - Facade over all layers
```

### 3.3 Path Resolution Architecture

**Current - elf_paths.py:**

```python
def get_base_path(start: Optional[Path] = None) -> Path:
    # 1. Check ELF_BASE_PATH env var
    # 2. Search for repo markers (.git, .coordination)
    # 3. Fall back to ~/.claude/emergent-learning
    # 4. Migrate legacy data if found
```

**Issues:**

1. **Auto-migration logic in path resolver** - Side effects!
2. **No caching** - Filesystem searches on every call
3. **Implicit behavior** - Migration happens silently

**Recommendation:**

```python
# src/elf/config.py
class ELFConfig:
    """Centralized configuration with explicit initialization."""

    _instance = None

    @classmethod
    def initialize(cls, base_path: Optional[Path] = None,
                   auto_migrate: bool = True) -> 'ELFConfig':
        if cls._instance is None:
            cls._instance = cls._resolve_config(base_path, auto_migrate)
        return cls._instance

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def memory_path(self) -> Path:
        return self._base_path / "memory"

    # No side effects in property access

# Usage
config = ELFConfig.initialize()  # Explicit initialization
db_path = config.memory_path / "index.db"
```

---

## 4. API Design Patterns

### 4.1 Current API Inconsistencies

**Query API:**

```python
# Sync version (query.py)
qs = QuerySystem()
result = qs.build_context("task", domain="testing")

# Async version (core.py)
qs = await QuerySystem.create()
result = await qs.build_context("task", domain="testing")
await qs.cleanup()
```

**Coordination APIs:**

```python
# Blackboard (sync)
bb = Blackboard()
bb.register_agent("agent-1", "Analyze code")

# Conductor (sync)
conductor = Conductor(db_path)
run_id = conductor.create_run("workflow-1")

# Both coordinate agents but incompatible APIs!
```

**Dashboard API:**

```python
# REST endpoint
GET /api/heuristics?domain=testing&limit=10

# WebSocket
ws://localhost:8888/ws
{"type": "subscribe", "topic": "heuristics"}

# No versioning, no API specification
```

### 4.2 Recommended API Architecture

**1. Unified Async Core with Sync Facades**

```python
# elf/core/query.py - Canonical async implementation
class AsyncQuerySystem:
    @classmethod
    async def create(cls, config: ELFConfig) -> 'AsyncQuerySystem':
        instance = cls(config)
        await instance._initialize()
        return instance

    async def build_context(self, query: str, **kwargs) -> str:
        # Real implementation

# elf/sync/query.py - Sync facade
class QuerySystem:
    """Synchronous facade for backward compatibility."""

    def __init__(self, config: Optional[ELFConfig] = None):
        self._config = config or ELFConfig.initialize()
        self._async_instance = None

    def build_context(self, query: str, **kwargs) -> str:
        return asyncio.run(self._get_async().build_context(query, **kwargs))

    def _get_async(self) -> AsyncQuerySystem:
        if not self._async_instance:
            self._async_instance = asyncio.run(
                AsyncQuerySystem.create(self._config)
            )
        return self._async_instance
```

**2. Standardized REST API with Versioning**

```python
# apps/dashboard/backend/api/v1/heuristics.py
from fastapi import APIRouter
from elf.services import HeuristicsService

router = APIRouter(prefix="/api/v1", tags=["heuristics-v1"])

@router.get("/heuristics")
async def list_heuristics(
    domain: Optional[str] = None,
    is_golden: Optional[bool] = None,
    limit: int = Query(10, ge=1, le=100),
    service: HeuristicsService = Depends()
) -> HeuristicsListResponse:
    """
    List heuristics with filtering.

    **Version:** 1.0
    **Stability:** Stable
    """
    return await service.list_heuristics(
        domain=domain,
        is_golden=is_golden,
        limit=limit
    )

# OpenAPI spec auto-generated at /api/v1/docs
```

**3. Event-Driven Architecture**

```python
# elf/events/bus.py
class EventBus:
    """Pub/sub for cross-module communication."""

    async def publish(self, event: Event):
        for handler in self._subscribers[event.type]:
            await handler(event)

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers[event_type].append(handler)

# Usage
bus = EventBus()

# Dashboard subscribes to heuristic changes
bus.subscribe("heuristic.promoted", update_ui_callback)

# Query system publishes events
await bus.publish(HeuristicPromoted(id=123, domain="testing"))
```

---

## 5. Scalability Considerations

### 5.1 Current Bottlenecks

**1. SQLite Concurrency**
- Single-writer limitation
- Dashboard + hooks + background jobs all write
- File locking contention on Windows

**Current:**
```python
# apps/dashboard/backend/main.py
def _get_db_change_counts():
    with get_db() as conn:  # Blocks entire function
        cursor = conn.cursor()
        # Multiple SELECT queries...
```

**Recommendation:**
```python
# Connection pooling with retry logic
import sqlite3
from contextlib import asynccontextmanager

class SQLitePool:
    def __init__(self, db_path: Path, pool_size: int = 5):
        self._db_path = db_path
        self._pool = asyncio.Queue(maxsize=pool_size)
        for _ in range(pool_size):
            self._pool.put_nowait(sqlite3.connect(db_path))

    @asynccontextmanager
    async def acquire(self, timeout: float = 5.0):
        conn = await asyncio.wait_for(self._pool.get(), timeout=timeout)
        try:
            yield conn
        finally:
            await self._pool.put(conn)

# Read replicas for analytics
analytics_db = SQLitePool(db_path, pool_size=10)  # Read-heavy
write_db = SQLitePool(db_path, pool_size=2)       # Write-only
```

**2. File-Based Blackboard**
- .coordination/blackboard.json grows indefinitely
- JSON parse/serialize on every operation
- File locking overhead

**Recommendation:**
```python
# Hybrid: Redis for real-time, SQLite for history
class HybridBlackboard:
    def __init__(self, redis_client, sqlite_conn):
        self.cache = redis_client      # Real-time state
        self.archive = sqlite_conn     # Historical queries

    async def add_finding(self, finding: Finding):
        # Write to Redis for immediate access
        await self.cache.lpush("findings", finding.json())

        # Async background: Persist to SQLite
        asyncio.create_task(self._persist_finding(finding))

    async def get_recent_findings(self, limit: int = 10):
        # Fast Redis read
        return await self.cache.lrange("findings", 0, limit-1)
```

**3. Dashboard WebSocket Broadcasting**
- O(n) broadcast to all connected clients
- No message filtering
- Unnecessary updates sent

**Current:**
```python
async def broadcast_update(self, topic: str, data: dict):
    for connection in self.active_connections:
        await connection.send_json({"type": topic, "data": data})
```

**Recommendation:**
```python
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def subscribe(self, ws: WebSocket, topics: List[str]):
        for topic in topics:
            self.connections.setdefault(topic, set()).add(ws)

    async def broadcast(self, topic: str, data: dict):
        # Only send to interested subscribers
        for ws in self.connections.get(topic, set()):
            try:
                await ws.send_json({"type": topic, "data": data})
            except:
                await self.unsubscribe(ws, [topic])
```

### 5.2 Horizontal Scaling Readiness

**Current:** Single-process, localhost-only

**To Enable Multi-Instance:**

1. **Replace File-Based Coordination**
   ```python
   # Current: .coordination/blackboard.json
   # Problem: Single node only

   # Solution: Shared state store
   class RedisBlackboard(Blackboard):
       def __init__(self, redis_url: str):
           self.redis = aioredis.from_url(redis_url)

       async def register_agent(self, agent_id: str, task: str):
           await self.redis.hset(f"agent:{agent_id}", mapping={
               "task": task,
               "registered_at": datetime.now().isoformat()
           })
           await self.redis.expire(f"agent:{agent_id}", 3600)
   ```

2. **Distributed Locking**
   ```python
   from redis.lock import Lock

   class DistributedLock:
       def __init__(self, redis_client, name: str):
           self.lock = Lock(redis_client, name, timeout=30)

       async def __aenter__(self):
           acquired = await self.lock.acquire(blocking=True, timeout=30)
           if not acquired:
               raise TimeoutError("Could not acquire distributed lock")

       async def __aexit__(self, *args):
           await self.lock.release()
   ```

3. **Load Balancer Support**
   ```python
   # apps/dashboard/backend/main.py

   # Add health check endpoint
   @app.get("/health")
   async def health_check():
       try:
           # Verify database connection
           async with db_pool.acquire() as conn:
               await conn.execute("SELECT 1")
           return {"status": "healthy"}
       except Exception as e:
           raise HTTPException(503, f"Unhealthy: {e}")
   ```

---

## 6. Integration Points

### 6.1 External System Integration

**Current Integrations:**

1. **Claude Code Hooks** - Tight coupling
   ```python
   # src/hooks/learning-loop/user_prompt_inject_context.py
   # Directly executes: python query.py --context
   # Problem: No abstraction, hard-coded paths
   ```

2. **TalkinHead Avatar** - Unidirectional
   ```python
   # apps/dashboard/TalkinHead/
   # Receives events but can't send back
   # Problem: No bidirectional communication
   ```

3. **Basic Memory MCP** - Documented but not integrated
   ```python
   # coordinator/blackboard.py mentions MCP but doesn't use it
   # Problem: Duplication of semantic search logic
   ```

**Recommendation: Plugin Architecture**

```python
# elf/plugins/base.py
class ELFPlugin(ABC):
    """Base class for ELF plugins."""

    @abstractmethod
    async def initialize(self, elf: 'ELFClient'):
        """Called when plugin loads."""

    @abstractmethod
    async def on_event(self, event: Event):
        """Handle ELF events."""

    @abstractmethod
    async def shutdown(self):
        """Clean shutdown."""

# elf/plugins/registry.py
class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, ELFPlugin] = {}

    async def load(self, plugin_path: Path):
        spec = importlib.util.spec_from_file_location("plugin", plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugin = module.Plugin()  # Convention: Plugin class
        await plugin.initialize(self.elf)
        self.plugins[plugin.name] = plugin

    async def broadcast_event(self, event: Event):
        for plugin in self.plugins.values():
            await plugin.on_event(event)

# Usage: TalkinHead as plugin
class TalkinHeadPlugin(ELFPlugin):
    async def on_event(self, event: Event):
        if event.type == "task.completed":
            await self.show_celebration(event.data)
```

### 6.2 Service-to-Service Communication

**Current: Direct Function Calls**
```python
# Tight coupling
from query import QuerySystem
qs = QuerySystem()
result = qs.build_context("task")
```

**Recommendation: Service Interfaces**

```python
# elf/services/interfaces.py
class IQueryService(ABC):
    @abstractmethod
    async def build_context(self, query: str, **kwargs) -> str:
        pass

class ICoordinationService(ABC):
    @abstractmethod
    async def register_agent(self, agent: Agent) -> str:
        pass

# elf/services/registry.py
class ServiceRegistry:
    """Dependency injection container."""

    _services: Dict[type, Any] = {}

    @classmethod
    def register(cls, interface: type, implementation: Any):
        cls._services[interface] = implementation

    @classmethod
    def get(cls, interface: type) -> Any:
        if interface not in cls._services:
            raise ServiceNotFoundError(f"No implementation for {interface}")
        return cls._services[interface]

# Usage
registry = ServiceRegistry()
registry.register(IQueryService, QuerySystem())
registry.register(ICoordinationService, Orchestrator())

# Loose coupling
query_service = registry.get(IQueryService)
context = await query_service.build_context("analyze code")
```

---

## 7. Recommendations by Priority

### Priority 1: Critical (Address Immediately)

1. **Unify Query System**
   - **Issue:** Sync/async duplication in query.py and core.py
   - **Action:** Implement async core with sync facade (Option B from refactor plan)
   - **Timeline:** 1 week
   - **Risk:** Medium - Requires careful testing of all call sites

2. **Merge Coordination Systems**
   - **Issue:** coordinator/ and src/conductor/ overlap
   - **Action:** Create unified src/coordination/ module
   - **Timeline:** 2 weeks
   - **Risk:** High - Core orchestration logic

3. **Fix Dashboard Database Concurrency**
   - **Issue:** SQLite write contention, no connection pooling
   - **Action:** Implement connection pool with read replicas
   - **Timeline:** 3 days
   - **Risk:** Low - Well-understood pattern

### Priority 2: High (Within 1 Month)

4. **Establish Module Boundaries**
   - **Issue:** Inconsistent imports, circular dependencies
   - **Action:** Reorganize into elf.* namespace, update all imports
   - **Timeline:** 1 week
   - **Risk:** Medium - Requires updating many files

5. **Add API Versioning**
   - **Issue:** Dashboard API lacks versioning
   - **Action:** Prefix routes with /api/v1/, document stability
   - **Timeline:** 2 days
   - **Risk:** Low - Additive change

6. **Implement Service Layer**
   - **Issue:** Business logic in routers, direct DB access
   - **Action:** Extract services, use repository pattern
   - **Timeline:** 1 week
   - **Risk:** Medium - Refactoring existing code

### Priority 3: Medium (Within 3 Months)

7. **Plugin Architecture**
   - **Issue:** Extensions are tightly coupled
   - **Action:** Create plugin system for loose coupling
   - **Timeline:** 2 weeks
   - **Risk:** Low - New functionality

8. **Event-Driven Communication**
   - **Issue:** Direct function calls between modules
   - **Action:** Implement event bus for decoupling
   - **Timeline:** 1 week
   - **Risk:** Medium - Changes communication patterns

9. **Configuration Management**
   - **Issue:** Implicit path resolution, side effects
   - **Action:** Centralized ELFConfig with explicit initialization
   - **Timeline:** 3 days
   - **Risk:** Low - Mostly refactoring

### Priority 4: Low (Future Enhancements)

10. **Horizontal Scaling Support**
    - **Issue:** Single-process, file-based coordination
    - **Action:** Redis for state, distributed locking
    - **Timeline:** 2 weeks
    - **Risk:** Low - Optional feature

11. **OpenAPI Specification**
    - **Issue:** No formal API contract
    - **Action:** Generate OpenAPI docs, client SDKs
    - **Timeline:** 1 week
    - **Risk:** Low - Documentation task

---

## 8. Architecture Decision Records (ADRs)

### ADR-001: Async Core with Sync Facade

**Status:** Proposed
**Date:** 2026-01-05
**Decision:** Use async implementation as canonical, provide sync wrapper for compatibility

**Context:**
- Two complete implementations exist (sync query.py, async core.py)
- External scripts depend on sync API
- Modern Python favors async for I/O operations

**Decision:**
- Make core.py the single source of truth
- query.py becomes thin sync wrapper using asyncio.run()
- All new code uses async API

**Consequences:**
- Positive: Single implementation, easier maintenance
- Negative: Slight performance overhead in sync wrapper
- Positive: Migration path for external callers

### ADR-002: Unified Coordination Module

**Status:** Proposed
**Date:** 2026-01-05
**Decision:** Merge coordinator/ and src/conductor/ into src/coordination/

**Context:**
- Two overlapping coordination systems
- Developers confused about which to use
- Both handle agent orchestration but differently

**Decision:**
- Create src/coordination/ with clear submodules
- Persistent workflows use SQLite (conductor pattern)
- Real-time coordination uses blackboard pattern
- Unified Orchestrator interface abstracts both

**Consequences:**
- Positive: Clear mental model, one way to coordinate
- Negative: Migration effort for existing workflows
- Positive: Can use both patterns where appropriate

### ADR-003: Service Layer with Repository Pattern

**Status:** Proposed
**Date:** 2026-01-05
**Decision:** Introduce service layer between API routes and database

**Context:**
- Business logic mixed with HTTP handling
- Direct Peewee ORM access in routers
- Difficult to test or reuse logic

**Decision:**
- Extract services for each domain (HeuristicsService, etc.)
- Services use repository interfaces
- Routers become thin HTTP adapters

**Consequences:**
- Positive: Better separation of concerns
- Positive: Easier to test business logic
- Negative: More boilerplate code
- Positive: Can swap persistence implementation

---

## 9. Testing Recommendations

### Current Testing Gaps

1. **No integration tests** for query system duplication
2. **No contract tests** between services
3. **No performance benchmarks** for SQLite under load
4. **Minimal coverage** in coordinator/

### Recommended Test Architecture

```
tests/
├── unit/                  # Fast, isolated tests
│   ├── test_query.py     # Test async core
│   ├── test_coordination.py
│   └── test_services.py
│
├── integration/           # Test module boundaries
│   ├── test_query_sync_async_parity.py  # Verify facades work
│   ├── test_blackboard_sqlite.py
│   └── test_dashboard_api.py
│
├── e2e/                   # End-to-end scenarios
│   ├── test_checkin_workflow.py
│   └── test_swarm_coordination.py
│
├── performance/           # Load and stress tests
│   ├── test_concurrent_writes.py
│   └── test_websocket_broadcast.py
│
└── contracts/             # API contract tests
    ├── test_api_v1_stability.py
    └── test_plugin_interface.py
```

**Critical Tests to Add:**

```python
# tests/integration/test_query_sync_async_parity.py
import pytest
import asyncio
from elf.sync import QuerySystem as SyncQS
from elf.core import AsyncQuerySystem

@pytest.mark.asyncio
async def test_sync_async_produce_same_results():
    """Ensure sync facade delegates correctly to async core."""

    query = "test query"
    domain = "testing"

    # Sync version
    sync_qs = SyncQS()
    sync_result = sync_qs.build_context(query, domain=domain)

    # Async version
    async_qs = await AsyncQuerySystem.create()
    async_result = await async_qs.build_context(query, domain=domain)
    await async_qs.cleanup()

    # Must produce identical output
    assert sync_result == async_result

# tests/performance/test_concurrent_writes.py
import pytest
import asyncio
from elf.persistence import HeuristicsRepository

@pytest.mark.asyncio
async def test_concurrent_heuristic_writes(db_pool):
    """Verify database handles concurrent writes without corruption."""

    repo = HeuristicsRepository(db_pool)

    async def write_heuristic(i: int):
        await repo.create(
            domain=f"domain-{i}",
            rule=f"rule-{i}",
            confidence=0.5
        )

    # 100 concurrent writes
    await asyncio.gather(*[write_heuristic(i) for i in range(100)])

    # Verify all persisted
    all_heuristics = await repo.find_all()
    assert len(all_heuristics) == 100
```

---

## 10. Migration Path

### Phase 1: Foundation (Week 1-2)

**Goal:** Establish architectural baseline without breaking changes

1. Add service layer interfaces
2. Implement connection pooling
3. Add comprehensive logging
4. Create ADRs for key decisions

**Deliverables:**
- `elf/services/interfaces.py`
- `elf/infrastructure/database.py` with pooling
- `docs/architecture/ADR-*.md`

### Phase 2: Unification (Week 3-4)

**Goal:** Eliminate duplication in query and coordination

1. Implement async core with sync facade
2. Merge coordinator/ into src/coordination/
3. Update all internal callers

**Deliverables:**
- `elf/core/query.py` (canonical async)
- `elf/sync/query.py` (facade)
- `elf/coordination/` (unified)

### Phase 3: Modernization (Week 5-8)

**Goal:** Improve API design and service boundaries

1. Add API versioning to dashboard
2. Extract services from routers
3. Implement repository pattern
4. Add event bus

**Deliverables:**
- `apps/dashboard/backend/api/v1/`
- `apps/dashboard/backend/services/`
- `apps/dashboard/backend/repositories/`
- `elf/events/bus.py`

### Phase 4: Scaling (Week 9-12)

**Goal:** Enable horizontal scaling and better performance

1. Implement Redis blackboard (optional)
2. Add distributed locking
3. Performance benchmarks
4. Load testing

**Deliverables:**
- `elf/coordination/realtime/redis_blackboard.py`
- `tests/performance/`
- Performance report

---

## 11. Conclusion

### Architecture Health Summary

| Aspect | Current Score | Target Score | Priority |
|--------|--------------|--------------|----------|
| **Module Cohesion** | 6/10 | 9/10 | HIGH |
| **Low Coupling** | 5/10 | 8/10 | HIGH |
| **API Design** | 6/10 | 9/10 | MEDIUM |
| **Scalability** | 5/10 | 8/10 | MEDIUM |
| **Testability** | 6/10 | 9/10 | HIGH |
| **Maintainability** | 6/10 | 9/10 | HIGH |
| **Documentation** | 7/10 | 9/10 | LOW |

**Overall Architecture Integrity: 6.5/10**

### Key Takeaways

**Strengths:**
1. Solid conceptual foundation (learning framework, pheromone trails, swarm intelligence)
2. Modern tech stack (FastAPI, React, SQLite, asyncio)
3. Good documentation for end users
4. Active development with clear vision

**Critical Weaknesses:**
1. Dual query system implementation creates maintenance burden
2. Overlapping coordination systems (conductor vs coordinator)
3. Lack of clear service boundaries
4. No formal API contracts or versioning
5. Direct database access throughout codebase

**Immediate Actions Required:**
1. **Week 1:** Unify query system (async core + sync facade)
2. **Week 2:** Merge coordination systems
3. **Week 3:** Add service layer to dashboard
4. **Week 4:** Implement connection pooling

**Long-Term Vision:**
Transform from a collection of scripts into a modular, scalable platform with:
- Clear architectural layers (Presentation → Service → Domain → Infrastructure)
- Formal API contracts (OpenAPI specs, versioned endpoints)
- Plugin system for extensions
- Horizontal scaling support
- Comprehensive test coverage

### Next Steps

1. **Review with team** - Discuss priorities and timeline
2. **Create work branches** - One per priority 1 item
3. **Set up CI/CD** - Ensure refactoring doesn't break functionality
4. **Incremental migration** - Make small, tested changes
5. **Update documentation** - Keep ADRs current

---

**Document Version:** 1.0
**Last Updated:** 2026-01-05
**Next Review:** 2026-02-05 (after Priority 1 items complete)
