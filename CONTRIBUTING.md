# Contributing to Emergent Learning Framework

Thank you for your interest in contributing to ELF! This document provides guidelines for setting up your development environment, understanding the codebase, and submitting contributions.

## Important Notice

**ELF is currently not accepting pull requests.** This is an active research project undergoing rapid experimentation and architectural refinement. The main branch represents live development and changes frequently.

**We welcome:**
- Feature requests via [GitHub Discussions](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/discussions)
- Bug reports via [GitHub Issues](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues)
- Questions and usage help via [GitHub Discussions](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/discussions)

If you want to contribute code, please open a discussion first to coordinate with the maintainers.

---

## Development Environment Setup

### Prerequisites

**Required:**
- Python 3.8 or higher
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)

**Optional (for Dashboard):**
- Node.js 18+ or Bun (Bun recommended on Windows)
- pnpm (optional, npm works but Bun is faster)

**Optional (for Swarm features):**
- Claude Code Pro or Max subscription

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF.git
cd Emergent-Learning-Framework_ELF

# Run the installer (sets up hooks, core system)
./install.sh              # Mac/Linux
./install.ps1             # Windows (PowerShell)

# Or install manually:
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Validate installation
python -m query --validate
```

### Dashboard Setup

```bash
cd apps/dashboard/frontend

# Using Bun (recommended, especially on Windows)
bun install
bun run dev

# Or using npm
npm install
npm run dev

# Dashboard runs at http://localhost:3001
```

**Windows Note:** Git Bash is not supported for npm operations. Use PowerShell or CMD. If you encounter `Cannot find module @rollup/rollup-win32-x64-msvc`, switch to Bun.

---

## Project Structure

### Core Directories

```
emergent-learning/
├── src/
│   ├── query/              # Core query system - SQLite knowledge retrieval
│   ├── conductor/          # Multi-agent orchestration (swarm coordination)
│   ├── hooks/              # Claude Code integration hooks
│   ├── agents/             # Agent personas and workflows
│   ├── skills/             # Reusable agent skills
│   └── watcher/            # Async monitoring system (Haiku→Opus escalation)
├── apps/
│   └── dashboard/
│       ├── frontend/       # React + TypeScript dashboard (Vite)
│       └── backend/        # Python backend (optional, future)
├── tests/                  # Python test suites
├── memory/
│   ├── golden-rules.md     # High-confidence universal principles
│   └── successes/          # Documented success patterns
├── scripts/                # CLI utilities and automation
├── coordinator/            # Legacy coordinator (being refactored)
└── docs/                   # Documentation and assets
```

### Key Components

**Query System (`src/query/`)**
- Async SQLite operations for knowledge retrieval
- Heuristic confidence tracking
- Domain-based pattern matching
- Project-scoped learning (`.elf/` directories)

**Conductor (`src/conductor/`)**
- Multi-agent blackboard architecture
- Agent claim chains and dependency graphs
- Fraud detection and coordination integrity
- Event-driven workflow orchestration

**Hooks (`src/hooks/`)**
- Claude Code integration via `PreToolUse` and `PostToolUse`
- Automatic context injection before tasks
- Outcome recording after task completion

**Dashboard (`apps/dashboard/frontend/`)**
- React 18 + TypeScript
- Three.js 3D visualizations (Galaxy view)
- Zustand state management
- Tailwind CSS styling
- Real-time WebSocket updates

---

## Running Tests

### Python Tests

```bash
# Activate virtual environment
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Run all tests
pytest

# Run specific test file
pytest tests/test_blackboard_v2.py

# Run tests matching pattern
pytest -k "claim_chain"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Suites Overview

| Test File | Focus Area |
|-----------|-----------|
| `test_blackboard_v2.py` | Blackboard architecture, agent coordination |
| `test_claim_chains*.py` | Claim chain integrity, fraud detection |
| `test_conductor_workflow.py` | Workflow orchestration end-to-end |
| `test_dependency_graph.py` | Agent dependency resolution |
| `test_fraud_*.py` | Fraud detection algorithms |
| `test_stress.py` | High-load concurrent operations |
| `test_sqlite_edge_cases.py` | Database edge cases and corruption recovery |

### Dashboard Tests (Playwright)

```bash
cd apps/dashboard/frontend

# Install Playwright browsers (first time only)
npx playwright install

# Run tests
npm test              # or: bun test
npx playwright test

# Run in UI mode (interactive)
npx playwright test --ui

# Run specific test
npx playwright test tests/dashboard.spec.ts
```

---

## Code Style Guidelines

### Python

**Type Hints Required**
```python
# Good
def query_heuristics(domain: str, limit: int = 10) -> list[dict]:
    pass

# Bad
def query_heuristics(domain, limit=10):
    pass
```

