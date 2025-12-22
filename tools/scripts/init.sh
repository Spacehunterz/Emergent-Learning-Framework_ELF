#!/bin/bash
# Initialize the Emergent Learning Framework

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Initializing Emergent Learning Framework ==="
echo "Base directory: $BASE_DIR"
echo ""

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$BASE_DIR/memory/failures"
mkdir -p "$BASE_DIR/memory/successes"
mkdir -p "$BASE_DIR/memory/heuristics"
mkdir -p "$BASE_DIR/experiments/active"
mkdir -p "$BASE_DIR/experiments/completed"
mkdir -p "$BASE_DIR/cycles"
mkdir -p "$BASE_DIR/ceo-inbox"
mkdir -p "$BASE_DIR/agents"
mkdir -p "$BASE_DIR/logs"
mkdir -p "$BASE_DIR/query"
mkdir -p "$BASE_DIR/scripts"
echo "✓ Directory structure created"

# Initialize git repository
cd "$BASE_DIR"
if [ ! -d ".git" ]; then
    echo ""
    echo "Initializing git repository..."
    git init

    # Create .gitignore
    cat > .gitignore <<'EOF'
# Logs
logs/*.log
*.tmp

# OS files
.DS_Store
Thumbs.db

# Editor files
.vscode/
.idea/
*.swp
*.swo
EOF

    echo "✓ Git repository initialized"
else
    echo "✓ Git repository already exists"
fi

# Initialize database
DB_PATH="$BASE_DIR/memory/index.db"
SCHEMA_PATH="$BASE_DIR/templates/init_db.sql"

if [ -f "$SCHEMA_PATH" ]; then
    echo ""
    echo "Initializing database..."
    sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
    echo "✓ Database initialized"
else
    echo "Warning: init_db.sql not found at $SCHEMA_PATH"
    echo "Database initialization skipped"
fi

# Create initial golden rules
GOLDEN_RULES_PATH="$BASE_DIR/memory/golden-rules.md"
if [ ! -f "$GOLDEN_RULES_PATH" ]; then
    echo ""
    echo "Creating golden rules..."
    cat > "$GOLDEN_RULES_PATH" <<'EOF'
# Golden Rules

These are the most validated and critical heuristics - promoted from the general pool after proving their value repeatedly.

---

## Rule 1: Make It Work, Then Make It Right

**Confidence**: 0.9
**Source**: observation
**Domain**: architecture

First focus on getting a working solution, even if imperfect. Then refactor and optimize. Trying to build the perfect architecture from the start often leads to analysis paralysis.

**Validated**: Proven across multiple projects
**Violations**: Premature optimization often causes delays

---

## Rule 2: Explicit is Better Than Implicit

**Confidence**: 0.95
**Source**: failure
**Domain**: coordination

When coordinating between agents, explicit communication of intent, state, and expectations prevents misunderstandings. Hidden assumptions are the enemy of reliable systems.

**Validated**: Critical for agent coordination
**Violations**: Implicit assumptions cause cascading failures

---

## Rule 3: Fail Fast, Learn Faster

**Confidence**: 0.85
**Source**: observation
**Domain**: debugging

Design systems to fail quickly and obviously rather than silently degrading. Fast feedback loops accelerate learning.

**Validated**: Speeds up debugging cycles
**Violations**: Silent failures waste time

---

## Rule 4: Document Decisions, Not Just Code

**Confidence**: 0.9
**Source**: success
**Domain**: coordination

Record the "why" behind decisions, not just the "what". Future you (or future agents) will thank you.

**Validated**: Prevents repeated mistakes
**Violations**: Forgotten context leads to regression

---

*These rules are living documents. As we learn more, they evolve.*
EOF
    echo "✓ Golden rules created"
else
    echo "✓ Golden rules already exist"
fi

# Create README if it does not exist
README_PATH="$BASE_DIR/README.md"
if [ ! -f "$README_PATH" ]; then
    echo ""
    echo "Creating README..."
    cat > "$README_PATH" <<'EOF'
# Emergent Learning Framework

A systematic approach to learning from failures, extracting heuristics, and running deliberate experiments.

## Directory Structure

```
emergent-learning/
├── memory/              # The knowledge base
│   ├── failures/        # Documented failures
│   ├── successes/       # Documented successes
│   ├── heuristics/      # Extracted rules by domain
│   ├── schema.sql       # Database schema
│   └── index.db         # SQLite index
├── experiments/         # Active learning experiments
│   ├── active/          # Currently running
│   └── completed/       # Finished experiments
├── cycles/              # Try/Break cycle logs
├── ceo-inbox/           # Decisions requiring human input
├── agents/              # Agent configurations
├── logs/                # Execution logs
├── query/               # Query tools and dashboards
└── scripts/             # Helper scripts
```

## Quick Start

### Initialize the Framework

```bash
./scripts/init.sh         # Bash
./scripts/init.ps1        # PowerShell
```

### Record a Failure

```bash
./scripts/record-failure.sh      # Bash
./scripts/record-failure.ps1     # PowerShell
```

### Record a Heuristic

```bash
./scripts/record-heuristic.sh    # Bash
./scripts/record-heuristic.ps1   # PowerShell
```

### Start an Experiment

```bash
./scripts/start-experiment.sh    # Bash
./scripts/start-experiment.ps1   # PowerShell
```

## Philosophy

1. **Fail Deliberately**: Create controlled experiments to test assumptions
2. **Extract Patterns**: Convert experiences into reusable heuristics
3. **Validate Continuously**: Track which rules prove helpful vs harmful
4. **Promote the Best**: Elevate proven heuristics to golden rules
5. **Stay Humble**: All knowledge is provisional and subject to revision

## The Learning Loop

```
Try → Break → Analyze → Extract → Validate → Promote
```

Every cycle adds to our collective intelligence.
EOF
    echo "✓ README created"
else
    echo "✓ README already exists"
fi

# Initial git commit
echo ""
echo "Creating initial git commit..."
git add .
git commit -m "init: Initialize Emergent Learning Framework" -m "Created directory structure, database, and golden rules" || echo "Already committed"
echo "✓ Initial commit created"

echo ""
echo "========================================="
echo "✓ Framework initialized successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Review golden rules: memory/golden-rules.md"
echo "  2. Record your first failure: ./scripts/record-failure.sh"
echo "  3. Start an experiment: ./scripts/start-experiment.sh"
echo ""
echo "Happy learning!"
