# Architecture Decision Records (ADR)

Key architectural decisions made during ELF development.

---

## ADR-001: SQLite as Primary Database

**Date:** 2024-11-15  
**Status:** Accepted  
**Context:** Need local, fast, zero-config database for learnings  

**Decision:** Use SQLite for memory/index.db

**Rationale:**
- Zero configuration required
- File-based, easy backup/restore
- Fast for single-user workloads
- Built into Python standard library

**Consequences:**
- **Positive:** Simple installation, no server needed
- **Negative:** Limited multi-user concurrency
- **Tradeoff:** Accepted for development-focused tool

**Alternatives Considered:**
- PostgreSQL: Too heavy, requires server
- JSON files: Too slow for queries
- In-memory: Data lost on restart

---

## ADR-002: Hooks-Based Learning Capture

**Date:** 2024-11-20  
**Status:** Accepted  
**Context:** Need automatic learning without manual intervention

**Decision:** Use Claude Code PreToolUse/PostToolUse hooks

**Rationale:**
- Automatic, no user action required
- Access to task context before/after execution
- Built into Claude Code platform

**Consequences:**
- **Positive:** Zero-friction learning capture
- **Negative:** Depends on hook system stability
- **Tradeoff:** Automatic trumps manual

**Alternatives Considered:**
- Manual recording only: Too easy to forget
- Prompt injection: Fragile, model-dependent
- External monitoring: No access to task context

---

## ADR-003: Confidence Scoring System

**Date:** 2024-12-01  
**Status:** Accepted  
**Context:** Need to distinguish strong patterns from weak ones

**Decision:** Heuristic confidence = validations / (validations + violations)

**Rationale:**
- Simple formula, easy to understand
- Increases with successes, decreases with failures
- Threshold of 0.9 for golden rule promotion

**Consequences:**
- **Positive:** Clear progression path for patterns
- **Negative:** Simple formula may miss nuance
- **Tradeoff:** Simplicity over sophistication

**Alternatives Considered:**
- Bayesian confidence: Too complex
- Time-based decay: Doesn't reflect actual usage
- Manual promotion only: Doesn't scale

---

## ADR-004: React + FastAPI for Dashboard

**Date:** 2024-12-05  
**Status:** Accepted  
**Context:** Need visual interface for browsing learnings

**Decision:** React frontend + FastAPI backend + WebSockets

**Rationale:**
- React: Rich UI, component reusability
- FastAPI: Python backend, matches query.py ecosystem
- WebSockets: Real-time updates without polling

**Consequences:**
- **Positive:** Modern stack, good DX
- **Negative:** Requires Node.js + Python
- **Tradeoff:** Rich UI justifies dual runtime

**Alternatives Considered:**
- CLI only: Not as discoverable
- Static HTML: No real-time updates
- Electron app: Too heavy for simple dashboard

---

## ADR-005: Swarm Multi-Agent Pattern

**Date:** 2024-12-08  
**Status:** Accepted  
**Context:** Complex tasks benefit from multiple perspectives

**Decision:** Conductor orchestrates specialized agent personas

**Rationale:**
- Parallel investigation faster than serial
- Different personas (Researcher, Architect, Skeptic) provide diversity
- Blackboard pattern enables coordination

**Consequences:**
- **Positive:** Speeds up complex debugging
- **Negative:** Higher token cost, Pro/Max plan only
- **Tradeoff:** Value for complex tasks, optional feature

**Alternatives Considered:**
- Single agent only: Slower, one perspective
- Hardcoded workflow: Less flexible
- Full DAG workflow engine: Over-engineered

---

## ADR-006: CLAUDE.md for Agent Instructions

**Date:** 2024-11-18  
**Status:** Accepted  
**Context:** Need to instruct Claude to query the building

**Decision:** Use CLAUDE.md global instructions file

**Rationale:**
- Loaded automatically by Claude Code at session start
- Persistent across sessions
- Version controlled by user

**Consequences:**
- **Positive:** Always injected, no manual step
- **Negative:** Competes with user custom instructions
- **Tradeoff:** Provide merge guidance in installer

**Alternatives Considered:**
- Prompt prefix: Not persistent
- Environment variable: Not visible to user
- Slash command only: Easy to forget

---

## ADR-007: Filesystem Structure

**Date:** 2024-11-22  
**Status:** Accepted  
**Context:** Where to install ELF components

**Decision:** Install to ~/.claude/emergent-learning/

**Rationale:**
- Standard hidden directory convention
- Grouped with Claude Code config (~/.claude/)
- Namespace emergent-learning prevents conflicts

**Consequences:**
- **Positive:** Discoverable, standard location
- **Negative:** Hidden directory less visible
- **Tradeoff:** Convention over discoverability

**Alternatives Considered:**
- ~/elf/: Not associated with Claude
- ~/.config/elf/: Doesn't match Claude Code convention
- /usr/local/: Requires sudo, shared install

---

## ADR-008: Optional Components (Core/Dashboard/Swarm)

**Date:** 2024-12-06  
**Status:** Accepted  
**Context:** Not all users need all features

**Decision:** Modular install with --core-only, --no-dashboard, --no-swarm flags

**Rationale:**
- Core is universal
- Dashboard requires Node.js (some users don't have it)
- Swarm requires Pro/Max plan (Free users can't use it)

**Consequences:**
- **Positive:** Users install only what they need
- **Negative:** More install complexity
- **Tradeoff:** Flexibility over simplicity

**Alternatives Considered:**
- All-or-nothing: Excludes Free plan users
- Separate repos: Too much fragmentation
- Plugin system: Over-engineered

---

## ADR-009: No Cloud Service

**Date:** 2024-11-16  
**Status:** Accepted  
**Context:** Should learnings be synced to cloud?

**Decision:** No cloud service. Local-only database.

**Rationale:**
- Privacy: User data stays on user machine
- Simplicity: No server to maintain
- Cost: No cloud infrastructure needed
- Portability: Export/import for sharing

**Consequences:**
- **Positive:** Privacy, simplicity, no ongoing cost
- **Negative:** No automatic team sync
- **Tradeoff:** Export/import is manual but controlled

**Alternatives Considered:**
- Cloud sync: Privacy concerns, ongoing cost
- P2P sync: Complex, firewall issues
- Git-based: Merge conflicts on binary DB

---

## ADR-010: Golden Rules in Markdown

**Date:** 2024-11-25  
**Status:** Accepted  
**Context:** How to store constitutional principles

**Decision:** golden-rules.md as human-readable markdown

**Rationale:**
- Human-readable and editable
- Version control friendly
- Can be included in CLAUDE.md or docs
- Doesn't require database query

**Consequences:**
- **Positive:** Easy to read, edit, version control
- **Negative:** Separate from database (not queryable)
- **Tradeoff:** Readability over centralization

**Alternatives Considered:**
- In database: Less readable
- Python constants: Not user-editable
- YAML config: Less readable than markdown

---

## Decision Process

### When to Create an ADR

Create an ADR for:
- Architectural choices affecting multiple components
- Technology stack decisions
- Trade-offs with significant consequences
- Decisions that constrain future changes

### ADR Template



### Reviewing ADRs

ADRs are living documents:
- **Accepted:** Currently in use
- **Deprecated:** No longer recommended, but not removed
- **Superseded:** Replaced by newer ADR (link to replacement)

---

*Last updated: 2025-12-08*