**Why:** Type hints improve IDE support, catch errors early, and serve as inline documentation. We use Mypy for static type checking.

**No Docstrings**
```python
# Good
def validate_claim_chain(chain_id: str) -> bool:
    integrity_check = check_signatures(chain_id)
    fraud_score = compute_fraud_risk(chain_id)
    return integrity_check and fraud_score < 0.3

# Bad
def validate_claim_chain(chain_id: str) -> bool:
    """
    Validates a claim chain by checking signatures and fraud score.

    Args:
        chain_id: The ID of the claim chain to validate

    Returns:
        True if valid, False otherwise
    """
    # ... implementation
```

**Why:** Claude reads code directly, making docstrings redundant and wasteful of tokens. Descriptive names and type hints provide the necessary context. Use commit messages for "why" explanations.

**Other Python Conventions**
- Use `python -m module` over direct script execution
- Always activate virtual environment before pip operations
- Prefer `async/await` for I/O operations
- Use `thiserror` patterns for error handling (typed errors)
- Validate input at system boundaries only

### TypeScript

**Strict Mode Required**
```typescript
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

**React Conventions**
- Use refs for callbacks in effects to avoid reconnect loops (Golden Rule #9)
- Await every Promise - no floating promises
- Forward slashes in paths (cross-platform compatibility)

### Universal Rules

**No Code Comments**
```python
# Bad
# Calculate confidence score based on validations
confidence = validations / (validations + violations)

# Good (descriptive naming)
def calculate_confidence(validations: int, violations: int) -> float:
    return validations / (validations + violations)
```

**Why:** Comments waste tokens in Claude's context. Descriptive names are self-documenting. Commit messages preserve reasoning in Git history.

**Zero-Dependency Preference**

Before adding a dependency, ask:
- Can we implement this in <100 lines?
- Does the dependency add significant value?
- What's the maintenance burden?

Justify new dependencies in commit messages.

---

## Git Workflow

### Branch Naming

Not applicable - PRs not currently accepted. For your own forks:
- `feature/descriptive-name`
- `fix/issue-description`
- `refactor/component-name`

### Commit Messages

Follow the conventional commit format:

```
<type>: <short description>

[optional body explaining WHY, not WHAT]

[optional footer with references]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `docs`: Documentation only
- `test`: Adding or updating tests
- `perf`: Performance improvement
- `chore`: Tooling, dependencies, etc.

**Examples:**

```
fix: resolve WebSocket reconnect loop in dashboard

React useEffect was re-running on every render because onMessage
callback was a new reference each time. Moved callback to ref,
updated ref in separate effect, used empty deps for connection.

Closes #123
```

```
feat: add temporal smoothing to confidence scores

Prevents confidence from spiking based on single data points.
Uses exponential moving average with configurable alpha.
```

### Commit Hygiene

- One logical change per commit
- Commits should be buildable and testable
- No "while we're here" changes (Golden Rule #21)
- Reference issue numbers in commit body

---

## Architecture Overview

### The Learning Loop

```
┌─────────────────────────────────────────────────┐
│                LEARNING CYCLE                    │
├─────────────────────────────────────────────────┤
│  1. QUERY    → Check building for knowledge     │
│  2. APPLY    → Use heuristics during task       │
│  3. RECORD   → Capture outcome (success/fail)   │
│  4. PERSIST  → Update confidence scores         │
│                                                  │
│       (cycle repeats, patterns strengthen)       │
└─────────────────────────────────────────────────┘
```

### Data Flow

```
Claude Code Session
       ↓
   PreToolUse Hook → Query System → SQLite
       ↓                              ↓
   Context Injection            Heuristics DB
       ↓
   Task Execution
       ↓
   PostToolUse Hook → Record Outcome → Update Confidence
```

### Blackboard Architecture (Swarm)

```
┌───────────┐     ┌───────────┐     ┌───────────┐
│  Agent A  │────▶│ Blackboard│◀────│  Agent B  │
└───────────┘     │  (.coord/) │     └───────────┘
                  └─────┬─────┘
                        │
                  ┌─────▼─────┐
                  │  Agent C  │
                  └───────────┘
```

Agents read/write to shared state in `.coordination/` rather than direct messaging. This provides:
- Decoupling (agents don't need to know about each other)
- Observability (all state changes are logged)
- Debuggability (inspect blackboard at any point)

### Key Design Decisions

**Why SQLite?**
- Zero configuration
- File-based (no server required)
- Excellent for read-heavy workloads
- Supports concurrent reads

**Why Async/Await in Query System?**
- Non-blocking database operations
- 2.9x faster for mixed workloads (concurrent queries)
- Better resource utilization

**Why No Docstrings?**
- Claude reads code directly
- Docstrings waste context tokens
- Type hints + descriptive names are sufficient
- Git commit messages preserve "why"

**Why Blackboard over Message Passing?**
- Decouples agents (no direct dependencies)
- Observable state (all changes logged)
- Easier debugging (inspect state at any point)
- Natural fit for distributed coordination

---

## Pull Request Process (When Accepted)

**Currently not accepting PRs.** When this changes, the process will be:

1. **Open a Discussion First**
   - Describe the problem and proposed solution
   - Get maintainer feedback before coding
   - Ensure alignment with project goals

2. **Create a Branch**
   - Fork the repository
   - Create a feature branch
   - Make your changes

3. **Write Tests**
   - Add tests for new functionality
   - Ensure existing tests pass
   - Aim for >80% coverage on new code

4. **Run Checks**
   ```bash
   # Type checking
   mypy src/

   # Tests
   pytest

   # Dashboard tests (if applicable)
   cd apps/dashboard/frontend && npm test
   ```

5. **Submit PR**
   - Reference related issues/discussions
   - Describe what changed and why
   - Include test results
   - Add screenshots for UI changes

6. **Code Review**
   - Address reviewer feedback
   - Keep PR focused (no scope creep)
   - Be responsive to questions

7. **Merge**
   - Maintainer merges after approval
   - Delete your branch after merge

---

## Testing Philosophy

### Break It Before Shipping It

Golden Rule #4: Actively try to break your solution before declaring it done.

**When writing tests, consider:**
- Edge cases (empty input, null, extremely large values)
- Race conditions (concurrent access)
- Error propagation (what happens when dependencies fail)
- Recovery scenarios (crash recovery, partial writes)

### Test Organization

Tests are organized by component and focus area:

**Unit Tests** - Single component isolation
- Fast, deterministic
- Mock external dependencies
- High coverage of edge cases

**Integration Tests** - Multi-component interaction
- Database + query system
- Blackboard + agents
- Hooks + query system

**Stress Tests** - High-load scenarios
- Concurrent database access
- Large knowledge bases
- Long-running workflows

### Writing Good Tests

```python
# Good: Descriptive name, single concern, clear assertion
def test_confidence_increases_after_validation():
    heuristic = create_heuristic(confidence=0.5)
    heuristic.record_validation()
    assert heuristic.confidence > 0.5

# Bad: Vague name, multiple concerns, unclear intent
def test_heuristic():
    h = Heuristic()
    h.validate()
    h.violate()
    assert h.conf == 0.5
```

---

## Common Development Tasks

### Adding a New Heuristic Domain

1. Update `src/query/domains.py` (if it exists) or query schema
2. Add domain-specific tests
3. Document domain in golden rules if universally applicable

### Adding a New Agent Persona

1. Create agent directory in `src/agents/`
2. Define persona.md with role, strengths, weaknesses
3. Add workflow.py with agent logic
4. Update conductor to recognize new agent type
5. Add integration tests

### Updating the Dashboard

1. Make changes in `apps/dashboard/frontend/src/`
2. Test locally with `bun run dev`
3. Add Playwright tests for new features
4. Update dashboard documentation

### Modifying the Query System

1. Changes to `src/query/query_system.py`
2. Update schema if database structure changes
3. Add migration script if needed
4. Update tests in `tests/test_*.py`
5. Run validation: `python -m query --validate`

---

## Getting Help

- **Feature Requests:** [GitHub Discussions](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/discussions)
- **Bug Reports:** [GitHub Issues](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues)
- **Questions:** [GitHub Discussions](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/discussions)
- **Documentation:** [Wiki](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki)

---

## License

By contributing to ELF, you agree that your contributions will be licensed under the MIT License.

See [LICENSE](LICENSE) for full text.

---

## Code of Conduct

**Be Respectful**
- Assume good intent
- Critique ideas, not people
- Welcome newcomers

**Be Constructive**
- Provide context with criticism
- Suggest alternatives
- Help others learn

**Be Professional**
- No harassment or discrimination
- Keep discussions on-topic
- Respect maintainer decisions

---

## Additional Resources

- [Getting Started Guide](GETTING_STARTED.md) - Initial setup walkthrough
- [README](README.md) - Project overview and features
- [Golden Rules](memory/golden-rules.md) - Proven development principles
- [Architecture Wiki](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Architecture) - Deep dive into system design

---

**Remember:** This is a research project exploring how AI agents can build institutional knowledge. Your contributions, whether code, documentation, or thoughtful discussion, help push this field forward. Thank you for being part of the journey.
